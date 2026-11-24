from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
from django.test import Client

from methodology.models import KarmaAward
from methodology.services.experts_service import ExpertsService
from tests.support.experts_data import CedarDataset
from tests.support.experts_logs import capture_experts_logs
from tests.support.experts_summary_stability import (
    assert_live_displays,
    capture_summary_state,
    post_authorized_copy,
)
from tests.support.log_story import assert_log_story

_LOGGERS = (
    "methodology.karma_views",
    "methodology.services.karma_service",
    "accounts.views",
    "methodology.services.contribution_summary_service",
    "methodology.services.contribution_summary_boundary",
)


@pytest.mark.django_db(transaction=True)
def test_s28_copy_receipt_with_stored_summary_updates_only_live_numbers(
    cedar_dataset: CedarDataset,
) -> None:
    """Prove the real receipt adds exactly the eligible pair, preserving prose.

    :param cedar_dataset: Owned real baseline. Example: CEDAR-RFP-01.
    :return: None. Example: Maria 8205, Mike 12455, identical summary state.
    :raises AssertionError: For wrong attribution, extra rows or changed metadata.
    """
    cedar = cedar_dataset
    client = _maria_client(cedar)
    maria, mike = (cedar.users_by_username[name] for name in ("mrodriguez", "mchen"))
    before = capture_summary_state(maria.pk)
    ledger = tuple(KarmaAward.objects.order_by("pk").values())
    action = post_authorized_copy(client, cedar)
    _assert_award_pair(ledger, maria.pk, mike.pk, action)
    assert capture_summary_state(maria.pk) == before


@pytest.mark.django_db(transaction=True)
def test_s28_display_with_completed_copy_reads_live_totals_and_stored_prose(
    cedar_dataset: CedarDataset,
) -> None:
    """Prove real surfaces read updated projections without changing prose.

    :param cedar_dataset: Owned real baseline. Example: CEDAR-RFP-01.
    :return: None. Example: own/list/detail show 8,205 and Design.
    :raises AssertionError: For stale display, changed text or GET side effects.
    """
    client = _maria_client(cedar_dataset)
    maria = cedar_dataset.users_by_username["mrodriguez"]
    before = capture_summary_state(maria.pk)
    post_authorized_copy(client, cedar_dataset)
    awards = tuple(KarmaAward.objects.order_by("pk").values())
    for _ in range(3):
        assert_live_displays(client, cedar_dataset)
        assert tuple(KarmaAward.objects.order_by("pk").values()) == awards
        assert capture_summary_state(maria.pk) == before


@pytest.mark.django_db(transaction=True)
def test_s28_copy_log_story_happy(
    caplog: pytest.LogCaptureFixture,
    cedar_dataset: CedarDataset,
) -> None:
    """Assert E's existing receipt/projection beats after clearing baseline logs.

    :param caplog: INFO capture. Example: receipt and profile records.
    :param cedar_dataset: Owned real baseline. Example: CEDAR-RFP-01.
    :return: None. Example: complete copy story and no generation entry.
    :raises AssertionError: For missing beats, extra generation or leaked bodies.
    """
    client = _maria_client(cedar_dataset)
    caplog.clear()
    with capture_experts_logs(caplog, _LOGGERS):
        action = post_authorized_copy(client, cedar_dataset)
        assert_live_displays(client, cedar_dataset)
    maria = cedar_dataset.users_by_username["mrodriguez"]
    mike = cedar_dataset.users_by_username["mchen"]
    _assert_receipt_logs(caplog, maria.pk, action)
    _assert_consumption_logs(caplog, maria.pk, mike.pk, action)
    _assert_profile_logs(caplog, maria.pk)
    assert "ContributionSummaryService.refresh_for_submission" not in caplog.text
    assert "PublicContributionSummaryBoundary.complete" not in caplog.text
    assert not any(user.email and user.email in caplog.text for user in (maria, mike))
    assert (
        capture_summary_state(maria.pk).profile_values["contribution_summary"]
        not in caplog.text
    )


def _maria_client(cedar: CedarDataset) -> Client:
    """Authenticate the real strict-CSRF client before observing receipt effects.

    :param cedar: Loaded test baseline. Example: CEDAR-RFP-01.
    :return: Warm authenticated client. Example: Maria's strict session.
    :raises AssertionError: If own-profile setup fails.
    """
    client = Client(enforce_csrf_checks=True)
    client.force_login(cedar.users_by_username["mrodriguez"])
    assert client.get("/auth/user/profile/").status_code == 200
    return client


