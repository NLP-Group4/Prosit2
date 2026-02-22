"""
Orchestrator — Chains the full pipeline:
  Prompt → PromptToSpecAgent → SpecReviewAgent → CodeGenerator → Assembler → DeployVerifyAgent

Each step is atomic. All intermediate artifacts are persisted to the database
for debugging, history, and user visibility.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app.spec_schema import BackendSpec
from app.code_generator import generate_project_files
from app.project_assembler import assemble_project
from app.report_generator import generate_report
from app.platform_db import Project, ProjectStatus
from app import storage
from agents.prompt_to_spec import generate_spec_from_prompt
from agents.spec_review import review_spec, ValidationResult
from agents.deploy_verify import verify_generated_backend, VerificationResult

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result of the full generation pipeline."""
    success: bool
    project_id: uuid.UUID | None = None
    zip_path: Path | None = None
    spec: BackendSpec | None = None
    errors: list[str] | None = None
    warnings: list[str] | None = None
    model_used: str | None = None
    verification: VerificationResult | None = None


def _update_project(db: Session, project: Project, **kwargs) -> None:
    """Update project fields and commit."""
    for key, value in kwargs.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)


async def run_pipeline(
    prompt: str,
    user_id: uuid.UUID,
    db: Session,
    model_id: str | None = None,
    skip_verify: bool = False,
    context: str = "",
) -> GenerationResult:
    """
    Execute the full backend generation pipeline from a natural language prompt.

    Pipeline steps (each atomic, artifacts persisted after each step):
    1. PromptToSpecAgent: prompt → BackendSpec JSON
    2. SpecReviewAgent: validate logical consistency
    3. CodeGenerator: spec → file dict
    4. ProjectAssembler: file dict → ZIP (with PROJECT_REPORT.md)
    5. DeployVerifyAgent: ZIP → Docker deploy → smoke test all endpoints

    Args:
        prompt: Natural language description of the desired backend.
        user_id: Authenticated user's ID.
        db: Database session for persisting artifacts.
        model_id: Optional model to use (defaults to registry default).
        skip_verify: If True, skip Docker-based endpoint verification.

    Returns:
        GenerationResult with project ID and artifacts on success, or errors on failure.
    """
    # Create project record
    project = Project(
        user_id=user_id,
        project_name="pending",
        prompt=prompt,
        status=ProjectStatus.PENDING,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    project_id = project.id

    # Step 1: Generate spec from prompt
    logger.info("Step 1: Running PromptToSpecAgent...")
    _update_project(db, project, status=ProjectStatus.GENERATING)

    try:
        spec, model_used = await generate_spec_from_prompt(
            prompt, model_id=model_id, context=context,
        )
        logger.info(
            f"Spec generated: {spec.project_name} with "
            f"{len(spec.entities)} entities (model: {model_used})"
        )
        # Persist spec artifact
        _update_project(
            db, project,
            project_name=spec.project_name,
            model_used=model_used,
            spec_json=spec.model_dump_json(indent=2),
        )
    except ValueError as e:
        logger.error(f"PromptToSpecAgent failed: {e}")
        _update_project(db, project, status=ProjectStatus.FAILED)
        return GenerationResult(
            success=False,
            project_id=project_id,
            errors=[f"Spec generation failed: {str(e)}"],
        )

    # Step 2: Validate spec
    logger.info("Step 2: Running SpecReviewAgent...")
    validation: ValidationResult = review_spec(spec)

    # Persist validation artifact
    validation_data = {
        "valid": validation.valid,
        "errors": validation.errors,
        "warnings": validation.warnings,
    }
    _update_project(db, project, validation_json=json.dumps(validation_data, indent=2))

    if not validation.valid:
        logger.error(f"SpecReviewAgent rejected spec: {validation.errors}")
        _update_project(db, project, status=ProjectStatus.FAILED)
        return GenerationResult(
            success=False,
            project_id=project_id,
            spec=spec,
            errors=validation.errors,
            warnings=validation.warnings,
            model_used=model_used,
        )
    if validation.warnings:
        logger.warning(f"Spec warnings: {validation.warnings}")

    # Step 3: Generate project files
    logger.info("Step 3: Running CodeGenerator...")
    files = generate_project_files(spec)
    logger.info(f"Generated {len(files)} files")

    # Step 4: Assemble project ZIP
    logger.info("Step 4: Running ProjectAssembler...")
    zip_path = assemble_project(project_name=spec.project_name, files=files)
    logger.info(f"ZIP created at: {zip_path}")

    # Step 5: Deploy and verify (optional)
    verification: VerificationResult | None = None
    all_warnings = list(validation.warnings or [])

    if not skip_verify:
        logger.info("Step 5: Running DeployVerifyAgent...")
        _update_project(db, project, status=ProjectStatus.VERIFYING)
        verification = verify_generated_backend(zip_path=zip_path, spec=spec)
        logger.info(f"Verification: {verification.summary}")

        # Persist verification artifact
        verification_data = {
            "passed": verification.passed,
            "total_tests": verification.total_tests,
            "passed_tests": verification.passed_tests,
            "failed_tests": verification.failed_tests,
            "skipped": verification.skipped,
            "skip_reason": verification.skip_reason,
            "results": [
                {
                    "method": r.method,
                    "path": r.path,
                    "expected_status": r.expected_status,
                    "actual_status": r.actual_status,
                    "passed": r.passed,
                    "error": r.error,
                }
                for r in verification.results
            ],
            "errors": verification.errors,
        }
        _update_project(db, project, verification_json=json.dumps(verification_data, indent=2))

        if verification.skipped:
            all_warnings.append(f"Verification skipped: {verification.skip_reason}")
        elif not verification.passed:
            for r in verification.results:
                if not r.passed:
                    msg = (
                        f"Endpoint test failed: {r.method} {r.path} "
                        f"→ got {r.actual_status}, expected {r.expected_status}"
                    )
                    if r.error:
                        msg += f" ({r.error})"
                    all_warnings.append(msg)
            if verification.errors:
                all_warnings.extend(verification.errors)
    else:
        logger.info("Step 5: Skipped (skip_verify=True)")

    # Step 6: Generate PROJECT_REPORT.md and re-package ZIP
    logger.info("Step 6: Generating PROJECT_REPORT.md...")
    report_md = generate_report(
        prompt=prompt,
        spec=spec,
        validation=validation,
        verification=verification,
        model_used=model_used,
    )
    # Re-assemble with report included
    files["PROJECT_REPORT.md"] = report_md
    zip_path = assemble_project(project_name=spec.project_name, files=files)

    # Move ZIP to user-scoped storage
    relative_path = storage.save_project_zip(user_id, project_id, zip_path)
    _update_project(
        db, project,
        status=ProjectStatus.COMPLETED,
        zip_path=relative_path,
    )

    return GenerationResult(
        success=True,
        project_id=project_id,
        zip_path=storage.get_project_zip_path(user_id, project_id),
        spec=spec,
        warnings=all_warnings if all_warnings else None,
        model_used=model_used,
        verification=verification,
    )
