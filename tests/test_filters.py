from linkedin_job_indexer.filters import evaluate
from linkedin_job_indexer.models import FilterConfig, Job


def make_job(*, title: str = "ML Engineer", description: str = "Python and PyTorch") -> Job:
    return Job(
        job_id="1",
        url="https://example.com/1",
        title=title,
        company="Example",
        location="Poland",
        posted_text="1 hour ago",
        posted_date="2026-07-24",
        description=description,
    )


def test_evaluate_rejects_title_keyword() -> None:
    decision = evaluate(
        make_job(title="Principal ML Engineer"),
        FilterConfig(reject_title=("principal",)),
    )

    assert decision.accepted is False
    assert decision.score == 0
    assert decision.reasons == ("title contains rejected keyword: principal",)


def test_evaluate_requires_relevant_keyword_across_title_and_description() -> None:
    config = FilterConfig(required_any=("machine learning", "llm"))

    accepted = evaluate(make_job(description="Build machine learning systems"), config)
    rejected = evaluate(make_job(title="Data Engineer", description="Build ETL pipelines"), config)

    assert accepted.accepted is True
    assert accepted.matched_required == ("machine learning",)
    assert rejected.accepted is False
    assert rejected.reasons == ("no required keyword matched",)


def test_evaluate_scores_unique_boost_keywords_and_applies_minimum() -> None:
    config = FilterConfig(boost=("python", "pytorch", "kubernetes"), min_score=2)

    accepted = evaluate(make_job(description="Python, Python and PyTorch"), config)
    rejected = evaluate(make_job(description="Python only"), config)

    assert accepted.accepted is True
    assert accepted.score == 2
    assert accepted.matched_boost == ("python", "pytorch")
    assert rejected.accepted is False
    assert rejected.reasons == ("score 1 is below minimum 2",)


def test_single_token_keyword_does_not_match_inside_another_word() -> None:
    decision = evaluate(
        make_job(title="Data Engineer", description="Work with HTML documents"),
        FilterConfig(boost=("ml",)),
    )

    assert decision.score == 0
