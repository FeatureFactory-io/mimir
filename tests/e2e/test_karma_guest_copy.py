from __future__ import annotations

"""Actual anonymous clipboard and zero-receipt certification."""
from dataclasses import dataclass
import pytest
from playwright.sync_api import BrowserContext, Page
from pytest import FixtureRequest


@dataclass(frozen=True)
class GuestCopyCase:
    """Immutable expected values captured before starting the browser page."""

    activity_path: str
    receipt_path: str
    expected_prompt: str
    user_ids: tuple[int, ...]
    expert_profile_ids: tuple[int, ...]
    award_rows: tuple[tuple[object, ...], ...]
    mike_id: int


@pytest.fixture
def guest_copy_case(transactional_db: None) -> GuestCopyCase:
    """Load S03's baseline and snapshot complete expected anonymous-copy state.

    :param transactional_db: Existing real test DB fixture. Example: isolated SQLite.
    :return: Frozen case for6203, full actual prompt and pre-copy DB state.
    :raises AssertionError: If Cedar does not contain public6203 or Mike12450.
    """
    raise NotImplementedError()


@pytest.fixture
def guest_copy_page(request: FixtureRequest, guest_copy_case: GuestCopyCase) -> Page:
    """Request the existing page only after baseline and prompt preparation.

    :param request: Pytest request. Example: getfixturevalue("page").
    :param guest_copy_case: Already prepared real baseline. Example: activity6203.
    :return: Existing function-scoped page; no replacement browser lifecycle.
    :raises AssertionError: If the existing page fixture cannot be obtained.
    """
    raise NotImplementedError()


@pytest.mark.django_db(transaction=True)
def test_guest_copy_with_public_activity_copies_full_prompt_without_receipt_or_awards(
    guest_copy_case: GuestCopyCase,
    guest_copy_page: Page,
    context: BrowserContext,
    live_server_url: str,
) -> None:
    """Certify every KARMA-COPY-02 clause using real clipboard and network.

    :param guest_copy_case: Immutable real baseline. Example: Mike12450/activity6203.
    :param guest_copy_page: Existing fresh anonymous page. Example: no login cookies.
    :param context: Existing context. Example: explicit clipboard-read/write grants.
    :param live_server_url: Existing live-server origin. Example: http://localhost:port.
    :return: None after full clipboard equality, zero receipts and unchanged DB.
    :raises AssertionError: If copying fails, receipt occurs or accounts/awards change.
    """
    raise NotImplementedError()
