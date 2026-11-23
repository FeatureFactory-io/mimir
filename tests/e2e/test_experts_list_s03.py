"""Actual browser order proof; reused by broader Cedar certification."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.support.experts_data import CedarBaseline

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.e2e]

DESIGN_RANKING = (
    ("Sofia Reed", "15,400"),
    ("Maria Rodriguez", "8,200"),
    ("Priya Nair", "7,600"),
    ("Daniel Ortiz", "6,900"),
    ("Hana Kim", "5,800"),
)
DEVELOPMENT_RANKING = (("Mike Chen", "12,450"), ("Jordan Lee", "6,100"))


def test_experts_list_with_design_browser_preserves_rank_order(
    page: Page, live_server_url: str, cedar_baseline: CedarBaseline
) -> None:
    """Open Design, assert five ordered cards, and follow Development.

    :param page: Existing real Playwright page fixture. Example: Chromium Page.
    :param live_server_url: Runner-owned Django server. Example: http://localhost:8000.
    :param cedar_baseline: Real transactional dataset. Example: CedarBaseline({}, {}, {}).
    :return: None. Example: None.
    :raises AssertionError: If visible order, boundaries or category switch fails.
    """
    page.goto(f"{live_server_url}/experts/?category=design")
    expect(page.get_by_test_id("experts-category-design")).to_have_attribute(
        "aria-current", "page"
    )
    leaderboard = page.get_by_test_id("experts-leaderboard")
    cards = leaderboard.get_by_role("article")
    expect(cards).to_have_count(len(DESIGN_RANKING))
    for position, (name, points) in enumerate(DESIGN_RANKING):
        card = cards.nth(position)
        expect(card.get_by_role("heading", name=name, exact=True)).to_be_visible()
        karma = card.get_by_test_id("expert-card-karma")
        expect(karma).to_be_visible()
        expect(karma).to_have_text(points)
    for username in ("mchen", "tmartin", "nberg"):
        expect(leaderboard.get_by_test_id(f"experts-card-{username}")).to_have_count(0)

    development = page.get_by_test_id("experts-category-development")
    development.click()
    expect(page).to_have_url(f"{live_server_url}/experts/?category=development")
    expect(development).to_have_attribute("aria-current", "page")
    expect(cards).to_have_count(len(DEVELOPMENT_RANKING))
    for position, (name, points) in enumerate(DEVELOPMENT_RANKING):
        card = cards.nth(position)
        expect(card.get_by_role("heading", name=name, exact=True)).to_be_visible()
        karma = card.get_by_test_id("expert-card-karma")
        expect(karma).to_be_visible()
        expect(karma).to_have_text(points)
    expect(leaderboard.get_by_test_id("experts-card-mrodriguez")).to_have_count(0)
