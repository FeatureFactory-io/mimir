from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

from methodology.llm.base import LLMError, LLMResponse
from methodology.models import (
    Activity,
    AgentInteraction,
    ExpertProfile,
    KarmaAward,
    PipChange,
    ProcessImprovementProposal,
)
from methodology.services.contribution_summary_boundary import (
    PublicContributionSummaryBoundary,
    SummaryBoundaryError,
    SummaryTraceEvent,
    trace_as_agent_story,
)
from methodology.services.experts_service import ExpertsService
from methodology.services.galdr_prompts import HOLISTIC_SYSTEM_PROMPT, SYSTEM_PROMPT
from methodology.services.pip_service import PIPService
from methodology.services.public_contribution_evidence import (
    MAX_EVIDENCE_CHARACTERS,
    PublicContributionEvidenceService,
)
from tests.support.agent_story import assert_agent_story
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
from tests.support.scripted_llm import ScriptedLLM, ScriptedLLMCall

_S27_SCRIPTS = Path(__file__).parents[1] / "fixtures/llm_scripts/PRF-EXPERTS-03"
_S27_RUN = "s27-proof-01"
_S23_RUN = "s23-agent-proof-01"
_S27_BOUNDARY = "PublicContributionSummaryBoundary.complete"
_S27_LOGGERS = (
    "methodology.services.contribution_summary_boundary",
    "methodology.services.public_contribution_evidence",
    "methodology.services.contribution_summary_prompts",
    "tests.support.scripted_llm",
)


