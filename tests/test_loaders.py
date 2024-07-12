from __future__ import annotations

from pathlib import Path

import pytest

from metricdiff import MetricKey, SnapshotError, load_csv, load_json, load_snapshot

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_load_json_flat_and_nested() -> None:
    snap = load_json('{"revenue": {"US": 600, "EU": 400}, "signups": 50}')
    assert snap[MetricKey("revenue", "US")] == 600.0
    assert snap[MetricKey("revenue", "EU")] == 400.0
    assert snap[MetricKey("signups", None)] == 50.0
    assert len(snap) == 3


def test_load_csv_with_and_without_dimension() -> None:
    text = "metric,dimension,value\nrevenue,US,600\nsignups,,50\n"
    snap = load_csv(text)
    assert snap[MetricKey("revenue", "US")] == 600.0
    assert snap[MetricKey("signups", None)] == 50.0


def test_csv_headers_are_case_and_order_insensitive() -> None:
    text = "Value,Metric\n50,signups\n"
    snap = load_csv(text)
    assert snap[MetricKey("signups", None)] == 50.0


def test_csv_and_json_fixtures_agree() -> None:
    assert load_snapshot(FIXTURES / "week1.csv") == load_snapshot(FIXTURES / "week1.json")
    assert load_snapshot(FIXTURES / "week2.csv") == load_snapshot(FIXTURES / "week2.json")


def test_load_snapshot_dispatches_on_extension() -> None:
    snap = load_snapshot(FIXTURES / "week1.json")
    assert snap[MetricKey("support_tickets", None)] == 320.0


@pytest.mark.parametrize(
    "text",
    [
        "not json at all",
        "[1, 2, 3]",
        '{"revenue": "abc"}',
        '{"revenue": true}',
        '{"revenue": {}}',
    ],
)
def test_bad_json_raises(text: str) -> None:
    with pytest.raises(SnapshotError):
        load_json(text)


def test_csv_missing_required_columns() -> None:
    with pytest.raises(SnapshotError):
        load_csv("name,amount\nrevenue,10\n")


def test_csv_duplicate_key_raises() -> None:
    text = "metric,value\nsignups,1\nsignups,2\n"
    with pytest.raises(SnapshotError):
        load_csv(text)


def test_csv_bad_value_raises() -> None:
    with pytest.raises(SnapshotError):
        load_csv("metric,value\nsignups,notanumber\n")


def test_missing_file_raises() -> None:
    with pytest.raises(SnapshotError):
        load_snapshot(FIXTURES / "does_not_exist.json")


def test_unsupported_extension_raises(tmp_path: Path) -> None:
    p = tmp_path / "data.txt"
    p.write_text("metric,value\nsignups,1\n")
    with pytest.raises(SnapshotError):
        load_snapshot(p)
