from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchConfig:
    keywords: str
    location: str
    remote_only: bool = False


@dataclass(frozen=True, slots=True)
class FilterConfig:
    required_any: tuple[str, ...] = ()
    reject_title: tuple[str, ...] = ()
    reject_description: tuple[str, ...] = ()
    boost: tuple[str, ...] = ()
    min_score: int = 0


@dataclass(frozen=True, slots=True)
class RunConfig:
    window_hours: int = 30
    max_pages: int = 4
    request_delay_seconds: float = 0.5
    timeout_seconds: float = 30.0
    retries: int = 2
    max_jobs: int = 0


@dataclass(frozen=True, slots=True)
class AppConfig:
    searches: tuple[SearchConfig, ...]
    filters: FilterConfig = FilterConfig()
    run: RunConfig = RunConfig()
