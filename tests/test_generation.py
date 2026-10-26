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


def test_predictions_carry_structured_targets():
    split = partition_deterministic(SOURCES, "g1", seed=1)
    visible = [s for s in SOURCES if s.source_id in split.visible_ids]
    preds = generate_predictions(visible, "g1", "m", "p")
    assert preds
    for p in preds:
        assert p.target and p.target.get("kind"), f"prediction {p.prediction_id} missing a structured target"


def test_lock_is_immutable_and_deterministic():
    split = partition_deterministic(SOURCES, "g2", seed=2)
    visible = [s for s in SOURCES if s.source_id in split.visible_ids]
    preds = generate_predictions(visible, "g2", "m", "p")
    locked = lock_predictions("g2", preds, split, "m", "p", {}, "0.1.0")
    h1 = locked.compute_hash()
    assert h1 == locked.compute_hash()
    assert locked.split_digest == split.digest()


def test_lock_only_uses_visible_ids():
    split = partition_deterministic(SOURCES, "g3", seed=3)
    visible = [s for s in SOURCES if s.source_id in split.visible_ids]
    preds = generate_predictions(visible, "g3", "m", "p")
    locked = lock_predictions("g3", preds, split, "m", "p", {}, "0.1.0")
    assert set(locked.source_ids) <= set(split.visible_ids)
