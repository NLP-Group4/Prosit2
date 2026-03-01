"""
Sandbox deployment endpoint.

Writes generated code files + dependencies to a shared Docker volume,
then triggers the sandbox-runner container to install deps and start uvicorn.
"""
import logging
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.agent.artifact_store import load_code_bundle
from app.api.deps import CurrentUser, get_db
from app.models import Project, ArtifactRecord, GenerationRun

logger = logging.getLogger(__name__)
router = APIRouter()

SANDBOX_ROOT = Path("/sandbox")


class SandboxStatus(BaseModel):
    status: str
    message: str
    swagger_url: str | None = None


def _get_latest_code(session: Session, project_id: uuid.UUID) -> dict | None:
    """Find the latest reviewer or implementer artifact for a project."""
    # Get the latest run for this project
    run = (
        session.query(GenerationRun)
        .filter(GenerationRun.project_id == project_id)
        .order_by(GenerationRun.created_at.desc())
        .first()
    )
    if not run:
        return None

    # Prefer the reviewer's final_code, fall back to implementer
    artifacts = (
        session.query(ArtifactRecord)
        .filter(ArtifactRecord.run_id == run.id)
        .all()
    )

    reviewer_artifact = None
    implementer_artifact = None
    for a in artifacts:
        if a.stage.startswith("reviewer_pass"):
            reviewer_artifact = a
        elif a.stage == "implementer":
            implementer_artifact = a

    if reviewer_artifact and reviewer_artifact.content.get("final_code"):
        return {
            "files": reviewer_artifact.content["final_code"],
            "dependencies": implementer_artifact.content.get("dependencies", []) if implementer_artifact else [],
        }
    if reviewer_artifact and reviewer_artifact.content.get("bundle_ref"):
        bundle = load_code_bundle(str(reviewer_artifact.content["bundle_ref"]))
        if bundle and bundle.get("files"):
            return {
                "files": bundle.get("files", []),
                "dependencies": bundle.get("dependencies")
                or reviewer_artifact.content.get("dependencies", [])
                or (implementer_artifact.content.get("dependencies", []) if implementer_artifact else [])
                or [],
            }
    elif implementer_artifact:
        if implementer_artifact.content.get("bundle_ref"):
            bundle = load_code_bundle(str(implementer_artifact.content["bundle_ref"]))
            if bundle and bundle.get("files"):
                return {
                    "files": bundle.get("files", []),
                    "dependencies": bundle.get("dependencies")
                    or implementer_artifact.content.get("dependencies", [])
                    or [],
                }
        return implementer_artifact.content
    return None


import re as _re

