from __future__ import annotations

"""Actual browser navigation, reload and history proof for EXPERTS-LIST-02."""
import pytest
from playwright.sync_api import Page

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]


def test_category_navigation_with_reload_and_history_preserves_query(
    page: Page, live_server_url: str
) -> None:
    """Prove category links retain Design through browser reload and history.

    :param page: Existing isolated browser page. Example: Chromium page.
    :param live_server_url: Existing real Django server URL.
        Example: "http://localhost:51327".
    :return: None. Example: actual Design URL and ARIA state verified.
    :raises AssertionError: If links, navigation, reload or history lose Design.
    :raises NotImplementedError: Until BPE adds the browser assertions.
    """
    raise NotImplementedError
