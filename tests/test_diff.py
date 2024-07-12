from __future__ import annotations

from pathlib import Path

from metricdiff import (
    ChangeStatus,
    DiffConfig,
    DiffReport,
    MetricChange,
    MetricKey,
    diff_snapshots,
    load_snapshot,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _by_label(report: DiffReport, label: str) -> MetricChange:
    for change in report.changes:
        if change.label == label:
            return change
    raise KeyError(label)


def test_basic_change_math() -> None:
    base = {MetricKey("x"): 100.0}
    curr = {MetricKey("x"): 125.0}
    report = diff_snapshots(base, curr)
    change = report.changes[0]
    assert change.status is ChangeStatus.CHANGED
    assert change.abs_change == 25.0
    assert change.pct_change == 25.0
    assert change.breach is True


def test_unchanged_is_not_a_breach() -> None:
    base = {MetricKey("x"): 100.0}
    report = diff_snapshots(base, dict(base))
    change = report.changes[0]
    assert change.status is ChangeStatus.UNCHANGED
    assert change.pct_change == 0.0
    assert change.breach is False


def test_percent_uses_magnitude_of_baseline() -> None:
    # A move from -100 to -50 is a +50% change (halved magnitude, less negative).
    base = {MetricKey("x"): -100.0}
    curr = {MetricKey("x"): -50.0}
    change = diff_snapshots(base, curr).changes[0]
    assert change.abs_change == 50.0
    assert change.pct_change == 50.0


def test_added_and_removed_flagged_by_default() -> None:
    base = {MetricKey("gone"): 1.0}
    curr = {MetricKey("fresh"): 1.0}
    report = diff_snapshots(base, curr)
    fresh = _by_label(report, "fresh")
    gone = _by_label(report, "gone")
    assert fresh.status is ChangeStatus.ADDED
    assert fresh.breach is True
    assert gone.status is ChangeStatus.REMOVED
    assert gone.breach is True


def test_added_removed_can_be_silenced() -> None:
    base = {MetricKey("gone"): 1.0}
    curr = {MetricKey("fresh"): 1.0}
    config = DiffConfig(breach_on_added=False, breach_on_removed=False)
    report = diff_snapshots(base, curr, config)
    assert report.has_breach is False


def test_growth_from_zero_is_a_breach() -> None:
    base = {MetricKey("x"): 0.0}
    curr = {MetricKey("x"): 5.0}
    change = diff_snapshots(base, curr).changes[0]
    assert change.status is ChangeStatus.CHANGED
    assert change.pct_change is None  # undefined percent
    assert change.abs_change == 5.0
    assert change.breach is True


def test_zero_to_zero_is_unchanged() -> None:
    base = {MetricKey("x"): 0.0}
    change = diff_snapshots(base, {MetricKey("x"): 0.0}).changes[0]
    assert change.status is ChangeStatus.UNCHANGED
    assert change.breach is False


def test_pct_threshold_boundary_is_inclusive() -> None:
    base = {MetricKey("x"): 100.0}
    curr = {MetricKey("x"): 110.0}  # exactly +10%
    assert diff_snapshots(base, curr, DiffConfig(pct_threshold=10.0)).has_breach is True
    assert diff_snapshots(base, curr, DiffConfig(pct_threshold=10.01)).has_breach is False


def test_abs_threshold_catches_small_percent_large_absolute() -> None:
    base = {MetricKey("x"): 1_000_000.0}
    curr = {MetricKey("x"): 1_005_000.0}  # +0.5%, but +5000 absolute
    config = DiffConfig(pct_threshold=10.0, abs_threshold=1000.0)
    change = diff_snapshots(base, curr, config).changes[0]
    assert change.pct_change is not None
    assert abs(change.pct_change) < 10.0
    assert change.breach is True


def test_output_is_sorted_deterministically() -> None:
    base = {MetricKey("b"): 1.0, MetricKey("a", "z"): 1.0, MetricKey("a", "a"): 1.0}
    labels = [c.label for c in diff_snapshots(base, dict(base)).changes]
    assert labels == ["a[a]", "a[z]", "b"]


def test_report_counts_over_fixtures() -> None:
    base = load_snapshot(FIXTURES / "week1.csv")
    curr = load_snapshot(FIXTURES / "week2.csv")
    report = diff_snapshots(base, curr)
    counts = report.counts()
    assert counts["added"] == 1  # refunds
    assert counts["removed"] == 1  # support_tickets
    assert counts["breaches"] == 4
    assert report.has_breach is True
    # revenue[US] is exactly +10% -> breach; revenue[EU] +0.5% -> not.
    assert _by_label(report, "revenue[US]").breach is True
    assert _by_label(report, "revenue[EU]").breach is False
    assert _by_label(report, "signups").breach is True
    assert _by_label(report, "churn_rate").status is ChangeStatus.UNCHANGED
