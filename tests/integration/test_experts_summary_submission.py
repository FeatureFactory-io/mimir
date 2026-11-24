"""S23 real-DB lifecycle, HTTP and logging contracts."""

from __future__ import annotations

import ast
import io
import json
import logging
import logging.config
from collections.abc import Iterator
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import enumerate as active_threads
from uuid import UUID

import pytest
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

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
from methodology.services.contribution_summary_factory import (
    build_contribution_summary_service,
)
from methodology.services.contribution_summary_prompts import _count_sentences
from methodology.services.experts_service import ExpertsService
from methodology.services.galdr_engine import GaldrEngine
from methodology.services.pip_service import PIPService
from mimir.request_local import get_current_request
from tests.support.experts_data import load_cedar_baseline
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

_RUN = "s23-submission-01"
_CREDENTIAL_LIKE_ID = "trace" + ("1" * 48)
_PROVIDER_MARKER = "provider_response_private_marker"
_LOGGERS = (
    "methodology.services.pip_service",
    "methodology.services.contribution_summary_service",
    "methodology.services.contribution_summary_boundary",
    "methodology.services.public_contribution_evidence",
    "methodology.services.contribution_summary_prompts",
    "methodology.services.galdr_client",
    "methodology.services.galdr_engine",
    "tests.support.scripted_llm",
)
_SERVICE = "ContributionSummaryService.refresh_for_submission"
_BOUNDARY = "PublicContributionSummaryBoundary.complete"


@pytest.fixture
def production_request_log() -> Iterator[io.StringIO]:
    """Capture the exact production console handler without adopting its settings."""
    path = Path(__file__).resolve().parents[2] / "mimir/settings/prod.py"
    source = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    spec = next(
        ast.literal_eval(node.value)
        for node in source.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(name, ast.Name) and name.id == "LOGGING" for name in node.targets
        )
    )
    capture = io.StringIO()
    production = logging.config.DictConfigurator(spec)
    config = production.config
    config["formatters"]["json"] = production.configure_formatter(
        config["formatters"]["json"]
    )
    config["filters"]["request_id"] = production.configure_filter(
        config["filters"]["request_id"]
    )
    config["handlers"]["console"]["stream"] = capture
    handler = production.configure_handler(config["handlers"]["console"])
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        yield capture
    finally:
        root.removeHandler(handler)
        handler.close()
        capture.close()


@pytest.fixture
def s23_pip() -> ProcessImprovementProposal:
    """Create the real Cedar draft and one unpublished ADD."""
    return prepare_summary_submission(load_cedar_baseline())


def _script(
    pip: ProcessImprovementProposal, name: str = "PRF-EXPERTS-01/happy.json"
) -> tuple[LLMResponse | LLMError, ...]:
    """Read one real fixture using this draft's exact change ID."""
    return load_summary_script(SUMMARY_SCRIPTS / name, pip.changes.get().pk)


def _ledger() -> tuple[tuple[object, ...], ...]:
    """Return all persisted awards for exact before/after comparison."""
    return tuple(KarmaAward.objects.order_by("pk").values_list())


def _prose(pip: ProcessImprovementProposal) -> tuple[str, datetime | None]:
    """Read the last-good fields separately from current attempt metadata."""
    profile = ExpertProfile.objects.get(user_id=pip.created_by_id)
    return profile.contribution_summary, profile.summary_updated_at


