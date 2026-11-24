"""S14-owned contact phrases; baseline/authentication bindings are reused."""

from __future__ import annotations

from http import HTTPStatus

from behave import then, when
from behave.runner import Context
from django.urls import reverse

from tests.support.experts_html import element_text, find_by_test_id

_MARIA_USERNAME = "mrodriguez"
_MARIA_CARD = f"experts-card-{_MARIA_USERNAME}"
_MARIA_ACTION = f"experts-reach-out-{_MARIA_USERNAME}"


@when("she inspects Maria's Reach out action on list and public detail")
def inspect_maria_contact_actions(context: Context) -> None:
    """Read real production HTML for both contact surfaces.

    :param context: Existing AT context. Example: Elena's authenticated client.
    :return: None. Example: two parsed Maria actions retained for assertions.
    :raises AssertionError: For unsuccessful requests or missing Maria actions.
    """
    listing = context.client.get(reverse("experts_list"), {"category": "design"})
    detail = context.client.get(reverse("expert_detail", args=[_MARIA_USERNAME]))
    assert listing.status_code == HTTPStatus.OK, "The Design list did not load."
    assert detail.status_code == HTTPStatus.OK, "Maria's public detail did not load."

    card = find_by_test_id(listing.content, _MARIA_CARD)
    context.maria_contact_actions = (
        ("Design list", find_by_test_id(str(card), _MARIA_ACTION)),
        ("public detail", find_by_test_id(detail.content, _MARIA_ACTION)),
    )


@then('both destinations are "{destination}"')
def assert_both_contact_destinations(context: Context, destination: str) -> None:
    """Compare both rendered Maria destinations with the exact contract value.

    :param context: Existing AT context. Example: retained list/detail actions.
    :param destination: Expected href. Example: "mailto:maria.rodriguez@example.com".
    :return: None. Example: both action destinations match.
    :raises AssertionError: For an absent, disabled or mismatched action.
    """
    for surface, action in context.maria_contact_actions:
        attributes = dict(action.attributes)
        assert action.name == "a", f"{surface}: Maria's Reach out is not an anchor."
        assert (
            "disabled" not in attributes and attributes.get("aria-disabled") != "true"
        ), f"{surface}: Maria's Reach out is disabled."
        assert (
            attributes.get("href") == destination
        ), f"{surface}: Maria's Reach out has the wrong destination."


@then("the action does not imply that availability is confirmed")
def assert_contact_does_not_confirm_availability(context: Context) -> None:
    """Check action labels/descriptions preserve the discussion-only handoff.

    :param context: Existing AT context. Example: both retained contact controls.
    :return: None. Example: discussion wording and no availability promise.
    :raises AssertionError: For availability or suitability confirmation language.
    """
    for surface, action in context.maria_contact_actions:
        assert (
            element_text(action) == "Reach out"
        ), f"{surface}: expected the Reach out label."
        assert dict(action.attributes).get("title") == (
            "Start an email discussion with Maria Rodriguez"
        ), f"{surface}: expected an invitation to start an email discussion."