def _load_s27_script(path: Path) -> tuple[LLMResponse | LLMError, ...]:
    """Read an explicit nonempty CAP-004 script, rejecting invalid/exhausted data.

    :param path: PRF fixture path. Example: PRF-EXPERTS-03/happy.json.
    :return: Ordered normalized responses/errors. Example: (public_response,).
    :raises ValueError: For empty scripts, invalid entries or malformed JSON.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    responses = document.get("responses") if isinstance(document, dict) else None
    if not isinstance(responses, list) or not responses:
        raise ValueError("S27 requires a nonempty response script")
    return tuple(_decode_s27_turn(turn) for turn in responses)


def _decode_s27_turn(turn: object) -> LLMResponse | LLMError:
    """Decode one explicit provider response or failure from a test script.

    :param turn: Script item. Example: {"kind": "error", "code": "provider_failed"}.
    :return: One finite scripted turn. Example: LLMError("provider_failed").
    :raises ValueError: For invalid turn metadata.
    """
    if not isinstance(turn, dict):
        raise ValueError("Invalid S27 script turn")  # noqa: TRY004
    if turn.get("kind") == "error" and isinstance(turn.get("code"), str):
        return LLMError(turn["code"])
    if turn.get("kind") != "response" or any(
        not isinstance(turn.get(field), str)
        for field in ("content", "model", "stop_reason")
    ):
        raise ValueError("Invalid S27 script response")
    usage = turn.get("usage", {})
    if not isinstance(usage, dict) or any(
        key not in {"input_tokens", "output_tokens"}
        or type(value) is not int
        or value < 0
        for key, value in usage.items()
    ):
        raise ValueError("Invalid S27 script usage")
    return LLMResponse(turn["content"], turn["model"], usage, turn["stop_reason"])


@pytest.fixture
def s27_proof_case(db: None) -> Mapping[str, Any]:
    """Construct the actual Cedar baseline through the shared adapter.

    :param db: Real test DB. Example: pytest Django DB.
    :return: Real ORM/privacy variant. Example: Maria and publication receipts.
    :raises ValueError: If fixture invariants fail.
    """
    return seed_s27_summary_privacy_variant()


def _s27_boundary() -> PublicContributionSummaryBoundary:
    """Compose the production boundary with the real public evidence service.

    :return: Read-only orchestrator around the actual database query service.
    """
    return PublicContributionSummaryBoundary(PublicContributionEvidenceService())


def _s27_domain_state() -> tuple[tuple[tuple[object, ...], ...], ...]:
    """Capture full profile, ledger and interaction rows before a boundary run.

    :return: All rows grouped by model, including the stored Cedar summaries.
    """
    return tuple(
        tuple(model.objects.order_by("pk").values_list())
        for model in (ExpertProfile, KarmaAward, AgentInteraction)
    )


def _assert_s27_sql_is_read_only(queries: CaptureQueriesContext) -> None:
    """Require real snapshot reads and allow only reads and savepoint controls.

    :param queries: Actual SQL dispatched by the boundary.
    :raises AssertionError: For missing reads or any domain mutation statement.
    """
    commands = [query["sql"].split(maxsplit=1)[0].upper() for query in queries]
    assert "SELECT" in commands
    assert set(commands) <= {"SELECT", "SAVEPOINT", "RELEASE"}


def _assert_s27_request(call: ScriptedLLMCall, case: Mapping[str, Any]) -> None:
    """Prove the actual model request retains public data and excludes private input.

    :param call: Captured CAP-001 request from the production boundary.
    :param case: Real Cedar data and exclusion sentinels.
    :raises AssertionError: For absent public facts, leaked private data or missing policy.
    """
    assert call.max_tokens == 1024
    assert len(call.messages) == 1
    assert call.messages[0].role == "user"
    begin, payload, end = call.messages[0].content.splitlines()
    assert (begin, end) == ("BEGIN PUBLIC EVIDENCE JSON", "END PUBLIC EVIDENCE JSON")
    evidence = json.loads(payload)
    assert evidence["subject_id"] == case["subject_id"]
    assert {"Accessibility Audit Playbook", "Keyboard Navigation Audit"} <= {
        fact["title"] for fact in evidence["facts"]
    }
    assert "Use the real published activity guidance." in payload
    assert any(fact["category"] == "development" for fact in evidence["facts"])
    assert len(payload) <= 24_000
    assert not any(sentinel in payload + call.system for sentinel in case["sentinels"])
    assert not any(
        key in payload for key in ("total_karma", "category_points", "copy_count")
    )
    assert "Foundation policy" in call.system and "Identity:" in call.system
    assert "Karma totals, category point subtotals" in call.system
    assert (
        "quoted data" in call.system
        and "changes published by acceptance" in call.system
    )


def _assert_s27_body_free(
    text: str, case: Mapping[str, Any], call: ScriptedLLMCall | None, body: str
) -> None:
    """Check that control telemetry omits private sentinels and model bodies.

    :param text: Rendered trace or captured log records.
    :param case: Real Cedar privacy fixture.
    :param call: Actual recorded provider request.
    :param body: Response text from the explicit test script.
    :raises AssertionError: If input/output content is recorded.
    """
    excluded = (
        *case["sentinels"],
        body,
        "Foundation policy:",
        "BEGIN PUBLIC EVIDENCE JSON",
        "Accessibility Audit Playbook",
        "Keyboard Navigation Audit",
        "Use the real published activity guidance.",
        "proof-mail@example.invalid",
    )
    if call is not None:
        excluded += (call.system, call.messages[0].content)
    assert not any(value in text for value in excluded)


def _assert_s27_trace(
    trace: tuple[SummaryTraceEvent, ...], case: Mapping[str, Any], failure: str = ""
) -> None:
    """Prove ordered control events from the actual completion boundary.

    :param trace: Actual immutable boundary trace.
    :param case: Real Cedar fixture identifying the subject.
    :param failure: Safe failure code if rejected. Example: "provider_failed".
    :raises AssertionError: For a missing or out-of-order beat or any domain write.
    """
    beats = {
        "entry": (f"subject_id={case['subject_id']}", f"correlation_id={_S27_RUN}"),
        "public_evidence": ("scope=public_released", "fact_count="),
        "llm_call": ("model=scripted", "tools=none", "max_tokens=1024"),
    }
    if failure:
        beats["failure"] = (f"reason_code={failure}",)
    else:
        beats["validation"] = ("status=accepted",)
    beats["exit"] = ("outcome=failure" if failure else "outcome=success",)
    assert tuple(event.beat for event in trace) == tuple(beats)
    assert_agent_story(
        trace_as_agent_story(trace), workflow="contribution_summary", beats=beats
    )


@pytest.mark.django_db
@pytest.mark.agent_proof
def test_s27_summary_agent_story_happy(s27_proof_case: Mapping[str, Any]) -> None:
    """Prove PRF-EXPERTS-03 through the real read-only completion boundary.

    :param s27_proof_case: Real Cedar variant. Example: Maria's privacy cases.
    :return: None when request capture, public facts and production trace pass.
    :raises AssertionError: For leaked input, bypassed collaborators or domain writes.
    """
    (turn,) = _load_s27_script(_S27_SCRIPTS / "happy.json")
    assert isinstance(turn, LLMResponse)
    llm = ScriptedLLM([turn])
    boundary = _s27_boundary()
    before = _s27_domain_state()
    assert before[0] and before[1] and not before[2]
    with CaptureQueriesContext(connection) as queries:
        completed = boundary.complete(
            s27_proof_case["subject_id"], llm=llm, correlation_id=_S27_RUN
        )
    _assert_s27_sql_is_read_only(queries)
    assert _s27_domain_state() == before
    (call,) = llm.calls
    _assert_s27_request(call, s27_proof_case)
    assert completed.text == completed.response.content == turn.content
    assert completed.response.model == "scripted"
    assert completed.response.stop_reason == "end_turn"
    assert completed.response.usage == {"input_tokens": 210, "output_tokens": 15}
    with pytest.raises(TypeError):
        completed.response.usage["output_tokens"] = 99
    _assert_s27_trace(completed.trace, s27_proof_case)
    _assert_s27_body_free(str(completed.trace), s27_proof_case, call, turn.content)


@pytest.mark.django_db
@pytest.mark.agent_proof
def test_s27_summary_agent_story_reject(s27_proof_case: Mapping[str, Any]) -> None:
    """Prove unsafe scripted output returns a sanitized typed failure trace.

    :param s27_proof_case: Real DB case. Example: Maria with last good profile data.
    :return: None when failure trace passes and database remains unchanged.
    :raises AssertionError: If unsafe output succeeds or changes domain state.
    """
    (turn,) = _load_s27_script(_S27_SCRIPTS / "reject_unsafe.json")
    assert isinstance(turn, LLMResponse)
    llm = ScriptedLLM([turn])
    boundary = _s27_boundary()
    before = _s27_domain_state()
    with (
        CaptureQueriesContext(connection) as queries,
        pytest.raises(SummaryBoundaryError) as failed,
    ):
        boundary.complete(
            s27_proof_case["subject_id"], llm=llm, correlation_id=_S27_RUN
        )
    _assert_s27_sql_is_read_only(queries)
    assert _s27_domain_state() == before
    (call,) = llm.calls
    _assert_s27_request(call, s27_proof_case)
    error = failed.value
    assert error.code == "output_validation_failed"
    assert error.response is not None
    assert error.response.usage == {"input_tokens": 210, "output_tokens": 17}
    assert error.response.stop_reason == "end_turn"
    assert error.response.content == error.response.thinking == ""
    _assert_s27_trace(error.trace, s27_proof_case, error.code)
    _assert_s27_body_free(f"{error} {error.trace}", s27_proof_case, call, turn.content)


@pytest.mark.django_db
@pytest.mark.agent_proof
def test_s27_summary_with_exhausted_script_fails_loudly(
    s27_proof_case: Mapping[str, Any],
) -> None:
    """Prove finite script exhaustion cannot produce fallback success.

    :param s27_proof_case: Real DB case. Example: Maria's public facts.
    :return: None when exhausted completion fails explicitly.
    :raises AssertionError: For fallback prose or a success outcome.
    """
    (turn,) = _load_s27_script(_S27_SCRIPTS / "happy.json")
    assert isinstance(turn, LLMResponse)
    llm = ScriptedLLM([turn])
    boundary = _s27_boundary()
    before = _s27_domain_state()
    subject_id = s27_proof_case["subject_id"]
    assert (
        boundary.complete(subject_id, llm=llm, correlation_id="s27-first-turn").text
        == turn.content
    )
    with (
        CaptureQueriesContext(connection) as queries,
        pytest.raises(SummaryBoundaryError) as failed,
    ):
        boundary.complete(subject_id, llm=llm, correlation_id=_S27_RUN)
    _assert_s27_sql_is_read_only(queries)
    assert _s27_domain_state() == before
    assert len(llm.calls) == 2
    assert llm.calls[0] == llm.calls[1]
    assert failed.value.code == "provider_failed"
    assert failed.value.response is None
    _assert_s27_trace(failed.value.trace, s27_proof_case, "provider_failed")
    _assert_s27_body_free(
        f"{failed.value} {failed.value.trace}",
        s27_proof_case,
        llm.calls[1],
        turn.content,
    )


def _run_s23_agent_case(
    script_name: str,
    *,
    rates: Mapping[str, tuple[str, str]] | None = None,
    without_usage: bool = False,
    holistic: bool = True,
) -> tuple[
    Mapping[str, Any],
    ProcessImprovementProposal,
    ScriptedLLM,
    AgentInteraction,
    LLMResponse | LLMError,
]:
    """Run one real Cedar submission with the PRF's finite two-turn queue."""
    case = seed_s27_summary_privacy_variant()
    pip = prepare_summary_submission(case["dataset"])
    summary, assessment = load_summary_script(
        SUMMARY_SCRIPTS / script_name, pip.changes.get().pk
    )
    if without_usage:
        assert isinstance(summary, LLMResponse)
        summary = replace(summary, usage={})
    before = tuple(KarmaAward.objects.order_by("pk").values_list())
    with (
        summary_processing_scope((summary, assessment), rates=rates) as llm,
        override_settings(GALDR_USE_TARGET_STATE=holistic),
    ):
        PIPService.submit_for_review(
            actor=pip.created_by, pip=pip, correlation_id=_S23_RUN
        )
    pip.refresh_from_db()
    assert pip.status == pip.STATUS_REVIEWED
    assert pip.changes.get().galdr_recommendation == PipChange.GALDR_ACCEPT
    assert tuple(KarmaAward.objects.order_by("pk").values_list()) == before
    assert ExpertsService().project_user(pip.created_by_id).total_points == 8200
    interaction = AgentInteraction.objects.get(pip=pip)
    assert interaction.correlation_id == _S23_RUN
    assert interaction.subject_id == pip.created_by_id
    assert interaction.workflow_id == "contribution_summary"
    assert interaction.call_id
    assert len(llm.calls) == 2
    return case, pip, llm, interaction, summary


