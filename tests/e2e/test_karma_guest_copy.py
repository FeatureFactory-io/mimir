"""Actual anonymous clipboard and zero-receipt certification."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from http import HTTPStatus
from types import MappingProxyType
from urllib.parse import urlsplit

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.db.models import Sum
from django.urls import reverse
from playwright.sync_api import BrowserContext, Page, Request, expect
from pytest import FixtureRequest

from methodology.models import ExpertProfile, KarmaAward
from methodology.services.copy_prompt_service import CopyPromptService
from tests.support.experts_data import CedarDataset

_ACTIVITY_ID = 6203
_MIKE_USERNAME = "mchen"
_MIKE_BASELINE_POINTS = 12_450
_CLIPBOARD_MARKER = "Cedar guest clipboard before Copy Prompt"
_RICH_GUIDANCE = (
    "\n\n# Prepare the résumé — 京都\n\n"
    "- Preserve **all** words, ampersands & brackets <draft>.\n"
    "- Keep the literal `</textarea>` and `&lt;` in this guidance.\n"
    "- Use curly quotes ‘like these’ and Unicode ✅.\n\n"
    "```text\n    preserve indentation and internal  spacing\n```\n\n"
    "Final line for complete clipboard retrieval.\n\t"
)
_DOMAIN_MODELS = (User, ExpertProfile, KarmaAward, Session)
_DomainSnapshot = Mapping[str, tuple[tuple[object, ...], ...]]


@dataclass(frozen=True)
class GuestCopyCase:
    """Immutable expected values captured before starting the browser page."""

    activity_path: str
    receipt_path: str
    expected_prompt: str = field(repr=False)
    expected_guidance: str = field(repr=False)
    domain_rows: _DomainSnapshot = field(repr=False)
    mike_id: int


@pytest.fixture(
    params=[
        pytest.param(None, id="empty"),
        pytest.param("\n", id="rich-lf"),
        pytest.param("\r\n", id="rich-crlf"),
        pytest.param("\r", id="rich-lone-cr"),
    ]
)
def guest_copy_case(
    request: FixtureRequest, transactional_db: None, cedar_dataset: CedarDataset
) -> GuestCopyCase:
    """Prepare guidance in the owned test DB before snapshotting guest state.

    :param request: Parameterized case. Example: CRLF for browser-authored Markdown.
    :param transactional_db: Existing real test DB fixture. Example: isolated SQLite.
    :param cedar_dataset: Fresh Cedar dataset imported into the live server test DB.
    :return: Frozen activity 6203 case with full prompt and pre-copy DB state.
    :raises AssertionError: If the activity is ineligible or Mike lacks 12,450 points.
    """
    activity = cedar_dataset.activities_by_pk[_ACTIVITY_ID]
    mike = cedar_dataset.users_by_username[_MIKE_USERNAME]
    playbook = activity.workflow.playbook
    assert playbook.author_id == mike.pk
    assert (playbook.visibility, playbook.status) == ("public", "released")
    assert activity.guidance == ""
    newline: str | None = request.param
    if newline is not None:
        activity.guidance = _RICH_GUIDANCE.replace("\n", newline)
        activity.save(update_fields=["guidance"])
        activity.refresh_from_db(fields=["guidance"])
        assert activity.guidance == _RICH_GUIDANCE.replace("\n", newline)
    assert not User.objects.filter(username__iexact="bob").exists()
    assert mike.karma_awards.aggregate(points=Sum("points"))["points"] == (
        _MIKE_BASELINE_POINTS
    )
    prompt = CopyPromptService.build_activity_prompt(activity)
    assert prompt and prompt != _CLIPBOARD_MARKER
    return GuestCopyCase(
        activity_path=reverse(
            "activity_detail", args=(playbook.pk, activity.workflow_id, activity.pk)
        ),
        receipt_path=reverse("karma_copy_receipt"),
        expected_prompt=prompt,
        expected_guidance="" if newline is None else _RICH_GUIDANCE.strip(),
        domain_rows=_guest_domain_snapshot(),
        mike_id=mike.pk,
    )


@pytest.fixture
def guest_copy_page(request: FixtureRequest, guest_copy_case: GuestCopyCase) -> Page:
    """Request the existing page only after baseline and prompt preparation.

    :param request: Pytest request. Example: getfixturevalue("page").
    :param guest_copy_case: Already prepared real baseline. Example: activity 6203.
    :return: The existing function-scoped page.
    :raises pytest.FixtureLookupError: If the existing page fixture is unavailable.
    """
    return request.getfixturevalue("page")


@pytest.mark.django_db(transaction=True)
def test_guest_copy_with_public_activity_copies_full_prompt_without_receipt_or_awards(
    guest_copy_case: GuestCopyCase,
    guest_copy_page: Page,
    context: BrowserContext,
    live_server_url: str,
) -> None:
    """Certify every KARMA-COPY-02 clause using real clipboard and network.

    :param guest_copy_case: Immutable real baseline. Example: activity 6203.
    :param guest_copy_page: Existing fresh anonymous page. Example: no login cookies.
    :param context: Existing context. Example: explicit clipboard-read/write grants.
    :param live_server_url: Existing live-server origin. Example: http://localhost:port.
    :return: None after full clipboard equality, zero receipts and unchanged DB.
    :raises AssertionError: If copying fails, receipt occurs or accounts/awards change.
    """
    page = guest_copy_page
    assert context.cookies() == []
    context.grant_permissions(
        ["clipboard-read", "clipboard-write"], origin=live_server_url
    )
    observed_requests = _open_guest_activity(page, live_server_url, guest_copy_case)
    copied_prompt = _copy_and_await_feedback(page)
    page.wait_for_load_state("networkidle")
    receipt_requests = [
        request.method
        for request in observed_requests
        if urlsplit(request.url).path.rstrip("/")
        == guest_copy_case.receipt_path.rstrip("/")
    ]
    assert receipt_requests == []
    _assert_guest_domain_unchanged(guest_copy_case, context)
    expected_prompt = guest_copy_case.expected_prompt
    if copied_prompt != expected_prompt:
        pytest.fail(
            f"Native clipboard ({len(copied_prompt.encode())} bytes) differs from "
            f"the full service prompt ({len(expected_prompt.encode())} bytes)."
        )
    assert copied_prompt.partition("\n\n")[2] == guest_copy_case.expected_guidance


def _open_guest_activity(page: Page, origin: str, case: GuestCopyCase) -> list[Request]:
    """Navigate as a guest while collecting requests through the copy action.

    :param page: Fresh anonymous page from the existing fixture.
    :param origin: Live server origin. Example: http://localhost:port.
    :param case: Baseline with the exact path to activity 6203.
    :return: Live request list populated from before navigation onward.
    :raises AssertionError: If the guest activity is unavailable or editable.
    """
    observed_requests: list[Request] = []

    def observe_request(request: Request) -> None:
        """Append the actual browser request to the ongoing observation.

        :param request: Observed request. Example: activity detail GET.
        :return: None after the request is recorded.
        """
        observed_requests.append(request)

    page.on("request", observe_request)
    response = page.goto(f"{origin}{case.activity_path}")
    assert response is not None and response.status == HTTPStatus.OK
    assert urlsplit(page.url).path == case.activity_path
    assert response.request in observed_requests
    expect(page.get_by_test_id("guest-auth-banner")).to_be_visible()
    expect(page.get_by_test_id("edit-btn")).to_have_count(0)
    page.evaluate("() => document.fonts.ready.then(() => true)")
    return observed_requests


def _copy_and_await_feedback(page: Page) -> str:
    """Click the real action and observe the native clipboard and toast lifecycle.

    :param page: Actual anonymous activity detail. Example: activity 6203.
    :return: Native clipboard text after the success toast auto-dismisses.
    :raises AssertionError: If copying or the user-visible feedback differs.
    """
    toast = page.get_by_test_id("copy-prompt-toast")
    expect(toast).to_be_hidden()
    # A different value rules out a pass from a previously populated clipboard.
    page.evaluate("text => navigator.clipboard.writeText(text)", _CLIPBOARD_MARKER)
    assert page.evaluate("() => navigator.clipboard.readText()") == _CLIPBOARD_MARKER
    page.get_by_test_id("copy-prompt-btn").click()
    expect(toast).to_be_visible()
    expect(toast).to_have_text("Prompt copied to clipboard")
    clipboard_text: str = page.evaluate("() => navigator.clipboard.readText()")
    expect(page.get_by_test_id("copy-prompt-error-toast")).to_be_hidden()
    earned = page.get_by_test_id("alert-message").filter(has_text="You earned")
    expect(earned).to_have_count(0)
    expect(toast).to_be_hidden()
    return clipboard_text


def _assert_guest_domain_unchanged(
    case: GuestCopyCase, context: BrowserContext
) -> None:
    """Require exact account, profile, ledger, and session preservation.

    :param case: Captured baseline. Example: Mike's total of 12,450.
    :param context: Fresh browser context for the guest activity copy.
    :return: None once all domain assertions pass.
    :raises AssertionError: If an award or guest account/session is created.
    """
    assert all(
        cookie["name"] != settings.SESSION_COOKIE_NAME for cookie in context.cookies()
    )
    current = _guest_domain_snapshot()
    changed_tables = [
        name for name, rows in case.domain_rows.items() if current[name] != rows
    ]
    assert not changed_tables, "Guest copy changed domain rows."
    assert not User.objects.filter(username__iexact="bob").exists()
    points = KarmaAward.objects.filter(recipient_id=case.mike_id).aggregate(
        points=Sum("points")
    )
    assert points["points"] == _MIKE_BASELINE_POINTS


def _guest_domain_snapshot() -> _DomainSnapshot:
    """Read all persisted fields in deterministic order.

    :return: Immutable table-to-rows mapping. Example: an empty Session table.
    """
    return MappingProxyType(
        {
            model.__name__: tuple(model.objects.order_by("pk").values_list())
            for model in _DOMAIN_MODELS
        }
    )
