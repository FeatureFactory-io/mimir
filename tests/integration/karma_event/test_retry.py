from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, replace
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import Sum
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from pytest import LogCaptureFixture

from methodology.models import (
    Activity,
    KarmaAward,
    PipChange,
    Playbook,
    ProcessImprovementProposal,
)
from methodology.services.karma_service import (
    AwardOutcome,
    AwardSpec,
    ConsumptionChannel,
    KarmaService,
)
from methodology.services.pip_admin_service import PIPAdminService
from methodology.services.pip_service import PIPService
from tests.support.experts_data import CedarDataset, create_reviewed_major_add_pip
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

_LOGGER = "methodology.services.karma_service"
_PERSIST_LOG = "KarmaService.persist_awards"
_MATCH_LOG = "KarmaService._assert_matching_event"
_AWARD_FIELDS = ("pk", *AwardSpec.__dataclass_fields__)
_PRIVATE_BODY = "Private staffing note hidden@example.test cedar-secret-token"
_ACTOR = "mrodriguez"
_AUTHOR = "mchen"
_ACTIVITY_ID = 6203
_ACTION_ID = UUID(int=45)
_NEW_ACTION_ID = UUID(int=1)
_AWARDABLE_REPLAYS = ("gui_copy", "mcp_detail", "export", "major", "minor")


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
def test_consumption_with_new_uuid_creates_new_complete_pair() -> None:
    """Distinguish two deliberate actions from retries of either action.

    :return: None. Example: four rows and plus ten for each recipient.
    :raises AssertionError: New action deduplicated or retry duplicated.
    """
    raise NotImplementedError()


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
def test_event_with_outer_rollback_preserves_atomicity() -> None:
    """Rollback actual pair/accepted recording and associated domain effects.

    :return: None. Example: zero new awards and no committed decision email.
    :raises AssertionError: Any ledger/version/content/decision change survives.
    """
    raise NotImplementedError()


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
def test_event_with_concurrent_writers_preserves_one_complete_event(
    separate_connections: None,
) -> None:
    """Race actual writers on distinct real connections with bounded waits.

    :param separate_connections: Cleanup fixture. Example: no leaked threads.
    :return: None. Example: one complete event and classified loser outcome.
    :raises AssertionError: Duplicate, partial, mixed or unclassified outcome.
    """
    raise NotImplementedError()


@pytest.mark.django_db(transaction=True)
def test_event_with_database_constraints_rejects_changed_recipient() -> None:
    """Exercise real unique constraints, independent of service validation.

    :return: None. Example: changed-recipient live anchor insert fails.
    :raises AssertionError: Database permits a second logical anchor.
    """
    raise NotImplementedError()


@pytest.mark.django_db(transaction=True)
def test_first_release_with_historical_marker_preserves_singleton() -> None:
    """Retain imported first-release marker through retries/author replacement.

    :return: None. Example: one first-release row for the playbook.
    :raises AssertionError: Historical channel is ignored or ownership earns twice.
    """
    raise NotImplementedError()


@pytest.mark.django_db(transaction=True)
def test_copy_receipt_with_retry_and_changed_target_enforces_identity(
    client: Client,
) -> None:
    """Exercise actual CSRF-valid HTTP receipt retries and target conflicts.

    :param client: Real Django client. Example: authenticated Maria session.
    :return: None. Example: retry returns existing; changed target conflicts.
    :raises AssertionError: Boundary bypasses identity or attribution validation.
    """
    raise NotImplementedError()


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
    beats = tuple(
        record.getMessage().split(" | ")[1]
        for record in caplog.records
        if "correlation_id=s45-log-replay" in record.getMessage()
    )
    assert beats.index("entry") < beats.index("validation") < beats.index("exit")
    _assert_replay(replay, consumption_specs)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("reason", ("event_payload_conflict", "event_shape_conflict"))
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


def _race_recording_calls(
    operations: tuple[Callable[[], tuple[AwardOutcome, ...]], ...],
) -> tuple[tuple[AwardOutcome, ...] | Exception, ...]:
    """Run finite, coordinated calls on separately opened real connections.

    :param operations: Real writer closures. Example: two same-identity calls.
    :return: Ordered actual outcomes/errors. Example: created then replayed.
    :raises AssertionError: Timeout, shared connection or leaked worker.
    """
    raise NotImplementedError()