def _assert_s23_trace(
    interaction: AgentInteraction,
    pip: ProcessImprovementProposal,
    llm: ScriptedLLM,
    *,
    failure: str = "",
    holistic: bool = True,
) -> None:
    """Check persisted lifecycle and boundary events in actual order."""
    public, private = llm.calls
    assert public.max_tokens == 1024
    assert private.max_tokens == (16384 if holistic else 4096)
    assert private.system == (HOLISTIC_SYSTEM_PROMPT if holistic else SYSTEM_PROMPT)
    assert SUMMARY_PIP_TITLE in private.messages[0].content
    payload = public.messages[0].content.splitlines()[1]
    evidence = json.loads(payload)["facts"]
    public_ids = ",".join(
        str(pk) for pk in sorted({fact["playbook_id"] for fact in evidence})
    )
    beats = {
        "entry": (
            f"subject_id={pip.created_by_id}",
            f"pip_id={pip.pk}",
            f"correlation_id={_S23_RUN}",
        ),
        "public_evidence": (
            "scope=public_released",
            f"evidence_chars={len(payload)}",
            f"public_playbook_ids={public_ids}",
        ),
        "llm_call": ("model=scripted", "tools=none", "max_tokens=1024"),
    }
    expected_order = ("entry", "entry", "public_evidence", "llm_call")
    if failure:
        beats["failure"] = (f"reason_code={failure}", "last_good_retained=true")
        expected_order += ("failure", "exit", "failure")
    else:
        beats["validation"] = ("status=accepted", "sentence_count=2", "limit=14")
        profile = ExpertProfile.objects.get(user_id=pip.created_by_id)
        beats["domain_write"] = (f"profile_id={profile.pk}", "summary_updated=true")
        expected_order += ("validation", "exit", "domain_write")
    beats["exit"] = (f"outcome={interaction.outcome}", "karma_awarded=0")
    assert tuple(event["beat"] for event in interaction.events) == (
        *expected_order,
        "exit",
    )
    assert_agent_story(
        {"workflow_id": interaction.workflow_id, "events": interaction.events},
        workflow="contribution_summary",
        beats=beats,
    )


