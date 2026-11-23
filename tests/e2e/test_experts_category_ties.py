from __future__ import annotations

import pytest
from playwright.sync_api import Page


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "variant,category", [("TIE01", "Development"), ("TIE02", "Design")]
)
def test_primary_category_with_cedar_tie_renders_correct_tab(
    page: Page, live_server_url: str, variant: str, category: str
) -> None:
    """Verify actual production list placement and badge for the ORM variant.
    :param page: Existing function-scoped real browser fixture.
    :param live_server_url: Existing isolated live-server URL.
    :param variant: Fresh TIE01 or TIE02 dataset.
    :param category: Required displayed primary category.
    :return: None.
    :raises AssertionError: Wrong placement, badge, total or mutated ledger.
    """
    raise NotImplementedError()
