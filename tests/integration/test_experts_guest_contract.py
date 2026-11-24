"""S07 real HTTP ranking and account boundary for anonymous visitors."""

from __future__ import annotations

from html import unescape
from http import HTTPStatus
from typing import cast

import pytest
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
from rest_framework.authtoken.models import Token

from methodology.models import KarmaAward, Playbook, ProcessImprovementProposal
from methodology.services.expert_contact_context import ExpertContactContext
from methodology.services.experts_service import PublicExpertDetail
from tests.support.experts_data import CedarDataset
from tests.support.experts_guest_assertions import (
    assert_guest_auth_banner,
    assert_no_private_account_controls,
    assert_public_design_ranking,
)
from tests.support.experts_html import (
    _walk_elements,
    assert_no_expert_cards,
    assert_other_empty_message,
    element_text,
    find_by_test_id,
)

_CONTACT_EXPLANATION = "You need to be logged in to reach out to the expert"
_PRIVATE_PLAYBOOK = "Cedar Bid Pricing"
_PRIVATE_PROPOSAL = "Internal staffing notes for Cedar"
_PRIVATE_TOKEN = "DEMO_ONLY_NOT_A_REAL_TOKEN"
_DEVELOPMENT_RANKING = (("mchen", 12450), ("jlee", 6100))
_PUBLIC_CARD_FIELDS = {
    "username",
    "name",
    "initials",
    "total_points",
    "category_subtotal",
    "formatted_karma",
    "primary_category",
    "hint",
    "contact",
}


