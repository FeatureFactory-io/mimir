from __future__ import annotations

import logging
from contextlib import ExitStack
from dataclasses import replace

from behave import given, then, when
from behave.runner import Context
from django.conf import settings
from django.core import mail
from django.test import Client

from methodology.llm.base import LLMResponse
from methodology.models import AgentInteraction, KarmaAward, PipChange
from methodology.services.experts_service import ExpertsService
from methodology.services.pip_service import PIPService
from methodology.services.public_contribution_evidence import (
    _contains_restricted_summary_text,
)
from tests.support.experts_summary_data import (
    SUMMARY_SCRIPTS,
    load_summary_script,
    prepare_summary_submission,
    summary_processing_scope,
)
from tests.support.experts_summary_stability import (
    _assert_s28_generation_story,
    _oracle_paragraph,
    assert_live_displays,
    capture_summary_state,
    post_authorized_copy,
)

logger = logging.getLogger(__name__)
_MARIA = "mrodriguez"
_MIKE = "mchen"
_GENERATED = "s28-real-generation"
_BASELINE_TOTALS = (8200, 12450)
_UPDATED_TOTALS = (8205, 12455)


@given("Maria's stored summary contains stable public facts and no aggregate scores")
def stable_summary(context: Context) -> None:
    """Generate real stable prose, retaining its captured provider across steps.

    :param context: Shared Cedar context. Example: context.cedar_dataset.
    :return: None. Example: immutable state saved on context.
    :raises AssertionError: For missing, altered or score-bearing prose.
    """
    cedar = context.cedar_dataset
    maria, mike = (cedar.users_by_username[name] for name in (_MARIA, _MIKE))
    _generate_stable_summary(context)
    context.s28_client = Client(enforce_csrf_checks=True)
    context.s28_client.force_login(maria)
    assert context.s28_client.get("/auth/user/profile/").status_code == 200
    context.s28_before = capture_summary_state(maria.pk)
    paragraph = context.s28_before.profile_values["contribution_summary"]
    assert paragraph == _oracle_paragraph(cedar)
    assert not _contains_restricted_summary_text(paragraph)
    assert context.s28_before.profile_values["summary_status"] == "success"
    assert context.s28_before.profile_values["summary_updated_at"] is not None
    context.s28_calls = context.s28_llm.calls
    assert len(context.s28_calls) == 2
    context.s28_ledger = tuple(KarmaAward.objects.order_by("pk").values())
    context.s28_mail = tuple(getattr(mail, "outbox", ()))
    assert (
        tuple(
            ExpertsService().project_user(user.pk).total_points
            for user in (maria, mike)
        )
        == _BASELINE_TOTALS
    )
    logger.info("S28 AT | setup | subject_id=%s provider_calls=2", maria.pk)


@when("an eligible consumption awards her 5 points")
def eligible_consumption(context: Context) -> None:
    """Use S36's real authorized activity-copy receipt with Maria's session.

    :param context: Real client and Cedar dataset. Example: Maria and activity 6203.
    :return: None. Example: successful receipt stored on context.
    :raises AssertionError: For failed receipt or missing atomic pair.
    """
    cedar, ledger = context.cedar_dataset, context.s28_ledger
    action = post_authorized_copy(context.s28_client, cedar)
    original_ids = [row["id"] for row in ledger]
    added = KarmaAward.objects.exclude(pk__in=original_ids)
    assert set(added.values_list("recipient_id", "source_kind", "points")) == {
        (cedar.users_by_username[_MARIA].pk, "learning", 5),
        (cedar.users_by_username[_MIKE].pk, "consumption", 5),
    }
    assert set(
        added.values_list(
            "category", "event_channel", "entity_type_snapshot", "entity_id_snapshot"
        )
    ) == {("development", "gui_copy", "activity", 6203)}
    maria_id = cedar.users_by_username[_MARIA].pk
    assert set(added.values_list("event_identity", flat=True)) == {
        f"consumption:gui_copy:{maria_id}:{action}"
    }
    assert (
        tuple(KarmaAward.objects.filter(pk__in=original_ids).order_by("pk").values())
        == ledger
    )
    assert KarmaAward.objects.count() == len(ledger) + 2
    context.s28_after_ledger = tuple(KarmaAward.objects.order_by("pk").values())
    assert context.s28_llm.calls == context.s28_calls
    logger.info("S28 AT | consumption | subject_id=%s new_awards=2", maria_id)