@pytest.mark.agent_proof
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("holistic", [True, False])
def test_s23_submission_agent_story_happy(holistic: bool) -> None:
    """Prove PRF-EXPERTS-01 through both real assessment modes."""
    name = "happy.json" if holistic else "happy_per_change.json"
    case, pip, llm, interaction, summary = _run_s23_agent_case(
        f"PRF-EXPERTS-01/{name}", holistic=holistic
    )
    assert isinstance(summary, LLMResponse)
    call = llm.calls[0]
    _assert_s27_request(call, case)
    _assert_s27_body_free(str(interaction.events), case, call, summary.content)
    assert interaction.outcome == "success"
    assert not interaction.error_code
    assert (
        ExpertProfile.objects.get(user_id=pip.created_by_id).contribution_summary
        == summary.content
    )
    _assert_s23_trace(interaction, pip, llm, holistic=holistic)


@pytest.mark.agent_proof
@pytest.mark.django_db(transaction=True)
def test_s23_submission_agent_story_reject() -> None:
    """Prove PRF-EXPERTS-02 retention and assessment continuity."""
    case, pip, llm, interaction, summary = _run_s23_agent_case(
        "PRF-EXPERTS-02/reject_provider.json"
    )
    assert isinstance(summary, LLMError)
    assert interaction.outcome == "failure"
    assert interaction.error_code == "provider_failed"
    profile = ExpertProfile.objects.get(user_id=pip.created_by_id)
    person = next(
        row
        for row in case["dataset"].oracle["people"]
        if row["username"] == "mrodriguez"
    )
    assert profile.contribution_summary == person["summary"]
    assert profile.summary_updated_at is None
    assert profile.summary_status == ExpertProfile.SummaryStatus.FAILURE
    assert profile.summary_error_code == interaction.error_code
    assert profile.last_summary_correlation_id == interaction.correlation_id
    assert (
        interaction.input_tokens
        is interaction.output_tokens
        is interaction.estimated_cost_usd
        is None
    )
    _assert_s23_trace(interaction, pip, llm, failure="provider_failed")
    _assert_s27_body_free(str(interaction.events), case, llm.calls[0], str(summary))


