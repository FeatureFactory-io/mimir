"""Shared assertions for the initial production guest contact markup."""

from __future__ import annotations

from html import unescape
from urllib.parse import unquote

from django.http import HttpResponse
from django.test.html import Element
from django.urls import reverse

from tests.support.experts_html import (
    _parse_root,
    _walk_elements,
    element_text,
    find_by_test_id,
)

GUEST_CONTACT_EXPLANATION = "You need to be logged in to reach out to the expert"
_GUEST_WRAPPER = "experts-reach-out-guest-tooltip"
_DISABLED_BUTTON_PREFIX = "experts-reach-out-disabled-"
_INACTIVE_ATTRIBUTES = frozenset({"hidden", "inert"})


def assert_guest_contact_markup(
    response: HttpResponse,
    container_test_id: str | None,
    forbidden_emails: tuple[str, ...],
) -> None:
    """Check an initial guest control and document-wide contact privacy.

    :param response: Actual guest response. Example: Design list HTTP 200.
    :param container_test_id: Card or document scope. Example: "experts-card-mrodriguez"; None for detail.
    :param forbidden_emails: Cedar contact values. Example: the fixture's account emails.
    :return: None when the disabled control and its initial description match.
    :raises AssertionError: For inaccessible, ambiguous or leaked contact markup.
    """
    html = response.content.decode()
    document = unquote(unescape(html)).casefold()
    assert "mailto:" not in document, "Guest HTML contains a mail destination"
    assert not any(
        email.casefold() in document for email in forbidden_emails if email
    ), "Guest HTML contains an account email"
    scope = str(find_by_test_id(html, container_test_id)) if container_test_id else html
    wrapper = find_by_test_id(scope, _GUEST_WRAPPER)
    username = _assert_disabled_button(wrapper)
    if container_test_id is not None:
        assert container_test_id == f"experts-card-{username}"
    assert not any(
        ("data-testid", f"experts-reach-out-{username}") in element.attributes
        for element in _walk_elements(_parse_root(scope))
    ), "Guest markup contains an authenticated contact control"
    _assert_guest_description(wrapper, html, username)


def assert_guest_profile_link(response: HttpResponse, username: str) -> None:
    """Check that the named public profile anchor is available in its card.

    :param response: Actual guest list response. Example: Design list HTTP 200.
    :param username: Contributor username. Example: "mrodriguez".
    :return: None when the anchor is enabled and targets /experts/mrodriguez/.
    :raises AssertionError: For a missing, disabled or incorrect link destination.
    """
    card = find_by_test_id(response.content, f"experts-card-{username}")
    link = find_by_test_id(str(card), f"experts-view-profile-{username}")
    attributes = dict(link.attributes)
    assert link.name == "a" and element_text(link) == "View profile"
    assert attributes.get("aria-label", "View profile") == "View profile"
    assert attributes.get("href") == reverse("expert_detail", args=[username])
    assert attributes.get("href") == f"/experts/{username}/"
    assert _INACTIVE_ATTRIBUTES.isdisjoint(attributes) and "disabled" not in attributes
    assert attributes.get("aria-disabled", "").casefold() != "true"
    assert attributes.get("tabindex", "0") == "0"


def _assert_disabled_button(wrapper: Element) -> str:
    """Check the focusable wrapper and derive its native button's subject.

    :param wrapper: Parsed tooltip wrapper. Example: Maria's card control.
    :return: Username encoded in the button hook. Example: "mrodriguez".
    :raises AssertionError: For a link, focus defect or an operable button.
    """
    attributes = dict(wrapper.attributes)
    assert attributes.get("tabindex") == "0"
    assert _INACTIVE_ATTRIBUTES.isdisjoint(attributes)
    assert attributes.get("data-bs-toggle") == "tooltip"
    assert set(attributes.get("data-bs-trigger", "hover focus").split()) == {
        "hover",
        "focus",
    }
    assert attributes.get("title") == GUEST_CONTACT_EXPLANATION
    elements = tuple(_walk_elements(wrapper))
    assert not any("href" in dict(element.attributes) for element in elements)
    buttons = tuple(element for element in elements if element.name == "button")
    assert len(buttons) == 1, "Expected one native Reach out button per wrapper"
    (button,) = buttons
    button_attrs = dict(button.attributes)
    assert element_text(button) == "Reach out"
    assert button_attrs.get("type") == "button"
    assert "disabled" in button_attrs and "formaction" not in button_attrs
    hook = button_attrs.get("data-testid", "")
    username = hook.removeprefix(_DISABLED_BUTTON_PREFIX)
    assert hook != username and username, "Expected a subject-specific disabled hook"
    return username


def _assert_guest_description(wrapper: Element, html: str, username: str) -> None:
    """Require the exact description under its wrapper with a unique document ID.

    :param wrapper: Parsed tooltip wrapper. Example: the focusable Maria control.
    :param html: Full rendered document. Example: HTML containing five cards.
    :param username: Subject of the disabled button. Example: "mrodriguez".
    :return: None when aria-describedby resolves unambiguously to the explanation.
    :raises AssertionError: For a missing, duplicated or incorrect description.
    """
    id_attribute = ("id", f"reach-explanation-{username}")
    assert dict(wrapper.attributes).get("aria-describedby") == id_attribute[1]
    descriptions = tuple(
        element
        for element in _walk_elements(_parse_root(html))
        if id_attribute in element.attributes
    )
    assert len(descriptions) == 1, "The contact description ID must be unique"
    (description,) = descriptions
    assert description in _walk_elements(wrapper)
    assert description != wrapper
    assert element_text(description) == GUEST_CONTACT_EXPLANATION
