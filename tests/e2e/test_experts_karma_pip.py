from __future__ import annotations

import pytest
from playwright.sync_api import Page


@pytest.mark.django_db(transaction=True)
def test_admin_browser_with_major_add_finalization_awards_maria(
    page: Page, live_server_url: str
) -> None:
    """Certify the existing administrator decision flow reaches the real award hook.

    :param page: Existing Playwright page fixture. Example: staff Mike browser session.
    :param live_server_url: Existing live server origin. Example: "http://localhost:54321".
    :return: None. Example: confirmed ADD publishes 3.0 and credits Maria once.
    :raises AssertionError: If real navigation, confirmation or persisted effects differ.
    """
    raise NotImplementedError()
