from bridgelab.evaluation import evaluate_all, evaluate_prediction
from bridgelab.models import Prediction, Source


def test_theme_match_and_miss():
    hit = Prediction("p1", "theme", "Concept 'resonance' recurs.", test_criteria="'resonance' appears")
    miss = Prediction("p2", "theme", "Concept 'krypton' recurs.", test_criteria="'krypton' appears")
    withheld = [Source("w1", "resonance and harmony"), Source("w2", "entropy and disorder")]
    r1 = evaluate_prediction(hit, withheld)
    r2 = evaluate_prediction(miss, withheld)
    assert r1.outcome == "match"
    assert r2.outcome == "miss"


def test_contradiction_prediction_absent_wins():
    pred = Prediction("p3", "contradiction", "entropy is absent", test_criteria="term absent")
    withheld = [Source("w1", "photosynthesis and carbon fixation only")]
    r = evaluate_prediction(pred, withheld)
    # "photosynthesis"/"carbon"/"fixation" tokens present, but the prediction's
    # own statement token ("entropy") is absent -> contradiction holds.
    assert r.outcome == "match"


def test_evaluate_all_returns_same_count():
    preds = [Prediction(f"p{i}", "theme", f"concept token{i}", test_criteria="x") for i in range(3)]
    withheld = [Source("w", "token0 token1 token2")]
    results = evaluate_all(preds, withheld)
    assert len(results) == 3
