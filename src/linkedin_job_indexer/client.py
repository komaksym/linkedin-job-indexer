from collections.abc import Callable
import time

import httpx

from linkedin_job_indexer.errors import ExtractionBlockedError, ExtractionError
from linkedin_job_indexer.models import RunConfig, SearchConfig

_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
_JOB_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
_RETRYABLE = {500, 502, 503, 504}
_BLOCKED = {403, 429}
_BLOCK_MARKERS = (
    "authwall",
    "checkpoint/challenge",
    "security verification",
    "captcha",
)


class LinkedInClient:
    def __init__(
        self,
        config: RunConfig,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._sleep = sleep
        self._client = httpx.Client(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 Chrome/150.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
            timeout=config.timeout_seconds,
            transport=transport,
        )

    def __enter__(self) -> "LinkedInClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def search(self, search: SearchConfig, start: int) -> str:
        params: dict[str, str | int] = {
            "keywords": search.keywords,
            "location": search.location,
            "f_TPR": f"r{self._config.window_hours * 3600}",
            "sortBy": "DD",
            "start": start,
        }
        if search.remote_only:
            params["f_WT"] = "2"
        return self._request(_SEARCH_URL, params=params)

    def job(self, job_id: str) -> str:
        return self._request(_JOB_URL.format(job_id=job_id))

    def _request(self, url: str, *, params: dict[str, str | int] | None = None) -> str:
        last_error: Exception | None = None
        for attempt in range(self._config.retries + 1):
            try:
                response = self._client.get(url, params=params)
            except httpx.TransportError as exc:
                last_error = exc
                if attempt < self._config.retries:
                    continue
                raise ExtractionError(f"request failed after {attempt + 1} attempts: {exc}") from exc

            if response.status_code in _BLOCKED:
                raise ExtractionBlockedError(
                    f"LinkedIn blocked the request with HTTP {response.status_code}"
                )
            if response.status_code in _RETRYABLE:
                if attempt < self._config.retries:
                    continue
                raise ExtractionError(
                    f"LinkedIn request failed with HTTP {response.status_code} after "
                    f"{attempt + 1} attempts"
                )
            if response.is_error:
                raise ExtractionError(f"LinkedIn request failed with HTTP {response.status_code}")

            body = response.text
            folded = body.casefold()
            if any(marker in folded for marker in _BLOCK_MARKERS):
                raise ExtractionBlockedError("LinkedIn returned a blocked or challenge page")

            if self._config.request_delay_seconds:
                self._sleep(self._config.request_delay_seconds)
            return body

        raise ExtractionError(f"request failed: {last_error}")
