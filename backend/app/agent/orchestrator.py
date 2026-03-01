import json
import logging
import uuid

from sqlmodel import Session

from app.agent.architecture_agent import ArchitectureAgent
from app.agent.artifact_store import store_code_bundle
from app.agent.artifacts import GeneratedCode, ProjectCharter, SystemArchitecture
from app.agent.implementer_agent import ImplementerAgent
from app.agent.requirements_agent import RequirementsAgent
from app.agent.reviewer_agent import ReviewerAgent
from app.agent.sandbox_executor import SandboxExecutor
from app.agent.test_generator_agent import TestGeneratorAgent
from app.agent.test_runner import TestRunner
from app.crud import create_artifact_record, update_generation_run_status
from app.models import ArtifactRecordCreate

logger = logging.getLogger(__name__)


def _rollback_session_safely(session: Session) -> None:
    try:
        session.rollback()
    except Exception as exc:
        logger.warning("Session rollback failed: %s", exc)


def _update_run_status_safely(session: Session, run_id: uuid.UUID, status: str) -> None:
    try:
        update_generation_run_status(session=session, run_id=run_id, status=status)
    except Exception as exc:
        logger.warning("Failed to update generation run %s to %s: %s", run_id, status, exc)


def _compact_generated_code_for_db(
    *,
    run_id: uuid.UUID,
    stage: str,
    code: GeneratedCode,
) -> dict:
    bundle_ref = store_code_bundle(
        run_id=run_id,
        stage=stage,
        files=code.files,
        dependencies=code.dependencies,
    )
    return {
        "bundle_ref": bundle_ref,
        "files_count": len(code.files),
        "paths": [file.path for file in code.files],
        "dependencies": code.dependencies,
    }


def _compact_review_for_db(
    *,
    run_id: uuid.UUID,
    stage: str,
    review_artifact: dict,
    dependencies: list[str],
) -> dict:
    final_code = list(review_artifact.get("final_code") or [])
    compact_artifact = dict(review_artifact)
    if not final_code:
        return compact_artifact

    bundle_ref = store_code_bundle(
        run_id=run_id,
        stage=stage,
        files=final_code,
        dependencies=dependencies,
    )
    compact_artifact["bundle_ref"] = bundle_ref
    compact_artifact["final_code"] = []
    compact_artifact["final_code_files_count"] = len(final_code)
    compact_artifact["paths"] = [
        file.get("path")
        for file in final_code
        if isinstance(file, dict) and file.get("path")
    ]
    compact_artifact["dependencies"] = dependencies
    return compact_artifact

