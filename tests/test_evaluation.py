"""Regression tests for evaluation integrity (BridgeLab issue #1).

The scoring logic must apply structured machine-testable targets, respect
token boundaries, and never re-parse prose. Each test maps to one of the
must-have fixtures in the issue.
"""
from bridgelab.evaluation import (
    baseline_predictions,
    evaluate_all,
    evaluate_prediction,
)
from bridgelab.models import Prediction, Source


def _pred(pid, category, term="decoherence", ta=None, tb=None, same=True):
    target = {"kind": category, "term": term}
    if category == "cooccurrence":
        target = {"kind": "cooccurrence", "term_a": ta or "alpha", "term_b": tb or "beta", "same_document": same}
    return Prediction(prediction_id=pid, category=category, statement="desc", target=target)


# 1. Generic prose words must NOT trigger a match when the target term is absent.
def test_generic_words_do_not_match():
    p = _pred("p1", "theme_present", term="decoherence")
    withheld = [Source("w1", "this is the concept and material and withheld generic prose")]
    r = evaluate_prediction(p, withheld)
    assert r.outcome == "miss"


# 2. theme_present matches only when the term is actually present (word boundary).
def test_theme_present_word_boundary():
    hit = _pred("p2", "theme_present", term="decoherence")
    nohit = _pred("p3", "theme_present", term="cohere")  # substring of "decoherence" must NOT match
    withheld = [Source("w1", "quantum decoherence occurs here")]
    assert evaluate_prediction(hit, withheld).outcome == "hit"
    assert evaluate_prediction(nohit, withheld).outcome == "miss"  # boundary respected


# 3. Relation with alpha+beta in DIFFERENT docs -> no co-occurrence match.
def test_cooccurrence_requires_same_document():
    p = _pred("p4", "cooccurrence", ta="alpha", tb="beta")
    withheld = [
        Source("w1", "alpha appears alone here"),
        Source("w2", "beta appears alone here"),
    ]
    assert evaluate_prediction(p, withheld).outcome == "miss"


# 4. Same pair in ONE doc -> match with that doc citation.
def test_cooccurrence_same_document_matches():
    p = _pred("p5", "cooccurrence", ta="alpha", tb="beta")
    withheld = [Source("w1", "alpha and beta together")]
    r = evaluate_prediction(p, withheld)
    assert r.outcome == "hit"
    assert r.matched_document_ids == ["w1"]


# 5. Absence with explicit target passes/fails correctly; NOT a contradiction.
def test_absence_scored_directionally_not_contradiction():
    absent_ok = _pred("p6", "term_absent", term="decoherence")
    absent_fail = _pred("p7", "term_absent", term="entropy")
    withheld = [Source("w1", "entropy increases and decoherence is absent from this doc")]
    r_ok = evaluate_prediction(absent_ok, withheld)  # "decoherence" actually present -> absence miss
    # note: above text DOES contain "decoherence", so absence should MISS
    assert r_ok.outcome == "miss"
    r_fail = evaluate_prediction(absent_fail, withheld)  # "entropy" present -> miss
    assert r_fail.outcome == "miss"


def test_absence_when_truly_absent_hits():
    p = _pred("p8", "term_absent", term="zebra")
    withheld = [Source("w1", "entropy and decoherence")]
    r = evaluate_prediction(p, withheld)
    assert r.outcome == "hit"
    assert r.notes.lower().startswith("term")  # absence recorded, not a claim contradiction


# 6. Semantic contradiction -> requires_review, never auto token match.
def test_semantic_contradiction_requires_review():
    p = Prediction(
        prediction_id="p9", category="contradiction", statement="claim X conflicts with claim Y",
        target={"kind": "contradiction"},
    )
    withheld = [Source("w1", "claims that use shared vocabulary")]
    r = evaluate_prediction(p, withheld)
    assert r.outcome == "requires_review"


# 7. Baseline is comparable: same withheld material, same predicate definitions.
def test_baseline_uses_same_evaluator():
    visible = [Source("v1", "resonance and resonance and harmony"), Source("v2", "resonance harmony harmony")]
    withheld = [Source("w1", "harmony appears here")]
    b = baseline_predictions(visible, withheld)
    assert b, "baseline should produce at least one prediction"
    # the baseline predicts the most frequent visible term ("harmony" or "resonance");
    # evaluate it by the SAME theme_present predicate on withheld:
    for br in b:
        assert br.target.get("kind") == "theme_present"
        assert br.outcome in ("hit", "miss")


# 8. Locked-prediction tampering invalidates the manifest hash.
def test_tampering_invalidates_lock():
    from bridgelab.generation import lock_predictions
    from bridgelab.partitioning import partition_deterministic
    sources = [
        Source("a", "resonance harmony synchronize here", family="f1", lineage=["r1"]),
        Source("b", "resonance harmony again", family="f1", lineage=["r1"]),
        Source("c", "photosynthesis carbon fixation", family="f2", lineage=["r2"]),
        Source("d", "entropy disorder thermodynamics", family="f3", lineage=["r3"]),
    ]
    split = partition_deterministic(sources, "t", seed=1)
    visible = [s for s in sources if s.source_id in split.visible_ids]
    from bridgelab.generation import generate_predictions
    preds = generate_predictions(visible, "t", "m", "p")
    locked = lock_predictions("t", preds, split, "m", "p", {}, "1.0.0")
    original = locked.prediction_manifest_hash
    # tamper with a prediction statement
    locked.predictions[0].statement = "tampered"
    assert locked.compute_hash() != original


# 9. Family never straddles the split.
def test_no_family_leakage():
    from bridgelab.partitioning import assert_no_leakage, partition_deterministic
    sources = [
        Source("a1", "x", family="f1", lineage=["r1"]),
        Source("a2", "x", family="f1", lineage=["r1"]),
        Source("b1", "y", family="f2", lineage=["r2"]),
        Source("b2", "y", family="f2", lineage=["r2"]),
        Source("c1", "z", family="f3", lineage=["r3"]),
    ]
    m = partition_deterministic(sources, "t2", seed=4)
    assert_no_leakage(m, sources)


def test_evaluate_all_returns_same_count():
    preds = [_pred(f"p{i}", "theme_present", term=f"term{i}") for i in range(3)]
    withheld = [Source("w", "term0 term1 term2")]
    assert len(evaluate_all(preds, withheld)) == 3
