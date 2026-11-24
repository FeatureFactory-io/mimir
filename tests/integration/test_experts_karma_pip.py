from __future__ import annotations

import logging
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import timedelta
from decimal import Decimal
from threading import Event
from types import FrameType

import pytest
from _pytest.logging import LogCaptureFixture
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import DatabaseError, connection, connections, transaction
from django.db.models import Sum
from django.http import HttpResponseRedirect
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from methodology.models import (
    Activity,
    Artifact,
    EventChannel,
    KarmaAward,
    PipChange,
    Playbook,
    PlaybookVersion,
    ProcessImprovementProposal,
    Skill,
    VersionSource,
)
from methodology.services.karma_service import AwardOutcome, KarmaService
from methodology.services.pip_admin_service import PIPAdminService
from methodology.services.pip_apply_changes_service import (
    PipApplyChangesService,
    bump_playbook_major_version_after_pip_apply,
)
from methodology.services.pip_service import PIPService
from tests.support.experts_data import (
    CedarDataset,
    create_reviewed_major_add_pip,
    load_cedar_baseline,
)
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

_CORRELATION_ID = "pip_policy:s32"
_POLICY_LOGGER = "methodology.services.karma_service"
_ADMIN_LOGGER = "methodology.services.pip_admin_service"
_ENTRY = "KarmaService.award_accepted_changes"
_PRIVATE_CHANGE_BODY = "Private decision text: hidden@example.test cedar-test-token"
_REVIEW_INTERLEAVE_TIMEOUT = 30
_PUBLISHED_REVIEW_NOTE = "Confirmed in the publishing request"


def _record_policy_fixture(
    dataset: CedarDataset, *, entity_type: str = "Activity", second_decision: str = ""
) -> tuple[ProcessImprovementProposal, tuple[PipChange, ...], PlaybookVersion]:
    """Apply and publish real ORM rows below the N2 admin orchestration boundary."""
    pip = create_reviewed_major_add_pip(dataset, entity_type)
    first = pip.changes.get()
    _accept_change(first)
    if second_decision:
        PipChange.objects.create(
            pip=pip,
            change_type="ADD",
            entity_type="Skill",
            order=2,
            name="Second policy fixture",
            content=_PRIVATE_CHANGE_BODY,
            admin_decision=second_decision,
        )
    changes = tuple(pip.changes.order_by("order", "pk"))
    accepted = [
        change for change in changes if change.admin_decision == PipChange.ADMIN_ACCEPT
    ]
    PipApplyChangesService.apply_changes(
        pip=pip, accepted=accepted, playbook=pip.playbook
    )
    bump_playbook_major_version_after_pip_apply(
        pip=pip,
        playbook=pip.playbook,
        actor=dataset.users_by_username["mchen"],
        summary_line="Accepted policy fixture",
    )
    PIPAdminService._apply_terminal_status(
        pip, len(accepted), len(changes) - len(accepted)
    )
    return pip, changes, pip.playbook_versions.get()


def _record_policy_awards(pip: ProcessImprovementProposal) -> tuple[AwardOutcome, ...]:
    return KarmaService.award_accepted_changes(pip=pip, correlation_id=_CORRELATION_ID)


def _ledger_totals(recipient_id: int) -> dict[str, int]:
    return dict(
        KarmaAward.objects.filter(recipient_id=recipient_id)
        .values("category")
        .annotate(total=Sum("points"))
        .values_list("category", "total")
    )


def _added_content_exists(change: PipChange) -> bool:
    """Confirm the proposed content and owning relationship were really created."""
    playbook_id = change.pip.playbook_id
    if change.entity_type == PipChange.ENTITY_ACTIVITY:
        return Activity.objects.filter(
            workflow_id=change.parent_workflow_id,
            workflow__playbook_id=playbook_id,
            name=change.name,
            guidance=change.content,
        ).exists()
    if change.entity_type == PipChange.ENTITY_SKILL:
        return Skill.objects.filter(
            playbook_id=playbook_id, title=change.name, content=change.content
        ).exists()
    assert change.entity_type == PipChange.ENTITY_ARTIFACT
    return Artifact.objects.filter(
        playbook_id=playbook_id,
        produced_by_id=change.produced_by_activity_ref,
        name=change.name,
        description=change.content,
    ).exists()


def _accept_change(change: PipChange) -> None:
    """Persist a real prior admin choice for direct finalization service tests."""
    change.admin_decision = PipChange.ADMIN_ACCEPT
    change.save(update_fields=["admin_decision"])


