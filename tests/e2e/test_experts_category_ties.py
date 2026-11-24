"""Certify category tie placement on the real Experts leaderboard."""

from __future__ import annotations

import pytest
from django.urls import reverse
from playwright.sync_api import Page, expect

from methodology.models import KarmaAward
from tests.support.experts_category_ties import load_category_tie

TIED_TOTAL = "10,000"


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("variant", "category", "other_category"),
    [
        pytest.param("TIE01", "Development", "Design", id="TIE01"),
        pytest.param("TIE02", "Design", "Development", id="TIE02"),
    ],
)
def test_primary_category_with_cedar_tie_renders_correct_tab(
    page: Page, live_server_url: str, variant: str, category: str, other_category: str
) -> None:
    """Follow the real category links to verify where the tied expert appears.

    :param page: Isolated Chromium page.
    :param live_server_url: Runner-owned Django server. Example: http://localhost:8000.
    :param variant: Historical Cedar tie. Example: "TIE01".
    :param category: Expected category badge and current tab. Example: "Development".
    :param other_category: Other tied category. Example: "Design".
    :return: None after verifying placement, badge, total and ledger.
    :raises AssertionError: If any browser result differs or awards change.
    """
    tie = load_category_tie(variant)
    ledger = KarmaAward.objects.order_by("pk")
    before = tuple(ledger.values_list())
    list_url = f"{live_server_url}{reverse('experts_list')}"

    page.goto(list_url)
    tabs = page.get_by_test_id("experts-category-tabs")
    expected_tab = tabs.get_by_test_id(f"experts-category-{category.lower()}")
    other_tab = tabs.get_by_test_id(f"experts-category-{other_category.lower()}")
    leaderboard = page.get_by_test_id("experts-leaderboard")
    card = leaderboard.get_by_test_id(f"experts-card-{tie.user.username}")

    other_tab.click()
    expect(page).to_have_url(f"{list_url}?category={other_category.lower()}")
    expect(other_tab).to_have_attribute("aria-current", "page")
    expect(expected_tab).not_to_have_attribute("aria-current", "page")
    expect(card).to_have_count(0)

    expected_tab.click()
    expect(page).to_have_url(f"{list_url}?category={category.lower()}")
    expect(expected_tab).to_have_attribute("aria-current", "page")
    expect(other_tab).not_to_have_attribute("aria-current", "page")
    expect(card).to_be_visible()
    expect(
        card.get_by_role("heading", name=tie.user.get_full_name(), exact=True)
    ).to_be_visible()
    expect(card.get_by_text(category, exact=True)).to_be_visible()
    karma = card.get_by_test_id("expert-card-karma")
    expect(karma).to_be_visible()
    expect(karma).to_have_text(TIED_TOTAL)
    assert tuple(ledger.values_list()) == before
