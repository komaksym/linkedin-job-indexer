# LinkedIn Job Indexer Design

## Goal

Build a small command-line application that runs once per day, discovers recent public LinkedIn job postings for configured role and region searches, downloads their public descriptions, removes previously seen jobs, filters them by configurable keywords, and writes machine-readable results.

## Scope

The MVP uses LinkedIn's logged-out guest HTML endpoints. It does not log into LinkedIn, automate applications, provide a web UI, use an LLM, or promise complete coverage of LinkedIn's inventory. The extractor is best-effort and must fail loudly when LinkedIn blocks or changes the response instead of reporting zero jobs.

## Architecture

```text
TOML config
    |
    v
search URL builder -> guest search HTML -> job summaries
                                      |
                                      v
SQLite dedupe <- guest job HTML <- unseen job IDs
       |                 |
       |                 v
       +----------> keyword filter/scorer
                              |
                              v
                     CSV + JSON report
```

The LinkedIn-specific logic is isolated behind an HTTP client and parser. Domain filtering, persistence, orchestration, and presentation remain separate.

## Components

- `config.py`: loads and validates TOML configuration.
- `client.py`: performs bounded HTTP requests with retries, throttling, and block detection.
- `parser.py`: converts LinkedIn guest HTML into job summaries and descriptions.
- `filters.py`: applies deterministic reject, require, and boost keywords.
- `store.py`: initializes SQLite and stores seen jobs idempotently.
- `pipeline.py`: coordinates searches, pagination, deduplication, descriptions, filters, and outputs.
- `cli.py`: exposes the `linkedin-jobs run` command.

## Data flow

1. Load one or more search specifications from TOML.
2. Request guest search batches using a configurable retrieval window, defaulting to 30 hours to tolerate delayed daily schedules.
3. Parse summaries and deduplicate overlapping searches by LinkedIn job ID.
4. Skip IDs already stored in SQLite.
5. Fetch full guest job HTML for each unseen ID.
6. Parse title, company, location, posting metadata, and description.
7. Reject configured title or description terms; require at least one configured relevance term when provided; count boost matches for ranking.
8. Save every successfully parsed unseen job to SQLite, including rejected jobs, so repeated searches do not reprocess them.
9. Write accepted jobs to CSV and all run decisions to JSON.

## Failure handling

- HTTP 403, 429, login walls, challenge pages, or malformed HTML raise a clear extraction error.
- A search page returning no job cards is treated as valid only when it does not resemble a block page.
- One failed description is recorded in the report and does not abort unrelated jobs unless the failure indicates global blocking.
- Output files are written atomically.

## Testing

Unit tests use saved minimal HTML fixtures and do not depend on LinkedIn. A manual live smoke command fetches a very small result set. CI runs Ruff, mypy, pytest, and package build; live LinkedIn access is intentionally excluded from PR CI because it is an unstable third-party dependency.

## Operational model

The repository includes a daily GitHub Actions workflow and a manual trigger. The workflow restores the SQLite database from the latest cache, runs the indexer, and uploads CSV/JSON artifacts. Cloud execution remains best-effort because LinkedIn may treat datacenter IPs differently from residential traffic.
