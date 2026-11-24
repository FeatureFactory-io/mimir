"""S29 real Cedar failure-case setup; only the finite model transport is scripted."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from django.core import mail
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

from methodology.models import (
    Activity,
    AgentInteraction,
    ExpertProfile,
    KarmaAward,
    Playbook,
    PlaybookVersion,
    ProcessImprovementProposal,
)
from methodology.services.contribution_summary_boundary import (
    PublicContributionSummaryBoundary,
    SummaryBoundaryError,
    trace_as_agent_story,
)
from methodology.services.experts_service import ExpertsService
from methodology.services.galdr_prompts import HOLISTIC_SYSTEM_PROMPT, SYSTEM_PROMPT
from methodology.services.pip_service import PIPService
from methodology.services.public_contribution_evidence import (
    PublicContributionEvidenceService,
)
from tests.support.agent_story import assert_agent_story
from tests.support.experts_data import CedarDataset, seed_s27_summary_privacy_variant
from tests.support.experts_summary_data import (
    SUMMARY_CHANGE_BODY,
    SUMMARY_PIP_BODY,
    SUMMARY_PIP_TITLE,
    SUMMARY_SCRIPTS,
    load_summary_script,
    prepare_summary_submission,
)
from tests.support.log_story import assert_log_story
from tests.support.scripted_llm import ScriptedLLM

S29_FAILURES = ("provider", "empty", "overlong", "markup", "truncated")
S29_CODES = {
    name: "provider_failed" if name == "provider" else "output_validation_failed"
    for name in S29_FAILURES
}
S29_LOGGERS = (
    "methodology.services.pip_service",
    "methodology.services.galdr_engine",
    "methodology.services.galdr_client",
    "methodology.services.contribution_summary_service",
    "methodology.services.contribution_summary_boundary",
    "methodology.services.public_contribution_evidence",
    "methodology.services.contribution_summary_prompts",
    "tests.support.scripted_llm",
)
_SUCCESSFUL_AT = datetime(2026, 11, 23, 8, 0, tzinfo=UTC)

_FAILURE_ORDER = (
    "entry",
    "entry",
    "public_evidence",
    "llm_call",
    "failure",
    "exit",
    "failure",
    "exit",
)
_BOUNDARY_FAILURE_ORDER = ("entry", "public_evidence", "llm_call", "failure", "exit")
_RECOVERED_SUMMARY = "Maria maintains Accessibility Audit Playbook. She contributed Keyboard Navigation Audit to a published playbook."
_TRACE_BEATS = {
    "entry": ("subject_id={subject}", "correlation_id={correlation}"),
    "public_evidence": ("scope=public_released", "public_playbook_ids="),
    "llm_call": ("model=scripted", "tools=none", "max_tokens=1024"),
    "failure": ("reason_code={code}",),
    "exit": (
        "outcome=failure",
        "summary_updated=false",
        "karma_awarded=0",
        "pip_lifecycle=unchanged",
    ),
}
_TELEMETRY_EXCLUSIONS = (
    SUMMARY_PIP_TITLE,
    SUMMARY_PIP_BODY,
    SUMMARY_CHANGE_BODY,
    "Foundation policy:",
    "BEGIN PUBLIC EVIDENCE JSON",
    "Accessibility Audit Playbook",
    "s29_private_provider_failure_marker",
)
_SERVICE = "ContributionSummaryService.refresh_for_submission"
_BOUNDARY = "PublicContributionSummaryBoundary.complete"
_LOG_BEATS = (
    (
        _SERVICE,
        "entry",
        (
            "| entry |",
            "pip_id={pip}",
            "subject_id={subject}",
            "correlation_id={correlation}",
        ),
    ),
    (
        _SERVICE,
        "branch",
        (
            "| branch |",
            "last_good_retained={retained}",
            "karma_awarded=0",
            "correlation_id={correlation}",
        ),
    ),
    (
        _SERVICE,
        "exit",
        (
            "| exit |",
            "summary_updated=false",
            "outcome=failure",
            "interaction_id={interaction}",
            "pip_lifecycle=unchanged",
            "correlation_id={correlation}",
        ),
    ),
    (
        _BOUNDARY,
        "processing",
        (
            "| processing |",
            "model=scripted",
            "tools=none",
            "correlation_id={correlation}",
        ),
    ),
    (
        _BOUNDARY,
        "error",
        (
            "| error |",
            "outcome=failure",
            "reason_code=provider_failed",
            "correlation_id={correlation}",
        ),
    ),
)
_READ_ONLY_SQL = frozenset({"SELECT", "BEGIN", "COMMIT", "SAVEPOINT", "RELEASE"})


@dataclass(frozen=True)
class S29FailureCase:
    """Real ORM handles and immutable independent pre-attempt comparison values."""

    cedar: CedarDataset
    pip: ProcessImprovementProposal
    profile: ExpertProfile
    paragraph: str
    successful_at: datetime | None
    award_ids: tuple[int, ...]
    domain: tuple[tuple[tuple[object, ...], ...], ...]
    sentinels: tuple[str, ...]


def prepare_s29_failure_case(*, has_last_good: bool = True) -> S29FailureCase:
    """Restore Cedar and create an actual Maria draft/ADD through S23 builders.

    :param has_last_good: Prior successful fixture exists. Example: True.
    :return: Real case with exact old text/time. Example: Maria's nine sentences.
    :raises ValueError: For a non-boolean history flag or invalid real baseline.
    """
    if type(has_last_good) is not bool:
        raise ValueError("The last-good fixture flag must be boolean.")
    privacy = seed_s27_summary_privacy_variant()
    cedar = privacy["dataset"]
    pip = prepare_summary_submission(cedar)
    profile = ExpertProfile.objects.get(user_id=pip.created_by_id)
    if has_last_good:
        profile.summary_status = ExpertProfile.SummaryStatus.SUCCESS
        profile.summary_updated_at = _SUCCESSFUL_AT
        profile.last_summary_correlation_id = "s29-prior-success"
    else:
        profile.contribution_summary = ""
        profile.summary_status = ExpertProfile.SummaryStatus.NEVER
        profile.summary_updated_at = None
        profile.last_summary_correlation_id = ""
    profile.full_clean()
    profile.save()
    return S29FailureCase(
        cedar,
        pip,
        profile,
        profile.contribution_summary,
        profile.summary_updated_at,
        tuple(KarmaAward.objects.order_by("pk").values_list("pk", flat=True)),
        capture_s29_domain(),
        tuple(privacy["sentinels"]),
    )


def load_s29_submission_model(case: S29FailureCase, script_name: str) -> ScriptedLLM:
    """Load finite S23-normalized turns using this draft's actual change ID.

    :param case: Real Maria draft/ADD case. Example: prepare_s29_failure_case().
    :param script_name: Explicit fixture base. Example: "provider" or "retry".
    :return: Finite captured port. Example: two summary/assessment turns.
    :raises ValueError: For an unknown script or malformed nonempty script data.
    :raises OSError: When the declared fixture cannot be read.
    """
    if script_name not in (*S29_FAILURES, "retry", "exhaustion"):
        raise ValueError("Unknown S29 failure script.")
    path = SUMMARY_SCRIPTS / "PRF-EXPERTS-02" / f"s29_{script_name}.json"
    return ScriptedLLM(load_summary_script(path, case.pip.changes.get().pk))


def capture_s29_domain(
    *, include_summary: bool = False
) -> tuple[tuple[tuple[object, ...], ...], ...]:
    """Snapshot complete protected rows and optionally all summary storage.

    :param include_summary: Include profiles/interactions for read-only proof. Example: True.
    :return: Independent complete rows and mail. Example: all original awards.
    :raises ValueError: For a non-boolean snapshot flag.
    """
    if type(include_summary) is not bool:
        raise ValueError("The summary snapshot flag must be boolean.")
    models = (KarmaAward, Activity, Playbook, PlaybookVersion)
    if include_summary:
        models += (ExpertProfile, AgentInteraction)
    rows = tuple(tuple(model.objects.order_by("pk").values_list()) for model in models)
    return (
        *rows,
        tuple(
            (message.message().as_bytes(),) for message in getattr(mail, "outbox", ())
        ),
    )


def assert_s29_domain_unchanged(case: S29FailureCase) -> None:
    """Require exact domain rows and no decision/apply after normal assessment.

    :param case: Original real case. Example: Maria's draft and baseline snapshots.
    :return: None. Example: target remains Hana's v2.0 and Maria remains 8,200.
    :raises AssertionError: For any award, publication, activity, decision or mail drift.
    """
    assert capture_s29_domain() == case.domain
    assert ExpertsService().project_user(case.pip.created_by_id).total_points == 8200
    assert (
        tuple(KarmaAward.objects.order_by("pk").values_list("pk", flat=True))
        == case.award_ids
    )
    case.pip.refresh_from_db()
    change = case.pip.changes.get()
    assert case.pip.decided_at is None
    assert change.admin_decision == change.admin_note == ""
    assert not PlaybookVersion.objects.filter(pip=case.pip).exists()
    assert case.pip.playbook.version == 2
    assert not Activity.objects.filter(
        workflow__playbook_id=case.pip.playbook_id, name=SUMMARY_PIP_TITLE
    ).exists()


def submit_s29_case(
    case: S29FailureCase, llm: ScriptedLLM, correlation: str, *, holistic: bool = True
) -> AgentInteraction:
    """Run actual eager on-commit submission using only the explicit model port.

    :param case: Real draft/retry proposal. Example: Maria's one-ADD draft.
    :param llm: Finite captured model. Example: failed summary then valid assessment.
    :param correlation: Safe attempt identity. Example: "s29-provider".
    :param holistic: Existing assessment mode. Example: False for per-change.
    :return: Actual persisted summary interaction. Example: failure trace row.
    :raises AssertionError: For wrong proposal identity or changed domain state.
    """
    with override_settings(GALDR_EAGER=True, GALDR_USE_TARGET_STATE=holistic):
        result = PIPService.submit_for_review(
            actor=case.pip.created_by, pip=case.pip, llm=llm, correlation_id=correlation
        )
    case.pip.refresh_from_db()
    assert result.pk == case.pip.pk and result.status == case.pip.status
    assert_s29_domain_unchanged(case)
    return AgentInteraction.objects.get(pip=case.pip, correlation_id=correlation)


def assert_s29_retention(
    case: S29FailureCase, interaction: AgentInteraction, code: str
) -> None:
    """Compare last-good fields separately from new safe failure metadata.

    :param case: Independent prior text/time. Example: nine sentences and a real timestamp.
    :param interaction: Actual persisted attempt. Example: summary failure row.
    :param code: Canonical S27 reason. Example: "provider_failed".
    :return: None. Example: exact old paragraph/time with failure metadata.
    :raises AssertionError: If failure changes history or loses safe correlation.
    """
    profile = ExpertProfile.objects.get(pk=case.profile.pk)
    assert (profile.contribution_summary, profile.summary_updated_at) == (
        case.paragraph,
        case.successful_at,
    )
    assert profile.summary_status == ExpertProfile.SummaryStatus.FAILURE
    assert profile.summary_error_code == interaction.error_code == code
    assert profile.last_summary_correlation_id == interaction.correlation_id
    assert interaction.outcome == AgentInteraction.Outcome.FAILURE
    assert interaction.subject_id == case.pip.created_by_id
    assert interaction.pip_id == case.pip.pk and interaction.call_id
    assert interaction.workflow_id == "contribution_summary"
    assert interaction.latency_ms is not None and interaction.latency_ms >= 0
    assert_s29_domain_unchanged(case)


def assert_s29_requests(
    case: S29FailureCase, llm: ScriptedLLM, *, holistic: bool = True
) -> None:
    """Inspect two actual requests, separating public summary from private review.

    :param case: Real privacy-extended Cedar. Example: Maria with unpublished ADD.
    :param llm: Actual captured queue. Example: summary then private assessment.
    :param holistic: Existing assessment mode. Example: True.
    :return: None. Example: bounded public facts and original assessment policy.
    :raises AssertionError: For bypassed request, privacy leak or an extra model attempt.
    """
    assert len(llm.calls) == 2
    public, private = llm.calls
    assert public.max_tokens == 1024 and len(public.messages) == 1
    assert public.messages[0].role == "user"
    payload = public.messages[0].content.splitlines()[1]
    assert len(payload) <= 24000
    facts = json.loads(payload)["facts"]
    assert any(fact["playbook_id"] == 6101 for fact in facts)
    request = public.system + public.messages[0].content
    excluded = (
        *case.sentinels,
        SUMMARY_PIP_TITLE,
        SUMMARY_PIP_BODY,
        SUMMARY_CHANGE_BODY,
    )
    assert all(value not in request for value in excluded)
    assert (
        "Accessibility Audit Playbook" in request and "Trace Keyboard Focus" in request
    )
    assert (
        "quoted data" in public.system
        and "public contribution summarizer" in public.system
    )
    assert private.max_tokens == (16384 if holistic else 4096)
    assert private.system == (HOLISTIC_SYSTEM_PROMPT if holistic else SYSTEM_PROMPT)
    assert SUMMARY_PIP_TITLE in private.messages[0].content


def assert_s29_failure_trace(
    case: S29FailureCase, interaction: AgentInteraction, code: str
) -> None:
    """Authenticate persisted partial production events, order and body-free state.

    :param case: Real subject/proposal. Example: Maria's one-ADD draft.
    :param interaction: Real failure row. Example: entry through retained exit.
    :param code: Canonical expected code. Example: "output_validation_failed".
    :return: None. Example: no successful validation or domain-write event.
    :raises AssertionError: For reordered events, private text or false success.
    """
    assert tuple(event["beat"] for event in interaction.events) == _FAILURE_ORDER
    context = {
        "subject": case.pip.created_by_id,
        "correlation": interaction.correlation_id,
        "code": code,
    }
    beats = {
        beat: tuple(value.format(**context) for value in parts)
        for beat, parts in _TRACE_BEATS.items()
    }
    actual = {"workflow_id": interaction.workflow_id, "events": interaction.events}
    assert_agent_story(actual, workflow="contribution_summary", beats=beats)
    text = json.dumps(interaction.events)
    assert all(value not in text for value in (*case.sentinels, *_TELEMETRY_EXCLUSIONS))
    assert bool(case.paragraph) == any(
        "last_good_retained=true" in event["details"] for event in interaction.events
    )


def assert_s29_log_story(
    caplog: pytest.LogCaptureFixture,
    case: S29FailureCase,
    interaction: AgentInteraction,
) -> None:
    """Compare actual correlated INFO records against all five declared log rows.

    :param caplog: Enabled actual logger capture. Example: s29_log_capture.
    :param case: Prior history and real subject. Example: Maria with no last good.
    :param interaction: Actual attempt identity. Example: failed summary row.
    :return: None. Example: exact retention=false and safe provider failure logs.
    :raises AssertionError: If any beat or concrete context is missing.
    """
    context = {
        "subject": case.pip.created_by_id,
        "pip": case.pip.pk,
        "correlation": interaction.correlation_id,
        "interaction": interaction.pk,
        "retained": str(bool(case.paragraph)).lower(),
    }
    for where, beat, parts in _LOG_BEATS:
        required = tuple(value.format(**context) for value in parts)
        assert_log_story(caplog, where=where, beats={beat: required})


def assert_s29_exhausted_boundary(case: S29FailureCase) -> None:
    """Consume one finite response, then reject actual exhaustion without writes.

    :param case: Real public Cedar subject. Example: Maria's prior successful profile.
    :return: None. Example: two identical captured requests, second typed failure.
    :raises AssertionError: For default prose, successful failure trace or storage drift.
    """
    llm = load_s29_submission_model(case, "exhaustion")
    boundary = PublicContributionSummaryBoundary(PublicContributionEvidenceService())
    before = capture_s29_domain(include_summary=True)
    with CaptureQueriesContext(connection) as queries:
        first = boundary.complete(
            case.pip.created_by_id, llm=llm, correlation_id="s29-finite-first"
        )
        assert first.text == _RECOVERED_SUMMARY
        with pytest.raises(SummaryBoundaryError) as failed:
            boundary.complete(
                case.pip.created_by_id, llm=llm, correlation_id="s29-finite-exhausted"
            )
    commands = tuple(query["sql"].lstrip().split()[0].upper() for query in queries)
    assert commands and set(commands) <= _READ_ONLY_SQL
    assert capture_s29_domain(include_summary=True) == before
    assert len(llm.calls) == 2 and llm.calls[0] == llm.calls[1]
    assert failed.value.code == str(failed.value) == "provider_failed"
    assert failed.value.response is None
    trace = trace_as_agent_story(failed.value.trace)
    assert tuple(event["beat"] for event in trace["events"]) == _BOUNDARY_FAILURE_ORDER
    assert_agent_story(
        trace,
        workflow="contribution_summary",
        beats={
            "failure": ("reason_code=provider_failed",),
            "exit": ("outcome=failure",),
        },
    )
