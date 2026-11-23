from __future__ import annotations

from typing import Literal
from playwright.sync_api import Locator, Page


def guest_contact_wrapper(page: Page, container_test_id: str | None) -> Locator:
    """Locate the guest wrapper with semantic test hooks and fail on ambiguity.

    :param page: Actual browser page. Example: production Design list.
    :param container_test_id: Card scope or document root. Example: "experts-card-mrodriguez"; None for detail.
    :return: Unique wrapper Locator. Example: scoped experts-reach-out-guest-tooltip.
    :raises AssertionError: If the expected wrapper is absent or ambiguous.
    """
    raise NotImplementedError()


def activate_guest_tooltip(
    page: Page, wrapper: Locator, activation: Literal["hover", "keyboard"]
) -> Locator:
    """Reveal the actual Bootstrap tooltip by pointer or bounded Tab traversal.

    :param page: Actual page. Example: fresh anonymous Chromium context.
    :param wrapper: Unique focusable contact wrapper. Example: Maria's list wrapper.
    :param activation: Real interaction. Example: "keyboard" uses Tab, never programmatic focus.
    :return: Visible page-level tooltip Locator with exact restriction text.
    :raises AssertionError: If focus cannot reach the wrapper or its visible explanation differs.
    :raises ValueError: If activation is unsupported.
    """
    raise NotImplementedError()


def assert_guest_tooltip_in_viewport(
    page: Page, tooltip: Locator, viewport: tuple[int, int]
) -> None:
    """Check tooltip geometry separately from document overflow.

    :param page: Actual page after tooltip activation. Example: scrolled Maria card.
    :param tooltip: Visible rendered tooltip. Example: Bootstrap role=tooltip portal.
    :param viewport: CSS pixel dimensions. Example: (360, 800).
    :return: None when all tooltip edges are in bounds and document horizontal overflow is absent.
    :raises AssertionError: For missing geometry, clipping or horizontal page overflow.
    """
    raise NotImplementedError()
