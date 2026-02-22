"""
Tests for API endpoints using FastAPI TestClient.

These tests validate the HTTP interface: status codes, response formats,
authentication, and security boundaries — without making real LLM calls.
"""

import json
import uuid
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.spec_schema import BackendSpec
from agents.orchestrator import GenerationResult


VALID_SPEC = {
    "project_name": "test-api",
    "description": "Test",
    "spec_version": "1.0",
    "database": {"type": "postgres", "version": "15"},
    "auth": {"enabled": False, "type": "jwt", "access_token_expiry_minutes": 30},
    "entities": [
        {
            "name": "Item",
            "table_name": "items",
            "fields": [
                {"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True},
                {"name": "title", "type": "string", "nullable": False},
            ],
            "crud": True,
        }
    ],
}


# ---------------------------------------------------------------------------
# Public endpoints (no auth required)
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestModelsEndpoint:
    def test_models_returns_list(self, client):
        r = client.get("/models")
        assert r.status_code == 200
        data = r.json()
        assert "models" in data
        assert "default" in data
        assert len(data["models"]) >= 3


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

class TestAuthEndpoints:
    def test_register_new_user(self, client):
        r = client.post("/auth/register", json={
            "email": "new@example.com",
            "password": "securepass123",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["email"] == "new@example.com"
        assert "id" in data

    def test_register_duplicate_email(self, client, test_user):
        r = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "anotherpass123",
        })
        assert r.status_code == 409

    def test_register_weak_password(self, client):
        r = client.post("/auth/register", json={
            "email": "weak@example.com",
            "password": "short",
        })
        assert r.status_code == 422

    def test_login_success(self, client, test_user):
        r = client.post("/auth/login", data={
            "username": "test@example.com",
            "password": "testpass123",
        })
        assert r.status_code == 200
        assert "access_token" in r.json()
        assert r.json()["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        r = client.post("/auth/login", data={
            "username": "test@example.com",
            "password": "wrongpass",
        })
        assert r.status_code == 401

    def test_login_nonexistent_user(self, client):
        r = client.post("/auth/login", data={
            "username": "nobody@example.com",
            "password": "pass123",
        })
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Protected endpoints — auth required
# ---------------------------------------------------------------------------

class TestAuthRequired:
    def test_generate_requires_auth(self, client):
        r = client.post("/generate", json=VALID_SPEC)
        assert r.status_code == 401

    def test_generate_from_prompt_requires_auth(self, client):
        r = client.post("/generate-from-prompt", json={"prompt": "test"})
        assert r.status_code == 401

    def test_projects_list_requires_auth(self, client):
        r = client.get("/projects")
        assert r.status_code == 401

    def test_project_detail_requires_auth(self, client):
        r = client.get(f"/projects/{uuid.uuid4()}")
        assert r.status_code == 401

    def test_project_download_requires_auth(self, client):
        r = client.get(f"/projects/{uuid.uuid4()}/download")
        assert r.status_code == 401

    def test_project_delete_requires_auth(self, client):
        r = client.delete(f"/projects/{uuid.uuid4()}")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# POST /generate (direct spec, authenticated)
# ---------------------------------------------------------------------------

