from __future__ import annotations

"""Browser certification using existing page and live_server_url fixtures."""
import pytest
from playwright.sync_api import Page

VIEWPORTS = (
    (1280, 800),
    (1920, 1080),
    (1512, 982),
    (768, 1024),
    (1024, 768),
    (390, 844),
    (360, 800),
)


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(("width", "height"), VIEWPORTS)
@pytest.mark.parametrize(
    "variant", ("normal", "long_identity_and_prose", "missing_summary")
)
def test_experts_cards_with_required_viewports_keep_actions_readable(
    page: Page, live_server_url: str, width: int, height: int, variant: str
) -> None:
    """Certify ranking, readability, two-line hint geometry and reachable actions.

    :param page: Fresh browser page. Example: Chromium page.
    :param live_server_url: Existing real server fixture. Example: "http://localhost:8081".
    :param width: CSS viewport width. Example: 360.
    :param height: CSS viewport height. Example: 800.
    :param variant: Real-data display state. Example: "missing_summary".
    :return: None. Example: screenshot and geometry assertions recorded.
    :raises AssertionError: If clipping, overlap, overflow or inaccessible actions occur.
    """
    raise NotImplementedError()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_experts_card_with_view_profile_opens_full_evidence(
    page: Page, live_server_url: str
) -> None:
    """Follow Maria's actual profile action to the complete stored paragraph.

    :param page: Fresh browser page. Example: authenticated Elena page.
    :param live_server_url: Existing server fixture. Example: "http://localhost:8081".
    :return: None. Example: S17 route and full public prose verified.
    :raises AssertionError: If navigation or complete evidence fails.
    """
    raise NotImplementedError()
