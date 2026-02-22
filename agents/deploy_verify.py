"""
DeployVerifyAgent — Automated endpoint verification for generated backends.

After a backend is generated, this agent:
1. Unzips the project to a temp directory
2. Deploys it via docker compose (on a non-conflicting port)
3. Smoke-tests every endpoint: health, auth, full CRUD per entity
4. Tears down the Docker environment
5. Returns a structured VerificationResult

This ensures users receive a verified, working backend.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time
import uuid as uuid_mod
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests

from app.spec_schema import BackendSpec, FieldType

logger = logging.getLogger(__name__)

# Port used for verification — avoids conflict with the platform (8000)
VERIFY_PORT = 9123
HEALTH_TIMEOUT = 90  # seconds to wait for the app to become healthy
BASE_URL = f"http://localhost:{VERIFY_PORT}"


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class EndpointResult:
    """Result of testing a single endpoint."""
    method: str
    path: str
    expected_status: int
    actual_status: int | None = None
    passed: bool = False
    error: str | None = None


@dataclass
class VerificationResult:
    """Aggregated result of all endpoint tests."""
    passed: bool = False
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    results: list[EndpointResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None

    @property
    def summary(self) -> str:
        if self.skipped:
            return f"Verification skipped: {self.skip_reason}"
        return (
            f"Verification {'PASSED' if self.passed else 'FAILED'}: "
            f"{self.passed_tests}/{self.total_tests} tests passed"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_docker_available() -> bool:
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _generate_test_value(field_type: FieldType, field_name: str) -> object:
    """Generate a type-appropriate test value for a field."""
    match field_type:
        case FieldType.STRING:
            return f"test_{field_name}"
        case FieldType.TEXT:
            return f"Test text content for {field_name}"
        case FieldType.INTEGER:
            return 42
        case FieldType.FLOAT:
            return 3.14
        case FieldType.BOOLEAN:
            return False
        case FieldType.DATETIME:
            return datetime.now(timezone.utc).isoformat()
        case FieldType.UUID:
            return str(uuid_mod.uuid4())
        case _:
            return "test_value"


def _generate_update_value(field_type: FieldType, field_name: str) -> object:
    """Generate a different value for update testing."""
    match field_type:
        case FieldType.STRING:
            return f"updated_{field_name}"
        case FieldType.TEXT:
            return f"Updated text content for {field_name}"
        case FieldType.INTEGER:
            return 99
        case FieldType.FLOAT:
            return 6.28
        case FieldType.BOOLEAN:
            return True
        case FieldType.DATETIME:
            return datetime.now(timezone.utc).isoformat()
        case FieldType.UUID:
            return str(uuid_mod.uuid4())
        case _:
            return "updated_value"


def _build_create_payload(spec: BackendSpec, entity_idx: int) -> dict:
    """Build a JSON payload for creating an entity instance."""
    entity = spec.entities[entity_idx]
    payload = {}
    for f in entity.fields:
        if f.primary_key:
            continue  # Skip PK — auto-generated
        payload[f.name] = _generate_test_value(f.type, f.name)
    return payload


def _build_update_payload(spec: BackendSpec, entity_idx: int) -> dict:
    """Build a JSON payload for updating an entity instance (non-PK fields only)."""
    entity = spec.entities[entity_idx]
    payload = {}
    for f in entity.fields:
        if f.primary_key:
            continue
        payload[f.name] = _generate_update_value(f.type, f.name)
    return payload


def _wait_for_health(timeout: int = HEALTH_TIMEOUT) -> bool:
    """Poll /health until it returns 200 or timeout is reached."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=3)
            if r.status_code == 200:
                return True
        except requests.ConnectionError:
            pass
        time.sleep(2)
    return False


def _record(
    results: list[EndpointResult],
    method: str,
    path: str,
    expected: int,
    actual: int | None,
    error: str | None = None,
) -> EndpointResult:
    """Record a test result."""
    passed = actual == expected and error is None
    result = EndpointResult(
        method=method,
        path=path,
        expected_status=expected,
        actual_status=actual,
        passed=passed,
        error=error,
    )
    results.append(result)
    status = "✓" if passed else "✗"
    logger.info(f"  {status} {method} {path} → {actual} (expected {expected})")
    return result


