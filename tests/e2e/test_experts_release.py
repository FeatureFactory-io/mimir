"""Browser certification of the independently restored Nora release case."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from e2e_helpers import login
from playwright.sync_api import Page, expect

from methodology.models import KarmaAward, VersionSource
from tests.support.experts_data import CEDAR_PASSWORD
from tests.support.experts_release import build_nora_release_case

_RELEASE_DESCRIPTION = "Publish the workshop guide"
_EARNED_MESSAGE = "You earned 5,000 Karma for releasing Accessible Workshop Starter"


@pytest.mark.django_db(transaction=True)
def test_karma_release_01_with_browser_shows_award_and_product_order(
    page: Page, live_server_url: str
) -> None:
    """Release through the actual modal and inspect the refreshed Product list.

    Reuse login/live-server fixtures and the shared Cedar adapter. Use existing
    release-modal, release-description-input, release-confirm and alert-message
    test IDs; use S03's semantic expert-card selectors for ranking.

    :param page: Fresh real browser page. Example: Chromium page.
    :param live_server_url: Real isolated Django origin. Example: http://localhost:8123.
    :return: None when publication is persisted and earned Karma is visible in Product.
    :raises AssertionError: If publication, feedback, displayed points or ordering fail.
    """
    case = build_nora_release_case()
    login(page, live_server_url, case.author.username, CEDAR_PASSWORD)
    detail_path = reverse("playbook_detail", kwargs={"pk": case.playbook.pk})
    page.goto(f"{live_server_url}{detail_path}")
    page.get_by_test_id("open-release-modal").click()
    modal = page.get_by_test_id("release-modal")
    expect(modal).to_be_visible()
    modal.get_by_test_id("release-description-input").fill(_RELEASE_DESCRIPTION)
    modal.get_by_test_id("release-confirm").click()

    alert = page.get_by_test_id("alert-message")
    expect(alert).to_be_visible()
    expect(alert).to_have_text(_EARNED_MESSAGE)
    expect(page.get_by_test_id("version-badge")).to_have_text("v1.0")
    version = case.playbook.versions.get(source=VersionSource.RELEASE)
    assert version.version_number == Decimal("1.0")
    assert version.description == _RELEASE_DESCRIPTION
    award = KarmaAward.objects.get(recipient=case.author)
    assert award.source_kind == KarmaAward.SourceKind.RELEASE
    assert (award.category, award.points) == ("product", 5000)

    experts_url = f"{live_server_url}{reverse('experts_list')}"
    page.goto(experts_url)
    product = page.get_by_test_id("experts-category-product")
    product.click()
    expect(page).to_have_url(f"{experts_url}?category=product")
    expect(product).to_have_attribute("aria-current", "page")
    leaderboard = page.get_by_test_id("experts-leaderboard")
    expect(leaderboard.get_by_role("heading")).to_have_text(["Alex Patel", "Nora Berg"])
    scores = leaderboard.get_by_test_id("expert-card-karma")
    expect(scores).to_have_text(["5,400", "5,000"])
    for score in scores.all():
        expect(score).to_be_visible()