def _assert_unpublished(pip: ProcessImprovementProposal, award_count: int) -> None:
    """Assert finalization did not persist the decision, history, version or ledger."""
    pip.refresh_from_db()
    assert pip.status == pip.STATUS_REVIEWED and pip.decided_at is None
    assert pip.playbook.version == Decimal("2.0")
    assert not pip.playbook_versions.exists()
    assert KarmaAward.objects.count() == award_count


def _assert_major_publication(
    pip: ProcessImprovementProposal, change: PipChange
) -> None:
    """Verify the version owner's receipt and the ledger event refer to the applied ADD."""
    receipt = pip.playbook_versions.get()
    assert receipt.playbook_id == pip.playbook_id
    assert receipt.version_number == pip.playbook.version == Decimal("3.0")
    assert receipt.source == VersionSource.PIP_SOURCE and receipt.is_major
    assert receipt.snapshot_data == {
        "pip_id": pip.pk,
        "playbook_name": pip.playbook.name,
        "version_before": "2.0",
        "version_after": "3.0",
        "accepted_change_ids": [change.pk],
        "category": "design",
    }
    award = KarmaAward.objects.get(event_identity=f"accepted_change:{change.pk}")
    assert award.recipient_id == pip.created_by_id
    assert award.playbook_id_snapshot == pip.playbook_id
    assert award.change_id_snapshot == change.pk
    assert award.event_channel == EventChannel.ACCEPTED_CHANGE
    assert (award.source_kind, award.points, award.category) == ("major", 500, "design")
    assert award.occurred_at == pip.decided_at and timezone.is_aware(award.occurred_at)


def _post_staff_choice(
    client: Client,
    change_key: tuple[int, int],
    action: str,
    decision: str,
    note: str,
) -> HttpResponseRedirect:
    """Send an actual authenticated staff decision form POST."""
    pip_id, change_id = change_key
    return client.post(
        reverse("pip_admin_review", args=[pip_id]),
        {
            "action": action,
            f"decision_{change_id}": decision,
            f"note_{change_id}": note,
        },
    )


def _post_with_stale_review_snapshot(
    client: Client,
    change_key: tuple[int, int],
    action: str,
    preloaded: Event,
    resume: Event,
    publishing_connection: object,
) -> HttpResponseRedirect:
    """Observe the real read returning in this thread before any write transaction."""

    def pause_after_preload(frame: FrameType, event: str, result: object) -> None:
        if (
            event == "return"
            and frame.f_code is PIPService.get_pip_with_changes.__code__
        ):
            assert isinstance(result, ProcessImprovementProposal)
            assert (
                result.pk == change_key[0] and result.status == result.STATUS_REVIEWED
            )
            assert connection.connection is not publishing_connection
            assert not connection.in_atomic_block
            preloaded.set()
            assert resume.wait(_REVIEW_INTERLEAVE_TIMEOUT), (
                "Publishing request timed out"
            )

    original_profile = sys.getprofile()
    sys.setprofile(pause_after_preload)
    try:
        return _post_staff_choice(
            client, change_key, action, PipChange.ADMIN_REJECT, "Stale rejection note"
        )
    finally:
        sys.setprofile(original_profile)
        connections.close_all()


