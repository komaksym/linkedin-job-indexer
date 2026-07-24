from pathlib import Path

import pytest

from linkedin_job_indexer.config import ConfigError, load_config


def write_config(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_load_config_parses_searches_filters_and_defaults(tmp_path: Path) -> None:
    path = write_config(
        tmp_path / "config.toml",
        """
        [filters]
        required_any = ["machine learning", "llm"]
        reject_title = ["principal"]
        reject_description = ["security clearance"]
        boost = ["pytorch", "evaluation"]
        min_score = 1

        [[searches]]
        keywords = "machine learning engineer"
        location = "Poland"
        remote_only = true
        """,
    )

    config = load_config(path)

    assert config.run.window_hours == 30
    assert config.run.max_pages == 4
    assert config.run.max_jobs == 0
    assert config.searches[0].keywords == "machine learning engineer"
    assert config.searches[0].location == "Poland"
    assert config.searches[0].remote_only is True
    assert config.filters.required_any == ("machine learning", "llm")
    assert config.filters.min_score == 1


def test_load_config_rejects_missing_searches(tmp_path: Path) -> None:
    path = write_config(tmp_path / "config.toml", "[run]\nwindow_hours = 24\n")

    with pytest.raises(ConfigError, match="at least one"):
        load_config(path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("window_hours", 0),
        ("max_pages", 0),
        ("timeout_seconds", 0),
        ("retries", -1),
        ("request_delay_seconds", -0.1),
        ("max_jobs", -1),
    ],
)
def test_load_config_rejects_invalid_run_values(
    tmp_path: Path, field: str, value: int | float
) -> None:
    path = write_config(
        tmp_path / "config.toml",
        f"""
        [run]
        {field} = {value}

        [[searches]]
        keywords = "AI engineer"
        location = "Europe"
        """,
    )

    with pytest.raises(ConfigError, match=field):
        load_config(path)
