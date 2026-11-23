from __future__ import annotations

"""Actual desktop and offcanvas sidebar certification."""
import pytest
from playwright.sync_api import Page


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("viewport", [(1280, 720), (390, 844)])
def test_sidebar_with_real_navigation_opens_experts(
    page: Page, live_server_url: str, viewport: tuple[int, int]
) -> None:
    """Follow the real Experts anchor through the existing responsive shell.

    :param page: Existing fresh Playwright page. Example: Chromium page.
    :param live_server_url: Existing real server URL. Example: http://localhost:8081.
    :param viewport: Exact viewport dimensions. Example: (390, 844).
    :return: None. Example: None.
    :raises AssertionError: If actual navigation or accessible current state fails.
    """
    raise NotImplementedError()
