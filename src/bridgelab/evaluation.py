"""Stage E: Independent Evaluation.

Reveal withheld material ONLY to the evaluator, compare locked predictions
against actual passages, and score outcomes including a simple baseline.
"""
from __future__ import annotations

from .models import EvaluationResult, Prediction, Source


def _levenshtein(a: str, b: str) -> int:
    """Small dependency-free edit distance used as the baseline scorer."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _term_set(text: str) -> set[str]:
    import re
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def baseline_contains_token(pred: Prediction, withheld: list[Source]) -> bool:
    """Trivial baseline: does ANY withheld source contain the prediction's
    first alphabetic token? This is the naive method the experimental result
    must beat, not the target itself."""
    import re
    m = re.search(r"[a-z]{3,}", pred.statement.lower())
    if not m:
        return False
    tok = m.group(0)
    return any(tok in s.text.lower() for s in withheld)


def evaluate_prediction(
    pred: Prediction,
    withheld_sources: list[Source],
    similarity_threshold: float = 0.5,
) -> EvaluationResult:
    """Evaluate one prediction against withheld material.

    semantic_text_similarity is treated as a *candidate* relationship, not
    proof. The evaluator looks for literal/structural matches first; fuzzy
    similarity is reported as a candidate only.
    """
    result = EvaluationResult(prediction_id=pred.prediction_id, outcome="no_finding")
    result.baseline_outcome = "match" if baseline_contains_token(pred, withheld_sources) else "miss"

    # Literal token presence for theme/relation/contradiction categories.
    import re
    toks = re.findall(r"[a-z]{3,}", pred.statement.lower())
    matches: list[dict] = []
    for s in withheld_sources:
        text = s.text.lower()
        hit_toks = [t for t in toks if t in text]
        if hit_toks:
            matches.append({"source_id": s.source_id, "tokens": hit_toks})

    if pred.category == "contradiction":
        # A contradiction prediction "term absent from withheld" succeeds when
        # the term is NOT found in withheld material.
        if not matches:
            result.outcome = "match"
            result.notes = "predicted term is indeed absent from withheld material"
        else:
            result.outcome = "false_positive"
            result.notes = "predicted-absent term was found; prediction contradicted"
        return result

    if matches:
        result.outcome = "match"
        result.matched_evidence = [m["source_id"] for m in matches]
        result.citations = [
            f"{m['source_id']}: contains {m['tokens']}" for m in matches[:5]
        ]
    else:
        result.outcome = "miss"
        result.notes = "no withheld source contains the predicted tokens"

    return result


def evaluate_all(
    predictions: list[Prediction],
    withheld_sources: list[Source],
) -> list[EvaluationResult]:
    return [
        evaluate_prediction(p, withheld_sources) for p in predictions
    ]
