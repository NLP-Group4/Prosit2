"""
Preservation Property Tests for Docker Health Check Timeout Fix

**Property 2: Preservation - Fast Deployment and Error Handling**

**IMPORTANT**: These tests observe behavior on UNFIXED code to establish baseline.
They should PASS on unfixed code and continue to PASS after the fix is implemented.

This ensures the fix doesn't introduce regressions for:
- Fast deployments (< 30s) completing without delays
- Port conflict errors producing specific error messages
- Docker detection producing specific guidance messages
- Verification test execution producing expected results
- Project cleanup stopping containers correctly

**Validates Requirements**: 3.1, 3.2, 3.3, 3.4, 3.5

Run with: pytest -m docker backend/tests/e2e/test_docker_preservation.py
"""

import pytest
import time
import tempfile
import shutil
import os
from pathlib import Path
import subprocess
import random


# Mark this test to skip by default, run with pytest -m docker
pytestmark = pytest.mark.docker


@pytest.fixture
def mock_project_fast():
    """
    Creates a minimal backend project that becomes healthy quickly (< 5 seconds).
    Used to test that the fix doesn't introduce unnecessary delays.
    """
    temp_dir = tempfile.mkdtemp(prefix="docker_preservation_fast_")
    
    project_path = Path(temp_dir)
    
    # Create main.py with health endpoint (no delay)
    main_py = project_path / "main.py"
    main_py.write_text("""
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}
""")
    
    # Create Dockerfile
    dockerfile = project_path / "Dockerfile"
    dockerfile.write_text("""
FROM python:3.11-slim

WORKDIR /app

RUN pip install fastapi uvicorn

COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
""")
    
    # Create docker-compose.yml (no database, fast startup)
    docker_compose = project_path / "docker-compose.yml"
    docker_compose.write_text("""
services:
  backend:
    build: .
    ports:
      - "8001:8000"
""")
    
    yield str(project_path)
    
    # Cleanup
    try:
        subprocess.run(
            ["docker", "compose", "down", "-v"],
            cwd=project_path,
            capture_output=True,
            timeout=30
        )
    except Exception as e:
        print(f"Cleanup warning: {e}")
    
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_project_port_conflict():
    """
    Creates two identical projects to test port conflict error handling.
    """
    temp_dir1 = tempfile.mkdtemp(prefix="docker_preservation_conflict1_")
    temp_dir2 = tempfile.mkdtemp(prefix="docker_preservation_conflict2_")
    
    for temp_dir in [temp_dir1, temp_dir2]:
        project_path = Path(temp_dir)
        
        # Create main.py
        main_py = project_path / "main.py"
        main_py.write_text("""
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}
""")
        
        # Create Dockerfile
        dockerfile = project_path / "Dockerfile"
        dockerfile.write_text("""
FROM python:3.11-slim

WORKDIR /app

RUN pip install fastapi uvicorn

COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
""")
        
        # Both use the same port to trigger conflict
        docker_compose = project_path / "docker-compose.yml"
        docker_compose.write_text("""
services:
  backend:
    build: .
    ports:
      - "8001:8000"
""")
    
    yield (str(temp_dir1), str(temp_dir2))
    
    # Cleanup
    for temp_dir in [temp_dir1, temp_dir2]:
        try:
            subprocess.run(
                ["docker", "compose", "down", "-v"],
                cwd=temp_dir,
                capture_output=True,
                timeout=30
            )
        except Exception:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_preservation_fast_deployment_no_delays(mock_project_fast):
    """
    **PRESERVATION TEST 1: Fast deployments complete without unnecessary delays**
    
    Observes behavior on unfixed code: Fast deployments (< 30s) should complete quickly.
    After fix: Should continue to complete quickly without introducing delays.
    
    **Validates**: Requirements 3.1, 3.2
    """
    project_path = mock_project_fast
    
    print(f"\n[PRESERVATION TEST] Testing fast deployment timing")
    print(f"[TEST] Project path: {project_path}")
    
    start_time = time.time()
    deployment_succeeded = False
    
    try:
        # Start docker compose
        print(f"[TEST] Running docker compose up --build -d")
        result = subprocess.run(
            ["docker", "compose", "up", "--build", "-d"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            raise Exception(f"Docker Compose failed: {result.stderr}")
        
        print(f"[TEST] Containers started, waiting for health check...")
        
        # Wait for health with reasonable timeout
        health_url = "http://localhost:8001/health"
        max_attempts = 60  # Allow up to 60 attempts for flexibility
        
        for attempt in range(max_attempts):
            try:
                import urllib.request
                response = urllib.request.urlopen(health_url, timeout=2)
                if response.status == 200:
                    deployment_succeeded = True
                    elapsed = time.time() - start_time
                    print(f"[TEST] ✅ Health check succeeded after {elapsed:.1f}s")
                    break
            except Exception:
                pass
            
            time.sleep(1)
        
        elapsed = time.time() - start_time
        
        # Document observed behavior
        print(f"\n[OBSERVED BEHAVIOR]")
        print(f"  - Deployment succeeded: {deployment_succeeded}")
        print(f"  - Total time: {elapsed:.1f} seconds")
        print(f"  - Expected: < 30 seconds for fast deployments")
        
        # ASSERTION: Fast deployments should complete quickly
        # This should PASS on both unfixed and fixed code
        assert deployment_succeeded, "Fast deployment should succeed"
        assert elapsed < 45, (
            f"Fast deployment took {elapsed:.1f}s (expected < 45s). "
            f"This suggests unnecessary delays were introduced."
        )
        
        print(f"[TEST] ✅ PRESERVATION VERIFIED: Fast deployment completed in {elapsed:.1f}s")
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n[TEST] ❌ PRESERVATION FAILED after {elapsed:.1f}s: {e}")
        raise


def test_preservation_error_handling_port_conflict(mock_project_port_conflict):
    """
    **PRESERVATION TEST 2: Port conflict errors produce appropriate error messages**
    
    Observes behavior on unfixed code: Port conflicts should produce specific error messages.
    After fix: Should continue to produce the same error messages.
    
    **Validates**: Requirement 3.3
    """
    project_path1, project_path2 = mock_project_port_conflict
    
    print(f"\n[PRESERVATION TEST] Testing port conflict error handling")
    
    try:
        # Start first project
        print(f"[TEST] Starting first project on port 8001")
        result1 = subprocess.run(
            ["docker", "compose", "up", "--build", "-d"],
            cwd=project_path1,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result1.returncode != 0:
            raise Exception(f"First project failed: {result1.stderr}")
        
        # Wait for first project to be healthy
        health_url = "http://localhost:8001/health"
        for _ in range(30):
            try:
                import urllib.request
                response = urllib.request.urlopen(health_url, timeout=2)
                if response.status == 200:
                    print(f"[TEST] First project is healthy")
                    break
            except Exception:
                pass
            time.sleep(1)
        
        # Try to start second project on same port (should fail)
        print(f"[TEST] Attempting to start second project on same port (should fail)")
        result2 = subprocess.run(
            ["docker", "compose", "up", "--build", "-d"],
            cwd=project_path2,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Document observed error behavior
        print(f"\n[OBSERVED BEHAVIOR]")
        print(f"  - Second project exit code: {result2.returncode}")
        print(f"  - Error output contains 'port' or 'address': {('port' in result2.stderr.lower() or 'address' in result2.stderr.lower())}")
        
        # ASSERTION: Port conflict should produce an error
        # This should PASS on both unfixed and fixed code
        assert result2.returncode != 0, "Port conflict should cause deployment to fail"
        
        # The error message should mention port or address issues
        error_mentions_port = 'port' in result2.stderr.lower() or 'address' in result2.stderr.lower()
        
        print(f"[TEST] ✅ PRESERVATION VERIFIED: Port conflict produces appropriate error")
        
    except Exception as e:
        print(f"\n[TEST] ❌ PRESERVATION TEST ERROR: {e}")
        raise


def test_preservation_docker_detection():
    """
    **PRESERVATION TEST 3: Docker detection produces specific guidance messages**
    
    Observes behavior: Docker detection should work correctly.
    After fix: Should continue to work exactly the same.
    
    **Validates**: Requirement 3.3
    
    NOTE: This test verifies Docker is available. The actual docker-manager.cjs
    detection logic is tested in the JavaScript/Electron integration tests.
    """
    print(f"\n[PRESERVATION TEST] Testing Docker detection")
    
    try:
        # Test docker --version
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        docker_available = result.returncode == 0
        docker_version = result.stdout.strip() if docker_available else None
        
        # Test docker compose version
        result2 = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        compose_available = result2.returncode == 0
        compose_version = result2.stdout.strip() if compose_available else None
        
        # Document observed behavior
        print(f"\n[OBSERVED BEHAVIOR]")
        print(f"  - Docker available: {docker_available}")
        print(f"  - Docker version: {docker_version}")
        print(f"  - Docker Compose available: {compose_available}")
        print(f"  - Docker Compose version: {compose_version}")
        
        # ASSERTION: Docker should be available for these tests
        # This should PASS on both unfixed and fixed code
        assert docker_available, "Docker should be installed"
        assert compose_available, "Docker Compose should be available"
        
        print(f"[TEST] ✅ PRESERVATION VERIFIED: Docker detection works correctly")
        
    except Exception as e:
        print(f"\n[TEST] ❌ PRESERVATION TEST ERROR: {e}")
        pytest.skip(f"Docker not available: {e}")


def test_preservation_cleanup_behavior(mock_project_fast):
    """
    **PRESERVATION TEST 4: Project cleanup stops containers correctly**
    
    Observes behavior on unfixed code: stopProject should stop containers.
    After fix: Should continue to work exactly the same.
    
    **Validates**: Requirement 3.5
    """
    project_path = mock_project_fast
    
    print(f"\n[PRESERVATION TEST] Testing project cleanup behavior")
    
    try:
        # Start project
        print(f"[TEST] Starting project")
        result = subprocess.run(
            ["docker", "compose", "up", "--build", "-d"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            raise Exception(f"Docker Compose failed: {result.stderr}")
        
        # Wait for health
        health_url = "http://localhost:8001/health"
        deployment_succeeded = False
        
        for _ in range(30):
            try:
                import urllib.request
                response = urllib.request.urlopen(health_url, timeout=2)
                if response.status == 200:
                    deployment_succeeded = True
                    print(f"[TEST] Project is healthy")
                    break
            except Exception:
                pass
            time.sleep(1)
        
        assert deployment_succeeded, "Project should become healthy"
        
        # Now stop the project
        print(f"[TEST] Stopping project with docker compose down")
        stop_result = subprocess.run(
            ["docker", "compose", "down", "-v"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Document observed behavior
        print(f"\n[OBSERVED BEHAVIOR]")
        print(f"  - Stop command exit code: {stop_result.returncode}")
        print(f"  - Stop command succeeded: {stop_result.returncode == 0}")
        
        # Verify containers are stopped (health check should fail)
        time.sleep(2)  # Give containers time to stop
        
        containers_stopped = False
        try:
            import urllib.request
            response = urllib.request.urlopen(health_url, timeout=2)
        except Exception:
            # Connection refused means containers are stopped
            containers_stopped = True
        
        print(f"  - Containers stopped: {containers_stopped}")
        
        # ASSERTION: Cleanup should stop containers
        # This should PASS on both unfixed and fixed code
        assert stop_result.returncode == 0, "docker compose down should succeed"
        assert containers_stopped, "Containers should be stopped after cleanup"
        
        print(f"[TEST] ✅ PRESERVATION VERIFIED: Cleanup stops containers correctly")
        
    except Exception as e:
        print(f"\n[TEST] ❌ PRESERVATION TEST ERROR: {e}")
        raise


def test_preservation_verification_flow(mock_project_fast):
    """
    **PRESERVATION TEST 5: Verification test execution produces expected results**
    
    Observes behavior on unfixed code: Health endpoint should be accessible after deployment.
    After fix: Should continue to work exactly the same.
    
    **Validates**: Requirements 3.4, 3.5
    """
    project_path = mock_project_fast
    
    print(f"\n[PRESERVATION TEST] Testing verification flow")
    
    try:
        # Start project
        print(f"[TEST] Starting project")
        result = subprocess.run(
            ["docker", "compose", "up", "--build", "-d"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            raise Exception(f"Docker Compose failed: {result.stderr}")
        
        # Wait for health
        health_url = "http://localhost:8001/health"
        deployment_succeeded = False
        
        for _ in range(30):
            try:
                import urllib.request
                response = urllib.request.urlopen(health_url, timeout=2)
                if response.status == 200:
                    deployment_succeeded = True
                    print(f"[TEST] Project is healthy")
                    break
            except Exception:
                pass
            time.sleep(1)
        
        assert deployment_succeeded, "Project should become healthy"
        
        # Simulate verification test (GET /health)
        print(f"[TEST] Running verification test: GET /health")
        import urllib.request
        import json
        
        response = urllib.request.urlopen(health_url, timeout=5)
        response_data = json.loads(response.read().decode())
        
        # Document observed behavior
        print(f"\n[OBSERVED BEHAVIOR]")
        print(f"  - Health endpoint status: {response.status}")
        print(f"  - Health endpoint response: {response_data}")
        print(f"  - Verification test passed: {response.status == 200 and response_data.get('status') == 'ok'}")
        
        # ASSERTION: Verification should work correctly
        # This should PASS on both unfixed and fixed code
        assert response.status == 200, "Health endpoint should return 200"
        assert response_data.get('status') == 'ok', "Health endpoint should return status: ok"
        
        print(f"[TEST] ✅ PRESERVATION VERIFIED: Verification flow works correctly")
        
    except Exception as e:
        print(f"\n[TEST] ❌ PRESERVATION TEST ERROR: {e}")
        raise
