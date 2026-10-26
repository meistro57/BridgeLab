import json

from bridgelab.evaluation import baseline_predictions, evaluate_all
from bridgelab.generation import generate_predictions, lock_predictions
from bridgelab.models import Source
from bridgelab.partitioning import partition_deterministic
from bridgelab.reporting import build_report, compute_metrics, render_markdown

SOURCES = [
    Source("a", "resonance and harmony synchronize", family="f1", lineage=["r1"]),
    Source("b", "resonance harmony synchronization again", family="f1", lineage=["r1"]),
    Source("c", "photosynthesis and carbon fixation", family="f2", lineage=["r2"]),
    Source("d", "photosynthesis carbon fixation again", family="f2", lineage=["r2"]),
    Source("e", "doppler effect shifts frequency", family="f3", lineage=["r3"]),
]


def test_report_uses_honest_metrics():
    split = partition_deterministic(SOURCES, "r1", seed=11)
    visible = [s for s in SOURCES if s.source_id in split.visible_ids]
    withheld = [s for s in SOURCES if s.source_id in split.withheld_ids]
    preds = generate_predictions(visible, "r1", "m", "p")
    locked = lock_predictions("r1", preds, split, "m", "p", {}, "0.1.0")
    results = evaluate_all(preds, withheld)
    baseline = baseline_predictions(visible, withheld)
    report = build_report("r1", split, locked, results, baseline, SOURCES, [])
    m = report["metrics"]
    # honest metric names present; no fabricated precision/recall
    assert "hit_rate" in m
    assert "coverage" in m
    assert "precision" not in m
    assert "recall" not in m
    md = render_markdown(report)
    assert "BridgeLab Experiment" in md
    assert "hit rate" in md.lower()
    json.dumps(report)  # serialisable


def test_metrics_cover_outcome_types():
    from bridgelab.models import EvaluationResult
    results = [
        EvaluationResult("a", "hit"),
        EvaluationResult("b", "miss"),
        EvaluationResult("c", "requires_review"),
        EvaluationResult("d", "not_evaluable"),
    ]
    m = compute_metrics(results)
    assert m["hits"] == 1
    assert m["misses"] == 1
    assert m["abstentions"] == 2
