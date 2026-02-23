"""
Backend Generation Platform — Builder API

This is the platform's own FastAPI application (not the generated one).
It accepts backend specifications and produces downloadable backend projects.
Supports both direct JSON specs and natural language prompts.

Multi-user with JWT authentication. All generations are scoped to users.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.spec_schema import (
    BackendSpec, GenerateResponse, ProjectSummary, ProjectDetail, PromptRequest, AutomaticDeployRequest,
    AutoFixRequest, ThreadSummary, ThreadDetail, MessageSchema, ChatRequest, VerificationReportRequest
)
from backend.app.code_generator import generate_project_files
from backend.app.project_assembler import assemble_project
from backend.app.report_generator import generate_report
from backend.app.platform_db import (
    get_db, PlatformUser, Project, ProjectStatus, Document, DocumentChunk, Thread, Message, init_db
)
from backend.app.platform_auth import router as auth_router, get_current_user
from backend.app import storage
from backend.app.rag import store_document, retrieve_context, delete_document
from backend.app.document_processor import (
    extract_text, UnsupportedFileError, FileTooLargeError,
)
from backend.agents.orchestrator import run_pipeline, GenerationResult
from backend.agents.model_registry import list_models, DEFAULT_MODEL
from backend.agents.spec_review import review_spec
from backend.agents.intent_router import classify_intent, Intent

load_dotenv()
logging.basicConfig(level=logging.INFO)

# Configurable CORS origins — defaults to ["*"] for local dev.
_cors_raw = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",")]

app = FastAPI(
    title="Backend Generation Platform",
    description="A deterministic backend compiler. Feed it a spec, get a Dockerized FastAPI backend.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup — initialise database tables
# ---------------------------------------------------------------------------

@app.on_event("startup")
def on_startup():
    init_db()


# ---------------------------------------------------------------------------
# Auth routes (public)
# ---------------------------------------------------------------------------

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class PromptRequest(BaseModel):
    """Request body for prompt-based generation."""
    prompt: str
    model: str | None = None
    skip_verify: bool = False


class ProjectSummary(BaseModel):
    """Brief project info for listing."""
    id: uuid.UUID
    project_name: str
    prompt: str | None
    status: str
    model_used: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ProjectDetail(BaseModel):
    """Full project detail with all artifacts."""
    id: uuid.UUID
    project_name: str
    prompt: str | None
    status: str
    model_used: str | None
    spec: dict | None = None
    validation: dict | None = None
    verification: dict | None = None
    warnings: list[str] | None = None
    download_url: str | None = None
    created_at: str
    updated_at: str


class GenerateResponse(BaseModel):
    """Response from generate endpoints."""
    project_id: uuid.UUID
    project_name: str
    status: str
    download_url: str | None = None
    warnings: list[str] | None = None


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


@app.get("/models", tags=["Models"])
def get_models():
    """List available LLM models with their status."""
    models = list_models()
    return {
        "default": DEFAULT_MODEL,
        "models": models,
    }


@app.get("/", response_class=HTMLResponse, tags=["UI"])
def root():
    """Root endpoint - API documentation."""
    return HTMLResponse(
        content="<h1>Backend Generation Platform</h1>"
                "<p>Visit <a href='/docs'>/docs</a> for the API documentation.</p>"
    )


# ---------------------------------------------------------------------------
# Protected endpoints — generation
# ---------------------------------------------------------------------------

@app.post(
    "/generate",
    tags=["Generation"],
    response_model=GenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_backend(
    spec: BackendSpec,
    current_user: PlatformUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accept a validated backend specification and generate a project.
    Creates a project record with persisted artifacts.
    """
    try:
        validation = review_spec(spec)
        if not validation.valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"errors": validation.errors, "warnings": validation.warnings},
            )

        files = generate_project_files(spec)

        # Generate report
        report_md = generate_report(
            prompt=None,
            spec=spec,
            validation=validation,
        )
        files["PROJECT_REPORT.md"] = report_md

        zip_path = assemble_project(project_name=spec.project_name, files=files)

        # Create project record
        project = Project(
            user_id=current_user.id,
            project_name=spec.project_name,
            status=ProjectStatus.COMPLETED,
            spec_json=spec.model_dump_json(indent=2),
            validation_json=json.dumps({
                "valid": validation.valid,
                "errors": validation.errors,
                "warnings": validation.warnings,
            }, indent=2),
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        # Move ZIP to user storage
        relative_path = storage.save_project_zip(
            current_user.id, project.id, zip_path,
        )
        project.zip_path = relative_path
        db.commit()
        db.refresh(project)

        return GenerateResponse(
            project_id=project.id,
            project_name=spec.project_name,
            status=project.status.value,
            download_url=f"/projects/{project.id}/download",
            warnings=validation.warnings,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}",
        )


