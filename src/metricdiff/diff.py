"""The core diff engine: compare two snapshots into a :class:`DiffReport`."""

from __future__ import annotations

from .models import ChangeStatus, DiffConfig, DiffReport, MetricChange, MetricKey, Snapshot


def _sort_key(key: MetricKey) -> tuple[str, str]:
    return (key.metric, key.dimension or "")


def _is_breach(
    status: ChangeStatus,
    baseline: float | None,
    current: float | None,
    abs_change: float | None,
    pct_change: float | None,
    config: DiffConfig,
) -> bool:
    if status is ChangeStatus.ADDED:
        return config.breach_on_added
    if status is ChangeStatus.REMOVED:
        return config.breach_on_removed
    if status is ChangeStatus.UNCHANGED:
        return False

    # CHANGED: both values present and different.
    if (
        abs_change is not None
        and config.abs_threshold is not None
        and abs(abs_change) >= config.abs_threshold
    ):
        return True
    if pct_change is not None:
        return abs(pct_change) >= config.pct_threshold
    # pct is undefined only when baseline == 0 while current != 0: an
    # unbounded move, which is always material.
    return baseline == 0 and current not in (None, 0)


def diff_snapshots(
    baseline: Snapshot,
    current: Snapshot,
    config: DiffConfig | None = None,
) -> DiffReport:
    """Diff ``baseline`` against ``current`` and return a :class:`DiffReport`.

    Every key present in either snapshot yields exactly one
    :class:`MetricChange`, sorted by metric then dimension for deterministic
    output.
    """
    config = config or DiffConfig()
    keys = sorted(set(baseline) | set(current), key=_sort_key)

    changes: list[MetricChange] = []
    for key in keys:
        b = baseline.get(key)
        c = current.get(key)

        abs_change: float | None = None
        pct_change: float | None = None

        if b is None:
            status = ChangeStatus.ADDED
        elif c is None:
            status = ChangeStatus.REMOVED
        else:
            abs_change = c - b
            if b != 0:
                pct_change = (c - b) / abs(b) * 100.0
            status = ChangeStatus.UNCHANGED if b == c else ChangeStatus.CHANGED

        breach = _is_breach(status, b, c, abs_change, pct_change, config)
        changes.append(
            MetricChange(
                metric=key.metric,
                dimension=key.dimension,
                baseline=b,
                current=c,
                abs_change=abs_change,
                pct_change=pct_change,
                status=status,
                breach=breach,
            )
        )

    return DiffReport(config=config, changes=changes)
