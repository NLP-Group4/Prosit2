"""
Integration test — generates a project, builds it in Docker, and verifies
that the generated backend is fully functional (§16.2-5 & §18 deliverables).

Requires Docker to be running. Marked so it doesn't run in normal pytest:
    pytest tests/ -v -m "not integration"      # skip this
    pytest tests/test_integration.py -v -m integration   # run only this

Typical runtime: ~30-60 seconds.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
import zipfile

import pytest
import requests

from backend.app.spec_schema import BackendSpec
from backend.app.code_generator import generate_project_files
from backend.app.project_assembler import assemble_project


# ---------------------------------------------------------------------------
# Sample spec (1 entity, auth enabled → covers JWT + CRUD)
# ---------------------------------------------------------------------------

SAMPLE_SPEC_DICT = {
    "project_name": "integration-test",
    "description": "Integration test project",
    "database": {"type": "postgres", "version": "15"},
    "auth": {"enabled": True, "type": "jwt", "access_token_expiry_minutes": 30},
    "entities": [
        {
            "name": "Task",
            "table_name": "tasks",
            "fields": [
                {"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True},
                {"name": "title", "type": "string", "nullable": False},
                {"name": "done", "type": "boolean", "nullable": False},
            ],
            "crud": True,
        }
    ],
}

BASE_URL = "http://localhost:8000"
COMPOSE_TIMEOUT = 60  # seconds to wait for app to be healthy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wait_for_health(url: str, timeout: int = COMPOSE_TIMEOUT) -> bool:
    """Poll /health until it returns 200 or timeout is reached."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{url}/health", timeout=2)
            if r.status_code == 200:
                return True
        except requests.ConnectionError:
            pass
        time.sleep(2)
    return False


def _docker_available() -> bool:
    """Return True only if Docker daemon is reachable for this process."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def project_dir():
    """Generate the project, unzip, and yield the directory. Teardown afterwards."""
    from pathlib import Path
    spec = BackendSpec(**SAMPLE_SPEC_DICT)
    files = generate_project_files(spec)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        zip_path = assemble_project(
            project_name=spec.project_name,
            files=files,
            output_dir=tmp_path,
        )

        # Unzip
        extract_dir = tmp_path / "extracted"
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)

        project_root = extract_dir / spec.project_name
        yield str(project_root)


@pytest.fixture(scope="module")
def running_compose(project_dir):
    """Start docker compose, wait for health, yield, then tear down."""
    if not _docker_available():
        pytest.skip("Docker is unavailable or inaccessible in this environment")

    # Build & start
    result = subprocess.run(
        ["docker", "compose", "up", "-d", "--build"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"Docker Compose failed to start.\nStdout:\n{result.stdout}\nStderr:\n{result.stderr}")

    try:
        healthy = _wait_for_health(BASE_URL)
        if not healthy:
            # Dump logs for debugging
            logs = subprocess.run(
                ["docker", "compose", "logs"],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )
            pytest.fail(
                f"App did not become healthy within {COMPOSE_TIMEOUT}s.\n"
                f"Logs:\n{logs.stdout}\n{logs.stderr}"
            )
        yield BASE_URL
    finally:
        subprocess.run(
            ["docker", "compose", "down", "-v", "--remove-orphans"],
            cwd=project_dir,
            capture_output=True,
        )


@pytest.mark.integration
class TestDockerBuild:
    """§16.2 — Docker build test."""

    def test_project_dir_exists(self, project_dir):
        assert os.path.isdir(project_dir)
        assert os.path.isfile(os.path.join(project_dir, "docker-compose.yml"))
        assert os.path.isfile(os.path.join(project_dir, "Dockerfile"))


@pytest.mark.integration
class TestRunningBackend:
    """§16.3-5 — uvicorn, /docs, CRUD, JWT."""

    def test_health_endpoint(self, running_compose):
        r = requests.get(f"{running_compose}/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_swagger_ui_loads(self, running_compose):
        """§16.4 — /docs serves Swagger UI HTML."""
        r = requests.get(f"{running_compose}/docs")
        assert r.status_code == 200
        assert "swagger" in r.text.lower() or "openapi" in r.text.lower()

    def test_openapi_json(self, running_compose):
        r = requests.get(f"{running_compose}/openapi.json")
        assert r.status_code == 200
        data = r.json()
        assert "paths" in data

    def test_crud_cycle(self, running_compose):
        """§16.5 & §18 — Full CRUD cycle on /tasks."""
        # Register a user (auth enabled)
        reg = requests.post(f"{running_compose}/auth/register", json={
            "email": "test@example.com",
            "password": "testpass123",
        })
        assert reg.status_code == 201, f"Register failed: {reg.text}"

        # Login to get JWT (OAuth2 form-encoded)
        login = requests.post(f"{running_compose}/auth/login", data={
            "username": "test@example.com",
            "password": "testpass123",
            "grant_type": "password",
        })
        assert login.status_code == 200, f"Login failed: {login.text}"
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # CREATE
        create = requests.post(f"{running_compose}/tasks/", json={
            "title": "Test task",
            "done": False,
        }, headers=headers)
        assert create.status_code == 201, f"Create failed: {create.text}"
        task_id = create.json()["id"]

        # READ (list)
        read_all = requests.get(f"{running_compose}/tasks/", headers=headers)
        assert read_all.status_code == 200
        assert len(read_all.json()) >= 1

        # READ (single)
        read_one = requests.get(f"{running_compose}/tasks/{task_id}", headers=headers)
        assert read_one.status_code == 200
        assert read_one.json()["title"] == "Test task"

        # UPDATE
        update = requests.put(f"{running_compose}/tasks/{task_id}", json={
            "done": True,
        }, headers=headers)
        assert update.status_code == 200
        assert update.json()["done"] is True

        # DELETE
        delete = requests.delete(f"{running_compose}/tasks/{task_id}", headers=headers)
        assert delete.status_code == 204

        # Verify deleted
        verify = requests.get(f"{running_compose}/tasks/{task_id}", headers=headers)
        assert verify.status_code == 404
