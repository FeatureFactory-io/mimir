from __future__ import annotations

import logging
from datetime import timedelta

import pytest
from _pytest.logging import LogCaptureFixture
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.test import Client
from django.utils import timezone

from methodology.models import (
    EventChannel,
    KarmaAward,
    PipChange,
    Playbook,
    PlaybookVersion,
    ProcessImprovementProposal,
    VersionSource,
)
from methodology.services.karma_service import AwardOutcome, KarmaService
from methodology.services.pip_admin_service import PIPAdminService
from methodology.services.pip_apply_changes_service import (
    PipApplyChangesService,
    bump_playbook_major_version_after_pip_apply,
)
from tests.support.experts_data import (
    CedarDataset,
    create_reviewed_major_add_pip,
    load_cedar_baseline,
)
from tests.support.log_story import assert_log_story

_CORRELATION_ID = "pip_policy:s32"
_POLICY_LOGGER = "methodology.services.karma_service"
_ENTRY = "KarmaService.award_accepted_changes"
_PRIVATE_CHANGE_BODY = "Private decision text: hidden@example.test cedar-test-token"


def _record_policy_fixture(
    dataset: CedarDataset, *, entity_type: str = "Activity", second_decision: str = ""
) -> tuple[ProcessImprovementProposal, tuple[PipChange, ...], PlaybookVersion]:
    """Apply and publish real ORM rows below the N2 admin orchestration boundary."""
    pip = create_reviewed_major_add_pip(dataset, entity_type)
    first = pip.changes.get()
    first.admin_decision = PipChange.ADMIN_ACCEPT
    first.save(update_fields=["admin_decision"])
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
    receipt = pip.playbook_versions.get()
    # Supply the acceptance attestation that N2 will write in the transaction.
    receipt.snapshot_data.update(
        accepted_change_ids=[change.pk for change in accepted],
        category=pip.playbook.category,
    )
    receipt.save(update_fields=["snapshot_data"])
    return pip, changes, receipt


def _record_policy_awards(pip: ProcessImprovementProposal) -> tuple[AwardOutcome, ...]:
    return KarmaService.award_accepted_changes(pip=pip, correlation_id=_CORRELATION_ID)


def _ledger_totals(recipient_id: int) -> dict[str, int]:
    return dict(
        KarmaAward.objects.filter(recipient_id=recipient_id)
        .values("category")
        .annotate(total=Sum("points"))
        .values_list("category", "total")
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("entity_type", ["Activity", "Skill", "Artifact"])
def test_finalize_pip_with_major_add_awards_submitter_and_publishes_once(
    client: Client, entity_type: str
) -> None:
    """Prove real finalization, exact totals, publication and local decision email.

    :param client: Real Django client. Example: authenticated staff client.
    :param entity_type: Independently restored outline entity. Example: "Skill".
    :return: None. Example: all persisted effects match the acceptance oracle.
    :raises AssertionError: If recipient, totals, content, version or email differs.
    """
    raise NotImplementedError()


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
def test_finalize_pip_with_outer_rollback_restores_content_version_decision_and_awards() -> (
    None
):
    """Prove all domain effects and deferred mail obey the real outer transaction.

    :return: None. Example: no new content, version, award or email after rollback.
    :raises AssertionError: If any rolled-back effect remains.
    """
    raise NotImplementedError()


@pytest.mark.django_db(transaction=True)
def test_finalize_pip_with_invalid_apply_creates_no_award_or_email() -> None:
    """Prove a real invalid reference prevents committed finalization and awards.

    :return: None. Example: target remains 2.0 with baseline totals.
    :raises AssertionError: If failed application creates an award or notification.
    """
    raise NotImplementedError()


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
    pip, (change,), _ = _record_policy_fixture(dataset)
    with caplog.at_level(logging.INFO, logger=_POLICY_LOGGER):
        _record_policy_awards(pip)
        _record_policy_awards(pip)
    assert_log_story(
        caplog,
        where=_ENTRY,
        beats={
            "entry": (
                "| entry |",
                f"pip_id={pip.pk}",
                f"correlation_id={_CORRELATION_ID}",
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
                f"correlation_id={_CORRELATION_ID}",
            ),
        },
    )
    assert change.content not in caplog.text and pip.created_by.email not in caplog.text


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
