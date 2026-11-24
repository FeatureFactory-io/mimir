"""Actual browser certification of EXPERTS-PROFILE-02."""

from __future__ import annotations

from http import HTTPStatus
from typing import TypedDict, cast

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from e2e_helpers import login
from playwright.sync_api import Locator, Page, expect

from methodology.models import AgentInteraction, ExpertProfile, KarmaAward
from tests.e2e.test_experts_own_profile import _assert_account_controls
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

_PREVIEW_LINES = 4
_PIXEL_TOLERANCE = 1
_PREVIEW_HEIGHT = 96
_MARIA_SUMMARY_SENTENCES = 9
_WIDE_LOW_VIEWPORT = (1280, 800)
_TAB_CANDIDATES = "a[href], button, input, select, textarea, [tabindex]"


class SummaryGeometry(TypedDict):
    """Measured rendered geometry; pixels refer to CSS pixels."""

    height: float
    line_height: float
    scroll_height: float
    client_height: float
    line_clamp: str
    overflow_y: str
    tooltip_overlaps: bool


def _open_own_profile(
    page: Page, live_server_url: str, user: User
) -> tuple[Locator, str]:
    """Open the authenticated account's own profile through the live server.

    :param page: Existing browser page. Example: a fresh Chromium page.
    :param live_server_url: Runner-owned server origin. Example: http://localhost:8081.
    :param user: Existing Cedar account. Example: Maria's seeded user.
    :return: Profile locator and URL. Example: /auth/user/profile/ on the live server.
    :raises AssertionError: If the HTTP response or signed-in identity is incorrect.
    """
    login(page, live_server_url, user.username, CEDAR_PASSWORD)
    profile_url = f"{live_server_url}{reverse('profile')}"
    response = page.goto(profile_url)
    assert response is not None and response.status == HTTPStatus.OK
    expect(page).to_have_url(profile_url)
    profile = page.get_by_test_id("profile-page")
    expect(profile.get_by_test_id("profile-email")).to_have_text(user.email)
    return profile, profile_url


def _tab_past_assistant_link(page: Page, profile: Locator) -> None:
    """Follow the native Tab order through the link preceding the summary.

    :param page: Loaded own-profile page. Example: Maria's Chromium page.
    :param profile: Profile wrapper. Example: profile-page.
    :return: None after Tab advances from Configure your AI Assistant.
    :raises AssertionError: If the link is absent from the expected Tab order.
    """
    assistant_link = profile.get_by_role("link", name="Configure your AI Assistant")
    for _ in range(page.locator(_TAB_CANDIDATES).count()):
        page.keyboard.press("Tab")
        if assistant_link.evaluate("link => document.activeElement === link"):
            page.keyboard.press("Tab")
            return
    pytest.fail("Could not reach Configure your AI Assistant with Tab")


def _measure_summary(summary: Locator) -> SummaryGeometry:
    """Measure the actual browser summary box and computed line presentation.

    :param summary: Unique visible region. Example: profile-contribution-summary.
    :return: Geometry. Example: height=96, line_height=24, line_clamp="4".
    :raises AssertionError: If the region is missing, duplicated or unmeasurable.
    """
    expect(summary).to_have_count(1)
    expect(summary).to_be_visible()
    geometry = cast(
        SummaryGeometry,
        summary.evaluate("""async element => {
            await document.fonts.ready;
            const style = getComputedStyle(element);
            const summaryBox = element.getBoundingClientRect();
            const tooltipOverlaps = [...document.querySelectorAll('[role="tooltip"]')].some(tip => {
                const box = tip.getBoundingClientRect();
                return box.width > 0 && box.height > 0 &&
                    box.left < summaryBox.right && box.right > summaryBox.left &&
                    box.top < summaryBox.bottom && box.bottom > summaryBox.top;
            });
            return {
                height: summaryBox.height,
                line_height: Number.parseFloat(style.lineHeight),
                scroll_height: element.scrollHeight,
                client_height: element.clientHeight,
                line_clamp: style.webkitLineClamp,
                overflow_y: style.overflowY,
                tooltip_overlaps: tooltipOverlaps,
            };
        }"""),
    )
    assert geometry["height"] > 0 and geometry["line_height"] > 0
    return geometry


def _assert_summary_toggle(
    page: Page, summary: Locator, toggle: Locator, expanded: bool
) -> None:
    """Check the native control and its accessible state and relationship.

    :param page: Profile page. Example: actual authenticated Chromium page.
    :param summary: Controlled region. Example: profile-contribution-summary.
    :param toggle: Native button. Example: profile-summary-toggle.
    :param expanded: Expected state. Example: False for Show more.
    :return: None when visible text and accessible semantics match.
    :raises AssertionError: If the control, state, label or relationship disagrees.
    """
    expect(toggle).to_be_visible()
    expect(toggle).to_have_js_property("tagName", "BUTTON")
    expect(toggle).to_have_attribute("type", "button")
    expect(toggle).to_have_attribute("aria-expanded", str(expanded).lower())
    label = "Show less" if expanded else "Show more"
    expect(toggle).to_have_text(label, use_inner_text=True)
    expect(toggle).to_have_accessible_name(label)
    summary_id = summary.get_attribute("id")
    assert summary_id and page.locator(f'[id="{summary_id}"]').count() == 1
    expect(toggle).to_have_attribute("aria-controls", summary_id)
    expect(toggle).to_have_accessible_description(
        "Show or hide the full contribution summary"
    )


