"""
E2E-style coverage for the Cloud/Electron integration endpoints.

These tests run against FastAPI TestClient and mocked auto-fix behavior so they
remain deterministic in CI and sandboxed environments.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from backend.app.platform_db import Project, ProjectStatus
from backend.agents.auto_fix import AutoFixResult


def _valid_spec(project_name: str) -> dict:
    return {
        "project_name": project_name,
        "description": "E2E test project",
        "spec_version": "1.0",
        "database": {"type": "postgres", "version": "15"},
        "auth": {"enabled": False, "type": "jwt", "access_token_expiry_minutes": 30},
        "entities": [
            {
                "name": "Task",
                "table_name": "tasks",
                "fields": [
                    {"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True},
                    {"name": "title", "type": "string", "nullable": False},
                ],
                "crud": True,
            }
        ],
    }


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_models(client):
    r = client.get("/models")
    assert r.status_code == 200
    data = r.json()
    assert "models" in data
    assert len(data["models"]) >= 1


def test_verify_report_endpoint(client, auth_headers):
    gen = client.post("/generate", headers=auth_headers, json=_valid_spec("verify-project"))
    assert gen.status_code == 201
    project_id = gen.json()["project_id"]

    report = {
        "passed": False,
        "elapsed_ms": 1234,
        "results": [
            {
                "test_name": "GET /health",
                "endpoint": "/health",
                "method": "GET",
                "passed": False,
                "status_code": 500,
                "error_message": "Simulated failure",
            }
        ],
    }

    res = client.post(
        f"/projects/{project_id}/verify-report",
        headers=auth_headers,
        json=report,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "failed"


def test_fix_endpoint(client, auth_headers, db_session, test_user):
    user, _ = test_user
    project = Project(
        user_id=user.id,
        project_name="fix-project",
        status=ProjectStatus.FAILED,
        spec_json='{"project_name":"fix-project","description":"","spec_version":"1.0","database":{"type":"postgres","version":"15"},"auth":{"enabled":false,"type":"jwt","access_token_expiry_minutes":30},"entities":[{"name":"Task","table_name":"tasks","fields":[{"name":"id","type":"uuid","primary_key":true,"nullable":false,"unique":true}],"crud":true}]}',
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    fix_request = {
        "attempt_number": 1,
        "failed_tests": [
            {
                "method": "GET",
                "endpoint": "/tasks",
                "error_message": "Simulated failure",
            }
        ],
    }

    with patch("backend.agents.auto_fix.run_auto_fix_pipeline", new_callable=AsyncMock) as mock_fix:
        mock_fix.return_value = AutoFixResult(success=True, warnings=["Patched import"])
        res = client.post(
            f"/projects/{project.id}/fix",
            headers=auth_headers,
            json=fix_request,
        )

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "awaiting_verification"
    assert "Patched import" in body.get("warnings", [])
