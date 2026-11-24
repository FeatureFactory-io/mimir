from __future__ import annotations

import sqlite3
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, replace
from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus
from threading import Barrier, Event
from time import monotonic, sleep
from typing import Any
from uuid import UUID

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.exceptions import ValidationError
from django.db import (
    DatabaseError,
    IntegrityError,
    OperationalError,
    close_old_connections,
    connection,
    transaction,
)
from django.db.models import Sum
from django.http import HttpResponse
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from pytest import LogCaptureFixture

from methodology.models import (
    Activity,
    EventChannel,
    KarmaAward,
    PipChange,
    Playbook,
    PlaybookVersion,
    ProcessImprovementProposal,
    Workflow,
)
from methodology.services.karma_service import (
    AwardOutcome,
    AwardSpec,
    ConsumptionChannel,
    KarmaService,
)
from methodology.services.pip_admin_service import PIPAdminService
from methodology.services.pip_service import PIPService
from methodology.services.playbook_service import PlaybookService
from tests.support.experts_data import CedarDataset, create_reviewed_major_add_pip
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

_LOGGER = "methodology.services.karma_service"
_PERSIST_LOG = "KarmaService.persist_awards"
_MATCH_LOG = "KarmaService._assert_matching_event"
_EVENT_LOG = "KarmaService._persist_event_atomic"
_CONSUMPTION_LOG = "KarmaService.award_successful_consumption"
_RELEASE_LOG = "KarmaService.award_first_release"
_AWARD_FIELDS = ("pk", *AwardSpec.__dataclass_fields__)
_PRIVATE_BODY = "Private staffing note hidden@example.test cedar-secret-token"
_ACTOR = "mrodriguez"
_AUTHOR = "mchen"
_ACTIVITY_ID = 6203
_ACTION_ID = UUID(int=45)
_NEW_ACTION_ID = UUID(int=1)
_AWARDABLE_REPLAYS = ("gui_copy", "mcp_detail", "export", "major", "minor")
_RACE_TIMEOUT = 12
_RACE_POLL_SECONDS = 0.01
_SQLITE_PRIMARY_RESULT_CODE_MASK = 0xFF
_WINNER_TRACE = "s45-race-winner"
_LOSER_TRACE = "s45-race-loser"
_LEDGER_TABLE = '"methodology_karmaaward"'

RecordingResult = tuple[AwardOutcome, ...] | ValidationError | OperationalError


class _CancelOuterTransaction(Exception):
    """Roll back otherwise-successful Cedar actions through the real owner."""


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("commit", (False, True), ids=("rollback", "commit"))
def test_consumption_log_story_with_outer_transaction_reports_pending_pair(
    cedar_dataset: CedarDataset, caplog: LogCaptureFixture, commit: bool
) -> None:
    """Keep the logged pair pending inside commit and rollback paths alike."""
    actor = cedar_dataset.users_by_username[_ACTOR]
    identity = f"consumption:gui_copy:{actor.pk}:{_ACTION_ID}"
    with capture_experts_logs(caplog, (_LOGGER,)), transaction.atomic():
        outcomes = KarmaService.award_successful_consumption(
            actor, "activity", _ACTIVITY_ID, _ACTION_ID, channel="gui_copy"
        )
        assert len(outcomes) == 2 and all(outcome.created for outcome in outcomes)
        assert len(_event_rows(identity)) == 2
        context = (f"event_identity={identity}", "transaction=pending")
        assert_log_story(
            caplog,
            where=_CONSUMPTION_LOG,
            beats={
                "stage": ("| processing |", "status=staged", *context),
                "exit": ("| exit |", "created_count=2", *context),
            },
        )
        if not commit:
            transaction.set_rollback(True)
    assert len(_event_rows(identity)) == (2 if commit else 0)
    assert "status=applied" not in caplog.text
    assert "transaction=committed" not in caplog.text


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("commit", (False, True), ids=("rollback", "commit"))
def test_first_release_log_story_with_outer_transaction_reports_pending_award(
    cedar_dataset: CedarDataset, caplog: LogCaptureFixture, commit: bool
) -> None:
    """Prove the service record qualifies the award until publication commits."""
    book = cedar_dataset.playbooks_by_pk[6302]
    author = cedar_dataset.users_by_username["nberg"]
    Workflow.objects.create(playbook=book, name="Workshop preparation", order=1)
    identity = KarmaService.first_release_identity(book.pk)
    receipt = PlaybookVersion.objects.filter(playbook=book, version_number="1.0")
    correlation_id = "s45-release-outer-transaction"
    with capture_experts_logs(caplog, (_LOGGER,)), transaction.atomic():
        result = PlaybookService.release_playbook_with_award(
            book.pk,
            author,
            description="Initial workshop release",
            correlation_id=correlation_id,
        )
        assert result.first_release_award.created and receipt.exists()
        assert len(_event_rows(identity)) == 1
        context = (f"correlation_id={correlation_id}", "transaction=pending")
        assert_log_story(
            caplog,
            where=_RELEASE_LOG,
            beats={"exit": ("| exit |", "created=true", "points=5000", *context)},
        )
        if not commit:
            transaction.set_rollback(True)
    book.refresh_from_db()
    assert book.status == ("released" if commit else "draft")
    assert receipt.exists() is commit
    assert len(_event_rows(identity)) == int(commit)
    assert "transaction=committed" not in caplog.text


def _event_rows(event_identity: str) -> tuple[dict[str, object], ...]:
    """Read every field and PK from a real event in stable recipient order."""
    return tuple(
        KarmaAward.objects.filter(event_identity=event_identity)
        .order_by("recipient_id")
        .values(*_AWARD_FIELDS)
    )


def _snapshot_award(award: KarmaAward) -> AwardSpec:
    """Reconstruct an immutable specification from all persisted award fields."""
    return AwardSpec(
        **{name: getattr(award, name) for name in AwardSpec.__dataclass_fields__}
    )


def _category_totals(recipient_ids: tuple[int, ...]) -> dict[tuple[int, str], int]:
    """Project per-category totals from actual ledger rows for every recipient."""
    totals = (
        KarmaAward.objects.filter(recipient_id__in=recipient_ids)
        .values_list("recipient_id", "category")
        .annotate(total=Sum("points"))
    )
    return {(recipient, category): points for recipient, category, points in totals}