def _assert_award_pair(
    ledger: tuple[Mapping[str, Any], ...], maria_id: int, mike_id: int, action: str
) -> None:
    """Check exact new pair and unchanged historical rows from the real receipt.

    :param ledger: Complete baseline award rows. Example: 2129 immutable rows.
    :param maria_id: Actual recipient key. Example: Maria PK3.
    :param mike_id: Actual author key. Example: Mike PK8.
    :param action: Real receipt UUID. Example: newUUID4.
    :return: None. Example: two new Development GUI awards and no other mutation.
    :raises AssertionError: For wrong attribution, totals or historical changes.
    """
    added = KarmaAward.objects.exclude(pk__in=[row["id"] for row in ledger])
    assert set(added.values_list("recipient_id", "source_kind", "points")) == {
        (maria_id, "learning", 5),
        (mike_id, "consumption", 5),
    }
    assert set(
        added.values_list(
            "category", "event_channel", "entity_type_snapshot", "entity_id_snapshot"
        )
    ) == {("development", "gui_copy", "activity", 6203)}
    assert set(added.values_list("event_identity", flat=True)) == {
        f"consumption:gui_copy:{maria_id}:{action}"
    }
    _assert_history_preserved(ledger)
    assert KarmaAward.objects.count() == len(ledger) + 2
    assert (
        ExpertsService().project_user(maria_id).total_points,
        ExpertsService().project_user(mike_id).total_points,
    ) == (8205, 12455)


def _assert_receipt_logs(
    caplog: pytest.LogCaptureFixture, maria_id: int, action: str
) -> None:
    """Actual receipt entry, validation and applied exit.

    :param caplog: Real INFO capture. Example: cleared receipt/display window.
    :param maria_id: Actual Maria key. Example: 3.
    :param action: Real action UUID. Example: newUUID4.
    :return: None. Example: every declared beat present.
    :raises AssertionError: If a beat or safe identifier is missing.
    """
    assert_log_story(
        caplog,
        where="copy_success_receipt",
        beats={
            "entry": (
                "| entry |",
                f"actor_id={maria_id}",
                "request_id=s28-copy-receipt",
            ),
            "validation": ("| validation |", f"action_uuid={action}", "entity_id=6203"),
            "exit": ("| exit |", "status=applied", f"action_uuid={action}"),
        },
    )


def _assert_consumption_logs(
    caplog: pytest.LogCaptureFixture, maria_id: int, mike_id: int, action: str
) -> None:
    """Actual atomic consumption pair persistence and exit.

    :param caplog: Real INFO capture. Example: cleared receipt/display window.
    :param maria_id: Actual Maria key. Example: 3.
    :param mike_id: Actual author key. Example: 8.
    :param action: Real action UUID. Example: newUUID4.
    :return: None. Example: every declared beat present.
    :raises AssertionError: If a beat or safe identifier is missing.
    """
    assert_log_story(
        caplog,
        where="KarmaService.award_successful_consumption",
        beats={
            "processing": (
                "| processing |",
                f"learner_id={maria_id}",
                f"author_id={mike_id}",
                "points=5",
                "status=staged",
            ),
            "exit": (
                "| exit |",
                "created_count=2",
                f"event_identity=consumption:gui_copy:{maria_id}:{action}",
            ),
        },
    )


def _assert_profile_logs(caplog: pytest.LogCaptureFixture, maria_id: int) -> None:
    """Actual stored-prose profile branch and live projection exit.

    :param caplog: Real INFO capture. Example: cleared receipt/display window.
    :param maria_id: Actual Maria key. Example: 3.
    :return: None. Example: every declared beat present.
    :raises AssertionError: If a beat or safe identifier is missing.
    """
    assert_log_story(
        caplog,
        where="accounts.views._profile_contribution_context",
        beats={
            "branch": (
                "beat=branch",
                "summary_state=stored",
                f"subject_user_id={maria_id}",
                "request_id=s28-live-displays",
            ),
            "exit": (
                "beat=exit",
                "total_points=8205",
                "primary_category=Design",
                "source_count=4",
            ),
        },
    )


def _assert_history_preserved(ledger: tuple[Mapping[str, Any], ...]) -> None:
    """Require every preexisting award column to survive the copy unchanged.

    :param ledger: Complete original rows. Example: 2129 baseline records.
    :return: None. Example: equal original IDs, timestamps and values.
    :raises AssertionError: For altered or deleted history.
    """
    assert (
        tuple(
            KarmaAward.objects.filter(pk__in=[row["id"] for row in ledger])
            .order_by("pk")
            .values()
        )
        == ledger
    )
