from __future__ import annotations

import pytest
from playwright.sync_api import BrowserContext, Page


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_s28_browser_with_successful_copy_updates_score_and_preserves_paragraph(
    page: Page, context: BrowserContext, live_server_url: str
) -> None:
    """Copy full actual prompt, await receipt and reload all relevant displays.
    :param page: Real Chromium page. Example: Maria's authenticated session.
    :param context: Clipboard-enabled context. Example: live-server origin grants.
    :param live_server_url: Function server URL. Example: http://localhost:50123.
    :return: None. Example: clipboard exact; totals live; summary state unchanged.
    :raises AssertionError: For clipboard, receipt, display or persistence mismatch.
    """
    raise NotImplementedError()
