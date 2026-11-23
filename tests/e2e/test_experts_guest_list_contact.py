from __future__ import annotations

from typing import Literal
import pytest
from playwright.sync_api import Page
from tests.support.experts_data import CedarDataset


@pytest.fixture
def cedar_guest_browser_dataset(transactional_db: None) -> CedarDataset:
    """Load Cedar into the real browser-test database before page interaction.

    :param transactional_db: Function-isolated database access. Example: live-server-visible committed rows.
    :return: CedarDataset from the shared baseline loader; example: real Maria and Elena users.
    :raises ValueError: If the baseline data is invalid.
    """
    raise NotImplementedError()


@pytest.mark.e2e
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
@pytest.mark.parametrize("activation", ["hover", "keyboard"])
def test_experts_reach_02_with_guest_activation_explains_restriction(
    cedar_guest_browser_dataset: CedarDataset,
    page: Page,
    live_server_url: str,
    viewport: tuple[int, int],
    activation: Literal["hover", "keyboard"],
) -> None:
    """Certify full EXPERTS-REACH-02 on production UI for one viewport and activation.

    :param cedar_guest_browser_dataset: Real fixture. Example: Maria appears on Design list.
    :param page: Existing fresh anonymous page fixture. Example: empty cookies/storage.
    :param live_server_url: Function-scoped server origin. Example: http://localhost:49152.
    :param viewport: Required IA dimensions. Example: (390, 844).
    :param activation: Actual tooltip interaction. Example: "hover".
    :return: None when route, disabled contact, email privacy, actual explanation, focus/geometry and profile availability all pass.
    :raises AssertionError: If any exact acceptance assertion fails; never click a mailto or send email.
    """
    raise NotImplementedError()
