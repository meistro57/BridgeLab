"""Stage G: Experimental Reports.

Produce readable Markdown and machine-readable JSON reports. Unsuccessful
experiments are preserved, never hidden.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import (
    EvaluationResult,
    LockedPredictions,
    Prediction,
    SplitManifest,
)


def compute_metrics(results: list[EvaluationResult]) -> dict[str, Any]:
    n = len(results)
    matches = sum(1 for r in results if r.outcome == "match")
    false_pos = sum(1 for r in results if r.outcome == "false_positive")
    missed = sum(1 for r in results if r.outcome == "miss")
    no_finding = sum(1 for r in results if r.outcome == "no_finding")
    baseline_matches = sum(1 for r in results if r.baseline_outcome == "match")
    precision = (matches / (matches + false_pos)) if (matches + false_pos) else 0.0
    recall = (matches / n) if n else 0.0
    baseline_precision = (baseline_matches / n) if n else 0.0
    return {
        "total_predictions": n,
        "matches": matches,
        "false_positives": false_pos,
        "missed": missed,
        "no_finding": no_finding,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "baseline_matches": baseline_matches,
        "baseline_precision": round(baseline_precision, 4),
    }


def build_report(
    experiment_id: str,
    split: SplitManifest,
    locked: LockedPredictions,
    results: list[EvaluationResult],
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
        "adversarial_review": adversarial_notes,
        "limitations": [
            "Single-token proxies are weak semantic signals.",
            "Semantic similarity is a candidate relationship, not proof.",
            "ABSENCE of a term is not evidence of conceptual absence.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    m = report["metrics"]
    out = []
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
    out.append("| ID | Category | Statement | Outcome |")
    out.append("|---|---|---|---|")
    preds = {p["prediction_id"]: p for p in report["locked_predictions"]["predictions"]}
    for r in report["evaluation"]:
        stmt = preds[r["prediction_id"]]["statement"]
        out.append("| %s | %s | %s | **%s** |" % (r["prediction_id"], preds[r["prediction_id"]]["category"], stmt, r["outcome"]))
    out.append("")
    out.append("## Results vs Baseline")
    out.append("- Experimental precision: **%s** (%d match / %d false-pos / %d missed)" % (m["precision"], m["matches"], m["false_positives"], m["missed"]))
    out.append("- Baseline precision: **%s** (%d naive matches)" % (m["baseline_precision"], m["baseline_matches"]))
    out.append("")
    out.append("## Adversarial Review")
    for note in report["adversarial_review"]:
        out.append("- " + note)
    out.append("")
    out.append("## Limitations")
    for note in report["limitations"]:
        out.append("- " + note)
    return "\n".join(out)
