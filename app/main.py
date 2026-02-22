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
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.spec_schema import BackendSpec
from app.code_generator import generate_project_files
from app.project_assembler import assemble_project
from app.report_generator import generate_report
from app.platform_db import get_db, init_db, PlatformUser, Project, ProjectStatus, Document
from app.platform_auth import router as auth_router, get_current_user
from app import storage
from app.rag import store_document, retrieve_context, delete_document
from app.document_processor import (
    extract_text, UnsupportedFileError, FileTooLargeError,
)
from agents.orchestrator import run_pipeline, GenerationResult
from agents.model_registry import list_models, DEFAULT_MODEL
from agents.spec_review import review_spec

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

# Serve static assets
STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


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
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    return HTMLResponse(
        content="<h1>Backend Generation Platform</h1>"
                "<p>Visit <a href='/docs'>/docs</a> for the API.</p>"
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
    All intermediate artifacts are persisted.
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

        return GenerateResponse(
            project_id=result.project_id,
            project_name=result.spec.project_name if result.spec else "unknown",
            status="completed",
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
