"""Unique S04 Django-client acceptance bindings."""

from __future__ import annotations

from http import HTTPStatus

from behave import then
from behave.runner import Context
from django.test.html import Element
from django.urls import reverse

from methodology.models import ExpertProfile
from tests.support.experts_html import element_text, find_by_test_id

_CARD_PREFIX = "experts-card-"
_REACH_OUT_EXPLANATION = "You need to be logged in to reach out to the expert"
_CONVERSATION_CAVEAT = "availability and project fit still require a conversation."


@then('card "{card_id}" shows rank {rank:d} and "{display_name}"')
def card_identity(context: Context, card_id: str, rank: int, display_name: str) -> None:
    """Retain the requested real HTTP article and assert identity.

    :param context: Shared Cedar AT context. Example: context.cedar_dataset.
    :param card_id: Stable article hook. Example: "experts-card-mrodriguez".
    :param rank: Expected position. Example: 2.
    :param display_name: Expected visible name. Example: "Maria Rodriguez".
    :return: None. Example: scoped card retained for subsequent Then steps.
    :raises AssertionError: If article, rank or identity is incorrect.
    """
    response = context.response
    assert response.status_code == HTTPStatus.OK, "The Design leaderboard did not load."
    assert card_id.startswith(_CARD_PREFIX) and card_id != _CARD_PREFIX, (
        "Expected a contributor card selector."
    )
    leaderboard = find_by_test_id(response.content, "experts-leaderboard")
    articles = [
        child
        for child in leaderboard.children
        if isinstance(child, Element) and child.name == "article"
    ]
    card = find_by_test_id(str(leaderboard), card_id)
    assert card.name == "article", "The requested contributor is not a card article."
    assert 1 <= rank <= len(articles), "Expected rank is outside the leaderboard."
    assert ("data-testid", card_id) in articles[rank - 1].attributes, (
        "The contributor card is in the wrong position."
    )

    rank_label = find_by_test_id(str(card), "expert-card-rank")
    assert element_text(rank_label) == str(rank), "The displayed rank differs."
    assert ("aria-label", f"Rank {rank}") in rank_label.attributes
    name = find_by_test_id(str(card), "expert-card-name")
    assert element_text(name) == display_name, "The displayed name differs."
    context.s04_card = card
    context.s04_username = card_id.removeprefix(_CARD_PREFIX)


@then(
    'it shows total "{total}", category "{category}", and an accessibility contribution hint'
)
def card_signals(context: Context, total: str, category: str) -> None:
    """Assert the actual scoped card values against Cedar's stored public prose.

    :param context: Context retaining Maria's article. Example: Design response.
    :param total: Formatted overall total. Example: "8,200".
    :param category: Display category. Example: "Design".
    :return: None. Example: total/category/accessibility evidence verified.
    :raises AssertionError: If values or public hint differ.
    """
    html = str(context.s04_card)
    assert element_text(find_by_test_id(html, "expert-card-karma")) == total
    assert element_text(find_by_test_id(html, "expert-card-category")) == category
    username = context.s04_username
    profile = ExpertProfile.objects.get(
        user_id=context.cedar_dataset.user_ids[username]
    )
    stored_summary = profile.contribution_summary
    assert stored_summary and "accessibility" in stored_summary.casefold(), (
        "The Cedar contributor must have stored accessibility prose."
    )
    hint = find_by_test_id(html, f"experts-card-hint-{username}")
    assert hint.name == "p" and hint.children == [stored_summary], (
        "The card must contain the complete stored paragraph as text."
    )


@then("it has an avatar or initials plus View profile and Reach out controls")
def card_actions(context: Context) -> None:
    """Assert initials and actual S17/S14 controls from rendered HTML.

    :param context: Context retaining Maria's article. Example: rank-two card.
    :return: None. Example: MR, View profile and guest Reach out verified.
    :raises AssertionError: If identity fallback or either action is absent.
    """
    html = str(context.s04_card)
    username = context.s04_username
    name = element_text(find_by_test_id(html, "expert-card-name"))
    initials = find_by_test_id(html, f"experts-card-initials-{username}")
    assert element_text(initials) == "MR", "Expected Maria's initials."
    assert ("role", "img") in initials.attributes
    assert ("aria-label", f"{name} initials") in initials.attributes

    profile = find_by_test_id(html, f"experts-view-profile-{username}")
    profile_attrs = dict(profile.attributes)
    assert profile.name == "a" and element_text(profile) == "View profile"
    assert profile_attrs.get("href") == reverse("expert_detail", args=[username])
    assert (
        "disabled" not in profile_attrs and profile_attrs.get("aria-disabled") != "true"
    )
    assert profile_attrs.get("title") == f"View public contribution evidence for {name}"

    # This scenario never performs the shared Elena sign-in step.
    _assert_guest_reach_out(html, username, name)


@then("it makes no availability or suitability assertion")
def card_claims(context: Context) -> None:
    """Reject added inferred claims while preserving the approved caveat.

    :param context: Scoped card and validated stored prose. Example: Maria's card.
    :return: None. Example: exact prose and no recommendation fields.
    :raises AssertionError: If additional assertions appear.
    """
    card = context.s04_card
    username = context.s04_username
    hint = element_text(find_by_test_id(str(card), f"experts-card-hint-{username}"))
    assert hint.endswith(_CONVERSATION_CAVEAT), "The approved caveat must remain."
    assert element_text(card) == (
        f"2 MR Maria Rodriguez Design {hint} 8,200 Karma View profile Reach out "
        f"{_REACH_OUT_EXPLANATION}"
    ), "The card adds copy outside the approved evidence and action labels."


def _assert_guest_reach_out(html: str, username: str, display_name: str) -> None:
    """Check S14's actual guest action in the selected contributor article.

    :param html: Card markup from the guest GET. Example: Maria's article.
    :param username: Contributor route name. Example: "mrodriguez".
    :param display_name: Public name. Example: "Maria Rodriguez".
    :return: None after verifying the disabled control and its description.
    :raises AssertionError: If the login-gated action is missing or altered.
    """
    wrapper = find_by_test_id(html, "experts-reach-out-guest-tooltip")
    wrapper_attrs = dict(wrapper.attributes)
    description_id = f"reach-explanation-{username}"
    assert wrapper_attrs.get("tabindex") == "0"
    assert wrapper_attrs.get("aria-describedby") == description_id
    assert wrapper_attrs.get("title") == _REACH_OUT_EXPLANATION
    button = find_by_test_id(str(wrapper), f"experts-reach-out-disabled-{username}")
    button_attrs = dict(button.attributes)
    assert button.name == "button" and element_text(button) == "Reach out"
    assert "disabled" in button_attrs and "href" not in button_attrs
    assert button_attrs.get("aria-label") == f"Reach out to {display_name}"
    assert any(
        isinstance(child, Element)
        and ("id", description_id) in child.attributes
        and element_text(child) == _REACH_OUT_EXPLANATION
        for child in wrapper.children
    ), "The linked Reach out description is missing or incorrect."
