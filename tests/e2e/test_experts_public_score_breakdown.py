"""S18 browser certification using the existing E2E lifecycle."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from playwright.sync_api import Locator, Page, expect
from rest_framework.authtoken.models import Token

from methodology.models import (
    AgentInteraction,
    ExpertProfile,
    KarmaAward,
    Playbook,
    ProcessImprovementProposal,
)
from tests.support.experts_html import assert_karma_source_rows
from tests.support.experts_privacy import (
    _assert_private_markers_absent,
    assert_private_rows_exist,
    load_privacy_case,
)

_VIEWPORTS = (
    (1280, 800),
    (1920, 1080),
    (1512, 982),
    (768, 1024),
    (1024, 768),
    (390, 844),
    (360, 800),
)
_SOURCES = {
    "Released playbooks": 5000,
    "PIP contributions": 1600,
    "Consumption": 1200,
    "Learning": 400,
}
_CATEGORY_LABELS = ("Design", "Development")
_CATEGORY_POINTS = ("7,200", "1,000")
_TOTAL = 8200
_BOOTSTRAP_MD_WIDTH = 768
_LAYOUT_TOLERANCE_PX = 1
_READ_ONLY_MODELS = (
    User,
    Token,
    Playbook,
    ProcessImprovementProposal,
    KarmaAward,
    ExpertProfile,
    AgentInteraction,
)
DatabaseState = tuple[tuple[dict[str, object], ...], ...]


@pytest.mark.e2e
@pytest.mark.parametrize("viewport", _VIEWPORTS)
def test_public_score_breakdown_with_required_viewport_stays_readable(
    page: Page,
    live_server_url: str,
    transactional_db: None,
    viewport: tuple[int, int],
    mailoutbox: list[EmailMessage],
) -> None:
    """Certify actual detail geometry, legibility and reconciled numbers.

    :param page: Existing function-scoped page. Example: Chromium Page.
    :param live_server_url: Real Django origin. Example: http://localhost:8081.
    :param transactional_db: Runner-owned transactional database. Example: None.
    :param viewport: IA dimensions. Example: (390, 844).
    :param mailoutbox: Actual local mail capture. Example: an empty list.
    :return: None when each source/category value is readable without writes.
    :raises AssertionError: For mismatched data, clipping, overflow or writes.
    """
    dataset = load_privacy_case()
    assert_private_rows_exist(dataset)
    before, mail_before = _database_state(), tuple(mailoutbox)
    page.set_viewport_size(dict(zip(("width", "height"), viewport, strict=True)))
    assert not page.context.cookies()
    response = page.goto(f"{live_server_url}/experts/mrodriguez/")
    assert response is not None and response.status == HTTPStatus.OK
    assert response.request.redirected_from is None
    _settle_public_detail(page)
    _assert_private_markers_absent(page.content(), dataset, allow_contact=False)
    assert_karma_source_rows(page.content(), _SOURCES, "expert-karma-total", _TOTAL)
    _assert_recipe_geometry(page, viewport[0])
    _assert_visible_breakdowns(page)
    assert page.evaluate(
        "document.documentElement.scrollWidth === document.documentElement.clientWidth"
    )
    assert not page.context.cookies()
    if _database_state() != before or tuple(mailoutbox) != mail_before:
        raise AssertionError("Public breakdown reading changed domain rows or mail.")


def _database_state() -> DatabaseState:
    """Snapshot every field of all seven guarded domain models.

    :return: Ordered immutable outer snapshots, e.g. complete award timestamps.
    :raises RuntimeError: An actual ORM failure propagates rather than passing.
    """
    return tuple(
        tuple(model.objects.order_by("pk").values()) for model in _READ_ONLY_MODELS
    )


def _settle_public_detail(page: Page) -> None:
    """Wait for actual identity, loaded typography and any initial consent dialog.

    :param page: Real guest page after successful public navigation.
    :return: None after the actual page is ready for geometry measurements.
    :raises AssertionError: If identity or dismissal does not settle.
    """
    expect(page.get_by_test_id("expert-name")).to_have_text("Maria Rodriguez")
    page.evaluate("document.fonts.ready")
    page.wait_for_function("""() => [...document.fonts].some(font =>
        font.status === 'loaded' && /montserrat/i.test(font.family))""")
    dismiss = page.get_by_role("button", name="Not now", exact=True)
    if dismiss.is_visible():
        dismiss.click()
        expect(dismiss).not_to_be_visible()
    expect(page.get_by_test_id("expert-karma-total")).to_have_text("8,200")


def _assert_recipe_geometry(page: Page, width: int) -> None:
    """Require the actual body-first Bootstrap 8+4 reading/context recipe.

    :param page: Actual settled public detail page.
    :param width: Required CSS viewport width. Example: 360.
    :return: None for stacked phone columns or desktop 8+4 geometry.
    :raises AssertionError: For missing boxes, reversed reading or overlap.
    """
    read = page.get_by_test_id("expert-read-column")
    rail = page.get_by_test_id("expert-context-rail")
    assert read.evaluate("""element => Boolean(element.compareDocumentPosition(
        document.querySelector('[data-testid="expert-context-rail"]')
    ) & Node.DOCUMENT_POSITION_FOLLOWING)""")
    read_box, rail_box = read.bounding_box(), rail.bounding_box()
    assert read_box is not None and rail_box is not None
    if width < _BOOTSTRAP_MD_WIDTH:
        assert rail_box["x"] == pytest.approx(read_box["x"], abs=_LAYOUT_TOLERANCE_PX)
        assert rail_box["width"] == pytest.approx(
            read_box["width"], abs=_LAYOUT_TOLERANCE_PX
        )
        assert rail_box["y"] >= read_box["y"] + read_box["height"]
    else:
        assert rail_box["y"] == pytest.approx(read_box["y"], abs=_LAYOUT_TOLERANCE_PX)
        assert rail_box["x"] == pytest.approx(
            read_box["x"] + read_box["width"], abs=_LAYOUT_TOLERANCE_PX
        )
        assert read_box["width"] == pytest.approx(
            2 * rail_box["width"], abs=_LAYOUT_TOLERANCE_PX
        )


def _assert_visible_breakdowns(page: Page) -> None:
    """Read each source/total cell and separate category through ordinary scrolling.

    :param page: Actual Maria page with its real source table and category list.
    :return: None when every required label/value is separate and unobscured.
    :raises AssertionError: For missing sources, merged categories or clipped text.
    """
    rail = page.get_by_test_id("expert-context-rail")
    sources = rail.get_by_test_id("karma-source-breakdown")
    categories = rail.get_by_test_id("karma-category-breakdown")
    expect(sources.locator("tbody tr")).to_have_count(len(_SOURCES))
    expect(categories.locator("dt")).to_have_text(list(_CATEGORY_LABELS))
    expect(categories.locator("dd")).to_have_text(list(_CATEGORY_POINTS))
    assert not sources.locator("dt, dd").count()
    assert not categories.locator("table").count()
    assert sources.evaluate(
        "(source, category) => !source.contains(category)",
        categories.element_handle(),
    )
    for cell in sources.locator(
        "thead th, tbody th, tbody td, tfoot th, tfoot td"
    ).all():
        _assert_legible_text(cell)
    for field in categories.locator("dt, dd").all():
        _assert_legible_text(field)
    _assert_legible_text(page.get_by_test_id("expert-karma-total"))


def _assert_legible_text(locator: Locator) -> None:
    """Measure actual text line boxes and hit-test them after normal document scroll.

    :param locator: Actual table/category/total text element. Example: Karma cell.
    Inline text whitespace can hit its own ancestor; unrelated covering nodes fail.

    :return: None for unclipped 16px Montserrat text without visible occlusion.
    :raises AssertionError: If the text is clipped, too small, hidden or covered.
    """
    locator.scroll_into_view_if_needed()
    expect(locator).to_be_visible()
    assert locator.evaluate(
        """(element, tolerance) => {
        const style = getComputedStyle(element), box = element.getBoundingClientRect();
        const range = document.createRange(); range.selectNodeContents(element);
        const lines = [...range.getClientRects()];
        return parseFloat(style.fontSize) >= 16 && /montserrat/i.test(style.fontFamily) &&
            style.visibility === 'visible' && Number(style.opacity) > 0 && lines.length > 0 &&
            lines.every(line => line.left >= box.left - tolerance &&
                line.right <= box.right + tolerance && line.top >= box.top - tolerance &&
                line.bottom <= box.bottom + tolerance && line.left >= 0 &&
                line.right <= innerWidth && line.top >= 0 && line.bottom <= innerHeight &&
                [line.left + 1, (line.left + line.right) / 2, line.right - 1].every(x =>
                    {
                    const hit = document.elementFromPoint(x, (line.top + line.bottom) / 2);
                    return element.contains(hit) || Boolean(hit?.contains(element));
                }));
    }""",
        _LAYOUT_TOLERANCE_PX,
    ), "A public breakdown label/value is clipped or obscured."
