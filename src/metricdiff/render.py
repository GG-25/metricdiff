"""Render a :class:`DiffReport` as an aligned text table or as JSON."""

from __future__ import annotations

import json

from .models import ChangeStatus, DiffReport, MetricChange

_HEADERS = ("METRIC", "BASELINE", "CURRENT", "DELTA", "DELTA%", "STATUS", "FLAG")


def _fmt_num(value: float | None) -> str:
    if value is None:
        return "-"
    if value == int(value):
        return f"{int(value):,}"
    return f"{value:,.2f}"


def _fmt_signed(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:+,.2f}"


def _fmt_pct(value: float | None, status: ChangeStatus) -> str:
    if value is None:
        if status is ChangeStatus.CHANGED:
            return "inf"
        return "-"
    return f"{value:+.2f}%"


def _row_cells(change: MetricChange) -> tuple[str, ...]:
    return (
        change.label,
        _fmt_num(change.baseline),
        _fmt_num(change.current),
        _fmt_signed(change.abs_change),
        _fmt_pct(change.pct_change, change.status),
        change.status.value,
        "BREACH" if change.breach else "",
    )


def render_table(report: DiffReport, only_breaches: bool = False) -> str:
    """Return a monospace, column-aligned table of the diff."""
    rows = report.breaches if only_breaches else report.changes
    cells = [_row_cells(change) for change in rows]

    widths = [len(h) for h in _HEADERS]
    for row in cells:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    # Left-align the label and status/flag columns; right-align numerics.
    aligns = ("<", ">", ">", ">", ">", "<", "<")

    def fmt_row(values: tuple[str, ...]) -> str:
        parts = zip(values, aligns, widths, strict=True)
        return "  ".join(f"{val:{align}{width}}" for val, align, width in parts)

    lines = [fmt_row(_HEADERS), "  ".join("-" * w for w in widths)]
    lines.extend(fmt_row(row) for row in cells)

    counts = report.counts()
    summary = (
        f"{len(report.changes)} metric(s): "
        f"{counts['changed']} changed, {counts['added']} added, "
        f"{counts['removed']} removed, {counts['unchanged']} unchanged | "
        f"{counts['breaches']} breach(es)"
    )
    lines.append("")
    lines.append(summary)
    return "\n".join(lines)


def render_json(report: DiffReport, only_breaches: bool = False) -> str:
    """Return the diff as a stable, pretty-printed JSON document."""
    rows = report.breaches if only_breaches else report.changes
    payload = {
        "config": report.config.model_dump(),
        "summary": {
            **report.counts(),
            "has_breach": report.has_breach,
        },
        "changes": [change.model_dump() for change in rows],
    }
    return json.dumps(payload, indent=2, sort_keys=True)
