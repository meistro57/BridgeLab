import pytest

from bridgelab.models import Source
from bridgelab.partitioning import (
    assert_no_leakage,
    partition_deterministic,
)


def _sources():
    # Two-member families ensure splitting keeps families whole.
    return [
        Source("a1", "resonance and harmony", family="res", lineage=["res_root"]),
        Source("a2", "harmony and resonance", family="res", lineage=["res_root"]),
        Source("b1", "photosynthesis and carbon", family="photo", lineage=["photo_root"]),
        Source("b2", "carbon and photosynthesis", family="photo", lineage=["photo_root"]),
        Source("c1", "entropy and disorder", family="ent", lineage=["ent_root"]),
        Source("c2", "disorder and entropy", family="ent", lineage=["ent_root"]),
        Source("d1", "entanglement and spin", family="entangle", lineage=["entangle_root"]),
        Source("d2", "spin and entanglement", family="entangle", lineage=["entangle_root"]),
        Source("e1", "doppler and redshift", family="doppler", lineage=["doppler_root"]),
        Source("f1", "a negative example about nothing", family="neg", lineage=["neg_root"]),
    ]


def test_partition_is_deterministic_and_reproducible():
    m1 = partition_deterministic(_sources(), "exp", seed=7)
    m2 = partition_deterministic(_sources(), "exp", seed=7)
    assert m1.visible_ids == m2.visible_ids
    assert m1.withheld_ids == m2.withheld_ids
    assert m1.digest() == m2.digest()


def test_partition_keeps_families_whole():
    m = partition_deterministic(_sources(), "exp", seed=3)
    assert_no_leakage(m, _sources())  # must not raise


def test_withheld_fraction_roughly_target():
    sources = _sources()
    m = partition_deterministic(sources, "exp", seed=5, withheld_fraction=0.2)
    total = len(sources)
    assert 0 < len(m.withheld_ids) <= total
    frac = len(m.withheld_ids) / total
    assert 0.1 <= frac <= 0.4  # family granularity means it won't hit exactly 0.2


def test_empty_input_raises():
    with pytest.raises(ValueError):
        partition_deterministic([], "exp")
