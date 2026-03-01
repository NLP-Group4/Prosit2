"""
End-to-End Pipeline Benchmark
================================
Runs the full orchestrator pipeline on benchmark prompts and collects
performance metrics: completion rate, reviewer passes, security scores,
sandbox success, and latency.

Usage:
    cd backend && python -m evals.pipeline_benchmark

Requires:
    - Database connection (uses the same DB as the backend)
    - LLM API keys configured in .env
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.agent.orchestrator import Orchestrator  # noqa: E402
from app.models import (  # noqa: E402
    Project,
    ProjectCreate,
    User,
    UserCreate,
    GenerationRunCreate,
)
from app.crud import create_project, create_user, create_generation_run  # noqa: E402

DATASET_PATH = Path(__file__).parent / "datasets" / "benchmark_prompts.json"
RESULTS_PATH = Path(__file__).parent / "results"


def _get_or_create_eval_user(session: Session) -> User:
    """Get or create a dedicated user for evals."""
    from sqlmodel import select
    stmt = select(User).where(User.email == "eval@craftlive.test")
    user = session.exec(stmt).first()
    if not user:
        user = create_user(session, UserCreate(
            email="eval@craftlive.test",
            full_name="Eval Runner",
            password="eval-runner-password-not-real",
        ))
    return user


async def run_single_benchmark(prompt_data: dict, session: Session, user: User) -> dict:
    """Run a single benchmark prompt through the full pipeline."""
    prompt_id = prompt_data["id"]
    prompt = prompt_data["prompt"]
    complexity = prompt_data.get("complexity", "unknown")

    print(f"\n{'='*60}")
    print(f"  Benchmark: {prompt_id} ({complexity})")
    print(f"  Prompt: {prompt[:80]}...")
    print(f"{'='*60}")

    # Create a project for this eval run
    project = create_project(session, ProjectCreate(
        name=f"eval_{prompt_id}_{int(time.time())}",
        description=f"Eval benchmark: {prompt_id}",
    ), owner_id=user.id)
    session.commit()

    run = create_generation_run(session, GenerationRunCreate(
        project_id=project.id,
        prompt=prompt,
    ))
    session.commit()

    orchestrator = Orchestrator()
    result = {
        "id": prompt_id,
        "prompt": prompt,
        "complexity": complexity,
        "completed": False,
        "error": None,
        "reviewer_passes": 0,
        "final_score": None,
        "sandbox_deployed": None,
        "sandbox_health_ok": None,
        "sandbox_tests_passed": None,
        "sandbox_tests_failed": None,
        "sandbox_tests_total": None,
        "deterministic_tests_passed": None,
        "latency_seconds": None,
        "stages_reached": [],
    }

    start_time = time.time()

    try:
        async for event_str in orchestrator.run_pipeline(
            session=session,
            project_id=project.id,
            run_id=run.id,
            prompt=prompt,
        ):
            try:
                event = json.loads(event_str)
            except json.JSONDecodeError:
                continue

            status = event.get("status", "")
            result["stages_reached"].append(status)

            # Track metrics from events
            if status == "testing_done":
                result["deterministic_tests_passed"] = event.get("passed")

            elif status == "sandbox_deploy_done":
                artifact = event.get("artifact", {})
                if artifact:
                    result["sandbox_deployed"] = artifact.get("deployed")
                    result["sandbox_health_ok"] = artifact.get("health_check_ok")
                    result["sandbox_tests_passed"] = artifact.get("tests_passed")
                    result["sandbox_tests_failed"] = artifact.get("tests_failed")
                    result["sandbox_tests_total"] = artifact.get("tests_total")

            elif status == "reviewer":
                result["reviewer_passes"] += 1

            elif status == "reviewer_done":
                result["final_score"] = event.get("score")

            elif status == "completed":
                result["completed"] = True

            # Print progress
            msg = event.get("message", status)
            print(f"  [{status}] {msg[:80]}")

    except Exception as exc:
        result["error"] = str(exc)
        print(f"  💥 ERROR: {exc}")

    result["latency_seconds"] = round(time.time() - start_time, 2)

    # Print result summary
    print(f"\n  Result: {'✅ Completed' if result['completed'] else '❌ Failed'}")
    print(f"  Score: {result['final_score']}/10")
    print(f"  Reviewer passes: {result['reviewer_passes']}")
    print(f"  Sandbox: deployed={result['sandbox_deployed']}, tests={result['sandbox_tests_passed']}/{result['sandbox_tests_total']}")
    print(f"  Latency: {result['latency_seconds']}s")

    return result


async def run_all_benchmarks() -> dict:
    """Run all benchmark prompts and collect results."""
    with open(DATASET_PATH) as f:
        prompts = json.load(f)

    all_results = []
    total_start = time.time()

    with Session(engine) as session:
        user = _get_or_create_eval_user(session)
        session.commit()

        for prompt_data in prompts:
            result = await run_single_benchmark(prompt_data, session, user)
            all_results.append(result)

    total_elapsed = time.time() - total_start

    # Compute aggregate metrics
    completed = [r for r in all_results if r["completed"]]
    scores = [r["final_score"] for r in all_results if r["final_score"] is not None]
    sandbox_deployed = [r for r in all_results if r.get("sandbox_deployed") is True]
    sandbox_healthy = [r for r in all_results if r.get("sandbox_health_ok") is True]

    summary = {
        "total_benchmarks": len(all_results),
        "total_elapsed_seconds": round(total_elapsed, 2),
        "completion_rate": len(completed) / len(all_results) if all_results else 0,
        "avg_reviewer_passes": (
            sum(r["reviewer_passes"] for r in all_results) / len(all_results)
            if all_results else 0
        ),
        "avg_security_score": sum(scores) / len(scores) if scores else 0,
        "min_security_score": min(scores) if scores else None,
        "max_security_score": max(scores) if scores else None,
        "sandbox_deploy_rate": len(sandbox_deployed) / len(all_results) if all_results else 0,
        "sandbox_health_rate": len(sandbox_healthy) / len(all_results) if all_results else 0,
        "avg_latency_seconds": (
            sum(r["latency_seconds"] for r in all_results if r["latency_seconds"]) / len(all_results)
            if all_results else 0
        ),
        "results": all_results,
    }

    return summary


def print_summary(summary: dict) -> None:
    """Pretty-print the aggregate benchmark results."""
    print("\n" + "=" * 60)
    print("  END-TO-END PIPELINE BENCHMARK RESULTS")
    print("=" * 60)

    print(f"\n📊 Aggregate Metrics:")
    print(f"  Benchmarks:         {summary['total_benchmarks']}")
    print(f"  Completion rate:    {summary['completion_rate']:.0%}")
    print(f"  Avg reviewer passes:{summary['avg_reviewer_passes']:.1f}")
    print(f"  Avg security score: {summary['avg_security_score']:.1f}/10")
    print(f"  Score range:        {summary['min_security_score']}-{summary['max_security_score']}")
    print(f"  Sandbox deploy:     {summary['sandbox_deploy_rate']:.0%}")
    print(f"  Sandbox health:     {summary['sandbox_health_rate']:.0%}")
    print(f"  Avg latency:        {summary['avg_latency_seconds']:.0f}s")
    print(f"  Total time:         {summary['total_elapsed_seconds']:.0f}s")

    print(f"\n📋 Per-Benchmark Results:")
    print(f"  {'ID':<20} {'Status':<10} {'Score':<8} {'Passes':<8} {'Sandbox':<10} {'Time'}")
    print(f"  {'-'*18}   {'-'*8}  {'-'*6}  {'-'*6}  {'-'*8}  {'-'*6}")
    for r in summary["results"]:
        status = "✅" if r["completed"] else "❌"
        score = f"{r['final_score']}/10" if r["final_score"] else "N/A"
        sandbox = "✅" if r.get("sandbox_health_ok") else "❌"
        print(f"  {r['id']:<20} {status:<10} {score:<8} {r['reviewer_passes']:<8} {sandbox:<10} {r['latency_seconds']}s")

    print("\n" + "=" * 60)


def save_results(summary: dict) -> Path:
    """Save results to JSON."""
    RESULTS_PATH.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_PATH / f"pipeline_benchmark_{timestamp}.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n💾 Results saved to: {out_path}")
    return out_path


def main():
    print("🧪 Running End-to-End Pipeline Benchmark...")
    print(f"   Dataset: {DATASET_PATH}")
    summary = asyncio.run(run_all_benchmarks())
    print_summary(summary)
    save_results(summary)


if __name__ == "__main__":
    main()
