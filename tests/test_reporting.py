import json

from bridgelab.evaluation import evaluate_all
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


def test_full_report_builds_and_roundtrips():
    split = partition_deterministic(SOURCES, "expR", seed=11)
    visible = [s for s in SOURCES if s.source_id in split.visible_ids]
    withheld = [s for s in SOURCES if s.source_id in split.withheld_ids]
    preds = generate_predictions(visible, "expR", "m", "p")
    locked = lock_predictions("expR", preds, split, "m", "p", {}, "0.1.0")
    results = evaluate_all(preds, withheld)
    report = build_report("expR", split, locked, results, SOURCES, ["note"])
    md = render_markdown(report)
    assert "BridgeLab Experiment" in md
    assert report["metrics"]["total_predictions"] == len(preds)
    # ensure serialisable
    json.dumps(report)
