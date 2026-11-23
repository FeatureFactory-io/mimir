from __future__ import annotations

"""Browser certification against the real Experts route."""
import pytest
from playwright.sync_api import Page

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]


def test_experts_list_with_tie03_browser_preserves_dom_and_visible_rank(
    page: Page, live_server_url: str
) -> None:
    """Certify tied contributors in real browser order before and after reload.

    :param page: Existing isolated browser page. Example: Chromium Page.
    :param live_server_url: Existing Django live server. Example: "http://localhost:8000".
    :return: None. Example: Alina is visibly rank 1 and Sofia rank 2.
    :raises AssertionError: If browser DOM, geometry, totals or reload order differs.
    :raises NotImplementedError: Until the approved browser proof is implemented.
    """
    raise NotImplementedError()