def _independent_pair(specs: tuple[AwardSpec, ...]) -> tuple[AwardSpec, ...]:
    """Give another deliberate activity copy a key sorted ahead of the original."""
    identity = KarmaService._canonical_consumption_identity(
        specs[0].recipient_id, _NEW_ACTION_ID, "gui_copy"
    )
    return tuple(replace(spec, event_identity=identity) for spec in specs)


def _finalize_accepted_pip(
    dataset: CedarDataset, kind: str
) -> ProcessImprovementProposal:
    """Exercise actual finalization once for a reviewed major or minor Cedar case."""
    if kind == "major":
        pip = create_reviewed_major_add_pip(dataset, PipChange.ENTITY_ACTIVITY)
    else:
        book = dataset.playbooks_by_pk[6106]
        actor = dataset.users_by_username[_ACTOR]
        pip = PIPService.create_draft_for_playbook(
            actor=actor,
            playbook_id=book.pk,
            title="S45 minor contribution",
            summary="Add the review workflow.",
        )
        PIPService.add_change(
            actor=actor,
            pip=pip,
            change_type=PipChange.CHANGE_ADD,
            entity_type=PipChange.ENTITY_WORKFLOW,
            name="S45 review workflow",
            content="Review form accessibility.",
        )
        pip.status = pip.STATUS_REVIEWED
        pip.submitted_at = pip.reviewed_at = timezone.now()
        pip.save(update_fields=["status", "submitted_at", "reviewed_at"])
    change = pip.changes.get()
    return PIPAdminService.finalize_pip(
        pip,
        dataset.users_by_username[_AUTHOR],
        decisions={change.pk: (PipChange.ADMIN_ACCEPT, "Confirmed review")},
    )


def _assert_replay(
    outcomes: tuple[AwardOutcome, ...], originals: tuple[AwardSpec, ...]
) -> None:
    """Require outcome order, full historical payload and duplicate status."""
    assert len(outcomes) == len(originals)
    for outcome, original in zip(outcomes, originals, strict=True):
        assert not outcome.created and outcome.reason == "duplicate"
        assert outcome.award is not None
        assert _snapshot_award(outcome.award) == original


def _repeat_consumption(dataset: CedarDataset, channel: ConsumptionChannel) -> None:
    """Certify one actual successful-consumption receipt and its exact replay."""
    actor, author = (dataset.users_by_username[name] for name in (_ACTOR, _AUTHOR))
    identity = f"consumption:{channel}:{actor.pk}:{_ACTION_ID}"
    old_count = KarmaAward.objects.count()
    totals = _category_totals((actor.pk, author.pk))
    created = KarmaService.award_successful_consumption(
        actor, "activity", _ACTIVITY_ID, _ACTION_ID, channel=channel
    )
    assert len(created) == 2 and all(outcome.created for outcome in created)
    learn, consume = tuple(_snapshot_award(outcome.award) for outcome in created)
    assert timezone.is_aware(learn.occurred_at)
    assert learn == AwardSpec(
        actor.pk,
        "learning",
        5,
        "development",
        identity,
        6201,
        None,
        learn.occurred_at,
        channel,
        "activity",
        _ACTIVITY_ID,
    )
    assert consume == replace(learn, recipient_id=author.pk, source_kind="consumption")
    rows = _event_rows(identity)
    replay = KarmaService.award_successful_consumption(
        actor, "activity", _ACTIVITY_ID, _ACTION_ID, channel=channel
    )
    _assert_replay(replay, (learn, consume))
    assert tuple(result.award.pk for result in replay) == tuple(
        result.award.pk for result in created
    )
    assert _event_rows(identity) == rows
    for recipient in (actor.pk, author.pk):
        totals[recipient, "development"] += 5
    assert _category_totals((actor.pk, author.pk)) == totals
    assert KarmaAward.objects.count() == old_count + 2


def _repeat_accepted_change(dataset: CedarDataset, kind: str) -> None:
    """Certify one publication, its stored singleton and a side-effect-free retry."""
    submitter_id = dataset.users_by_username[_ACTOR].pk
    old_count = KarmaAward.objects.count()
    totals = _category_totals((submitter_id,))
    book = dataset.playbooks_by_pk[6106]
    old_versions = book.versions.count()
    pip = _finalize_accepted_pip(dataset, kind)
    change_id = pip.changes.get().pk
    identity = f"accepted_change:{change_id}"
    (original,) = KarmaAward.objects.filter(event_identity=identity)
    points = 500 if kind == "major" else 100
    assert _snapshot_award(original) == AwardSpec(
        submitter_id,
        kind,
        points,
        "design",
        identity,
        book.pk,
        change_id,
        pip.decided_at,
        "accepted_change",
        None,
        None,
    )
    assert timezone.is_aware(original.occurred_at)
    assert pip.status == pip.STATUS_ACCEPTED
    (publication,) = pip.playbook_versions.values()
    (notification,) = mail.outbox
    rows = _event_rows(identity)
    replay = KarmaService.award_accepted_changes(
        pip=pip, correlation_id="s45-replay-pip"
    )
    _assert_replay(replay, (_snapshot_award(original),))
    assert replay[0].award.pk == original.pk and _event_rows(identity) == rows
    pip.refresh_from_db()
    assert pip.status == pip.STATUS_ACCEPTED and pip.decided_at == original.occurred_at
    assert (
        pip.playbook.version == Decimal("3.0")
        and book.versions.count() == old_versions + 1
    )
    assert tuple(pip.playbook_versions.values()) == (publication,) and mail.outbox == [
        notification
    ]
    totals[submitter_id, "design"] += points
    assert _category_totals((submitter_id,)) == totals
    assert KarmaAward.objects.count() == old_count + 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind", _AWARDABLE_REPLAYS)
def test_record_event_with_repeated_write_preserves_original_event(
    cedar_dataset: CedarDataset, kind: str, mailoutbox: list[mail.EmailMessage]
) -> None:
    """Replay actual singleton and paired receipts after one successful operation.

    :param cedar_dataset: Real baseline. Example: Maria, Mike and their ledger.
    :param kind: Source or channel under test. Example: "mcp_detail".
    :param mailoutbox: Fresh local notification state. Example: no initial messages.
    :return: None. Example: unchanged PK, timestamp, payload, totals and publication.
    :raises AssertionError: Replay changes persisted data or duplicates side effects.
    """
    assert not mailoutbox
    if kind in ("major", "minor"):
        _repeat_accepted_change(cedar_dataset, kind)
    else:
        _repeat_consumption(cedar_dataset, kind)


