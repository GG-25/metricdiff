"""Command-line interface for metricdiff.

Usage::

    metricdiff BASELINE CURRENT [options]

Exit codes: ``0`` = no breach, ``1`` = at least one breach, ``2`` = usage or
input error.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .diff import diff_snapshots
from .loaders import SnapshotError, load_snapshot
from .models import DiffConfig
from .render import render_json, render_table


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="metricdiff",
        description="Diff two metric snapshots and flag material moves.",
    )
    parser.add_argument("baseline", help="Baseline snapshot file (.csv or .json)")
    parser.add_argument("current", help="Current snapshot file (.csv or .json)")
    parser.add_argument(
        "--pct-threshold",
        type=float,
        default=10.0,
        help="Percent-change magnitude that counts as a breach (default: 10.0)",
    )
    parser.add_argument(
        "--abs-threshold",
        type=float,
        default=None,
        help="Optional absolute-change magnitude that counts as a breach",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--only-breaches",
        action="store_true",
        help="Show only rows flagged as breaches",
    )
    parser.add_argument(
        "--no-breach-added",
        action="store_true",
        help="Do not treat newly added metrics as breaches",
    )
    parser.add_argument(
        "--no-breach-removed",
        action="store_true",
        help="Do not treat removed metrics as breaches",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = DiffConfig(
        pct_threshold=args.pct_threshold,
        abs_threshold=args.abs_threshold,
        breach_on_added=not args.no_breach_added,
        breach_on_removed=not args.no_breach_removed,
    )

    try:
        baseline = load_snapshot(args.baseline)
        current = load_snapshot(args.current)
    except SnapshotError as exc:
        print(f"metricdiff: error: {exc}", file=sys.stderr)
        return 2

    report = diff_snapshots(baseline, current, config)

    if args.format == "json":
        print(render_json(report, only_breaches=args.only_breaches))
    else:
        print(render_table(report, only_breaches=args.only_breaches))

    return 1 if report.has_breach else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
