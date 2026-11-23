from __future__ import annotations

import re
import pytest
from playwright.sync_api import Page, expect
from e2e_helpers import login
from tests.support.experts_data import CEDAR_PASSWORD, load_cedar_baseline


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("width", "height"),
    [
        (1280, 800),
        (1920, 1080),
        (1512, 982),
        (768, 1024),
        (1024, 768),
        (390, 844),
        (360, 800),
    ],
)
def test_experts_other_with_responsive_viewport_shows_empty_state(
    page: Page, live_server_url: str, width: int, height: int
) -> None:
    """Certify the production empty category at every IA viewport.

    :param page: Existing isolated browser page. Example: pytest page fixture.
    :param live_server_url: Real Django server origin. Example: "http://localhost:8081".
    :param width: CSS viewport width. Example: 360.
    :param height: CSS viewport height. Example: 800.
    :return: None after visible text, zero cards, current tab and overflow checks.
    :raises AssertionError: If production browser behavior violates the contract.
    """
    raise NotImplementedError()
