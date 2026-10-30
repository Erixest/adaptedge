"""Command-line entry point for the reproducible evaluation artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .dataset import pilot_report
from .simulator import run_simulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AdaptEdge replay benchmark")
    parser.add_argument("--runs", type=int, default=200, help="number of replay episodes")
    parser.add_argument("--seed", type=int, default=42, help="deterministic RNG seed")
    parser.add_argument(
        "--switch-penalty-ms",
        type=float,
        default=6.0,
        help="control-plane cost of changing transport",
    )
    parser.add_argument("--deadline-ms", type=float, default=750.0, help="hard deadline")
    parser.add_argument("--out", type=Path, default=Path("reports/metrics.json"))
    parser.add_argument(
        "--pilot-dir",
        type=Path,
        default=Path("data"),
        help="directory containing the real LoRa pilot CSVs",
    )
    parser.add_argument(
        "--include-episodes",
        action="store_true",
        help="include the per-episode decision trace in the artifact",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_simulation(
        runs=args.runs,
        seed=args.seed,
        switch_penalty_ms=args.switch_penalty_ms,
        deadline_ms=args.deadline_ms,
    )
    if not args.include_episodes:
        result.pop("episodes", None)
    pilot = pilot_report(args.pilot_dir)
    payload = {"tool": "adaptedge", "version": __version__, **result, "pilot": pilot}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"wrote {args.out} | runs={args.runs} seed={args.seed} "
        f"best_pinned={result['best_pinned']} "
        f"p95_improvement={result['p95_improvement_pct']}% "
        f"p99_improvement={result['p99_improvement_pct']}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
