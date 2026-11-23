from __future__ import annotations

"""Real browser certification of public-detail guest contact."""
import pytest
from playwright.sync_api import Page

VIEWPORTS = (
    (1280, 800),
    (1920, 1080),
    (1512, 982),
    (768, 1024),
    (1024, 768),
    (390, 844),
    (360, 800),
)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("viewport", VIEWPORTS)
def test_guest_detail_with_required_viewport_keeps_tooltip_and_evidence_accessible(
    page: Page, live_server_url: str, viewport: tuple[int, int]
) -> None:
    """Certify actual hover, keyboard explanation and readable public evidence.

    :param page: Existing isolated browser page. Example: fresh anonymous Page.
    :param live_server_url: Existing real server URL. Example: http://localhost:8081.
    :param viewport: CSS width/height. Example: (360, 800).
    :return: None. Example: None after real interactions and geometry checks.
    :raises AssertionError: If tooltip, focus, geometry or evidence fails.
    """
    raise NotImplementedError()
