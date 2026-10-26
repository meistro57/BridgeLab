"""Stage F: Adversarial Review.

A MisfitCrew-style critical pass over a completed experiment. Each reviewer
raises a specific objection with evidence, and the pass returns structured
notes rather than a single verdict.
"""
from __future__ import annotations

from typing import Any

# The objections we always check, in priority order.
_OBJECTIONS = [
    ("source_contamination", "Source contamination: did withheld material leak into the prediction stage?"),
    ("confirmation_bias", "Confirmation bias: does the generator only look for what it already expects?"),
    ("shared_vocabulary", "Shared vocabulary mistaken for conceptual agreement."),
    ("correlated_sources", "Correlated sources mistaken for independent confirmation."),
    ("causal_inference", "Unsupported causal inferences."),
    ("overconfidence", "Overconfident conclusions relative to the evidence quality."),
]


def review(
    report: dict[str, Any],
    visible_ids: list[str],
    withheld_ids: list[str],
) -> list[str]:
    """Return a list of adversarial notes (strings), one per raised objection."""
    notes: list[str] = []

    # 1. Source contamination — is there any overlap between prediction source ids and withheld ids?
    pred_sources = set(report["locked_predictions"].get("source_ids", []) or [])
    if pred_sources & set(withheld_ids):
        notes.append(_OBJECTIONS[0][1] + "  <-- DETECTED: prediction used withheld source ids")
    else:
        notes.append(_OBJECTIONS[0][1] + "  (ok: no id overlap)")

    # 2. Confirmation bias — the heuristic generator only emits terms it already measured.
    notes.append(_OBJECTIONS[1][1] + "  (risk: token-frequency generator is self-confirming by design)")

    # 3. Shared vocabulary — single tokens are a weak proxy for conceptual agreement.
    notes.append(_OBJECTIONS[2][1] + "  (risk: token match != agreement)")

    # 4. Correlated sources — flag if visible families are very few (low independence).
    # (families are not exposed in the report directly; note the structural risk.)
    notes.append(_OBJECTIONS[3][1] + "  (risk: family-based split cannot guarantee source independence)")

    # 5. Causal inference — the generator makes no causal claims; note absence as a limitation.
    notes.append(_OBJECTIONS[4][1] + "  (none claimed; non-causal by construction)")

    # 6. Overconfidence — every prediction carries a confidence <= 0.5 by default.
    max_conf = max((p.get("confidence") or 0.0) for p in report["locked_predictions"]["predictions"])         if report["locked_predictions"]["predictions"] else 0.0
    if max_conf > 0.7:
        notes.append(_OBJECTIONS[5][1] + f"  <-- DETECTED: a prediction carries confidence {max_conf}")
    else:
        notes.append(_OBJECTIONS[5][1] + "  (ok: calibrations conservative)")

    return notes
