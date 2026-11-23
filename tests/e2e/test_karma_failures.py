from __future__ import annotations

"""Native Chromium clipboard-permission failure certification."""
import pytest
from playwright.sync_api import BrowserContext, Page

pytestmark = pytest.mark.django_db(transaction=True)


def deny_native_clipboard(context: BrowserContext, page: Page, origin: str) -> None:
    """Deny permissions through CDP for this actual browser context.

    :param context: Existing isolated Chromium context.
    :param page: Real page used to obtain its browserContextId.
    :param origin: Live-server origin. Example: http://localhost:54321.
    :return: None. Example: native clipboard-write permission is denied.
    :raises AssertionError: Context ID or native denial cannot be verified.
    """
    raise NotImplementedError()


def test_copy_prompt_with_native_clipboard_denial_creates_no_receipt_or_awards(
    context: BrowserContext, page: Page, live_server_url: str
) -> None:
    """Click actual Copy Prompt after native denial and verify no award.

    :param context: Existing isolated context fixture.
    :param page: Existing real page fixture.
    :param live_server_url: Function-scoped Django origin.
    :return: None. Example: error toast, zero receipt requests, unchanged ledger.
    :raises AssertionError: Clipboard succeeds, receipt sends or awards change.
    """
    raise NotImplementedError()