def _publish_while_staff_request_has_stale_snapshot(
    publisher: Client, stale_client: Client, change: PipChange, action: str
) -> tuple[HttpResponseRedirect, dict[str, object], dict[str, object]]:
    """Commit publication on the first connection while the stale request waits."""
    preloaded, resume = Event(), Event()
    pip = change.pip
    change_key = pip.pk, change.pk
    publishing_connection = connection.connection
    assert publishing_connection is not None and not connection.in_atomic_block
    with ThreadPoolExecutor(max_workers=1) as worker:
        stale = worker.submit(
            _post_with_stale_review_snapshot,
            stale_client,
            change_key,
            action,
            preloaded,
            resume,
            publishing_connection,
        )
        try:
            assert preloaded.wait(_REVIEW_INTERLEAVE_TIMEOUT), (
                "No stale Reviewed snapshot"
            )
            published = _post_staff_choice(
                publisher,
                change_key,
                "finalize",
                PipChange.ADMIN_ACCEPT,
                _PUBLISHED_REVIEW_NOTE,
            )
            assert (published.status_code, published.url) == (
                302,
                reverse("pip_detail", args=[pip.pk]),
            )
            pip.refresh_from_db()
            change.refresh_from_db()
            assert pip.status == pip.STATUS_ACCEPTED
            assert (change.admin_decision, change.admin_note) == (
                PipChange.ADMIN_ACCEPT,
                _PUBLISHED_REVIEW_NOTE,
            )
            _assert_major_publication(pip, change)
            receipt = pip.playbook_versions.values().get()
            award = KarmaAward.objects.values().get(
                event_identity=f"accepted_change:{change.pk}"
            )
        finally:
            resume.set()
        return stale.result(timeout=_REVIEW_INTERLEAVE_TIMEOUT), receipt, award


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("action", ["finalize", "save_decisions"])
def test_staff_post_with_stale_review_preserves_original_publication(
    client: Client, action: str, mailoutbox: list[EmailMessage]
) -> None:
    """Two real connections cannot change an already published choice or receipt.

    :param client: Real Django client that publishes the proposal.
    :param action: The concurrently started staff POST. Example: "save_decisions".
    :param mailoutbox: Django's local decision mail capture.
    :return: None. Example: the original award is returned as a duplicate on retry.
    :raises AssertionError: If stale data is saved or an effect is repeated.
    """
    dataset = load_cedar_baseline()
    pip = create_reviewed_major_add_pip(dataset, PipChange.ENTITY_ACTIVITY)
    change = pip.changes.get()
    staff = dataset.users_by_username["mchen"]
    stale_client = Client()
    client.force_login(staff)
    stale_client.force_login(staff)
    response, receipt, award = _publish_while_staff_request_has_stale_snapshot(
        client, stale_client, change, action
    )
    change.refresh_from_db()
    pip.refresh_from_db()
    assert change.admin_decision == PipChange.ADMIN_ACCEPT
    assert change.admin_note == _PUBLISHED_REVIEW_NOTE
    assert (response.status_code, response.url) == (
        302,
        reverse("pip_detail", args=[pip.pk]),
    )
    assert pip.status == pip.STATUS_ACCEPTED and _added_content_exists(change)
    assert pip.playbook.version == Decimal("3.0")
    assert pip.playbook_versions.values().get() == receipt
    (retry,) = _record_policy_awards(pip)
    assert not retry.created and retry.reason == "duplicate"
    assert KarmaAward.objects.values().get(pk=retry.award.pk) == award
    assert _ledger_totals(pip.created_by_id) == {"design": 7700, "development": 1000}
    (sent,) = mailoutbox
    assert sent.to == [pip.created_by.email] and "Decision: ACCEPT" in sent.body


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("entity_type", ["Activity", "Skill", "Artifact"])
def test_finalize_pip_with_major_add_awards_submitter_and_publishes_once(
    client: Client, entity_type: str, mailoutbox: list[EmailMessage]
) -> None:
    """Prove real finalization, exact totals, publication and local decision email.

    :param client: Real Django client. Example: authenticated staff client.
    :param entity_type: Independently restored outline entity. Example: "Skill".
    :param mailoutbox: Django's local decision mail capture.
    :return: None. Example: all persisted effects match the acceptance oracle.
    :raises AssertionError: If recipient, totals, content, version or email differs.
    """
    dataset = load_cedar_baseline()
    pip = create_reviewed_major_add_pip(dataset, entity_type)
    change = pip.changes.get()
    maria, staff = pip.created_by, dataset.users_by_username["mchen"]
    assert not maria.is_staff and staff.is_staff
    unaffected = (pip.playbook.author_id, staff.pk)
    prior_totals = [_ledger_totals(user_id) for user_id in unaffected]
    assert _ledger_totals(maria.pk) == {"design": 7200, "development": 1000}
    prior_count = KarmaAward.objects.count()
    release_awards = KarmaAward.objects.filter(
        source_kind=KarmaAward.SourceKind.RELEASE
    )
    release_count = release_awards.count()
    prior_history_count = pip.playbook.versions.count()
    assert not _added_content_exists(change)
    url = reverse("pip_admin_review", kwargs={"pk": pip.pk})
    post_data = {"action": "finalize", f"decision_{change.pk}": PipChange.ADMIN_ACCEPT}
    client.force_login(maria)
    assert client.post(url, post_data).status_code == 403
    _assert_unpublished(pip, prior_count)
    assert not _added_content_exists(change) and not mailoutbox
    client.force_login(staff)
    detail_url = reverse("pip_detail", kwargs={"pk": pip.pk})
    assert client.post(url, post_data).url == detail_url
    assert client.post(url, post_data).url == detail_url
    pip.refresh_from_db()
    assert pip.status == pip.STATUS_ACCEPTED and _added_content_exists(change)
    _assert_major_publication(pip, change)
    assert _ledger_totals(maria.pk) == {"design": 7700, "development": 1000}
    assert [_ledger_totals(user_id) for user_id in unaffected] == prior_totals
    assert KarmaAward.objects.count() == prior_count + 1
    assert release_awards.count() == release_count
    assert pip.playbook.versions.count() == prior_history_count + 1
    (sent,) = mailoutbox
    assert sent.to == [maria.email]
    assert "Accepted" in sent.subject
    assert f'ADD {entity_type} "{change.name}"' in sent.body
    assert "Decision: ACCEPT" in sent.body and "is now v3.0" in sent.body