@pytest.mark.django_db(transaction=True)
def test_consumption_with_new_uuid_creates_new_complete_pair(
    cedar_dataset: CedarDataset,
) -> None:
    """Distinguish two deliberate actions from retries of either action.

    :param cedar_dataset: Actual actors and released Activity.
    :return: None. Example: four rows and plus ten for each recipient.
    :raises AssertionError: New action deduplicated or retry duplicated.
    """
    actor, author = (
        cedar_dataset.users_by_username[name] for name in (_ACTOR, _AUTHOR)
    )
    recipients = (actor.pk, author.pk)
    totals = _category_totals(recipients)
    old_count = KarmaAward.objects.count()
    original_events = {}
    for action in (_ACTION_ID, _NEW_ACTION_ID):
        created = KarmaService.award_successful_consumption(
            actor, "activity", _ACTIVITY_ID, action, channel="gui_copy"
        )
        assert created[0].created and created[1].created
        assert (
            created[0].award.recipient_id,
            created[1].award.recipient_id,
        ) == recipients
        assert tuple(outcome.award.points for outcome in created) == (5, 5)
        original_events[action] = tuple(
            _snapshot_award(outcome.award) for outcome in created
        )
    assert len({specs[0].event_identity for specs in original_events.values()}) == 2
    for action, originals in original_events.items():
        rows = _event_rows(originals[0].event_identity)
        replay = KarmaService.award_successful_consumption(
            actor, "activity", _ACTIVITY_ID, action, channel="gui_copy"
        )
        _assert_replay(replay, originals)
        assert len(rows) == 2 and _event_rows(originals[0].event_identity) == rows
    for recipient in recipients:
        totals[recipient, "development"] += 10
    assert _category_totals(recipients) == totals
    assert KarmaAward.objects.count() == old_count + 4


def _alter_pair(
    pair: tuple[AwardSpec, ...], field: str, dataset: CedarDataset
) -> tuple[AwardSpec, ...]:
    """Build a concrete alternative to a previously recorded complete pair."""
    learner, author = pair
    alternate_user = dataset.users_by_username["hkim"]
    alternate_activity = (
        Activity.objects.create(workflow_id=6202, name="Alternate S45 lookup", order=2)
        if field == "entity-id"
        else None
    )
    common = {
        "category": {"category": "design"},
        "points": {"points": 6},
        "playbook": {"playbook_id_snapshot": 6204},
        "entity-type": {"entity_type_snapshot": "workflow"},
        "entity-id": {
            "entity_id_snapshot": alternate_activity.pk if alternate_activity else None
        },
        "changed-id": (
            {
                "change_id_snapshot": dataset.pips_by_key["HIST-MARIA-DESIGN-01"]
                .changes.first()
                .pk
            }
            if field == "changed-id"
            else {}
        ),
        "channel": {"event_channel": "mcp_detail"},
        "fresh-time": {"occurred_at": learner.occurred_at + timedelta(minutes=1)},
        "naive-time": {"occurred_at": learner.occurred_at.replace(tzinfo=None)},
        "missing-target": {"entity_type_snapshot": None, "entity_id_snapshot": None},
        "missing-playbook": {"playbook_id_snapshot": None},
    }
    shapes = {
        "learner": (replace(learner, recipient_id=alternate_user.pk), author),
        "author": (learner, replace(author, recipient_id=alternate_user.pk)),
        "remove": (learner,),
        "add": (learner, author, replace(author, recipient_id=alternate_user.pk)),
        "duplicate": (learner, replace(author, recipient_id=learner.recipient_id)),
        "source": (
            replace(learner, source_kind="consumption"),
            replace(author, source_kind="learning"),
        ),
        "two-authors": (replace(learner, source_kind="consumption"), author),
        "different-time": (
            learner,
            replace(author, occurred_at=author.occurred_at + timedelta(seconds=1)),
        ),
    }
    if field in common:
        return tuple(replace(spec, **common[field]) for spec in pair)
    return shapes[field]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "field",
    (
        "category",
        "points",
        "playbook",
        "entity-type",
        "entity-id",
        "changed-id",
        "channel",
        "learner",
        "author",
        "remove",
        "add",
        "duplicate",
        "source",
        "two-authors",
        "different-time",
        "fresh-time",
        "naive-time",
        "missing-target",
        "missing-playbook",
    ),
)
def test_persist_awards_with_changed_payload_rejects_entire_batch(
    consumption_specs: tuple[AwardSpec, ...], cedar_dataset: CedarDataset, field: str
) -> None:
    """Check every logical field and shape; accept fresh request time alone.

    :param consumption_specs: Pair built for an authorized real Cedar target.
    :param cedar_dataset: Actual alternative accounts and content references.
    :param field: Logical or shape variation. Example: "category".
    :return: None. Example: a conflicting complete batch persists nothing new.
    :raises AssertionError: Conflict inserts rows or valid replay changes time/order.
    """
    created = KarmaService.persist_awards(
        consumption_specs, correlation_id="s45-original"
    )
    assert all(outcome.created for outcome in created)
    identity = consumption_specs[0].event_identity
    original_rows = _event_rows(identity)
    old_count = KarmaAward.objects.count()
    alternative = _alter_pair(consumption_specs, field, cedar_dataset)
    if field == "fresh-time":
        replay = KarmaService.persist_awards(
            alternative[::-1], correlation_id="s45-time-only"
        )
        _assert_replay(replay, consumption_specs[::-1])
    else:
        with (
            CaptureQueriesContext(connection) as queries,
            pytest.raises(ValidationError),
        ):
            KarmaService.persist_awards(
                (*_independent_pair(consumption_specs), *alternative),
                correlation_id="s45-conflicting-batch",
            )
        assert not any(
            query["sql"].lstrip().upper().startswith("INSERT") for query in queries
        )
    assert (
        KarmaAward.objects.count() == old_count
        and _event_rows(identity) == original_rows
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "field", ("recipient_id", "category", "source_kind", "change_id_snapshot")
)
def test_persist_accepted_singleton_with_changed_payload_rejects_entire_batch(
    consumption_specs: tuple[AwardSpec, ...], cedar_dataset: CedarDataset, field: str
) -> None:
    """Reject direct changes to a real accepted-change receipt in a mixed batch.

    :param consumption_specs: Independent complete live consumption event.
    :param cedar_dataset: Real actors and actual PIP publication fixture.
    :param field: Singleton field under test. Example: "source_kind".
    :return: None. Example: no consumption written alongside a changed award.
    :raises AssertionError: Existing singleton changes or a second event is written.
    """
    pip = _finalize_accepted_pip(cedar_dataset, "major")
    identity = f"accepted_change:{pip.changes.get().pk}"
    original = _snapshot_award(KarmaAward.objects.get(event_identity=identity))
    changes = {
        "recipient_id": {"recipient_id": pip.playbook.author_id},
        "category": {"category": "development"},
        "source_kind": {"source_kind": "minor", "points": 100},
        "change_id_snapshot": {
            "change_id_snapshot": PipChange.objects.exclude(
                pk=original.change_id_snapshot
            )
            .first()
            .pk
        },
    }
    rows = _event_rows(identity)
    old_count = KarmaAward.objects.count()
    with pytest.raises(ValidationError):
        KarmaService.persist_awards(
            (*consumption_specs, replace(original, **changes[field])),
            correlation_id="s45-changed-singleton",
        )
    assert _event_rows(identity) == rows and KarmaAward.objects.count() == old_count


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("change", ("entity-type", "entity-id", "category", "author"))
def test_consumption_reassignment_with_changed_payload_preserves_the_receipt(
    cedar_dataset: CedarDataset, change: str
) -> None:
    """Exercise actual receipt retries after authorized target or attribution changes.

    :param cedar_dataset: Actual authenticated actor, content and playbook author.
    :param change: Domain mutation or replacement target. Example: "author".
    :return: None. Example: original learner/author rows remain byte-for-byte equal.
    :raises AssertionError: An altered action receives credit or rewrites old attribution.
    """
    actor = cedar_dataset.users_by_username[_ACTOR]
    kind, entity_id = "activity", _ACTIVITY_ID
    created, _ = KarmaService.award_successful_consumption(
        actor, kind, entity_id, _ACTION_ID, channel="gui_copy"
    )
    identity = created.award.event_identity
    rows = _event_rows(identity)
    old_count = KarmaAward.objects.count()
    if change == "entity-type":
        kind, entity_id = "workflow", 6202
    elif change == "entity-id":
        entity_id = Activity.objects.create(
            workflow_id=6202, name="Different S45 target", order=2
        ).pk
    elif change == "category":
        Playbook.objects.filter(pk=6201).update(category="design")
    else:
        Playbook.objects.filter(pk=6201).update(
            author=cedar_dataset.users_by_username["hkim"]
        )
    with pytest.raises(ValidationError, match="conflict"):
        KarmaService.award_successful_consumption(
            actor, kind, entity_id, _ACTION_ID, channel="gui_copy"
        )
    assert _event_rows(identity) == rows and KarmaAward.objects.count() == old_count


