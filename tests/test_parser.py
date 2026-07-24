from pathlib import Path

import pytest

from linkedin_job_indexer.errors import ParsingError
from linkedin_job_indexer.models import JobSummary
from linkedin_job_indexer.parser import parse_job, parse_search


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_search_extracts_and_deduplicates_job_cards() -> None:
    html = (FIXTURES / "search.html").read_text(encoding="utf-8")

    jobs = parse_search(html)

    assert [job.job_id for job in jobs] == ["1111111111", "2222222222"]
    assert jobs[0].title == "Machine Learning Engineer"
    assert jobs[0].company == "Example AI"
    assert jobs[0].location == "Warsaw, Poland"
    assert jobs[0].posted_text == "2 hours ago"
    assert jobs[0].posted_date == "2026-07-24"
    assert jobs[0].url == "https://www.linkedin.com/jobs/view/ml-engineer-1111111111"


def test_parse_job_extracts_full_description() -> None:
    html = (FIXTURES / "job.html").read_text(encoding="utf-8")
    summary = JobSummary(
        job_id="1111111111",
        url="https://www.linkedin.com/jobs/view/ml-engineer-1111111111",
        title="Machine Learning Engineer",
        company="Example AI",
        location="Warsaw, Poland",
        posted_text="2 hours ago",
        posted_date="2026-07-24",
    )

    job = parse_job(html, summary)

    assert job.description.startswith("Build production machine-learning systems")
    assert "LLM evaluation" in job.description
    assert job.title == summary.title


def test_parse_job_rejects_missing_description() -> None:
    summary = JobSummary(
        job_id="1",
        url="https://www.linkedin.com/jobs/view/example-1",
        title="Example",
        company="Company",
        location="Poland",
        posted_text="now",
        posted_date="2026-07-24",
    )

    with pytest.raises(ParsingError, match="description"):
        parse_job("<html><body><h1>Example</h1></body></html>", summary)
