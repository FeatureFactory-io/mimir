"""Certify EXPERTS-PROFILE-03 on the production account profile."""

from __future__ import annotations

from http import HTTPStatus
from typing import TypedDict, cast

import pytest
from django.db.models import Sum
from django.urls import reverse
from e2e_helpers import login
from playwright.sync_api import Locator, Page, expect

from methodology.models import AgentInteraction, ExpertProfile, KarmaAward
from tests.e2e.test_experts_own_profile import _assert_account_controls
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
from tests.support.experts_logs import capture_experts_logs

_EXPECTED_SOURCES = (
    ("Released", 5000),
    ("PIP", 1600),
    ("Consumption", 1200),
    ("Learning", 400),
)
_EXPECTED_TOTAL = 8200
_MINIMUM_TEXT_SIZE = 16
_SUMMARY_LOGGERS = (
    "methodology.services.contribution_summary_service",
    "methodology.services.contribution_summary_boundary",
)


class SourceGeometry(TypedDict):
    """Readability measurements in CSS pixels and DOM-order cell indices."""

    root_width: int
    root_scroll_width: int
    wrapper_width: int
    wrapper_scroll_width: int
    table_width: float
    smallest_font: float
    horizontally_clipped_cells: list[int]
    obstructed_cells: list[int]
    wrapper_overflow_x: str
    wrapper_scroll_left: int
    page_scroll_y: float


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("width", "height"),
    [
        pytest.param(1280, 800, id="wide-low-1280x800"),
        pytest.param(1920, 1080, id="large-desktop-1920x1080"),
        pytest.param(1512, 982, id="laptop-1512x982"),
        pytest.param(768, 1024, id="tablet-portrait-768x1024"),
        pytest.param(1024, 768, id="tablet-landscape-1024x768"),
        pytest.param(390, 844, id="phone-390x844"),
        pytest.param(360, 800, id="minimum-phone-360x800"),
    ],
)
def test_profile_sources_with_required_viewports_remain_reconciled(
    page: Page,
    live_server_url: str,
    width: int,
    height: int,
    cedar_dataset: CedarDataset,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Certify authenticated profile rows at each IA viewport.

    :param page: Real Chromium page. Example: fresh isolated context.
    :param live_server_url: Function-scoped Django URL. Example: http://localhost:50123.
    :param width: Required CSS viewport width. Example: 360.
    :param height: Required CSS viewport height. Example: 800.
    :param cedar_dataset: Imported Cedar fixture with Maria's stored history.
    :param caplog: Capture for the real summary service and provider boundary.
    :return: None once four readable rows reconcile to 8200 without overflow.
    :raises AssertionError: If navigation, values, geometry or persisted state differs.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    profiles = ExpertProfile.objects.filter(user=maria).values()
    awards = KarmaAward.objects.order_by("pk").values()
    interactions = AgentInteraction.objects.order_by("pk").values()
    stored_profile = profiles.get()
    ledger = tuple(awards.all())
    history = tuple(interactions.all())
    sources = _ledger_source_totals(maria.pk)

    page.set_viewport_size({"width": width, "height": height})
    login(page, live_server_url, maria.username, CEDAR_PASSWORD)
    with capture_experts_logs(caplog, _SUMMARY_LOGGERS):
        profile = _open_profile(page, live_server_url)
        expect(profile.get_by_test_id("profile-email")).to_have_text(maria.email)
        _assert_profile_context(profile, stored_profile["contribution_summary"])
        table = profile.get_by_test_id("profile-karma-source-breakdown")
        _assert_source_values(table, sources)
        _assert_source_geometry(table)
    expect(page).to_have_url(f"{live_server_url}{reverse('profile')}")
    assert not any(record.name in _SUMMARY_LOGGERS for record in caplog.records)
    assert profiles.get() == stored_profile
    assert tuple(awards.all()) == ledger
    assert tuple(interactions.all()) == history


def _open_profile(page: Page, live_server_url: str) -> Locator:
    """Open the actual owner profile using the authenticated browser.

    :param page: Real authenticated Chromium page. Example: Maria's session.
    :param live_server_url: Runner-owned Django origin. Example: http://localhost:50123.
    :return: Live profile container. Example: profile-page.
    :raises AssertionError: If the server does not return HTTP 200.
    """
    response = page.goto(f"{live_server_url}{reverse('profile')}")
    assert response is not None and response.status == HTTPStatus.OK
    return page.get_by_test_id("profile-page")


def _ledger_source_totals(user_id: int) -> tuple[tuple[str, int], ...]:
    """Aggregate Maria's persisted awards without the presentation service.

    :param user_id: Fixture account ID. Example: Maria's primary key.
    :return: Source labels and points. Example: (("Released", 5000), ...).
    :raises AssertionError: If the independent source/category contracts differ.
    """
    awards = KarmaAward.objects.filter(recipient_id=user_id)
    by_kind = dict(awards.values_list("source_kind").annotate(total=Sum("points")))
    sources = (
        ("Released", by_kind["release"]),
        ("PIP", by_kind["major"] + by_kind["minor"]),
        ("Consumption", by_kind["consumption"]),
        ("Learning", by_kind["learning"]),
    )
    assert sources == _EXPECTED_SOURCES
    assert sum(by_kind.values()) == _EXPECTED_TOTAL
    assert dict(awards.values_list("category").annotate(total=Sum("points"))) == {
        "design": 7200,
        "development": 1000,
    }
    return sources


def _assert_profile_context(profile: Locator, stored_summary: str) -> None:
    """Check separate categories, the stored summary and retained account actions.

    :param profile: Authenticated profile region. Example: profile-page.
    :param stored_summary: Original nonempty Maria paragraph.
    :return: None once categories, score, summary and controls are available.
    :raises AssertionError: If any inherited signal or control regresses.
    """
    assert stored_summary.strip()
    _assert_account_controls(profile)
    card = profile.get_by_test_id("profile-karma-card")
    total = card.get_by_test_id("profile-karma-total")
    expect(total).to_be_visible()
    expect(total).to_have_text(f"{_EXPECTED_TOTAL:,}")
    expect(card.get_by_test_id("profile-primary-category")).to_have_text("Design")
    expect(card.get_by_test_id("profile-contribution-summary")).to_have_text(
        stored_summary
    )
    card.get_by_test_id("profile-summary-toggle").click(trial=True)

    category = profile.get_by_test_id("profile-karma-category-breakdown")
    expect(category).to_be_visible()
    expect(category).to_have_js_property("tagName", "DL")
    expect(category.locator("dt, dd")).to_have_text(
        ["Design", "7200", "Development", "1000"]
    )


def _assert_source_values(table: Locator, sources: tuple[tuple[str, int], ...]) -> None:
    """Check the semantic table and reconcile its actual numbers.

    :param table: Profile source table, distinct from the category definition list.
    :param sources: Expected labels and points from the ORM, in presentation order.
    :return: None once actual rows sum to the footer and the expected card total.
    :raises AssertionError: If the headers, ordered sources or total differ.
    """
    expect(table).to_be_visible()
    expect(table).to_have_role("table")
    expect(table.get_by_role("columnheader")).to_have_text(["Source", "Karma"])
    rows = table.locator("tbody").get_by_role("row")
    expect(rows).to_have_count(len(sources))
    expect(rows.get_by_role("rowheader")).to_have_text([label for label, _ in sources])
    amounts = rows.get_by_role("cell")
    expect(amounts).to_have_text([str(points) for _, points in sources])
    actual_sum = sum(int(value) for value in amounts.all_inner_texts())
    assert actual_sum == _EXPECTED_TOTAL
    footer = table.locator("tfoot")
    expect(footer.get_by_role("rowheader", name="Total", exact=True)).to_be_visible()
    expect(footer.get_by_role("cell")).to_have_text(f"{actual_sum:,}")


def _assert_source_geometry(table: Locator) -> None:
    """Require every cell to be readable using the documented table wrapper.

    :param table: Actual source table. Example: profile-karma-source-breakdown.
    :return: None when all text is readable through normal scrolling.
    :raises AssertionError: If text is obscured or the whole page overflows.
    """
    table.page.evaluate("() => document.fonts.ready.then(() => true)")
    table.scroll_into_view_if_needed()
    initial = _measure_source_geometry(table)
    if not initial["horizontally_clipped_cells"]:
        return

    # IA §11 permits horizontal scrolling inside the table wrapper.
    assert initial["wrapper_overflow_x"] in ("auto", "scroll"), initial
    scroll_limit = initial["wrapper_scroll_width"] - initial["wrapper_width"]
    assert scroll_limit > initial["wrapper_scroll_left"], initial
    bounds = table.bounding_box()
    assert bounds is not None
    table.page.mouse.move(
        bounds["x"] + initial["wrapper_width"] / 2, bounds["y"] + bounds["height"] / 2
    )
    table.page.mouse.wheel(scroll_limit, 0)
    expect(table.locator("..")).to_have_js_property("scrollLeft", scroll_limit)

    scrolled = _measure_source_geometry(table)
    assert scrolled["page_scroll_y"] == initial["page_scroll_y"], scrolled
    assert not set(initial["horizontally_clipped_cells"]).intersection(
        scrolled["horizontally_clipped_cells"]
    ), (initial, scrolled)


def _measure_source_geometry(table: Locator) -> SourceGeometry:
    """Measure actual text bounds and whether each visible text area is unobstructed.

    :param table: Visible source table. Example: profile-karma-source-breakdown.
    :return: Browser geometry. Example: equal root widths and no obstructed cells.
    :raises AssertionError: If text is obstructed, shrunk or overflows the page.
    """
    geometry = cast(SourceGeometry, table.evaluate(_SOURCE_GEOMETRY))
    assert geometry["root_scroll_width"] == geometry["root_width"], geometry
    assert geometry["smallest_font"] >= _MINIMUM_TEXT_SIZE, geometry
    assert not geometry["obstructed_cells"], geometry
    return geometry


_SOURCE_GEOMETRY = """table => {
    const root = document.documentElement;
    const wrapper = table.closest(".table-responsive");
    const box = wrapper.getBoundingClientRect();
    const cells = [...table.querySelectorAll("th, td")];
    const range = document.createRange();
    const clipped = [];
    const obstructed = [];

    cells.forEach((cell, index) => {
        range.selectNodeContents(cell);
        const rects = [...range.getClientRects()];
        if (rects.some(rect => rect.left < box.left || rect.right > box.right)) {
            clipped.push(index);
        }
        if (!rects.length || rects.some(rect => !isUnobstructed(cell, rect))) {
            obstructed.push(index);
        }
    });

    function isUnobstructed(cell, rect) {
        if (rect.width <= 0 || rect.height <= 0 ||
            rect.top < 0 || rect.bottom > root.clientHeight ||
            box.left < 0 || box.right > root.clientWidth) {
            return false;
        }
        const left = Math.max(rect.left, box.left);
        const right = Math.min(rect.right, box.right);
        if (left >= right) return true;  // This text must be read after local scrolling.
        return [0.1, 0.5, 0.9].every(fraction =>
            [rect.top + 1, rect.bottom - 1].every(y =>
                cell.contains(document.elementFromPoint(left + (right - left) * fraction, y))
            )
        );
    }

    return {
        root_width: root.clientWidth,
        root_scroll_width: root.scrollWidth,
        wrapper_width: wrapper.clientWidth,
        wrapper_scroll_width: wrapper.scrollWidth,
        table_width: table.getBoundingClientRect().width,
        smallest_font: Math.min(...cells.map(cell => parseFloat(getComputedStyle(cell).fontSize))),
        horizontally_clipped_cells: clipped,
        obstructed_cells: obstructed,
        wrapper_overflow_x: getComputedStyle(wrapper).overflowX,
        wrapper_scroll_left: wrapper.scrollLeft,
        page_scroll_y: window.scrollY,
    };
}"""