@pytest.mark.django_db
@pytest.mark.parametrize("entity_type", ["Activity", "Skill", "Artifact"])
def test_award_accepted_changes_with_retry_preserves_original_event(
    entity_type: str,
) -> None:
    """Replaying a complete event keeps the author's original points and attribution."""
    dataset = load_cedar_baseline()
    pip, (change,), receipt = _record_policy_fixture(dataset, entity_type=entity_type)
    maria = dataset.users_by_username["mrodriguez"]
    original_time = pip.decided_at
    prior_count = KarmaAward.objects.count()
    assert _ledger_totals(maria.pk) == {"design": 7200, "development": 1000}
    assert not maria.is_staff and dataset.users_by_username["mchen"].is_staff

    (first,) = _record_policy_awards(pip)
    Playbook.objects.filter(pk=pip.playbook_id).update(category="product")
    ProcessImprovementProposal.objects.filter(pk=pip.pk).update(
        decided_at=original_time + timedelta(minutes=1)
    )
    (retry,) = _record_policy_awards(pip)

    assert first.created and not retry.created and retry.reason == "duplicate"
    award = retry.award
    assert award == first.award
    assert (
        award.event_identity,
        award.event_channel,
        award.source_kind,
        award.points,
    ) == (
        f"accepted_change:{change.pk}",
        EventChannel.ACCEPTED_CHANGE,
        "major",
        500,
    )
    assert (
        award.recipient_id,
        award.playbook_id_snapshot,
        award.change_id_snapshot,
    ) == (
        maria.pk,
        pip.playbook_id,
        change.pk,
    )
    assert award.entity_type_snapshot is None and award.entity_id_snapshot is None
    assert award.occurred_at == original_time and timezone.is_aware(award.occurred_at)
    assert award.category == receipt.snapshot_data["category"] == "design"
    assert _ledger_totals(maria.pk) == {"design": 7700, "development": 1000}
    assert KarmaAward.objects.count() == prior_count + 1


@pytest.mark.django_db(transaction=True)
def test_finalize_pip_with_outer_rollback_restores_content_version_decision_and_awards(
    mailoutbox: list[EmailMessage],
) -> None:
    """Prove all domain effects and deferred mail obey the real outer transaction.

    :param mailoutbox: Django's local decision mail capture.
    :return: None. Example: no new content, version, award or email after rollback.
    :raises AssertionError: If any rolled-back effect remains.
    """
    dataset = load_cedar_baseline()
    pip = create_reviewed_major_add_pip(dataset, PipChange.ENTITY_ACTIVITY)
    change = pip.changes.get()
    _accept_change(change)
    prior_count = KarmaAward.objects.count()
    with transaction.atomic():
        result = PIPAdminService.finalize_pip(pip, dataset.users_by_username["mchen"])
        assert result.pk == pip.pk and result.status == pip.STATUS_ACCEPTED
        assert _added_content_exists(change)
        _assert_major_publication(result, change)
        assert not mailoutbox
        transaction.set_rollback(True)

    _assert_unpublished(pip, prior_count)
    assert not _added_content_exists(change) and not mailoutbox


def _add_artifact_with_unresolved_producer(
    pip: ProcessImprovementProposal,
) -> PipChange:
    """Add a previously rejected artifact that cannot resolve its producer."""
    return PipChange.objects.create(
        pip=pip,
        change_type=PipChange.CHANGE_ADD,
        entity_type=PipChange.ENTITY_ARTIFACT,
        order=2,
        name="Artifact with missing producer",
        produced_by_activity_ref="#missing-producer",
        admin_decision=PipChange.ADMIN_REJECT,
        admin_note="Prior saved decision",
    )


