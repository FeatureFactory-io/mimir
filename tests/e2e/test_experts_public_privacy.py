from __future__ import annotations

import pytest
from playwright.sync_api import Page


@pytest.mark.django_db(transaction=True)
def test_public_detail_with_guest_browser_omits_private_markup(
    page: Page, live_server_url: str
) -> None:
    """Certify actual production guest DOM using real committed test rows.

    :param page: Existing isolated Playwright page, e.g. fresh guest context.
    :param live_server_url: Existing function-scoped server, e.g. localhost URL.
    :return: None; public evidence is visible and sensitive markup absent.
    :raises AssertionError: If HTTP status, DOM privacy or evidence is wrong.
    """
    raise NotImplementedError()
