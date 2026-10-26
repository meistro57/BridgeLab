"""Stage F: Adversarial Review.

A MisfitCrew-style critical pass over a completed experiment. Each check raises
a specific objection with evidence; the pass returns structured notes rather
than a single verdict.
"""
from __future__ import annotations

from typing import Any

_OBJECTIONS = [
    ("source_contamination", "Source contamination: withheld material leaked into the prediction stage?"),
    ("confirmation_bias", "Confirmation bias: the generator only looks for what it already expects?"),
    ("shared_vocabulary", "Shared vocabulary mistaken for conceptual agreement?"),
    ("correlated_sources", "Correlated sources mistaken for independent confirmation?"),
    ("causal_inference", "Unsupported causal inferences?"),
    ("overconfidence", "Overconfident conclusions relative to evidence quality?"),
]


def review(
    report: dict[str, Any],
    visible_ids: list[str],
    withheld_ids: list[str],
) -> list[str]:
    notes: list[str] = []

    pred_sources = set(report["locked_predictions"].get("source_ids", []) or [])
    if pred_sources & set(withheld_ids):
        notes.append(_OBJECTIONS[0][1] + "  <-- DETECTED: prediction used withheld source ids")
    else:
        notes.append(_OBJECTIONS[0][1] + "  (ok: no id overlap)")

    notes.append(_OBJECTIONS[1][1] + "  (risk: token-frequency generator is self-confirming by design)")

    notes.append(_OBJECTIONS[2][1] + "  (risk: token presence != conceptual agreement; reported as a limitation)")

    notes.append(_OBJECTIONS[3][1] + "  (risk: family-based split cannot guarantee source independence)")

    notes.append(_OBJECTIONS[4][1] + "  (none claimed; non-causal by construction)")

    preds = report["locked_predictions"]["predictions"]
    max_conf = max((p.get("confidence") or 0.0) for p in preds) if preds else 0.0
    if max_conf > 0.7:
        notes.append(_OBJECTIONS[5][1] + f"  <-- DETECTED: a prediction carries confidence {max_conf}")
    else:
        notes.append(_OBJECTIONS[5][1] + "  (ok: calibrations conservative)")

    return notes
