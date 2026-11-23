from __future__ import annotations

"""S19 real browser evidence navigation."""
import pytest
from playwright.sync_api import Page
from tests.support.experts_data import CedarDataset, load_cedar_baseline


@pytest.fixture
def s19_browser_dataset(transactional_db: None) -> CedarDataset:
    """Prepare real Cedar objects before the browser begins navigation.

    :param transactional_db: Shared live-server test DB. Example: None.
    :return: Cedar dataset. Example: dataset.playbooks_by_pk[6101].
    :raises ValueError: If Cedar source data is invalid.
    """
    raise NotImplementedError()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("username", ["esvensson", None])
def test_public_evidence_with_real_browser_navigation_reaches_cedar_workflow(
    page: Page,
    live_server_url: str,
    s19_browser_dataset: CedarDataset,
    username: str | None,
) -> None:
    """Click existing evidence/workflow links and inspect readable activities.

    :param page: Existing fresh Playwright page. Example: page.
    :param live_server_url: Existing function-scoped server. Example: "http://localhost:8000".
    :param s19_browser_dataset: Prepared Cedar graph. Example: playbook 6101.
    :param username: Authenticated actor or guest. Example: None.
    :return: None. Example: None after real document/status/visibility checks.
    :raises AssertionError: If links, destination, status or readable evidence differ.
    """
    raise NotImplementedError()