@pytest.mark.django_db(transaction=True)
def test_finalize_pip_with_invalid_apply_creates_no_award_or_email(
    client: Client, mailoutbox: list[EmailMessage]
) -> None:
    """Prove an apply failure rolls back new choices and restores any saved notes.

    :param client: Real Django client for the staff review POST.
    :param mailoutbox: Django's local decision mail capture.
    :return: None. Example: target remains 2.0 with baseline totals and choices.
    :raises AssertionError: If failed application leaves any finalized effects.
    """
    dataset = load_cedar_baseline()
    pip = create_reviewed_major_add_pip(dataset, PipChange.ENTITY_SKILL)
    skill = pip.changes.get()
    broken_artifact = _add_artifact_with_unresolved_producer(pip)
    prior_count = KarmaAward.objects.count()
    assert not _added_content_exists(skill)
    client.force_login(dataset.users_by_username["mchen"])
    url = reverse("pip_admin_review", kwargs={"pk": pip.pk})
    response = client.post(
        url,
        {
            "action": "finalize",
            f"decision_{skill.pk}": PipChange.ADMIN_ACCEPT,
            f"decision_{broken_artifact.pk}": PipChange.ADMIN_ACCEPT,
            f"note_{skill.pk}": "Do not retain this failed proposal choice",
            f"note_{broken_artifact.pk}": "Do not overwrite the saved note",
        },
        follow=True,
    )
    assert response.redirect_chain == [(url, 302)]
    assert b"Unresolved internal reference" in response.content
    _assert_unpublished(pip, prior_count)
    skill.refresh_from_db()
    broken_artifact.refresh_from_db()
    assert (skill.admin_decision, skill.admin_note) == (PipChange.ADMIN_UNSET, "")
    assert (broken_artifact.admin_decision, broken_artifact.admin_note) == (
        PipChange.ADMIN_REJECT,
        "Prior saved decision",
    )
    assert not _added_content_exists(skill) and not mailoutbox


@contextmanager
def _fail_accepted_change_insert() -> Iterator[None]:
    """Fail the real ledger insert without substituting application services."""
    table = KarmaAward._meta.db_table
    trigger = "s32_fail_accepted_award_insert"
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute(
                "CREATE FUNCTION pg_temp.s32_reject_award() RETURNS trigger LANGUAGE plpgsql AS "
                "$$ BEGIN RAISE EXCEPTION 's32 award storage failure'; END; $$"
            )
            cursor.execute(
                f"CREATE TRIGGER {trigger} BEFORE INSERT ON {table} FOR EACH ROW "
                "WHEN (NEW.event_channel = 'accepted_change') "
                "EXECUTE FUNCTION pg_temp.s32_reject_award()"
            )
        else:
            assert connection.vendor == "sqlite"
            cursor.execute(
                f"CREATE TEMP TRIGGER {trigger} BEFORE INSERT ON {table} "
                "WHEN NEW.event_channel = 'accepted_change' BEGIN "
                "SELECT RAISE(ABORT, 's32 award storage failure'); END"
            )
    try:
        yield
    finally:
        with connection.cursor() as cursor:
            if connection.vendor == "postgresql":
                cursor.execute(f"DROP TRIGGER {trigger} ON {table}")
                cursor.execute("DROP FUNCTION pg_temp.s32_reject_award()")
            else:
                cursor.execute(f"DROP TRIGGER {trigger}")


@pytest.mark.django_db(transaction=True)
def test_finalize_pip_with_award_storage_failure_rolls_back_publication(
    mailoutbox: list[EmailMessage],
) -> None:
    """A real failed ledger insert aborts the owning finalization and its email."""
    dataset = load_cedar_baseline()
    pip = create_reviewed_major_add_pip(dataset, PipChange.ENTITY_ACTIVITY)
    change = pip.changes.get()
    _accept_change(change)
    prior_count = KarmaAward.objects.count()
    with (
        _fail_accepted_change_insert(),
        pytest.raises(DatabaseError, match="s32 award storage failure"),
    ):
        PIPAdminService.finalize_pip(pip, dataset.users_by_username["mchen"])

    _assert_unpublished(pip, prior_count)
    assert not _added_content_exists(change) and not mailoutbox


@pytest.mark.django_db
def test_accepted_change_policy_with_supported_rows_returns_exact_points() -> None:
    """Assert the full contracted operation and entity matrix on stored changes."""
    dataset = load_cedar_baseline()
    pip = dataset.pips_by_key["HIST-MARIA-DESIGN-01"]
    major = ("Activity", "Skill", "Artifact")
    minor_add = ("Workflow", "Phase", "Agent", "Rule")
    matrix = [
        *(("ADD", entity, "", ("major", 500)) for entity in major),
        *(("ADD", entity, "", ("minor", 100)) for entity in minor_add),
        *(
            (op, entity, "", ("minor", 100))
            for op in ("ALTER", "DROP")
            for entity in major + minor_add
        ),
        *((op, "", "skill_activity", ("minor", 100)) for op in ("LINK", "UNLINK")),
    ]
    assert len(matrix) == 23
    for operation, entity, relationship, result in matrix:
        change = PipChange.objects.create(
            pip=pip,
            change_type=operation,
            entity_type=entity,
            relationship_type=relationship,
            source_entity_type=PipChange.ENTITY_SKILL if relationship else "",
            target_entity_type=PipChange.ENTITY_ACTIVITY if relationship else "",
        )
        assert KarmaService._accepted_change_policy(change) == result