class TestGenerateEndpoint:
    def test_valid_spec_returns_project(self, client, auth_headers):
        r = client.post("/generate", json=VALID_SPEC, headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert "project_id" in data
        assert data["project_name"] == "test-api"
        assert data["status"] == "completed"
        assert data["download_url"] is not None

    def test_invalid_spec_returns_422(self, client, auth_headers):
        r = client.post("/generate", json={
            "project_name": "bad-api",
            "entities": [],
        }, headers=auth_headers)
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /generate-from-prompt (authenticated)
# ---------------------------------------------------------------------------

class TestGenerateFromPrompt:
    def test_successful_generation(self, client, auth_headers, test_user, tmp_path):
        spec = BackendSpec(**VALID_SPEC)
        fake_zip = tmp_path / "test.zip"
        with zipfile.ZipFile(fake_zip, "w") as zf:
            zf.writestr("test/app/main.py", "# test")

        project_id = uuid.uuid4()
        mock_result = GenerationResult(
            success=True,
            project_id=project_id,
            zip_path=fake_zip,
            spec=spec,
            model_used="gemini-2.0-flash",
        )

        with patch("app.main.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
            mock_pipeline.return_value = mock_result
            r = client.post("/generate-from-prompt", json={
                "prompt": "Build a simple task API"
            }, headers=auth_headers)
            assert r.status_code == 201
            data = r.json()
            assert data["project_id"] == str(project_id)
            assert data["status"] == "completed"

    def test_pipeline_failure_returns_422(self, client, auth_headers):
        project_id = uuid.uuid4()
        mock_result = GenerationResult(
            success=False,
            project_id=project_id,
            errors=["Spec validation failed"],
            warnings=["Generic name"],
        )

        with patch("app.main.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
            mock_pipeline.return_value = mock_result
            r = client.post("/generate-from-prompt", json={
                "prompt": "Build a task API"
            }, headers=auth_headers)
            assert r.status_code == 422


# ---------------------------------------------------------------------------
# Project management (authenticated)
# ---------------------------------------------------------------------------

class TestProjectEndpoints:
    def test_list_projects_empty(self, client, auth_headers):
        r = client.get("/projects", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_list_projects_after_generate(self, client, auth_headers):
        # Generate a project first
        client.post("/generate", json=VALID_SPEC, headers=auth_headers)
        r = client.get("/projects", headers=auth_headers)
        assert r.status_code == 200
        projects = r.json()
        assert len(projects) == 1
        assert projects[0]["project_name"] == "test-api"

    def test_get_project_detail(self, client, auth_headers):
        # Generate then retrieve
        gen_r = client.post("/generate", json=VALID_SPEC, headers=auth_headers)
        project_id = gen_r.json()["project_id"]

        r = client.get(f"/projects/{project_id}", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["project_name"] == "test-api"
        assert data["spec"] is not None
        assert data["validation"] is not None

    def test_delete_project(self, client, auth_headers):
        gen_r = client.post("/generate", json=VALID_SPEC, headers=auth_headers)
        project_id = gen_r.json()["project_id"]

        r = client.delete(f"/projects/{project_id}", headers=auth_headers)
        assert r.status_code == 204

        # Verify it's gone
        r = client.get(f"/projects/{project_id}", headers=auth_headers)
        assert r.status_code == 404

    def test_nonexistent_project_returns_404(self, client, auth_headers):
        r = client.get(f"/projects/{uuid.uuid4()}", headers=auth_headers)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Security boundaries — cross-user access
# ---------------------------------------------------------------------------

class TestSecurityBoundaries:
    def test_user_cannot_see_others_projects(
        self, client, auth_headers, other_auth_headers,
    ):
        """User B should not be able to access User A's projects."""
        # User A generates a project
        gen_r = client.post("/generate", json=VALID_SPEC, headers=auth_headers)
        project_id = gen_r.json()["project_id"]

        # User B tries to access it
        r = client.get(f"/projects/{project_id}", headers=other_auth_headers)
        assert r.status_code == 404  # Not 403 — no info leakage

    def test_user_cannot_delete_others_projects(
        self, client, auth_headers, other_auth_headers,
    ):
        gen_r = client.post("/generate", json=VALID_SPEC, headers=auth_headers)
        project_id = gen_r.json()["project_id"]

        r = client.delete(f"/projects/{project_id}", headers=other_auth_headers)
        assert r.status_code == 404

    def test_user_cannot_download_others_projects(
        self, client, auth_headers, other_auth_headers,
    ):
        gen_r = client.post("/generate", json=VALID_SPEC, headers=auth_headers)
        project_id = gen_r.json()["project_id"]

        r = client.get(f"/projects/{project_id}/download", headers=other_auth_headers)
        assert r.status_code == 404

    def test_users_see_only_own_projects(
        self, client, auth_headers, other_auth_headers,
    ):
        """Each user's project list is isolated."""
        # Both users generate projects
        client.post("/generate", json=VALID_SPEC, headers=auth_headers)
        client.post("/generate", json=VALID_SPEC, headers=other_auth_headers)

        # User A sees only their project
        r = client.get("/projects", headers=auth_headers)
        assert len(r.json()) == 1

        # User B sees only their project
        r = client.get("/projects", headers=other_auth_headers)
        assert len(r.json()) == 1