# ---------------------------------------------------------------------------
# Main verification logic
# ---------------------------------------------------------------------------

def _write_compose_override(project_dir: str) -> None:
    """Write a docker-compose.override.yml to remap port to VERIFY_PORT."""
    override = (
        'services:\n'
        '  app:\n'
        '    ports:\n'
        f'      - "{VERIFY_PORT}:8000"\n'
    )
    override_path = os.path.join(project_dir, "docker-compose.override.yml")
    with open(override_path, "w") as f:
        f.write(override)


def verify_generated_backend(
    zip_path: Path,
    spec: BackendSpec,
) -> VerificationResult:
    """
    Deploy and smoke-test a generated backend.

    Args:
        zip_path: Path to the generated ZIP file.
        spec: The BackendSpec used to generate the project.

    Returns:
        VerificationResult with per-endpoint pass/fail details.
    """
    # Check Docker availability
    if not _is_docker_available():
        logger.warning("Docker not available — skipping verification")
        return VerificationResult(
            skipped=True,
            skip_reason="Docker is not available on this machine",
        )

    results: list[EndpointResult] = []
    errors: list[str] = []
    project_dir: str | None = None
    tmpdir: str | None = None
    compose_project = f"verify-{uuid_mod.uuid4().hex[:8]}"

    try:
        # 1. Unzip to temp directory
        tmpdir = tempfile.mkdtemp(prefix="verify_")
        logger.info(f"Step 5a: Extracting {zip_path.name} to temp directory...")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmpdir)

        # Find the project root (first directory in the zip)
        entries = os.listdir(tmpdir)
        if len(entries) == 1 and os.path.isdir(os.path.join(tmpdir, entries[0])):
            project_dir = os.path.join(tmpdir, entries[0])
        else:
            project_dir = tmpdir

        # 2. Write port override
        logger.info(f"Step 5b: Starting Docker containers on port {VERIFY_PORT}...")
        _write_compose_override(project_dir)

        # 3. Build and start with unique project name
        build_result = subprocess.run(
            ["docker", "compose", "-p", compose_project, "up", "-d", "--build"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if build_result.returncode != 0:
            errors.append(f"Docker build failed: {build_result.stderr}")
            return VerificationResult(
                passed=False,
                errors=errors,
            )

        # 4. Wait for health
        logger.info("Step 5c: Waiting for app to become healthy...")
        if not _wait_for_health():
            # Grab logs for diagnostics
            logs_result = subprocess.run(
                ["docker", "compose", "-p", compose_project, "logs", "--tail=50"],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )
            errors.append(
                f"App did not become healthy within {HEALTH_TIMEOUT}s. "
                f"Logs:\n{logs_result.stdout}\n{logs_result.stderr}"
            )
            return VerificationResult(
                passed=False,
                errors=errors,
            )

        # 5. Test health endpoint
        logger.info("Step 5d: Running smoke tests...")
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=5)
            _record(results, "GET", "/health", 200, r.status_code)
        except Exception as e:
            _record(results, "GET", "/health", 200, None, str(e))

        # 6. Test Swagger docs
        try:
            r = requests.get(f"{BASE_URL}/docs", timeout=5)
            _record(results, "GET", "/docs", 200, r.status_code)
        except Exception as e:
            _record(results, "GET", "/docs", 200, None, str(e))

        # 7. Auth flow (if enabled)
        auth_headers: dict[str, str] = {}
        if spec.auth.enabled:
            logger.info("  Testing auth endpoints...")

            # Register
            try:
                r = requests.post(
                    f"{BASE_URL}/auth/register",
                    json={"email": "verify@test.com", "password": "TestPass123!"},
                    timeout=10,
                )
                _record(results, "POST", "/auth/register", 201, r.status_code)
            except Exception as e:
                _record(results, "POST", "/auth/register", 201, None, str(e))

            # Login (OAuth2 form-encoded)
            try:
                r = requests.post(
                    f"{BASE_URL}/auth/login",
                    data={
                        "username": "verify@test.com",
                        "password": "TestPass123!",
                        "grant_type": "password",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10,
                )
                _record(results, "POST", "/auth/login", 200, r.status_code)
                if r.status_code == 200:
                    token = r.json().get("access_token")
                    if token:
                        auth_headers = {"Authorization": f"Bearer {token}"}
                    else:
                        errors.append("Login succeeded but no access_token in response")
            except Exception as e:
                _record(results, "POST", "/auth/login", 200, None, str(e))

        # 8. CRUD smoke tests for each entity
        for idx, entity in enumerate(spec.entities):
            if not entity.crud:
                continue

            # Skip User entity CRUD when auth is enabled —
            # user management is via /auth/register & /auth/login
            if spec.auth.enabled and entity.name == "User":
                logger.info(f"  Skipping CRUD for {entity.name} (handled by auth)")
                continue

            prefix = f"/{entity.table_name}"
            logger.info(f"  Testing CRUD for {entity.name} ({prefix})...")

            created_id = None
            create_response_data = None

            # Non-PK field names for data integrity checks
            non_pk_fields = [
                f.name for f in entity.fields if not f.primary_key
            ]

            # CREATE
            try:
                payload = _build_create_payload(spec, idx)
                r = requests.post(
                    f"{BASE_URL}{prefix}/",
                    json=payload,
                    headers=auth_headers,
                    timeout=10,
                )
                _record(results, "POST", f"{prefix}/", 201, r.status_code)
                if r.status_code == 201:
                    create_response_data = r.json()
                    # Find the PK field name
                    pk_name = next(
                        (f.name for f in entity.fields if f.primary_key), "id"
                    )
                    created_id = create_response_data.get(pk_name)

                    # DATA INTEGRITY: Verify created data matches payload
                    mismatches = []
                    for key in non_pk_fields:
                        sent = payload.get(key)
                        received = create_response_data.get(key)
                        if sent is not None and received is not None:
                            # Compare as strings for datetime/uuid tolerance
                            if str(sent) != str(received):
                                mismatches.append(
                                    f"{key}: sent={sent!r}, got={received!r}"
                                )
                    if mismatches:
                        _record(
                            results, "POST",
                            f"{prefix}/ (data integrity)", 201, 201,
                            f"Field mismatches: {'; '.join(mismatches)}",
                        )
                    else:
                        _record(
                            results, "POST",
                            f"{prefix}/ (data integrity)", 201, 201,
                        )
            except Exception as e:
                _record(results, "POST", f"{prefix}/", 201, None, str(e))

            # LIST
            try:
                r = requests.get(
                    f"{BASE_URL}{prefix}/",
                    headers=auth_headers,
                    timeout=10,
                )
                _record(results, "GET", f"{prefix}/", 200, r.status_code)

                # DATA INTEGRITY: Verify list contains created item
                if r.status_code == 200 and created_id:
                    items = r.json()
                    pk_name = next(
                        (f.name for f in entity.fields if f.primary_key), "id"
                    )
                    found = any(
                        str(item.get(pk_name)) == str(created_id)
                        for item in items
                    )
                    if found:
                        _record(
                            results, "GET",
                            f"{prefix}/ (contains created item)", 200, 200,
                        )
                    else:
                        _record(
                            results, "GET",
                            f"{prefix}/ (contains created item)", 200, 200,
                            f"Created item {created_id} not found in list",
                        )
            except Exception as e:
                _record(results, "GET", f"{prefix}/", 200, None, str(e))

            # READ (single)
            if created_id:
                try:
                    r = requests.get(
                        f"{BASE_URL}{prefix}/{created_id}",
                        headers=auth_headers,
                        timeout=10,
                    )
                    _record(results, "GET", f"{prefix}/{{id}}", 200, r.status_code)

                    # DATA INTEGRITY: Verify read matches create response
                    if r.status_code == 200 and create_response_data:
                        read_data = r.json()
                        mismatches = []
                        for key in non_pk_fields:
                            created_val = create_response_data.get(key)
                            read_val = read_data.get(key)
                            if str(created_val) != str(read_val):
                                mismatches.append(
                                    f"{key}: created={created_val!r}, read={read_val!r}"
                                )
                        if mismatches:
                            _record(
                                results, "GET",
                                f"{prefix}/{{id}} (data integrity)", 200, 200,
                                f"Read mismatch: {'; '.join(mismatches)}",
                            )
                        else:
                            _record(
                                results, "GET",
                                f"{prefix}/{{id}} (data integrity)", 200, 200,
                            )
                except Exception as e:
                    _record(results, "GET", f"{prefix}/{{id}}", 200, None, str(e))

                # UPDATE
                try:
                    update_payload = _build_update_payload(spec, idx)
                    r = requests.put(
                        f"{BASE_URL}{prefix}/{created_id}",
                        json=update_payload,
                        headers=auth_headers,
                        timeout=10,
                    )
                    _record(results, "PUT", f"{prefix}/{{id}}", 200, r.status_code)

                    # DATA INTEGRITY: Verify update applied new values
                    if r.status_code == 200:
                        updated_data = r.json()
                        mismatches = []
                        for key in non_pk_fields:
                            expected = update_payload.get(key)
                            actual = updated_data.get(key)
                            if expected is not None and actual is not None:
                                if str(expected) != str(actual):
                                    mismatches.append(
                                        f"{key}: expected={expected!r}, got={actual!r}"
                                    )
                        if mismatches:
                            _record(
                                results, "PUT",
                                f"{prefix}/{{id}} (data integrity)", 200, 200,
                                f"Update mismatch: {'; '.join(mismatches)}",
                            )
                        else:
                            _record(
                                results, "PUT",
                                f"{prefix}/{{id}} (data integrity)", 200, 200,
                            )
                except Exception as e:
                    _record(results, "PUT", f"{prefix}/{{id}}", 200, None, str(e))

                # DELETE
                try:
                    r = requests.delete(
                        f"{BASE_URL}{prefix}/{created_id}",
                        headers=auth_headers,
                        timeout=10,
                    )
                    _record(results, "DELETE", f"{prefix}/{{id}}", 204, r.status_code)
                except Exception as e:
                    _record(results, "DELETE", f"{prefix}/{{id}}", 204, None, str(e))

                # VERIFY DELETED
                try:
                    r = requests.get(
                        f"{BASE_URL}{prefix}/{created_id}",
                        headers=auth_headers,
                        timeout=10,
                    )
                    _record(
                        results, "GET", f"{prefix}/{{id}} (after delete)", 404,
                        r.status_code,
                    )
                except Exception as e:
                    _record(
                        results, "GET", f"{prefix}/{{id}} (after delete)", 404,
                        None, str(e),
                    )
            else:
                # If create failed, skip dependent tests but record them
                for method, path, code in [
                    ("GET", f"{prefix}/{{id}}", 200),
                    ("PUT", f"{prefix}/{{id}}", 200),
                    ("DELETE", f"{prefix}/{{id}}", 204),
                    ("GET", f"{prefix}/{{id}} (after delete)", 404),
                ]:
                    _record(results, method, path, code, None, "Skipped: CREATE failed")

    except Exception as e:
        logger.error(f"Verification failed with exception: {e}")
        errors.append(f"Unexpected error during verification: {str(e)}")

    finally:
        # Cleanup: tear down Docker
        if project_dir:
            logger.info("Step 5e: Tearing down Docker containers...")
            try:
                subprocess.run(
                    ["docker", "compose", "-p", compose_project, "down", "-v", "--remove-orphans"],
                    cwd=project_dir,
                    capture_output=True,
                    timeout=30,
                )
            except Exception as e:
                logger.warning(f"Docker cleanup failed: {e}")

            # Remove override file
            override_path = os.path.join(project_dir, "docker-compose.override.yml")
            if os.path.exists(override_path):
                os.remove(override_path)

        # Remove temp directory
        if tmpdir:
            try:
                shutil.rmtree(tmpdir)
            except Exception as e:
                logger.warning(f"Temp cleanup failed: {e}")

    # Aggregate results
    total = len(results)
    passed_count = sum(1 for r in results if r.passed)
    failed_count = total - passed_count

    return VerificationResult(
        passed=failed_count == 0 and total > 0 and not errors,
        total_tests=total,
        passed_tests=passed_count,
        failed_tests=failed_count,
        results=results,
        errors=errors,
    )
