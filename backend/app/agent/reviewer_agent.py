from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from app.agent.artifacts import GeneratedCode, Issue, ReviewReport
from app.agent.base import BaseAgent
from app.agent.prompts.reviewer import REVIEWER_SYSTEM_PROMPT
from app.core.config import settings

if TYPE_CHECKING:
    from app.agent.artifacts import SandboxTestReport


class ReviewerAgent(BaseAgent[GeneratedCode, ReviewReport]):
    """
    Agent responsible for reviewing and fixing generated code logic and security.
    """

    def __init__(self):
        super().__init__(model_name=settings.MODEL_REVIEWER)

    async def run(
        self,
        input_data: GeneratedCode,
        *,
        previous_score: int | None = None,
        previous_issues: Sequence[Issue] | None = None,
        sandbox_report: SandboxTestReport | None = None,
    ) -> ReviewReport:
        """
        Processes the GeneratedCode and returns a ReviewReport artifact.

        On retry passes, pass `previous_score` and `previous_issues` to enable
        delta reviewing (score can only improve, issues must be new or unresolved).

        If `sandbox_report` is provided, test results are included so the reviewer
        can base its score on actual runtime evidence.
        """
        prompt = "Files to Review:\n"
        for code_file in input_data.files:
            prompt += f"\n--- {code_file.path} ---\n{code_file.content}\n"

        if sandbox_report is not None:
            prompt += "\n\n---\n## Sandbox Test Results\n"
            prompt += f"- Deployed: {'✅' if sandbox_report.deployed else '❌'}\n"
            prompt += f"- Health check: {'✅' if sandbox_report.health_check_ok else '❌'}\n"
            if sandbox_report.tests_total > 0:
                prompt += f"- Tests: {sandbox_report.tests_passed}/{sandbox_report.tests_total} passed, {sandbox_report.tests_failed} failed\n"
                if sandbox_report.failures:
                    prompt += "\nFailed tests:\n"
                    for f in sandbox_report.failures[:10]:
                        prompt += f"  - {f}\n"
                if sandbox_report.test_output:
                    prompt += f"\nPytest output (truncated):\n```\n{sandbox_report.test_output[:1000]}\n```\n"
            prompt += "\nWeight these real test results heavily in your security_score.\n"
            prompt += "If all tests pass and no critical security issues exist, approve with score >= 8.\n"

        if previous_score is not None:
            prompt += f"\n\n---\nThis is a RE-REVIEW after targeted fixes.\n"
            prompt += f"Previous security score: {previous_score}/10.\n"
            prompt += "Your new score MUST be >= the previous score (scores only improve on retry).\n"
            if previous_issues:
                issues_summary = "\n".join(
                    f"- [{i.severity}] {i.file_path}: {i.description}"
                    for i in previous_issues
                    if i.file_path and i.description
                )
                if issues_summary:
                    prompt += f"\nIssues that were flagged previously (only re-flag if still present and unresolved):\n{issues_summary}\n"

        review_report = await self.llm.generate_structured(
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            user_prompt=prompt,
            response_schema=ReviewReport,
            task_name="Reviewer",
        )

        # Score floor: never allow regression below previous score
        if previous_score is not None and (review_report.security_score or 0) < previous_score:
            review_report = review_report.model_copy(
                update={"security_score": previous_score}
            )

        return review_report

