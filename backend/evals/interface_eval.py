"""
Interface Agent Classification Eval
====================================
Runs the InterfaceAgent on a labeled dataset and computes:
- Precision, Recall, F1 for `should_trigger_pipeline`
- Per-category accuracy breakdown
- Confusion matrix

Usage:
    cd backend && python -m evals.interface_eval
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

# Ensure the backend app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.interface import InterfaceAgent  # noqa: E402


DATASET_PATH = Path(__file__).parent / "datasets" / "interface_prompts.json"
RESULTS_PATH = Path(__file__).parent / "results"


async def run_eval() -> dict:
    """Run the InterfaceAgent on every labeled prompt and collect results."""

    with open(DATASET_PATH) as f:
        dataset = json.load(f)

    agent = InterfaceAgent()
    results = []
    start_time = time.time()

    for i, item in enumerate(dataset):
        prompt = item["prompt"]
        expected = item["label"]
        category = item.get("category", "unknown")

        print(f"  [{i+1}/{len(dataset)}] \"{prompt[:50]}...\" ", end="", flush=True)

        try:
            decision = await agent.run(prompt)
            predicted = decision.should_trigger_pipeline
            correct = predicted == expected
            print(f"{'✅' if correct else '❌'} (predicted={predicted}, expected={expected})")

            results.append({
                "prompt": prompt,
                "category": category,
                "expected": expected,
                "predicted": predicted,
                "correct": correct,
                "intent": decision.intent,
                "action_type": decision.action_type,
                "reply_preview": decision.assistant_reply[:80] if decision.assistant_reply else "",
            })
        except Exception as exc:
            print(f"💥 ERROR: {exc}")
            results.append({
                "prompt": prompt,
                "category": category,
                "expected": expected,
                "predicted": None,
                "correct": False,
                "error": str(exc),
            })

    elapsed = time.time() - start_time

    # Compute metrics
    tp = sum(1 for r in results if r["expected"] is True and r.get("predicted") is True)
    fp = sum(1 for r in results if r["expected"] is False and r.get("predicted") is True)
    tn = sum(1 for r in results if r["expected"] is False and r.get("predicted") is False)
    fn = sum(1 for r in results if r["expected"] is True and r.get("predicted") is False)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (tp + tn) / len(results) if results else 0

    # Per-category breakdown
    category_stats: dict[str, dict] = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in results:
        cat = r["category"]
        category_stats[cat]["total"] += 1
        if r["correct"]:
            category_stats[cat]["correct"] += 1

    category_accuracy = {
        cat: {
            "total": stats["total"],
            "correct": stats["correct"],
            "accuracy": stats["correct"] / stats["total"] if stats["total"] > 0 else 0,
        }
        for cat, stats in sorted(category_stats.items())
    }

    # Misclassified examples
    misclassified = [r for r in results if not r["correct"]]

    summary = {
        "total_prompts": len(results),
        "elapsed_seconds": round(elapsed, 2),
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "category_accuracy": category_accuracy,
        "misclassified": misclassified,
        "all_results": results,
    }

    return summary


def print_report(summary: dict) -> None:
    """Pretty-print the eval results."""
    print("\n" + "=" * 60)
    print("  INTERFACE AGENT CLASSIFICATION EVAL")
    print("=" * 60)

    cm = summary["confusion_matrix"]
    print(f"\n📊 Confusion Matrix:")
    print(f"                  Predicted Pipeline  Predicted Chat")
    print(f"  Actual Pipeline       {cm['tp']:>4}              {cm['fn']:>4}")
    print(f"  Actual Chat           {cm['fp']:>4}              {cm['tn']:>4}")

    print(f"\n📈 Metrics:")
    print(f"  Accuracy:   {summary['accuracy']:.1%}")
    print(f"  Precision:  {summary['precision']:.1%}")
    print(f"  Recall:     {summary['recall']:.1%}")
    print(f"  F1 Score:   {summary['f1']:.1%}")
    print(f"  Time:       {summary['elapsed_seconds']:.1f}s")

    print(f"\n📋 Per-Category Accuracy:")
    for cat, stats in summary["category_accuracy"].items():
        bar = "█" * int(stats["accuracy"] * 10) + "░" * (10 - int(stats["accuracy"] * 10))
        print(f"  {cat:<25} {bar} {stats['accuracy']:.0%} ({stats['correct']}/{stats['total']})")

    if summary["misclassified"]:
        print(f"\n❌ Misclassified ({len(summary['misclassified'])}):")
        for m in summary["misclassified"]:
            print(f"  - \"{m['prompt'][:60]}\" → predicted={m.get('predicted')}, expected={m['expected']} [{m['category']}]")

    print("\n" + "=" * 60)


def save_results(summary: dict) -> Path:
    """Save results to JSON."""
    RESULTS_PATH.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_PATH / f"interface_eval_{timestamp}.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n💾 Results saved to: {out_path}")
    return out_path


def main():
    print("🧪 Running Interface Agent Classification Eval...")
    print(f"   Dataset: {DATASET_PATH}")
    summary = asyncio.run(run_eval())
    print_report(summary)
    save_results(summary)


if __name__ == "__main__":
    main()
