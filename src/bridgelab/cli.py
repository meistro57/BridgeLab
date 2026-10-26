"""BridgeLab CLI.

Run the full experiment pipeline end-to-end, offline, against local fixtures.

Usage:
    bridgelab run --evidence fixtures/demo.jsonl --out runs/demo
    bridgelab run --evidence fixtures/demo.jsonl --out runs/demo --seed 42
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .adapters import adapt_from_path
from .adversarial import review
from .evaluation import evaluate_all
from .generation import generate_predictions, lock_predictions
from .models import Source
from .partitioning import assert_no_leakage, partition_deterministic
from .reporting import build_report, render_markdown


def run_experiment(evidence_path: str, out_dir: str, seed: int = 42) -> dict:
    """Run a complete experiment and write JSON + Markdown reports to out_dir."""
    adapter = adapt_from_path(evidence_path)
    sources: list[Source] = adapter.load_sources()
    experiment_id = _experiment_id(evidence_path)

    # Stage B: blind partition
    split = partition_deterministic(sources, experiment_id, seed=seed)
    assert_no_leakage(split, sources)

    by_id = {s.source_id: s for s in sources}
    visible = [by_id[i] for i in split.visible_ids]
    withheld = [by_id[i] for i in split.withheld_ids]

    # Stage C: hypothesis generation (visible only)
    predictions = generate_predictions(
        visible, experiment_id,
        model_name="bridgelab.token-frequency.v1",
        prompt="offline deterministic heuristic (no LLM)",
    )

    # Stage D: lock predictions
    locked = lock_predictions(
        experiment_id, predictions, split,
        model_name="bridgelab.token-frequency.v1",
        prompt="offline deterministic heuristic (no LLM)",
        parameters={"seed": seed},
        code_version=__version__,
    )

    # Stage E: independent evaluation (withheld only)
    results = evaluate_all(predictions, withheld)

    # Stage F: adversarial review
    report = build_report(
        experiment_id, split, locked, results, sources, []
    )
    notes = review(report, split.visible_ids, split.withheld_ids)
    report["adversarial_review"] = notes

    # Stage G: write reports
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"{experiment_id}.json")
    md_path = os.path.join(out_dir, f"{experiment_id}.md")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(report))

    report["_json_path"] = json_path
    report["_md_path"] = md_path
    return report


def _experiment_id(path: str) -> str:
    base = os.path.splitext(os.path.basename(path))[0]
    return base or "experiment"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bridgelab", description="BridgeLab validation engine")
    parser.add_argument("--version", action="version", version=f"bridgelab {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    runp = sub.add_parser("run", help="run a full experiment")
    runp.add_argument("--evidence", required=True, help="path to .json or .jsonl evidence corpus")
    runp.add_argument("--out", required=True, help="output directory for reports")
    runp.add_argument("--seed", type=int, default=42, help="partition seed")

    args = parser.parse_args(argv)
    if args.command == "run":
        report = run_experiment(args.evidence, args.out, seed=args.seed)
        metrics = report["metrics"]
        print(f"Experiment {report['experiment_id']}: precision {metrics['precision']} vs baseline {metrics['baseline_precision']}")
        print(f"  JSON: {report['_json_path']}")
        print(f"  MD:   {report['_md_path']}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
