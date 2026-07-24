import re

from linkedin_job_indexer.models import Decision, FilterConfig, Job

_NON_WORD = re.compile(r"[^\w]+", re.UNICODE)
_SPACES = re.compile(r"\s+")


def _normalize(value: str) -> str:
    return _SPACES.sub(" ", _NON_WORD.sub(" ", value.casefold())).strip()


def _contains(text: str, keyword: str) -> bool:
    normalized_keyword = _normalize(keyword)
    if not normalized_keyword:
        return False
    return f" {normalized_keyword} " in f" {_normalize(text)} "


def _matches(text: str, keywords: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    matches: list[str] = []
    for keyword in keywords:
        if keyword not in seen and _contains(text, keyword):
            seen.add(keyword)
            matches.append(keyword)
    return tuple(matches)


def evaluate(job: Job, config: FilterConfig) -> Decision:
    title_rejections = _matches(job.title, config.reject_title)
    if title_rejections:
        return Decision(
            accepted=False,
            score=0,
            matched_required=(),
            matched_boost=(),
            reasons=tuple(
                f"title contains rejected keyword: {keyword}" for keyword in title_rejections
            ),
        )

    description_rejections = _matches(job.description, config.reject_description)
    if description_rejections:
        return Decision(
            accepted=False,
            score=0,
            matched_required=(),
            matched_boost=(),
            reasons=tuple(
                f"description contains rejected keyword: {keyword}"
                for keyword in description_rejections
            ),
        )

    combined = f"{job.title}\n{job.description}"
    required = _matches(combined, config.required_any)
    if config.required_any and not required:
        return Decision(False, 0, (), (), ("no required keyword matched",))

    boost = _matches(combined, config.boost)
    score = len(boost)
    if score < config.min_score:
        return Decision(
            False,
            score,
            required,
            boost,
            (f"score {score} is below minimum {config.min_score}",),
        )

    return Decision(True, score, required, boost, ())
