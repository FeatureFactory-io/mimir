from __future__ import annotations

import pytest
from playwright.sync_api import Page


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("width", "height"),
    [
        (1280, 800),
        (1920, 1080),
        (1512, 982),
        (768, 1024),
        (1024, 768),
        (390, 844),
        (360, 800),
    ],
)
def test_profile_sources_with_required_viewports_remain_reconciled(
    page: Page, live_server_url: str, width: int, height: int
) -> None:
    """Certify real authenticated profile rows at every required viewport.

    :param page: Real Chromium page. Example: fresh isolated browser context.
    :param live_server_url: Function-scoped Django URL. Example: "http://localhost:50123".
    :param width: Required CSS viewport width. Example: 360.
    :param height: Required CSS viewport height. Example: 800.
    :return: None. Example: four readable rows reconcile to 8200 without overflow.
    :raises AssertionError: If navigation, values, readability or geometry differs.
    """
    raise NotImplementedError()
