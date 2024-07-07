"""Load metric snapshots from CSV or JSON, from a path or a raw string.

Accepted shapes
---------------
JSON, flat::

    {"revenue": 1000, "signups": 50}

JSON, sliced by one dimension::

    {"revenue": {"US": 600, "EU": 400}}

CSV, with a header row containing ``metric`` and ``value`` and an optional
``dimension`` column::

    metric,dimension,value
    revenue,US,600
    revenue,EU,400
    signups,,50
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from .models import MetricKey, Snapshot


class SnapshotError(ValueError):
    """Raised when snapshot input is malformed."""


def _coerce_number(raw: Any, where: str) -> float:
    if isinstance(raw, bool):
        raise SnapshotError(f"{where}: boolean is not a valid metric value")
    if isinstance(raw, int | float):
        return float(raw)
    if isinstance(raw, str):
        text = raw.strip()
        try:
            return float(text)
        except ValueError as exc:
            raise SnapshotError(f"{where}: {raw!r} is not a number") from exc
    raise SnapshotError(f"{where}: {raw!r} is not a number")


def load_json(text: str) -> Snapshot:
    """Parse a JSON snapshot string into a :class:`Snapshot`."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SnapshotError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SnapshotError("top-level JSON must be an object keyed by metric name")

    snapshot: Snapshot = {}
    for metric, value in data.items():
        if isinstance(value, dict):
            if not value:
                raise SnapshotError(f"metric {metric!r} has an empty dimension object")
            for dimension, sub in value.items():
                key = MetricKey(str(metric), str(dimension))
                snapshot[key] = _coerce_number(sub, f"{metric}[{dimension}]")
        else:
            snapshot[MetricKey(str(metric), None)] = _coerce_number(value, str(metric))
    return snapshot


def load_csv(text: str) -> Snapshot:
    """Parse a CSV snapshot string into a :class:`Snapshot`."""
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise SnapshotError("CSV is empty (no header row)")

    headers = {name.strip().lower(): name for name in reader.fieldnames if name}
    if "metric" not in headers or "value" not in headers:
        raise SnapshotError("CSV header must contain 'metric' and 'value' columns")
    metric_col = headers["metric"]
    value_col = headers["value"]
    dim_col = headers.get("dimension")

    snapshot: Snapshot = {}
    for lineno, row in enumerate(reader, start=2):
        metric = (row.get(metric_col) or "").strip()
        if not metric:
            raise SnapshotError(f"line {lineno}: empty metric name")
        dimension: str | None = None
        if dim_col is not None:
            raw_dim = (row.get(dim_col) or "").strip()
            dimension = raw_dim or None
        key = MetricKey(metric, dimension)
        if key in snapshot:
            raise SnapshotError(f"line {lineno}: duplicate metric {key.label!r}")
        snapshot[key] = _coerce_number(row.get(value_col), f"line {lineno} ({metric})")
    return snapshot


def load_text(text: str, fmt: str) -> Snapshot:
    """Parse a snapshot string given an explicit format (``"json"`` or ``"csv"``)."""
    fmt = fmt.lower()
    if fmt == "json":
        return load_json(text)
    if fmt == "csv":
        return load_csv(text)
    raise SnapshotError(f"unknown format {fmt!r}; expected 'json' or 'csv'")


def load_snapshot(path: str | Path) -> Snapshot:
    """Load a snapshot from a file, dispatching on the file extension."""
    path = Path(path)
    if not path.exists():
        raise SnapshotError(f"no such file: {path}")
    suffix = path.suffix.lower()
    if suffix == ".json":
        fmt = "json"
    elif suffix == ".csv":
        fmt = "csv"
    else:
        raise SnapshotError(f"unsupported file extension {suffix!r}; use .json or .csv")
    return load_text(path.read_text(encoding="utf-8"), fmt)
