from __future__ import annotations

import pytest
from playwright.sync_api import Page


@pytest.mark.django_db(transaction=True)
def test_later_major_with_browser_release_omits_second_award_message(
    page: Page, live_server_url: str
) -> None:
    """Release twice using real modal controls and inspect fresh Product output.

    :param page: Existing fresh browser fixture. Example: Chromium page.
    :param live_server_url: Existing function-scoped origin. Example: localhost:8123.
    :return: None. Example: v1.0 then v2.0, Nora=5000, second earned message absent.
    :raises AssertionError: If UI, actual versions, message or one-row ledger fails.
    """
    raise NotImplementedError()
