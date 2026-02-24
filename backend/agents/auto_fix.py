"""
Auto-Fix Agent — LLM-powered error correction for generated backends.

In the Cloud/Electron architecture, this agent receives the verification failure report
from the Electron local test runner, and attempts to resolve the underlying bug by:
1. Analyzing the failed tests and error messages
2. Loading the current project spec and generated code
3. Using an LLM to identify the root cause
4. Generating patches for the affected files
5. Reassembling and returning a fixed ZIP

The agent uses Google Gemini via ADK as the primary provider, with Groq as a fallback
when Gemini quotas are exhausted.
"""

import uuid
import logging
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from sqlalchemy.orm import Session

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from backend.app.spec_schema import AutoFixRequest, BackendSpec
from backend.app.platform_db import Project
from backend.app.code_generator import generate_project_files
from backend.app.project_assembler import assemble_project
from backend.app import storage
from backend.agents.model_registry import DEFAULT_MODEL

logger = logging.getLogger(__name__)

# Import Groq client for fallback
try:
    try:
        from backend.agents.groq_client import GroqClient
    except ImportError:
        from agents.groq_client import GroqClient
    GROQ_AVAILABLE = GroqClient.is_available()
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("Groq client not available. Install groq library for fallback support.")


@dataclass
class AutoFixResult:
    success: bool
    errors: list[str] | None = None
    warnings: list[str] | None = None


_AUTO_FIX_INSTRUCTION = """You are an expert backend debugging agent.

Your job is to analyze failed API endpoint tests and fix the underlying code issues.

You will receive:
1. The original backend specification (JSON)
2. Failed test reports with error messages
3. The current generated code files

Your task:
1. Analyze the failed tests to identify the root cause
2. Determine which files need to be modified
3. Generate ONLY the specific code changes needed to fix the issues
4. Return a JSON object with file patches

RULES:
1. Return ONLY valid JSON. No markdown, no explanation.
2. Focus on the most likely root causes (missing imports, incorrect field types, validation errors)
3. Make minimal changes - only fix what's broken
4. Preserve existing functionality
5. Common issues to check:
   - Missing or incorrect imports
   - Field type mismatches (e.g., UUID vs string)
   - Missing validation logic
   - Incorrect route definitions
   - Database model inconsistencies

OUTPUT FORMAT:
{
  "analysis": "Brief explanation of what went wrong",
  "fixes": [
    {
      "file": "path/to/file.py",
      "reason": "Why this file needs to be changed",
      "changes": "The complete fixed file content"
    }
  ]
}

Return ONLY the JSON object. Nothing else."""


def _create_fix_agent(model_id: str) -> Agent:
    """Create a fresh ADK Agent for auto-fixing."""
    return Agent(
        name="auto_fix_agent",
        model=model_id,
        description="Analyzes failed tests and generates code fixes.",
        instruction=_AUTO_FIX_INSTRUCTION,
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,  # Slightly higher for creative problem-solving
            response_mime_type="application/json",
        ),
    )


