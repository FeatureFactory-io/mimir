from __future__ import annotations

"""Browser certification; keep separate from Django-client AT settings."""
import pytest
from playwright.sync_api import Page


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_experts_list_with_guest_browser_shows_public_cards_and_auth_actions(
    page: Page, live_server_url: str
) -> None:
    """Certify guest cards, private-control absence and keyboard auth access.

    :param page: Fresh real Page. Example: context has no authenticated cookies.
    :param live_server_url: Django live URL str. Example: http://localhost:51000.
    :return: None. Example: five visible cards and reachable auth actions.
    :raises AssertionError: Visible ranking, privacy or keyboard access fails.
    """
    raise NotImplementedError()
