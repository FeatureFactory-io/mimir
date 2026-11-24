"""Browser certification against the real Experts route."""

from __future__ import annotations

import pytest
from e2e_helpers import login
from playwright.sync_api import Page, expect

from methodology.models import KarmaAward
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
from tests.support.experts_tie_data import apply_cedar_tie03

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

_DESIGN_PATH = "/experts/?category=design"
_DESIGN_RANKING = (
    ("apark", "Alina Park", "15,400"),
    ("sreed", "Sofia Reed", "15,400"),
    ("mrodriguez", "Maria Rodriguez", "8,200"),
    ("pnair", "Priya Nair", "7,600"),
    ("dortiz", "Daniel Ortiz", "6,900"),
)


def test_experts_list_with_tie03_browser_preserves_dom_and_visible_rank(
    page: Page, live_server_url: str, cedar_baseline: CedarDataset
) -> None:
    """Certify tied contributors in real browser order before and after reload.

    :param page: Existing isolated browser page. Example: Chromium Page.
    :param live_server_url: Existing Django live server. Example: "http://localhost:8000".
    :param cedar_baseline: Imported Cedar history for the isolated TIE03 variant.
    :return: None. Example: Alina is visibly rank 1 and Sofia rank 2.
    :raises AssertionError: If route, rank, geometry, totals or ledger differ.
    """
    variant = apply_cedar_tie03(cedar_baseline)
    elena = variant.users_by_username["esvensson"]
    ledger = KarmaAward.objects.order_by("pk")
    original_awards = tuple(ledger.values_list())
    design_url = f"{live_server_url}{_DESIGN_PATH}"

    login(page, live_server_url, elena.username, CEDAR_PASSWORD)
    response = page.goto(design_url)
    assert response is not None and response.ok
    expect(page).to_have_url(design_url)
    expect(page.get_by_test_id("user-display")).to_have_text(elena.username)
    _assert_design_ranking(page)
    assert tuple(ledger.values_list()) == original_awards

    response = page.reload()
    assert response is not None and response.ok
    expect(page).to_have_url(design_url)
    _assert_design_ranking(page)
    assert tuple(ledger.values_list()) == original_awards


def _assert_design_ranking(page: Page) -> None:
    """Check the five visible cards in DOM order and their rendered placement.

    :param page: Loaded Design leaderboard. Example: the TIE03 result after reload.
    :return: None when Alina, Sofia and the three lower ranks match.
    :raises AssertionError: If the current tab, cards, ranks, totals or bounds differ.
    """
    expect(page.get_by_test_id("experts-category-design")).to_have_attribute(
        "aria-current", "page"
    )
    cards = page.get_by_test_id("experts-leaderboard").get_by_role("article")
    expect(cards).to_have_count(len(_DESIGN_RANKING))

    previous_bottom = float("-inf")
    for index, (username, name, total) in enumerate(_DESIGN_RANKING):
        card = cards.nth(index)
        expect(card).to_have_attribute("data-testid", f"experts-card-{username}")
        expect(card.get_by_role("heading", name=name, exact=True)).to_be_visible()

        rank = index + 1
        rank_label = card.get_by_test_id("expert-card-rank")
        expect(rank_label).to_be_visible()
        expect(rank_label).to_have_text(str(rank))
        expect(rank_label).to_have_attribute("aria-label", f"Rank {rank}")

        karma = card.get_by_test_id("expert-card-karma")
        expect(karma).to_be_visible()
        expect(karma).to_have_text(total)

        bounds = card.bounding_box()
        assert bounds is not None, f"Rank {rank} has no visible card bounds"
        assert (
            previous_bottom <= bounds["y"]
        ), f"Rank {rank} overlaps or precedes its predecessor"
        previous_bottom = bounds["y"] + bounds["height"]
