from __future__ import annotations

"""Browser certification of the existing positive empty-evidence contract."""
import pytest
from playwright.sync_api import Page

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]


def test_expert_detail_with_positive_sam_shows_empty_evidence_in_browser(
    page: Page, live_server_url: str
) -> None:
    """Observe Sam's actual production profile after normal Elena login.

    :param page: Existing fresh browser page. Example: Chromium page.
    :param live_server_url: Existing function-scoped server. Example: http://localhost:8081.
    :return: None. Example: visible positive identity and empty evidence verified.
    :raises AssertionError: If navigation, identity, visibility or evidence is incorrect.
    """
    raise NotImplementedError()
