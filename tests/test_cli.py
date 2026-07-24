from pathlib import Path

from linkedin_job_indexer import cli


class FakeLinkedInClient:
    def __init__(self, _: object) -> None:
        pass

    def __enter__(self) -> "FakeLinkedInClient":
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def search(self, _: object, start: int) -> str:
        if start:
            return ""
        return """
        <li><div data-entity-urn="urn:li:jobPosting:1234567890">
          <a href="https://www.linkedin.com/jobs/view/ml-engineer-1234567890"></a>
          <h3>ML Engineer</h3><h4>Example</h4>
          <span class="job-search-card__location">Poland</span>
          <time datetime="2026-07-24">1 hour ago</time>
        </div></li>
        """

    def job(self, _: str) -> str:
        return """
        <div class="show-more-less-html__markup">
          Build machine learning products with Python and PyTorch.
        </div>
        """


def test_cli_runs_pipeline_and_prints_summary(
    tmp_path: Path, monkeypatch: object, capsys: object
) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        """
        [run]
        max_pages = 1
        request_delay_seconds = 0

        [filters]
        required_any = ["machine learning"]
        boost = ["python", "pytorch"]
        min_score = 1

        [[searches]]
        keywords = "machine learning engineer"
        location = "Poland"
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "LinkedInClient", FakeLinkedInClient)

    code = cli.main(
        [
            "run",
            "--config",
            str(config),
            "--db",
            str(tmp_path / "jobs.sqlite3"),
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )

    assert code == 0
    assert (tmp_path / "out" / "jobs.csv").exists()
    assert (tmp_path / "out" / "report.json").exists()
    output = capsys.readouterr().out
    assert "discovered=1" in output
    assert "accepted=1" in output


def test_cli_returns_nonzero_for_invalid_config(tmp_path: Path, capsys: object) -> None:
    config = tmp_path / "config.toml"
    config.write_text("[run]\nmax_pages = 1\n", encoding="utf-8")

    code = cli.main(["run", "--config", str(config)])

    assert code == 1
    assert "at least one" in capsys.readouterr().err
