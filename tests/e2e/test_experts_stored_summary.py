from __future__ import annotations

from collections.abc import Mapping
import pytest
from playwright.sync_api import Locator, Page


@pytest.fixture
def cedar_summary(transactional_db: None) -> Mapping[str, str]:
    """Load real Cedar before navigation through the existing browser fixtures.

    :param transactional_db: Committed isolated test DB access. Example: None.
    :return: Login/source mapping. Example: {"username": "mrodriguez", "summary": "..."}.
    :raises AssertionError: If imported stored prose is not the nine-sentence oracle.
    """
    raise NotImplementedError()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
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
def test_stored_summary_with_target_viewport_preserves_visual_contract(
    cedar_summary: Mapping[str, str],
    page: Page,
    live_server_url: str,
    viewport: tuple[int, int],
) -> None:
    """Measure real production card, own-profile and public-summary rendering.

    :param cedar_summary: Real Cedar credentials/source. Example: {"summary": "..."}.
    :param page: Existing fresh Chromium page. Example: page.
    :param live_server_url: Existing function-scoped server. Example: "http://localhost:9000".
    :param viewport: Exact IA dimensions. Example: (390, 844).
    :return: None when identical prose, clamp geometry and expansion pass.
    :raises AssertionError: For clipping, changed text, wrong ARIA or horizontal overflow.
    """
    raise NotImplementedError()


def _assert_summary_geometry(node: Locator, maximum_lines: int | None) -> None:
    """Assert actual computed layout without simulating truncation.

    :param node: Real rendered summary locator. Example: page.get_by_test_id("expert-contribution-summary").
    :param maximum_lines: Expected clamp, or full text. Example: 2, 4 or None.
    :return: None when measured heights/overflow agree within one CSS pixel.
    :raises AssertionError: If a clamp is absent, excessive or public prose is clipped.
    :raises ValueError: If a requested clamp is not 2, 4 or None.
    """
    raise NotImplementedError()