@pytest.mark.django_db
def test_experts_list_with_anonymous_design_request_matches_public_ranking(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Compare public rankings and prove that anonymous visits are read-only.

    :param client: Real anonymous Django client. Example: Bob's fresh session.
    :param cedar_dataset: Imported independent Cedar data. Example: Elena and Maria.
    :return: None after checking public content, authentication and record counts.
    :raises AssertionError: If public access, ranking, privacy or counts differ.
    """
    elena = Client()
    elena.force_login(cedar_dataset.users_by_username["esvensson"])
    private_values = _private_cedar_values(cedar_dataset)
    initial_counts = _account_counts()
    list_url = reverse("experts_list")
    assert list_url == "/experts/"
    design = client.get(list_url, {"category": "design"})
    signed_in = elena.get(list_url, {"category": "design"})
    assert design.status_code == signed_in.status_code == HTTPStatus.OK
    assert signed_in.wsgi_request.user.is_authenticated
    for response in (design, signed_in):
        assert_public_design_ranking(response.content.decode())
    assert _context_ranking(design) == _context_ranking(signed_in)
    assert _account_counts() == initial_counts
    _assert_guest_listing(design, "design", private_values)
    default = client.get(list_url)
    _assert_guest_listing(default, "development", private_values)
    assert _context_ranking(default) == _DEVELOPMENT_RANKING
    other = client.get(list_url, {"category": "other"})
    _assert_guest_listing(other, "other", private_values)
    assert_no_expert_cards(other)
    assert_other_empty_message(other)
    _assert_maria_profile(client, design, cedar_dataset, private_values)
    assert _account_counts() == initial_counts


def _account_counts() -> tuple[int, int, int]:
    """Return User, Token and ledger counts through the real test database."""
    return User.objects.count(), Token.objects.count(), KarmaAward.objects.count()


def _private_cedar_values(dataset: CedarDataset) -> tuple[str, ...]:
    """Prove that the private fixture records exist before testing exclusion."""
    token_keys = tuple(Token.objects.values_list("key", flat=True))
    assert _PRIVATE_TOKEN in token_keys
    assert Playbook.objects.filter(
        name=_PRIVATE_PLAYBOOK, visibility="private"
    ).exists()
    assert ProcessImprovementProposal.objects.filter(
        title=_PRIVATE_PROPOSAL, status=ProcessImprovementProposal.STATUS_DRAFT
    ).exists()
    emails = tuple(
        user.email for user in dataset.users_by_username.values() if user.email
    )
    assert emails
    return (*emails, *token_keys, _PRIVATE_PLAYBOOK, _PRIVATE_PROPOSAL)


def _context_ranking(response: HttpResponse) -> tuple[tuple[str, int], ...]:
    """Get the username and raw total projection without comparing contact state."""
    return tuple(
        (row["username"], row["total_points"]) for row in response.context["people"]
    )


def _assert_guest_surface(
    response: HttpResponse, private_values: tuple[str, ...]
) -> None:
    """Check successful guest access and privacy across rendered HTML and context."""
    assert response.status_code == HTTPStatus.OK
    assert not response.wsgi_request.user.is_authenticated
    html = response.content.decode()
    assert_no_private_account_controls(html)
    for surface in (unescape(html).casefold(), repr(response.context).casefold()):
        assert "mailto:" not in surface, "Guest response exposed a mail destination"
        leaked = any(value.casefold() in surface for value in private_values)
        assert not leaked, "Guest response exposed private Cedar data"
    assert all(
        not isinstance(value, User)
        for context in response.context
        for value in context.flatten().values()
    ), "A public template received an account object"


def _assert_guest_listing(
    response: HttpResponse, category: str, private_values: tuple[str, ...]
) -> None:
    """Check the selected category, public card projection and both card actions."""
    _assert_guest_surface(response, private_values)
    html = response.content.decode()
    assert_guest_auth_banner(html)
    assert response.context["selected_category"] == category
    tabs = find_by_test_id(html, "experts-category-tabs")
    current_tabs = [
        dict(node.attributes).get("data-testid")
        for node in _walk_elements(tabs)
        if ("aria-current", "page") in node.attributes
    ]
    assert current_tabs == [f"experts-category-{category}"]
    rows = response.context["people"]
    leaderboard = find_by_test_id(html, "experts-leaderboard")
    cards = [node for node in _walk_elements(leaderboard) if node.name == "article"]
    assert len(cards) == len(rows) == response.context["count"]
    for row, card in zip(rows, cards, strict=True):
        assert set(row) == _PUBLIC_CARD_FIELDS
        assert all(
            type(value) in (str, int) for key, value in row.items() if key != "contact"
        )
        username, total = row["username"], row["total_points"]
        assert ("data-testid", f"experts-card-{username}") in card.attributes
        assert (
            element_text(find_by_test_id(str(card), "expert-card-karma"))
            == f"{total:,}"
        )
        assert (
            element_text(find_by_test_id(str(card), "expert-card-category"))
            == category.title()
        )
        link = find_by_test_id(str(card), f"experts-view-profile-{username}")
        assert link.name == "a" and element_text(link) == "View profile"
        attributes = dict(link.attributes)
        assert attributes["href"] == reverse("expert_detail", args=[username])
        assert (
            "disabled" not in attributes and attributes.get("aria-disabled") != "true"
        )
        _assert_guest_contact(str(card), username, row["contact"])


def _assert_guest_contact(
    html: str, username: str, contact: ExpertContactContext
) -> None:
    """Check inactive contact policy and the initial focusable explanation markup."""
    assert contact == ExpertContactContext(
        username, "authentication_required", None, _CONTACT_EXPLANATION
    )
    wrapper = find_by_test_id(html, "experts-reach-out-guest-tooltip")
    description_id = f"reach-explanation-{username}"
    wrapper_attributes = dict(wrapper.attributes)
    assert wrapper_attributes["tabindex"] == "0"
    assert {"hidden", "inert"}.isdisjoint(wrapper_attributes)
    assert wrapper_attributes["aria-describedby"] == description_id
    assert wrapper_attributes["title"] == _CONTACT_EXPLANATION
    assert wrapper_attributes["data-bs-toggle"] == "tooltip"
    [description] = [
        node
        for node in _walk_elements(wrapper)
        if ("id", description_id) in node.attributes
    ]
    assert element_text(description) == _CONTACT_EXPLANATION
    button = find_by_test_id(str(wrapper), f"experts-reach-out-disabled-{username}")
    assert button.name == "button" and element_text(button) == "Reach out"
    button_attributes = dict(button.attributes)
    assert button_attributes["type"] == "button" and "disabled" in button_attributes
    assert "href" not in wrapper_attributes and "href" not in button_attributes


def _assert_maria_profile(
    client: Client,
    listing: HttpResponse,
    dataset: CedarDataset,
    private_values: tuple[str, ...],
) -> None:
    """Follow Maria's public profile and its public evidence with the same guest client."""
    profile = find_by_test_id(listing.content, "experts-view-profile-mrodriguez")
    path = dict(profile.attributes)["href"]
    assert path == "/experts/mrodriguez/"
    response = client.get(path)
    _assert_guest_surface(response, private_values)
    person = cast(PublicExpertDetail, response.context["person"])
    _assert_maria_projection(person, dataset)
    contact_person = response.context["contact_person"]
    assert set(contact_person) == set(person) | {"contact"}
    assert all(contact_person[key] == value for key, value in person.items())
    _assert_guest_contact(
        response.content.decode(), "mrodriguez", contact_person["contact"]
    )
    assert (
        element_text(find_by_test_id(response.content, "expert-name"))
        == "Maria Rodriguez"
    )
    summary = find_by_test_id(response.content, "expert-contribution-summary")
    assert element_text(summary) == person["summary"]
    evidence = find_by_test_id(response.content, "expert-public-playbooks")
    assert "Accessibility Audit Playbook" in element_text(evidence)
    action = find_by_test_id(str(evidence), "expert-playbook-6101")
    assert action.name == "a" and element_text(action) == "View"
    evidence_path = dict(action.attributes)["href"]
    assert evidence_path == reverse("playbook_detail", args=[6101])
    playbook = client.get(evidence_path)
    assert playbook.status_code == HTTPStatus.OK
    assert not playbook.wsgi_request.user.is_authenticated


def _assert_maria_projection(person: PublicExpertDetail, dataset: CedarDataset) -> None:
    """Check the allowlisted detail DTO against real identity and independent Cedar facts."""
    assert person.keys() == PublicExpertDetail.__required_keys__
    oracle = next(
        row for row in dataset.oracle["people"] if row["username"] == "mrodriguez"
    )
    assert person["subject_id"] == dataset.user_ids["mrodriguez"]
    assert person["username"] == "mrodriguez"
    assert person["name"] == oracle["name"]
    assert person["initials"] == "MR"
    assert person["total_karma"] == 8200 and person["formatted_karma"] == "8,200"
    assert person["primary_category"] == "Design"
    assert person["summary"] == oracle["summary"] and person["summary"]
    assert person["numeric_fallback"] == "1 released playbook · 0 copies"
    assert person["public_playbooks"] == (
        {
            "pk": 6101,
            "title": "Accessibility Audit Playbook",
            "version": "1.0",
            "category": "Design",
        },
    )
    for row in (*person["source_rows"], *person["category_rows"]):
        assert set(row) == {"label", "points"}
        assert all(type(value) is str for value in row.values())
