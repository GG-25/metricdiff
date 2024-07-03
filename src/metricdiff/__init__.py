"""metricdiff: diff two snapshots of named metrics and flag material moves.

Public API::

    from metricdiff import diff_snapshots, load_snapshot, DiffConfig
    from metricdiff import render_table, render_json
"""

from __future__ import annotations

from .diff import diff_snapshots
from .loaders import (
    SnapshotError,
    load_csv,
    load_json,
    load_snapshot,
    load_text,
)
from .models import (
    ChangeStatus,
    DiffConfig,
    DiffReport,
    MetricChange,
    MetricKey,
    Snapshot,
)
from .render import render_json, render_table

__all__ = [
    "ChangeStatus",
    "DiffConfig",
    "DiffReport",
    "MetricChange",
    "MetricKey",
    "Snapshot",
    "SnapshotError",
    "diff_snapshots",
    "load_csv",
    "load_json",
    "load_snapshot",
    "load_text",
    "render_json",
    "render_table",
]