def _assert_reviewed(pip: ProcessImprovementProposal, *, holistic: bool = True) -> None:
    """Assert the existing Galdr recommendation and unchanged publication state."""
    pip.refresh_from_db()
    pip.playbook.refresh_from_db()
    change = pip.changes.get()
    assert pip.status == pip.STATUS_REVIEWED
    assert pip.reviewed_at is not None
    assert bool(pip.galdr_holistic_assessment) is holistic
    assert change.galdr_recommendation == PipChange.GALDR_ACCEPT
    assert change.galdr_reasoning == "The proposed activity fits the review workflow."
    assert not Activity.objects.filter(
        workflow__playbook=pip.playbook, name=SUMMARY_PIP_TITLE
    ).exists()
    assert pip.playbook.version == Decimal("2.0")
    assert not PlaybookVersion.objects.filter(pip=pip).exists()
    assert ExpertsService().project_user(pip.created_by_id).total_points == 8200


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("holistic", [True, False])
def test_s23_submit_for_review_with_add_activity_refreshes_without_acceptance_award(
    s23_pip: ProcessImprovementProposal, holistic: bool
) -> None:
    """Prove both existing assessment modes use one explicit port after commit."""
    name = "happy.json" if holistic else "happy_per_change.json"
    script = _script(s23_pip, f"PRF-EXPERTS-01/{name}")
    explicit = ScriptedLLM(script)
    before = _ledger()
    with (
        summary_processing_scope(script) as scoped,
        override_settings(GALDR_USE_TARGET_STATE=holistic),
    ):
        PIPService.submit_for_review(
            actor=s23_pip.created_by, pip=s23_pip, llm=explicit, correlation_id=_RUN
        )
    assert not scoped.calls
    assert len(explicit.calls) == 2
    _assert_reviewed(s23_pip, holistic=holistic)
    assert _ledger() == before
    assert isinstance(script[0], LLMResponse)
    profile = ExpertProfile.objects.get(user_id=s23_pip.created_by_id)
    assert profile.contribution_summary == script[0].content
    assert 0 < _count_sentences(profile.contribution_summary) <= 14
    assert profile.summary_updated_at
    assert profile.summary_status == ExpertProfile.SummaryStatus.SUCCESS
    assert not profile.summary_error_code
    assert profile.last_summary_correlation_id == _RUN
    assert AgentInteraction.objects.get(pip=s23_pip).outcome == "success"


@pytest.mark.django_db(transaction=True)
def test_s23_submit_for_review_with_invalid_actor_requests_no_summary(
    s23_pip: ProcessImprovementProposal,
) -> None:
    """Prove existing submitter permissions reject before generation."""
    ledger = _ledger()
    prose = _prose(s23_pip)
    with (
        summary_processing_scope(_script(s23_pip)) as llm,
        pytest.raises(ValidationError, match="Only the submitter"),
    ):
        PIPService.submit_for_review(actor=s23_pip.playbook.author, pip=s23_pip)
    s23_pip.refresh_from_db()
    assert s23_pip.status == s23_pip.STATUS_DRAFT
    assert not llm.calls
    assert not AgentInteraction.objects.filter(pip=s23_pip).exists()
    assert _prose(s23_pip) == prose
    assert _ledger() == ledger


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("eager", [True, False])
def test_s23_submit_for_review_with_rollback_does_not_dispatch_processing(
    s23_pip: ProcessImprovementProposal, eager: bool
) -> None:
    """Prove rollback discards the callback for both dispatch modes."""
    before = _ledger(), _prose(s23_pip)
    with (
        summary_processing_scope(_script(s23_pip)) as llm,
        override_settings(GALDR_EAGER=eager),
    ):
        with transaction.atomic():
            PIPService.submit_for_review(actor=s23_pip.created_by, pip=s23_pip)
            assert not llm.calls
            assert not AgentInteraction.objects.filter(pip=s23_pip).exists()
            transaction.set_rollback(True)
    s23_pip.refresh_from_db()
    assert s23_pip.status == s23_pip.STATUS_DRAFT
    assert not llm.calls
    assert not AgentInteraction.objects.filter(pip=s23_pip).exists()
    assert (_ledger(), _prose(s23_pip)) == before


@pytest.mark.django_db(transaction=True)
def test_s23_committed_submission_uses_port_captured_before_dispatch(
    s23_pip: ProcessImprovementProposal,
) -> None:
    """Commit after the scoped provider setting has already been restored."""
    with transaction.atomic():
        with summary_processing_scope(_script(s23_pip)) as llm:
            PIPService.submit_for_review(actor=s23_pip.created_by, pip=s23_pip)
            assert not llm.calls
        assert not llm.calls
    assert len(llm.calls) == 2
    _assert_reviewed(s23_pip)