def _auto_patch_content(filepath: str, content: str) -> str:
    """Apply auto-patches to fix common LLM code-generation mistakes."""
    patched = content

    # 1. Pydantic v1 'regex' kwarg → v2 'pattern' kwarg
    patched = patched.replace("regex=", "pattern=")

    # 2. Fix get_db().bind → engine
    patched = patched.replace("from .database import get_db", "from .database import get_db, engine")
    patched = patched.replace("bind=get_db().bind", "bind=engine")

    # 3. Fix recursive get_db shadowing in dependencies.py
    basename = filepath.rsplit("/", 1)[-1] if "/" in filepath else filepath
    if basename == "dependencies.py" and "def get_db" in patched:
        if _re.search(r"from\s+\S+\s+import\s+.*get_db", patched) and \
           _re.search(r"def\s+get_db\s*\(", patched):
            patched = _re.sub(
                r"def\s+get_db\s*\([^)]*\)[^:]*:\s*\n\s*return\s+get_db\(\)",
                "# get_db is re-exported from database module (auto-patched)",
                patched,
            )
            if "# get_db is re-exported" in patched:
                logger.info(f"Auto-patched recursive get_db in {filepath}")

    # 4. Fix Pydantic v1 validator → v2 field_validator
    patched = patched.replace("from pydantic import validator", "from pydantic import field_validator")

    # 5. Ensure any function containing 'await' IS marked async.
    #    LLMs sometimes generate 'def foo(): ... await bar()' which is a SyntaxError.
    patched = _re.sub(
        r"^(\s*)def\s+(\w+)\s*\(([^)]*)\)([^:]*:)",
        lambda m: (
            f"{m.group(1)}async def {m.group(2)}({m.group(3)}){m.group(4)}"
            if "await " in _get_function_body(patched, m.start())
            else m.group(0)
        ),
        patched,
        flags=_re.MULTILINE,
    )

    # 6. Remove error-swallowing try/except blocks that silently return None.
    #    Pattern:  except Exception as e: ... return None
    #    This hides real DB errors and causes ResponseValidationError when
    #    a route tries to serialize None as a response model.
    patched = _re.sub(
        r"    except Exception as e:\s*\n"
        r"        print\(f\"Error[^\"]*: \{e\}\"\)\s*\n"
        r"        (?:db\.rollback\(\)\s*\n\s*)?"
        r"        return None",
        "    except Exception:\n"
        "        db.rollback()\n"
        "        raise",
        patched,
    )

    # 7. Ensure create_db() is called on startup in main.py if it exists.
    #    LLMs often define create_db in database.py but forget to call it.
    if basename == "main.py" and "create_db" not in patched:
        if "app = FastAPI" in patched:
            # We inject a defensive import inside the startup event so it doesn't 
            # crash the whole app if database.py doesn't have create_db.
            startup_block = """
@app.on_event('startup')
def on_startup():
    try:
        from app.database import create_db
        create_db()
    except ImportError:
        pass
"""
            patched += startup_block
            logger.info(f"Auto-patched: injected defensive create_db() startup in {filepath}")

    # 8. Fix UnmappedInstanceError: LLMs pass schema objects (e.g. TodoCreate)
    #    directly to db.add() instead of converting to the ORM model first.
    #    Inject a runtime conversion before every db.add(var) call.
    patched = _re.sub(
        r"^(\s+)(db\.add\()(\w+)(\))",
        r"""\1# Auto-patch: convert Pydantic schema to ORM model if needed
\1if hasattr(\3, 'model_dump') and not hasattr(\3, '__tablename__'):
\1    import app.models as _models
\1    _cls_name = type(\3).__name__.replace('Create', '').replace('Update', '').replace('Base', '')
\1    _cls = getattr(_models, _cls_name, None)
\1    if _cls and hasattr(_cls, '__tablename__'):
\1        \3 = _cls(**\3.model_dump())
\1\2\3\4""",
        patched,
        flags=_re.MULTILINE,
    )
    # 9. Fix async SQLAlchemy → sync for sandbox reliability.
    #    LLMs often generate async database code (create_async_engine, AsyncSession)
    #    which is overkill for simple apps and causes driver issues in the sandbox.
    #    Convert to synchronous SQLite for simplicity and reliability.
    if "create_async_engine" in patched:
        patched = patched.replace("create_async_engine", "create_engine")
        patched = patched.replace(
            "from sqlalchemy.ext.asyncio import create_async_engine",
            "from sqlalchemy import create_engine",
        )
        patched = patched.replace(
            "from sqlmodel.ext.asyncio.session import AsyncSession",
            "from sqlmodel import Session",
        )
        # Clean up aiosqlite dialect if present — plain sqlite:/// works with sync engine
        patched = patched.replace("sqlite+aiosqlite:///", "sqlite:///")
        logger.info(f"Auto-patched: create_async_engine → create_engine in {filepath}")

    if "AsyncSession" in patched:
        patched = patched.replace("AsyncSession", "Session")
        patched = patched.replace(
            "from sqlalchemy.ext.asyncio import AsyncSession",
            "from sqlmodel import Session",
        )
        logger.info(f"Auto-patched: AsyncSession → Session in {filepath}")

    # Convert async_sessionmaker to sessionmaker for sync
    if "async_sessionmaker" in patched:
        patched = patched.replace("async_sessionmaker", "sessionmaker")
        patched = patched.replace(
            "from sqlalchemy.ext.asyncio import async_sessionmaker",
            "from sqlalchemy.orm import sessionmaker",
        )
        logger.info(f"Auto-patched: async_sessionmaker → sessionmaker in {filepath}")

    return patched


