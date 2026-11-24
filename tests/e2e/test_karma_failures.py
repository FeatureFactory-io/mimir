"""Native Chromium clipboard-permission failure certification."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from urllib.parse import urlsplit

import pytest
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.urls import reverse
from e2e_helpers import login
from playwright.sync_api import (
    BrowserContext,
    CDPSession,
    ConsoleMessage,
    Page,
    Request,
    expect,
)
from rest_framework.authtoken.models import Token

from methodology.models import (
    AgentInteraction,
    ExpertProfile,
    KarmaAward,
    Playbook,
    ProcessImprovementProposal,
)
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.e2e]
_ACTIVITY_ID = 6203
_CLIPBOARD_PERMISSION = "clipboard-write"
_ERROR_MESSAGE = "Could not copy to clipboard. Check browser permissions."
_READ_ONLY_MODELS = (
    User,
    Token,
    Playbook,
    ProcessImprovementProposal,
    KarmaAward,
    ExpertProfile,
    AgentInteraction,
)
DatabaseState = tuple[tuple[dict[str, object], ...], ...]


@dataclass(frozen=True)
class ClipboardDenialCase:
    """Public activity and receipt paths from the real Cedar fixture."""

    activity_path: str
    receipt_path: str


@pytest.fixture
def denial_case(cedar_dataset: CedarDataset) -> ClipboardDenialCase:
    """Resolve an actual other-author public activity before opening Playwright.

    :param cedar_dataset: Restored runner-owned Cedar database, e.g. Mike's activity.
    :return: Immutable actual production paths, e.g. activity6203 and its receipt.
    :raises AssertionError: If fixture ownership or public release state differs.
    """
    activity = cedar_dataset.activities_by_pk[_ACTIVITY_ID]
    playbook = activity.workflow.playbook
    assert playbook.author_id == cedar_dataset.users_by_username["mchen"].pk
    assert (playbook.visibility, playbook.status) == ("public", "released")
    return ClipboardDenialCase(
        reverse(
            "activity_detail", args=(playbook.pk, activity.workflow_id, activity.pk)
        ),
        reverse("karma_copy_receipt"),
    )


@pytest.fixture
def denial_page(
    request: pytest.FixtureRequest, denial_case: ClipboardDenialCase
) -> Page:
    """Request the existing isolated page after the real fixture is prepared.

    :param request: Existing pytest request, e.g. dynamic page fixture resolution.
    :param denial_case: Already resolved Cedar activity, e.g. Mike's public activity.
    :return: The unchanged function-scoped Playwright page.
    :raises pytest.FixtureLookupError: If the project's page fixture is unavailable.
    """
    return request.getfixturevalue("page")


def deny_native_clipboard(
    context: BrowserContext, page: Page, origin: str
) -> CDPSession:
    """Deny native permissions only in the actual current Chromium context.

    :param context: Existing isolated Chromium context, e.g. the page's own context.
    :param page: Real page used to obtain its nonempty browserContextId.
    :param origin: Current live-server origin, e.g. http://localhost:54321.
    :return: Active CDP session retaining native denial until its caller detaches it.
    :raises ValueError: For a different context or a nonmatching origin.
    :raises AssertionError: If the native context or permission cannot be verified.
    """
    target = urlsplit(page.url)
    if page.context is not context or origin != f"{target.scheme}://{target.netloc}":
        raise ValueError("Native denial requires the page's own context and origin.")
    session = context.new_cdp_session(page)
    try:
        context_id = session.send("Target.getTargetInfo")["targetInfo"].get(
            "browserContextId"
        )
        assert isinstance(context_id, str) and context_id
        session.send(
            "Browser.setPermission",
            {
                "permission": {"name": _CLIPBOARD_PERMISSION},
                "setting": "denied",
                "origin": origin,
                "browserContextId": context_id,
            },
        )
        _assert_permission_denied(page)
        return session
    except Exception:
        session.detach()
        raise


def test_copy_prompt_with_native_clipboard_denial_creates_no_receipt_or_awards(
    denial_case: ClipboardDenialCase,
    denial_page: Page,
    context: BrowserContext,
    live_server_url: str,
    mailoutbox: list[EmailMessage],
) -> None:
    """Click the actual copy control under native denial without crediting anyone.

    :param denial_case: Restored real public activity and receipt route.
    :param denial_page: Existing isolated page requested after fixture preparation.
    :param context: The unchanged isolated Chromium context fixture.
    :param live_server_url: Function-scoped actual Django server origin.
    :param mailoutbox: Existing local mail capture, e.g. no copied-prompt mail.
    :return: None after native error, feedback, zero receipts and unchanged state.
    :raises AssertionError: If copying succeeds or produces persisted/mail effects.
    """
    page = denial_page
    login(page, live_server_url, "mrodriguez", CEDAR_PASSWORD)
    response = page.goto(f"{live_server_url}{denial_case.activity_path}")
    assert response is not None and response.status == 200
    assert response.request.redirected_from is None
    session = deny_native_clipboard(context, page, live_server_url)
    try:
        before, mail_before = _database_state(), tuple(mailoutbox)
        requests, errors = _observe_copy_failure(page)
        page.get_by_test_id("copy-prompt-btn").click()
        _assert_native_error_feedback(page, errors)
        page.wait_for_load_state("networkidle")
        _assert_permission_denied(page)
        assert not any(path == denial_case.receipt_path for _, path in requests)
        _assert_state_unchanged(before, mail_before, mailoutbox)
    finally:
        session.detach()


def _observe_copy_failure(page: Page) -> tuple[list[tuple[str, str]], list[str]]:
    """Observe genuine requests and only the application's clipboard error name.

    :param page: Authenticated activity page with native permission denied.
    :return: Live request-path and DOMException-name lists populated by the click.
    :raises RuntimeError: Unexpected Playwright observation failures propagate.
    """
    requests: list[tuple[str, str]] = []
    errors: list[str] = []
    page.on("request", partial(_record_request_path, requests))
    page.on("console", partial(_record_clipboard_error, errors))
    return requests, errors


def _record_request_path(paths: list[tuple[str, str]], request: Request) -> None:
    """Retain method/path only, excluding payloads, tokens and query values.

    :param paths: Actual live request list, e.g. no receipt request after denial.
    :param request: Real emitted browser request.
    :return: None after appending its method and parsed path.
    :raises ValueError: If URL parsing rejects the request URL.
    """
    paths.append((request.method, urlsplit(request.url).path))


def _record_clipboard_error(errors: list[str], message: ConsoleMessage) -> None:
    """Read the real DOMException name from the handled application warning.

    :param errors: Actual native names, e.g. NotAllowedError.
    :param message: Browser console message from the original copy failure handler.
    :return: None; unrelated messages and arbitrary error content are not retained.
    :raises RuntimeError: Unexpected browser-handle observation failures propagate.
    """
    if message.type != "warning" or not message.text.startswith(
        "[copy-prompt] clipboard failed"
    ):
        return
    if message.args:
        name = message.args[-1].evaluate("error => error && error.name")
        if isinstance(name, str):
            errors.append(name)


def _assert_native_error_feedback(page: Page, errors: list[str]) -> None:
    """Require the native exception and actual error-only application feedback.

    :param page: Existing activity page after its real Copy Prompt click.
    :param errors: Names read from actual console DOMException handles.
    :return: None when error toast is visible and success feedback remains hidden.
    :raises AssertionError: For a missing native rejection or false success state.
    """
    error = page.get_by_test_id("copy-prompt-error-toast")
    expect(error).to_be_visible()
    expect(error).to_have_css("opacity", "1")
    expect(error).to_be_in_viewport()
    expect(error).to_contain_text(_ERROR_MESSAGE)
    expect(page.get_by_test_id("copy-prompt-toast")).to_be_hidden()
    expect(page.locator(".mm-copy-prompt-success-icon")).to_be_hidden()
    assert "NotAllowedError" in errors, "No native clipboard rejection was observed."


def _database_state() -> DatabaseState:
    """Snapshot every field of all rows in the seven sensitive domain models.

    :return: Ordered complete snapshots, e.g. original global award PK/timestamps.
    :raises RuntimeError: Actual ORM failures propagate.
    """
    return tuple(
        tuple(model.objects.order_by("pk").values()) for model in _READ_ONLY_MODELS
    )


def _assert_state_unchanged(
    before: DatabaseState,
    mail_before: tuple[EmailMessage, ...],
    mailoutbox: list[EmailMessage],
) -> None:
    """Reject any state/mail change without printing private row values.

    :param before: Full snapshots after genuine login and before clipboard attempt.
    :param mail_before: Actual local mail messages before the click.
    :param mailoutbox: The same actual mail capture after native failure settles.
    :return: None if all rows and mail remain unchanged.
    :raises AssertionError: If any state/mail effect appears after denied copying.
    """
    if _database_state() != before:
        raise AssertionError("Native clipboard denial changed a domain model.")
    if tuple(mailoutbox) != mail_before:
        raise AssertionError("Native clipboard denial changed the local outbox.")


def _assert_permission_denied(page: Page) -> None:
    """Read the native browser permission without replacing its API.

    :param page: Actual page in the active overridden Chromium context.
    :return: None when clipboard-write remains natively denied.
    :raises AssertionError: If the native permission is prompt or granted.
    """
    state = page.evaluate(
        "name => navigator.permissions.query({name}).then(permission => permission.state)",
        _CLIPBOARD_PERMISSION,
    )
    assert state == "denied", "Chromium did not enforce native clipboard denial."
