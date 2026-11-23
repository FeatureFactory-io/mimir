from __future__ import annotations

"""S26 real-browser missing-summary certification."""
import pytest
from playwright.sync_api import Page


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("viewport", [(390, 844), (1280, 800)])
def test_numeric_fallback_with_reload_shows_updated_live_counts(
    page: Page, live_server_url: str, viewport: tuple[int, int]
) -> None:
    """Verify actual navigation, missing prose and fresh numeric rendering.

    :param page: Function-scoped real browser page. Example: Chromium Page.
    :param live_server_url: Existing live-server URL. Example: http://localhost:8081.
    :param viewport: Width/height pixels. Example: (390, 844).
    :return: None. Example: None after visible 2/47 then changed count on reload.
    :raises AssertionError: If fallback is stale, unreadable or fabricates prose.
    """
    raise NotImplementedError()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_numeric_fallback_with_own_profile_shows_no_expansion_control(
    page: Page, live_server_url: str
) -> None:
    """Authenticate Mike through the real login and inspect his own profile.

    :param page: Function-scoped browser page. Example: Chromium Page.
    :param live_server_url: Existing server URL. Example: http://localhost:8081.
    :return: None. Example: None after numeric fallback and absent expansion.
    :raises AssertionError: If own profile invents summary text or expansion state.
    """
    raise NotImplementedError()
