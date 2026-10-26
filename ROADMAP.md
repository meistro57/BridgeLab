# Roadmap

## MVP (this repository) — DONE

- Offline, deterministic pipeline (A–G).
- Reproducible family-blocked partitioning with leakage guard.
- Immutable prediction locking (SHA-256 manifest).
- Independent evaluation with baseline.
- Adversarial review pass.
- Markdown + JSON reports.
- Fixture corpus with positive/negative/contradiction/leakage cases.
- pytest suite + GitHub Actions CI.

## Next milestones

1. **Qdrant adapter live run** — point the existing adapter at a real
   collection (e.g. Meta-Bridge `meta_reflections`) with a field map.
2. **Real generator backend** — swap the token-frequency heuristic for an LLM
   generator while keeping the `Prediction` schema and lock.
3. **Cross-repo import** — a small importer that reads KAE / Meta-Bridge /
   Keystone exported JSON into `Source` objects with provenance.
4. **Human review** — an explicit human-review queue for ambiguous semantic
   matches (stage E extension).
5. **Severity / overconfidence scoring** — richer adversarial signals.
```
