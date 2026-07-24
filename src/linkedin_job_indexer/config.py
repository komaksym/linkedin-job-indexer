from collections.abc import Mapping
from pathlib import Path
from typing import Any
import tomllib

from linkedin_job_indexer.models import AppConfig, FilterConfig, RunConfig, SearchConfig


class ConfigError(ValueError):
    """Raised when the TOML configuration is invalid."""


def _table(value: object, name: str) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ConfigError(f"{name} must be a TOML table")
    return value


def _strings(value: object, name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{name} must be an array of strings")
    return tuple(item.strip().casefold() for item in value if item.strip())


def _string(table: Mapping[str, Any], name: str) -> str:
    value = table.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} must be a non-empty string")
    return value.strip()


def _int(table: Mapping[str, Any], name: str, default: int, minimum: int) -> int:
    value = table.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ConfigError(f"{name} must be an integer >= {minimum}")
    return value


def _number(table: Mapping[str, Any], name: str, default: float, minimum: float) -> float:
    value = table.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int | float) or value < minimum:
        raise ConfigError(f"{name} must be a number >= {minimum}")
    return float(value)


def load_config(path: Path) -> AppConfig:
    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"cannot read config {path}: {exc}") from exc

    raw_searches = raw.get("searches")
    if not isinstance(raw_searches, list) or not raw_searches:
        raise ConfigError("config must define at least one [[searches]] entry")

    searches: list[SearchConfig] = []
    for index, raw_search in enumerate(raw_searches):
        table = _table(raw_search, f"searches[{index}]")
        remote_only = table.get("remote_only", False)
        if not isinstance(remote_only, bool):
            raise ConfigError(f"searches[{index}].remote_only must be a boolean")
        searches.append(
            SearchConfig(
                keywords=_string(table, "keywords"),
                location=_string(table, "location"),
                remote_only=remote_only,
            )
        )

    raw_filters = _table(raw.get("filters"), "filters")
    filters = FilterConfig(
        required_any=_strings(raw_filters.get("required_any"), "filters.required_any"),
        reject_title=_strings(raw_filters.get("reject_title"), "filters.reject_title"),
        reject_description=_strings(
            raw_filters.get("reject_description"), "filters.reject_description"
        ),
        boost=_strings(raw_filters.get("boost"), "filters.boost"),
        min_score=_int(raw_filters, "min_score", 0, 0),
    )

    raw_run = _table(raw.get("run"), "run")
    run = RunConfig(
        window_hours=_int(raw_run, "window_hours", 30, 1),
        max_pages=_int(raw_run, "max_pages", 4, 1),
        request_delay_seconds=_number(raw_run, "request_delay_seconds", 0.5, 0.0),
        timeout_seconds=_number(raw_run, "timeout_seconds", 30.0, 0.1),
        retries=_int(raw_run, "retries", 2, 0),
        max_jobs=_int(raw_run, "max_jobs", 0, 0),
    )

    return AppConfig(searches=tuple(searches), filters=filters, run=run)
