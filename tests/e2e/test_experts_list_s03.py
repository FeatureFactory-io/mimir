"""Actual browser order proof; reused by broader Cedar certification."""

from __future__ import annotations

from typing import Any
import pytest
from playwright.sync_api import Page
from tests.support.experts_data import CedarBaseline

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.e2e]


def test_experts_list_with_design_browser_preserves_rank_order(
    page: Page, live_server_url: str, cedar_baseline: CedarBaseline
) -> None:
    """Open Design, assert five ordered cards, and follow Development.

    :param page: Existing real Playwright page fixture. Example: Chromium Page.
    :param live_server_url: Runner-owned Django server. Example: http://localhost:8000.
    :param cedar_baseline: Real transactional dataset. Example: CedarBaseline({}, {}, {}).
    :return: None. Example: None.
    :raises AssertionError: If visible order, boundaries or category switch fails.
    """
    raise NotImplementedError()
