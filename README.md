# LinkedIn Job Indexer

A small daily CLI that searches LinkedIn's public logged-out job pages, fetches full descriptions, removes jobs already indexed, filters them using deterministic keywords, and writes a ranked CSV plus an audit JSON report.

It deliberately does **not** log into LinkedIn, automate applications, run a browser, or claim complete LinkedIn coverage. The public guest endpoints are undocumented and may change or block cloud IPs.

## How it works

```text
config.toml
    |
    v
public LinkedIn searches -> unique job IDs -> full descriptions
                                                |
                                                v
SQLite seen-state <- reject/require/boost filters
                              |
                              v
                     out/jobs.csv
                     out/report.json
```

## Run locally

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
cp config.example.toml config.toml
# Edit searches and filters first.
uv sync --dev
uv run linkedin-jobs run \
  --config config.toml \
  --db .data/jobs.sqlite3 \
  --out-dir out
```

Expected terminal output:

```text
discovered=42 new=39 accepted=11 rejected=28 seen=3 failed=0
results=out/jobs.csv
report=out/report.json
```

`jobs.csv` contains only accepted jobs, sorted by keyword score. `report.json` contains every newly processed job and its accepted, rejected, or failed decision. The SQLite database remembers accepted and rejected IDs, so overlapping searches and later runs do not process the same LinkedIn job twice.

## Configure searches

Each search needs a role query and region:

```toml
[[searches]]
keywords = "machine learning engineer"
location = "Poland"
remote_only = false
```

Use several narrow searches instead of one giant Boolean query. LinkedIn can limit or reorder public results, and overlapping results are deduplicated by job ID.

## Configure filters

```toml
[filters]
required_any = ["machine learning", "llm"]
reject_title = ["principal", "director"]
reject_description = ["active security clearance"]
boost = ["python", "pytorch", "evaluation"]
min_score = 1
```

The matching is case-insensitive and token-boundary aware: the keyword `ml` does not match the letters inside `HTML`.

Filtering order:

1. Reject title keywords.
2. Reject description keywords.
3. Require at least one relevance keyword when `required_any` is non-empty.
4. Count unique boost-keyword matches.
5. Reject scores below `min_score`.

## Cheap live smoke test

Copy the config and temporarily set:

```toml
max_pages = 1
max_jobs = 3
request_delay_seconds = 0.25
```

Then run the normal command. This proves the current public HTML still matches the parser without making a large request batch.

## Daily GitHub Actions run

The `Daily index` workflow runs at 06:00 UTC and can also be started manually from **Actions → Daily index → Run workflow**. It:

1. Restores the most recent cached SQLite state.
2. Runs `config.example.toml`.
3. Saves the new SQLite cache.
4. Uploads `jobs.csv` and `report.json` as a workflow artifact.

Edit `config.example.toml` in the repository to change the scheduled searches. GitHub Actions uses datacenter IPs, so a local run may work while a hosted run is blocked; a failure is surfaced as a failed workflow rather than an empty successful report.

## Validation

```bash
uv run ruff check .
uv run mypy
uv run pytest
uv run python -m build
```

## Known limitations

- LinkedIn provides no supported public job-search API for this use case.
- Logged-out results are best-effort and may be incomplete.
- Guest endpoint parameters and HTML are undocumented.
- A LinkedIn layout or anti-bot change requires updating only `client.py` or `parser.py`; the filter, database, and outputs remain independent.
- Automated scraping may conflict with LinkedIn's terms. Decide whether that risk is acceptable before scheduling continued use.
