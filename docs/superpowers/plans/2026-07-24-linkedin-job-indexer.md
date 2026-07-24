# LinkedIn Job Indexer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daily CLI that indexes recent public LinkedIn jobs, fetches descriptions, deduplicates, filters, and exports results.

**Architecture:** Use a small Python package with separate configuration, HTTP adapter, parser, filtering, SQLite storage, orchestration, and CLI modules. LinkedIn responses remain HTML and are parsed through fixtures in tests; live access is only a smoke test.

**Tech Stack:** Python 3.11+, httpx, Beautiful Soup, standard-library TOML/SQLite/CSV/JSON, pytest, Ruff, mypy, uv, GitHub Actions.

## Global Constraints

- Do not authenticate to LinkedIn or store LinkedIn cookies.
- Fail loudly on blocks or malformed responses.
- Keep the CLI and output format small and documented.
- Do not add a web UI, LLM integration, application automation, or migration framework.

---

### Task 1: Package and configuration

**Files:**
- Create: `pyproject.toml`
- Create: `src/linkedin_job_indexer/models.py`
- Create: `src/linkedin_job_indexer/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `load_config(path: Path) -> AppConfig` and immutable configuration/domain dataclasses.

- [ ] Write tests for valid configuration, missing searches, and invalid positive limits.
- [ ] Run the focused tests and confirm they fail because the package is missing.
- [ ] Implement the minimal dataclasses and TOML loader.
- [ ] Run the focused tests and full tests.
- [ ] Commit with a short subject and detailed body.

### Task 2: LinkedIn parser and HTTP adapter

**Files:**
- Create: `src/linkedin_job_indexer/errors.py`
- Create: `src/linkedin_job_indexer/parser.py`
- Create: `src/linkedin_job_indexer/client.py`
- Create: `tests/fixtures/search.html`
- Create: `tests/fixtures/job.html`
- Test: `tests/test_parser.py`
- Test: `tests/test_client.py`

**Interfaces:**
- Produces: `parse_search(html: str) -> list[JobSummary]`, `parse_job(html: str, summary: JobSummary) -> Job`, and `LinkedInClient` search/detail methods.

- [ ] Write parser tests and block-detection tests first.
- [ ] Run focused tests and verify expected failures.
- [ ] Implement parsing, URL construction, retries, throttling, and block detection.
- [ ] Run focused tests and the full suite.
- [ ] Commit with a short subject and detailed body.

### Task 3: Filters, storage, and pipeline

**Files:**
- Create: `src/linkedin_job_indexer/filters.py`
- Create: `src/linkedin_job_indexer/store.py`
- Create: `src/linkedin_job_indexer/pipeline.py`
- Test: `tests/test_filters.py`
- Test: `tests/test_store.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Produces: `evaluate(job: Job, config: FilterConfig) -> Decision`, `JobStore`, and `run_pipeline(...) -> RunReport`.

- [ ] Write tests for reject/require/boost decisions, idempotent storage, pagination, cross-search deduplication, and atomic outputs.
- [ ] Run focused tests and verify expected failures.
- [ ] Implement the smallest passing domain logic and orchestration.
- [ ] Run focused tests and full suite.
- [ ] Commit with a short subject and detailed body.

### Task 4: CLI, documentation, automation, and verification

**Files:**
- Create: `src/linkedin_job_indexer/cli.py`
- Create: `src/linkedin_job_indexer/__init__.py`
- Create: `src/linkedin_job_indexer/__main__.py`
- Create: `config.example.toml`
- Create: `README.md`
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/daily.yml`
- Create: `.gitignore`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `linkedin-jobs run --config ... --db ... --out-dir ...`.

- [ ] Write a CLI smoke test first.
- [ ] Run it and verify the expected failure.
- [ ] Implement CLI and project files.
- [ ] Run Ruff, mypy, pytest, package build, and a bounded live smoke run.
- [ ] Update documentation with exact commands and limitations.
- [ ] Commit, push the feature branch, and open a PR containing the system DAG.