def _get_function_body(content: str, match_start: int) -> str:
    """Extract the body of a function starting at match_start position."""
    lines = content[match_start:].split("\n")
    if not lines:
        return ""
    # Get indent of the def line
    def_line = lines[0]
    def_indent = len(def_line) - len(def_line.lstrip())
    body_lines = []
    for line in lines[1:]:
        if line.strip() == "":
            body_lines.append(line)
            continue
        line_indent = len(line) - len(line.lstrip())
        if line_indent <= def_indent and line.strip():
            break
        body_lines.append(line)
    return "\n".join(body_lines)


@router.post("/deploy/{project_id}", response_model=SandboxStatus)
def deploy_to_sandbox(
    project_id: uuid.UUID,
    session: Session = Depends(get_db),
    current_user: CurrentUser = None,
) -> Any:
    """Deploy generated code to the sandbox runner container."""

    # 1. Verify project ownership
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # 2. Get the latest generated code
    code_data = _get_latest_code(session, project_id)
    if not code_data or not code_data.get("files"):
        raise HTTPException(
            status_code=400,
            detail="No generated code found for this project. Run the pipeline first.",
        )

    files = code_data["files"]
    dependencies = code_data.get("dependencies", [])

    # 3. Write files to sandbox volume
    sandbox_dir = SANDBOX_ROOT / str(project_id)
    if sandbox_dir.exists():
        shutil.rmtree(sandbox_dir)
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        file_path = sandbox_dir / f["path"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = _auto_patch_content(f["path"], f["content"])
        
        file_path.write_text(content, encoding="utf-8")
        logger.info(f"Wrote sandbox file: {file_path}")

    # 4. Write requirements.txt
    # Always ensure fastapi and uvicorn are present
    base_deps = {"fastapi", "uvicorn[standard]", "sqlmodel"}
    all_deps = base_deps | set(dependencies)
    reqs_path = sandbox_dir / "requirements.txt"
    reqs_path.write_text("\n".join(sorted(all_deps)), encoding="utf-8")

    # 5. Write a launcher script
    launcher = sandbox_dir / "start.sh"
    launcher.write_text(
        f"""#!/bin/bash
set -e
cd /sandbox/{project_id}
pip install -q -r requirements.txt 2>&1

# Auto-fix common Pydantic v1 / syntax errors before starting
ruff check . --select E,F,UP --ignore E501 --fix --quiet 2>&1 || true

# Kill previous uvicorn if it exists
if [ -f /sandbox/uvicorn.pid ]; then
    kill -9 $(cat /sandbox/uvicorn.pid) 2>/dev/null || true
    rm /sandbox/uvicorn.pid
fi
sleep 1

# Try to find the main app module
if [ -f "app/main.py" ]; then
    MODULE="app.main:app"
elif [ -f "main.py" ]; then
    MODULE="main:app"
else
    # Find any file that creates a FastAPI app
    MODULE=$(grep -rl "FastAPI()" . --include="*.py" | head -1 | sed 's|^./||;s|/|.|g;s|.py$||'):app
fi

# Start uvicorn in background and save its PID
uvicorn $MODULE --host 0.0.0.0 --port 9000 > /sandbox/uvicorn.log 2>&1 &
echo $! > /sandbox/uvicorn.pid
""",
        encoding="utf-8",
    )
    launcher.chmod(0o755)

    # 6. Execute the launcher via docker exec on the sandbox-runner container
    try:
        result = subprocess.run(
            [
                "docker", "exec", "-d",
                "craftlive-sandbox-runner-1",
                "bash", f"/sandbox/{project_id}/start.sh",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error(f"Sandbox start failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start sandbox: {result.stderr}",
            )
    except FileNotFoundError:
        # Docker CLI not available — try writing a signal file instead
        logger.warning("docker CLI not found, writing signal file for sandbox runner")
        signal = sandbox_dir / ".deploy"
        signal.write_text("start", encoding="utf-8")

    return SandboxStatus(
        status="deployed",
        message=f"API deployed to sandbox. {len(files)} files written.",
        swagger_url="http://localhost:9000/docs",
    )


def _chat_thread_project_marker(thread_id: str) -> str:
    """Must match the marker format used in generate.py."""
    return f"[chat-thread:{thread_id}]"


@router.post("/deploy-by-thread/{thread_id}", response_model=SandboxStatus)
def deploy_to_sandbox_by_thread(
    thread_id: str,
    session: Session = Depends(get_db),
) -> Any:
    """
    Deploy generated code to the sandbox using a chat thread ID.

    Resolves the thread -> project mapping via the marker stored in
    Project.description by generate.py, then delegates to the standard
    deploy flow.
    """
    from sqlmodel import select

    marker = _chat_thread_project_marker(thread_id)
    project = session.exec(
        select(Project).where(Project.description == marker)
    ).first()

    if not project:
        raise HTTPException(
            status_code=404,
            detail="No project found for this thread. Run the build pipeline first.",
        )

    code_data = _get_latest_code(session, project.id)
    if not code_data or not code_data.get("files"):
        raise HTTPException(
            status_code=400,
            detail="No generated code found for this thread. Run the pipeline first.",
        )

    files = code_data["files"]
    dependencies = code_data.get("dependencies", [])

    # Write files to sandbox volume
    sandbox_dir = SANDBOX_ROOT / str(project.id)
    if sandbox_dir.exists():
        shutil.rmtree(sandbox_dir)
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        file_path = sandbox_dir / f["path"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        content = _auto_patch_content(f["path"], f["content"])
        file_path.write_text(content, encoding="utf-8")
        logger.info(f"Wrote sandbox file: {file_path}")

    # Write requirements.txt
    base_deps = {"fastapi", "uvicorn[standard]", "sqlmodel"}
    all_deps = base_deps | set(dependencies)
    reqs_path = sandbox_dir / "requirements.txt"
    reqs_path.write_text("\n".join(sorted(all_deps)), encoding="utf-8")

    # Write launcher script
    launcher = sandbox_dir / "start.sh"
    launcher.write_text(
        f"""#!/bin/bash
set -e
cd /sandbox/{project.id}
pip install -q -r requirements.txt 2>&1

# Auto-fix common Pydantic v1 / syntax errors before starting
ruff check . --select E,F,UP --ignore E501 --fix --quiet 2>&1 || true

# Kill previous uvicorn if it exists
if [ -f /sandbox/uvicorn.pid ]; then
    kill -9 $(cat /sandbox/uvicorn.pid) 2>/dev/null || true
    rm /sandbox/uvicorn.pid
fi
sleep 1

# Try to find the main app module
if [ -f "app/main.py" ]; then
    MODULE="app.main:app"
elif [ -f "main.py" ]; then
    MODULE="main:app"
else
    MODULE=$(grep -rl "FastAPI()" . --include="*.py" | head -1 | sed 's|^./||;s|/|.|g;s|.py$||'):app
fi

# Start uvicorn in background and save its PID
uvicorn $MODULE --host 0.0.0.0 --port 9000 > /sandbox/uvicorn.log 2>&1 &
echo $! > /sandbox/uvicorn.pid
""",
        encoding="utf-8",
    )
    launcher.chmod(0o755)

    # Execute the launcher via docker exec
    try:
        result = subprocess.run(
            [
                "docker", "exec", "-d",
                "craftlive-sandbox-runner-1",
                "bash", f"/sandbox/{project.id}/start.sh",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error(f"Sandbox start failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start sandbox: {result.stderr}",
            )
    except FileNotFoundError:
        logger.warning("docker CLI not found, writing signal file for sandbox runner")
        signal = sandbox_dir / ".deploy"
        signal.write_text("start", encoding="utf-8")

    return SandboxStatus(
        status="deployed",
        message=f"API deployed to sandbox. {len(files)} files written.",
        swagger_url="http://localhost:9000/docs",
    )


@router.get("/status", response_model=SandboxStatus)
def get_sandbox_status() -> Any:
    """Check if the sandbox runner is serving an API."""
    import urllib.request

    try:
        req = urllib.request.urlopen("http://sandbox-runner:9000/docs", timeout=3)
        return SandboxStatus(
            status="running",
            message="Sandbox API is live.",
            swagger_url="http://localhost:9000/docs",
        )
    except Exception:
        return SandboxStatus(
            status="stopped",
            message="Sandbox is not currently running.",
        )
