import re
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup, Tag

from linkedin_job_indexer.errors import ParsingError
from linkedin_job_indexer.models import Job, JobSummary

_JOB_ID = re.compile(r"(?:jobPosting:|[-/])(\d{6,})(?:[/?#]|$)")


def _text(node: Tag | None) -> str:
    return node.get_text(" ", strip=True) if node is not None else ""


def _job_id(card: Tag, href: str) -> str | None:
    urn = card.get("data-entity-urn", "")
    match = _JOB_ID.search(str(urn)) or _JOB_ID.search(href)
    return match.group(1) if match else None


def _canonical_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def parse_search(html: str) -> list[JobSummary]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: dict[str, JobSummary] = {}

    for item in soup.select("li"):
        card = item.select_one("[data-entity-urn]") or item
        link = card.select_one('a[href*="/jobs/view/"]')
        if link is None:
            continue

        href = str(link.get("href", "")).strip()
        job_id = _job_id(card, href)
        title = _text(card.select_one("h3"))
        if not job_id or not href or not title or job_id in jobs:
            continue

        time = card.select_one("time")
        jobs[job_id] = JobSummary(
            job_id=job_id,
            url=_canonical_url(href),
            title=title,
            company=_text(card.select_one("h4")),
            location=_text(card.select_one(".job-search-card__location")),
            posted_text=_text(time),
            posted_date=str(time.get("datetime", "")) if time is not None else "",
        )

    return list(jobs.values())


def parse_job(html: str, summary: JobSummary) -> Job:
    soup = BeautifulSoup(html, "html.parser")
    description = soup.select_one(
        ".show-more-less-html__markup, .description__text, .jobs-description-content__text"
    )
    text = description.get_text("\n", strip=True) if description is not None else ""
    if len(text) < 40:
        raise ParsingError(f"job {summary.job_id} description was not found")

    return Job(
        job_id=summary.job_id,
        url=summary.url,
        title=summary.title,
        company=summary.company,
        location=summary.location,
        posted_text=summary.posted_text,
        posted_date=summary.posted_date,
        description=text,
    )
