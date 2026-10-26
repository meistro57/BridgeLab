"""Stage E: Independent Evaluation.

Applies each prediction's machine-testable ``target`` predicate to the
withheld material. Token matching respects word boundaries; absence and
co-occurrence are tested as *predicates*, not prose re-parsing. Semantic
inference is routed to ``requires_review`` rather than fabricated as a match.
"""
from __future__ import annotations

import re

from .models import EvaluationResult, Prediction, Source

_TOKEN_RE = re.compile(r"[a-z0-9]{2,}")


def _token_set(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _contains_term(text: str, term: str) -> bool:
    """Respect word boundaries: 'decoherence' matches 'decoherence' but not
    'nondecoherence-boundary' (substring-only would). We use a token set with
    a normalised term so punctuation/plural suffixes are tolerated but
    arbitrary substrings are not."""
    term_norm = _TERM_NORM(term)
    for tok in _TOKEN_RE.findall(text.lower()):
        if _TERM_NORM(tok) == term_norm:
            return True
    return False


def _TERM_NORM(s: str) -> str:
    # naive lemmatisation: strip a trailing plural 's' to allow token/terms.
    return s.rstrip("s") if s.endswith("s") else s


def _match_theme(pred: Prediction, withheld: list[Source]) -> EvaluationResult:
    term = pred.target.get("term", "")
    hits = [s for s in withheld if _contains_term(s.text, term)]
    res = EvaluationResult(
        prediction_id=pred.prediction_id,
        outcome="hit" if hits else "miss",
        matched_document_ids=[s.source_id for s in hits],
        target=dict(pred.target),
    )
    if hits:
        res.evidence = [f"{s.source_id}: term {term!r} present" for s in hits]
    else:
        res.notes = f"term {term!r} not present in any withheld source"
    return res


def _match_cooccurrence(pred: Prediction, withheld: list[Source]) -> EvaluationResult:
    a = pred.target.get("term_a", "")
    b = pred.target.get("term_b", "")
    same_doc = pred.target.get("same_document", True)
    hits = []
    for s in withheld:
        has_a = _contains_term(s.text, a)
        has_b = _contains_term(s.text, b)
        if same_doc:
            if has_a and has_b:
                hits.append(s)
        else:
            if has_a or has_b:
                hits.append(s)
    res = EvaluationResult(
        prediction_id=pred.prediction_id,
        outcome="hit" if hits else "miss",
        matched_document_ids=[s.source_id for s in hits],
        target=dict(pred.target),
    )
    if hits:
        res.evidence = [f"{s.source_id}: {a!r} and {b!r} co-occur in same doc" for s in hits]
    else:
        res.notes = f"{a!r} and {b!r} did not co-occur in any single withheld doc"
    return res


def _match_absent(pred: Prediction, withheld: list[Source]) -> EvaluationResult:
    term = pred.target.get("term", "")
    present = [s for s in withheld if _contains_term(s.text, term)]
    res = EvaluationResult(
        prediction_id=pred.prediction_id,
        outcome="miss" if present else "hit",
        matched_document_ids=[s.source_id for s in present],
        target=dict(pred.target),
    )
    if present:
        res.evidence = [f"{s.source_id}: term {term!r} unexpectedly present (absence missed)" for s in present]
    else:
        res.notes = f"term {term!r} confirmed absent from all withheld sources (NOT a contradiction finding)"
    return res


def evaluate_prediction(pred: Prediction, withheld: list[Source]) -> EvaluationResult:
    kind = pred.target.get("kind", pred.category)
    if kind == "theme_present":
        return _match_theme(pred, withheld)
    if kind == "cooccurrence":
        return _match_cooccurrence(pred, withheld)
    if kind == "term_absent":
        return _match_absent(pred, withheld)
    if kind in ("requires_review", "contradiction", "similarity"):
        return EvaluationResult(
            prediction_id=pred.prediction_id,
            outcome="requires_review",
            target=dict(pred.target),
            notes="semantic inference cannot be resolved by token matching; flagged for human review",
        )
    return EvaluationResult(
        prediction_id=pred.prediction_id,
        outcome="not_evaluable",
        target=dict(pred.target),
        notes=f"unknown target kind {kind!r}",
    )


def evaluate_all(predictions: list[Prediction], withheld: list[Source]) -> list[EvaluationResult]:
    return [evaluate_prediction(p, withheld) for p in predictions]


def baseline_predictions(visible_sources: list[Source], withheld: list[Source]) -> list[EvaluationResult]:
    """A comparable naive baseline trained on visible material only, evaluated
    by the SAME predicates and target definitions as the experiment.

    The baseline predicts theme_present for the single most frequent visible
    term. It is intentionally simple so any improvement the structured
    generator shows is a fair, like-for-like comparison.
    """
    from .generation import _top_terms
    terms = _top_terms(visible_sources, top_n=3)
    if not terms:
        return []
    pred = Prediction(
        prediction_id="baseline-001",
        category="theme_present",
        statement=f"most frequent visible term {terms[0]!r} recurs in withheld material (naive baseline)",
        target={"kind": "theme_present", "term": terms[0]},
    )
    return [evaluate_prediction(pred, withheld)]
