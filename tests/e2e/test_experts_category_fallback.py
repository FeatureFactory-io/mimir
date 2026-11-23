from __future__ import annotations

import pytest
from playwright.sync_api import Page
from tests.support.experts_data import CedarDataset

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]


def test_experts_list_with_unknown_category_survives_browser_refresh(
    page: Page,
    live_server_url: str,
    cedar_dataset: CedarDataset,
    viewport_size: tuple[int, int],
) -> None:
    """Certify the recovered production state at each of the seven IA viewports.

    :param page: Existing fresh browser page. Example: Chromium Page.
    :param live_server_url: Actual Django server origin. Example: "http://localhost:8081".
    :param cedar_dataset: Shared function-scoped ORM baseline. Example: Elena and Mike.
    :param viewport_size: Section H viewport row. Example: (390, 844).
    :return: None. Example: successful browser assertions return None.
    :raises AssertionError: If HTTP, current state, cards, refresh or geometry fails.
    """
    raise NotImplementedError()