def _assert_summary_state(
    page: Page, expected_text: str, expanded: bool, *, restored: bool = False
) -> SummaryGeometry:
    """Assert text, ARIA, button label and actual visual clipping together.

    :param page: Existing real browser page. Example: Chromium own-profile page.
    :param expected_text: Complete stored prose. Example: Maria's nine sentences.
    :param expanded: Required real state. Example: False for four-line preview.
    :param restored: Require the preview and toggle to remain readable after collapse.
    :return: Measured geometry. Example: collapsed height approximately 96 pixels.
    :raises AssertionError: If text, linkage, state, label or geometry disagrees.
    :raises ValueError: If expected_text is empty.
    """
    if not expected_text.strip():
        raise ValueError("Expected a nonempty stored contribution summary")
    summary = page.get_by_test_id("profile-contribution-summary")
    toggle = page.get_by_test_id("profile-summary-toggle")
    _assert_summary_toggle(page, summary, toggle, expanded)
    expect(summary).to_have_js_property("textContent", expected_text)
    geometry = _measure_summary(summary)
    preview_height = _PREVIEW_LINES * geometry["line_height"]
    if expanded:
        assert not geometry["tooltip_overlaps"], "A tooltip covers the summary"
        assert geometry["line_clamp"] == "none"
        assert geometry["height"] > preview_height + _PIXEL_TOLERANCE
        assert geometry["scroll_height"] == geometry["client_height"]
    else:
        assert geometry["line_clamp"] == str(_PREVIEW_LINES)
        assert geometry["overflow_y"] == "hidden"
        assert geometry["height"] == pytest.approx(preview_height, abs=_PIXEL_TOLERANCE)
        assert geometry["height"] == pytest.approx(
            _PREVIEW_HEIGHT, abs=_PIXEL_TOLERANCE
        )
        assert geometry["scroll_height"] > geometry["client_height"]
    root = page.locator("html")
    assert root.evaluate("element => element.scrollWidth === element.clientWidth")
    if restored:
        expect(toggle).to_be_focused()
        _assert_restored_preview_in_viewport(page)
    return geometry


def _assert_restored_preview_in_viewport(page: Page) -> None:
    """Check that the restored paragraph and button are clear of the sticky header.

    :param page: Profile page immediately after clicking or pressing Show less.
    :return: None when the preview and button are fully within the visible viewport.
    :raises AssertionError: If the focused control or any preview line is obscured.
    """
    bounds = page.evaluate("""() => {
        const box = name => document.querySelector(`[data-testid="${name}"]`).getBoundingClientRect();
        const summary = box('profile-contribution-summary');
        const toggle = box('profile-summary-toggle');
        const header = box('realm-navbar');
        return {
            contentTop: Math.min(summary.top, toggle.top),
            contentBottom: Math.max(summary.bottom, toggle.bottom),
            headerBottom: Math.max(0, header.bottom),
            viewportBottom: window.innerHeight,
        };
    }""")
    assert bounds["contentTop"] >= bounds["headerBottom"] - _PIXEL_TOLERANCE, bounds
    assert (
        bounds["contentBottom"] <= bounds["viewportBottom"] + _PIXEL_TOLERANCE
    ), bounds


