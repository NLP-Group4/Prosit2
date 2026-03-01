"""
SandboxExecutor — auto-deploys generated code to the sandbox container,
waits for a health check, runs pytest tests, and returns results.

Used by the orchestrator between the implementer and reviewer stages.
"""
from __future__ import annotations

import asyncio
import logging
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from app.agent.artifacts import CodeFile, SandboxTestReport

logger = logging.getLogger(__name__)

SANDBOX_ROOT = Path("/sandbox")
SANDBOX_CONTAINER_NAME = "craftlive-sandbox-runner-1"
SANDBOX_PORT = 9000
HEALTH_CHECK_URL = f"http://sandbox-runner:{SANDBOX_PORT}/docs"
HEALTH_CHECK_TIMEOUT = 45  # seconds to wait for the API to come alive
PYTEST_TIMEOUT = 60  # seconds for pytest to finish


class SandboxExecutor:
    """Deploys generated code + tests to the sandbox and runs pytest."""

    def __init__(self, project_id: uuid.UUID):
        self.project_id = project_id
        self.sandbox_dir = SANDBOX_ROOT / str(project_id)

    def _write_files(
        self,
        code_files: list[CodeFile],
        test_files: list[CodeFile] | None = None,
        dependencies: list[str] | None = None,
        test_dependencies: list[str] | None = None,
    ) -> None:
        """Write code files, test files, requirements.txt, and start.sh to the sandbox volume."""
        # Clean previous deploy
        if self.sandbox_dir.exists():
            shutil.rmtree(self.sandbox_dir)
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)

        # Write application code
        for f in code_files:
            file_path = self.sandbox_dir / f.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            # Apply auto-patches from sandbox.py import
            from app.api.routes.sandbox import _auto_patch_content
            content = _auto_patch_content(f.path, f.content)
            file_path.write_text(content, encoding="utf-8")

        # Write test files
        if test_files:
            for f in test_files:
                file_path = self.sandbox_dir / f.path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(f.content, encoding="utf-8")

        # Write requirements.txt
        base_deps = {"fastapi", "uvicorn[standard]", "sqlmodel"}
        all_deps = base_deps | set(dependencies or [])
        if test_files:
            all_deps |= {"pytest", "httpx", "anyio", "pytest-anyio"}
            all_deps |= set(test_dependencies or [])
        reqs_path = self.sandbox_dir / "requirements.txt"
        reqs_path.write_text("\n".join(sorted(all_deps)), encoding="utf-8")

        # Write launcher script
        launcher = self.sandbox_dir / "start.sh"
        launcher.write_text(
            f"""#!/bin/bash
set -e
cd /sandbox/{self.project_id}
pip install -q -r requirements.txt 2>&1

# Auto-fix common syntax errors before starting
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
uvicorn $MODULE --host 0.0.0.0 --port {SANDBOX_PORT} > /sandbox/uvicorn.log 2>&1 &
echo $! > /sandbox/uvicorn.pid

# Wait for uvicorn to come up before running tests
echo "Waiting for uvicorn..."
python -c "
import urllib.request, time
for _ in range(30):
    try:
        urllib.request.urlopen('http://localhost:{SANDBOX_PORT}/docs', timeout=1)
        break
    except Exception:
        time.sleep(1)
"

# Run tests if they exist
rm -f /sandbox/{self.project_id}/.pytest_done
if [ -d "tests" ]; then
    python -m pytest tests/ -v --tb=short --no-header -q > /sandbox/{self.project_id}/pytest.log 2>&1 || true
else
    echo "No tests directory found." > /sandbox/{self.project_id}/pytest.log
fi
touch /sandbox/{self.project_id}/.pytest_done
""",
            encoding="utf-8",
        )
        launcher.chmod(0o755)
        logger.info("Wrote %d code files + %d test files to sandbox", len(code_files), len(test_files or []))

    def _start_sandbox(self) -> bool:
        """Execute start.sh inside the sandbox container. Returns True if successful."""
        try:
            result = subprocess.run(
                [
                    "docker", "exec", "-d",
                    SANDBOX_CONTAINER_NAME,
                    "bash", f"/sandbox/{self.project_id}/start.sh",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.error("Sandbox start failed: %s", result.stderr)
                return False
            return True
        except FileNotFoundError:
            # Docker CLI not available — write signal file
            logger.warning("docker CLI not found, writing signal file")
            signal = self.sandbox_dir / ".deploy"
            signal.write_text("start", encoding="utf-8")
            return True
        except Exception as exc:
            logger.error("Sandbox start exception: %s", exc)
            return False

    async def _wait_for_health(self) -> bool:
        """Poll the sandbox until /docs responds or timeout."""
        import urllib.request

        for i in range(HEALTH_CHECK_TIMEOUT):
            await asyncio.sleep(1)
            try:
                urllib.request.urlopen(HEALTH_CHECK_URL, timeout=2)
                logger.info("Sandbox health check passed after %ds", i + 1)
                return True
            except Exception:
                continue
        logger.warning("Sandbox health check timed out after %ds", HEALTH_CHECK_TIMEOUT)
        return False

    def _run_pytest(self) -> tuple[int, int, int, str]:
        """Wait for pytest to finish in the sandbox and parse its output. Returns (passed, failed, total, output)."""
        import time
        done_marker = self.sandbox_dir / ".pytest_done"
        log_file = self.sandbox_dir / "pytest.log"

        # Wait for the sandbox start.sh to create the .pytest_done marker
        start_time = time.time()
        while time.time() - start_time < PYTEST_TIMEOUT:
            if done_marker.exists():
                break
            time.sleep(1)
        else:
            return 0, 0, 0, "pytest timed out or start.sh failed to run tests"

        if not log_file.exists():
            return 0, 0, 0, "pytest log not found"

        output = log_file.read_text(encoding="utf-8")

        # Truncate long outputs
        if len(output) > 2000:
            output = output[:2000] + "\n... (truncated)"

        # Parse pytest summary line e.g. "3 passed, 2 failed"
        passed = 0
        failed = 0
        summary_match = re.search(r"(\d+) passed", output)
        if summary_match:
            passed = int(summary_match.group(1))
        fail_match = re.search(r"(\d+) failed", output)
        if fail_match:
            failed = int(fail_match.group(1))
        error_match = re.search(r"(\d+) error", output)
        if error_match:
            failed += int(error_match.group(1))

        total = passed + failed
        return passed, failed, total, output

    @staticmethod
    def _extract_failures(pytest_output: str) -> list[str]:
        """Extract individual test failure names from pytest output."""
        failures = []
        for line in pytest_output.splitlines():
            if line.strip().startswith("FAILED"):
                failures.append(line.strip())
            elif " FAILED" in line and "::" in line:
                failures.append(line.strip())
        return failures[:20]  # Cap at 20 failures

    async def deploy_and_test(
        self,
        code_files: list[CodeFile],
        test_files: list[CodeFile] | None = None,
        dependencies: list[str] | None = None,
        test_dependencies: list[str] | None = None,
    ) -> SandboxTestReport:
        """
        Full loop: write files → start sandbox → health check → run pytest → return report.
        """
        # Step 1: Write everything
        self._write_files(code_files, test_files, dependencies, test_dependencies)

        # Step 2: Start the sandbox
        started = self._start_sandbox()
        if not started:
            return SandboxTestReport(
                deployed=False,
                health_check_ok=False,
                test_output="Failed to start sandbox container",
            )

        # Step 3: Wait for health check
        healthy = await self._wait_for_health()
        if not healthy:
            # Try to get uvicorn.log for diagnostics
            log_content = ""
            try:
                alt_log = SANDBOX_ROOT / "uvicorn.log"
                if alt_log.exists():
                    log_content = alt_log.read_text(encoding="utf-8")[-2000:]
            except Exception:
                pass

            # Parse traceback from uvicorn logs for structured error info
            error_file_path = None
            error_line = None
            traceback_summary = ""
            if log_content:
                # Find the last traceback file reference pointing to app code
                tb_file_matches = list(re.finditer(
                    r'File "[^"]*/(app/\S+\.py)", line (\d+)',
                    log_content,
                ))
                if tb_file_matches:
                    last_match = tb_file_matches[-1]
                    error_file_path = last_match.group(1)
                    error_line = int(last_match.group(2))

                # Find the error type and message
                tb_error_match = re.search(
                    r'(NameError|ImportError|ModuleNotFoundError|AttributeError|TypeError|ValueError|SyntaxError|IndentationError|KeyError|RuntimeError): (.+)',
                    log_content,
                )
                if tb_error_match:
                    traceback_summary = f"{tb_error_match.group(1)}: {tb_error_match.group(2).strip()}"

            return SandboxTestReport(
                deployed=True,
                health_check_ok=False,
                test_output=f"Health check failed. Uvicorn log:\n{log_content}",
                error_file_path=error_file_path,
                error_line=error_line,
                traceback_summary=traceback_summary,
            )

        # Step 4: Run pytest (if test files were provided)
        if test_files:
            passed, failed, total, output = self._run_pytest()
            failures = self._extract_failures(output)
            return SandboxTestReport(
                deployed=True,
                health_check_ok=True,
                tests_passed=passed,
                tests_failed=failed,
                tests_total=total,
                test_output=output,
                failures=failures,
            )

        # No tests — just deployment verification
        return SandboxTestReport(
            deployed=True,
            health_check_ok=True,
            test_output="Sandbox deployed and healthy. No test files provided.",
        )
