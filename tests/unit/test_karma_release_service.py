"""Real-database contracts for first-publication commands."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from methodology.models import (
    EventChannel,
    KarmaAward,
    Playbook,
    PlaybookVersion,
    VersionSource,
    Workflow,
)
from methodology.services.karma_service import AwardSpec, KarmaService
from methodology.services.playbook_service import PlaybookService
from tests.support.experts_release import build_nora_release_case


@pytest.fixture
def release_spec(db: None) -> AwardSpec:
    """Create a valid release specification with a real recipient and playbook."""
    recipient = User.objects.create_user(username="award-recipient")
    playbook = Playbook.objects.create(
        name="Award prototype", category="product", author=recipient
    )
    return AwardSpec(
        recipient_id=recipient.pk,
        source_kind="release",
        points=5000,
        category="product",
        event_identity=f"first_release:{playbook.pk}",
        playbook_id_snapshot=playbook.pk,
        change_id_snapshot=None,
        occurred_at=timezone.now(),
        event_channel="release",
        entity_type_snapshot=None,
        entity_id_snapshot=None,
    )


@pytest.fixture
def release_draft(db: None) -> Playbook:
    """Build an independently testable draft with a real owner and workflow."""
    owner = User.objects.create_user(username="release-owner")
    draft = Playbook.objects.create(
        name="Release draft",
        category="product",
        author=owner,
        version=Decimal("0.8"),
    )
    Workflow.objects.create(playbook=draft, name="One workflow", order=1)
    draft.refresh_from_db()
    return draft


@pytest.mark.django_db
def test_award_first_release_with_v1_release_creates_5000_category_snapshot() -> None:
    """Prove author, points, category, original time, source and stable identity."""
    case = build_nora_release_case()
    outcome = PlaybookService.release_playbook_with_award(
        case.playbook.pk,
        case.author,
        description="First public milestone",
        correlation_id="first-release",
    )
    receipt = PlaybookVersion.objects.get(
        playbook=case.playbook, source=VersionSource.RELEASE
    )
    award = KarmaAward.objects.get(recipient=case.author)
    assert outcome.playbook.pk == case.playbook.pk
    assert outcome.playbook.status == "released"
    assert outcome.playbook.version == receipt.version_number == Decimal("1.0")
    assert outcome.first_release_award.created
    assert outcome.first_release_award.award == award
    assert award.points == 5000
    assert award.category == "product"
    assert award.source_kind == KarmaAward.SourceKind.RELEASE
    assert award.event_channel == EventChannel.RELEASE
    assert award.event_identity == f"first_release:{case.playbook.pk}"
    assert award.playbook_id_snapshot == case.playbook.pk
    assert award.change_id_snapshot is None
    assert award.entity_type_snapshot is None
    assert award.entity_id_snapshot is None
    assert award.occurred_at == receipt.created_at
    assert timezone.is_aware(award.occurred_at)


@pytest.mark.django_db
def test_award_first_release_with_same_receipt_returns_existing_award(
    release_draft: Playbook,
) -> None:
    """Replay the original receipt after the playbook category has changed."""
    outcome = PlaybookService.release_playbook_with_award(
        release_draft.pk,
        release_draft.author,
        description="First milestone",
        correlation_id="first-release",
    )
    release_draft.refresh_from_db()
    receipt = PlaybookVersion.objects.get(
        playbook=release_draft, source=VersionSource.RELEASE
    )
    release_draft.category = "design"
    release_draft.save(update_fields=["category"])
    replay = KarmaService.award_first_release(
        release_draft,
        receipt,
        release_draft.author,
        correlation_id="replayed-release",
    )
    assert replay.reason == "duplicate"
    assert not replay.created
    assert replay.award == outcome.first_release_award.award
    assert replay.award.category == "product"
    assert replay.award.occurred_at == receipt.created_at
    assert KarmaAward.objects.filter(recipient=release_draft.author).count() == 1
    assert (
        PlaybookVersion.objects.filter(
            playbook=release_draft, source=VersionSource.RELEASE
        ).count()
        == 1
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "changes",
    [
        {"points": 0},
        {"points": -1},
        {"points": True},
        {"source_kind": "undocumented"},
        {"category": "retired"},
        {"recipient_id": 0},
        {"recipient_id": 2**31 - 1},
        {"event_identity": " "},
        {"event_identity": "first_release:0"},
        {"playbook_id_snapshot": True},
        {"change_id_snapshot": False},
        {"entity_type_snapshot": "playbook"},
        {"occurred_at": datetime(2026, 11, 23, tzinfo=UTC).replace(tzinfo=None)},
        {"event_channel": "gui_copy"},
        {},
    ],
    ids=[
        "zero_points",
        "negative_points",
        "boolean_points",
        "source",
        "category",
        "recipient",
        "missing_recipient",
        "blank_identity",
        "wrong_release_identity",
        "playbook_id",
        "change_id",
        "entity_pair",
        "naive_time",
        "channel",
        "duplicate_recipient",
    ],
)
def test_persist_awards_with_invalid_input_rejects_without_writes(
    release_spec: AwardSpec,
    changes: dict[str, object],
) -> None:
    """Put each malformed specification behind a valid one and verify atomicity."""
    invalid = replace(release_spec, **changes)
    with pytest.raises(ValidationError):
        KarmaService.persist_awards(
            (release_spec, invalid), correlation_id="invalid-award"
        )
    assert not KarmaAward.objects.exists()


@pytest.mark.django_db
def test_persist_awards_with_reused_identity_and_changed_payload_rejects(
    release_spec: AwardSpec,
) -> None:
    """Reject contradictory attribution and roll back other new events in the batch."""
    original = KarmaService.persist_awards(
        (release_spec,), correlation_id="original-award"
    )[0].award
    assert original is not None
    replay = KarmaService.persist_awards(
        (
            replace(
                release_spec,
                occurred_at=release_spec.occurred_at + timedelta(seconds=1),
            ),
        ),
        correlation_id="fresh-request-time",
    )[0]
    assert not replay.created
    assert replay.award.occurred_at == release_spec.occurred_at

    other_book = Playbook.objects.create(
        name="Independent prototype",
        category="product",
        author_id=release_spec.recipient_id,
    )
    other_spec = replace(
        release_spec,
        playbook_id_snapshot=other_book.pk,
        event_identity=f"first_release:{other_book.pk}",
    )
    conflict = replace(release_spec, category="design")
    with pytest.raises(ValidationError):
        KarmaService.persist_awards(
            (other_spec, conflict), correlation_id="conflicting-award"
        )
    assert KarmaAward.objects.get().pk == original.pk
    assert KarmaAward.objects.get().category == "product"
    assert KarmaAward.objects.get().occurred_at == release_spec.occurred_at


@pytest.mark.django_db(transaction=True)
def test_release_with_outer_transaction_rollback_removes_version_and_award(
    release_draft: Playbook,
) -> None:
    """Verify real rollback removes a release and its staged award together."""
    initial_version = release_draft.version
    with pytest.raises(RuntimeError, match="caller cancelled"), transaction.atomic():
        outcome = PlaybookService.release_playbook_with_award(
            release_draft.pk,
            release_draft.author,
            description="First milestone",
            correlation_id="rollback-release",
        )
        assert outcome.first_release_award.created
        assert KarmaAward.objects.filter(recipient=release_draft.author).count() == 1
        assert PlaybookVersion.objects.filter(
            playbook=release_draft, source=VersionSource.RELEASE
        ).exists()
        raise RuntimeError("caller cancelled")

    release_draft.refresh_from_db()
    assert release_draft.status == "draft"
    assert release_draft.version == initial_version
    assert not PlaybookVersion.objects.filter(
        playbook=release_draft, source=VersionSource.RELEASE
    ).exists()
    assert not KarmaAward.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("status", "version", "with_history", "next_version"),
    [
        ("released", "1.2", False, "2.0"),
        ("draft", "1.2", True, "2.0"),
        ("draft", "0.8", True, "1.0"),
    ],
)
def test_release_with_preexisting_history_and_no_ledger_does_not_backfill(
    release_draft: Playbook,
    status: str,
    version: str,
    with_history: bool,
    next_version: str,
) -> None:
    """Keep legacy publication working without granting retroactive Karma."""
    release_draft.status = status
    release_draft.version = Decimal(version)
    release_draft.category = ""
    release_draft.save(update_fields=["status", "version", "category"])
    if with_history:
        PlaybookVersion.objects.create(
            playbook=release_draft,
            version_number=Decimal("1.1"),
            snapshot_data={},
            source=VersionSource.RELEASE,
            is_major=True,
            created_by=release_draft.author,
        )
    outcome = PlaybookService.release_playbook_with_award(
        release_draft.pk,
        release_draft.author,
        description="Legacy milestone",
        correlation_id="legacy-release",
    )
    assert outcome.playbook.version == Decimal(next_version)
    assert outcome.playbook.status == "released"
    assert not outcome.first_release_award.created
    assert outcome.first_release_award.reason == "previously_released"
    assert not KarmaAward.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("rejection", "error_type", "message"),
    [
        ("wrong_owner", PermissionError, "permission to release"),
        ("blank_description", ValidationError, "Release description is required"),
        ("missing_workflow", ValidationError, "at least one workflow"),
        ("invalid_status", ValidationError, "only available for draft or released"),
        ("blank_category", ValidationError, "Choose a valid playbook category"),
        ("retired_category", ValidationError, "Choose a valid playbook category"),
    ],
)
def test_release_with_rejected_precondition_preserves_draft_and_empty_ledger(
    release_draft: Playbook,
    rejection: str,
    error_type: type[Exception],
    message: str,
) -> None:
    """Keep all original release guards and side effects together."""
    author = release_draft.author
    notes = "Release notes"
    if rejection == "wrong_owner":
        author = User.objects.create_user(username="other-user")
    elif rejection == "blank_description":
        notes = "   "
    elif rejection == "missing_workflow":
        Workflow.objects.filter(playbook=release_draft).delete()
    elif rejection == "invalid_status":
        release_draft.status = "disabled"
        release_draft.save(update_fields=["status"])
    else:
        release_draft.category = "" if rejection == "blank_category" else "retired"
        release_draft.save(update_fields=["category"])
    release_draft.refresh_from_db()
    status, version = release_draft.status, release_draft.version
    with pytest.raises(error_type, match=message):
        PlaybookService.release_playbook_with_award(
            release_draft.pk,
            author,
            description=notes,
            correlation_id="rejected-release",
        )
    release_draft.refresh_from_db()
    assert (release_draft.status, release_draft.version) == (status, version)
    assert not PlaybookVersion.objects.filter(
        playbook=release_draft, source=VersionSource.RELEASE
    ).exists()
    assert not KarmaAward.objects.exists()


@pytest.mark.django_db
def test_release_with_conflicting_award_identity_rolls_back_publication(
    release_draft: Playbook,
) -> None:
    """Keep the draft and the existing ledger row when the award writer rejects."""
    existing = KarmaAward.objects.create(
        recipient=release_draft.author,
        source_kind="major",
        event_channel="historical",
        category="product",
        points=500,
        event_identity=f"first_release:{release_draft.pk}",
        occurred_at=timezone.now(),
    )
    initial_version = release_draft.version
    with pytest.raises(ValidationError, match="conflicts with its recorded payload"):
        PlaybookService.release_playbook_with_award(
            release_draft.pk,
            release_draft.author,
            description="Conflicting milestone",
            correlation_id="award-conflict-release",
        )
    release_draft.refresh_from_db()
    assert (release_draft.status, release_draft.version) == ("draft", initial_version)
    assert not release_draft.versions.filter(source=VersionSource.RELEASE).exists()
    assert KarmaAward.objects.get().pk == existing.pk


@pytest.mark.django_db
def test_release_with_legacy_entrypoint_preserves_playbook_return_contract(
    release_draft: Playbook,
) -> None:
    """Exercise the existing public service API without changing its return type."""
    playbook = PlaybookService.release_playbook(
        release_draft.pk,
        release_draft.author,
        description=" \t First milestone \n",
    )
    assert isinstance(playbook, Playbook)
    assert playbook.pk == release_draft.pk
    assert playbook.status == "released"
    assert playbook.version == Decimal("1.0")
    assert (
        PlaybookVersion.objects.get(
            playbook=playbook, source=VersionSource.RELEASE
        ).description
        == "First milestone"
    )
    assert KarmaAward.objects.get(recipient=release_draft.author).points == 5000
