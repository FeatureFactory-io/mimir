from __future__ import annotations

import pytest
from playwright.sync_api import Page


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_expert_detail_with_missing_or_zero_karma_subject_browser_returns_404(
    page: Page, live_server_url: str
) -> None:
    """Certify both anonymous rejection pages with the existing browser lifecycle.

    :param page: Isolated Playwright page. Example: fresh anonymous page.
    :param live_server_url: Existing server URL. Example: "http://localhost:8123".
    :return: None after both navigation statuses and safe UI assertions pass.
    :raises AssertionError: If status, generic presentation or privacy differs.
    """
    raise NotImplementedError()
