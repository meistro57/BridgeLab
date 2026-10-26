"""Stages C & D: Hypothesis Generation and Prediction Locking.

Predictions are generated from *visible* material only, then locked with an
immutable manifest and SHA-256 digest before any withheld material is revealed.
"""
from __future__ import annotations

from .models import (
    LockedPredictions,
    Prediction,
    Source,
    SplitManifest,
    _now,
    _sha256,
)


def generate_predictions(
    visible_sources: list[Source],
    experiment_id: str,
    model_name: str,
    prompt: str,
    parameters: dict | None = None,
) -> list[Prediction]:
    """Generate structured predictions from visible material alone.

    The default heuristic generator extracts recurring concept terms and emits
    typed predictions (themes, relations, contradictions, similarities,
    absences). It is deliberately simple and deterministic so the offline demo
    has no hidden LLM dependency; production adapters may replace it with a
    real model while keeping the same Prediction shape.
    """
    params = dict(parameters or {})
    terms = _top_terms(visible_sources, top_n=params.get("top_n", 12))
    preds: list[Prediction] = []
    idx = 0

    # themes: predicted to recur in withheld material
    for term in terms[:6]:
        idx += 1
        preds.append(Prediction(
            prediction_id=f"{experiment_id}-p{idx:03d}",
            category="theme",
            statement=f"Concept '{term}' recurs across the withheld material.",
            supporting_evidence=_evidence_summary(visible_sources, term),
            test_criteria=f"the exact token '{term}' (case-insensitive) appears in a withheld source",
            uncertainty="single-token proxy; may over-fit shared vocabulary",
            confidence=0.5,
        ))

    # relation: co-occurring pair
    if len(terms) >= 2:
        idx += 1
        preds.append(Prediction(
            prediction_id=f"{experiment_id}-p{idx:03d}",
            category="relation",
            statement=f"'{terms[0]}' and '{terms[1]}' co-occur in the same withheld source.",
            supporting_evidence=_cooccurrence_summary(visible_sources, terms[0], terms[1]),
            test_criteria=f"both '{terms[0]}' and '{terms[1]}' appear in one withheld source",
            uncertainty="co-occurrence is not causation or even conceptual relation",
            confidence=0.4,
        ))

    # contradiction: predicted absence of a rare term
    idx += 1
    preds.append(Prediction(
        prediction_id=f"{experiment_id}-p{idx:03d}",
        category="contradiction",
        statement="A term frequent in visible material is absent from the withheld material.",
        supporting_evidence=["visible term-frequency scan"],
        test_criteria="a top visible term is missing from all withheld sources",
        uncertainty="absence may be an artifact of the split, not a real signal",
        confidence=0.3,
    ))

    return preds


def lock_predictions(
    experiment_id: str,
    predictions: list[Prediction],
    split: SplitManifest,
    model_name: str,
    prompt: str,
    parameters: dict | None,
    code_version: str,
) -> LockedPredictions:
    """Lock predictions with an immutable manifest + digest."""
    locked = LockedPredictions(
        experiment_id=experiment_id,
        created_at=_now(),
        predictions=predictions,
        model_name=model_name,
        prompt=prompt,
        parameters=dict(parameters or {}),
        source_ids=sorted(split.visible_ids),
        code_version=code_version,
        dataset_hash=split.dataset_hash,
        split_digest=split.digest(),
    )
    locked.compute_hash()
    return locked


def _top_terms(sources: list[Source], top_n: int) -> list[str]:
    import re
    from collections import Counter
    stop = {
        "and", "the", "a", "an", "of", "to", "in", "is", "it", "as", "that",
        "was", "for", "on", "with", "are", "be", "at", "or", "by", "from",
        "this", "has", "have", "its", "not", "they", "but", "we", "you", "he",
        "she", "his", "her", "their", "our",
    }
    counter: Counter = Counter()
    for s in sources:
        for tok in re.findall(r"[A-Za-z]{3,}", s.text.lower()):
            if tok not in stop:
                counter[tok] += 1
    return [w for w, _ in counter.most_common(top_n)]


def _evidence_summary(sources: list[Source], term: str) -> list[str]:
    out = []
    for s in sources:
        if term.lower() in s.text.lower():
            out.append(f"{s.source_id}: '{term}'")
            if len(out) >= 3:
                break
    return out


def _cooccurrence_summary(sources: list[Source], a: str, b: str) -> list[str]:
    out = []
    for s in sources:
        t = s.text.lower()
        if a.lower() in t and b.lower() in t:
            out.append(f"{s.source_id}: '{a}' + '{b}' co-occur")
            if len(out) >= 3:
                break
    return out