@pytest.mark.agent_proof
@pytest.mark.django_db(transaction=True)
def test_s23_submission_with_private_sentinels_agent_story_happy() -> None:
    """Prove PRF-EXPERTS-03 filters the real current unpublished ADD."""
    case, pip, llm, interaction, summary = _run_s23_agent_case(
        "PRF-EXPERTS-03/submission_happy.json"
    )
    assert isinstance(summary, LLMResponse)
    public_call, assessment_call = llm.calls
    _assert_s27_request(public_call, case)
    current_sentinels = (SUMMARY_PIP_TITLE, SUMMARY_PIP_BODY, SUMMARY_CHANGE_BODY)
    public_request = public_call.system + public_call.messages[0].content
    assert not any(sentinel in public_request for sentinel in current_sentinels)
    assert SUMMARY_CHANGE_BODY in assessment_call.messages[0].content
    assert pip.playbook.visibility == "public" and pip.playbook.status == "released"
    _assert_s23_trace(interaction, pip, llm)
    _assert_s27_body_free(str(interaction.events), case, public_call, summary.content)
    assert not any(
        sentinel in str(interaction.events) for sentinel in current_sentinels
    )


@pytest.mark.agent_proof
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("pricing", ["known", "unknown_rates", "unknown_usage"])
def test_s23_summary_interaction_agent_story_happy(pricing: str) -> None:
    """Prove PRF-OBS-01 persisted correlation, usage, latency, cost and nulls."""
    rates = None if pricing == "unknown_rates" else {"scripted": ("3", "15")}
    name = "unknown_rates.json" if rates is None else "happy.json"
    case, pip, llm, interaction, summary = _run_s23_agent_case(
        f"PRF-OBS-01/{name}", rates=rates, without_usage=pricing == "unknown_usage"
    )
    assert isinstance(summary, LLMResponse)
    assert interaction.outcome == "success"
    assert interaction.model == "scripted"
    assert isinstance(interaction.latency_ms, Decimal) and interaction.latency_ms >= 0
    assert interaction.input_tokens == summary.usage.get("input_tokens")
    assert interaction.output_tokens == summary.usage.get("output_tokens")
    assert interaction.estimated_cost_usd == (
        Decimal("0.000855") if pricing == "known" else None
    )
    interaction.full_clean()
    _assert_s23_trace(interaction, pip, llm)
    _assert_s27_body_free(str(interaction.events), case, llm.calls[0], summary.content)


