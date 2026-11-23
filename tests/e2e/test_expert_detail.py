from __future__ import annotations

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.e2e
DETAIL_VIEWPORTS = (
    (1280, 800),
    (1920, 1080),
    (1512, 982),
    (768, 1024),
    (1024, 768),
    (390, 844),
    (360, 800),
)


def test_public_detail_with_full_summary_has_no_visual_truncation(
    page: Page, live_server_url: str
) -> None:
    """Prove actual browser text and computed styles preserve the paragraph.

    :param page: Existing isolated page fixture. Example: Chromium page.
    :param live_server_url: Real Django URL. Example: http://localhost:8081.
    :return: None. Example: full stored paragraph fits without clamp or ellipsis.
    :raises AssertionError: For missing sentences or computed truncation.
    """
    raise NotImplementedError()


@pytest.mark.parametrize(("width", "height"), DETAIL_VIEWPORTS)
def test_public_detail_with_required_viewport_preserves_read_context_recipe(
    page: Page, live_server_url: str, width: int, height: int
) -> None:
    """Prove the required body/rail recipe at every IA viewport.

    :param page: Existing page fixture. Example: isolated Chromium page.
    :param live_server_url: Real server address. Example: http://localhost:8081.
    :param width: CSS viewport width. Example: 390.
    :param height: CSS viewport height. Example: 844.
    :return: None. Example: readable full paragraph, correct rail position, no overflow.
    :raises AssertionError: For clipping, overlap or incorrect reading layout.
    """
    raise NotImplementedError()
