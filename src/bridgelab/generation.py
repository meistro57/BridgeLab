"""Stages C & D: Hypothesis Generation and Prediction Locking.

Predictions are generated from *visible* material only, then locked. Every
prediction carries a structured machine-testable ``target`` predicate so the
evaluator never re-parses prose (BridgeLab issue #1).
"""
from __future__ import annotations

import re
from collections import Counter

from .models import LockedPredictions, Prediction, Source, SplitManifest, _now, _sha256

_STOP = {
    "and", "the", "a", "an", "of", "to", "in", "is", "it", "as", "that",
    "was", "for", "on", "with", "are", "be", "at", "or", "by", "from",
    "this", "has", "have", "its", "not", "they", "but", "we", "you", "he",
    "she", "his", "her", "their", "our", "which", "between", "across",
    "concept", "material", "withheld", "recurs", "recurring",
}


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z]{3,}", text.lower()) if t not in _STOP]


def _top_terms(sources: list[Source], top_n: int) -> list[str]:
    counter: Counter = Counter()
    for s in sources:
        for tok in _tokens(s.text):
            counter[tok] += 1
    return [w for w, _ in counter.most_common(top_n)]


def _cooccur(term_a: str, term_b: str, sources: list[Source]) -> list[Source]:
    return [
        s for s in sources
        if term_a.lower() in s.text.lower() and term_b.lower() in s.text.lower()
    ]


def generate_predictions(
    visible_sources: list[Source],
    experiment_id: str,
    model_name: str,
    prompt: str,
    parameters: dict | None = None,
) -> list[Prediction]:
    """Generate structured predictions from visible material alone.

    The default heuristic is deterministic and offline (no LLM). Each
    prediction carries an explicit machine-testable target:
      theme_present(term)  -> term appears in at least one withheld source
      cooccurrence(a, b)   -> a and b appear in the SAME withheld source
      term_absent(term)    -> term appears in NO withheld source
    """
    params = dict(parameters or {})
    terms = _top_terms(visible_sources, top_n=params.get("top_n", 12))
    preds: list[Prediction] = []
    idx = 0

    # theme_present targets for the most frequent visible terms.
    for term in terms[:params.get("theme_n", 5)]:
        idx += 1
        preds.append(Prediction(
            prediction_id=f"{experiment_id}-p{idx:03d}",
            category="theme_present",
            statement=f"Concept {term!r} recurs across the withheld material.",
            target={"kind": "theme_present", "term": term},
            supporting_evidence=[f"{s.source_id}: contains {term!r}" for s in visible_sources if term in _tokens(s.text)][:3],
            uncertainty="single-term proxy; token presence is not conceptual agreement",
            confidence=0.5,
        ))

    # cooccurrence target for the two most frequent terms.
    if len(terms) >= 2:
        a, b = terms[0], terms[1]
        co = _cooccur(a, b, visible_sources)
        idx += 1
        preds.append(Prediction(
            prediction_id=f"{experiment_id}-p{idx:03d}",
            category="cooccurrence",
            statement=f"{a!r} and {b!r} co-occur in the same withheld source.",
            target={"kind": "cooccurrence", "term_a": a, "term_b": b, "same_document": True},
            supporting_evidence=[f"{s.source_id}: {a!r}+{b!r} co-occur" for s in co][:3],
            uncertainty="co-occurrence is not causation or conceptual relation",
            confidence=0.4,
        ))

    # term_absent target: the least frequent visible term is predicted absent.
    if terms:
        rare = terms[-1]
        idx += 1
        preds.append(Prediction(
            prediction_id=f"{experiment_id}-p{idx:03d}",
            category="term_absent",
            statement=f"The term {rare!r} is absent from the withheld material.",
            target={"kind": "term_absent", "term": rare},
            supporting_evidence=["visible term-frequency scan"],
            uncertainty="absence may be a split artifact, not a real signal; NOT a claim contradiction",
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
