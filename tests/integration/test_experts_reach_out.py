"""S14 real database, rendered response and captured log contracts."""

from __future__ import annotations

from html import unescape

import pytest
from django.core.mail import EmailMessage
from django.db import connection
from django.test import Client
from django.test.html import parse_html
from django.test.utils import CaptureQueriesContext
from pytest import LogCaptureFixture

from methodology.services.expert_contact_context import build_expert_contact_context
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
from tests.support.experts_html import element_text, find_by_test_id
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

pytestmark = pytest.mark.django_db

_CONTACT_LOGGER = "methodology.services.expert_contact_context"
_CONTACT_OPERATION = "build_expert_contact_context"
_DETAIL_PATH = "/experts/mrodriguez/"
_LIST_PATH = "/experts/"
_MARIA_CARD = "experts-card-mrodriguez"
_MAILTO = "mailto:maria.rodriguez@example.com"
_DISCUSSION = "Start an email discussion with Maria Rodriguez"
_DESCRIPTION_ID = "reach-explanation-mrodriguez"
_SIGN_IN = "You need to be logged in to reach out to the expert"
_UNAVAILABLE = "Contact information is unavailable"


def test_reach_out_with_authenticated_elena_matches_both_surfaces(
    client: Client, cedar_dataset: CedarDataset, mailoutbox: list[EmailMessage]
) -> None:
    """Prove the exact mailto and nonblocking discussion hint on both surfaces.

    :param client: Real Django client. Example: logged-in Cedar Elena.
    :param cedar_dataset: Real account rows. Example: Elena and Maria.
    :param mailoutbox: Django's captured mail. Example: an empty list.
    :return: None. Example: two exact destinations, no outbox growth.
    :raises AssertionError: For incorrect actions, availability claims or mail.
    """
    assert client.login(username="esvensson", password=CEDAR_PASSWORD)
    initial_mail_count = len(mailoutbox)
    listing = client.get(_LIST_PATH, {"category": "design"})
    detail = client.get(_DETAIL_PATH)
    assert listing.status_code == detail.status_code == 200

    card = find_by_test_id(listing.content, _MARIA_CARD)
    description = parse_html(
        f'<span id="{_DESCRIPTION_ID}" hidden>{_DISCUSSION}</span>'
    )
    for surface in (str(card), detail.content.decode()):
        action = find_by_test_id(surface, "experts-reach-out-mrodriguez")
        assert action.name == "a"
        assert element_text(action) == "Reach out"
        attributes = dict(action.attributes)
        assert attributes["href"] == _MAILTO
        assert attributes["title"] == _DISCUSSION
        assert attributes.get("data-bs-toggle") != "tooltip"
        assert attributes["aria-describedby"] == _DESCRIPTION_ID
        assert parse_html(surface).count(description) == 1
    assert len(mailoutbox) == initial_mail_count


def test_reach_out_with_guest_request_excludes_email_on_both_surfaces(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove response and contact-context privacy for both public routes.

    :param client: Real anonymous client. Example: Cedar Bob.
    :param cedar_dataset: Real public and private accounts. Example: Maria.
    :return: None. Example: disabled action and public content without email.
    :raises AssertionError: For address leakage, href leakage or blocked browsing.
    """
    listing = client.get(_LIST_PATH, {"category": "design"})
    detail = client.get(_DETAIL_PATH)
    assert listing.status_code == detail.status_code == 200

    for response in (listing, detail):
        document = unescape(response.content.decode()).lower()
        context = repr(response.context).lower()
        for rendered in (document, context):
            assert "mailto:" not in rendered
            assert all(
                account.email.lower() not in rendered
                for account in cedar_dataset.users_by_username.values()
                if account.email
            )

    card = find_by_test_id(listing.content, _MARIA_CARD)
    find_by_test_id(str(card), "experts-view-profile-mrodriguez")
    assert element_text(find_by_test_id(detail.content, "expert-name")) == (
        "Maria Rodriguez"
    )
    find_by_test_id(detail.content, "expert-contribution-summary")
    find_by_test_id(detail.content, "expert-public-playbooks")

    for surface in (str(card), detail.content):
        _assert_disabled_contact(surface, "guest", _SIGN_IN)


def test_reach_out_with_authenticated_unusable_email_renders_disabled_action(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove unavailable target contact degrades safely on both surfaces.

    :param client: Real Django client. Example: Elena viewing missing-email Maria.
    :param cedar_dataset: Real account rows. Example: Maria's stored address.
    :return: None. Example: HTTP 200 with neutral disabled contact.
    :raises AssertionError: For malformed destinations, a 500 or false success.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    maria.email = "maria.rodriguez@example.com?bcc=extra@example.com"
    maria.save(update_fields=["email"])
    assert client.login(username="esvensson", password=CEDAR_PASSWORD)
    listing = client.get(_LIST_PATH, {"category": "design"})
    detail = client.get(_DETAIL_PATH)
    assert listing.status_code == detail.status_code == 200

    card = find_by_test_id(listing.content, _MARIA_CARD)
    for surface in (str(card), detail.content.decode()):
        document = unescape(surface)
        assert "mailto:" not in document
        assert maria.email not in document
        assert _SIGN_IN not in document
        _assert_disabled_contact(surface, "unavailable", _UNAVAILABLE)


def _assert_disabled_contact(
    surface: str | bytes, state_hook: str, explanation: str
) -> None:
    """Assert the shared initial HTML of Maria's restricted contact control.

    :param surface: Scoped actual HTML. Example: Maria's card.
    :param state_hook: Stable selector fragment. Example: "guest".
    :param explanation: Expected accessible explanation. Example: _SIGN_IN.
    :return: None after verifying the focus wrapper, button and description.
    :raises AssertionError: For an enabled or inaccessible contact control.
    """
    wrapper = find_by_test_id(surface, f"experts-reach-out-{state_hook}-tooltip")
    attributes = dict(wrapper.attributes)
    assert attributes["tabindex"] == "0"
    assert attributes["data-bs-toggle"] == "tooltip"
    assert attributes["data-bs-placement"] == "bottom"
    assert set(attributes.get("data-bs-trigger", "hover focus").split()) == {
        "hover",
        "focus",
    }
    assert attributes["title"] == explanation
    assert attributes["aria-describedby"] == "reach-explanation-mrodriguez"
    assert any(
        ("id", attributes["aria-describedby"]) in child.attributes
        and element_text(child) == explanation
        for child in wrapper.children
        if not isinstance(child, str)
    )
    button = find_by_test_id(str(wrapper), "experts-reach-out-disabled-mrodriguez")
    assert button.name == "button"
    assert "disabled" in dict(button.attributes)
    assert dict(button.attributes)["aria-label"] == "Reach out to Maria Rodriguez"
    assert element_text(button) == "Reach out"


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
