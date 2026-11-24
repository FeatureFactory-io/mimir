"""Real publication lifecycles preserve the original first-release event."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from methodology.models import (
    Activity,
    KarmaAward,
    Playbook,
    PlaybookVersion,
    ProcessImprovementProposal,
    VersionSource,
)
from methodology.services.playbook_service import PlaybookService
from tests.support.experts_data import load_cedar_baseline
from tests.support.experts_release import (
    NoraReleaseCase,
    assert_release_history_preserved,
    build_nora_release_case,
    capture_release_history,
    prepare_reviewed_next_major_pip,
)

User = get_user_model()
NOTES = "Workshop delivery ready for review"
EARNED = "You earned 5,000 Karma for releasing Accessible Workshop Starter"


def _publish(case: NoraReleaseCase, version: str, *, earned: bool = False) -> None:
    """Publish through the real owner POST and inspect its exact alert decision.

    :param case: Real owner/client case. Example: Nora and playbook 6302.
    :param version: Expected published version. Example: "2.0".
    :param earned: Whether the first-release alert is required. Example: False.
    :return: None. Example: publication and actual alert assertions pass.
    :raises AssertionError: If the real domain or log contract differs.
    """
    response = case.client.post(
        reverse("playbook_release", kwargs={"pk": case.playbook.pk}),
        {"release_description": NOTES},
        follow=True,
    )
    assert response.status_code == 200 and response.redirect_chain
    messages = [str(message) for message in response.context["messages"]]
    assert earned or any("released" in message.lower() for message in messages)
    assert (EARNED in messages) is earned
    assert sum("You earned" in message for message in messages) == int(earned)
    case.playbook.refresh_from_db()
    assert case.playbook.status == "released"
    assert case.playbook.version == Decimal(version)
    if earned:
        award = KarmaAward.objects.get(
            event_identity=f"first_release:{case.playbook.pk}"
        )
        assert (
            award.recipient_id,
            award.category,
            award.event_channel,
            award.points,
        ) == (
            case.author.pk,
            "product",
            "release",
            5000,
        )


@pytest.mark.django_db
def test_later_major_with_accepted_pip_preserves_first_release_award() -> None:
    """Finalize Maria's reviewed change as Mike without re-awarding Nora.

    :return: None. Example: accepted PIP/v2.0 and original 5,000 award intact.
    :raises AssertionError: If actual changes, receipts or immutable history differ.
    """
    case = build_nora_release_case()
    PlaybookService.update_playbook(case.playbook.pk, visibility="public")
    _publish(case, "1.0", earned=True)
    original = capture_release_history(case.playbook)
    pip = prepare_reviewed_next_major_pip(
        case.playbook, User.objects.get(username="mrodriguez")
    )
    _finalize_reviewed_pip(pip)
    assert_release_history_preserved(
        case.playbook, original, version="2.0", recipient_total=5000
    )


@pytest.mark.django_db
def test_later_major_with_normal_releases_preserves_single_award() -> None:
    """Publish three normal major versions while retaining the first receipt.

    :return: None. Example: v1.0/v2.0/v3.0, one 5,000 award and no later earned alert.
    :raises AssertionError: If versions, messages or persisted event fields differ.
    """
    case = build_nora_release_case()
    _publish(case, "1.0", earned=True)
    original = capture_release_history(case.playbook)
    for version in ("2.0", "3.0"):
        _publish(case, version)
        assert_release_history_preserved(
            case.playbook, original, version=version, recipient_total=5000
        )
    assert list(
        case.playbook.versions.filter(source=VersionSource.RELEASE)
        .order_by("version_number")
        .values_list("version_number", flat=True)
    ) == [Decimal("1.0"), Decimal("2.0"), Decimal("3.0")]


@pytest.mark.django_db
def test_later_major_with_staff_revert_and_release_preserves_single_award() -> None:
    """Revert with Mike, edit the draft, and publish normally as Nora.

    :return: None. Example: v1.0 retained on revert, v1.1 edit, v2.0 publication.
    :raises AssertionError: If legitimate version transitions or original history differ.
    """
    case = build_nora_release_case()
    _publish(case, "1.0", earned=True)
    original = capture_release_history(case.playbook)
    PlaybookService.revert_released_playbook_to_draft(
        case.playbook.pk,
        actor=User.objects.get(username="mchen"),
        reason="Review workshop guidance",
    )
    case.playbook.refresh_from_db()
    assert case.playbook.status == "draft" and case.playbook.version == Decimal("1.0")
    Activity.objects.create(
        workflow=case.playbook.workflows.get(),
        name="Confirm access needs",
        guidance="Ask participants about accessible workshop requirements.",
        order=1,
    )
    case.playbook.refresh_from_db()
    assert case.playbook.version == Decimal("1.1")
    _publish(case, "2.0")
    assert_release_history_preserved(
        case.playbook, original, version="2.0", recipient_total=5000
    )


@pytest.mark.django_db
def test_later_major_with_imported_release_marker_preserves_history() -> None:
    """Publish the imported historical playbook without minting a live award.

    :return: None. Example: Mike's canonical historical event and 12,450 persist.
    :raises AssertionError: If historical timestamp, recipient or history changes.
    """
    dataset = load_cedar_baseline()
    playbook = dataset.playbooks_by_pk[6201]
    mike = dataset.users_by_username["mchen"]
    original = capture_release_history(playbook)
    award = KarmaAward.objects.get(event_identity="first_release:6201")
    assert award.event_channel == "historical" and award.recipient_id == mike.pk
    client = Client()
    client.force_login(mike)
    _publish(NoraReleaseCase(mike, playbook, client), "3.0")
    assert_release_history_preserved(
        playbook, original, version="3.0", recipient_total=12450
    )
    assert not KarmaAward.objects.filter(
        playbook_id_snapshot=6201, event_channel="release"
    ).exists()


@pytest.mark.django_db
def test_later_major_with_changed_author_preserves_original_recipient() -> None:
    """Reassign authorship as explicit adversarial setup after the real award.

    :return: None. Example: Maria publishes v2.0 while Nora keeps her sole 5,000.
    :raises AssertionError: If author identity changes the first-release event.
    """
    case = build_nora_release_case()
    _publish(case, "1.0", earned=True)
    original = capture_release_history(case.playbook)
    maria = User.objects.get(username="mrodriguez")
    maria_awards = tuple(
        KarmaAward.objects.filter(recipient=maria).order_by("pk").values_list()
    )
    Playbook.objects.filter(pk=case.playbook.pk).update(author=maria)
    case.playbook.refresh_from_db()
    case.client.force_login(maria)
    _publish(NoraReleaseCase(maria, case.playbook, case.client), "2.0")
    assert case.playbook.author_id == maria.pk
    assert_release_history_preserved(
        case.playbook, original, version="2.0", recipient_total=5000
    )
    assert (
        tuple(KarmaAward.objects.filter(recipient=maria).order_by("pk").values_list())
        == maria_awards
    )


@pytest.mark.django_db
def test_later_major_with_denied_operations_preserves_version_and_award() -> None:
    """Reject wrong owner, nonstaff revert, and staff revert without a reason.

    :return: None. Example: v1.0/released with identical complete history and award.
    :raises AssertionError: If denied actions mutate any persisted release state.
    """
    case = build_nora_release_case()
    _publish(case, "1.0", earned=True)
    original = capture_release_history(case.playbook)
    before = Playbook.objects.values().get(pk=case.playbook.pk)
    for error, operation in _denied_operations(case):
        with pytest.raises(error):
            operation()
        assert Playbook.objects.values().get(pk=case.playbook.pk) == before
        assert_release_history_preserved(
            case.playbook, original, version="1.0", recipient_total=5000
        )
        assert capture_release_history(case.playbook) == original


def _finalize_reviewed_pip(pip: ProcessImprovementProposal) -> None:
    """Use the real administrator POST and verify applied Activity and PIP receipt.

    :param pip: One-change reviewed proposal. Example: Maria ADD Activity.
    :return: None. Example: real Mike POST applies v2.0/PIP receipt.
    :raises AssertionError: If the real domain or log contract differs.
    """
    change = pip.changes.get()
    staff = Client()
    staff.force_login(User.objects.get(username="mchen"))
    response = staff.post(
        reverse("pip_admin_review", kwargs={"pk": pip.pk}),
        {
            "action": "finalize",
            f"decision_{change.pk}": "ACCEPT",
            f"note_{change.pk}": "Reviewed workshop step",
        },
    )
    assert response.status_code == 302
    pip.refresh_from_db()
    assert pip.status == pip.STATUS_ACCEPTED and pip.decided_at is not None
    change.refresh_from_db()
    assert change.admin_decision == "ACCEPT"
    assert Activity.objects.filter(
        workflow=change.parent_workflow,
        name=change.name,
        guidance=change.content,
    ).exists()
    receipt = PlaybookVersion.objects.get(
        playbook=pip.playbook, version_number=Decimal("2.0")
    )
    assert receipt.source == VersionSource.PIP_SOURCE and receipt.pip_id == pip.pk
    assert receipt.created_by_id == User.objects.get(username="mchen").pk


def _denied_operations(
    case: NoraReleaseCase,
) -> tuple[tuple[type[Exception], Callable[[], object]], ...]:
    """Describe the three real forbidden lifecycle calls without executing them.

    :param case: Published Nora target. Example: playbook 6302 at v1.0.
    :return: Forbidden exception/call pairs. Example: PermissionError and wrong-owner release.
    :raises AssertionError: If the real domain or log contract differs.
    """
    return (
        (
            PermissionError,
            lambda: PlaybookService.release_playbook(
                case.playbook.pk,
                User.objects.get(username="mrodriguez"),
                description=NOTES,
            ),
        ),
        (
            PermissionError,
            lambda: PlaybookService.revert_released_playbook_to_draft(
                case.playbook.pk, actor=case.author, reason=NOTES
            ),
        ),
        (
            ValidationError,
            lambda: PlaybookService.revert_released_playbook_to_draft(
                case.playbook.pk, actor=User.objects.get(username="mchen"), reason=" "
            ),
        ),
    )
