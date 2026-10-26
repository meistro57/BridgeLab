import pytest

from bridgelab.generation import generate_predictions, lock_predictions
from bridgelab.models import Source
from bridgelab.partitioning import partition_deterministic


SOURCES = [
    Source("a", "the resonance principle governs synchronization and harmony", family="f1", lineage=["r1"]),
    Source("b", "resonance and harmony appear together", family="f1", lineage=["r1"]),
    Source("c", "photosynthesis drives carbon fixation", family="f2", lineage=["r2"]),
    Source("d", "photosynthesis and carbon fixation co-occur", family="f2", lineage=["r2"]),
    Source("e", "entropy increases in isolation", family="f3", lineage=["r3"]),
]


def test_lock_produces_immutable_digest():
    split = partition_deterministic(SOURCES, "exp1", seed=1)
    visible = [s for s in SOURCES if s.source_id in split.visible_ids]
    preds = generate_predictions(visible, "exp1", "test-model", "test prompt")
    locked = lock_predictions("exp1", preds, split, "test-model", "test prompt", {}, "0.1.0")
    h1 = locked.compute_hash()
    h2 = locked.compute_hash()
    assert h1 == h2
    assert locked.prediction_manifest_hash
    assert locked.split_digest == split.digest()


def test_predictions_only_use_visible_source_ids():
    split = partition_deterministic(SOURCES, "exp2", seed=2)
    visible = [s for s in SOURCES if s.source_id in split.visible_ids]
    locked = lock_predictions(
        "exp2",
        generate_predictions(visible, "exp2", "m", "p"),
        split, "m", "p", {}, "0.1.0",
    )
    assert set(locked.source_ids) <= set(split.visible_ids)