@pytest.mark.django_db(transaction=True)
def test_s23_committed_submission_dispatches_existing_worker_once(
    s23_pip: ProcessImprovementProposal,
) -> None:
    """Exercise a committed submission through the actual daemon scheduler."""
    worker_name = f"galdr-pip-{s23_pip.pk}"
    with (
        summary_processing_scope(_script(s23_pip)) as llm,
        override_settings(GALDR_EAGER=False),
    ):
        with transaction.atomic():
            PIPService.submit_for_review(actor=s23_pip.created_by, pip=s23_pip)
            assert not llm.calls
            assert worker_name not in {worker.name for worker in active_threads()}
        worker = next(
            (worker for worker in active_threads() if worker.name == worker_name), None
        )
        if worker is not None:
            worker.join(timeout=5)
            assert not worker.is_alive()
    assert len(llm.calls) == 2
    _assert_reviewed(s23_pip)
    assert AgentInteraction.objects.filter(pip=s23_pip).count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "request_id", [_RUN, None, "unsafe@example.invalid", _CREDENTIAL_LIKE_ID]
)
def test_s23_http_submission_with_request_id_uses_normal_lifecycle(
    client: Client,
    s23_pip: ProcessImprovementProposal,
    request_id: str | None,
    caplog: pytest.LogCaptureFixture,
    production_request_log: io.StringIO,
) -> None:
    """Keep one safe ID across production JSON logs, response and storage."""
    client.force_login(s23_pip.created_by)
    before = _ledger(), _prose(s23_pip)
    with (
        capture_experts_logs(caplog, (*_LOGGERS, "mimir.middleware")),
        summary_processing_scope(_script(s23_pip)) as llm,
    ):
        response = client.post(
            reverse("pip_submit_review", kwargs={"pk": s23_pip.pk}),
            headers={"X-Request-ID": request_id} if request_id is not None else {},
        )
    assert response.status_code == 302
    assert response.url == reverse("pip_detail", kwargs={"pk": s23_pip.pk})
    assert len(llm.calls) == 2
    _assert_reviewed(s23_pip)
    interaction = AgentInteraction.objects.get(pip=s23_pip)
    profile = ExpertProfile.objects.get(user_id=s23_pip.created_by_id)
    assert interaction.subject_id == s23_pip.created_by_id
    assert interaction.outcome == "success"
    assert _ledger() == before[0]
    assert _prose(s23_pip) != before[1]
    correlation = interaction.correlation_id
    formatted = production_request_log.getvalue()
    assert f"correlation_id={correlation}" in caplog.text
    if request_id is not None and request_id != _RUN:
        assert request_id not in formatted
        assert request_id not in str(interaction.events)
        assert request_id not in repr(llm.calls)
    assert (
        correlation
        == response.headers["X-Request-ID"]
        == profile.last_summary_correlation_id
    )
    if request_id == _RUN:
        assert correlation == request_id
    else:
        assert str(UUID(correlation, version=4)) == correlation
    records = [json.loads(line) for line in formatted.splitlines()]
    for message in ("[REQUEST_START]", _SERVICE, "[REQUEST_END]"):
        matching = [record for record in records if message in record["message"]]
        assert matching and {record["request_id"] for record in matching} == {
            correlation
        }
    assert get_current_request() is None


@pytest.mark.django_db(transaction=True)
def test_s23_direct_refresh_and_schedule_reject_unpersistable_correlation(
    s23_pip: ProcessImprovementProposal, caplog: pytest.LogCaptureFixture
) -> None:
    """Reject a credential-like ID before logging, querying or completing."""
    llm = ScriptedLLM(_script(s23_pip))
    service = build_contribution_summary_service(llm)
    with capture_experts_logs(caplog, _LOGGERS):
        with pytest.raises(ValueError, match="safe processing correlation ID"):
            service.refresh_for_submission(s23_pip.pk, _CREDENTIAL_LIKE_ID)
        with pytest.raises(ValueError, match="safe processing correlation ID"):
            GaldrEngine.schedule(
                s23_pip.pk, llm=llm, correlation_id=_CREDENTIAL_LIKE_ID
            )
    assert not llm.calls
    assert _CREDENTIAL_LIKE_ID not in caplog.text
    assert not AgentInteraction.objects.filter(pip=s23_pip).exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("configured_model", ["", _CREDENTIAL_LIKE_ID])
