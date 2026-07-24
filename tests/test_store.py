from datetime import UTC, datetime
from pathlib import Path

from linkedin_job_indexer.models import Decision, Job
from linkedin_job_indexer.store import JobStore


def make_job() -> Job:
    return Job(
        job_id="123",
        url="https://example.com/123",
        title="ML Engineer",
        company="Example",
        location="Poland",
        posted_text="1 hour ago",
        posted_date="2026-07-24",
        description="Build ML systems",
    )


def test_store_initializes_and_saves_idempotently(tmp_path: Path) -> None:
    path = tmp_path / "jobs.sqlite3"
    decision = Decision(True, 1, (), ("ml",), ())
    seen_at = datetime(2026, 7, 24, 8, tzinfo=UTC)

    with JobStore(path) as store:
        assert store.contains("123") is False
        assert store.save(make_job(), decision, seen_at) is True
        assert store.save(make_job(), decision, seen_at) is False
        assert store.contains("123") is True
        assert store.count() == 1

    assert path.exists()
