"""Shared HTML assertions for the anonymous Experts contract."""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

from django.urls import reverse

from tests.support.experts_html import (
    _parse_root,
    _walk_elements,
    element_text,
    find_by_test_id,
)

_DESIGN_RANKING = (
    ("sreed", 15400, 13900),
    ("mrodriguez", 8200, 7200),
    ("pnair", 7600, 7600),
    ("dortiz", 6900, 6900),
    ("hkim", 5800, 5800),
)
_DESIGN_EXCLUDED = ("tmartin", "mchen", "nberg")
_PRIVATE_ACCOUNT_HOOKS = (
    "profile-karma-card",
    "profile-contribution-summary",
    "nav-view-profile",
)
_PRIVATE_TOKEN_PREFIXES = ("profile-api-token", "profile-token-")


def assert_public_design_ranking(html: str) -> None:
    """Check all five public Design cards in their fixed Cedar order.

    :param html: Rendered HTML str. Example: response.content.decode().
    :return: None. Example: assertions succeed.
    :raises AssertionError: Wrong count, order, totals or excluded card.
    :raises ValueError: If the input cannot be parsed as HTML.
    """
    leaderboard = find_by_test_id(html, "experts-leaderboard")
    cards = [node for node in _walk_elements(leaderboard) if node.name == "article"]
    assert len(cards) == len(_DESIGN_RANKING), "Expected five ranked Design cards"
    for rank, (card, (username, total, subtotal)) in enumerate(
        zip(cards, _DESIGN_RANKING, strict=True), start=1
    ):
        attributes = dict(card.attributes)
        assert attributes["data-testid"] == f"experts-card-{username}"
        assert attributes["data-total-points"] == str(total)
        assert attributes["data-category-points"] == str(subtotal)
        rank_label = find_by_test_id(str(card), "expert-card-rank")
        assert element_text(rank_label) == str(rank)
        assert dict(rank_label.attributes)["aria-label"] == f"Rank {rank}"
        score = find_by_test_id(str(card), "expert-card-karma")
        assert element_text(score) == f"{total:,}"
    hooks = {
        value
        for node in _walk_elements(leaderboard)
        for key, value in node.attributes
        if key == "data-testid"
    }
    assert hooks.isdisjoint(f"experts-card-{username}" for username in _DESIGN_EXCLUDED)


def assert_guest_auth_banner(html: str) -> None:
    """Check the guest banner's named authentication anchors.

    :param html: Rendered HTML str. Example: response.content.decode().
    :return: None. Example: Sign In and Register both match routes.
    :raises AssertionError: Missing, duplicated or incorrect banner action.
    :raises ValueError: If the input cannot be parsed as HTML or a URL is malformed.
    """
    banner = find_by_test_id(html, "guest-auth-banner")
    for hook, text, route in (
        ("experts-guest-login", "Sign In", "login"),
        ("experts-guest-register", "Register", "register"),
    ):
        link = find_by_test_id(str(banner), hook)
        attributes = dict(link.attributes)
        assert link.name == "a" and element_text(link) == text
        assert attributes.get("aria-label", text) == text
        assert (
            "disabled" not in attributes and attributes.get("aria-disabled") != "true"
        )
        target = urlsplit(attributes.get("href", ""))
        assert not (target.scheme or target.netloc or target.fragment)
        assert target.path == reverse(route)
        query = parse_qs(target.query, keep_blank_values=True)
        assert not query or (
            route == "login" and query == {"next": [reverse("experts_list")]}
        )


def assert_no_private_account_controls(html: str) -> None:
    """Reject own-profile controls and the fictional private-token sentinel.

    :param html: Rendered HTML str. Example: anonymous Experts response.
    :return: None. Example: no private account control exists.
    :raises AssertionError: Private control or fixture token sentinel appears.
    :raises ValueError: If the input is blank or cannot be parsed as HTML.
    """
    if not isinstance(html, str) or not html.strip():
        raise ValueError("Nonblank HTML text is required to check private controls.")
    for node in _walk_elements(_parse_root(html)):
        for key, value in node.attributes:
            if key in ("data-testid", "id"):
                assert (
                    value not in _PRIVATE_ACCOUNT_HOOKS
                ), "Found an account-only control"
                assert not value.startswith(
                    _PRIVATE_TOKEN_PREFIXES
                ), "Found a private token control"
    assert "DEMO_ONLY_NOT_A_REAL_TOKEN" not in html, "Found a private token sentinel"
