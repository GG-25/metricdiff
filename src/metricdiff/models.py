"""Typed data models for metricdiff.

A *snapshot* is a mapping from :class:`MetricKey` to a numeric value. The diff
engine compares two snapshots and produces a :class:`DiffReport` of
:class:`MetricChange` rows, each flagged as a breach or not according to a
:class:`DiffConfig`.
"""

from __future__ import annotations

from enum import StrEnum
from typing import NamedTuple

from pydantic import BaseModel, Field


class MetricKey(NamedTuple):
    """Identity of a single metric series.

    A metric may be plain (``dimension is None``) or sliced by a single
    dimension value (e.g. ``region=US`` -> ``dimension="US"``).
    """

    metric: str
    dimension: str | None = None

    @property
    def label(self) -> str:
        """Human-readable label, e.g. ``revenue`` or ``revenue[US]``."""
        if self.dimension is None:
            return self.metric
        return f"{self.metric}[{self.dimension}]"


Snapshot = dict[MetricKey, float]


class ChangeStatus(StrEnum):
    """Lifecycle of a metric between the two snapshots."""

    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"
    UNCHANGED = "unchanged"


class DiffConfig(BaseModel):
    """Thresholds and rules that decide whether a change is *material*."""

    model_config = {"frozen": True}

    pct_threshold: float = Field(
        default=10.0,
        ge=0.0,
        description="Percent-change magnitude (>=) that counts as a breach.",
    )
    abs_threshold: float | None = Field(
        default=None,
        ge=0.0,
        description="Optional absolute-change magnitude (>=) that counts as a breach.",
    )
    breach_on_added: bool = Field(
        default=True, description="Treat newly appearing metrics as breaches."
    )
    breach_on_removed: bool = Field(
        default=True, description="Treat disappearing metrics as breaches."
    )


class MetricChange(BaseModel):
    """One row of a diff: the before/after values and derived deltas."""

    metric: str
    dimension: str | None
    baseline: float | None
    current: float | None
    abs_change: float | None
    pct_change: float | None
    status: ChangeStatus
    breach: bool

    @property
    def label(self) -> str:
        return MetricKey(self.metric, self.dimension).label


class DiffReport(BaseModel):
    """Full result of diffing two snapshots under a config."""

    config: DiffConfig
    changes: list[MetricChange]

    @property
    def breaches(self) -> list[MetricChange]:
        return [c for c in self.changes if c.breach]

    @property
    def has_breach(self) -> bool:
        return any(c.breach for c in self.changes)

    def counts(self) -> dict[str, int]:
        """Tally of rows per :class:`ChangeStatus` plus a ``breaches`` total."""
        tally = {status.value: 0 for status in ChangeStatus}
        for change in self.changes:
            tally[change.status.value] += 1
        tally["breaches"] = len(self.breaches)
        return tally
