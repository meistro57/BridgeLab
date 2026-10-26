"""Evidence adapters.

BridgeLab imports findings from JSON/JSONL (default) and exposes a clean,
provider-agnostic adapter interface for Qdrant. Collection schemas are never
hard-coded: an adapter declares the field mapping.
"""
from __future__ import annotations

import json
import os
from typing import Any, Iterable, Protocol

from .models import Source


class EvidenceAdapter(Protocol):
    """A source of Source objects. Implementations must be side-effect free."""

    def load_sources(self) -> list[Source]:
        ...


class JsonlAdapter:
    """Load sources from a JSONL file.

    Expected shape per line:
        {"source_id": str, "text": str, "family": optional str,
         "provenance": optional dict, "lineage": optional list}
    """

    def __init__(self, path: str):
        self.path = path

    def load_sources(self) -> list[Source]:
        sources: list[Source] = []
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                sources.append(_source_from_mapping(obj))
        return sources


class JsonAdapter:
    """Load sources from a JSON file: either a list, or {"sources": [...]}."""

    def __init__(self, path: str):
        self.path = path

    def load_sources(self) -> list[Source]:
        with open(self.path, "r", encoding="utf-8") as fh:
            obj = json.load(fh)
        items = obj["sources"] if isinstance(obj, dict) and "sources" in obj else obj
        return [_source_from_mapping(m) for m in items]


def _source_from_mapping(obj: dict[str, Any]) -> Source:
    return Source(
        source_id=str(obj["source_id"]),
        text=str(obj.get("text", "")),
        family=obj.get("family"),
        provenance=dict(obj.get("provenance") or {}),
        lineage=list(obj.get("lineage") or []),
    )


class QdrantAdapter:
    """Optional adapter for Qdrant collections.

    This adapter is intentionally minimal and maps an existing collection's
    payload to Source objects via an explicit field map. It does NOT create or
    modify collections, and it never hard-codes a schema.

    Requires the optional dependency: pip install 'bridgelab[qdrant]'.
    """

    def __init__(self, client: Any, collection: str, field_map: dict[str, str]):
        """
        client: a qdrant_client.QdrantClient instance.
        field_map: e.g. {"source_id": "id", "text": "text", "family": "family"}.
        """
        self.client = client
        self.collection = collection
        self.field_map = field_map

    def load_sources(self, limit: int = 10_000) -> list[Source]:
        sources: list[Source] = []
        # Scroll the collection in pages.
        scroll = self.client.scroll(
            collection_name=self.collection,
            limit=min(limit, 512),
            with_payload=True,
            with_vectors=False,
        )
        points, next_offset = scroll[0], scroll[1]
        while True:
            for point in points:
                payload = point.payload or {}
                sources.append(Source(
                    source_id=str(payload.get(self.field_map["source_id"], point.id)),
                    text=str(payload.get(self.field_map["text"], "")),
                    family=payload.get(self.field_map.get("family") or "family"),
                    provenance={"qdrant_collection": self.collection, "point_id": point.id},
                    lineage=[],
                ))
                if len(sources) >= limit:
                    return sources
            if next_offset is None:
                break
            nxt = self.client.scroll(
                collection_name=self.collection,
                offset=next_offset,
                limit=min(limit, 512),
                with_payload=True,
                with_vectors=False,
            )
            points, next_offset = nxt[0], nxt[1]
        return sources


def adapt_from_path(path: str) -> EvidenceAdapter:
    if path.endswith(".jsonl"):
        return JsonlAdapter(path)
    if path.endswith(".json"):
        return JsonAdapter(path)
    raise ValueError(f"unsupported evidence path: {path} (use .json or .jsonl)")
