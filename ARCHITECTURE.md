# Architecture

BridgeLab is a **validation layer**, not a discovery system. It must remain small,
inspectable, and impossible to confuse with a generator of conclusions.

## Design principles

1. **Predictions are locked before evidence is revealed.** The lock is a SHA-256
   digest of a manifest (model, prompt, params, code version, split digest,
   dataset hash). Nothing downstream can silently revise an earlier guess.
2. **Withheld data never reaches the prediction stage.** Partitioning happens
   first; generation happens only over visible sources; evaluation is the only
   stage that sees withheld material.
3. **Semantic similarity is a candidate, not proof.** The evaluator treats a
   fuzzy match as a signal to inspect, never as a verdict.
4. **Baseline or it didn't happen.** Every result is compared against a naive
   method so "the model did something" is measured, not assumed.
5. **Failures are preserved.** Unsuccessful experiments are written to disk like
   every other result.

## Package layout

```
bridgelab/
  models.py        # Source, Prediction, SplitManifest, LockedPredictions, EvaluationResult
  partitioning.py  # Stage B — blind, family-blocked, leakage-guarded split
  generation.py    # Stages C/D — hypothesis generation + immutable prediction lock
  evaluation.py    # Stage E — independent evaluation + baseline
  adversarial.py   # Stage F — MisfitCrew-style critical pass
  reporting.py     # Stage G — Markdown + JSON reports, metrics
  adapters.py      # evidence loaders (JSON/JSONL) + Qdrant adapter interface
  cli.py           # entry point: bridgelab run --evidence ... --out ...
```

## Data flow

```
[JSON / JSONL / Qdrant adapter]
          │  load_sources() -> list[Source]
          ▼
   partition_deterministic()  ──►  SplitManifest (visible / withheld, digest)
          │
          ├── visible ──► generate_predictions() ──► lock_predictions() ──► LockedPredictions (hashed)
          │
          └── withheld ──────────────────────► evaluate_all() ──► EvaluationResult[] (baseline too)
                                                     │
                                                     ▼
                                          adversarial.review() ──► notes
                                                     │
                                                     ▼
                                    build_report() ──► JSON + Markdown
```

## Extension points (future, out of scope for MVP)

- **Qdrant adapter**: `QdrantAdapter(client, collection, field_map)` already
  exists behind a clean interface; it scrolls a collection and maps payloads to
  `Source`. It never hard-codes a schema and never mutates a collection.
- **Real generator backends**: `generate_predictions` is a deterministic
  token-frequency heuristic today; the `Prediction` shape is backend-agnostic,
  so an LLM backend can be swapped in without changing stage E/F/G.
- **Cross-repo import**: KAE / Meta-Bridge / Keystone findings can be adapted to
  `Source` objects via their exported JSON, preserving provenance & lineage.
```

## Why no web dashboard / LLM in the MVP

The instrument must be trusted before it is decorated. A deterministic, offline,
dependency-light core makes the experimental protocol auditable end to end.
