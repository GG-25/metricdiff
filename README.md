# metricdiff

**Diff two snapshots of your metrics and fail the build when something moves too much.**

## The problem

Dashboards drift silently. Between two runs of an ETL job, a nightly report, or a
model-evaluation suite, a metric can jump 30%, a KPI can vanish, or a brand-new
series can appear, and nobody notices until a human squints at two spreadsheets
side by side. `metricdiff` turns that eyeball-diff into a deterministic check:
give it a *baseline* and a *current* snapshot, set a threshold, and it prints a
clean table (or JSON) and **exits non-zero if any change is material** - so it
drops straight into CI or a cron job.

It handles:

- **CSV or JSON** input, auto-detected by extension.
- **Dimensions** - a metric sliced by one label (e.g. `revenue[US]`, `revenue[EU]`).
- **Added / removed** metrics, flagged as breaches by default.
- **Percent and absolute** thresholds - catch a 24% jump *and* a big move that's
  only 0.5% of a huge base.
- **Zero baselines** - a move from 0 has undefined percent, so it's reported as an
  unbounded (always-material) change instead of dividing by zero.

Pure Python + [pydantic](https://docs.pydantic.dev/). No pandas, no services, no
network, everything runs offline.

## Quickstart

From a fresh clone (requires [uv](https://docs.astral.sh/uv/)):

```bash
uv sync
uv run metricdiff fixtures/week1.csv fixtures/week2.csv
```

## Usage example

The repo ships two deterministic fixtures, week-one and week-two of a small SaaS
dashboard. `week1` has `support_tickets`; `week2` drops it and adds `refunds`.

```console
$ uv run metricdiff fixtures/week1.csv fixtures/week2.csv
METRIC           BASELINE  CURRENT      DELTA   DELTA%  STATUS     FLAG
---------------  --------  -------  ---------  -------  ---------  ------
active_users       12,000   12,100    +100.00   +0.83%  changed
churn_rate           2.50     2.50      +0.00   +0.00%  unchanged
refunds                 -       15          -        -  added      BREACH
revenue[EU]        40,000   40,200    +200.00   +0.50%  changed
revenue[US]        60,000   66,000  +6,000.00  +10.00%  changed    BREACH
signups               500      620    +120.00  +24.00%  changed    BREACH
support_tickets       320        -          -        -  removed    BREACH

7 metric(s): 4 changed, 1 added, 1 removed, 1 unchanged | 4 breach(es)

$ echo $?
1
```

At the default 10% threshold four rows breach: `revenue[US]` (+10.00%, the
boundary is inclusive), `signups` (+24.00%), the added `refunds`, and the removed
`support_tickets`. `revenue[EU]` (+0.50%) and `active_users` (+0.83%) are within
tolerance, and the process exits `1` so CI stops.

### JSON output, only the breaches

```bash
uv run metricdiff fixtures/week1.json fixtures/week2.json --format json --only-breaches
```

```json
{
  "changes": [
    { "metric": "refunds", "dimension": null, "baseline": null, "current": 15.0,
      "abs_change": null, "pct_change": null, "status": "added", "breach": true },
    { "metric": "revenue", "dimension": "US", "baseline": 60000.0, "current": 66000.0,
      "abs_change": 6000.0, "pct_change": 10.0, "status": "changed", "breach": true }
  ],
  "summary": { "changed": 4, "added": 1, "removed": 1, "unchanged": 1,
               "breaches": 4, "has_breach": true }
}
```

*(Keys are sorted and the full document lists all four breaches; trimmed here.)*

### Useful flags

| Flag | Effect |
|---|---|
| `--pct-threshold N` | Percent magnitude (>=) that counts as a breach (default `10.0`). |
| `--abs-threshold N` | Also breach when the absolute change magnitude is >= `N`. |
| `--format {text,json}` | Table (default) or machine-readable JSON. |
| `--only-breaches` | Print only the flagged rows. |
| `--no-breach-added` / `--no-breach-removed` | Don't treat appear/disappear as breaches. |

Exit codes: `0` no breach, `1` at least one breach, `2` bad input.

## Library API

```python
from metricdiff import diff_snapshots, load_snapshot, DiffConfig, render_table

base = load_snapshot("fixtures/week1.csv")
curr = load_snapshot("fixtures/week2.csv")

report = diff_snapshots(base, curr, DiffConfig(pct_threshold=10.0))
print(render_table(report))

if report.has_breach:
    for change in report.breaches:
        print(change.label, change.pct_change)
```

## Input formats

**CSV** - header must contain `metric` and `value`; `dimension` is optional
(headers are case- and order-insensitive):

```csv
metric,dimension,value
revenue,US,60000
signups,,500
```

**JSON** - a flat number, or a one-level object to slice by dimension:

```json
{ "revenue": { "US": 60000, "EU": 40000 }, "signups": 500 }
```

## Development

```bash
uv sync
uv run ruff check .     # lint (E,F,I,UP,B,SIM,RUF, line-length 100)
uv run mypy src tests   # strict type-check
uv run pytest -q        # 33 tests
```

Every number in this README is produced by the shipped fixtures and asserted in
the test suite (`tests/test_diff.py::test_report_counts_over_fixtures`) - nothing
here is hand-typed.

## What I'd build next

- **Multi-dimension keys** - today a metric carries at most one dimension value;
  a composite key (`region=US, plan=pro`) would cover real warehouse exports.
- **Per-metric thresholds** - a config file so `churn_rate` can tolerate ±0.5%
  while `revenue` tolerates ±10%.
- **Directional rules** - flag drops but not rises (or vice-versa) for guardrail
  metrics like error rate.
- **A Markdown/HTML reporter** to post the diff as a PR comment.

## Maintainer

Maintained by **Gayathri Gurram**, NPI & Supply Chain Program Manager, with
experience in data-driven program delivery and process optimization.

- Email: [ggurram.work@gmail.com](mailto:ggurram.work@gmail.com)
- LinkedIn: [gayathri-g-b86207348](https://linkedin.com/in/gayathri-g-b86207348/)