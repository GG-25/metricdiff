from __future__ import annotations

import json
from pathlib import Path

import pytest

from metricdiff import DiffReport, diff_snapshots, load_snapshot, render_json, render_table
from metricdiff.cli import main

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _report() -> DiffReport:
    base = load_snapshot(FIXTURES / "week1.csv")
    curr = load_snapshot(FIXTURES / "week2.csv")
    return diff_snapshots(base, curr)


def test_render_table_has_headers_and_summary() -> None:
    out = render_table(_report())
    assert "METRIC" in out
    assert "DELTA%" in out
    assert "BREACH" in out
    assert "4 breach(es)" in out
    assert "revenue[US]" in out


def test_render_table_only_breaches_hides_clean_rows() -> None:
    out = render_table(_report(), only_breaches=True)
    assert "revenue[US]" in out
    assert "revenue[EU]" not in out
    assert "churn_rate" not in out


def test_render_json_is_valid_and_structured() -> None:
    out = render_json(_report())
    payload = json.loads(out)
    assert payload["summary"]["has_breach"] is True
    assert payload["summary"]["breaches"] == 4
    assert payload["config"]["pct_threshold"] == 10.0
    labels = {c["metric"] for c in payload["changes"]}
    assert "refunds" in labels


def test_cli_returns_1_on_breach(capsys: pytest.CaptureFixture[str]) -> None:
    code = main([str(FIXTURES / "week1.csv"), str(FIXTURES / "week2.csv")])
    out = capsys.readouterr().out
    assert code == 1
    assert "BREACH" in out


def test_cli_returns_0_when_within_threshold(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        [
            str(FIXTURES / "week1.csv"),
            str(FIXTURES / "week2.csv"),
            "--pct-threshold",
            "1000",
            "--no-breach-added",
            "--no-breach-removed",
        ]
    )
    capsys.readouterr()
    assert code == 0


def test_cli_json_format(capsys: pytest.CaptureFixture[str]) -> None:
    code = main([str(FIXTURES / "week1.json"), str(FIXTURES / "week2.json"), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["summary"]["added"] == 1


def test_cli_bad_input_returns_2(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    missing = tmp_path / "nope.csv"
    code = main([str(missing), str(FIXTURES / "week2.csv")])
    err = capsys.readouterr().err
    assert code == 2
    assert "error" in err
