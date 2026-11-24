"""Certify native first/later publication and one immutable release award."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from e2e_helpers import login
from playwright.sync_api import Page, expect

from methodology.models import KarmaAward, VersionSource
from tests.e2e.test_experts_stored_summary import _wait_for_actual_fonts
from tests.support.experts_data import CEDAR_PASSWORD
from tests.support.experts_release import (
    NoraReleaseCase,
    ReleaseHistorySnapshot,
    assert_release_history_preserved,
    build_nora_release_case,
    capture_release_history,
)

_EARNED = "You earned 5,000 Karma for releasing Accessible Workshop Starter"
_NOTES = {
    "1.0": "Publish the workshop guide",
    "2.0": "Publish the reviewed workshop guide",
}


@pytest.mark.django_db(transaction=True)
def test_later_major_with_browser_release_omits_second_award_message(
    page: Page, live_server_url: str
) -> None:
    """Release twice using real modal controls and inspect fresh Product output.

    :param page: Existing fresh browser fixture. Example: Chromium page.
    :param live_server_url: Existing function-scoped origin. Example: localhost:8123.
    :return: None. Example: v1.0 then v2.0, Nora=5000, second earned message absent.
    :raises AssertionError: If UI, actual versions, message or one-row ledger fails.
    """
    case = build_nora_release_case()
    page.set_viewport_size({"width": 1280, "height": 800})
    login(page, live_server_url, case.author.username, CEDAR_PASSWORD)
    detail_path = reverse("playbook_detail", kwargs={"pk": case.playbook.pk})
    page.goto(live_server_url + detail_path)
    _publish_major(page, "open-release-modal", "1.0")
    expect(page.get_by_test_id("alert-message")).to_have_text(_EARNED)
    original = capture_release_history(case.playbook)
    _assert_release_state(case, original, "1.0")
    ledger = tuple(KarmaAward.objects.order_by("pk").values_list())
    _publish_major(page, "open-release-modal-released", "2.0")
    expect(page.get_by_test_id("alert-message")).to_contain_text("released")
    expect(page.get_by_test_id("alert-message")).not_to_contain_text("You earned")
    _assert_release_state(case, original, "2.0")
    assert tuple(KarmaAward.objects.order_by("pk").values_list()) == ledger
    _assert_fresh_product(page, live_server_url)
    assert tuple(KarmaAward.objects.order_by("pk").values_list()) == ledger


def _publish_major(page: Page, opening_id: str, version: str) -> None:
    """Use the actual modal and require normal native completion.

    :param page: Nora's actual playbook page. Example: draft6302.
    :param opening_id: Existing release control. Example: open-release-modal-released.
    :param version: Intended next major. Example: "2.0".
    :return: None. Example: native modal submits and the version badge updates.
    :raises AssertionError: If the modal, normal feedback or version differs.
    """
    assert version in _NOTES, "Only the two declared publication steps are supported"
    _wait_for_actual_fonts(page)
    page.get_by_test_id(opening_id).click()
    modal = page.get_by_test_id("release-modal")
    expect(modal).to_be_visible()
    modal.get_by_test_id("release-description-input").fill(_NOTES[version])
    modal.get_by_test_id("release-confirm").click()
    expect(modal).to_be_hidden()
    expect(page.get_by_test_id("alert-message")).to_be_visible()
    expect(page.get_by_test_id("version-badge")).to_have_text(f"v{version}")
    _wait_for_actual_fonts(page)


def _assert_release_state(
    case: NoraReleaseCase, original: ReleaseHistorySnapshot, version: str
) -> None:
    """Verify complete original award and real version receipt preservation.

    :param case: Actual Nora publication case. Example: owner nberg/book6302.
    :param original: Entire persisted first-award snapshot. Example: one5000row.
    :param version: Legitimate current major. Example: "2.0".
    :return: None. Example: original row and prior history unchanged.
    :raises AssertionError: If receipt, award identity/category/recipient differs.
    """
    assert_release_history_preserved(
        case.playbook, original, version=version, recipient_total=5000
    )
    award = KarmaAward.objects.get(event_identity=f"first_release:{case.playbook.pk}")
    assert (award.recipient_id, award.points, award.category, award.event_channel) == (
        case.author.pk,
        5000,
        "product",
        "release",
    )
    versions = case.playbook.versions.filter(source=VersionSource.RELEASE)
    assert versions.count() == int(Decimal(version))
    receipt = versions.get(version_number=Decimal(version))
    assert receipt.description == _NOTES[version]


def _assert_fresh_product(page: Page, origin: str) -> None:
    """Navigate through the real category link and read Nora's fresh total.

    :param page: Same authenticated native browser. Example: Nora after v2.0.
    :param origin: Function-scoped server. Example: http://localhost:8123.
    :return: None. Example: Alex5400 then Nora5000 with Product selected.
    :raises AssertionError: If route, ranking, displayed score or overflow differs.
    """
    path = reverse("experts_list")
    page.goto(origin + path)
    product = page.get_by_test_id("experts-category-product")
    product.click()
    expect(page).to_have_url(f"{origin}{path}?category=product")
    _wait_for_actual_fonts(page)
    expect(product).to_have_attribute("aria-current", "page")
    leaders = page.get_by_test_id("experts-leaderboard")
    expect(leaders.get_by_role("heading")).to_have_text(["Alex Patel", "Nora Berg"])
    expect(leaders.get_by_test_id("expert-card-karma")).to_have_text(["5,400", "5,000"])
    expect(page.get_by_test_id("experts-card-nberg")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth === innerWidth")
