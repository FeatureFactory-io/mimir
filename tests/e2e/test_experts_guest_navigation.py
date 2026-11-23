from __future__ import annotations

"""Actual browser certification; use the existing isolated page/server fixtures."""
import pytest
from playwright.sync_api import Page


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_guest_navigation_with_real_sidebar_click_preserves_public_access(
    page: Page, live_server_url: str
) -> None:
    """Click from public shell to Experts, then inspect public Design state.

    :param page: Fresh real Page. Example: anonymous Chromium context.
    :param live_server_url: Real server URL str. Example: "http://localhost:51000".
    :return: None. Example: public navigation, banner and restricted contacts.
    :raises AssertionError: Redirect, ranking, account or contact boundary fails.
    """
    raise NotImplementedError()
