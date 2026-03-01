"""
Evaluation Report Generator
==============================
Reads eval result JSON files and produces a polished markdown report.

Usage:
    cd backend && python -m evals.generate_report
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

RESULTS_PATH = Path(__file__).parent / "results"
REPORT_PATH = Path(__file__).parent / "results"


def find_latest_result(prefix: str) -> dict | None:
    """Find the most recent result file matching a prefix."""
    if not RESULTS_PATH.exists():
        return None
    files = sorted(RESULTS_PATH.glob(f"{prefix}_*.json"), reverse=True)
    if not files:
        return None
    with open(files[0]) as f:
        return json.load(f)


def generate_interface_section(data: dict) -> str:
    """Generate the interface agent eval section."""
    if not data:
        return "### Interface Agent Eval\n\n> ⚠️ No results found. Run `python -m evals.interface_eval` first.\n\n"

    cm = data.get("confusion_matrix", {})
    lines = [
        "## 1. Interface Agent Classification\n",
        "### Metrics\n",
        "| Metric | Value |",
        "|--------|-------|",
        f"| **Accuracy** | {data.get('accuracy', 0):.1%} |",
        f"| **Precision** | {data.get('precision', 0):.1%} |",
        f"| **Recall** | {data.get('recall', 0):.1%} |",
        f"| **F1 Score** | {data.get('f1', 0):.1%} |",
        f"| Prompts tested | {data.get('total_prompts', 0)} |",
        f"| Time | {data.get('elapsed_seconds', 0):.1f}s |",
        "",
        "### Confusion Matrix\n",
        "|  | Predicted: Pipeline | Predicted: Chat |",
        "|--|---:|---:|",
        f"| **Actual: Pipeline** | {cm.get('tp', 0)} (TP) | {cm.get('fn', 0)} (FN) |",
        f"| **Actual: Chat** | {cm.get('fp', 0)} (FP) | {cm.get('tn', 0)} (TN) |",
        "",
        "### Per-Category Accuracy\n",
        "| Category | Accuracy | Correct / Total |",
        "|----------|----------|-----------------|",
    ]

    for cat, stats in data.get("category_accuracy", {}).items():
        acc = stats.get("accuracy", 0)
        lines.append(f"| {cat} | {acc:.0%} | {stats['correct']}/{stats['total']} |")

    # Misclassified examples
    misclassified = data.get("misclassified", [])
    if misclassified:
        lines.append("")
        lines.append("### Misclassified Examples\n")
        lines.append("| Prompt | Expected | Predicted | Category |")
        lines.append("|--------|----------|-----------|----------|")
        for m in misclassified:
            prompt = m.get("prompt", "")[:50]
            lines.append(f"| {prompt} | {m.get('expected')} | {m.get('predicted')} | {m.get('category')} |")

    lines.append("")
    return "\n".join(lines)


def generate_pipeline_section(data: dict) -> str:
    """Generate the pipeline benchmark section."""
    if not data:
        return "## 2. End-to-End Pipeline Benchmark\n\n> ⚠️ No results found. Run `python -m evals.pipeline_benchmark` first.\n\n"

    lines = [
        "## 2. End-to-End Pipeline Benchmark\n",
        "### Aggregate Metrics\n",
        "| Metric | Value |",
        "|--------|-------|",
        f"| **Completion rate** | {data.get('completion_rate', 0):.0%} |",
        f"| **Avg security score** | {data.get('avg_security_score', 0):.1f}/10 |",
        f"| Score range | {data.get('min_security_score', 'N/A')}-{data.get('max_security_score', 'N/A')} |",
        f"| Avg reviewer passes | {data.get('avg_reviewer_passes', 0):.1f} |",
        f"| Sandbox deploy rate | {data.get('sandbox_deploy_rate', 0):.0%} |",
        f"| Sandbox health rate | {data.get('sandbox_health_rate', 0):.0%} |",
        f"| Avg latency | {data.get('avg_latency_seconds', 0):.0f}s |",
        f"| Total benchmarks | {data.get('total_benchmarks', 0)} |",
        "",
        "### Per-Benchmark Results\n",
        "| Benchmark | Complexity | Status | Score | Passes | Sandbox | Latency |",
        "|-----------|------------|--------|-------|--------|---------|---------|",
    ]

    for r in data.get("results", []):
        status = "✅" if r.get("completed") else "❌"
        score = f"{r['final_score']}/10" if r.get("final_score") else "N/A"
        sandbox = "✅" if r.get("sandbox_health_ok") else "❌"
        latency = f"{r.get('latency_seconds', 'N/A')}s"
        lines.append(
            f"| {r['id']} | {r.get('complexity', '?')} | {status} | {score} | "
            f"{r.get('reviewer_passes', 0)} | {sandbox} | {latency} |"
        )

    # Failures
    failures = [r for r in data.get("results", []) if not r.get("completed")]
    if failures:
        lines.append("")
        lines.append("### Failed Benchmarks\n")
        for f in failures:
            lines.append(f"- **{f['id']}**: {f.get('error', 'Unknown error')}")

    lines.append("")
    return "\n".join(lines)


def generate_report() -> str:
    """Generate the full evaluation report."""
    interface_data = find_latest_result("interface_eval")
    pipeline_data = find_latest_result("pipeline_benchmark")

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    report = f"""# Craftlive Evaluation Report

> Generated: {timestamp}

---

{generate_interface_section(interface_data)}

---

{generate_pipeline_section(pipeline_data)}

---

## Methodology

### Interface Agent Eval
- **Dataset**: 50 manually labeled prompts across 10 categories
- **Metric**: Binary classification (should_trigger_pipeline: true/false)
- **Model**: Configured in `.env` as `MODEL_INTERFACE`

### Pipeline Benchmark
- **Dataset**: 5 prompts of increasing complexity (simple → complex)
- **Metrics**: Completion, security score, reviewer passes, sandbox tests, latency
- **Model**: Configured in `.env` as `MODEL_DEFAULT`, `MODEL_IMPLEMENTER`, `MODEL_REVIEWER`
"""
    return report


def main():
    report = generate_report()

    REPORT_PATH.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = REPORT_PATH / f"eval_report_{timestamp}.md"
    out_path.write_text(report, encoding="utf-8")

    # Also write a "latest" symlink-like copy
    latest_path = REPORT_PATH / "eval_report_latest.md"
    latest_path.write_text(report, encoding="utf-8")

    print(f"📄 Report generated: {out_path}")
    print(f"📄 Latest copy:      {latest_path}")
    print(f"\n{report}")


if __name__ == "__main__":
    main()