@pytest.mark.django_db
def test_accepted_change_policy_with_existing_relationship_types_returns_100_per_change() -> (
    None
):
    """Recognize every relationship supported by the current PIP domain."""
    dataset = load_cedar_baseline()
    pip = dataset.pips_by_key["HIST-MARIA-DESIGN-01"]
    endpoints = (
        ("rule_activity", "Rule", "Activity"),
        ("agent_activity", "Agent", "Activity"),
        ("activity_workflow", "Activity", "Workflow"),
        ("artifact_activity", "Artifact", "Activity"),
        ("activity_predecessor", "Activity", "Activity"),
    )
    for relationship, source, target in endpoints:
        for operation in ("LINK", "UNLINK"):
            change = PipChange.objects.create(
                pip=pip,
                change_type=operation,
                relationship_type=relationship,
                source_entity_type=source,
                target_entity_type=target,
            )
            assert KarmaService._accepted_change_policy(change) == ("minor", 100)


@pytest.mark.django_db
def test_accepted_change_policy_with_unsupported_change_returns_no_award() -> None:
    """Unknown operations, types and relationship shapes earn no default points."""
    dataset = load_cedar_baseline()
    pip = dataset.pips_by_key["HIST-MARIA-DESIGN-01"]
    for operation, entity, relationship in (
        ("COPY", "Activity", ""),
        ("ADD", "Unknown", ""),
        ("DROP", "", ""),
        ("ALTER", "Activity", "skill_activity"),
        ("LINK", "", "invented"),
        ("LINK", "Skill", "skill_activity"),
        ("UNLINK", "", ""),
        ("LINK", "", "skill_activity"),  # Missing the recognized endpoint types.
    ):
        change = PipChange.objects.create(
            pip=pip,
            change_type=operation,
            entity_type=entity,
            relationship_type=relationship,
        )
        assert KarmaService._accepted_change_policy(change) is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invalid_context",
    [
        "nonterminal",
        "rejected",
        "null_creator",
        "no_decision_time",
        "no_accepted_changes",
        "undecided_child",
        "wrong_book",
        "unpublished",
        "wrong_source",
        "missing_receipt",
        "empty_snapshot",
        "wrong_pip",
        "wrong_version",
        "missing_category",
        "missing_ids",
        "empty_ids",
        "wrong_ids",
        "repeated_ids",
        "foreign_id",
        "rejected_id",
        "incomplete_ids",
    ],
)
def test_award_accepted_changes_with_ineligible_context_returns_no_awards(
    invalid_context: str,
) -> None:
    """Malformed publication evidence fails as a whole before any ledger write."""
    dataset = load_cedar_baseline()
    approved = PipChange.ADMIN_ACCEPT
    rejected = PipChange.ADMIN_REJECT
    second = approved if invalid_context == "incomplete_ids" else rejected
    pip, (first, other), receipt = _record_policy_fixture(
        dataset, second_decision=second
    )
    count = KarmaAward.objects.count()
    _invalidate_policy_context(invalid_context, pip, first, other, receipt)
    assert _record_policy_awards(pip) == ()
    assert KarmaAward.objects.count() == count


def _invalidate_policy_context(
    case: str,
    pip: ProcessImprovementProposal,
    first: PipChange,
    other: PipChange,
    receipt: PlaybookVersion,
) -> None:
    """Corrupt one persisted input for each absence or contradiction case."""
    proposal_updates = {
        "nonterminal": {"status": pip.STATUS_REVIEWED},
        "rejected": {"status": pip.STATUS_REJECTED},
        "null_creator": {"created_by": None},
        "no_decision_time": {"decided_at": None},
    }
    receipt_updates = {
        "wrong_book": {"playbook_id": 6101, "version_number": "9.0"},
        "unpublished": {"version_number": "9.0"},
        "wrong_source": {"source": VersionSource.RELEASE},
        "empty_snapshot": {"snapshot_data": {}},
    }
    snapshot_updates = {
        "wrong_pip": {"pip_id": pip.pk + 1},
        "wrong_version": {"version_after": "9.0"},
        "missing_category": {"category": None},
        "missing_ids": {"accepted_change_ids": None},
        "empty_ids": {"accepted_change_ids": []},
        "wrong_ids": {"accepted_change_ids": [str(first.pk)]},
        "repeated_ids": {"accepted_change_ids": [first.pk, first.pk]},
        "foreign_id": {
            "accepted_change_ids": [
                first.pk,
                PipChange.objects.exclude(pip=pip).first().pk,
            ]
        },
        "rejected_id": {"accepted_change_ids": [first.pk, other.pk]},
        "incomplete_ids": {"accepted_change_ids": [first.pk]},
    }
    if case in proposal_updates:
        ProcessImprovementProposal.objects.filter(pk=pip.pk).update(
            **proposal_updates[case]
        )
    elif case in receipt_updates:
        PlaybookVersion.objects.filter(pk=receipt.pk).update(**receipt_updates[case])
    elif case in snapshot_updates:
        receipt.snapshot_data.update(snapshot_updates[case])
        receipt.save(update_fields=["snapshot_data"])
    elif case == "missing_receipt":
        receipt.delete()
    else:
        assert case in ("no_accepted_changes", "undecided_child")
        PipChange.objects.filter(pk=first.pk).update(
            admin_decision=(
                PipChange.ADMIN_REJECT if case == "no_accepted_changes" else ""
            )
        )