@pytest.mark.agent_proof
@pytest.mark.django_db(transaction=True)
def test_s25_resubmission_agent_story_happy() -> None:
    """Prove genuine two-cycle summary orchestration and public-only requests.

    :return: None. Example: None after traces, four calls and real DB assertions.
    :raises AssertionError: For synthetic trace, private input or missing writes.
    """
    raise NotImplementedError()


@pytest.mark.agent_proof
@pytest.mark.django_db(transaction=True)
def test_s25_resubmission_agent_story_reject() -> None:
    """Prove authentic second-run failure trace and last-good retention.

    :return: None. Example: None after failure trace and assessment assertions.
    :raises AssertionError: For swallowed failure or successful replacement.
    """
    raise NotImplementedError()


@pytest.mark.agent_proof
@pytest.mark.django_db(transaction=True)
def test_s28_points_change_agent_story_happy() -> None:
    """Generate through real S23 lifecycle, then prove copy makes no model call.
    :return: None. Example: baseline two calls stay two; totals become 8205/12455.
    :raises AssertionError: For bypassed orchestration or changed calls/state.
    """
    raise NotImplementedError()


@pytest.mark.django_db
@pytest.mark.agent_proof
def test_s29_summary_agent_story_reject() -> None:
    """Assert persisted authentic failure trace through real normal submission.

    :return: None when PRF-EXPERTS-02, retention and bounded calls pass.
    :raises AssertionError: For missing beats, domain writes or unexpected awards.
    """
    raise NotImplementedError()


@pytest.mark.django_db
@pytest.mark.agent_proof
def test_s29_summary_interaction_with_failure_preserves_usage_agent_story_reject() -> (
    None
):
    """Parameterize supplied usage, absent usage and absent configured rates.

    :return: None when failed interactions retain known usage and unknown nulls.
    :raises AssertionError: For false zero cost, lost tokens or unsafe trace data.
    """
    raise NotImplementedError()


