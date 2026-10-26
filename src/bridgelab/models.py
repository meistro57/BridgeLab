"""Core data models for BridgeLab.

These are plain dataclasses / TypedDict-style shapes serialised to JSON so the
whole pipeline is inspectable and reproducible. We deliberately avoid any
framework so the experiment's shape stays readable and auditable.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(obj: Any) -> str:
    canon = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


@dataclass
class Source:
    """A single source document (or claim) under test."""

    source_id: str
    text: str
    family: Optional[str] = None          # e.g. "wheat-and-chaff", used to partition by family
    provenance: dict = field(default_factory=dict)   # timestamps, origin repo, etc.
    lineage: list = field(default_factory=list)      # ancestry / parent doc ids

    def fingerprint(self) -> str:
        return _sha256(self.text)


@dataclass
class Prediction:
    """A structured, evidence-backed prediction about withheld material."""

    prediction_id: str
    category: str                  # theme | relation | contradiction | similarity | absence
    statement: str
    supporting_evidence: list = field(default_factory=list)  # source ids + quotes
    test_criteria: str = ""
    uncertainty: str = ""
    confidence: Optional[float] = None


@dataclass
class SplitManifest:
    experiment_id: str
    created_at: str
    visible_ids: list
    withheld_ids: list
    partition_method: str
    seed: int
    dataset_hash: str

    def digest(self) -> str:
        # Digest must be reproducible: exclude the wall-clock timestamp so two
        # identical splits hash identically. Only the content-determining
        # fields are included.
        body = {
            "experiment_id": self.experiment_id,
            "visible_ids": self.visible_ids,
            "withheld_ids": self.withheld_ids,
            "partition_method": self.partition_method,
            "seed": self.seed,
            "dataset_hash": self.dataset_hash,
        }
        return _sha256(body)


@dataclass
class LockedPredictions:
    experiment_id: str
    created_at: str
    predictions: list
    model_name: str
    prompt: str
    parameters: dict
    source_ids: list
    code_version: str
    dataset_hash: str
    split_digest: str
    prediction_manifest_hash: str = ""

    def compute_hash(self) -> str:
        self.prediction_manifest_hash = _sha256([asdict(p) for p in self.predictions])
        return self.prediction_manifest_hash


@dataclass
class EvaluationResult:
    prediction_id: str
    outcome: str                   # match | missed | false_positive | contradiction | no_finding
    matched_evidence: list = field(default_factory=list)
    citations: list = field(default_factory=list)
    baseline_outcome: str = ""
    notes: str = ""