@pytest.mark.django_db
def test_award_accepted_changes_with_fabricated_policy_input_rejects() -> None:
    """A manually constructed instance cannot stand in for a reloaded proposal."""
    dataset = load_cedar_baseline()
    pip, _, _ = _record_policy_fixture(dataset)
    with pytest.raises(ValueError, match="persisted proposal"):
        _record_policy_awards(ProcessImprovementProposal(pk=pip.pk))


@pytest.mark.django_db
def test_award_accepted_changes_with_partial_decision_policy_omits_rejected_change() -> (
    None
):
    """Only credit the applied ID even when an untrusted in-memory object disagrees."""
    dataset = load_cedar_baseline()
    pip, (first, rejected), _ = _record_policy_fixture(
        dataset,
        second_decision=PipChange.ADMIN_REJECT,
    )
    pip.status = pip.STATUS_DRAFT
    pip.created_by = dataset.users_by_username["mchen"]
    (result,) = _record_policy_awards(pip)
    assert result.created and result.award.change_id_snapshot == first.pk
    assert result.award.recipient_id == dataset.users_by_username["mrodriguez"].pk
    assert not KarmaAward.objects.filter(
        event_identity=f"accepted_change:{rejected.pk}"
    ).exists()


@pytest.mark.django_db
def test_award_accepted_changes_with_partial_ledger_retry_preserves_existing_rows() -> (
    None
):
    """A partial ledger cannot be quietly filled or logged as a complete retry."""
    dataset = load_cedar_baseline()
    pip, (first, second), _ = _record_policy_fixture(
        dataset, second_decision=PipChange.ADMIN_ACCEPT
    )
    results = _record_policy_awards(pip)
    assert [outcome.award.change_id_snapshot for outcome in results] == [
        first.pk,
        second.pk,
    ]
    assert all(outcome.created for outcome in results)
    retry = _record_policy_awards(pip)
    assert [outcome.award.pk for outcome in retry] == [
        outcome.award.pk for outcome in results
    ]
    assert all(not outcome.created for outcome in retry)
    KarmaAward.objects.filter(pk=results[1].award.pk).delete()
    ledger = set(KarmaAward.objects.values_list("pk", flat=True))
    with pytest.raises(ValidationError, match="partially recorded"):
        _record_policy_awards(pip)
    assert set(KarmaAward.objects.values_list("pk", flat=True)) == ledger


@pytest.mark.django_db
def test_award_accepted_changes_with_conflicting_retry_rejects_the_batch() -> None:
    """A collision on the second accepted ID cannot create the first credit."""
    dataset = load_cedar_baseline()
    pip, (first, second), _ = _record_policy_fixture(
        dataset,
        second_decision=PipChange.ADMIN_ACCEPT,
    )
    conflicting = KarmaAward.objects.create(
        recipient=dataset.users_by_username["mchen"],
        event_identity=f"accepted_change:{second.pk}",
        event_channel=EventChannel.ACCEPTED_CHANGE,
        source_kind=KarmaAward.SourceKind.MAJOR,
        points=500,
        category="design",
        playbook_id_snapshot=pip.playbook_id,
        change_id_snapshot=second.pk,
        occurred_at=pip.decided_at,
    )
    before = KarmaAward.objects.count()
    with pytest.raises(ValidationError, match="conflicting award"):
        _record_policy_awards(pip)
    assert KarmaAward.objects.count() == before
    assert (
        KarmaAward.objects.get(pk=conflicting.pk).recipient_id
        == conflicting.recipient_id
    )
    assert not KarmaAward.objects.filter(change_id_snapshot=first.pk).exists()


