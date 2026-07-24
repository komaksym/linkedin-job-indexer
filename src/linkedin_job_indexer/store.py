from datetime import datetime
import json
from pathlib import Path
import sqlite3

from linkedin_job_indexer.models import Decision, Job

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT NOT NULL,
    posted_text TEXT NOT NULL,
    posted_date TEXT NOT NULL,
    description TEXT NOT NULL,
    accepted INTEGER NOT NULL,
    score INTEGER NOT NULL,
    matched_keywords_json TEXT NOT NULL,
    reasons_json TEXT NOT NULL,
    first_seen_at TEXT NOT NULL
)
"""


class JobStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._connection.execute(_SCHEMA)
        self._connection.commit()

    def __enter__(self) -> "JobStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def contains(self, job_id: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM jobs WHERE job_id = ? LIMIT 1", (job_id,)
        ).fetchone()
        return row is not None

    def save(self, job: Job, decision: Decision, seen_at: datetime) -> bool:
        matched = (*decision.matched_required, *decision.matched_boost)
        cursor = self._connection.execute(
            """
            INSERT OR IGNORE INTO jobs (
                job_id, url, title, company, location, posted_text, posted_date,
                description, accepted, score, matched_keywords_json, reasons_json,
                first_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.job_id,
                job.url,
                job.title,
                job.company,
                job.location,
                job.posted_text,
                job.posted_date,
                job.description,
                int(decision.accepted),
                decision.score,
                json.dumps(matched, ensure_ascii=False),
                json.dumps(decision.reasons, ensure_ascii=False),
                seen_at.isoformat(),
            ),
        )
        self._connection.commit()
        return cursor.rowcount == 1

    def count(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) FROM jobs").fetchone()
        return int(row[0]) if row is not None else 0
