import csv
import json
from pathlib import Path

import pytest

from linkedin_job_indexer.errors import ExtractionBlockedError
from linkedin_job_indexer.models import AppConfig, FilterConfig, RunConfig, SearchConfig
from linkedin_job_indexer.pipeline import run_pipeline
from linkedin_job_indexer.store import JobStore


def card(job_id: str, title: str, company: str = "Example") -> str:
    return f"""
    <li><div data-entity-urn="urn:li:jobPosting:{job_id}">
      <a href="https://www.linkedin.com/jobs/view/{title.lower().replace(' ', '-')}-{job_id}"></a>
      <h3>{title}</h3><h4>{company}</h4>
      <span class="job-search-card__location">Poland</span>
      <time datetime="2026-07-24">1 hour ago</time>
    </div></li>
    """


def detail(description: str) -> str:
    return f"<div class='show-more-less-html__markup'>{description}</div>"


class FakeClient:
    def __init__(self) -> None:
        self.search_calls: list[tuple[str, int]] = []
        self.job_calls: list[str] = []

    def search(self, search: SearchConfig, start: int) -> str:
        self.search_calls.append((search.keywords, start))
        pages = {
            ("machine learning engineer", 0): card("1000000001", "ML Engineer")
            + card("1000000002", "Principal ML Engineer"),
            ("machine learning engineer", 25): card("1000000001", "ML Engineer"),
            ("machine learning engineer", 50): "",
            ("ai engineer", 0): card("1000000001", "ML Engineer")
            + card("1000000003", "AI Engineer"),
            ("ai engineer", 25): "",
        }
        return pages.get((search.keywords, start), "")

    def job(self, job_id: str) -> str:
        self.job_calls.append(job_id)
        descriptions = {
            "1000000001": detail("Build machine learning products with Python and PyTorch."),
            "1000000002": detail("Lead machine learning strategy with Python."),
            "1000000003": detail("Build LLM evaluation systems with Python."),
        }
        return descriptions[job_id]


def test_pipeline_deduplicates_filters_persists_and_writes_outputs(tmp_path: Path) -> None:
    config = AppConfig(
        searches=(
            SearchConfig("machine learning engineer", "Poland"),
            SearchConfig("ai engineer", "Poland"),
        ),
        filters=FilterConfig(
            required_any=("machine learning", "llm"),
            reject_title=("principal",),
            boost=("python", "pytorch", "evaluation"),
            min_score=1,
        ),
        run=RunConfig(max_pages=3, request_delay_seconds=0),
    )
    client = FakeClient()

    with JobStore(tmp_path / "jobs.sqlite3") as store:
        report = run_pipeline(config, store, tmp_path / "out", client)

    assert report.discovered == 3
    assert report.unseen == 3
    assert report.accepted == 2
    assert report.rejected == 1
    assert report.failed == 0
    assert client.job_calls == ["1000000001", "1000000002", "1000000003"]

    with (tmp_path / "out" / "jobs.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["job_id"] for row in rows] == ["1000000003", "1000000001"]
    assert [row["score"] for row in rows] == ["2", "2"]

    payload = json.loads((tmp_path / "out" / "report.json").read_text(encoding="utf-8"))
    assert payload["accepted"] == 2
    assert len(payload["items"]) == 3
    assert list((tmp_path / "out").glob("*.tmp")) == []


def test_pipeline_skips_jobs_seen_in_previous_run(tmp_path: Path) -> None:
    config = AppConfig(
        searches=(SearchConfig("machine learning engineer", "Poland"),),
        run=RunConfig(max_pages=1, request_delay_seconds=0),
    )
    client = FakeClient()

    with JobStore(tmp_path / "jobs.sqlite3") as store:
        first = run_pipeline(config, store, tmp_path / "first", client)
        second_client = FakeClient()
        second = run_pipeline(config, store, tmp_path / "second", second_client)

    assert first.unseen == 2
    assert second.unseen == 0
    assert second.skipped_seen == 2
    assert second_client.job_calls == []


def test_pipeline_propagates_global_block(tmp_path: Path) -> None:
    class BlockedClient(FakeClient):
        def search(self, search: SearchConfig, start: int) -> str:
            raise ExtractionBlockedError("blocked")

    config = AppConfig(searches=(SearchConfig("AI", "Poland"),))

    with JobStore(tmp_path / "jobs.sqlite3") as store:
        with pytest.raises(ExtractionBlockedError):
            run_pipeline(config, store, tmp_path / "out", BlockedClient())


def test_pipeline_does_not_stop_on_repeated_nonempty_pages(tmp_path: Path) -> None:
    class RepeatingClient:
        def search(self, _: SearchConfig, start: int) -> str:
            pages = {
                0: card("1000000001", "ML Engineer"),
                25: card("1000000001", "ML Engineer"),
                50: card("1000000001", "ML Engineer"),
                75: card("1000000004", "Applied ML Engineer"),
            }
            return pages.get(start, "")

        def job(self, job_id: str) -> str:
            return detail(f"Build machine learning systems with Python for job {job_id}.")

    config = AppConfig(
        searches=(SearchConfig("machine learning", "Poland"),),
        filters=FilterConfig(required_any=("machine learning",)),
        run=RunConfig(max_pages=4, request_delay_seconds=0),
    )

    with JobStore(tmp_path / "jobs.sqlite3") as store:
        report = run_pipeline(config, store, tmp_path / "out", RepeatingClient())

    assert report.discovered == 2
    assert report.accepted == 2


def test_pipeline_does_not_persist_partial_run_when_globally_blocked(tmp_path: Path) -> None:
    class PartiallyBlockedClient:
        def search(self, _: SearchConfig, start: int) -> str:
            if start:
                return ""
            return card("1000000001", "ML Engineer") + card("1000000002", "AI Engineer")

        def job(self, job_id: str) -> str:
            if job_id == "1000000002":
                raise ExtractionBlockedError("blocked")
            return detail("Build machine learning products with Python.")

    config = AppConfig(
        searches=(SearchConfig("machine learning", "Poland"),),
        filters=FilterConfig(required_any=("machine learning",)),
        run=RunConfig(max_pages=1, request_delay_seconds=0),
    )

    with JobStore(tmp_path / "jobs.sqlite3") as store:
        with pytest.raises(ExtractionBlockedError):
            run_pipeline(config, store, tmp_path / "out", PartiallyBlockedClient())
        assert store.count() == 0
