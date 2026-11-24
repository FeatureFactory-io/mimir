from __future__ import annotations

import pytest
from e2e_helpers import login
from playwright.sync_api import Locator, Page, expect

from methodology.models import ExpertProfile
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.e2e]
DETAIL_VIEWPORTS = (
    (1280, 800),
    (1920, 1080),
    (1512, 982),
    (768, 1024),
    (1024, 768),
    (390, 844),
    (360, 800),
)
BOOTSTRAP_MD_WIDTH = 768
LAYOUT_TOLERANCE_PX = 1
MARIA_DETAIL_PATH = "/experts/mrodriguez/"


@pytest.fixture
def stored_maria_summary(cedar_dataset: CedarDataset) -> str:
    """Read the expected paragraph from the real fixture's persisted profile.

    :param cedar_dataset: Imported Cedar history. Example: includes Maria.
    :return: The complete stored contribution paragraph.
    :raises ExpertProfile.DoesNotExist: The profile was not imported.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    return ExpertProfile.objects.get(user=maria).contribution_summary


def test_public_detail_with_full_summary_has_no_visual_truncation(
    page: Page, live_server_url: str, stored_maria_summary: str
) -> None:
    """Prove actual browser text and computed styles preserve the paragraph.

    :param page: Existing isolated page fixture. Example: Chromium page.
    :param live_server_url: Real Django URL. Example: http://localhost:8081.
    :param stored_maria_summary: Complete paragraph from Maria's persisted profile.
    :return: None. Example: full stored paragraph fits without clamp or ellipsis.
    :raises AssertionError: For missing sentences or computed truncation.
    """
    login(page, live_server_url, "esvensson", CEDAR_PASSWORD)
    summary = _open_maria_detail(page, live_server_url)
    _assert_untruncated_summary(summary, stored_maria_summary)


@pytest.mark.parametrize(("width", "height"), DETAIL_VIEWPORTS)
def test_public_detail_with_required_viewport_preserves_read_context_recipe(
    page: Page, live_server_url: str, stored_maria_summary: str, width: int, height: int
) -> None:
    """Prove the required body/rail recipe at every IA viewport.

    :param page: Existing page fixture. Example: isolated Chromium page.
    :param live_server_url: Real server address. Example: http://localhost:8081.
    :param stored_maria_summary: Complete paragraph from Maria's persisted profile.
    :param width: CSS viewport width. Example: 390.
    :param height: CSS viewport height. Example: 844.
    :return: None. Example: readable full paragraph, correct rail position, no overflow.
    :raises AssertionError: For clipping, overlap or incorrect reading layout.
    """
    page.set_viewport_size({"width": width, "height": height})
    summary = _open_maria_detail(page, live_server_url)
    dismiss_consent = page.get_by_role("button", name="Not now", exact=True)
    if dismiss_consent.is_visible():
        dismiss_consent.click()

    read_column = page.get_by_test_id("expert-read-column")
    context_rail = page.get_by_test_id("expert-context-rail")
    _assert_read_context_geometry(read_column, context_rail, width)
    assert page.evaluate(
        "document.documentElement.scrollWidth === document.documentElement.clientWidth"
    )
    _assert_untruncated_summary(summary, stored_maria_summary)
    _assert_summary_has_no_visible_occlusion(summary)

    page.get_by_test_id("expert-back-link").click(trial=True)
    context_rail.get_by_test_id("expert-playbook-6101").click(trial=True)


def _open_maria_detail(page: Page, live_server_url: str) -> Locator:
    """Open the real expert view and settle its typography before measuring.

    :param page: Existing Chromium page.
    :param live_server_url: Real server origin. Example: http://localhost:8081.
    :return: The visible public contribution paragraph locator.
    :raises AssertionError: The real detail route or identity is unavailable.
    """
    response = page.goto(f"{live_server_url}{MARIA_DETAIL_PATH}")
    assert response is not None and response.ok
    expect(page.get_by_test_id("expert-name")).to_have_text("Maria Rodriguez")
    page.evaluate("document.fonts.ready")
    return page.get_by_test_id("expert-contribution-summary")


def _assert_untruncated_summary(summary: Locator, stored_text: str) -> None:
    """Require the entire persisted paragraph and room for all its line boxes.

    :param summary: Public contribution paragraph locator.
    :param stored_text: Full text of the persisted profile summary.
    :return: None when all text fits in the visible paragraph.
    :raises AssertionError: Text is missing, clamped, styled to clip or extends past the paragraph.
    """
    expect(summary).to_be_visible()
    assert stored_text and summary.inner_text() == stored_text
    expect(summary).to_have_css("overflow-x", "visible")
    expect(summary).to_have_css("overflow-y", "visible")
    assert summary.evaluate("""element => {
            const style = getComputedStyle(element);
            return style.textOverflow === 'clip' &&
                ['', 'none'].includes(style.getPropertyValue('line-clamp')) &&
                style.webkitLineClamp === 'none';
        }"""), "Public prose has computed ellipsis or line clamping"
    assert summary.evaluate(
        """(element, tolerance) => {
            const range = document.createRange();
            range.selectNodeContents(element);
            const bounds = element.getBoundingClientRect();
            return Array.from(range.getClientRects()).every(line =>
                line.left >= bounds.left - tolerance && line.right <= bounds.right + tolerance &&
                line.top >= bounds.top - tolerance && line.bottom <= bounds.bottom + tolerance
            );
        }""",
        LAYOUT_TOLERANCE_PX,
    ), "Public prose has line boxes extending past the paragraph"


def _assert_read_context_geometry(read: Locator, rail: Locator, width: int) -> None:
    """Check the reading order and measured Bootstrap 8+4 geometry.

    :param read: Primary reading column locator.
    :param rail: Supplementary context rail locator.
    :param width: CSS viewport width. Example: 768.
    :return: None when the visible layout follows the recipe.
    :raises AssertionError: Wrong reading order, proportions, or stacking.
    """
    assert read.evaluate("""element => Boolean(element.compareDocumentPosition(
            document.querySelector('[data-testid="expert-context-rail"]')
        ) & Node.DOCUMENT_POSITION_FOLLOWING)""")
    read_box = read.bounding_box()
    rail_box = rail.bounding_box()
    assert read_box is not None and rail_box is not None
    if width < BOOTSTRAP_MD_WIDTH:
        assert rail_box["x"] == pytest.approx(read_box["x"], abs=LAYOUT_TOLERANCE_PX)
        assert rail_box["width"] == pytest.approx(
            read_box["width"], abs=LAYOUT_TOLERANCE_PX
        )
        assert rail_box["y"] >= read_box["y"] + read_box["height"]
    else:
        assert rail_box["y"] == pytest.approx(read_box["y"], abs=LAYOUT_TOLERANCE_PX)
        assert rail_box["x"] == pytest.approx(
            read_box["x"] + read_box["width"], abs=LAYOUT_TOLERANCE_PX
        )
        assert read_box["width"] == pytest.approx(
            2 * rail_box["width"], abs=LAYOUT_TOLERANCE_PX
        )


def _assert_summary_has_no_visible_occlusion(summary: Locator) -> None:
    """Hit-test text lines in view to detect shell controls covering the prose.

    :param summary: Settled visible paragraph on the expert detail page.
    :return: None when the visible lines remain unobstructed.
    :raises AssertionError: A paragraph line is covered by another element.
    """
    covered = summary.evaluate("""element => {
            const range = document.createRange();
            range.selectNodeContents(element);
            const covered = [];
            for (const line of range.getClientRects()) {
                const y = (line.top + line.bottom) / 2;
                if (y < 0 || y >= innerHeight) continue;
                for (const x of [line.left + 1, (line.left + line.right) / 2, line.right - 1]) {
                    const top = document.elementFromPoint(x, y);
                    if (!element.contains(top)) {
                        covered.push({x, y, line: line.toJSON(),
                            covering: top?.getAttribute('aria-label') || top?.tagName,
                            coveringBox: top?.getBoundingClientRect().toJSON()});
                    }
                }
            }
            return covered;
        }""")
    assert not covered, f"Public contribution text is obscured: {covered}"