def test_s23_http_submission_with_invalid_default_model_allows_retry(
    client: Client,
    s23_pip: ProcessImprovementProposal,
    configured_model: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Keep bad default config in the normal Submitted/retry lifecycle."""
    client.force_login(s23_pip.created_by)
    client.raise_request_exception = False
    before = _ledger(), _prose(s23_pip)
    url = reverse("pip_submit_review", kwargs={"pk": s23_pip.pk})
    with (
        capture_experts_logs(caplog, (*_LOGGERS, "methodology.llm.anthropic_adapter")),
        override_settings(
            GALDR_EAGER=True,
            GALDR_USE_ANTHROPIC=True,
            GALDR_MODEL=configured_model,
            CONTRIBUTION_SUMMARY_LLM=None,
        ),
    ):
        response = client.post(url, headers={"X-Request-ID": _RUN})
        assert response.status_code == 302
        assert response.url == reverse("pip_detail", kwargs={"pk": s23_pip.pk})
        s23_pip.refresh_from_db()
        assert s23_pip.status == s23_pip.STATUS_SUBMITTED
        assert s23_pip.submitted_at and not s23_pip.reviewed_at
        assert not s23_pip.changes.get().galdr_recommendation
        assert not AgentInteraction.objects.filter(pip=s23_pip).exists()
        assert (_ledger(), _prose(s23_pip)) == before
        assert "reason=provider_configuration_invalid" in caplog.text
        assert "AnthropicAdapter.complete" not in caplog.text
        assert _CREDENTIAL_LIKE_ID not in caplog.text
        with summary_processing_scope(_script(s23_pip)) as llm:
            assert client.post(url).status_code == 302
    assert len(llm.calls) == 2 and _ledger() == before[0]
    _assert_reviewed(s23_pip)
    assert AgentInteraction.objects.get(pip=s23_pip).outcome == "success"


@pytest.mark.django_db(transaction=True)
def test_s23_unpersistable_response_model_preserves_summary_and_known_usage(
    s23_pip: ProcessImprovementProposal, caplog: pytest.LogCaptureFixture
) -> None:
    """Keep validated text and usage without storing or pricing a rejected ID."""
    summary, assessment = _script(s23_pip)
    assert isinstance(summary, LLMResponse)
    script = (replace(summary, model=_CREDENTIAL_LIKE_ID), assessment)
    with (
        capture_experts_logs(caplog, _LOGGERS),
        summary_processing_scope(
            script, rates={"scripted": ("3", "15"), "unknown": ("3", "15")}
        ) as llm,
    ):
        PIPService.submit_for_review(actor=s23_pip.created_by, pip=s23_pip)
    assert len(llm.calls) == 2
    _assert_reviewed(s23_pip)
    assert _prose(s23_pip)[0] == summary.content
    interaction = AgentInteraction.objects.get(pip=s23_pip)
    assert interaction.outcome == "success"
    assert interaction.model == "unknown"
    assert interaction.input_tokens == summary.usage["input_tokens"]
    assert interaction.output_tokens == summary.usage["output_tokens"]
    assert interaction.estimated_cost_usd is None
    assert any("model=scripted " in event["details"] for event in interaction.events)
    assert _CREDENTIAL_LIKE_ID not in str(interaction.events)
    assert _CREDENTIAL_LIKE_ID not in caplog.text


def _assert_common_logs(
    caplog: pytest.LogCaptureFixture,
    pip: ProcessImprovementProposal,
    llm: ScriptedLLM,
) -> None:
    """Assert E1 through E5 from the committed path and actual summary request."""
    correlation = f"correlation_id={_RUN}"
    pip_id = f"pip_id={pip.pk}"
    assert_log_story(
        caplog,
        where="PIPService._schedule_processing",
        beats={
            "entry": (
                "| entry |",
                pip_id,
                f"actor_id={pip.created_by_id}",
                correlation,
                "reason=submission",
            )
        },
    )
    evidence = llm.calls[0].messages[0].content.splitlines()[1]
    assert_log_story(
        caplog,
        where=_SERVICE,
        beats={
            "entry": (
                "| entry |",
                f"subject_id={pip.created_by_id}",
                pip_id,
                correlation,
            ),
            "config": (
                "| config |",
                "workflow=contribution_summary",
                "model=scripted",
                "max_tokens=1024",
                "tools=none",
                correlation,
            ),
        },
    )
    assert_log_story(
        caplog,
        where=_BOUNDARY,
        beats={
            "evidence": (
                "| validation |",
                "visibility=public_released",
                f"evidence_chars={len(evidence)}",
                correlation,
            ),
            "processing": ("| processing |", "operation=complete", correlation),
        },
    )


def _assert_s23_log_order(caplog: pytest.LogCaptureFixture, *, rejected: bool) -> None:
    """Verify E1–E10 occur in the order of the committed lifecycle."""
    methods = {"PIPService._schedule_processing", _SERVICE, _BOUNDARY}
    beats = []
    for record in caplog.records:
        method, _, remainder = record.getMessage().partition(" | ")
        beat, _, details = remainder.partition(" | ")
        if method not in methods:
            continue
        if method == _BOUNDARY and not (
            "visibility=public_released" in details or "operation=complete" in details
        ):
            continue
        beats.append(beat)
    ending = ["error", "branch", "exit"] if rejected else ["validation", "exit"]
    assert beats == ["entry", "entry", "config", "validation", "processing", *ending]


def _assert_body_free(caplog: pytest.LogCaptureFixture, *extra: str) -> None:
    """Protect the public boundary and private assessment outputs in ordinary logs."""
    for body in (
        SUMMARY_PIP_TITLE,
        SUMMARY_PIP_BODY,
        SUMMARY_CHANGE_BODY,
        "BEGIN PUBLIC EVIDENCE JSON",
        "The proposed activity fits the review workflow.",
        "The proposed activity has a clear place in the workflow.",
        *extra,
    ):
        assert body not in caplog.text


@pytest.mark.django_db(transaction=True)
def test_s23_summary_log_story_happy(
    s23_pip: ProcessImprovementProposal, caplog: pytest.LogCaptureFixture
) -> None:
    """Assert E1–E7 with the shared helper and absent sensitive sentinels."""
    script = _script(s23_pip)
    with (
        summary_processing_scope(script) as llm,
        capture_experts_logs(caplog, _LOGGERS),
    ):
        PIPService.submit_for_review(
            actor=s23_pip.created_by, pip=s23_pip, correlation_id=_RUN
        )
    interaction = AgentInteraction.objects.get(pip=s23_pip)
    _assert_common_logs(caplog, s23_pip, llm)
    assert_log_story(
        caplog,
        where=_SERVICE,
        beats={
            "validation": (
                "| validation |",
                "sentence_count=2",
                "limit=14",
                f"correlation_id={_RUN}",
            ),
            "exit": (
                "| exit |",
                "outcome=success",
                "summary_updated=true",
                f"interaction_id={interaction.pk}",
                "karma_awarded=0",
                f"correlation_id={_RUN}",
            ),
        },
    )
    assert isinstance(script[0], LLMResponse)
    _assert_s23_log_order(caplog, rejected=False)
    _assert_body_free(caplog, script[0].content)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("has_last_good", [True, False])
def test_s23_summary_log_story_reject(
    s23_pip: ProcessImprovementProposal,
    caplog: pytest.LogCaptureFixture,
    has_last_good: bool,
) -> None:
    """Assert E1–E5/E8–E10, including whether earlier prose exists."""
    if not has_last_good:
        ExpertProfile.objects.filter(user_id=s23_pip.created_by_id).update(
            contribution_summary=""
        )
    before = _ledger(), _prose(s23_pip)
    script = _script(s23_pip, "PRF-EXPERTS-02/reject_provider.json")
    with (
        summary_processing_scope(script) as llm,
        capture_experts_logs(caplog, _LOGGERS),
    ):
        PIPService.submit_for_review(
            actor=s23_pip.created_by, pip=s23_pip, correlation_id=_RUN
        )
    _assert_reviewed(s23_pip)
    assert (_ledger(), _prose(s23_pip)) == before
    _assert_common_logs(caplog, s23_pip, llm)
    correlation = f"correlation_id={_RUN}"
    retained = str(has_last_good).lower()
    interaction = AgentInteraction.objects.get(pip=s23_pip)
    assert_log_story(
        caplog,
        where=_SERVICE,
        beats={
            "error": (
                "| error |",
                "outcome=failure",
                "reason_code=provider_failed",
                correlation,
            ),
            "branch": (
                "| branch |",
                f"last_good_retained={retained}",
                "karma_awarded=0",
                correlation,
            ),
            "exit": (
                "| exit |",
                "summary_updated=false",
                "pip_lifecycle=unchanged",
                f"interaction_id={interaction.pk}",
                correlation,
            ),
        },
    )
    _assert_s23_log_order(caplog, rejected=True)
    _assert_body_free(caplog, _PROVIDER_MARKER)


@pytest.fixture
def s23_previous_refresh(s23_pip: ProcessImprovementProposal) -> None:
    """Give Cedar's stored prose real last-good metadata for retention tests."""
    ExpertProfile.objects.filter(user_id=s23_pip.created_by_id).update(
        summary_updated_at=timezone.now() - timedelta(days=1),
        summary_status=ExpertProfile.SummaryStatus.SUCCESS,
        last_summary_correlation_id="s23-previous-refresh",
    )


@pytest.fixture
def fail_s23_success_interaction_storage() -> Iterator[None]:
    """Force a real SQL insert error after the success profile write."""
    table = "methodology_agentinteraction"
    trigger = "s23_fail_summary_insert"
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute(
                "CREATE FUNCTION pg_temp.s23_reject_summary() RETURNS trigger LANGUAGE plpgsql AS "
                "$$ BEGIN RAISE EXCEPTION 's23 storage failure'; END; $$"
            )
            cursor.execute(
                f"CREATE TRIGGER {trigger} BEFORE INSERT ON {table} FOR EACH ROW "
                "WHEN (NEW.outcome = 'success') EXECUTE FUNCTION pg_temp.s23_reject_summary()"
            )
        else:
            assert connection.vendor == "sqlite"
            cursor.execute(
                f"CREATE TEMP TRIGGER {trigger} BEFORE INSERT ON {table} "
                "WHEN NEW.outcome = 'success' BEGIN SELECT RAISE(ABORT, 's23 storage failure'); END"
            )
    try:
        yield
    finally:
        with connection.cursor() as cursor:
            if connection.vendor == "postgresql":
                cursor.execute(f"DROP TRIGGER {trigger} ON {table}")
                cursor.execute("DROP FUNCTION pg_temp.s23_reject_summary()")
            else:
                cursor.execute(f"DROP TRIGGER {trigger}")


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("fail_s23_success_interaction_storage", "s23_previous_refresh")
def test_s23_summary_storage_failure_preserves_last_good_fields(
    s23_pip: ProcessImprovementProposal,
) -> None:
    """Prove the real failed success write rolls back before failure recovery."""
    before = _ledger(), _prose(s23_pip)
    with summary_processing_scope(_script(s23_pip)) as llm:
        PIPService.submit_for_review(
            actor=s23_pip.created_by, pip=s23_pip, correlation_id=_RUN
        )
    assert len(llm.calls) == 2
    assert (_ledger(), _prose(s23_pip)) == before
    _assert_reviewed(s23_pip)
    interaction = AgentInteraction.objects.get(pip=s23_pip)
    assert (interaction.outcome, interaction.error_code) == (
        "failure",
        "storage_failed",
    )
    assert not any(event["beat"] == "domain_write" for event in interaction.events)
    assert interaction.input_tokens == 210
    assert interaction.output_tokens == 15


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("s23_previous_refresh")
def test_s23_invalid_summary_retains_last_good_prose_and_received_usage(
    s23_pip: ProcessImprovementProposal,
) -> None:
    """Prove an invalid provider completion retains prose and known usage."""
    before = _ledger(), _prose(s23_pip)
    summary, assessment = _script(s23_pip)
    assert isinstance(summary, LLMResponse)
    rejected_text = "<strong>Unapproved replacement prose.</strong>"
    with summary_processing_scope(
        (replace(summary, content=rejected_text), assessment),
        rates={"scripted": ("3", "15")},
    ) as llm:
        PIPService.submit_for_review(
            actor=s23_pip.created_by, pip=s23_pip, correlation_id=_RUN
        )
    assert len(llm.calls) == 2
    assert (_ledger(), _prose(s23_pip)) == before
    _assert_reviewed(s23_pip)
    interaction = AgentInteraction.objects.get(pip=s23_pip)
    assert (interaction.outcome, interaction.error_code) == (
        "failure",
        "output_validation_failed",
    )
    assert interaction.input_tokens == 210
    assert interaction.output_tokens == 15
    assert interaction.estimated_cost_usd == Decimal("0.000855")
    assert rejected_text not in str(interaction.events)
    assert not any(event["beat"] == "domain_write" for event in interaction.events)
