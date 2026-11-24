"""S10 production-profile browser certification; no prototype routes."""

from __future__ import annotations

import pytest
from django.urls import reverse
from e2e_helpers import login
from playwright.sync_api import Locator, Page, expect

from methodology.models import ExpertProfile
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

PROFILE_PATH = "/auth/user/profile/"


@pytest.mark.parametrize(
    "viewport",
    (
        pytest.param((1280, 800), id="wide-low-1280x800"),
        pytest.param((1920, 1080), id="large-desktop-1920x1080"),
        pytest.param((1512, 982), id="laptop-1512x982"),
        pytest.param((768, 1024), id="tablet-portrait-768x1024"),
        pytest.param((1024, 768), id="tablet-landscape-1024x768"),
        pytest.param((390, 844), id="phone-390x844"),
        pytest.param((360, 800), id="minimum-phone-360x800"),
    ),
)
def test_own_profile_with_maria_renders_signals_and_existing_controls(
    page: Page,
    live_server_url: str,
    viewport: tuple[int, int],
    cedar_dataset: CedarDataset,
) -> None:
    """Certify exact contribution signals and retained controls in Chromium.

    :param page: Existing isolated browser page; example: fresh context.
    :param live_server_url: Runner-owned server; example: http://localhost:12345.
    :param viewport: IA viewport pixels; example: (390, 844).
    :param cedar_dataset: Real Cedar ORM fixture with Maria and her award history.
    :return: None; example: exact score/category and controls are visible.
    :raises AssertionError: If signals, account controls or geometry fail.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    stored_summary = ExpertProfile.objects.get(user=maria).contribution_summary
    width, height = viewport
    page.set_viewport_size({"width": width, "height": height})
    login(page, live_server_url, maria.username, CEDAR_PASSWORD)

    profile_url = f"{live_server_url}{PROFILE_PATH}"
    response = page.goto(profile_url)
    assert response is not None and response.status == 200
    expect(page).to_have_url(profile_url)
    profile = page.get_by_test_id("profile-page")
    expect(profile.get_by_test_id("profile-email")).to_have_text(maria.email)
    _assert_contribution_signals(profile, stored_summary)
    _assert_account_controls(profile)
    assert page.evaluate("""() => {
        const root = document.documentElement;
        return root.scrollWidth === root.clientWidth;
    }"""), f"Profile overflows horizontally at {width}×{height} CSS pixels"


def _assert_contribution_signals(profile: Locator, stored_summary: str) -> None:
    """Check the visible contribution record against Maria's stored paragraph.

    :param profile: Real profile region. Example: profile-page.
    :param stored_summary: Full nonempty paragraph from Maria's ORM record.
    :return: None once the score, category, prose and breakdowns are present.
    :raises AssertionError: If a signal or section is missing or incorrect.
    """
    assert stored_summary.strip()
    card = profile.get_by_test_id("profile-karma-card")
    expect(card).to_be_visible()
    for test_id, text in (
        ("profile-karma-total", "8,200"),
        ("profile-primary-category", "Design"),
        ("profile-contribution-summary", stored_summary),
    ):
        signal = card.get_by_test_id(test_id)
        expect(signal).to_be_visible()
        expect(signal).to_have_text(text)
    card.get_by_test_id("profile-summary-toggle").click(trial=True)
    for section in ("source", "category"):
        expect(
            profile.get_by_test_id(f"profile-karma-{section}-breakdown")
        ).to_be_visible()


def _assert_account_controls(profile: Locator) -> None:
    """Check retained account sections and exercise actionability safely.

    :param profile: Real profile region. Example: profile-page.
    :return: None once existing account actions are reachable.
    :raises AssertionError: If an existing account control is absent or altered.
    """
    edit = profile.get_by_test_id("profile-edit-btn")
    expect(edit).to_have_attribute("href", reverse("profile_edit"))
    token_field = profile.get_by_test_id("profile-token-field")
    expect(token_field).to_be_visible()
    expect(token_field).to_have_attribute("type", "password")
    password = profile.get_by_test_id("profile-token-regenerate-password")
    expect(password).to_be_visible()
    expect(password).to_be_editable()
    expect(password).to_have_attribute("required", "")
    for test_id in (
        "profile-edit-btn",
        "profile-token-toggle",
        "profile-token-copy",
        "profile-token-regenerate-submit",
    ):
        profile.get_by_test_id(test_id).click(trial=True)
    for test_id in (
        "profile-pips-table",
        "profile-playbooks-table",
        "profile-teams-section",
    ):
        expect(profile.get_by_test_id(test_id)).to_be_visible()
