import csv
import json
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from linkedin_job_indexer.errors import ExtractionBlockedError, ExtractionError, ParsingError
from linkedin_job_indexer.filters import evaluate
from linkedin_job_indexer.models import (
    AppConfig,
    Decision,
    Job,
    JobSummary,
    RunItem,
    RunReport,
    SearchConfig,
)
from linkedin_job_indexer.parser import parse_job, parse_search
from linkedin_job_indexer.store import JobStore


class JobClient(Protocol):
    def search(self, search: SearchConfig, start: int) -> str: ...

    def job(self, job_id: str) -> str: ...


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _write_csv(path: Path, jobs: Sequence[tuple[Job, int, tuple[str, ...]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "job_id",
                "title",
                "company",
                "location",
                "posted",
                "score",
                "matched_keywords",
                "url",
                "description",
            ),
        )
        writer.writeheader()
        for job, score, matched in jobs:
            writer.writerow(
                {
                    "job_id": job.job_id,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "posted": job.posted_text or job.posted_date,
                    "score": score,
                    "matched_keywords": ", ".join(matched),
                    "url": job.url,
                    "description": job.description,
                }
            )
    temporary.replace(path)


def _discover(config: AppConfig, client: JobClient) -> list[JobSummary]:
    jobs: dict[str, JobSummary] = {}
    for search in config.searches:
        for page in range(config.run.max_pages):
            summaries = parse_search(client.search(search, start=page * 25))
            if not summaries:
                break

            for summary in summaries:
                jobs.setdefault(summary.job_id, summary)
                if config.run.max_jobs and len(jobs) >= config.run.max_jobs:
                    return list(jobs.values())

    return list(jobs.values())


def run_pipeline(
    config: AppConfig,
    store: JobStore,
    out_dir: Path,
    client: JobClient,
    *,
    now: datetime | None = None,
) -> RunReport:
    summaries = _discover(config, client)
    seen_at = now or datetime.now(UTC)
    items: list[RunItem] = []
    accepted_jobs: list[tuple[Job, int, tuple[str, ...]]] = []
    processed: list[tuple[Job, Decision]] = []
    unseen = 0
    accepted = 0
    rejected = 0
    skipped_seen = 0
    failed = 0

    for summary in summaries:
        if store.contains(summary.job_id):
            skipped_seen += 1
            continue

        unseen += 1
        try:
            job = parse_job(client.job(summary.job_id), summary)
        except ExtractionBlockedError:
            raise
        except (ExtractionError, ParsingError) as exc:
            failed += 1
            items.append(
                RunItem(
                    job_id=summary.job_id,
                    title=summary.title,
                    company=summary.company,
                    location=summary.location,
                    url=summary.url,
                    status="failed",
                    error=str(exc),
                )
            )
            continue

        decision = evaluate(job, config.filters)
        processed.append((job, decision))
        matched = (*decision.matched_required, *decision.matched_boost)
        status = "accepted" if decision.accepted else "rejected"
        items.append(
            RunItem(
                job_id=job.job_id,
                title=job.title,
                company=job.company,
                location=job.location,
                url=job.url,
                status=status,
                score=decision.score,
                matched_keywords=matched,
                reasons=decision.reasons,
            )
        )

        if decision.accepted:
            accepted += 1
            accepted_jobs.append((job, decision.score, matched))
        else:
            rejected += 1

    accepted_jobs.sort(key=lambda item: (-item[1], item[0].title.casefold()))
    report = RunReport(
        discovered=len(summaries),
        unseen=unseen,
        accepted=accepted,
        rejected=rejected,
        skipped_seen=skipped_seen,
        failed=failed,
        items=tuple(items),
    )

    _write_csv(out_dir / "jobs.csv", accepted_jobs)
    _atomic_text(
        out_dir / "report.json",
        json.dumps(asdict(report), ensure_ascii=False, indent=2) + "\n",
    )
    store.save_many(processed, seen_at)
    return report
