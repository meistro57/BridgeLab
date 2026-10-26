"""BridgeLab CLI.

Run the full experiment pipeline end-to-end, offline, against local fixtures.

Usage:
    bridgelab run --evidence fixtures/demo.jsonl --out runs/demo
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .adapters import adapt_from_path
from .adversarial import review
from .evaluation import baseline_predictions, evaluate_all
from .generation import generate_predictions, lock_predictions
from .partitioning import assert_no_leakage, partition_deterministic
from .reporting import build_report, render_markdown


def run_experiment(evidence_path: str, out_dir: str, seed: int = 42) -> dict:
    adapter = adapt_from_path(evidence_path)
    sources = adapter.load_sources()
    experiment_id = _experiment_id(evidence_path)

    split = partition_deterministic(sources, experiment_id, seed=seed)
    assert_no_leakage(split, sources)

    by_id = {s.source_id: s for s in sources}
    visible = [by_id[i] for i in split.visible_ids]
    withheld = [by_id[i] for i in split.withheld_ids]

    predictions = generate_predictions(
        visible, experiment_id,
        model_name="bridgelab.token-frequency.v1",
        prompt="offline deterministic heuristic (no LLM)",
    )
    locked = lock_predictions(
        experiment_id, predictions, split,
        model_name="bridgelab.token-frequency.v1",
        prompt="offline deterministic heuristic (no LLM)",
        parameters={"seed": seed},
        code_version=__version__,
    )

    results = evaluate_all(predictions, withheld)
    baseline = baseline_predictions(visible, withheld)

    report = build_report(
        experiment_id, split, locked, results, baseline, sources, [],
    )
    report["adversarial_review"] = review(report, split.visible_ids, split.withheld_ids)

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
    runp.add_argument("--evidence", required=True)
    runp.add_argument("--out", required=True)
    runp.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    if args.command == "run":
        report = run_experiment(args.evidence, args.out, seed=args.seed)
        m = report["metrics"]
        b = report["baseline"]
        print(f"Experiment {report['experiment_id']}: hit_rate {m['hit_rate']} (coverage {m['coverage']}) vs baseline {b['baseline_hit_rate']}")
        print(f"  JSON: {report['_json_path']}")
        print(f"  MD:   {report['_md_path']}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
