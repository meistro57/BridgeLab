"""Stage G: Experimental Reports.

Markdown + JSON reports with honestly-named metrics. Unsuccessful
experiments are preserved, never hidden.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import EvaluationResult, LockedPredictions, Prediction, SplitManifest


def compute_metrics(results: list[EvaluationResult]) -> dict[str, Any]:
    """Honest metrics.

    Precision/recall require gold labels and a TP/FP/FN/TN contingency table;
    this evaluator does not define gold opportunities, so we report hit rate,
    coverage, abstentions and the outcome distribution instead, and we do NOT
    fabricate standard precision/recall numbers.
    """
    n = len(results)
    hits = sum(1 for r in results if r.outcome == "hit")
    misses = sum(1 for r in results if r.outcome == "miss")
    review = sum(1 for r in results if r.outcome == "requires_review")
    not_eval = sum(1 for r in results if r.outcome == "not_evaluable")
    evaluated = hits + misses
    return {
        "total_predictions": n,
        "hit_rate": round(hits / n, 4) if n else 0.0,
        "coverage": round(evaluated / n, 4) if n else 0.0,
        "abstentions": review + not_eval,
        "hits": hits,
        "misses": misses,
        "requires_review": review,
        "not_evaluable": not_eval,
    }


def _baseline_metrics(baseline: list[EvaluationResult], n_experimental: int) -> dict[str, Any]:
    b_hits = sum(1 for r in baseline if r.outcome == "hit")
    return {
        "baseline_predictions": len(baseline),
        "baseline_hits": b_hits,
        "baseline_hit_rate": round(b_hits / len(baseline), 4) if baseline else 0.0,
    }


def build_report(
    experiment_id: str,
    split: SplitManifest,
    locked: LockedPredictions,
    results: list[EvaluationResult],
    baseline: list[EvaluationResult],
    sources: list,
    adversarial_notes: list[str],
) -> dict[str, Any]:
    return {
        "experiment_id": experiment_id,
        "dataset_inventory": {
            "total_sources": len(sources),
            "visible": len(split.visible_ids),
            "withheld": len(split.withheld_ids),
            "dataset_hash": split.dataset_hash,
        },
        "split": asdict(split),
        "locked_predictions": {
            "manifest_hash": locked.prediction_manifest_hash,
            "split_digest": locked.split_digest,
            "model_name": locked.model_name,
            "code_version": locked.code_version,
            "predictions": [asdict(p) for p in locked.predictions],
        },
        "evaluation": [asdict(r) for r in results],
        "metrics": compute_metrics(results),
        "baseline": _baseline_metrics(baseline, len(results)),
        "adversarial_review": adversarial_notes,
        "limitations": [
            "Token presence is not conceptual agreement.",
            "HIT RATE is not precision: no gold-positive/negative labels are defined.",
            "Term_absent is scored as absence, never as a claim contradiction.",
            "Semantic similarity/contradiction is routed to human review, not auto-judged.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    m = report["metrics"]
    b = report["baseline"]
    out: list[str] = []
    out.append("# BridgeLab Experiment — " + report["experiment_id"])
    out.append("")
    out.append("## Dataset & Split")
    inv = report["dataset_inventory"]
    out.append("- Sources: %d (visible %d / withheld %d)" % (inv["total_sources"], inv["visible"], inv["withheld"]))
    out.append("- Dataset hash: `%s…`" % inv["dataset_hash"][:16])
    out.append("- Split digest: `%s…`" % report["locked_predictions"]["split_digest"][:16])
    out.append("") 
    out.append("## Locked Predictions")
    out.append("- Manifest hash: `%s…`" % report["locked_predictions"]["manifest_hash"][:16])
    out.append("- Model: `%s` (code `%s`)" % (report["locked_predictions"]["model_name"], report["locked_predictions"]["code_version"]))
    out.append("")
    out.append("| ID | Category | Statement | Outcome | Evidence |")
    out.append("|---|---|---|---|---|")
    preds = {p["prediction_id"]: p for p in report["locked_predictions"]["predictions"]}
    for r in report["evaluation"]:
        stmt = preds[r["prediction_id"]]["statement"]
        ev = "; ".join(r["evidence"]) if r["evidence"] else (r["notes"] or "-")
        out.append("| %s | %s | %s | **%s** | %s |" % (r["prediction_id"], preds[r["prediction_id"]]["category"], stmt, r["outcome"], ev))
    out.append("")
    out.append("## Results vs Baseline (like-for-like)")
    out.append("- Experimental hit rate: **%s** (%d/%d hits)" % (m["hit_rate"], m["hits"], m["total_predictions"]))
    out.append("- Baseline hit rate: **%s** (%d/%d hits)" % (b["baseline_hit_rate"], b["baseline_hits"], b["baseline_predictions"]))
    out.append("- Coverage: **%s** | Abstentions (review+not_evaluable): **%d**" % (m["coverage"], m["abstentions"]))
    out.append("")
    out.append("### Honest metric note")
    out.append("`hit_rate` and `coverage` are reported because precision/recall require a labelled gold set which this corpus does not define. They are not silent stand-ins for precision/recall.")
    out.append("")
    out.append("## Adversarial Review")
    for note in report["adversarial_review"]:
        out.append("- " + note)
    out.append("")
    out.append("## Limitations")
    for note in report["limitations"]:
        out.append("- " + note)
    return "\n".join(out)
