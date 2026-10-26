# Experiment Protocol

Defines the *shape* of a valid BridgeLab experiment. Anything that does not
satisfy these steps is not a BridgeLab experiment.

## 1. Evidence Selection

- Sources are imported with stable `source_id`, `text`, optional `family`,
  provenance, and lineage.
- Duplicate material is identified by lineage/fingerprint, not re-derived.

## 2. Blind Partitioning

- Corpus split ~80% visible / 20% withheld.
- Partition is by **whole document or family** — never by random text chunk.
- Families must not straddle the boundary (enforced by `assert_no_leakage`).
- A manifest records the split and a reproducible digest.

## 3. Hypothesis Generation

- Predictions are generated from **visible material only**.
- Each prediction carries: category, statement, supporting evidence, test
  criteria, and uncertainty.

## 4. Prediction Locking

- Predictions are frozen and hashed **before** withheld material is revealed.
- The manifest records model name, prompt, parameters, source ids, code version,
  and dataset hash.

## 5. Independent Evaluation

- Withheld material is revealed **only** to the evaluator.
- Each prediction is scored: match / miss / false positive / contradiction /
  no-finding.
- A naive baseline is computed for comparison.

## 6. Adversarial Review

- A critical pass checks: source contamination, confirmation bias, shared
  vocabulary, correlated sources, unsupported causation, overconfidence.

## 7. Reports

- Markdown + JSON, with experiment id, inventory, split, locked predictions,
  hashes, outcomes, metrics, limitations, citations.
- **Unsuccessful experiments are preserved.**

## Invariants (what makes it trustworthy)

- Locked predictions are immutable after audit (digest over content, not time).
- Withheld = only reachable by the evaluator.
- Baseline and experimental results are shown separately.
- Every claim keeps its source citation.
- No fabricated results; synthetic fixtures are explicitly labelled.
