"""Unified command-line interface for the project."""

from __future__ import annotations

import argparse
import json

from . import __version__
from .evaluate import main as evaluate_main
from .simulator import run_simulation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adaptedge", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="run the FastAPI service")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)

    ev = sub.add_parser("evaluate", help="run the deterministic replay benchmark")
    ev.add_argument("--runs", type=int, default=200)
    ev.add_argument("--seed", type=int, default=42)
    ev.add_argument("--out", default="reports/metrics.json")

    sub.add_parser("version", help="print the package version")

    args = parser.parse_args(argv)
    if args.command == "serve":
        import uvicorn

        uvicorn.run("adaptedge.api:app", host=args.host, port=args.port)
        return 0
    if args.command == "evaluate":
        return evaluate_main(
            ["--runs", str(args.runs), "--seed", str(args.seed), "--out", args.out]
        )
    if args.command == "version":
        print(__version__)
        return 0
    if args.command is None:
        result = run_simulation(runs=20, seed=1)
        print(json.dumps({"p99_improvement_pct": result["p99_improvement_pct"]}, indent=2))
        return 0
    parser.print_help()
    return 2