@pytest.mark.django_db(transaction=True)
def test_event_with_outer_rollback_preserves_atomicity(
    cedar_dataset: CedarDataset,
    consumption_specs: tuple[AwardSpec, ...],
    mailoutbox: list[mail.EmailMessage],
) -> None:
    """Rollback actual pair/accepted recording and associated domain effects.

    :param cedar_dataset: Actual reviewed-PIP actors and versioned content.
    :param consumption_specs: Complete Cedar learner/author pair.
    :param mailoutbox: Actual locmem delivery list.
    :return: None. Example: zero new awards and no committed decision email.
    :raises AssertionError: Any ledger/version/content/decision change survives.
    """
    author = cedar_dataset.users_by_username[_AUTHOR]
    pip = create_reviewed_major_add_pip(cedar_dataset, PipChange.ENTITY_ACTIVITY)
    change = pip.changes.get()
    activity = Activity.objects.filter(
        workflow_id=change.parent_workflow_id, name=change.name
    )
    old_awards = tuple(KarmaAward.objects.order_by("pk").values(*_AWARD_FIELDS))
    old_versions = tuple(pip.playbook.versions.order_by("pk").values())
    old_pip = ProcessImprovementProposal.objects.values().get(pk=pip.pk)
    old_change = PipChange.objects.values().get(pk=change.pk)
    assert not activity.exists() and not mailoutbox
    with pytest.raises(_CancelOuterTransaction), transaction.atomic():
        created = KarmaService.persist_awards(
            consumption_specs, correlation_id="s45-rollback-pair"
        )
        assert len(created) == 2 and all(outcome.created for outcome in created)
        assert len(_event_rows(consumption_specs[0].event_identity)) == 2
        decided = PIPAdminService.finalize_pip(
            pip,
            author,
            decisions={change.pk: (PipChange.ADMIN_ACCEPT, "Confirmed review")},
        )
        assert decided.status == pip.STATUS_ACCEPTED and decided.decided_at is not None
        assert decided.playbook.version == Decimal("3.0")
        assert decided.playbook_versions.count() == 1 and activity.exists()
        assert len(_event_rows(f"accepted_change:{change.pk}")) == 1
        assert not mailoutbox
        raise _CancelOuterTransaction
    pip.refresh_from_db()
    assert pip.playbook.version == Decimal("2.0") and not activity.exists()
    assert tuple(pip.playbook.versions.order_by("pk").values()) == old_versions
    assert not pip.playbook_versions.exists() and not mailoutbox
    assert ProcessImprovementProposal.objects.values().get(pk=pip.pk) == old_pip
    assert PipChange.objects.values().get(pk=change.pk) == old_change
    assert tuple(KarmaAward.objects.order_by("pk").values(*_AWARD_FIELDS)) == old_awards


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "damage", ("missing-author", "missing-learner", "extra-author", "different-time")
)
def test_event_with_partial_existing_pair_rejects_without_repair(
    consumption_specs: tuple[AwardSpec, ...], cedar_dataset: CedarDataset, damage: str
) -> None:
    """Seed individually valid rows that violate the complete-event contract.

    :param consumption_specs: Complete frozen spec pair for Maria and Mike.
    :param cedar_dataset: Real Cedar accounts. Example: an additional valid author.
    :param damage: Persisted shape/time fault. Example: "missing-author".
    :return: None. Example: the missing row is not silently restored.
    :raises AssertionError: A malformed stored event is reused or repaired.
    """
    learner, author = consumption_specs
    third = cedar_dataset.users_by_username["hkim"]
    malformed = {
        "missing-author": (learner,),
        "missing-learner": (author,),
        "extra-author": (learner, author, replace(author, recipient_id=third.pk)),
        "different-time": (
            learner,
            replace(author, occurred_at=author.occurred_at + timedelta(seconds=1)),
        ),
    }
    for spec in malformed[damage]:
        KarmaAward.objects.create(**asdict(spec))
    original = _event_rows(learner.event_identity)
    old_count = KarmaAward.objects.count()
    with pytest.raises(ValidationError) as rejection:
        KarmaService.persist_awards(
            consumption_specs, correlation_id="s45-malformed-existing"
        )
    assert rejection.value.code == "award_event_shape_conflict"
    assert (
        _event_rows(learner.event_identity) == original
        and KarmaAward.objects.count() == old_count
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "race",
    (
        "pair-identical",
        "pair-target",
        "pair-author",
        "singleton-identical",
        "singleton-recipient",
    ),
)
def test_event_with_concurrent_writers_preserves_one_complete_event(
    separate_connections: None,
    consumption_specs: tuple[AwardSpec, ...],
    cedar_dataset: CedarDataset,
    caplog: LogCaptureFixture,
    race: str,
) -> None:
    """Race actual writers on distinct real connections with bounded waits.

    :param separate_connections: Cleanup fixture. Example: no leaked threads.
    :param consumption_specs: Frozen pair from a real Cedar target.
    :param cedar_dataset: Recipients and real PIP or Activity references.
    :param caplog: Observes actual retry decision logs.
    :param race: Two competing immutable event proposals. Example: pair-author.
    :return: None. Example: one complete event and classified loser outcome.
    :raises AssertionError: Duplicate, partial, mixed or unclassified outcome.
    """
    winner, loser = _race_specifications(consumption_specs, cedar_dataset, race)
    event_identity = winner[0].event_identity
    before = KarmaAward.objects.count()
    with capture_experts_logs(caplog, [_LOGGER]):
        first, second = _race_recording_calls(
            (_record(winner, _WINNER_TRACE), _record(loser, _LOSER_TRACE)),
            event_identity,
        )
    assert isinstance(first, tuple) and all(outcome.created for outcome in first)
    assert [_snapshot_award(outcome.award) for outcome in first] == list(winner)
    if race.endswith("identical"):
        assert isinstance(second, tuple)
        _assert_replay(second, winner[::-1])
        assert [result.award.pk for result in second] == [
            result.award.pk for result in first[::-1]
        ]
    else:
        assert (
            isinstance(second, ValidationError)
            and second.code == "award_payload_conflict"
        )
    stored = _event_rows(event_identity)
    assert {row["pk"] for row in stored} == {result.award.pk for result in first}
    assert len(stored) == len(winner) and KarmaAward.objects.count() == before + len(
        winner
    )
    if connection.vendor == "sqlite":
        _assert_sqlite_busy_log(caplog, owner="service", attempt=1)
    elif race == "pair-target":
        independent = _independent_pair(winner)[0].event_identity
        assert_log_story(
            caplog,
            where=_EVENT_LOG,
            beats={
                "discarded staged pair": (
                    "| processing |",
                    f"event_identity={independent}",
                    "commit_state=staged",
                    f"correlation_id={_LOSER_TRACE}",
                ),
            },
        )
        assert not _event_rows(independent)


