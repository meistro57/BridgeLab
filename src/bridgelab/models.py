"""Core data models for BridgeLab.

Plain dataclasses serialised to JSON; deliberately no framework so the
experiment shape stays readable and auditable.
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
    family: str | None = None
    provenance: dict = field(default_factory=dict)
    lineage: list = field(default_factory=list)

    def fingerprint(self) -> str:
        return _sha256(self.text)


@dataclass
class Prediction:
    """A structured, evidence-backed prediction about withheld material.

    ``statement`` is the human-readable description. ``target`` is the exact
    machine-testable predicate the evaluator applies; the two are decoupled so
    test logic never re-parses prose (BridgeLab issue #1).
    """
    prediction_id: str
    category: str  # theme_present | cooccurrence | term_absent | requires_review
    statement: str
    target: dict = field(default_factory=dict)
    supporting_evidence: list = field(default_factory=list)
    uncertainty: str = ""
    confidence: float | None = None


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
    outcome: str  # hit | miss | requires_review | not_evaluable
    matched_document_ids: list = field(default_factory=list)
    evidence: list = field(default_factory=list)
    target: dict = field(default_factory=dict)
    baseline_outcome: str = ""
    notes: str = ""