@pytest.mark.django_db
@pytest.mark.agent_proof
def test_s29_summary_with_exhausted_script_fails_loudly() -> None:
    """Exhaust a finite queue through the real read-only production boundary.

    :return: None when typed failure preserves explicit exhaustion and DB state.
    :raises AssertionError: If exhaustion becomes success or fallback prose.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_s27_summary_log_story_happy(
    s27_proof_case: Mapping[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    """Capture actual ordinary logs across evidence, prompt validation and the read-only boundary.

    :param s27_proof_case: Real independent public/private Cedar case. Example: Maria.
    :param caplog: Real enabled-and-restored logger capture. Example: correlated INFO records.
    :return: None after assert_log_story checks every declared happy beat and private exclusions.
    :raises AssertionError: Missing beat, false domain write or leaked private material.
    """
    (turn,) = _load_s27_script(_S27_SCRIPTS / "happy.json")
    assert isinstance(turn, LLMResponse)
    llm = ScriptedLLM([turn])
    subject_id = s27_proof_case["subject_id"]
    with capture_experts_logs(caplog, _S27_LOGGERS):
        _s27_boundary().complete(subject_id, llm=llm, correlation_id=_S27_RUN)
    (call,) = llm.calls
    payload = call.messages[0].content.splitlines()[1]
    _assert_s27_evidence_logs(caplog, subject_id, payload)
    assert_log_story(
        caplog,
        where="validate_summary_response",
        beats={
            "validation": ("| validation |", "sentence_count=1", "status=accepted"),
        },
    )
    _assert_s27_boundary_logs(caplog, subject_id, model_called=True)
    _assert_s27_body_free(caplog.text, s27_proof_case, call, turn.content)


def _assert_s27_evidence_logs(
    caplog: pytest.LogCaptureFixture, subject_id: int, payload: str
) -> None:
    """Check named evidence and prompt operations using the real request shape.

    :param caplog: Actual records from enabled named loggers.
    :param subject_id: Cedar contributor ID. Example: Maria's ID.
    :param payload: Compact evidence JSON taken from the actual request.
    :raises AssertionError: For a missing scope, fact or token-bound log beat.
    """
    assert_log_story(
        caplog,
        where="PublicContributionEvidenceService.collect",
        beats={
            "validation": (
                "| validation |",
                f"subject_id={subject_id}",
                "scope=public_released",
            ),
            "processing": (
                "| processing |",
                f"subject_id={subject_id}",
                f"fact_count={len(json.loads(payload)['facts'])}",
                f"evidence_chars={len(payload)}",
            ),
        },
    )
    assert_log_story(
        caplog,
        where="build_summary_prompt",
        beats={
            "config": (
                "| config |",
                "layers=foundation,identity,evidence",
                "max_tokens=1024",
            ),
        },
    )


def _assert_s27_boundary_logs(
    caplog: pytest.LogCaptureFixture,
    subject_id: int,
    *,
    model_called: bool,
    failure: str = "",
) -> None:
    """Prove the correlated ordinary boundary logs follow the chosen path.

    :param caplog: Actual records from enabled named loggers.
    :param subject_id: Cedar contributor ID or a missing valid-form ID.
    :param model_called: Whether processing reached model invocation.
    :param failure: Expected safe reason code. Example: "provider_failed".
    :raises AssertionError: If the model was unexpectedly called or a beat was lost.
    """
    correlation = f"correlation_id={_S27_RUN}"
    beats = {"entry": ("| entry |", f"subject_id={subject_id}", correlation)}
    if model_called:
        beats["validation"] = (
            "| validation |",
            correlation,
            "visibility=public_released",
            "evidence_chars=",
        )
        beats["processing"] = (
            "| processing |",
            correlation,
            "operation=complete",
            "model=scripted",
            "tools=none",
        )
    if failure:
        beats["error"] = (
            "| error |",
            correlation,
            f"reason_code={failure}",
            "outcome=failure",
        )
    beats["exit"] = (
        "| exit |",
        correlation,
        "outcome=failure" if failure else "outcome=success",
    )
    assert_log_story(caplog, where=_S27_BOUNDARY, beats=beats)
    actual = [
        record.getMessage().split(" | ")[1]
        for record in caplog.records
        if record.name == _S27_LOGGERS[0]
    ]
    assert actual == list(beats)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "stage,reason",
    [
        ("unsafe_output", "output_validation_failed"),
        ("provider", "provider_failed"),
        ("missing_subject", "public_evidence_failed"),
        ("oversize_snapshot", "public_evidence_failed"),
    ],
)
def test_s27_summary_log_story_reject(
    s27_proof_case: Mapping[str, Any],
    caplog: pytest.LogCaptureFixture,
    stage: str,
    reason: str,
) -> None:
    """Capture actual rejected prompt/output/boundary logs with safe reason codes and no body leakage.

    :param s27_proof_case: Real adverse Cedar case. Example: private sentinel and unsafe response.
    :param caplog: Real ordinary logger capture. Example: same correlated attempt.
    :param stage: Adverse stage. Example: "unsafe_output".
    :param reason: Expected safe failure code. Example: "output_validation_failed".
    :return: None after assert_log_story verifies the applicable rejection sequence.
    :raises AssertionError: Missing error/exit beat or private text disclosed.
    """
    (turn,) = _load_s27_script(_S27_SCRIPTS / "reject_unsafe.json")
    assert isinstance(turn, LLMResponse)
    body = turn.content
    subject_id = s27_proof_case["subject_id"]
    model_called = stage in {"unsafe_output", "provider"}
    if stage == "missing_subject":
        subject_id = 1_000_000
    if stage == "oversize_snapshot":
        body = "Private marker in oversized request evidence."
        Activity.objects.filter(workflow__playbook__author_id=subject_id).update(
            guidance=body + "x" * MAX_EVIDENCE_CHARACTERS
        )
    if stage == "provider":
        body = "Raw provider failure with request metadata."
        turn = LLMError(body)
    llm = ScriptedLLM([turn])
    with (
        capture_experts_logs(caplog, _S27_LOGGERS),
        pytest.raises(SummaryBoundaryError) as failed,
    ):
        _s27_boundary().complete(subject_id, llm=llm, correlation_id=_S27_RUN)
    assert failed.value.code == reason
    assert len(llm.calls) == int(model_called)
    _assert_s27_boundary_logs(
        caplog, subject_id, model_called=model_called, failure=reason
    )
    if stage == "unsafe_output":
        assert_log_story(
            caplog,
            where="validate_summary_response",
            beats={
                "error": ("| error |", "reason_code=invalid_response"),
            },
        )
    call = llm.calls[0] if model_called else None
    _assert_s27_body_free(f"{failed.value} {caplog.text}", s27_proof_case, call, body)