def _race_specifications(
    pair: tuple[AwardSpec, ...], dataset: CedarDataset, race: str
) -> tuple[tuple[AwardSpec, ...], tuple[AwardSpec, ...]]:
    """Build competing payloads with real target and recipient references."""
    if race in {"pair-target", "pair-author"}:
        field = "entity-id" if race == "pair-target" else "author"
        changed = _alter_pair(pair, field, dataset)[::-1]
        if race == "pair-target":
            # A late PostgreSQL collision must also discard the earlier staged pair.
            changed += _independent_pair(pair)
        return pair, changed
    if race == "pair-identical":
        return pair, _alter_pair(pair, "fresh-time", dataset)[::-1]
    pip = create_reviewed_major_add_pip(dataset, PipChange.ENTITY_ACTIVITY)
    change = pip.changes.get()
    spec = AwardSpec(
        pip.created_by_id,
        "major",
        500,
        pip.playbook.category,
        f"accepted_change:{change.pk}",
        pip.playbook_id,
        change.pk,
        timezone.now(),
        EventChannel.ACCEPTED_CHANGE,
        None,
        None,
    )
    recipient = (
        dataset.users_by_username["hkim"].pk
        if race == "singleton-recipient"
        else spec.recipient_id
    )
    return (spec,), (replace(spec, recipient_id=recipient, occurred_at=timezone.now()),)


