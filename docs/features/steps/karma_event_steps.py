"""Acceptance bindings for stable Karma identities and immutable award retries."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime
from decimal import Decimal
from http import HTTPStatus
from uuid import UUID

from behave import given, then, when
from behave.runner import Context
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from methodology.models import (
    Activity,
    EventChannel,
    KarmaAward,
    PipChange,
    Playbook,
    ProcessImprovementProposal,
)
from methodology.services.karma_service import AwardOutcome, AwardSpec, KarmaService
from tests.support.experts_data import CedarDataset, create_reviewed_major_add_pip

_CONSUMER = "mrodriguez"
_AUTHOR = "mchen"
_COPY_ACTIVITY_ID = 6203
_COPY_PLAYBOOK_ID = 6201
_COPY_CHANNEL = EventChannel.GUI_COPY
_ORIGINAL_ACTION = UUID(int=45)
_LATER_ACTION = UUID(int=46)
_MAJOR_POINTS = 500
_COPY_POINTS = 5
_COPY_RECIPIENT_COUNT = 2
_ACCEPTED_VERSION = Decimal("3.0")
_AWARD_FIELDS = tuple(AwardSpec.__dataclass_fields__)

_Rows = tuple[dict[str, object], ...]


@given(
    "one accepted eligible change or successful consumption has a stable event identity"
)
def prepare_stable_award_events(context: Context) -> None:
    """Prepare actual accepted receipt and successful consumption independently.

    :param context: Behave state. Example: context.cedar_dataset from S03.
    :return: None. Example: persisted change receipt plus stable action UUID.
    :raises AssertionError: Fixture/domain prerequisites differ from contract.
    """
    dataset: CedarDataset = context.cedar_dataset
    context.retry_baseline_award_count = KarmaAward.objects.count()
    pip = _finalize_reviewed_change(context)
    context.retry_pip = pip
    context.retry_publication = _publication_snapshot(pip)
    context.retry_notifications = tuple(mail.outbox)
    (notification,) = context.retry_notifications
    assert notification.to == [dataset.users_by_username[_CONSUMER].email]

    accepted_identity = f"accepted_change:{pip.changes.get().pk}"
    copy_identity = _copy_identity(dataset, _ORIGINAL_ACTION)
    original_copy = _record_copy(dataset, _ORIGINAL_ACTION)
    assert len(original_copy) == _COPY_RECIPIENT_COUNT
    assert all(outcome.created for outcome in original_copy)
    context.retry_original_awards = {
        identity: _event_rows(identity)
        for identity in (accepted_identity, copy_identity)
    }
    assert KarmaAward.objects.count() == (
        context.retry_baseline_award_count + 1 + _COPY_RECIPIENT_COUNT
    )


@when("recording that same event is retried")
def retry_recorded_award_events(context: Context) -> None:
    """Replay award recording only, preserving fixed identities and payloads.

    :param context: Prepared real event cases. Example: accepted and copy pair.
    :return: None. Example: actual retry outcomes retained for assertions.
    :raises AssertionError: Recording fails or repeats domain mutations.
    """
    with context.test.captureOnCommitCallbacks(execute=True) as callbacks:
        context.retry_outcomes = (
            KarmaService.award_accepted_changes(
                pip=context.retry_pip, correlation_id="s45-accepted-award-retry"
            ),
            _record_copy(context.cedar_dataset, _ORIGINAL_ACTION),
        )
    assert not callbacks, "Award recording queued a new post-commit action"


@then("exactly one award exists per applicable recipient")
def assert_one_award_per_recipient(context: Context) -> None:
    """Assert complete row payloads and no duplicate applicable recipient.

    :param context: Actual retry results. Example: original PKs and timestamps.
    :return: None. Example: unchanged whole-event field projections.
    :raises AssertionError: Duplicate, missing, extra or changed row.
    """
    for (identity, original), outcomes in zip(
        context.retry_original_awards.items(), context.retry_outcomes, strict=True
    ):
        assert _event_rows(identity) == original, f"Persisted event changed: {identity}"
        assert len(outcomes) == len(original)
        assert all(
            not outcome.created and outcome.reason == "duplicate"
            for outcome in outcomes
        )
        assert {
            outcome.award.pk for outcome in outcomes if outcome.award is not None
        } == {row["pk"] for row in original}

    assert KarmaAward.objects.count() == (
        context.retry_baseline_award_count + 1 + _COPY_RECIPIENT_COUNT
    )
    assert _publication_snapshot(context.retry_pip) == context.retry_publication
    assert tuple(mail.outbox) == context.retry_notifications


@then(
    "acceptance has one submitter award while eligible other-person consumption has consumer and author awards"
)
def assert_event_recipient_cardinality(context: Context) -> None:
    """Assert one submitter award versus exact learner/author pair.

    :param context: Independent accepted/consumption cases. Example: 1 versus 2.
    :return: None. Example: correct recipients, amounts and categories.
    :raises AssertionError: Cardinality or attribution differs.
    """
    dataset: CedarDataset = context.cedar_dataset
    pip: ProcessImprovementProposal = context.retry_pip
    change = pip.changes.get()
    identity = f"accepted_change:{change.pk}"
    (award,) = context.retry_original_awards[identity]
    assert pip.decided_at is not None and timezone.is_aware(pip.decided_at)
    expected = AwardSpec(
        recipient_id=dataset.user_ids[_CONSUMER],
        source_kind="major",
        points=_MAJOR_POINTS,
        category="design",
        event_identity=identity,
        playbook_id_snapshot=pip.playbook_id,
        change_id_snapshot=change.pk,
        occurred_at=pip.decided_at,
        event_channel=EventChannel.ACCEPTED_CHANGE,
        entity_type_snapshot=None,
        entity_id_snapshot=None,
    )
    assert award == {"pk": award["pk"], **asdict(expected)}
    copy_identity = _copy_identity(dataset, _ORIGINAL_ACTION)
    _assert_copy_pair(
        dataset, copy_identity, context.retry_original_awards[copy_identity]
    )


@then("a later intentional consumption is treated as a new event")
def record_later_intentional_consumption(context: Context) -> None:
    """Use a new UUID and prove one additional complete consumption event.

    :param context: Original successful-consumption case. Example: UUID A.
    :return: None. Example: UUID B creates exactly two additional rows.
    :raises AssertionError: New action is suppressed or creates extra awards.
    """
    dataset: CedarDataset = context.cedar_dataset
    identity = _copy_identity(dataset, _LATER_ACTION)
    assert identity not in context.retry_original_awards and not _event_rows(identity)
    before = KarmaAward.objects.count()
    outcomes = _record_copy(dataset, _LATER_ACTION)
    assert len(outcomes) == _COPY_RECIPIENT_COUNT
    assert all(outcome.created and outcome.reason == "created" for outcome in outcomes)
    _assert_copy_pair(dataset, identity, _event_rows(identity))
    assert KarmaAward.objects.count() == before + _COPY_RECIPIENT_COUNT
    for original_identity, original in context.retry_original_awards.items():
        assert _event_rows(original_identity) == original


def _finalize_reviewed_change(context: Context) -> ProcessImprovementProposal:
    """Publish one eligible Cedar ADD via the staff review endpoint.

    :param context: Isolated Behave client and restored Cedar data.
    :return: The persisted accepted proposal, for example Maria's ADD Activity.
    :raises AssertionError: If publication, application or local mail differs.
    """
    dataset: CedarDataset = context.cedar_dataset
    pip = create_reviewed_major_add_pip(dataset, PipChange.ENTITY_ACTIVITY)
    change = pip.changes.get()
    staff = dataset.users_by_username[_AUTHOR]
    versions_before = pip.playbook.versions.count()
    assert staff.is_staff and pip.status == pip.STATUS_REVIEWED
    assert not _applied_activity_rows(change) and not mail.outbox
    context.client.force_login(staff)
    route = {"pk": pip.pk}
    decision = {"action": "finalize", f"decision_{change.pk}": PipChange.ADMIN_ACCEPT}
    # Run the real on-commit callback within Behave's rollback-isolated TestCase.
    with context.test.captureOnCommitCallbacks(execute=True) as callbacks:
        response = context.client.post(
            reverse("pip_admin_review", kwargs=route), decision
        )
        assert not mail.outbox
    assert len(callbacks) == 1
    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("pip_detail", kwargs=route)
    pip.refresh_from_db()
    change.refresh_from_db()
    assert (
        pip.status == pip.STATUS_ACCEPTED
        and change.admin_decision == PipChange.ADMIN_ACCEPT
    )
    assert pip.playbook.version == _ACCEPTED_VERSION
    assert pip.playbook.versions.count() == versions_before + 1
    (activity,) = _applied_activity_rows(change)
    assert activity["guidance"] == change.content
    return pip


def _publication_snapshot(pip: ProcessImprovementProposal) -> dict[str, object]:
    """Read decision, application and publication state for replay comparison.

    :param pip: Persisted single-change proposal, for example an accepted activity.
    :return: Fresh row snapshots of the proposal, change, activity, book and history.
    :raises ProcessImprovementProposal.DoesNotExist: If the proposal disappeared.
    """
    change = pip.changes.get()
    return {
        "proposal": ProcessImprovementProposal.objects.values().get(pk=pip.pk),
        "change": PipChange.objects.values().get(pk=change.pk),
        "activity": _applied_activity_rows(change),
        "playbook": Playbook.objects.values().get(pk=pip.playbook_id),
        "versions": tuple(pip.playbook.versions.order_by("pk").values()),
    }


def _applied_activity_rows(change: PipChange) -> _Rows:
    """Read full activity rows under the chosen workflow.

    :param change: Reviewed ADD Activity, for example the accessibility check.
    :return: Matching rows by PK, empty before publication.
    """
    return tuple(
        Activity.objects.filter(name=change.name, workflow_id=change.parent_workflow_id)
        .order_by("pk")
        .values()
    )


def _record_copy(dataset: CedarDataset, action: UUID) -> tuple[AwardOutcome, ...]:
    """Record the server receipt for a successful authorized activity copy.

    :param dataset: Restored Cedar fixture with Maria and Mike's released activity.
    :param action: Stable copy UUID, for example the same UUID on retry.
    :return: Real service outcomes for Maria's learning and Mike's consumption.
    :raises ValidationError: If the UUID conflicts with its stored event payload.
    """
    return KarmaService.award_successful_consumption(
        dataset.users_by_username[_CONSUMER],
        "activity",
        _COPY_ACTIVITY_ID,
        action,
        channel=_COPY_CHANNEL,
    )


def _copy_identity(dataset: CedarDataset, action: UUID) -> str:
    """Express the contract's stable key independently of the receipt service.

    :param dataset: Restored Cedar fixture containing the authenticated consumer.
    :param action: Explicit UUID of the copy, for example the original action.
    :return: Key scoped to channel, consumer PK and action UUID.
    """
    return f"consumption:{_COPY_CHANNEL}:{dataset.user_ids[_CONSUMER]}:{action}"


def _event_rows(identity: str) -> _Rows:
    """Read every immutable award field and persisted PK for one event.

    :param identity: Full expected event key, for example accepted_change:12.
    :return: Fresh DB snapshots in stable recipient order.
    """
    return tuple(
        KarmaAward.objects.filter(event_identity=identity)
        .order_by("recipient_id")
        .values("pk", *_AWARD_FIELDS)
    )


def _assert_copy_pair(dataset: CedarDataset, identity: str, rows: _Rows) -> None:
    """Check both complete 5-point payloads, including their shared event time.

    :param dataset: Restored Cedar fixture containing both expected recipients.
    :param identity: Expected stable copy key, for example the original UUID's key.
    :param rows: Persisted awards projected from the real ledger.
    :return: None when the learner and author's awards match exactly.
    :raises AssertionError: If cardinality, recipients or immutable payload differ.
    """
    assert len(rows) == _COPY_RECIPIENT_COUNT
    occurred_at = rows[0]["occurred_at"]
    assert isinstance(occurred_at, datetime) and timezone.is_aware(occurred_at)
    learning = AwardSpec(
        recipient_id=dataset.user_ids[_CONSUMER],
        source_kind="learning",
        points=_COPY_POINTS,
        category="development",
        event_identity=identity,
        playbook_id_snapshot=_COPY_PLAYBOOK_ID,
        change_id_snapshot=None,
        occurred_at=occurred_at,
        event_channel=_COPY_CHANNEL,
        entity_type_snapshot="activity",
        entity_id_snapshot=_COPY_ACTIVITY_ID,
    )
    consumption = replace(
        learning, recipient_id=dataset.user_ids[_AUTHOR], source_kind="consumption"
    )
    payloads = {
        row["recipient_id"]: {key: row[key] for key in _AWARD_FIELDS} for row in rows
    }
    assert payloads == {
        learning.recipient_id: asdict(learning),
        consumption.recipient_id: asdict(consumption),
    }
