"""S25 lifecycle and log proofs through the existing PIP services."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from typing import Any, NamedTuple

import pytest
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.test import Client, override_settings

from methodology.llm.base import LLMError, LLMResponse
from methodology.models import (
    Activity,
    AgentInteraction,
    ExpertProfile,
    KarmaAward,
    PipChange,
    PlaybookVersion,
    ProcessImprovementProposal,
)
from methodology.services.experts_service import ExpertsService
from methodology.services.pip_service import PIPService
from tests.support.experts_data import seed_s27_summary_privacy_variant
from tests.support.experts_logs import capture_experts_logs
from tests.support.experts_summary_data import (
    SUMMARY_CHANGE_BODY,
    SUMMARY_PIP_BODY,
    SUMMARY_PIP_TITLE,
    SUMMARY_SCRIPTS,
    load_summary_script,
    prepare_summary_submission,
    summary_processing_scope,
)
from tests.support.log_story import assert_log_story
from tests.support.scripted_llm import ScriptedLLM

_INITIAL_RUN = "s25-initial"
_RESUBMISSION_RUN = "s25-resubmission"
_HAPPY_SCRIPT = "PRF-EXPERTS-01/resubmission_happy.json"
_FAILURE_SCRIPT = "PRF-EXPERTS-02/resubmission_reject_provider.json"
_REVISED_BODY = "Unpublished revision clarifying the screen reader recovery rationale."
_INITIAL_REASONING = "The proposed activity fits the review workflow."
_REVISED_REASONING = "The revised proposal clarifies recovery in the review workflow."
_SUMMARY_SERVICE = "ContributionSummaryService.refresh_for_submission"
_SUMMARY_BOUNDARY = "PublicContributionSummaryBoundary.complete"
_REVERT = "PIPService.revert_to_draft"
_LOGGERS = (
    "methodology.services.pip_service",
    "methodology.services.galdr_engine",
    "methodology.services.galdr_client",
    "methodology.services.contribution_summary_service",
    "methodology.services.contribution_summary_boundary",
    "methodology.services.public_contribution_evidence",
    "methodology.services.contribution_summary_prompts",
    "tests.support.scripted_llm",
)

_ProcessingScript = tuple[LLMResponse | LLMError, ...]
_LogBeat = tuple[str, tuple[str, ...]]


class _DomainState(NamedTuple):
    """Fields that submission and withdrawal must leave untouched."""

    awards: tuple[tuple[object, ...], ...]
    points: int
    version: Decimal
    activities: tuple[tuple[object, ...], ...]
    publication_receipts: tuple[tuple[object, ...], ...]
    decision: tuple[datetime | None, str, str]


@pytest.fixture
def s25_case() -> tuple[Mapping[str, Any], ProcessImprovementProposal]:
    """Prepare a real Cedar draft and existing exclusion sentinels.

    :return: Cedar privacy case and Maria's draft. Example: (cedar, pip).
    :raises ValueError: If the restored Cedar data or real target is invalid.
    """
    cedar = seed_s27_summary_privacy_variant()
    return cedar, prepare_summary_submission(cedar["dataset"])


def _domain_state(pip: ProcessImprovementProposal) -> _DomainState:
    """Read award, published content/version and decision state for comparison."""
    pip.refresh_from_db()
    pip.playbook.refresh_from_db()
    change = pip.changes.get()
    return _DomainState(
        tuple(KarmaAward.objects.order_by("pk").values_list()),
        ExpertsService().project_user(pip.created_by_id).total_points,
        pip.playbook.version,
        tuple(
            Activity.objects.filter(workflow__playbook_id=pip.playbook_id)
            .order_by("pk")
            .values_list()
        ),
        tuple(
            PlaybookVersion.objects.filter(playbook_id=pip.playbook_id)
            .order_by("pk")
            .values_list()
        ),
        (pip.decided_at, change.admin_decision, change.admin_note),
    )


def _submit_review(
    pip: ProcessImprovementProposal, correlation: str, reasoning: str, *, holistic: bool
) -> ExpertProfile:
    """Submit through the real scheduler and check the persisted assessment."""
    reviewed = PIPService.submit_for_review(
        actor=pip.created_by, pip=pip, correlation_id=correlation
    )
    pip.refresh_from_db()
    change = pip.changes.get()
    assert reviewed.pk == pip.pk
    assert reviewed.status == pip.status == pip.STATUS_REVIEWED
    assert pip.submitted_at is not None and pip.reviewed_at is not None
    assert bool(pip.galdr_holistic_assessment) is holistic
    assert (change.galdr_recommendation, change.galdr_reasoning) == (
        PipChange.GALDR_ACCEPT,
        reasoning,
    )
    return ExpertProfile.objects.get(user_id=pip.created_by_id)


def _withdraw_and_edit(
    pip: ProcessImprovementProposal, llm: ScriptedLLM, first: ExpertProfile
) -> None:
    """Return Reviewed to Draft, verify assessments clear and save a real edit."""
    first_calls = llm.calls
    first_interactions = tuple(AgentInteraction.objects.order_by("pk").values_list())
    PIPService.revert_to_draft(pip, pip.created_by)
    pip.refresh_from_db()
    change = pip.changes.get()
    assert pip.status == pip.STATUS_DRAFT
    assert pip.galdr_holistic_assessment == ""
    assert change.galdr_recommendation == change.galdr_reasoning == ""
    PIPService.save_draft_header(
        actor=pip.created_by, pip=pip, title=pip.title, summary=_REVISED_BODY
    )
    assert llm.calls == first_calls
    assert (
        tuple(AgentInteraction.objects.order_by("pk").values_list())
        == first_interactions
    )
    assert ExpertProfile.objects.values().get(pk=first.pk) == _profile_values(first)


def _profile_values(profile: ExpertProfile) -> dict[str, object]:
    """Compare all persisted profile fields, including the last-good timestamp."""
    return {
        field.attname: getattr(profile, field.attname)
        for field in ExpertProfile._meta.concrete_fields
    }


def _assert_run_identities(
    pip: ProcessImprovementProposal, initial: AgentInteraction
) -> AgentInteraction:
    """Require two independent, persisted interactions for the same proposal."""
    first, second = AgentInteraction.objects.order_by("pk")
    assert first.pk == initial.pk
    assert first.call_id and second.call_id and first.call_id != second.call_id
    assert first.correlation_id == _INITIAL_RUN
    assert second.correlation_id == _RESUBMISSION_RUN
    for interaction in (first, second):
        assert interaction.pip_id == pip.pk
        assert interaction.subject_id == pip.created_by_id
        assert interaction.workflow_id == "contribution_summary"
    return second


def _assert_initial_refresh(
    first: ExpertProfile, response: LLMResponse, interaction: AgentInteraction
) -> None:
    """Prove the first summary succeeded before withdrawal."""
    assert first.contribution_summary == response.content
    assert first.summary_updated_at is not None
    assert first.summary_status == ExpertProfile.SummaryStatus.SUCCESS
    assert first.last_summary_correlation_id == _INITIAL_RUN
    assert first.summary_error_code == interaction.error_code == ""
    assert interaction.outcome == AgentInteraction.Outcome.SUCCESS
    assert interaction.correlation_id == _INITIAL_RUN


def _assert_second_refresh(
    first: ExpertProfile,
    second: ExpertProfile,
    response: LLMResponse | LLMError,
    interaction: AgentInteraction,
) -> None:
    """Check the fresh replacement or the retained last good text and time."""
    assert second.last_summary_correlation_id == _RESUBMISSION_RUN
    if isinstance(response, LLMError):
        assert second.contribution_summary == first.contribution_summary
        assert second.summary_updated_at == first.summary_updated_at
        assert second.summary_status == ExpertProfile.SummaryStatus.FAILURE
        assert second.summary_error_code == interaction.error_code == "provider_failed"
        assert interaction.outcome == AgentInteraction.Outcome.FAILURE
        return
    assert second.contribution_summary == response.content
    assert second.summary_updated_at > first.summary_updated_at
    assert second.summary_status == ExpertProfile.SummaryStatus.SUCCESS
    assert second.summary_error_code == interaction.error_code == ""
    assert interaction.outcome == AgentInteraction.Outcome.SUCCESS


def _run_resubmission(
    pip: ProcessImprovementProposal, script: _ProcessingScript, *, holistic: bool = True
) -> None:
    """Execute both normal service cycles through the same finite model port."""
    baseline = _domain_state(pip)
    assert (baseline.points, baseline.version) == (8200, Decimal("2.0"))
    assert baseline.decision == (None, PipChange.ADMIN_UNSET, "")
    assert baseline.awards and baseline.activities
    assert not Activity.objects.filter(
        workflow__playbook_id=pip.playbook_id, name=SUMMARY_PIP_TITLE
    ).exists()
    initial_summary, _, refreshed_summary, _ = script
    assert isinstance(initial_summary, LLMResponse)
    with (
        summary_processing_scope(script) as llm,
        override_settings(GALDR_USE_TARGET_STATE=holistic),
    ):
        first = _submit_review(pip, _INITIAL_RUN, _INITIAL_REASONING, holistic=holistic)
        first_interaction = AgentInteraction.objects.get(pip=pip)
        _assert_initial_refresh(first, initial_summary, first_interaction)
        assert len(llm.calls) == 2 and _domain_state(pip) == baseline
        _withdraw_and_edit(pip, llm, first)
        assert _domain_state(pip) == baseline
        second = _submit_review(
            pip, _RESUBMISSION_RUN, _REVISED_REASONING, holistic=holistic
        )
    assert len(llm.calls) == 4 and _domain_state(pip) == baseline
    interaction = _assert_run_identities(pip, first_interaction)
    _assert_second_refresh(first, second, refreshed_summary, interaction)


def _assert_ordered_log_story(
    caplog: pytest.LogCaptureFixture, beats: tuple[_LogBeat, ...]
) -> None:
    """Check each shared log-story beat and require chronological order."""
    messages = (
        record.getMessage()
        for record in caplog.records
        if record.levelno >= logging.INFO
    )
    for where, fragments in beats:
        assert_log_story(caplog, where=where, beats={fragments[0]: fragments})
        assert any(
            where in message and all(fragment in message for fragment in fragments)
            for message in messages
        ), f"Out-of-order log beat {where}: {fragments}"


def _cycle_log_beats(
    pip: ProcessImprovementProposal, correlation: str, *, failure: bool = False
) -> tuple[_LogBeat, ...]:
    """Provide observed production log signatures scoped to one refresh run."""
    run = f"correlation_id={correlation}"
    pip_id = f"pip_id={pip.pk}"
    subject = f"subject_id={pip.created_by_id}"
    beats = (
        (_SUMMARY_SERVICE, ("| entry |", pip_id, subject, run)),
        (_SUMMARY_SERVICE, ("| config |", "tools=none", "model=scripted", run)),
        (
            _SUMMARY_BOUNDARY,
            ("| processing |", "tools=none", "max_tokens=1024", subject, run),
        ),
    )
    if failure:
        beats += (
            (_SUMMARY_SERVICE, ("| error |", "reason_code=provider_failed", run)),
            (
                _SUMMARY_SERVICE,
                ("| branch |", "last_good_retained=true", "karma_awarded=0", run),
            ),
            (
                _SUMMARY_SERVICE,
                ("| exit |", "outcome=failure", "summary_updated=false", run),
            ),
        )
    else:
        beats += (
            (
                _SUMMARY_SERVICE,
                ("| validation |", "status=accepted", "sentence_count=2", run),
            ),
            (
                _SUMMARY_SERVICE,
                (
                    "| exit |",
                    "outcome=success",
                    "summary_updated=true",
                    "karma_awarded=0",
                    run,
                ),
            ),
        )
    return (*beats, ("Galdr persisted", (f"pip id={pip.pk}", "reviewed")))


def _assert_resubmission_logs(
    caplog: pytest.LogCaptureFixture,
    pip: ProcessImprovementProposal,
    cedar: Mapping[str, Any],
    script: _ProcessingScript,
) -> None:
    """Assert both refresh stories enclose the real withdrawal log in order."""
    pip_id = f"pip={pip.pk}"
    revert_beats = (
        (_REVERT, (" entry ", pip_id, f"actor={pip.created_by_id}", "status=reviewed")),
        (_REVERT, (" validation allowed", pip_id, "status=reviewed")),
        (_REVERT, (" processing ", pip_id, "changes_cleared=1")),
        (_REVERT, (" exit ", pip_id, "status=draft")),
    )
    _assert_ordered_log_story(
        caplog,
        (
            *_cycle_log_beats(pip, _INITIAL_RUN),
            *revert_beats,
            *_cycle_log_beats(
                pip, _RESUBMISSION_RUN, failure=isinstance(script[2], LLMError)
            ),
        ),
    )
    _assert_logs_exclude_bodies(caplog, cedar, script)


def _assert_logs_exclude_bodies(
    caplog: pytest.LogCaptureFixture,
    cedar: Mapping[str, Any],
    script: _ProcessingScript,
) -> None:
    """Require body-free logs across assessment and public refresh services."""
    excluded = (
        *cedar["sentinels"],
        SUMMARY_PIP_TITLE,
        SUMMARY_PIP_BODY,
        SUMMARY_CHANGE_BODY,
        _REVISED_BODY,
        _INITIAL_REASONING,
        _REVISED_REASONING,
        "BEGIN PUBLIC EVIDENCE JSON",
        *(turn.content for turn in script if isinstance(turn, LLMResponse)),
    )
    assert not any(text in caplog.text for text in excluded)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("target_state", [True, False])
def test_s25_resubmit_with_reviewed_pip_refreshes_without_award(
    target_state: bool,
    s25_case: tuple[Mapping[str, Any], ProcessImprovementProposal],
    mailoutbox: list[EmailMessage],
) -> None:
    """Prove two normal processing cycles and zero lifecycle awards.

    :param target_state: Existing assessment mode. Example: True.
    :param s25_case: Imported Cedar fixture and real draft.
    :param mailoutbox: Captured Django mail for the test.
    :return: None. Example: None after four-call and ledger assertions.
    :raises AssertionError: For bypassed transitions, missing refresh or an award.
    """
    _, pip = s25_case
    script = load_summary_script(SUMMARY_SCRIPTS / _HAPPY_SCRIPT, pip.changes.get().pk)
    first, _, second, _ = script
    assert isinstance(first, LLMResponse) and isinstance(second, LLMResponse)
    assert first.content != second.content
    _run_resubmission(pip, script, holistic=target_state)
    assert not mailoutbox


@pytest.mark.django_db(transaction=True)
def test_s25_resubmit_with_identical_valid_summary_records_new_refresh(
    s25_case: tuple[Mapping[str, Any], ProcessImprovementProposal],
    mailoutbox: list[EmailMessage],
) -> None:
    """Prove repeated valid text still has a genuine new refresh interaction.

    :param s25_case: Imported Cedar fixture and real draft.
    :param mailoutbox: Captured Django mail for the test.
    :return: None. Example: None after second request/interaction assertions.
    :raises AssertionError: If equal prose suppresses the required refresh.
    """
    _, pip = s25_case
    first, first_assessment, _, second_assessment = load_summary_script(
        SUMMARY_SCRIPTS / _HAPPY_SCRIPT, pip.changes.get().pk
    )
    _run_resubmission(pip, (first, first_assessment, first, second_assessment))
    assert not mailoutbox


@pytest.mark.django_db(transaction=True)
def test_s25_submit_with_reviewed_or_foreign_actor_rejects_before_refresh(
    s25_case: tuple[Mapping[str, Any], ProcessImprovementProposal],
    mailoutbox: list[EmailMessage],
) -> None:
    """Prove Reviewed direct-submit and nonowner withdrawal remain rejected.

    :param s25_case: Imported Cedar fixture and real draft.
    :param mailoutbox: Captured Django mail for the test.
    :return: None. Example: None after unchanged state and call-count assertions.
    :raises AssertionError: For unauthorized transition or extra model use.
    """
    cedar, pip = s25_case
    foreign_actor = cedar["dataset"].users_by_username["hkim"]
    script = load_summary_script(SUMMARY_SCRIPTS / _HAPPY_SCRIPT, pip.changes.get().pk)
    baseline = _domain_state(pip)
    with (
        summary_processing_scope(script[:2]) as llm,
        override_settings(GALDR_USE_TARGET_STATE=True),
    ):
        first = _submit_review(pip, _INITIAL_RUN, _INITIAL_REASONING, holistic=True)
        interaction_rows = tuple(AgentInteraction.objects.order_by("pk").values_list())
        assert len(interaction_rows) == 1
        with pytest.raises(ValidationError, match="only allowed from Draft"):
            PIPService.submit_for_review(
                actor=pip.created_by, pip=pip, correlation_id=_RESUBMISSION_RUN
            )
        with pytest.raises(ValidationError, match="Only the submitter"):
            PIPService.revert_to_draft(pip, foreign_actor)
    assert _domain_state(pip) == baseline
    assert pip.status == pip.STATUS_REVIEWED
    assert ExpertProfile.objects.values().get(pk=first.pk) == _profile_values(first)
    assert (
        tuple(AgentInteraction.objects.order_by("pk").values_list()) == interaction_rows
    )
    assert len(llm.calls) == 2
    assert not mailoutbox


@pytest.mark.django_db(transaction=True)
def test_s25_http_withdraw_and_resubmit_uses_existing_post_routes(
    client: Client,
) -> None:
    """Prove authenticated normal submit/revert/resubmit POST behavior.

    :param client: Real Django client. Example: authenticated Maria session.
    :return: None. Example: None after redirects and persisted-state assertions.
    :raises AssertionError: For bypassed service, publication, decision or award.
    """
    raise NotImplementedError()


@pytest.mark.django_db(transaction=True)
def test_s25_resubmission_log_story_happy(
    caplog: pytest.LogCaptureFixture,
    s25_case: tuple[Mapping[str, Any], ProcessImprovementProposal],
    mailoutbox: list[EmailMessage],
) -> None:
    """Assert real withdrawal and two successful refresh log stories.

    :param caplog: Captured records. Example: scoped INFO service logs.
    :param s25_case: Imported Cedar fixture and real draft.
    :param mailoutbox: Captured Django mail for the test.
    :return: None. Example: None after shared log-story assertions.
    :raises AssertionError: For missing beats or sensitive body leakage.
    """
    cedar, pip = s25_case
    script = load_summary_script(SUMMARY_SCRIPTS / _HAPPY_SCRIPT, pip.changes.get().pk)
    with capture_experts_logs(caplog, _LOGGERS):
        _run_resubmission(pip, script)
    _assert_resubmission_logs(caplog, pip, cedar, script)
    assert not mailoutbox


@pytest.mark.django_db(transaction=True)
def test_s25_resubmission_log_story_reject(
    caplog: pytest.LogCaptureFixture,
    s25_case: tuple[Mapping[str, Any], ProcessImprovementProposal],
    mailoutbox: list[EmailMessage],
) -> None:
    """Assert second-summary failure preserves the first successful paragraph.

    :param caplog: Captured records. Example: safe provider-error reason logs.
    :param s25_case: Imported Cedar fixture and real draft.
    :param mailoutbox: Captured Django mail for the test.
    :return: None. Example: None after failure/retention story assertions.
    :raises AssertionError: For missing recovery evidence or overwritten text.
    """
    cedar, pip = s25_case
    script = load_summary_script(
        SUMMARY_SCRIPTS / _FAILURE_SCRIPT, pip.changes.get().pk
    )
    with capture_experts_logs(caplog, _LOGGERS):
        _run_resubmission(pip, script)
    _assert_resubmission_logs(caplog, pip, cedar, script)
    assert not mailoutbox
