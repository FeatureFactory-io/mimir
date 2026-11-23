from __future__ import annotations

"""S18 browser certification using the existing E2E lifecycle."""
import pytest
from playwright.sync_api import Page


@pytest.mark.parametrize(
    "viewport",
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
def test_public_score_breakdown_with_required_viewport_stays_readable(
    page: Page, live_server_url: str, transactional_db: None, viewport: tuple[int, int]
) -> None:
    """Certify actual detail geometry, legibility and reconciled numbers.

    :param page: Existing function-scoped page. Example: Chromium Page.
    :param live_server_url: Existing live-server URL. Example: "http://localhost:8081".
    :param transactional_db: Real transactional database fixture. Example: None.
    :param viewport: IA dimensions. Example: (390, 844).
    :return: None. Example: None for visible, separated, reconciled rows.
    :raises AssertionError: If content, geometry or responsive reading order fails.
    """
    raise NotImplementedError()
