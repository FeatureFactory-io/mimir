from __future__ import annotations

"""S13 browser certification using the existing isolated fixture lifecycle."""
import pytest
from playwright.sync_api import Page
from tests.support.experts_data import load_cedar_baseline


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_own_profile_with_anonymous_browser_navigation_shows_login_only(
    page: Page, live_server_url: str
) -> None:
    """Prove a fresh anonymous browser cannot display own-profile controls.

    :param page: Existing function-scoped page. Example: fresh Chromium page.
    :param live_server_url: Real test server origin. Example: http://localhost:8001.
    :return: None. Example: None after browser assertions pass.
    :raises AssertionError: For incorrect redirect or exposed private controls.
    """
    raise NotImplementedError()