async def _analyze_and_fix(
    spec: BackendSpec,
    failed_tests: list[dict],
    current_files: dict[str, str],
    model_id: str = DEFAULT_MODEL,
    use_groq: bool = False,
) -> dict:
    """
    Use LLM to analyze failed tests and generate fixes.
    
    Args:
        spec: Backend specification
        failed_tests: List of failed test details
        current_files: Current project files
        model_id: Model to use (for Gemini)
        use_groq: If True, use Groq instead of Gemini
    
    Returns:
        Dict with 'analysis' and 'fixes' keys
    """
    # Build context for the LLM
    failed_tests_summary = "\n".join([
        f"- {test['method']} {test['endpoint']}: {test['error_message']}"
        for test in failed_tests
    ])
    
    # Include only relevant files (not the entire codebase)
    relevant_files = {
        k: v for k, v in current_files.items()
        if k.endswith('.py') and not k.startswith('tests/')
    }
    
    files_summary = "\n\n".join([
        f"FILE: {filename}\n```python\n{content[:1000]}...\n```"  # Truncate long files
        for filename, content in list(relevant_files.items())[:5]  # Limit to 5 files
    ])
    
    user_message = f"""BACKEND SPECIFICATION:
{spec.model_dump_json(indent=2)}

FAILED TESTS:
{failed_tests_summary}

CURRENT CODE FILES:
{files_summary}

Please analyze these failures and provide fixes."""
    
    # Try Groq if requested or if it's available
    if use_groq and GROQ_AVAILABLE:
        try:
            logger.info("Using Groq API for auto-fix analysis")
            groq_client = GroqClient()
            
            response_text = groq_client.analyze_and_fix(
                system_prompt=_AUTO_FIX_INSTRUCTION,
                user_message=user_message,
                temperature=0.2,
                max_tokens=8192
            )
            
            # Parse and return
            fix_data = json.loads(response_text)
            logger.info("Groq analysis successful")
            return fix_data
            
        except Exception as e:
            logger.error(f"Groq API failed: {e}")
            if not use_groq:  # If Groq was fallback, re-raise
                raise
            # Otherwise, fall through to Gemini
            logger.info("Falling back to Google Gemini")
    
    # Use Google Gemini (original implementation)
    agent = _create_fix_agent(model_id)
    
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="auto_fix",
        session_service=session_service,
    )
    
    session = await session_service.create_session(
        app_name="auto_fix",
        user_id="fixer",
    )
    
    user_content = types.Content(
        role="user",
        parts=[types.Part(text=user_message)],
    )
    
    agent_response_text = ""
    
    try:
        async for event in runner.run_async(
            user_id="fixer",
            session_id=session.id,
            new_message=user_content,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    agent_response_text = event.content.parts[0].text
                break
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        
        # Check if it's a quota error and Groq is available
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            if GROQ_AVAILABLE and not use_groq:
                logger.info("Gemini quota exhausted, trying Groq fallback")
                return await _analyze_and_fix(
                    spec=spec,
                    failed_tests=failed_tests,
                    current_files=current_files,
                    model_id=model_id,
                    use_groq=True
                )
        raise
    
    if not agent_response_text:
        raise ValueError("Agent returned empty response")
    
    # Clean potential markdown wrapping
    clean_text = agent_response_text.strip()
    if clean_text.startswith("```"):
        lines = clean_text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        clean_text = "\n".join(lines)
    
    try:
        fix_data = json.loads(clean_text)
        return fix_data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        logger.error(f"Response was: {clean_text[:500]}")
        raise ValueError(f"LLM returned invalid JSON: {e}")


async def run_auto_fix_pipeline(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session,
    fix_request: AutoFixRequest
) -> AutoFixResult:
    """
    Execute the auto-fix pipeline:
    1. Load project spec and current code
    2. Analyze failed tests with LLM
    3. Apply fixes to code
    4. Reassemble and save fixed ZIP
    
    Args:
        project_id: Project to fix
        user_id: Owner of the project
        db: Database session
        fix_request: Failed test details
    
    Returns:
        AutoFixResult with success status and any warnings/errors
    """
    logger.info(f"Auto-Fix attempt {fix_request.attempt_number} for project {project_id}")
    logger.info(f"Failed tests: {len(fix_request.failed_tests)}")
    
    try:
        # Load project from database
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id
        ).first()
        
        if not project:
            return AutoFixResult(
                success=False,
                errors=["Project not found"]
            )
        
        if not project.spec_json:
            return AutoFixResult(
                success=False,
                errors=["Project has no spec - cannot fix"]
            )
        
        # Parse spec
        spec_data = json.loads(project.spec_json)
        spec = BackendSpec(**spec_data)
        
        # Load current ZIP to extract files
        zip_path = storage.get_project_zip_path(user_id, project_id)
        if not zip_path or not zip_path.exists():
            return AutoFixResult(
                success=False,
                errors=["Project ZIP not found"]
            )
        
        # Extract current files
        current_files = {}
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for file_info in zf.filelist:
                if not file_info.is_dir():
                    # Remove the project directory prefix
                    filename = file_info.filename
                    if '/' in filename:
                        filename = '/'.join(filename.split('/')[1:])
                    try:
                        content = zf.read(file_info.filename).decode('utf-8')
                        current_files[filename] = content
                    except UnicodeDecodeError:
                        # Skip binary files
                        pass
        
        logger.info(f"Extracted {len(current_files)} files from current ZIP")
        
        # Convert failed tests to dict format
        failed_tests_dict = [
            {
                "method": test.method,
                "endpoint": test.endpoint,
                "error_message": test.error_message
            }
            for test in fix_request.failed_tests
        ]
        
        # Call LLM to analyze and generate fixes
        logger.info("Calling LLM to analyze failures...")
        fix_data = await _analyze_and_fix(
            spec=spec,
            failed_tests=failed_tests_dict,
            current_files=current_files,
        )
        
        logger.info(f"LLM Analysis: {fix_data.get('analysis', 'No analysis provided')}")
        
        # Apply fixes to files
        fixes_applied = 0
        if 'fixes' in fix_data and fix_data['fixes']:
            for fix in fix_data['fixes']:
                file_path = fix.get('file')
                new_content = fix.get('changes')
                reason = fix.get('reason', 'No reason provided')
                
                if file_path and new_content:
                    current_files[file_path] = new_content
                    fixes_applied += 1
                    logger.info(f"Applied fix to {file_path}: {reason}")
        
        if fixes_applied == 0:
            logger.warning("LLM did not provide any file fixes")
            return AutoFixResult(
                success=False,
                warnings=[
                    f"Auto-fix analysis: {fix_data.get('analysis', 'Unknown')}",
                    "No specific fixes were generated. The issue may require manual intervention."
                ]
            )
        
        # Regenerate ZIP with fixed files
        logger.info(f"Reassembling project with {fixes_applied} fixes...")
        new_zip_path = assemble_project(
            project_name=spec.project_name,
            files=current_files
        )
        
        # Save fixed ZIP
        relative_path = storage.save_project_zip(user_id, project_id, new_zip_path)
        project.zip_path = relative_path
        db.commit()
        
        logger.info(f"Auto-fix complete: {fixes_applied} files modified")
        
        return AutoFixResult(
            success=True,
            warnings=[
                f"Auto-fix applied {fixes_applied} changes",
                f"Analysis: {fix_data.get('analysis', 'See logs for details')}"
            ]
        )
        
    except Exception as e:
        logger.error(f"Auto-fix failed: {e}", exc_info=True)
        return AutoFixResult(
            success=False,
            errors=[f"Auto-fix failed: {str(e)}"]
        )
