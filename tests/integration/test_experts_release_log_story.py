"""Captured log stories for real first-release service and view paths."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from methodology.models import KarmaAward, PlaybookVersion, VersionSource
from methodology.services.karma_service import KarmaService
from methodology.services.playbook_service import PlaybookService
from tests.support.experts_logs import capture_experts_logs
from tests.support.experts_release import build_nora_release_case
from tests.support.log_story import assert_log_story

PLAYBOOK_LOGGER = "methodology.services.playbook_service"
KARMA_LOGGER = "methodology.services.karma_service"
VIEW_LOGGER = "methodology.playbook_views"
RELEASE_METHOD = "PlaybookService.release_playbook_with_award"
AWARD_METHOD = "KarmaService.award_first_release"
RELEASE_NOTES = "Private milestone narrative"


@pytest.mark.django_db
def test_karma_release_log_story_happy(caplog: pytest.LogCaptureFixture) -> None:
    """Prove publication and ledger staging with traceable, safe context.

    :param caplog: Real pytest log capture. Example: INFO capture for release-01.
    :return: None when assert_log_story verifies every happy-path row.
    :raises AssertionError: If a required beat/context is absent or sensitive text leaks.
    """
    case = build_nora_release_case()
    caplog.clear()
    with capture_experts_logs(caplog, (PLAYBOOK_LOGGER, KARMA_LOGGER)):
        first = PlaybookService.release_playbook_with_award(
            case.playbook.pk,
            case.author,
            description=RELEASE_NOTES,
            correlation_id="release-01",
        )
        later = PlaybookService.release_playbook_with_award(
            case.playbook.pk,
            case.author,
            description=RELEASE_NOTES,
            correlation_id="release-02",
        )

    correlation = "correlation_id=release-01"
    playbook = f"playbook_id={case.playbook.pk}"
    assert_log_story(
        caplog,
        where=RELEASE_METHOD,
        beats={
            "entry": ("| entry |", playbook, f"actor_id={case.author.pk}", correlation),
            "validation": (
                "| validation |",
                "owner_valid=true",
                "workflow_present=true",
                "first_publication=true",
                correlation,
            ),
            "processing": (
                "| processing |",
                "version=1.0",
                "award_points=5000",
                "transaction=pending",
                correlation,
            ),
            "branch": (
                "| branch |",
                "reason=previously_released",
                "award_points=0",
                "correlation_id=release-02",
            ),
        },
    )
    assert_log_story(
        caplog,
        where="KarmaService.persist_awards",
        beats={
            "entry": ("| entry |", "award_count=1", correlation),
        },
    )
    assert_log_story(
        caplog,
        where=AWARD_METHOD,
        beats={
            "config": ("| config |", "source_kind=release", "points=5000", correlation),
            "exit": (
                "| exit |",
                f"recipient_id={case.author.pk}",
                "category=product",
                "created=true",
                "points=5000",
                "transaction=pending",
                correlation,
            ),
        },
    )
    assert first.first_release_award.created
    assert not later.first_release_award.created
    assert KarmaAward.objects.filter(recipient=case.author).count() == 1
    assert RELEASE_NOTES not in caplog.text
    assert case.playbook.name not in caplog.text
    assert case.author.email not in caplog.text
    assert case.author.username not in caplog.text


@pytest.mark.django_db
def test_release_view_log_story_reports_first_and_later_message_outcomes(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Trace the earnings alert decisions from real release POST requests.

    :param caplog: Real log capture. Example: INFO for cedar-first-release.
    :return: None when the view traces both decisions and their request IDs.
    :raises AssertionError: If an exit beat is missing or private text leaks.
    """
    case = build_nora_release_case()
    url = reverse("playbook_release", kwargs={"pk": case.playbook.pk})
    payload = {"release_description": RELEASE_NOTES}
    caplog.clear()
    with capture_experts_logs(caplog, (VIEW_LOGGER, PLAYBOOK_LOGGER)):
        first = case.client.post(url, payload, headers={"X-Request-ID": "cedar-first"})
        later = case.client.post(url, payload, headers={"X-Request-ID": "cedar-later"})

    assert first.status_code == later.status_code == 302
    playbook = f"playbook_id={case.playbook.pk}"
    assert_log_story(
        caplog,
        where="_release_with_karma_message",
        beats={
            "first": (
                "| exit |",
                playbook,
                "earned_message=true",
                "correlation_id=cedar-first",
            ),
            "later": (
                "| exit |",
                playbook,
                "earned_message=false",
                "correlation_id=cedar-later",
            ),
        },
    )
    assert_log_story(
        caplog,
        where=RELEASE_METHOD,
        beats={"entry": ("| entry |", playbook, "correlation_id=cedar-first")},
    )
    release_logs = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name in (VIEW_LOGGER, PLAYBOOK_LOGGER)
    )
    for private_text in (
        RELEASE_NOTES,
        case.playbook.name,
        case.author.username,
        case.author.email,
    ):
        assert private_text not in release_logs


@pytest.mark.django_db
def test_karma_release_log_story_reject(caplog: pytest.LogCaptureFixture) -> None:
    """Prove rejection logs a safe reason without award-success records.

    :param caplog: Real pytest log capture. Example: empty-description release.
    :return: None when the rejection story and unchanged ledger agree.
    :raises AssertionError: If a reason is missing or rejected work earns points.
    """
    case = build_nora_release_case()
    with (
        capture_experts_logs(caplog, (PLAYBOOK_LOGGER, KARMA_LOGGER)),
        pytest.raises(ValidationError, match="Release description is required"),
    ):
        PlaybookService.release_playbook_with_award(
            case.playbook.pk,
            case.author,
            description=" ",
            correlation_id="release-rejected",
        )
    assert_log_story(
        caplog,
        where=RELEASE_METHOD,
        beats={
            "error": (
                "| error |",
                "reason=release_description_required",
                f"playbook_id={case.playbook.pk}",
                "correlation_id=release-rejected",
            ),
        },
    )
    assert "KarmaService.persist_awards" not in caplog.text
    assert "KarmaService.award_first_release" not in caplog.text
    assert not KarmaAward.objects.filter(recipient=case.author).exists()
    assert not PlaybookVersion.objects.filter(
        playbook=case.playbook, source=VersionSource.RELEASE
    ).exists()


@pytest.mark.django_db
def test_karma_release_log_story_duplicate(caplog: pytest.LogCaptureFixture) -> None:
    """Prove a stable receipt replay identifies zero additional points.

    :param caplog: Real pytest log capture. Example: replay first_release:6302.
    :return: None when duplicate branch, row identity and totals agree.
    :raises AssertionError: If duplicate processing is hidden or awards again.
    """
    case = build_nora_release_case()
    release = PlaybookService.release_playbook_with_award(
        case.playbook.pk,
        case.author,
        description=RELEASE_NOTES,
        correlation_id="release-01",
    )
    receipt = PlaybookVersion.objects.get(
        playbook=case.playbook, source=VersionSource.RELEASE
    )
    with capture_experts_logs(caplog, (KARMA_LOGGER,)):
        replay = KarmaService.award_first_release(
            release.playbook,
            receipt,
            case.author,
            correlation_id="release-replay",
        )
    assert_log_story(
        caplog,
        where=AWARD_METHOD,
        beats={
            "branch": (
                "| branch |",
                f"event_identity=first_release:{case.playbook.pk}",
                "created=false",
                "additional_points=0",
                "correlation_id=release-replay",
            ),
        },
    )
    assert replay.award == release.first_release_award.award
    assert not replay.created
    assert KarmaAward.objects.filter(recipient=case.author).count() == 1