@app.post(
    "/generate-from-prompt",
    tags=["Generation"],
    response_model=GenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_from_prompt(
    request: PromptRequest,
    current_user: PlatformUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accept a natural language prompt and generate a complete backend project.
    All intermediate artifacts are persisted. A default Thread is auto-created
    so the project has at least one conversation thread immediately.
    """
    try:
        # Retrieve RAG context from user's uploaded documents
        rag_context = retrieve_context(db, current_user.id, request.prompt)

        result = await run_pipeline(
            request.prompt,
            user_id=current_user.id,
            db=db,
            model_id=request.model,
            skip_verify=request.skip_verify,
            context=rag_context,
        )

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "project_id": str(result.project_id),
                },
            )

        # Auto-create a default Thread so the sidebar has something to show
        project_name = result.spec.project_name if result.spec else "unknown"
        default_thread = Thread(
            project_id=result.project_id,
            title=f"Initial build – {project_name}"
        )
        db.add(default_thread)
        # Persist the original user prompt as the first message
        user_msg = Message(thread_id=default_thread.id, role="user", content=request.prompt)
        db.add(user_msg)
        agent_reply = Message(
            thread_id=default_thread.id,
            role="agent",
            content=f"Project **{project_name}** generated successfully. Your backend is ready to download."
        )
        db.add(agent_reply)
        db.commit()

        return GenerateResponse(
            project_id=result.project_id,
            project_name=project_name,
            status="completed",
            content=f"Project **{project_name}** generated successfully. Your backend is ready to download.",
            thread_id=default_thread.id,
            download_url=f"/projects/{result.project_id}/download",
            warnings=result.warnings,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Protected endpoints — project management
# ---------------------------------------------------------------------------

@app.get(
    "/projects",
    tags=["Projects"],
    response_model=list[ProjectSummary],
)
def list_projects(
    current_user: PlatformUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all projects belonging to the current user."""
    projects = (
        db.query(Project)
        .filter(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return [
        ProjectSummary(
            id=p.id,
            project_name=p.project_name,
            prompt=p.prompt,
            status=p.status.value,
            model_used=p.model_used,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in projects
    ]


@app.get(
    "/projects/{project_id}",
    tags=["Projects"],
    response_model=ProjectDetail,
)
def get_project(
    project_id: uuid.UUID,
    current_user: PlatformUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full project detail with all artifacts."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return ProjectDetail(
        id=project.id,
        project_name=project.project_name,
        prompt=project.prompt,
        status=project.status.value,
        model_used=project.model_used,
        spec=json.loads(project.spec_json) if project.spec_json else None,
        validation=json.loads(project.validation_json) if project.validation_json else None,
        verification=json.loads(project.verification_json) if project.verification_json else None,
        download_url=f"/projects/{project.id}/download" if project.zip_path else None,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


@app.get(
    "/projects/{project_id}/download",
    tags=["Projects"],
)
def download_project(
    project_id: uuid.UUID,
    current_user: PlatformUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download the generated project ZIP file."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if not project.zip_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ZIP file available for this project",
        )

    zip_path = storage.get_project_zip_path(current_user.id, project.id)
    if not zip_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ZIP file not found on disk",
        )

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"{project.project_name}.zip",
    )


@app.delete(
    "/projects/{project_id}",
    tags=["Projects"],
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_project(
    project_id: uuid.UUID,
    current_user: PlatformUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a project and all its files."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Delete files first
    storage.delete_project_files(current_user.id, project.id)

    # Delete DB record
    db.delete(project)
    db.commit()


# ---------------------------------------------------------------------------
# Thread & Memory endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/projects/{project_id}/threads",
    tags=["Threads"],
    response_model=list[ThreadSummary],
)
def list_threads(
    project_id: uuid.UUID,
    current_user: PlatformUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all threads for a specific project."""
    project = db.query(Project).filter(
        Project.id == project_id, Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    threads = (
        db.query(Thread)
        .filter(Thread.project_id == project.id)
        .order_by(Thread.created_at.desc())
        .all()
    )
    return [
        ThreadSummary(
            id=t.id, project_id=t.project_id, title=t.title,
            created_at=t.created_at.isoformat(), updated_at=t.updated_at.isoformat()
        ) for t in threads
    ]


@app.post(
    "/projects/{project_id}/threads",
    tags=["Threads"],
    response_model=ThreadSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_thread(
    project_id: uuid.UUID,
    current_user: PlatformUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new thread within a project."""
    project = db.query(Project).filter(
        Project.id == project_id, Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    thread_count = db.query(Thread).filter(Thread.project_id == project.id).count()
    thread = Thread(project_id=project.id, title=f"Conversation {thread_count + 1}")
    db.add(thread)
    db.commit()
    db.refresh(thread)

    return ThreadSummary(
        id=thread.id, project_id=thread.project_id, title=thread.title,
        created_at=thread.created_at.isoformat(), updated_at=thread.updated_at.isoformat()
    )


@app.get(
    "/projects/{project_id}/threads/{thread_id}",
    tags=["Threads"],
    response_model=ThreadDetail,
)
def get_thread(
    project_id: uuid.UUID,
    thread_id: uuid.UUID,
    current_user: PlatformUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the full message history of a thread."""
    project = db.query(Project).filter(
        Project.id == project_id, Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    thread = db.query(Thread).filter(
        Thread.id == thread_id, Thread.project_id == project.id
    ).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    messages = (
        db.query(Message)
        .filter(Message.thread_id == thread.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return ThreadDetail(
        id=thread.id, project_id=thread.project_id, title=thread.title,
        created_at=thread.created_at.isoformat(), updated_at=thread.updated_at.isoformat(),
        messages=[
            MessageSchema(id=m.id, role=m.role, content=m.content, created_at=m.created_at.isoformat())
            for m in messages
        ]
    )


@app.post(
    "/projects/{project_id}/threads/{thread_id}/chat",
    tags=["Generation", "Threads"],
    response_model=GenerateResponse,
)
async def chat_in_thread(
    project_id: uuid.UUID,
    thread_id: uuid.UUID,
    request: ChatRequest,
    current_user: PlatformUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send a message in a thread. Past messages feed into the LLM as RAG context,
    then the generation pipeline runs and stores the agent reply.
    """
    project = db.query(Project).filter(
        Project.id == project_id, Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    thread = db.query(Thread).filter(
        Thread.id == thread_id, Thread.project_id == project.id
    ).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Persist the incoming user message
    user_msg = Message(thread_id=thread.id, role="user", content=request.message)
    db.add(user_msg)
    db.commit()

    # Load full message history as context
    history = (
        db.query(Message)
        .filter(Message.thread_id == thread.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    # Exclude the just-saved message for history context (we want prior messages only)
    prior_history = [{"role": m.role, "content": m.content} for m in history[:-1]]

    # --- Intent classification ---
    has_existing_artifact = bool(project.zip_path)
    intent = classify_intent(
        prompt=request.message,
        has_existing_project=has_existing_artifact,
        message_history=prior_history,
    )

    try:
        # ── RETRIEVE: just return the existing project, no re-generation ──
        if intent == Intent.RETRIEVE:
            reply_content = (
                f"Here is your existing **{project.project_name}** project. "
                f"You can download it below."
            )
            agent_msg = Message(thread_id=thread.id, role="agent", content=reply_content)
            db.add(agent_msg)
            db.commit()
            return GenerateResponse(
                project_id=project.id,
                project_name=project.project_name,
                status="completed",
                content=reply_content,
                download_url=f"/projects/{project.id}/download" if project.zip_path else None,
                warnings=None,
            )

        # ── REFINE or GENERATE: run the pipeline ──
        # For REFINE, pass full history so LLM can evolve the spec.
        # For GENERATE, pass limited history (last few messages only) to avoid noise.
        messages_for_llm = prior_history if intent == Intent.REFINE else prior_history[-3:]

        rag_context = retrieve_context(db, current_user.id, request.message)
        result = await run_pipeline(
            request.message,
            user_id=current_user.id,
            db=db,
            context=rag_context,
            messages=messages_for_llm,
            project_id=project.id if intent == Intent.REFINE else None,
        )

        if not result.success:
            err_reply = Message(thread_id=thread.id, role="agent",
                                content=f"Generation failed: {result.errors}")
            db.add(err_reply)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"errors": result.errors, "warnings": result.warnings,
                        "project_id": str(project.id)}
            )

        final_project_name = result.spec.project_name if result.spec else project.project_name
        action_word = "refined" if intent == Intent.REFINE else "generated"
        success_content = (
            f"Successfully {action_word} **{final_project_name}**. "
            f"Your backend is ready to download."
        )
        agent_msg = Message(thread_id=thread.id, role="agent", content=success_content)
        db.add(agent_msg)

        # Auto-name the thread on first generation
        if len(history) <= 1:
            thread.title = final_project_name

        db.commit()

        return GenerateResponse(
            project_id=project.id,
            project_name=final_project_name,
            status="completed",
            content=success_content,
            download_url=f"/projects/{project.id}/download",
            warnings=result.warnings,
        )

    except HTTPException:
        raise
    except Exception as e:
        err_reply = Message(thread_id=thread.id, role="agent",
                            content=f"An error occurred: {str(e)}")
        db.add(err_reply)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.post(
    "/projects/{project_id}/verify-report",
    tags=["Projects"],
    status_code=status.HTTP_200_OK,
)
def submit_verification_report(
    project_id: uuid.UUID,
    report: VerificationReportRequest,
    current_user: PlatformUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Called by the Electron App to report the results of local Docker verification tests.
    """
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Update verification artifacts and status
    new_status = ProjectStatus.COMPLETED if report.passed else ProjectStatus.FAILED
    project.status = new_status
    project.verification_json = report.model_dump_json(indent=2)
    db.commit()

    return {"message": "Verification report recorded successfully.", "status": new_status.value}


@app.post(
    "/projects/{project_id}/fix",
    tags=["Projects"],
    response_model=GenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def request_auto_fix(
    project_id: uuid.UUID,
    fix_req: AutoFixRequest,
    current_user: PlatformUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Called by the Electron App if local verification fails and the user requests an AI fix.
    """
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.status != ProjectStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auto-fix can only be requested for failed projects.",
        )

    # Set project back to generating
    project.status = ProjectStatus.GENERATING
    db.commit()

    # NOTE: In Phase 1, we stub this out. The Electron auto-fix loop
    # will call this endpoint, but for now we simply invoke the AutoFix placeholder.
    from backend.agents.auto_fix import run_auto_fix_pipeline
    
    result = await run_auto_fix_pipeline(
        project_id=project.id,
        user_id=current_user.id,
        db=db,
        fix_request=fix_req
    )

    if not result.success:
        project.status = ProjectStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": result.errors, "warnings": result.warnings},
        )

    return GenerateResponse(
        project_id=project.id,
        project_name=project.project_name,
        status="awaiting_verification",  # After a fix, back to verification testing layer
        download_url=f"/projects/{project.id}/download",
        warnings=result.warnings,
    )


# ---------------------------------------------------------------------------
# Protected endpoints — document management (RAG)
# ---------------------------------------------------------------------------

class DocumentSummary(BaseModel):
    id: uuid.UUID
    filename: str
    created_at: str


@app.post(
    "/documents",
    tags=["Documents"],
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: PlatformUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a document for RAG context.
    Supported formats: .txt, .md, .json, .csv, .pdf (max 5MB).
    """
    try:
        content = await file.read()
        text_content = extract_text(file.filename or "unknown.txt", content)

        if not text_content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document is empty or could not be parsed",
            )

        doc = store_document(
            db=db,
            user_id=current_user.id,
            filename=file.filename or "unknown.txt",
            text_content=text_content,
        )

        return {
            "id": doc.id,
            "filename": doc.filename,
            "message": "Document uploaded and indexed for RAG",
        }

    except UnsupportedFileError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except FileTooLargeError as e:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}",
        )


@app.get("/documents", tags=["Documents"], response_model=list[DocumentSummary])
def list_documents(
    current_user: PlatformUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all documents uploaded by the current user."""
    docs = db.query(Document).filter(
        Document.user_id == current_user.id,
    ).order_by(Document.created_at.desc()).all()

    return [
        DocumentSummary(
            id=d.id,
            filename=d.filename,
            created_at=d.created_at.isoformat(),
        )
        for d in docs
    ]


@app.delete(
    "/documents/{document_id}",
    tags=["Documents"],
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_document(
    document_id: uuid.UUID,
    current_user: PlatformUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document and all its embedded chunks."""
    deleted = delete_document(db, current_user.id, document_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
