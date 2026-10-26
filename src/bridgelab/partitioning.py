"""Stage B: Blind Knowledge Partitioning.

Split a corpus into visible (80%) and withheld (20%) groups, partitioned by
whole source documents or families (never by random text chunks), preventing
duplicate / shared-ancestry leakage, and emitting a reproducible manifest.
"""
from __future__ import annotations

import hashlib
import random
from typing import Iterable, Optional

from .models import Source, SplitManifest


def _family_key(src: Source) -> str:
    # A family is the lineage root; documents that share a lineage ancestor
    # must never be split across the visible/withheld boundary.
    if src.lineage:
        return sorted(src.lineage)[0]
    if src.family:
        return src.family
    return src.source_id


def partition_deterministic(
    sources: list[Source],
    experiment_id: str,
    withheld_fraction: float = 0.2,
    seed: int = 42,
) -> SplitManifest:
    """Partition by family, deterministically, keeping whole families together.

    Groups sources by family key, shuffles the *families* with a seeded RNG,
    then assigns families to the withheld side until we reach the target
    fraction (or just over it). Never splits a family, and drops nothing.
    """
    if not sources:
        raise ValueError("no sources to partition")

    # Order families deterministically (sorted) then shuffle with seed.
    families: dict[str, list[Source]] = {}
    for s in sources:
        families.setdefault(_family_key(s), []).append(s)

    family_keys = sorted(families.keys())
    rng = random.Random(seed)
    rng.shuffle(family_keys)

    total = len(sources)
    target_withheld = max(1, int(round(total * withheld_fraction)))

    withheld_ids: list[str] = []
    visible_ids: list[str] = []
    for key in family_keys:
        members = families[key]
        ids = [m.source_id for m in members]
        # If withheld is still below target, take the whole family to withheld.
        if len(withheld_ids) < target_withheld:
            withheld_ids.extend(ids)
        else:
            visible_ids.extend(ids)

    dataset_hash = hashlib.sha256(
        "".join(s.fingerprint() for s in sources).encode("utf-8")
    ).hexdigest()

    from .models import _now
    manifest = SplitManifest(
        experiment_id=experiment_id,
        created_at=_now(),
        visible_ids=sorted(visible_ids),
        withheld_ids=sorted(withheld_ids),
        partition_method="family-block-deterministic",
        seed=seed,
        dataset_hash=dataset_hash,
    )
    return manifest


def assert_no_leakage(manifest: SplitManifest, sources: list[Source]) -> None:
    """Guard: a family must never straddle the visible/withheld boundary."""
    by_id = {s.source_id: s for s in sources}
    visible_families = {_family_key(by_id[i]) for i in manifest.visible_ids}
    withheld_families = {_family_key(by_id[i]) for i in manifest.withheld_ids}
    overlap = visible_families & withheld_families
    if overlap:
        raise ValueError(f"source-family leakage across split: {sorted(overlap)}")