async def run_pipeline_generator(
    session: Session,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    prompt: str,
    *,
    start_stage: str = "requirements",
    charter_override: ProjectCharter | None = None,
    architecture_override: SystemArchitecture | None = None,
):
    """
    Generator function that runs the agents sequentially, saves artifacts to the DB,
    and yields SSE events for the frontend.
    """
    yield json.dumps({"status": "starting", "message": "Initializing pipeline..."})
    _update_run_status_safely(session=session, run_id=run_id, status="running")

    try:
        # 1. RAG Context (Temporarily disabled for model testing)
        # yield json.dumps({"status": "rag", "message": "Retrieving project context..."})
        # rag_context = get_rag_manager().query_context(str(project_id), prompt)
        combined_prompt = prompt
        # if rag_context:
        #     combined_prompt += f"\n\n{rag_context}"

        stage_mode = (start_stage or "requirements").strip().lower()

        charter: ProjectCharter | None = None
        architecture: SystemArchitecture | None = None

        if stage_mode == "requirements":
            # 2. Requirements Agent
            yield json.dumps({"status": "requirements", "message": "Analyzing requirements..."})
            req_agent = RequirementsAgent()
            charter = await req_agent.run(combined_prompt)

            create_artifact_record(
                session=session,
                artifact_in=ArtifactRecordCreate(
                    run_id=run_id,
                    stage="requirements",
                    content=charter.model_dump()
                )
            )
            yield json.dumps({"status": "requirements_done", "artifact": charter.model_dump()})

            # 3. Architecture Agent
            yield json.dumps({"status": "architecture", "message": "Designing system architecture..."})
            arch_agent = ArchitectureAgent()
            architecture = await arch_agent.run(charter)

            create_artifact_record(
                session=session,
                artifact_in=ArtifactRecordCreate(
                    run_id=run_id,
                    stage="architecture",
                    content=architecture.model_dump()
                )
            )
            yield json.dumps({"status": "architecture_done", "artifact": architecture.model_dump()})
        elif stage_mode == "implementer":
            if architecture_override is None:
                raise ValueError("architecture_override is required when starting from implementer")
            architecture = architecture_override
            charter = charter_override
            # Emit checkpoint completion events so UI can resume consistently in future integrations if needed.
            if charter is not None:
                yield json.dumps({"status": "requirements_done", "artifact": charter.model_dump()})
            yield json.dumps({"status": "architecture_done", "artifact": architecture.model_dump()})
        else:
            raise ValueError(f"Unsupported start_stage: {start_stage}")

        # 4. Implementer Agent
        yield json.dumps({"status": "implementer", "message": "Generating source code..."})
        imp_agent = ImplementerAgent()
        code = await imp_agent.run(architecture)

        # Save Artifact
        create_artifact_record(
            session=session,
            artifact_in=ArtifactRecordCreate(
                run_id=run_id,
                stage="implementer",
                content=_compact_generated_code_for_db(
                    run_id=run_id,
                    stage="implementer",
                    code=code,
                ),
            )
        )
        yield json.dumps({
            "status": "implementer_done",
            "files_count": len(code.files),
            "artifact": code.model_dump()
        })

        # 4.5 Deterministic Tests (syntax + import smoke)
        yield json.dumps({"status": "testing", "message": "Running deterministic code checks (syntax, imports)..."})
        test_runner = TestRunner()
        test_report = await test_runner.run(code)

        create_artifact_record(
            session=session,
            artifact_in=ArtifactRecordCreate(
                run_id=run_id,
                stage="deterministic_tests",
                content=test_report.model_dump(),
            )
        )

        if not test_report.passed and test_report.patch_requests:
            yield json.dumps({
                "status": "testing_fix",
                "message": f"Found {len(test_report.failures)} issue(s), auto-patching...",
                "failures": [f.message for f in test_report.failures],
            })
            code = await imp_agent.patch_files(
                architecture=architecture,
                current_code=code,
                patch_requests=test_report.patch_requests,
                review_issue_descriptions_by_file={},
            )

        yield json.dumps({
            "status": "testing_done",
            "message": f"Deterministic checks: {', '.join(test_report.checks_run)}",
            "passed": test_report.passed,
            "checks": test_report.checks_run,
        })

        # 4.6 Generate Pytest Suite
        sandbox_report = None
        generated_tests = None
        MAX_SANDBOX_RETRIES = 3

        # Test generation is non-blocking — if it fails, we still deploy without tests
        try:
            yield json.dumps({"status": "test_generation", "message": "Generating endpoint test suite..."})
            test_gen_agent = TestGeneratorAgent()
            generated_tests = await test_gen_agent.run(architecture, code)

            create_artifact_record(
                session=session,
                artifact_in=ArtifactRecordCreate(
                    run_id=run_id,
                    stage="test_generation",
                    content={
                        "test_files": [f.model_dump() for f in generated_tests.test_files],
                        "dependencies": generated_tests.dependencies,
                    },
                )
            )
            yield json.dumps({
                "status": "test_generation_done",
                "message": f"Generated {len(generated_tests.test_files)} test file(s)",
                "test_files": [f.path for f in generated_tests.test_files],
            })
        except Exception as test_gen_exc:
            logger.warning("Test generation failed (non-blocking): %s", test_gen_exc)
            yield json.dumps({
                "status": "test_generation_done",
                "message": f"Test generation skipped: {test_gen_exc}",
            })

        # 5. Review Loop (Perceive-Plan-Act cycle)
        # We run the Reviewer BEFORE the Sandbox so the Sandbox tests the *final* code.
        MAX_REVIEW_ITERATIONS = 5
        REVIEW_TRUST_SCORE_THRESHOLD = 7
        rev_agent = ReviewerAgent()
        review_artifact_for_completion: dict = {
            "approved": True,
            "issues": [],
            "suggestions": [],
            "security_score": 7,
            "affected_files": [],
            "patch_requests": [],
            "final_code": [f.model_dump() for f in code.files],
        }

        try:
            prev_score: int | None = None
            prev_issues: list = []
            for attempt in range(1, MAX_REVIEW_ITERATIONS + 1):
                yield json.dumps({
                    "status": "reviewer",
                    "message": f"Review pass {attempt}/{MAX_REVIEW_ITERATIONS} - checking code quality and security...",
                    "attempt": attempt,
                    "prev_score": prev_score,
                })

                # Note: sandbox_report is None here since Sandbox runs after Reviewer
                review = await rev_agent.run(
                    code,
                    previous_score=prev_score,
                    previous_issues=prev_issues or None,
                    sandbox_report=None,
                )
                review_artifact_for_completion = review.model_dump()
                review_artifact_for_completion["final_code"] = [f.model_dump() for f in code.files]

                current_score = review.security_score or 0

                create_artifact_record(
                    session=session,
                    artifact_in=ArtifactRecordCreate(
                        run_id=run_id,
                        stage=f"reviewer_pass_{attempt}",
                        content=_compact_review_for_db(
                            run_id=run_id,
                            stage=f"reviewer_pass_{attempt}",
                            review_artifact=review_artifact_for_completion,
                            dependencies=code.dependencies,
                        ),
                    )
                )

                meets_trust_threshold = current_score >= REVIEW_TRUST_SCORE_THRESHOLD
                review_accepted = bool(review.approved) and meets_trust_threshold

                if review_accepted:
                    logger.info(
                        "Code approved on review pass %s (score=%s, threshold=%s)",
                        attempt,
                        current_score,
                        REVIEW_TRUST_SCORE_THRESHOLD,
                    )
                    yield json.dumps({
                        "status": "reviewer_done",
                        "message": (
                            f"Code approved on pass {attempt} "
                            f"(trust score {current_score}/{10})."
                        ),
                        "score": current_score,
                        "artifact": review_artifact_for_completion
                    })
                    break

                if review.approved and not meets_trust_threshold:
                    logger.info(
                        "Review pass %s approved code but score %s is below threshold %s; requesting targeted fixes.",
                        attempt,
                        current_score,
                        REVIEW_TRUST_SCORE_THRESHOLD,
                    )

                if review.final_code:
                    logger.info("Review pass %s returned reviewer rewrites; re-running review.", attempt)
                    code = GeneratedCode(files=review.final_code, dependencies=code.dependencies)
                    review_artifact_for_completion["final_code"] = [f.model_dump() for f in code.files]
                    prev_score = current_score
                    prev_issues = list(review.issues or [])
                    yield json.dumps(
                        {
                            "status": "revision",
                            "message": (
                                f"Pass {attempt}: reviewer provided code fixes; "
                                "re-reviewing updated files..."
                            ),
                            "attempt": attempt,
                            "score": current_score,
                            "prev_score": prev_score,
                            "issues_count": len(review.issues),
                        }
                    )
                    continue

                issue_map: dict[str, list[str]] = {}
                for issue in review.issues or []:
                    path = (issue.file_path or "").strip()
                    if not path:
                        continue
                    desc = f"[{issue.severity}] {issue.description}"
                    issue_map.setdefault(path, []).append(desc)

                affected_from_review = [p for p in (review.affected_files or []) if isinstance(p, str) and p.strip()]
                affected_from_issues = [p for p in issue_map.keys() if p]
                targeted_paths = list(dict.fromkeys(affected_from_review + affected_from_issues))
                patch_requests = list(review.patch_requests or [])

                if not patch_requests and targeted_paths:
                    from app.agent.artifacts import FilePatchRequest
                    patch_requests = [
                        FilePatchRequest(
                            path=path,
                            reason="Reviewer reported issues in this file",
                            instructions=issue_map.get(path, []) or ["Fix the reviewer-reported issues while preserving existing behavior."],
                        )
                        for path in targeted_paths
                    ]

                if not patch_requests:
                    logger.info(
                        "Review pass %s returned issues but no rewritten code; ending review loop without retry.",
                        attempt,
                    )
                    yield json.dumps({
                        "status": "reviewer_done",
                        "message": f"Review found {len(review.issues)} issue(s); returning generated code without reviewer rewrites.",
                        "score": current_score,
                        "artifact": review_artifact_for_completion
                    })
                    break

                logger.info(
                    "Review pass %s: %s issues found across %s file(s); regenerating affected files.",
                    attempt,
                    len(review.issues),
                    len(patch_requests),
                )
                prev_score = current_score
                prev_issues = list(review.issues or [])
                code = await imp_agent.patch_files(
                    architecture=architecture,
                    current_code=code,
                    patch_requests=patch_requests,
                    review_issue_descriptions_by_file=issue_map,
                )
                review_artifact_for_completion["final_code"] = [f.model_dump() for f in code.files]

                yield json.dumps({
                    "status": "revision",
                    "message": (
                        f"Pass {attempt}: {len(review.issues)} reviewer issue(s) "
                        f"(trust score {current_score}/{10}) - regenerating "
                        "affected files and re-reviewing..."
                    ),
                    "attempt": attempt,
                    "score": current_score,
                    "prev_score": prev_score,
                    "issues_count": len(review.issues),
                })
        except Exception as rev_exc:
            logger.exception("Reviewer error: %s", rev_exc)
            yield json.dumps({
                "status": "reviewer_done",
                "message": f"Review stage failed: {rev_exc}",
                "score": 0,
                "artifact": review_artifact_for_completion
            })

        # 6. Auto-Deploy to Sandbox & Run Tests — MANDATORY retry loop
        # Runs AFTER Reviewer so it tests the final code.
        # This is NOT wrapped in a try/except so sandbox errors are visible and
        # feed into the implementer's patch loop.
        for sandbox_attempt in range(1, MAX_SANDBOX_RETRIES + 1):
            yield json.dumps({
                "status": "sandbox_deploy",
                "message": f"Sandbox deploy attempt {sandbox_attempt}/{MAX_SANDBOX_RETRIES}...",
                "attempt": sandbox_attempt,
            })

            try:
                executor = SandboxExecutor(project_id=project_id)
                sandbox_report = await executor.deploy_and_test(
                    code_files=code.files,
                    test_files=generated_tests.test_files if generated_tests else None,
                    dependencies=code.dependencies,
                    test_dependencies=generated_tests.dependencies if generated_tests else None,
                )
            except Exception as deploy_exc:
                logger.error("Sandbox deploy exception on attempt %s: %s", sandbox_attempt, deploy_exc)
                from app.agent.artifacts import SandboxTestReport
                sandbox_report = SandboxTestReport(
                    deployed=False,
                    health_check_ok=False,
                    test_output=f"Sandbox deploy exception: {deploy_exc}",
                )

            create_artifact_record(
                session=session,
                artifact_in=ArtifactRecordCreate(
                    run_id=run_id,
                    stage=f"sandbox_tests_attempt_{sandbox_attempt}",
                    content=sandbox_report.model_dump(),
                )
            )

            sandbox_ok = (
                sandbox_report.deployed
                and sandbox_report.health_check_ok
                and sandbox_report.tests_failed == 0
            )

            if sandbox_ok:
                yield json.dumps({
                    "status": "sandbox_deploy_done",
                    "message": (
                        f"✅ Sandbox passed on attempt {sandbox_attempt} | "
                        f"Tests: {sandbox_report.tests_passed}/{sandbox_report.tests_total} passed"
                    ),
                    "artifact": sandbox_report.model_dump(),
                })
                break  # Success — exit retry loop

            # Sandbox failed — build patch requests from the failure output
            sandbox_error_summary = []
            if not sandbox_report.deployed:
                sandbox_error_summary.append("Sandbox container failed to start")
            if not sandbox_report.health_check_ok:
                sandbox_error_summary.append("Health check failed (API did not respond on /docs)")
            if sandbox_report.failures:
                sandbox_error_summary.extend(sandbox_report.failures[:5])
            if sandbox_report.test_output and not sandbox_report.health_check_ok:
                sandbox_error_summary.append(f"Logs: {sandbox_report.test_output[:500]}")

            # If this is the last attempt, accept the failure and move on
            if sandbox_attempt >= MAX_SANDBOX_RETRIES:
                yield json.dumps({
                    "status": "sandbox_deploy_done",
                    "message": (
                        f"❌ Sandbox failed after {MAX_SANDBOX_RETRIES} attempts | "
                        f"Tests: {sandbox_report.tests_passed}/{sandbox_report.tests_total} passed, "
                        f"{sandbox_report.tests_failed} failed"
                    ),
                    "artifact": sandbox_report.model_dump(),
                })
                break

            # Feed errors back to implementer for patching
            yield json.dumps({
                "status": "sandbox_retry",
                "message": (
                    f"Sandbox attempt {sandbox_attempt} failed — "
                    f"patching code and retrying..."
                ),
                "attempt": sandbox_attempt,
                "errors": sandbox_error_summary,
            })

            # Build patch requests from sandbox failures — parse tracebacks for precise targeting
            import re as _re

            from app.agent.artifacts import FilePatchRequest
            sandbox_patch_requests = []

            # Parse traceback from test_output to find the exact file and error
            traceback_file_path = None
            traceback_error_msg = None
            if sandbox_report.test_output:
                # Look for Python traceback patterns like:
                #   File "/sandbox/.../app/models.py", line 4, in Task
                #   NameError: name 'Field' is not defined
                tb_file_match = _re.search(
                    r'File "[^"]*/(app/\S+\.py)", line (\d+)',
                    sandbox_report.test_output,
                )
                tb_error_match = _re.search(
                    r'(NameError|ImportError|ModuleNotFoundError|AttributeError|TypeError|ValueError|SyntaxError): (.+)',
                    sandbox_report.test_output,
                )
                if tb_file_match:
                    traceback_file_path = tb_file_match.group(1)
                if tb_error_match:
                    traceback_error_msg = f"{tb_error_match.group(1)}: {tb_error_match.group(2).strip()}"

            # If we found exact traceback info, use it for a targeted patch
            if traceback_file_path:
                sandbox_patch_requests.append(FilePatchRequest(
                    path=traceback_file_path,
                    reason=f"Sandbox runtime error: {traceback_error_msg or 'unknown error'}",
                    instructions=[
                        "Fix the runtime error in this file that prevents the API from starting.",
                        f"Error: {traceback_error_msg or 'See full output below'}",
                        "Make sure all imports are correct — if you use Field, SQLModel, etc., import them explicitly.",
                        f"Sandbox output: {sandbox_report.test_output[:500]}",
                    ],
                ))

            # If health check failed and we didn't find a specific file, also patch main.py
            if not sandbox_report.health_check_ok and traceback_file_path != "app/main.py":
                sandbox_patch_requests.append(FilePatchRequest(
                    path="app/main.py",
                    reason="Sandbox health check failed — API did not start",
                    instructions=[
                        "Fix any import errors, syntax errors, or configuration issues that prevent uvicorn from starting.",
                        f"Sandbox error output: {sandbox_report.test_output[:300]}",
                    ],
                ))

            # If specific tests failed, patch the relevant files
            if sandbox_report.failures:
                failing_files = set()
                for failure_msg in sandbox_report.failures:
                    if "test_" in failure_msg and "::" in failure_msg:
                        continue  # Don't patch test files, patch app files
                    if "app/" in failure_msg:
                        match = _re.search(r'(app/\S+\.py)', failure_msg)
                        if match:
                            failing_files.add(match.group(1))

                for fpath in failing_files:
                    if fpath == traceback_file_path:
                        continue  # Already covered above
                    sandbox_patch_requests.append(FilePatchRequest(
                        path=fpath,
                        reason=f"Sandbox tests failed — {sandbox_report.tests_failed} test(s) failing",
                        instructions=[
                            "Fix issues causing sandbox test failures.",
                            f"Failing tests: {', '.join(sandbox_report.failures[:3])}",
                            f"Test output snippet: {sandbox_report.test_output[:200]}",
                        ],
                    ))

            if not sandbox_patch_requests:
                sandbox_patch_requests.append(FilePatchRequest(
                    path="app/main.py",
                    reason="Sandbox deployment failed",
                    instructions=[
                        "Review and fix the main application entry point.",
                        f"Error: {'; '.join(sandbox_error_summary[:3])}",
                    ],
                ))

            logger.info(
                "Sandbox attempt %s failed; patching %s file(s) and retrying.",
                sandbox_attempt,
                len(sandbox_patch_requests),
            )

            code = await imp_agent.patch_files(
                architecture=architecture,
                current_code=code,
                patch_requests=sandbox_patch_requests,
                review_issue_descriptions_by_file={},
            )

        # 5. Review Loop (Perceive-Plan-Act cycle)
        MAX_REVIEW_ITERATIONS = 5
        REVIEW_TRUST_SCORE_THRESHOLD = 7  # Reuse reviewer security_score as the current trust threshold.
        rev_agent = ReviewerAgent()
        review_artifact_for_completion: dict = {
            "approved": True,
            "issues": [],
            "suggestions": [],
            "security_score": 7,
            "affected_files": [],
            "patch_requests": [],
            "final_code": [f.model_dump() for f in code.files],
        }

        try:
            prev_score: int | None = None
            prev_issues: list = []
            for attempt in range(1, MAX_REVIEW_ITERATIONS + 1):
                yield json.dumps({
                    "status": "reviewer",
                    "message": f"Review pass {attempt}/{MAX_REVIEW_ITERATIONS} - checking code quality and security...",
                    "attempt": attempt,
                    "prev_score": prev_score,
                })

                review = await rev_agent.run(
                    code,
                    previous_score=prev_score,
                    previous_issues=prev_issues or None,
                    sandbox_report=None, # Sandbox report is not available yet
                )
                review_artifact_for_completion = review.model_dump()
                review_artifact_for_completion["final_code"] = [f.model_dump() for f in code.files]

                current_score = review.security_score or 0

                # Save the review artifact for this pass
                create_artifact_record(
                    session=session,
                    artifact_in=ArtifactRecordCreate(
                        run_id=run_id,
                        stage=f"reviewer_pass_{attempt}",
                        content=_compact_review_for_db(
                            run_id=run_id,
                            stage=f"reviewer_pass_{attempt}",
                            review_artifact=review_artifact_for_completion,
                            dependencies=code.dependencies,
                        ),
                    )
                )

                meets_trust_threshold = current_score >= REVIEW_TRUST_SCORE_THRESHOLD
                review_accepted = bool(review.approved) and meets_trust_threshold

                if review_accepted:
                    logger.info(
                        "Code approved on review pass %s (score=%s, threshold=%s)",
                        attempt,
                        current_score,
                        REVIEW_TRUST_SCORE_THRESHOLD,
                    )
                    yield json.dumps({
                        "status": "reviewer_done",
                        "message": (
                            f"Code approved on pass {attempt} "
                            f"(trust score {current_score}/{10})."
                        ),
                        "score": current_score,
                        "artifact": review_artifact_for_completion
                    })
                    break

                if review.approved and not meets_trust_threshold:
                    logger.info(
                        "Review pass %s approved code but score %s is below threshold %s; requesting targeted fixes.",
                        attempt,
                        current_score,
                        REVIEW_TRUST_SCORE_THRESHOLD,
                    )

                if review.final_code:
                    logger.info("Review pass %s returned reviewer rewrites; re-running review.", attempt)
                    code = GeneratedCode(files=review.final_code, dependencies=code.dependencies)
                    review_artifact_for_completion["final_code"] = [f.model_dump() for f in code.files]
                    prev_score = current_score
                    prev_issues = list(review.issues or [])
                    yield json.dumps(
                        {
                            "status": "revision",
                            "message": (
                                f"Pass {attempt}: reviewer provided code fixes; "
                                "re-reviewing updated files..."
                            ),
                            "attempt": attempt,
                            "score": current_score,
                            "prev_score": prev_score,
                            "issues_count": len(review.issues),
                        }
                    )
                    continue

                issue_map: dict[str, list[str]] = {}
                for issue in review.issues or []:
                    path = (issue.file_path or "").strip()
                    if not path:
                        continue
                    desc = f"[{issue.severity}] {issue.description}"
                    issue_map.setdefault(path, []).append(desc)

                affected_from_review = [p for p in (review.affected_files or []) if isinstance(p, str) and p.strip()]
                affected_from_issues = [p for p in issue_map.keys() if p]
                targeted_paths = list(dict.fromkeys(affected_from_review + affected_from_issues))
                patch_requests = list(review.patch_requests or [])

                if not patch_requests and targeted_paths:
                    # Build minimal patch requests from issues/affected files so implementer can patch deterministically.
                    from app.agent.artifacts import (
                        FilePatchRequest,  # local import to avoid circular import surprises
                    )
                    patch_requests = [
                        FilePatchRequest(
                            path=path,
                            reason="Reviewer reported issues in this file",
                            instructions=issue_map.get(path, []) or ["Fix the reviewer-reported issues while preserving existing behavior."],
                        )
                        for path in targeted_paths
                    ]

                # Code not approved - only retry if reviewer returned rewritten code or targeted patch requests.
                if not patch_requests:
                    logger.info(
                        "Review pass %s returned issues but no rewritten code; ending review loop without retry.",
                        attempt,
                    )
                    yield json.dumps({
                        "status": "reviewer_done",
                        "message": f"Review found {len(review.issues)} issue(s); returning generated code without reviewer rewrites.",
                        "score": current_score,
                        "artifact": review_artifact_for_completion
                    })
                    break

                logger.info(
                    "Review pass %s: %s issues found across %s file(s); regenerating affected files.",
                    attempt,
                    len(review.issues),
                    len(patch_requests),
                )
                prev_score = current_score
                prev_issues = list(review.issues or [])
                code = await imp_agent.patch_files(
                    architecture=architecture,
                    current_code=code,
                    patch_requests=patch_requests,
                    review_issue_descriptions_by_file=issue_map,
                )
                review_artifact_for_completion["final_code"] = [f.model_dump() for f in code.files]

                yield json.dumps({
                    "status": "revision",
                    "message": (
                        f"Pass {attempt}: {len(review.issues)} reviewer issue(s) "
                        f"(trust score {current_score}/{10}) - regenerating "
                        "affected files and re-reviewing..."
                    ),
                    "attempt": attempt,
                    "score": current_score,
                    "prev_score": prev_score,
                    "issues_count": len(review.issues),
                    "affected_files": [getattr(req, "path", None) for req in patch_requests if getattr(req, "path", None)],
                })
            else:
                # Exhausted all retries without approval
                logger.warning(f"Code not approved after {MAX_REVIEW_ITERATIONS} review passes")
                yield json.dumps({
                    "status": "reviewer_done",
                    "message": f"Review completed after {MAX_REVIEW_ITERATIONS} passes (some issues may remain).",
                    "score": prev_score,
                    "artifact": review_artifact_for_completion
                })
        except Exception as review_error:
            logger.warning("Reviewer stage failed; continuing with implementer output: %s", review_error)
            review_artifact_for_completion = {
                "approved": False,
                "issues": [],
                "suggestions": [f"Reviewer failed: {review_error}. Returning implementer output."],
                "security_score": 5,
                "final_code": [f.model_dump() for f in code.files],
            }
            yield json.dumps({
                "status": "reviewer_done",
                "message": "Reviewer failed; returning generated code without review approval.",
                "artifact": review_artifact_for_completion
            })

        yield json.dumps({
            "status": "completed",
            "message": "Pipeline finished successfully!",
            "artifact": review_artifact_for_completion,
        })
        _update_run_status_safely(session=session, run_id=run_id, status="completed")

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        _rollback_session_safely(session)
        yield json.dumps({"status": "error", "message": str(e)})
        _update_run_status_safely(session=session, run_id=run_id, status="failed")
