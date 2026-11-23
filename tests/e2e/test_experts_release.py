from __future__ import annotations

"""Browser certification of the independently restored Nora release case."""
import pytest
from playwright.sync_api import Page


@pytest.mark.django_db(transaction=True)
def test_karma_release_01_with_browser_shows_award_and_product_order(
    page: Page, live_server_url: str
) -> None:
    """Release through the actual modal and inspect the refreshed Product list.

    Reuse login/live-server fixtures and the shared Cedar adapter. Use existing
    release-modal, release-description-input, release-confirm and alert-message
    test IDs; use S03's semantic expert-card selectors for ranking.

    :param page: Fresh real browser page. Example: Chromium page.
    :param live_server_url: Real isolated Django origin. Example: http://localhost:8123.
    :return: None when the exact award message and Alex/Nora order are visible.
    :raises AssertionError: If release controls, displayed points or ordering fail.
    """
    raise NotImplementedError()
