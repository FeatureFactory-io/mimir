"""Actual correlated publication logs agree with persisted later-release outcomes."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.urls import reverse

from methodology.models import Playbook
from methodology.services.playbook_service import PlaybookService
from tests.support.experts_logs import capture_experts_logs
from tests.support.experts_release import (
    NoraReleaseCase,
    assert_release_history_preserved,
    build_nora_release_case,
    capture_release_history,
)
from tests.support.log_story import assert_log_story

PLAYBOOK_LOGGER = "methodology.services.playbook_service"
KARMA_LOGGER = "methodology.services.karma_service"
VIEW_LOGGER = "methodology.playbook_views"
RELEASE_METHOD = "PlaybookService.release_playbook_with_award"
PRIVATE_NOTES = "Private later workshop delivery narrative"


@pytest.mark.django_db
def test_karma_later_release_log_story_happy(caplog: pytest.LogCaptureFixture) -> None:
    """Capture only the second real POST, including its earnings-alert decision.

    :param caplog: Actual captured logger records. Example: later-release-02.
    :return: None. Example: correlated zero-points branch with identical original award.
    :raises AssertionError: If required actual beats, privacy or domain outcomes differ.
    """
    case = _published_case()
    original = capture_release_history(case.playbook)
    caplog.clear()
    with capture_experts_logs(caplog, (PLAYBOOK_LOGGER, KARMA_LOGGER, VIEW_LOGGER)):
        response = case.client.post(
            reverse("playbook_release", kwargs={"pk": case.playbook.pk}),
            {"release_description": PRIVATE_NOTES},
            headers={"X-Request-ID": "later-release-02"},
        )
    assert response.status_code == 302
    _assert_later_happy_story(caplog, case)
    _assert_safe_logs(caplog, case.playbook, case.author)
    assert_release_history_preserved(
        case.playbook, original, version="2.0", recipient_total=5000
    )


@pytest.mark.django_db
def test_karma_later_release_log_story_reject(caplog: pytest.LogCaptureFixture) -> None:
    """Reject Maria's wrong-owner action with traceable logs and no mutation.

    :param caplog: Actual captured INFO-or-higher records. Example: later-release-denied.
    :return: None. Example: permission rejection and identical v1.0/history/award.
    :raises AssertionError: If rejected work reaches success or changes stored fields.
    """
    case = _published_case()
    original = capture_release_history(case.playbook)
    before = Playbook.objects.values().get(pk=case.playbook.pk)
    maria = get_user_model().objects.get(username="mrodriguez")
    caplog.clear()
    with (
        capture_experts_logs(caplog, (PLAYBOOK_LOGGER, KARMA_LOGGER, VIEW_LOGGER)),
        pytest.raises(PermissionError),
    ):
        PlaybookService.release_playbook_with_award(
            case.playbook.pk,
            maria,
            description=PRIVATE_NOTES,
            correlation_id="later-release-denied",
        )
    trace = (f"playbook_id={case.playbook.pk}", "correlation_id=later-release-denied")
    assert_log_story(
        caplog,
        where=RELEASE_METHOD,
        beats={
            "entry": ("| entry |", f"actor_id={maria.pk}", *trace),
            "error": ("| error |", "reason=PermissionError", *trace),
        },
    )
    _assert_safe_logs(caplog, case.playbook, case.author, rejected=True)
    assert Playbook.objects.values().get(pk=case.playbook.pk) == before
    assert capture_release_history(case.playbook) == original
    assert_release_history_preserved(
        case.playbook, original, version="1.0", recipient_total=5000
    )


def _assert_safe_logs(
    caplog: pytest.LogCaptureFixture,
    playbook: Playbook,
    author: AbstractBaseUser,
    *,
    rejected: bool = False,
) -> None:
    """Require actual ineligible operations never invoke the ledger writer.

    :param caplog: Actual captured records. Example: later-release-02.
    :param playbook: Target whose name must stay private. Example: 6302.
    :param author: Original recipient. Example: Nora.
    :param rejected: Whether publication was denied. Example: True.
    :return: None. Example: no ledger-success or sensitive text records.
    :raises AssertionError: If the real domain or log contract differs.
    """
    if rejected:
        assert (
            "| processing |" not in caplog.text and "earned_message=" not in caplog.text
        )
    for forbidden in (
        "earned_message=true",
        "KarmaService.persist_awards",
        "KarmaService.award_first_release",
        PRIVATE_NOTES,
        playbook.name,
        author.username,
        author.email,
    ):
        assert forbidden not in caplog.text


def _assert_later_happy_story(
    caplog: pytest.LogCaptureFixture, case: NoraReleaseCase
) -> None:
    """Require the declared S30 service and response beats on the same request.

    :param caplog: Actual captured records. Example: later-release-02.
    :param case: Released Nora case. Example: playbook 6302.
    :return: None. Example: correlated branch and view exit are present.
    :raises AssertionError: If the real domain or log contract differs.
    """
    trace = (f"playbook_id={case.playbook.pk}", "correlation_id=later-release-02")
    assert_log_story(
        caplog,
        where=RELEASE_METHOD,
        beats={
            "entry": ("| entry |", f"actor_id={case.author.pk}", *trace),
            "branch": (
                "| branch |",
                "reason=previously_released",
                "award_points=0",
                *trace,
            ),
        },
    )
    assert_log_story(
        caplog,
        where="_release_with_karma_message",
        beats={"exit": ("| exit |", "earned_message=false", *trace)},
    )


def _published_case() -> NoraReleaseCase:
    """Obtain the baseline and earn the first event through the real service.

    :return: Real released case. Example: Nora at v1.0 with live first-release award.
    :raises AssertionError: If the real domain or log contract differs.
    """
    case = build_nora_release_case()
    PlaybookService.release_playbook(
        case.playbook.pk, case.author, description=PRIVATE_NOTES
    )
    return case
