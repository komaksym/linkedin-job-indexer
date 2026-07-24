import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from linkedin_job_indexer.client import LinkedInClient
from linkedin_job_indexer.config import load_config
from linkedin_job_indexer.errors import ConfigError, JobIndexerError
from linkedin_job_indexer.pipeline import run_pipeline
from linkedin_job_indexer.store import JobStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linkedin-jobs",
        description="Index and filter recent public LinkedIn job postings.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run the daily indexing pipeline")
    run.add_argument(
        "--config",
        type=Path,
        default=Path("config.toml"),
        help="TOML configuration path (default: config.toml)",
    )
    run.add_argument(
        "--db",
        type=Path,
        default=Path(".data/jobs.sqlite3"),
        help="SQLite state path (default: .data/jobs.sqlite3)",
    )
    run.add_argument(
        "--out-dir",
        type=Path,
        default=Path("out"),
        help="CSV/JSON output directory (default: out)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "run":
        return 2

    try:
        config = load_config(args.config)
        with LinkedInClient(config.run) as client, JobStore(args.db) as store:
            report = run_pipeline(config, store, args.out_dir, client)
    except (ConfigError, JobIndexerError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        " ".join(
            (
                f"discovered={report.discovered}",
                f"new={report.unseen}",
                f"accepted={report.accepted}",
                f"rejected={report.rejected}",
                f"seen={report.skipped_seen}",
                f"failed={report.failed}",
            )
        )
    )
    print(f"results={args.out_dir / 'jobs.csv'}")
    print(f"report={args.out_dir / 'report.json'}")
    return 0