@pytest.mark.parametrize(
    "viewport_size",
    (
        pytest.param(_WIDE_LOW_VIEWPORT, id="wide-low-1280x800"),
        pytest.param((1920, 1080), id="large-desktop-1920x1080"),
        pytest.param((1512, 982), id="laptop-1512x982"),
        pytest.param((768, 1024), id="tablet-portrait-768x1024"),
        pytest.param((1024, 768), id="tablet-landscape-1024x768"),
        pytest.param((390, 844), id="phone-390x844"),
        pytest.param((360, 800), id="minimum-phone-360x800"),
    ),
)
def test_profile_summary_with_long_paragraph_expands_and_collapses(
    page: Page,
    live_server_url: str,
    cedar_dataset: CedarDataset,
    viewport_size: tuple[int, int],
) -> None:
    """Certify every exact EXPERTS-PROFILE-02 transition in a real browser.

    :param page: Existing isolated page. Example: Chromium Page.
    :param live_server_url: Actual server origin. Example: "http://localhost:8081".
    :param cedar_dataset: Real baseline. Example: seeded Maria stored paragraph.
    :param viewport_size: IA viewport. Example: (390, 844).
    :return: None. Example: collapsed, full, then restored four-line presentation.
    :raises AssertionError: If any exact transition or visible geometry fails.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    profiles = ExpertProfile.objects.filter(user=maria).values()
    stored_profile = profiles.get()
    paragraph = stored_profile["contribution_summary"]
    assert len(paragraph.split(". ")) == _MARIA_SUMMARY_SENTENCES
    awards = KarmaAward.objects.order_by("pk").values()
    interactions = AgentInteraction.objects.order_by("pk").values()
    ledger, interaction_history = tuple(awards.all()), tuple(interactions.all())
    width, height = viewport_size
    page.set_viewport_size({"width": width, "height": height})
    profile, profile_url = _open_own_profile(page, live_server_url, maria)
    toggle = profile.get_by_test_id("profile-summary-toggle")
    collapsed = _assert_summary_state(page, paragraph, expanded=False)
    toggle.click()
    _assert_summary_state(page, paragraph, expanded=True)
    expect(toggle).to_be_focused()
    expect(page).to_have_url(profile_url)
    toggle.click()
    restored = _assert_summary_state(page, paragraph, expanded=False, restored=True)
    assert abs(restored["height"] - collapsed["height"]) <= _PIXEL_TOLERANCE
    _assert_account_controls(profile)
    expect(page).to_have_url(profile_url)
    assert profiles.get() == stored_profile
    assert tuple(awards.all()) == ledger
    assert tuple(interactions.all()) == interaction_history


def test_profile_summary_with_keyboard_activation_preserves_focus_and_state(
    page: Page, live_server_url: str, cedar_dataset: CedarDataset
) -> None:
    """Prove keyboard activation and stable focus on the native button.

    :param page: Existing isolated page. Example: Chromium Page.
    :param live_server_url: Real server origin. Example: "http://localhost:8081".
    :param cedar_dataset: Real baseline. Example: authenticated Maria.
    :return: None. Example: Enter expands and Space collapses without navigation.
    :raises AssertionError: If focus, state, text, URL or account controls change.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    paragraph = ExpertProfile.objects.get(user=maria).contribution_summary
    profile, profile_url = _open_own_profile(page, live_server_url, maria)
    toggle = profile.get_by_test_id("profile-summary-toggle")
    initial = _assert_summary_state(page, paragraph, expanded=False)
    _tab_past_assistant_link(page, profile)
    expect(toggle).to_be_focused()
    page.keyboard.press("Enter")
    _assert_summary_state(page, paragraph, expanded=True)
    expect(toggle).to_be_focused()
    expect(page).to_have_url(profile_url)
    page.keyboard.press("Space")
    restored = _assert_summary_state(page, paragraph, expanded=False, restored=True)
    assert abs(restored["height"] - initial["height"]) <= _PIXEL_TOLERANCE
    expect(page).to_have_url(profile_url)
    _assert_account_controls(profile)


def test_profile_summary_with_short_paragraph_displays_without_unnecessary_toggle(
    page: Page, live_server_url: str, cedar_dataset: CedarDataset
) -> None:
    """Prove naturally short stored prose remains fully readable.

    :param page: Existing isolated page. Example: Chromium Page.
    :param live_server_url: Real server origin. Example: "http://localhost:8081".
    :param cedar_dataset: Real baseline. Example: Jordan's short stored paragraph.
    :return: None. Example: full text with no visible or focusable expansion action.
    :raises AssertionError: If text clips or an unnecessary control remains usable.
    """
    jordan = cedar_dataset.users_by_username["jlee"]
    paragraph = ExpertProfile.objects.get(user=jordan).contribution_summary
    assert paragraph.strip()
    # Use a real layout where Jordan’s baseline prose fits without truncation.
    width, height = _WIDE_LOW_VIEWPORT
    page.set_viewport_size({"width": width, "height": height})
    profile, _ = _open_own_profile(page, live_server_url, jordan)
    summary = profile.get_by_test_id("profile-contribution-summary")
    expect(summary).to_have_js_property("textContent", paragraph)
    geometry = _measure_summary(summary)
    assert geometry["line_clamp"] == "none"
    assert geometry["scroll_height"] == geometry["client_height"]
    assert (
        geometry["height"]
        <= _PREVIEW_LINES * geometry["line_height"] + _PIXEL_TOLERANCE
    )
    toggle = profile.get_by_test_id("profile-summary-toggle")
    expect(toggle).to_be_hidden()
    _tab_past_assistant_link(page, profile)
    assert profile.evaluate("""profile => {
        const focused = document.activeElement;
        return profile.contains(focused) &&
            !focused.matches('[data-testid="profile-summary-toggle"]');
    }""")
    profile.get_by_test_id("profile-edit-btn").click(trial=True)
    profile.get_by_test_id("profile-token-regenerate-submit").click(trial=True)
