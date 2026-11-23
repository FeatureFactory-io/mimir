from __future__ import annotations

import pytest
from playwright.sync_api import Page


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_experts_navigation_with_sidebar_click_opens_default_page(
    page: Page, live_server_url: str
) -> None:
    """Certify actual login and sidebar navigation to default Experts.

    :param page: Fresh Playwright page. Example: Chromium page at 1280x800.
    :param live_server_url: Real Django server URL. Example: "http://localhost:8081".
    :return: None. Example: None.
    :raises AssertionError: If navigation or rendered default state differs.
    """
    raise NotImplementedError()
