# Changelog

## 0.1.0 — 2026-10-26

Initial MVP.

- Seven-stage experimental pipeline (evidence → partition → generate → lock → evaluate → review → report).
- Deterministic family-blocked blind partitioning with source-lineage leakage guard.
- Immutable prediction locking via SHA-256 manifest (content-only digest).
- Independent evaluation with a naive token-match baseline.
- MisfitCrew-style adversarial review pass.
- Markdown + JSON experimental reports, including failed predictions.
- Synthetic fixture corpus with positive / negative / contradiction / leakage test cases.
- pytest suite (10 tests) and GitHub Actions CI.
- Optional Qdrant adapter behind a clean, schema-agnostic interface.
```
