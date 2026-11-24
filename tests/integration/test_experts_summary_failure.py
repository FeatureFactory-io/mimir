"""S29 real normal-lifecycle failure retention, assessment and log certification."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from methodology.llm.base import LLMResponse
from methodology.models import AgentInteraction, ExpertProfile, PipChange
from methodology.services.contribution_summary_prompts import _count_sentences
from methodology.services.experts_service import ExpertsService
from tests.support.experts_logs import capture_experts_logs
from tests.support.experts_summary_data import SUMMARY_SCRIPTS, load_summary_script
from tests.support.experts_summary_failure_data import (
    S29_CODES,
    S29_FAILURES,
    S29_LOGGERS,
    assert_s29_domain_unchanged,
    assert_s29_failure_trace,
    assert_s29_log_story,
    assert_s29_requests,
    assert_s29_retention,
    load_s29_submission_model,
    prepare_s29_failure_case,
    submit_s29_case,
)


@pytest.fixture
def s29_log_capture(
    caplog: pytest.LogCaptureFixture,
) -> Iterator[pytest.LogCaptureFixture]:
    """Enable actual disabled loggers and restore their state on fixture exit.

    :param caplog: Actual pytest capture. Example: caplog fixture.
    :return: Enabled INFO capture context. Example: yielded caplog.
    :raises ValueError: For invalid named logger configuration.
    """
    with capture_experts_logs(caplog, S29_LOGGERS):
        yield caplog


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("failure", S29_FAILURES)
def test_s29_submission_with_summary_failure_retains_last_good(failure: str) -> None:
    """Certify provider/empty/fifteen-sentence/markup/truncation failures.

    :param failure: Finite explicit adverse script. Example: "overlong".
    :return: None. Example: nine-sentence paragraph and success timestamp unchanged.
    :raises AssertionError: For lost history, malformed failure metadata or domain drift.
    """
    case = prepare_s29_failure_case()
    assert case.successful_at is not None and _count_sentences(case.paragraph) == 9
    llm = load_s29_submission_model(case, failure)
    if failure == "overlong":
        path = SUMMARY_SCRIPTS / "PRF-EXPERTS-02/s29_overlong.json"
        turn = load_summary_script(path, case.pip.changes.get().pk)[0]
        assert isinstance(turn, LLMResponse) and _count_sentences(turn.content) == 15
    interaction = submit_s29_case(case, llm, f"s29-{failure}")
    assert_s29_retention(case, interaction, S29_CODES[failure])
    assert AgentInteraction.objects.filter(pip=case.pip).count() == 1
    assert case.pip.status == case.pip.STATUS_REVIEWED
    assert_s29_requests(case, llm)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("holistic", (True, False), ids=("holistic", "per-change"))
def test_s29_submission_with_summary_failure_continues_existing_assessment(
    holistic: bool,
) -> None:
    """Run both original assessment modes after an actual failed summary.

    :param holistic: Existing mode, not new orchestration. Example: False.
    :return: None. Example: two real calls, Reviewed and no applied ADD/award.
    :raises AssertionError: For changed parser, skipped assessment or extra call.
    """
    case = prepare_s29_failure_case()
    llm = load_s29_submission_model(case, "provider")
    interaction = submit_s29_case(case, llm, "s29-assessment", holistic=holistic)
    assert case.pip.status == case.pip.STATUS_REVIEWED
    assert bool(case.pip.galdr_holistic_assessment) is holistic
    assert case.pip.reviewed_at is not None
    change = case.pip.changes.get()
    assert change.galdr_recommendation == PipChange.GALDR_ACCEPT
    assert change.galdr_reasoning == "The proposed activity fits the review workflow."
    assert_s29_retention(case, interaction, "provider_failed")
    assert_s29_requests(case, llm, holistic=holistic)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("holistic", (True, False), ids=("holistic", "per-change"))
def test_s29_submission_with_assessment_failure_uses_existing_retry(
    holistic: bool,
) -> None:
    """Recover only through explicit normal Submitted retry after both errors.

    :param holistic: Existing assessment parser. Example: True.
    :return: None. Example: Submitted then Reviewed, four calls, no domain award.
    :raises AssertionError: For hidden retry, new provider loop or replaced old history.
    """
    case = prepare_s29_failure_case()
    llm = load_s29_submission_model(case, "retry")
    first = submit_s29_case(case, llm, "s29-retry-first", holistic=holistic)
    assert case.pip.status == case.pip.STATUS_SUBMITTED and len(llm.calls) == 2
    assert case.pip.reviewed_at is None
    assert_s29_retention(case, first, "provider_failed")
    assert_s29_failure_trace(case, first, "provider_failed")
    second = submit_s29_case(case, llm, "s29-retry-explicit", holistic=holistic)
    assert case.pip.status == case.pip.STATUS_REVIEWED and len(llm.calls) == 4
    assert case.pip.changes.get().galdr_recommendation == PipChange.GALDR_ACCEPT
    assert second.outcome == AgentInteraction.Outcome.SUCCESS
    assert first.pk != second.pk and first.call_id != second.call_id
    assert AgentInteraction.objects.filter(pip=case.pip).count() == 2
    profile = ExpertProfile.objects.get(pk=case.profile.pk)
    assert (
        profile.contribution_summary
        == "Maria maintains Accessibility Audit Playbook. She contributed Keyboard Navigation Audit to a published playbook."
    )
    assert profile.summary_updated_at > case.successful_at
    assert profile.summary_status == ExpertProfile.SummaryStatus.SUCCESS
    assert profile.summary_error_code == ""
    assert profile.last_summary_correlation_id == second.correlation_id
    assert tuple(call.max_tokens for call in llm.calls) == (
        1024,
        16384 if holistic else 4096,
        1024,
        16384 if holistic else 4096,
    )
    assert_s29_domain_unchanged(case)


@pytest.mark.django_db(transaction=True)
def test_s29_submission_with_missing_last_good_preserves_empty_state() -> None:
    """Keep missing prose/null time while live numeric projection remains usable.

    :return: None. Example: empty paragraph, null timestamp, live8200 and original counts.
    :raises AssertionError: For fabricated fallback prose or changed counts/domain state.
    """
    case = prepare_s29_failure_case(has_last_good=False)
    llm = load_s29_submission_model(case, "provider")
    interaction = submit_s29_case(case, llm, "s29-no-last-good")
    assert_s29_retention(case, interaction, "provider_failed")
    assert case.paragraph == "" and case.successful_at is None
    assert_s29_failure_trace(case, interaction, "provider_failed")
    projection = ExpertsService().project_user(case.pip.created_by_id)
    assert projection.total_points == 8200
    assert projection.released_public_playbook_count == 1
    assert projection.successful_gui_copy_count == 0
    assert case.pip.status == case.pip.STATUS_REVIEWED
    assert_s29_requests(case, llm)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("has_last_good", (True, False), ids=("retained", "absent"))
def test_s29_summary_log_story_reject(
    s29_log_capture: pytest.LogCaptureFixture, has_last_good: bool
) -> None:
    """Prove exact correlated failure/retention/exit beats without raw bodies.

    :param s29_log_capture: Actual enabled INFO logs. Example: caplog.
    :param has_last_good: Independent prior-history case. Example: False.
    :return: None. Example: safe reason and retained=true/false, no secret prose.
    :raises AssertionError: If a beat, correlation or privacy requirement differs.
    """
    case = prepare_s29_failure_case(has_last_good=has_last_good)
    llm = load_s29_submission_model(case, "provider")
    s29_log_capture.clear()
    correlation = "s29-log-failure"
    interaction = submit_s29_case(case, llm, correlation)
    assert_s29_log_story(s29_log_capture, case, interaction)
    text = "\n".join(record.getMessage() for record in s29_log_capture.records)
    excluded = (
        *case.sentinels,
        "s29_private_provider_failure_marker",
        llm.calls[0].system,
        llm.calls[0].messages[0].content,
        case.paragraph,
    )
    assert all(value not in text for value in excluded if value)
    assert_s29_retention(case, interaction, "provider_failed")
