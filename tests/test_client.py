import httpx
import pytest

from linkedin_job_indexer.client import LinkedInClient
from linkedin_job_indexer.errors import ExtractionBlockedError, ExtractionError
from linkedin_job_indexer.models import RunConfig, SearchConfig


def make_client(handler: httpx.MockTransport) -> LinkedInClient:
    return LinkedInClient(
        RunConfig(request_delay_seconds=0, retries=1),
        transport=handler,
        sleep=lambda _: None,
    )


def test_search_requests_guest_endpoint_with_daily_filters() -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, text="<li>job</li>")

    with make_client(httpx.MockTransport(handle)) as client:
        body = client.search(
            SearchConfig("machine learning engineer", "Poland", remote_only=True), start=25
        )

    assert body == "<li>job</li>"
    params = seen[0].url.params
    assert seen[0].url.path.endswith("/seeMoreJobPostings/search")
    assert params["keywords"] == "machine learning engineer"
    assert params["location"] == "Poland"
    assert params["f_TPR"] == "r108000"
    assert params["sortBy"] == "DD"
    assert params["f_WT"] == "2"
    assert params["start"] == "25"


def test_job_requests_public_detail_endpoint() -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, text="<div class='description'>text</div>")

    with make_client(httpx.MockTransport(handle)) as client:
        client.job("1234567890")

    assert seen[0].url.path.endswith("/jobs-guest/jobs/api/jobPosting/1234567890")


def test_client_retries_server_error() -> None:
    attempts = 0

    def handle(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, text="unavailable")
        return httpx.Response(200, text="ok")

    with make_client(httpx.MockTransport(handle)) as client:
        assert client.job("123") == "ok"

    assert attempts == 2


def test_client_raises_clear_error_for_authwall() -> None:
    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<main class='authwall'>Sign in</main>")

    with make_client(httpx.MockTransport(handle)) as client:
        with pytest.raises(ExtractionBlockedError, match="blocked"):
            client.job("123")


def test_client_raises_after_retries_are_exhausted() -> None:
    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="unavailable")

    with make_client(httpx.MockTransport(handle)) as client:
        with pytest.raises(ExtractionError, match="503"):
            client.job("123")


def test_client_does_not_treat_job_text_about_captcha_as_a_block() -> None:
    body = """
    <div class='show-more-less-html__markup'>
      Build CAPTCHA detection and abuse-prevention systems.
    </div>
    """

    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=body)

    with make_client(httpx.MockTransport(handle)) as client:
        assert client.job("123") == body