@then("the numeric total is 8205")
def live_total(context: Context) -> None:
    """Check actual projection and rendered numeric surfaces.

    :param context: Post-receipt context. Example: EV01 completed.
    :return: None. Example: Maria 8205 and Mike 12455 verified.
    :raises AssertionError: For stale or incorrect totals/category/source.
    """
    cedar = context.cedar_dataset
    assert (
        tuple(
            ExpertsService().project_user(cedar.users_by_username[name].pk).total_points
            for name in (_MARIA, _MIKE)
        )
        == _UPDATED_TOTALS
    )
    assert_live_displays(context.s28_client, cedar)
    assert context.s28_llm.calls == context.s28_calls
    logger.info("S28 AT | displays | maria_total=8205 mike_total=12455")


@then("the stored summary is unchanged")
def unchanged_summary(context: Context) -> None:
    """Compare exact paragraph, refresh metadata and interaction snapshots.

    :param context: Before/after evidence. Example: identical nine sentences.
    :return: None. Example: persistent summary state is unchanged.
    :raises AssertionError: For text, refresh metadata or interaction change.
    """
    maria_id = context.cedar_dataset.users_by_username[_MARIA].pk
    assert capture_summary_state(maria_id) == context.s28_before
    assert tuple(KarmaAward.objects.order_by("pk").values()) == context.s28_after_ledger
    assert tuple(getattr(mail, "outbox", ())) == context.s28_mail
    logger.info("S28 AT | unchanged | subject_id=%s summary_and_history=true", maria_id)


@then("no extra summary-generation call is required")
def no_extra_generation(context: Context) -> None:
    """Require the same actual captured port and calls after receipt and GETs.

    :param context: Real receipt and display responses. Example: S28 execution.
    :return: None. Example: no refresh dispatch in these paths.
    :raises AssertionError: For a changed port, extra call or persisted refresh.
    """
    assert settings.CONTRIBUTION_SUMMARY_LLM is context.s28_llm
    assert len(context.s28_calls) == 2
    assert context.s28_llm.calls == context.s28_calls
    maria_id = context.cedar_dataset.users_by_username[_MARIA].pk
    assert capture_summary_state(maria_id) == context.s28_before
    logger.info("S28 AT | no_generation | subject_id=%s provider_calls=2", maria_id)


def _generate_stable_summary(context: Context) -> None:
    """Submit a real draft with two finite turns and inspect its persisted trace.

    :param context: Real Cedar AT lifecycle. Example: context.test and dataset.
    :return: None. Example: captured port remains installed until scenario cleanup.
    :raises AssertionError: For failed assessment, missing trace or bypassed generation.
    """
    pip = prepare_summary_submission(context.cedar_dataset)
    summary, assessment = load_summary_script(
        SUMMARY_SCRIPTS / "PRF-EXPERTS-01/happy.json", pip.changes.get().pk
    )
    assert isinstance(summary, LLMResponse)
    summary = replace(summary, content=_oracle_paragraph(context.cedar_dataset))
    scope = ExitStack()
    context.add_cleanup(scope.close)
    context.s28_llm = scope.enter_context(
        summary_processing_scope((summary, assessment))
    )
    with context.test.captureOnCommitCallbacks(execute=True) as callbacks:
        PIPService.submit_for_review(
            actor=pip.created_by, pip=pip, correlation_id=_GENERATED
        )
    assert len(callbacks) == 1
    pip.refresh_from_db()
    assert pip.status == pip.STATUS_REVIEWED
    assert pip.changes.get().galdr_recommendation == PipChange.GALDR_ACCEPT
    _assert_s28_generation_story(
        AgentInteraction.objects.get(pip=pip), pip.created_by_id, pip.pk
    )