@pytest.mark.django_db(transaction=True)
def test_event_with_database_constraints_rejects_changed_recipient(
    consumption_specs: tuple[AwardSpec, ...],
    cedar_dataset: CedarDataset,
) -> None:
    """Exercise real unique constraints, independent of service validation.

    :param consumption_specs: Actual valid GUI consumption pair.
    :param cedar_dataset: Imported release row and distinct candidate recipient.
    :return: None. Example: changed-recipient live anchor insert fails.
    :raises AssertionError: Database permits a second logical anchor.
    """
    learner, author = consumption_specs
    unrelated = User.objects.create_user(username="s45-cascade-recipient")
    original = KarmaAward.objects.create(**asdict(learner))
    conflicting_anchor = replace(learner, recipient_id=unrelated.pk)
    duplicate_recipient = replace(author, recipient_id=learner.recipient_id)
    for invalid in (conflicting_anchor, duplicate_recipient):
        with pytest.raises(IntegrityError), transaction.atomic():
            KarmaAward.objects.bulk_create([KarmaAward(**asdict(invalid))])
    release = KarmaAward.objects.get(event_identity="first_release:6201")
    competing_release = replace(
        _snapshot_award(release),
        recipient_id=unrelated.pk,
        event_identity="s45-competing-release",
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        # Bulk create bypasses model canonical-key validation; the DB must arbitrate.
        KarmaAward.objects.bulk_create([KarmaAward(**asdict(competing_release))])
    extra = KarmaAward.objects.create(
        **asdict(replace(author, recipient_id=unrelated.pk))
    )
    assert tuple(
        KarmaAward.objects.filter(event_identity=learner.event_identity).order_by("pk")
    ) == (original, extra)
    assert release.recipient_id == cedar_dataset.users_by_username[_AUTHOR].pk
    unrelated.delete()
    assert not KarmaAward.objects.filter(pk=extra.pk).exists()
    assert KarmaAward.objects.filter(pk=original.pk).exists()


@pytest.mark.django_db(transaction=True)
def test_first_release_with_historical_marker_preserves_singleton(
    cedar_dataset: CedarDataset,
) -> None:
    """Retain imported first-release marker through retries/author replacement.

    :param cedar_dataset: Real imported historical first-release marker and v1 history.
    :return: None. Example: one first-release row for the playbook.
    :raises AssertionError: Historical channel is ignored or ownership earns twice.
    """
    book = cedar_dataset.playbooks_by_pk[6201]
    new_author = cedar_dataset.users_by_username[_ACTOR]
    identity = KarmaService.first_release_identity(book.pk)
    marker = KarmaAward.objects.get(event_identity=identity)
    original = _snapshot_award(marker)
    rows, versions = _event_rows(identity), tuple(book.versions.order_by("pk").values())
    assert original.event_channel == EventChannel.HISTORICAL and original.points == 5000
    replay = KarmaService.persist_awards(
        (replace(original, occurred_at=timezone.now()),),
        correlation_id="s45-history-replay",
    )
    _assert_replay(replay, (original,))
    assert (
        replay[0].award.pk == marker.pk
        and tuple(book.versions.order_by("pk").values()) == versions
    )
    competing = replace(
        original, recipient_id=new_author.pk, event_channel=EventChannel.RELEASE
    )
    with pytest.raises(ValidationError, match="conflicts with its recorded payload"):
        KarmaService.persist_awards((competing,), correlation_id="s45-history-conflict")
    PlaybookService.revert_released_playbook_to_draft(
        book.pk, actor=marker.recipient, reason="Prepare a revision"
    )
    Playbook.objects.filter(pk=book.pk).update(author=new_author)
    published = PlaybookService.release_playbook_with_award(
        book.pk,
        new_author,
        description="Revised review workflow",
        correlation_id="s45-author-changed",
    )
    assert published.playbook.version == Decimal("3.0")
    assert published.first_release_award.reason == "previously_released"
    assert published.first_release_award.award is None
    assert book.versions.count() == len(versions) + 1
    assert _event_rows(identity) == rows
    assert (
        KarmaAward.objects.filter(
            source_kind="release", playbook_id_snapshot=book.pk
        ).count()
        == 1
    )


@pytest.mark.django_db(transaction=True)
def test_copy_receipt_with_retry_and_changed_target_enforces_identity(
    cedar_dataset: CedarDataset,
) -> None:
    """Exercise actual CSRF-valid HTTP receipt retries and target conflicts.

    :param cedar_dataset: Actual authorized, non-self Cedar Activity and actor.
    :return: None. Example: retry returns existing; changed target conflicts.
    :raises AssertionError: Boundary bypasses identity or attribution validation.
    """
    actor = cedar_dataset.users_by_username[_ACTOR]
    alt = Activity.objects.create(
        workflow_id=6202, name="Second S45 copy target", order=2
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(actor)
    for target in (_ACTIVITY_ID, alt.pk):
        assert (
            client.get(
                reverse(
                    "activity_detail",
                    kwargs={
                        "playbook_pk": 6201,
                        "workflow_pk": 6202,
                        "activity_pk": target,
                    },
                )
            ).status_code
            == HTTPStatus.OK
        )
    token = client.cookies[settings.CSRF_COOKIE_NAME].value
    before = KarmaAward.objects.count()
    _assert_copy_reply(
        _post_copy(client, token, _ACTIVITY_ID, _ACTION_ID),
        HTTPStatus.OK,
        status="applied",
    )
    identity = f"consumption:gui_copy:{actor.pk}:{_ACTION_ID}"
    rows = _event_rows(identity)
    _assert_copy_reply(
        _post_copy(client, token, _ACTIVITY_ID, _ACTION_ID),
        HTTPStatus.OK,
        status="replayed",
    )
    _assert_copy_reply(
        _post_copy(client, token, alt.pk, _ACTION_ID),
        HTTPStatus.CONFLICT,
        status="rejected",
        reason="event_conflict",
    )
    _assert_copy_reply(
        _post_copy(client, token, alt.pk, _NEW_ACTION_ID, points=5000),
        HTTPStatus.BAD_REQUEST,
        status="rejected",
        reason="invalid_payload",
    )
    assert KarmaAward.objects.count() == before + 2 and _event_rows(identity) == rows
    _assert_copy_reply(
        _post_copy(client, token, alt.pk, _NEW_ACTION_ID),
        HTTPStatus.OK,
        status="applied",
    )
    new_rows = _event_rows(f"consumption:gui_copy:{actor.pk}:{_NEW_ACTION_ID}")
    assert len(rows) == len(new_rows) == 2 and _event_rows(identity) == rows
    assert {row["entity_id_snapshot"] for row in new_rows} == {alt.pk}
    assert tuple(row["recipient_id"] for row in new_rows) == tuple(
        row["recipient_id"] for row in rows
    )
    assert KarmaAward.objects.count() == before + 4


def _post_copy(
    client: Client, token: str, target: int, action: UUID, **extra: object
) -> HttpResponse:
    """Post a real browser-format receipt with the session's CSRF cookie token."""
    return client.post(
        reverse("karma_copy_receipt"),
        data={
            "entity_type": "activity",
            "entity_id": target,
            "event_identity": str(action),
            **extra,
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )


def _assert_copy_reply(
    response: HttpResponse, code: HTTPStatus, **payload: str
) -> None:
    """Check the full safe HTTP response without reading it as ledger evidence."""
    assert response.status_code == code
    assert response.json() == payload


@pytest.mark.django_db(transaction=True)
def test_karma_event_log_story_happy(
    consumption_specs: tuple[AwardSpec, ...], caplog: LogCaptureFixture
) -> None:
    """Assert correlated entry, whole-event replay validation and completion.

    :param consumption_specs: Actual five-point pair to create and replay.
    :param caplog: Actual INFO capture. Example: records from KarmaService.
    :return: None. Example: replay exit has zero new and two existing rows.
    :raises AssertionError: Required beat, safe identifiers or outcome is absent.
    """
    identity = consumption_specs[0].event_identity
    with capture_experts_logs(caplog, [_LOGGER]):
        KarmaService.persist_awards(consumption_specs, correlation_id="s45-log-create")
        new_request = tuple(
            replace(spec, occurred_at=spec.occurred_at + timedelta(minutes=1))
            for spec in consumption_specs
        )
        replay = KarmaService.persist_awards(
            new_request, correlation_id="s45-log-replay"
        )
    assert_log_story(
        caplog,
        where=_PERSIST_LOG,
        beats={
            "create entry": (
                "| entry |",
                "event_count=1",
                "row_count=2",
                "correlation_id=s45-log-create",
            ),
            "create exit": (
                "| exit |",
                "created_count=2",
                "existing_count=0",
                "correlation_id=s45-log-create",
            ),
            "replay entry": (
                "| entry |",
                "event_count=1",
                "row_count=2",
                "correlation_id=s45-log-replay",
            ),
            "replay exit": (
                "| exit |",
                "created_count=0",
                "existing_count=2",
                "correlation_id=s45-log-replay",
            ),
        },
    )
    assert_log_story(
        caplog,
        where=_MATCH_LOG,
        beats={
            "validation": (
                "| validation |",
                f"event_identity={identity}",
                "recipient_count=2",
                "payload_match=true",
                "correlation_id=s45-log-replay",
            )
        },
    )
    assert_log_story(
        caplog,
        where=_EVENT_LOG,
        beats={
            "staged": (
                "| processing |",
                f"event_identity={identity}",
                "channel=gui_copy",
                "recipient_count=2",
                "created_count=2",
                "commit_state=staged",
                "correlation_id=s45-log-create",
            ),
            "replayed": (
                "| branch |",
                f"event_identity={identity}",
                "reason=replayed",
                "created_count=0",
                "correlation_id=s45-log-replay",
            ),
        },
    )
    beats = tuple(
        record.getMessage().split(" | ")[1]
        for record in caplog.records
        if "correlation_id=s45-log-replay" in record.getMessage()
    )
    assert beats.index("entry") < beats.index("validation") < beats.index("exit")
    _assert_replay(replay, consumption_specs)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "reason", ("event_payload_conflict", "event_shape_conflict", "database_failure")
)
def test_karma_event_log_story_reject(
    consumption_specs: tuple[AwardSpec, ...], caplog: LogCaptureFixture, reason: str
) -> None:
    """Assert distinct safe reject beats and verify absence of a success claim.

    :param consumption_specs: Real eligible pair. Example: Maria and Mike.
    :param caplog: Actual INFO capture. Example: safe event identity and reason.
    :param reason: Rejection branch under test. Example: "event_payload_conflict".
    :return: None. Example: clear branch reason without private target content.
    :raises AssertionError: Missing reason, false success or secret leakage.
    """
    if reason == "database_failure":
        _assert_database_failure_logs(consumption_specs, caplog)
        return
    learner, author = consumption_specs
    Activity.objects.filter(pk=_ACTIVITY_ID).update(guidance=_PRIVATE_BODY)
    stored = consumption_specs if reason == "event_payload_conflict" else (learner,)
    for spec in stored:
        KarmaAward.objects.create(**asdict(spec))
    request = (replace(learner, category="design"), replace(author, category="design"))
    with capture_experts_logs(caplog, [_LOGGER]), pytest.raises(ValidationError):
        KarmaService.persist_awards(request, correlation_id="s45-log-reject")
    assert_log_story(
        caplog,
        where=_PERSIST_LOG,
        beats={
            "entry": (
                "| entry |",
                "event_count=1",
                "row_count=2",
                "correlation_id=s45-log-reject",
            )
        },
    )
    assert_log_story(
        caplog,
        where=_MATCH_LOG,
        beats={
            "branch": (
                "| branch |",
                f"event_identity={learner.event_identity}",
                f"reason={reason}",
                "correlation_id=s45-log-reject",
            )
        },
    )
    messages = [
        record.getMessage() for record in caplog.records if record.name == _LOGGER
    ]
    assert not any(
        "| exit |" in message or "payload_match=true" in message for message in messages
    )
    assert all(
        secret not in message
        for message in messages
        for secret in (
            _PRIVATE_BODY,
            "hidden@example.test",
            "cedar-secret-token",
        )
    )


@dataclass
class _RaceControl:
    """Coordinate real statements and the visibility of the winner's transaction."""

    staged: Barrier = field(default_factory=lambda: Barrier(2, timeout=_RACE_TIMEOUT))
    attempted_insert: Event = field(default_factory=Event)
    sqlite_statement_busy: Event = field(default_factory=Event)
    winner_can_commit: Event = field(default_factory=Event)
    winner_committed: Event = field(default_factory=Event)
    connection_ids: dict[str, int] = field(default_factory=dict)
    backend_pids: dict[str, int] = field(default_factory=dict)

    def observe_loser_statement(
        self,
        execute: Callable[..., Any],
        sql: str,
        params: object,
        many: bool,
        context: dict[str, Any],
    ) -> Any:
        """Observe actual contention without replacing SQL or its result."""
        ledger_query = _LEDGER_TABLE in sql
        insert = ledger_query and sql.lstrip().startswith("INSERT")
        if insert:
            self.attempted_insert.set()
        if (
            ledger_query
            and sql.lstrip().startswith("SELECT")
            and self.sqlite_statement_busy.is_set()
        ):
            assert self.winner_committed.wait(_RACE_TIMEOUT), (
                "winner did not commit before retry"
            )
        try:
            return execute(sql, params, many, context)
        except OperationalError as error:
            driver_code = getattr(error.__cause__, "sqlite_errorcode", -1)
            if insert and (driver_code & _SQLITE_PRIMARY_RESULT_CODE_MASK) in (
                sqlite3.SQLITE_BUSY,
                sqlite3.SQLITE_LOCKED,
            ):
                self.sqlite_statement_busy.set()
            raise


def _record(
    specifications: tuple[AwardSpec, ...],
    correlation_id: str,
    *,
    caller_owned: bool = False,
) -> Callable[[], tuple[AwardOutcome, ...]]:
    """Bind a real writer call to committed fixture references and its trace."""

    def operation() -> tuple[AwardOutcome, ...]:
        if caller_owned:
            with transaction.atomic():
                return KarmaService.persist_awards(
                    specifications, correlation_id=correlation_id
                )
        return KarmaService.persist_awards(
            specifications, correlation_id=correlation_id
        )

    return operation


def _race_recording_calls(
    operations: tuple[
        Callable[[], tuple[AwardOutcome, ...]], Callable[[], tuple[AwardOutcome, ...]]
    ],
    event_identity: str,
) -> tuple[RecordingResult, RecordingResult]:
    """Run finite, coordinated calls on separately opened real connections.

    :param operations: Real writer closures. Example: two same-identity calls.
    :param event_identity: Actual ledger key withheld by the winning transaction.
    :return: Ordered actual outcomes/errors. Example: created then replayed.
    :raises AssertionError: Timeout, shared connection or leaked worker.
    """
    control = _RaceControl()
    assert not _event_rows(event_identity)
    with ThreadPoolExecutor(max_workers=2) as executor:
        winner = executor.submit(_run_race_worker, control, "winner", operations[0])
        loser = executor.submit(_run_race_worker, control, "loser", operations[1])
        interleave_error: AssertionError | None = None
        try:
            assert control.attempted_insert.wait(_RACE_TIMEOUT), (
                "loser never attempted SQL INSERT"
            )
            assert not _event_rows(event_identity), (
                "winner committed before loser reached SQL"
            )
            if connection.vendor == "postgresql":
                _assert_postgres_waiting_on_winner(control)
            else:
                assert control.sqlite_statement_busy.wait(_RACE_TIMEOUT), (
                    "SQLite did not return a real lock error"
                )
        except AssertionError as error:
            interleave_error = error
        finally:
            control.winner_can_commit.set()
        result = (
            winner.result(timeout=_RACE_TIMEOUT),
            loser.result(timeout=_RACE_TIMEOUT),
        )
        if interleave_error is not None:
            raise interleave_error
    assert len(set(control.connection_ids.values()) | {id(connection.connection)}) == 3
    return result


def _run_race_worker(
    control: _RaceControl,
    role: str,
    operation: Callable[[], tuple[AwardOutcome, ...]],
) -> RecordingResult:
    """Use a distinct real connection and propagate every unexpected worker error."""
    close_old_connections()
    connection.ensure_connection()
    control.connection_ids[role] = id(connection.connection)
    try:
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SET statement_timeout = '10s'")
                cursor.execute("SELECT pg_backend_pid()")
                control.backend_pids[role] = cursor.fetchone()[0]
        if role == "winner":
            with transaction.atomic():
                result = operation()
                control.staged.wait()
                assert control.winner_can_commit.wait(_RACE_TIMEOUT), (
                    "no release for winning transaction"
                )
            control.winner_committed.set()
            return result
        control.staged.wait()
        with connection.execute_wrapper(control.observe_loser_statement):
            try:
                return operation()
            except (ValidationError, OperationalError) as error:
                return error
    finally:
        try:
            assert not connection.in_atomic_block and connection.get_autocommit()
        finally:
            connection.close()


def _assert_postgres_waiting_on_winner(control: _RaceControl) -> None:
    """Require the server to report the actual winner PID as the loser's blocker."""
    deadline = monotonic() + _RACE_TIMEOUT
    with connection.cursor() as cursor:
        while monotonic() < deadline:
            cursor.execute(
                "SELECT pg_blocking_pids(%s)", [control.backend_pids["loser"]]
            )
            if control.backend_pids["winner"] in cursor.fetchone()[0]:
                return
            sleep(_RACE_POLL_SECONDS)
    raise AssertionError(
        "PostgreSQL did not report the uncommitted winner as the loser's blocker"
    )


def _assert_sqlite_busy_log(
    caplog: LogCaptureFixture, *, owner: str, attempt: int
) -> None:
    """Validate that native SQLite contention used the expected transaction owner."""
    assert_log_story(
        caplog,
        where=_PERSIST_LOG,
        beats={
            "contention": (
                "| branch |",
                "vendor=sqlite",
                f"attempt={attempt}",
                f"transaction_owner={owner}",
                "reason=database_busy",
                f"correlation_id={_LOSER_TRACE}",
            ),
        },
    )


def _assert_database_failure_logs(
    specifications: tuple[AwardSpec, ...],
    caplog: LogCaptureFixture,
) -> None:
    """Observe native contention and unrelated SQL errors through their real boundaries."""
    if connection.vendor == "sqlite":
        with capture_experts_logs(caplog, [_LOGGER]):
            first, second = _race_recording_calls(
                (
                    _record(specifications, _WINNER_TRACE),
                    _record(specifications, _LOSER_TRACE, caller_owned=True),
                ),
                specifications[0].event_identity,
            )
        assert isinstance(first, tuple) and isinstance(second, OperationalError)
        _assert_sqlite_busy_log(caplog, owner="caller", attempt=1)
        assert_log_story(
            caplog,
            where=_PERSIST_LOG,
            beats={
                "caller failure": (
                    "| error |",
                    "reason=database_busy",
                    "vendor=sqlite",
                    "transaction_owner=caller",
                    f"correlation_id={_LOSER_TRACE}",
                ),
            },
        )
        loser_messages = (record.getMessage() for record in caplog.records)
        assert not any(
            f"correlation_id={_LOSER_TRACE}" in message
            and ("| exit |" in message or "attempt=2" in message)
            for message in loser_messages
        )
    trace = "s45-unrelated-db-failure"
    with (
        capture_experts_logs(caplog, [_LOGGER]),
        pytest.raises(DatabaseError),
        transaction.atomic(),
    ):
        with connection.cursor() as cursor:
            cursor.execute(
                f"ALTER TABLE {_LEDGER_TABLE} RENAME TO methodology_karmaaward_s45_hidden"
            )
        KarmaService.persist_awards(specifications, correlation_id=trace)
    assert_log_story(
        caplog,
        where=_PERSIST_LOG,
        beats={
            "unrelated failure": (
                "| error |",
                "reason=database_failure",
                f"vendor={connection.vendor}",
                "transaction_owner=caller",
                f"correlation_id={trace}",
            ),
        },
    )
    assert not any(
        f"correlation_id={trace}" in record.getMessage()
        and (
            "| exit |" in record.getMessage()
            or "reason=database_busy" in record.getMessage()
        )
        for record in caplog.records
    )