@pytest.mark.django_db
def test_award_accepted_changes_with_historical_retry_keeps_original_rows() -> None:
    """Known historical receipt bindings replay without replacing historical data."""
    dataset = load_cedar_baseline()
    pip = dataset.pips_by_key["HIST-MARIA-DESIGN-01"]
    before = set(KarmaAward.objects.values_list("pk", flat=True))
    results = _record_policy_awards(pip)
    assert sorted(outcome.award.points for outcome in results) == [100, 500]
    assert all(not outcome.created for outcome in results)
    assert all(outcome.award.entity_id_snapshot is not None for outcome in results)
    assert set(KarmaAward.objects.values_list("pk", flat=True)) == before


@pytest.mark.django_db
def test_accepted_change_log_story_happy(caplog: LogCaptureFixture) -> None:
    """Prove ordered policy processing, persistence and safe transaction-local counts."""
    dataset = load_cedar_baseline()
    pip = create_reviewed_major_add_pip(dataset, PipChange.ENTITY_ACTIVITY)
    change = pip.changes.get()
    change.content = _PRIVATE_CHANGE_BODY
    change.save(update_fields=["content"])
    _accept_change(change)
    staff = dataset.users_by_username["mchen"]
    with capture_experts_logs(caplog, (_POLICY_LOGGER, _ADMIN_LOGGER)):
        PIPAdminService.finalize_pip(pip, staff)
        _record_policy_awards(pip)
    assert_log_story(
        caplog,
        where=_ENTRY,
        beats={
            "entry": (
                "| entry |",
                f"pip_id={pip.pk}",
                f"correlation_id=pip_finalize:{pip.pk}",
            ),
            "created": (
                "| exit |",
                f"pip_id={pip.pk}",
                "created_count=1",
                "existing_count=0",
                "transaction=pending",
            ),
            "replayed": (
                "| exit |",
                f"pip_id={pip.pk}",
                "created_count=0",
                "existing_count=1",
                "transaction=pending",
            ),
        },
    )
    assert_log_story(
        caplog,
        where="KarmaService._accepted_change_policy",
        beats={
            "processing": (
                "| processing |",
                f"change_id={change.pk}",
                "operation=ADD",
                "entity=Activity",
                "source_kind=major",
                "points=500",
            ),
        },
    )
    assert_log_story(
        caplog,
        where="KarmaService.persist_awards",
        beats={
            "persistence": (
                "| exit |",
                "award_count=1",
                "created_count=1",
                f"correlation_id=pip_finalize:{pip.pk}",
            ),
        },
    )
    assert_log_story(
        caplog,
        where="PIPAdminService._award_finalized_pip",
        beats={
            "hook_completed": (
                "| exit |",
                f"pip_id={pip.pk}",
                f"actor_id={staff.pk}",
                f"recipient_id={pip.created_by_id}",
                f"correlation_id=pip_finalize:{pip.pk}",
                "transaction=pending",
            ),
        },
    )
    for private_data in (
        _PRIVATE_CHANGE_BODY,
        "hidden@example.test",
        "cedar-test-token",
        pip.created_by.email,
    ):
        assert private_data not in caplog.text


@pytest.mark.django_db
def test_accepted_change_log_story_reject(caplog: LogCaptureFixture) -> None:
    """Log safe reasons for ineligible proposals and unsupported private change data."""
    dataset = load_cedar_baseline()
    pip, (change,), _ = _record_policy_fixture(dataset)
    count = KarmaAward.objects.count()
    private_type = "secret-token-should-not-log"
    with caplog.at_level(logging.INFO, logger=_POLICY_LOGGER):
        ProcessImprovementProposal.objects.filter(pk=pip.pk).update(
            status=pip.STATUS_REVIEWED
        )
        assert _record_policy_awards(pip) == ()
        ProcessImprovementProposal.objects.filter(pk=pip.pk).update(
            status=pip.STATUS_ACCEPTED
        )
        PipChange.objects.filter(pk=change.pk).update(
            entity_type=private_type, content=_PRIVATE_CHANGE_BODY
        )
        assert _record_policy_awards(pip) == ()
    assert_log_story(
        caplog,
        where=_ENTRY,
        beats={
            "ineligible": (
                "| branch |",
                f"pip_id={pip.pk}",
                "reason=decision_ineligible",
            ),
            "unsupported": (
                "| branch |",
                f"pip_id={pip.pk}",
                f"change_id={change.pk}",
                "reason=unsupported_change",
            ),
        },
    )
    assert KarmaAward.objects.count() == count
    assert private_type not in caplog.text
    assert (
        _PRIVATE_CHANGE_BODY not in caplog.text
        and pip.created_by.email not in caplog.text
    )
