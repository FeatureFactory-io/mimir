"""Real Cedar release-case construction for pytest and AT."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.db import transaction
from django.db.models import Sum
from django.test import Client
from django.utils import timezone

from methodology.models import (
    KarmaAward,
    PipChange,
    Playbook,
    PlaybookVersion,
    Workflow,
)
from methodology.services.pip_service import PIPService
from tests.support.experts_data import load_cedar_baseline

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from methodology.models import ProcessImprovementProposal


@dataclass(frozen=True)
class NoraReleaseCase:
    """Hold the independently restored real Cedar publication case.

    :param author: Persisted nberg user. Example: Nora.
    :param playbook: Persisted draft 6302. Example: Accessible Workshop Starter.
    :param client: Authenticated real Django client. Example: Nora's session.
    """

    author: AbstractBaseUser
    playbook: Playbook
    client: Client


def build_nora_release_case() -> NoraReleaseCase:
    """Load the shared Cedar baseline and prepare its normal release prerequisites.

    Use S03's real loader and fixed Cedar identities. Keep Nora at zero points.
    If adding a required workflow increments the draft minor version, retain that
    real behavior; the first major must still be exactly 1.0. Never call a live
    release/acceptance service while constructing historical baseline objects.

    :return: Isolated real case. Example: Nora, draft 6302 and authenticated client.
    :raises ValueError: If baseline records or totals do not match the contract.
    """
    dataset = load_cedar_baseline()
    author = dataset.users_by_username["nberg"]
    playbook = dataset.playbooks_by_pk[6302]
    if (
        playbook.author_id != author.pk
        or playbook.status != "draft"
        or playbook.category != "product"
        or playbook.version >= Decimal("1.0")
        or KarmaAward.objects.filter(recipient=author).exists()
    ):
        raise ValueError(
            "Cedar Nora must own an unpublished Product draft and have zero Karma."
        )
    Workflow.objects.get_or_create(
        playbook=playbook,
        name="Workshop preparation",
        defaults={"description": "Prepare an accessible workshop.", "order": 1},
    )
    playbook.refresh_from_db()
    client = Client()
    client.force_login(author)
    return NoraReleaseCase(author, playbook, client)


def prepare_reviewed_next_major_pip(
    playbook: Playbook, submitter: AbstractBaseUser
) -> ProcessImprovementProposal:
    """Prepare real reviewed ADD Activity fixture without invoking Galdr.

    Use real draft/change builders; set reviewed metadata only as explicit test
    setup. Do not finalize, publish, award, reset Cedar or set numeric versions.
    :param playbook: Released target as Playbook. Example: Nora's 6302 at v1.0.
    :param submitter: Existing actor. Example: Cedar Maria.
    :return: Undecided reviewed PIP. Example: one ADD Activity under target workflow.
    :raises ValueError: If the target lacks valid released/workflow prerequisites.
    """
    if not isinstance(playbook, Playbook) or playbook.pk is None:
        raise ValueError("A persisted released playbook is required.")
    playbook.refresh_from_db()
    workflow = playbook.workflows.order_by("pk").first()
    if playbook.status != "released" or workflow is None:
        raise ValueError("A released target with a workflow is required.")
    with transaction.atomic():
        pip = PIPService.create_draft_for_playbook(
            actor=submitter,
            playbook_id=playbook.pk,
            title="Confirm workshop access requirements",
        )
        change = PIPService.add_change(
            actor=submitter,
            pip=pip,
            change_type=PipChange.CHANGE_ADD,
            entity_type=PipChange.ENTITY_ACTIVITY,
            parent_workflow_id=workflow.pk,
            name="Confirm participant access needs",
            content="Ask participants to confirm workshop access requirements.",
        )
        pip.status = pip.STATUS_REVIEWED
        pip.submitted_at = pip.reviewed_at = timezone.now()
        pip.save(update_fields=["status", "submitted_at", "reviewed_at", "updated_at"])
        change.galdr_recommendation = PipChange.GALDR_ACCEPT
        change.galdr_reasoning = "The workshop requires this preparation step."
        change.save(
            update_fields=["galdr_recommendation", "galdr_reasoning", "updated_at"]
        )
    return pip


@dataclass(frozen=True)
class ReleaseHistorySnapshot:
    """Retain all persisted first-release fields and existing history bytes."""

    awards: tuple[tuple[Any, ...], ...]
    history: tuple[tuple[int, str], ...]
    recipient_id: int


def capture_release_history(playbook: Playbook) -> ReleaseHistorySnapshot:
    """Read complete immutable release awards and version records from the database.

    :param playbook: Persisted released book. Example: Nora's 6302 at v1.0.
    :return: Complete field snapshot. Example: one award and its initial receipt.
    :raises AssertionError: If the case has no single canonical first-release event.
    """
    awards = KarmaAward.objects.filter(
        source_kind="release", playbook_id_snapshot=playbook.pk
    )
    award = awards.get()
    assert (
        award.event_identity == f"first_release:{playbook.pk}" and award.points == 5000
    )
    history = tuple(
        (row["id"], json.dumps(row, sort_keys=True, default=str))
        for row in PlaybookVersion.objects.filter(playbook=playbook)
        .order_by("pk")
        .values()
    )
    assert history
    return ReleaseHistorySnapshot(
        tuple(awards.order_by("pk").values_list()), history, award.recipient_id
    )


def assert_release_history_preserved(
    playbook: Playbook,
    original: ReleaseHistorySnapshot,
    *,
    version: str,
    recipient_total: int,
) -> None:
    """Require the complete award and prior receipts to survive a later action.

    :param playbook: Persisted lifecycle target. Example: 6302.
    :param original: Pre-action snapshot. Example: actual first release at v1.0.
    :param version: Expected legitimate version. Example: "2.0".
    :param recipient_total: Original recipient's actual total. Example: 5000.
    :return: None. Example: later history grows without changing original rows.
    :raises AssertionError: If the event, prior history, total or current version differs.
    """
    current = capture_release_history(playbook)
    assert current.awards == original.awards
    assert set(original.history).issubset(set(current.history))
    total = KarmaAward.objects.filter(recipient_id=original.recipient_id).aggregate(
        total=Sum("points")
    )["total"]
    assert total == recipient_total
    playbook.refresh_from_db()
    assert playbook.status == "released" and playbook.version == Decimal(version)
