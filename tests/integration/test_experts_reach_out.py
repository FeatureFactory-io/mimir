"""S14 real database, rendered response and captured log contracts."""

from __future__ import annotations

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from pytest import LogCaptureFixture

from methodology.services.expert_contact_context import build_expert_contact_context
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

pytestmark = pytest.mark.django_db

_CONTACT_LOGGER = "methodology.services.expert_contact_context"
_CONTACT_OPERATION = "build_expert_contact_context"
_DETAIL_PATH = "/experts/mrodriguez/"
_LIST_PATH = "/experts/"
_MAILTO = "mailto:maria.rodriguez@example.com"


def test_reach_out_with_authenticated_elena_matches_both_surfaces(
    client: Client,
) -> None:
    """Prove Maria's exact mailto on real list/detail without sending.

    :param client: Real Django client. Example: logged-in Cedar Elena.
    :return: None. Example: two exact destinations, no outbox growth.
    :raises AssertionError: For incorrect actions, availability claims or mail.
    """
    raise NotImplementedError()


def test_reach_out_with_guest_request_excludes_email_on_both_surfaces(
    client: Client,
) -> None:
    """Prove response and contact-context privacy for both public routes.

    :param client: Real anonymous client. Example: Cedar Bob.
    :return: None. Example: disabled action and public content without email.
    :raises AssertionError: For address leakage, href leakage or blocked browsing.
    """
    raise NotImplementedError()


def test_reach_out_with_authenticated_unusable_email_renders_disabled_action(
    client: Client,
) -> None:
    """Prove unavailable target contact degrades safely on both surfaces.

    :param client: Real Django client. Example: Elena viewing missing-email Maria.
    :return: None. Example: HTTP 200 with neutral disabled contact.
    :raises AssertionError: For malformed destinations, a 500 or false success.
    """
    raise NotImplementedError()


def test_reach_out_log_story_happy(
    client: Client, cedar_dataset: CedarDataset, caplog: LogCaptureFixture
) -> None:
    """Assert successful contact-boundary beats with the shared story helper.

    :param client: Real Django client. Example: authenticated Elena.
    :param cedar_dataset: Fixture with real account rows. Example: Maria and Elena.
    :param caplog: Pytest capture fixture. Example: INFO contact records.
    :return: None. Example: entry, processing and exit proved without email.
    :raises AssertionError: For missing beats or sensitive log content.
    """
    assert client.login(username="esvensson", password=CEDAR_PASSWORD)
    headers = {"X-Request-ID": "cedar-s14-happy"}
    with capture_experts_logs(caplog, (_CONTACT_LOGGER,)):
        listing = client.get(_LIST_PATH, {"category": "design"}, headers=headers)
        detail = client.get(_DETAIL_PATH, headers=headers)
    assert listing.status_code == detail.status_code == 200
    maria = next(
        row for row in listing.context["people"] if row["username"] == "mrodriguez"
    )
    assert (
        maria["contact"].href
        == detail.context["contact_person"]["contact"].href
        == _MAILTO
    )
    assert "contact" not in detail.context["person"]
    assert "email" not in maria and "email" not in detail.context["person"]

    actor = cedar_dataset.users_by_username["esvensson"]
    correlation = "correlation_id=cedar-s14-happy"
    assert_log_story(
        caplog,
        where=_CONTACT_OPERATION,
        beats={
            "entry": (
                "| entry |",
                f"actor_id={actor.pk}",
                "target_count=1",
                correlation,
            ),
            "processing": (
                "| processing |",
                "email_lookup=true",
                "target_count=1",
                correlation,
            ),
            "exit": ("| exit |", "available_count=1", "disabled_count=0", correlation),
        },
    )
    assert actor.email not in caplog.text
    assert cedar_dataset.users_by_username["mrodriguez"].email not in caplog.text
    assert "mailto:" not in caplog.text


def test_reach_out_log_story_reject(
    client: Client, cedar_dataset: CedarDataset, caplog: LogCaptureFixture
) -> None:
    """Assert guest, unavailable-mailbox and invalid-input decisions safely.

    :param client: Real Django client. Example: anonymous then authenticated GETs.
    :param cedar_dataset: Fixture with real account rows. Example: Maria and Elena.
    :param caplog: Pytest capture fixture. Example: INFO/WARNING boundary records.
    :return: None. Example: rejection reasons and exit counts proved.
    :raises AssertionError: For missing branches, lookup leakage or logged email.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    invalid_email = "maria.rodriguez@example.com?bcc=extra@example.com"
    maria.email = invalid_email
    maria.save(update_fields=["email"])
    with capture_experts_logs(caplog, (_CONTACT_LOGGER,)):
        with CaptureQueriesContext(connection) as guest_queries:
            guest = client.get(
                _DETAIL_PATH,
                {"guest": "0"},
                headers={"X-Request-ID": "cedar-s14-guest"},
            )
        assert client.login(username="esvensson", password=CEDAR_PASSWORD)
        unavailable = client.get(
            _DETAIL_PATH, headers={"X-Request-ID": "cedar-s14-unavailable"}
        )
        with pytest.raises(ValueError, match="username"):
            build_expert_contact_context(
                unavailable.wsgi_request, ["extra@example.com?bcc=1"]
            )

    assert guest.status_code == unavailable.status_code == 200
    assert all('"auth_user"."email"' not in query["sql"] for query in guest_queries)
    assert guest.context["contact_person"]["contact"].state == "authentication_required"
    assert unavailable.context["contact_person"]["contact"].state == "unavailable"
    assert_log_story(
        caplog,
        where=_CONTACT_OPERATION,
        beats={
            "guest": (
                "| branch |",
                "reason=authentication_required",
                "email_lookup=false",
                "correlation_id=cedar-s14-guest",
            ),
            "unavailable": (
                "| branch |",
                "reason=contact_unavailable",
                "unavailable_count=1",
                "correlation_id=cedar-s14-unavailable",
            ),
            "exit": (
                "| exit |",
                "available_count=0",
                "disabled_count=1",
                "correlation_id=cedar-s14-unavailable",
            ),
        },
    )
    assert_log_story(
        caplog,
        where=_CONTACT_OPERATION,
        level="WARNING",
        beats={
            "validation": (
                "| validation |",
                "reason=invalid_input",
                "field=expert_usernames",
                "correlation_id=cedar-s14-unavailable",
            )
        },
    )
    assert "mailto:" not in caplog.text
    assert "example.com" not in caplog.text
    assert "email_lookup=true" not in "\n".join(
        record.getMessage()
        for record in caplog.records
        if "cedar-s14-guest" in record.getMessage()
    )
