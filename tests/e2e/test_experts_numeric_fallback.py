"""S26 real-browser missing-summary certification."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import partial
from http import HTTPStatus
from threading import get_ident, local
from typing import Any

import pytest
from django.conf import settings
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.core.signals import request_finished, request_started
from django.db import connection
from e2e_helpers import login
from playwright.sync_api import Page, expect
from rest_framework.authtoken.models import Token

from methodology.models import EventChannel, ExpertProfile, KarmaAward, Playbook
from tests.e2e.test_experts_stored_summary import _wait_for_actual_fonts
from tests.integration.test_experts_numeric_fallback import (
    _add_award,
    _assert_live_counts,
    _fingerprint,
    _public_book,
)
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
from tests.support.experts_logs import capture_experts_logs
from tests.support.experts_privacy import _assert_private_markers_absent

_MIKE = "mchen"
_LIST_PATH = "/experts/?category=development"
_DETAIL_PATH = "/experts/mchen/"
_OWN_PATH = "/auth/user/profile/"
_BASE_HINT = "2 released playbooks · 47 copies"
_CHANGED_HINT = "1 released playbook · 48 copies"
_READ_COMMANDS = {"SELECT", "BEGIN", "COMMIT", "SAVEPOINT", "RELEASE"}
_GENERATION_LOGGER = "methodology.services.contribution_summary_service"
_SETTLE_TIMEOUT_MS = 5000
_READ_MARGIN_PX = 32
_MINIMUM_HINT_FONT_PX = 14


@dataclass
class _ReadAudit:
    """Parameter-free observations of actual live-server SQL and callbacks."""

    commands: list[str] = field(default_factory=list)
    requests: list[dict[str, object]] = field(default_factory=list)
    thread: local = field(default_factory=local)


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("viewport", [(390, 844), (1280, 800)])
def test_numeric_fallback_with_reload_shows_updated_live_counts(
    page: Page,
    live_server_url: str,
    viewport: tuple[int, int],
    cedar_dataset: CedarDataset,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify actual navigation, missing prose and fresh numeric rendering.

    :param page: Function-scoped real browser page. Example: Chromium Page.
    :param live_server_url: Existing live-server URL. Example: http://localhost:8081.
    :param viewport: Width/height pixels. Example: (390, 844).
    :param cedar_dataset: Single real owned baseline. Example: Mike's missing prose.
    :param caplog: Actual generation logger observation. Example: empty during GETs.
    :return: None. Example: None after visible 2/47 then changed count on reload.
    :raises AssertionError: If fallback is stale, unreadable or fabricates prose.
    """
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    _assert_live_counts(cedar_dataset, 2, 47)
    with _observe_reads(page, caplog):
        _follow_public_fallback(page, live_server_url, _BASE_HINT, cedar_dataset)
    _change_live_counts(cedar_dataset)
    with _observe_reads(page, caplog):
        _reload_public_fallback(page, _CHANGED_HINT, cedar_dataset)
        _follow_public_fallback(page, live_server_url, _CHANGED_HINT, cedar_dataset)
    assert not page.context.cookies(), "Anonymous discovery created cookies."


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_numeric_fallback_with_own_profile_shows_no_expansion_control(
    page: Page,
    live_server_url: str,
    cedar_dataset: CedarDataset,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Authenticate Mike through the real login and inspect his own profile.

    :param page: Function-scoped browser page. Example: Chromium Page.
    :param live_server_url: Existing server URL. Example: http://localhost:8081.
    :param cedar_dataset: Real Mike account/history. Example: baseline 2/47.
    :param caplog: Actual generation logger observation. Example: no GET trigger.
    :return: None. Example: None after numeric fallback and absent expansion.
    :raises AssertionError: If own profile invents summary text or expansion state.
    """
    page.set_viewport_size({"width": 1280, "height": 800})
    mike = cedar_dataset.users_by_username[_MIKE]
    Token.objects.get_or_create(user=mike)
    login(page, live_server_url, _MIKE, CEDAR_PASSWORD)
    with _observe_reads(page, caplog):
        _open_document(page, live_server_url + _OWN_PATH)
        _assert_own_fallback(page, _BASE_HINT)
    _change_live_counts(cedar_dataset)
    with _observe_reads(page, caplog):
        response = page.reload()
        assert response is not None and response.status == HTTPStatus.OK
        _settle_document(page)
        _assert_own_fallback(page, _CHANGED_HINT)
    assert ExpertProfile.objects.get(user=mike).contribution_summary == ""


def _follow_public_fallback(
    page: Page, origin: str, expected: str, dataset: CedarDataset
) -> None:
    """Follow Mike's actual card link into the production public detail.

    :param page: Actual anonymous page. Example: Development list.
    :param origin: Owned live origin. Example: http://localhost:8081.
    :param expected: Complete independent sentence. Example: exact 2/47.
    :param dataset: Real privacy probes. Example: persisted Cedar private rows.
    :return: None after complete readable list and detail fallbacks.
    :raises AssertionError: For wrong navigation, privacy or missing-prose states.
    """
    _open_document(page, origin + _LIST_PATH)
    _assert_fallback(page, "experts-card-hint-mchen", expected)
    _assert_private_markers_absent(page.content(), dataset, False)
    link = page.get_by_test_id("experts-view-profile-mchen")
    expect(link).to_have_attribute("href", _DETAIL_PATH)
    with page.expect_response(origin + _DETAIL_PATH) as navigation:
        link.click()
    assert navigation.value.status == HTTPStatus.OK
    assert navigation.value.request.redirected_from is None
    expect(page).to_have_url(origin + _DETAIL_PATH)
    _settle_document(page)
    _assert_public_fallback(page, expected, dataset)


def _reload_public_fallback(page: Page, expected: str, dataset: CedarDataset) -> None:
    """Reload the real public document after controlled persisted-row changes.

    :param page: Actual Mike detail at the baseline numeric state.
    :param expected: Updated independent sentence. Example: exact 1/48.
    :param dataset: Real marker source. Example: Cedar baseline.
    :return: None after actual HTTP200 and fresh readable counts.
    :raises AssertionError: For stale DOM, redirection or private disclosure.
    """
    response = page.reload()
    assert response is not None and response.status == HTTPStatus.OK
    assert response.request.redirected_from is None
    _settle_document(page)
    _assert_public_fallback(page, expected, dataset)


def _assert_public_fallback(page: Page, expected: str, dataset: CedarDataset) -> None:
    """Inspect missing public prose and the complete privacy boundary.

    :param page: Actual Mike production detail. Example: /experts/mchen/.
    :param expected: Complete independent sentence. Example: exact 2/47.
    :param dataset: Real marker-bearing baseline. Example: Cedar accounts.
    :return: None after exact fallback and absent fabricated summary.
    :raises AssertionError: For changed copy, private disclosure or invented prose.
    """
    expect(page.get_by_test_id("expert-name")).to_have_text("Mike Chen")
    _assert_fallback(page, "expert-numeric-fallback", expected)
    expect(page.get_by_test_id("expert-contribution-summary")).to_have_count(0)
    expect(page.get_by_test_id("profile-summary-toggle")).to_have_count(0)
    html = page.content()
    _assert_private_markers_absent(html, dataset, False)
    for book in Playbook.objects.filter(
        author_id=dataset.user_ids[_MIKE], visibility="private"
    ):
        if book.name in html or f'href="/playbooks/{book.pk}/"' in html:
            raise AssertionError(
                "A now-private Mike playbook leaked into public detail."
            )


def _assert_own_fallback(page: Page, expected: str) -> None:
    """Read live owner facts while retaining existing account controls.

    :param page: Actual authenticated Mike profile. Example: /auth/user/profile/.
    :param expected: Exact independent fallback. Example: 1 released playbook · 48 copies.
    :return: None after readable fallback without summary or expansion controls.
    :raises AssertionError: For fabricated prose, expansion or account replacement.
    """
    _assert_fallback(page, "profile-numeric-fallback", expected)
    expect(page.get_by_test_id("profile-contribution-summary")).to_have_count(0)
    expect(page.get_by_test_id("profile-summary-toggle")).to_have_count(0)
    expect(page.get_by_role("button", name="Show more", exact=True)).to_have_count(0)
    expect(page.get_by_role("button", name="Show less", exact=True)).to_have_count(0)
    expect(page.get_by_test_id("profile-edit-btn")).to_have_count(1)
    expect(page.get_by_test_id("profile-token-field")).to_have_attribute(
        "type", "password"
    )


def _change_live_counts(dataset: CedarDataset) -> None:
    """Change an owned book and a validated GUI author award, outside GET guards.

    :param dataset: Actual owned baseline. Example: Mike's real account/book.
    :return: None after independently reconciled 1/48 and unchanged empty prose.
    :raises AssertionError: For wrong live counts or any summary mutation.
    """
    mike = dataset.users_by_username[_MIKE]
    profile = tuple(ExpertProfile.objects.filter(user=mike).values())
    book = _public_book(dataset)
    assert Playbook.objects.filter(pk=book.pk).update(visibility="private") == 1
    _add_award(
        dataset,
        "browser-fresh-count",
        KarmaAward.SourceKind.CONSUMPTION,
        EventChannel.GUI_COPY,
    )
    _assert_live_counts(dataset, 1, 48)
    assert tuple(ExpertProfile.objects.filter(user=mike).values()) == profile


def _open_document(page: Page, url: str) -> None:
    """Open the actual production document without redirects or mock screens.

    :param page: Existing real Chromium page. Example: anonymous context.
    :param url: Owned production URL. Example: Development list.
    :return: None after actual HTTP200 and stable real typography.
    :raises AssertionError: For a failed or redirected production request.
    """
    response = page.goto(url)
    assert response is not None and response.status == HTTPStatus.OK
    assert response.request.redirected_from is None
    expect(page).to_have_url(url)
    _settle_document(page)


def _settle_document(page: Page) -> None:
    """Settle actual assets and normal first-visit preference without style changes.

    :param page: Existing actual document. Example: Mike public profile.
    :return: None after real glyph/font readiness and native scroll to the top.
    :raises AssertionError: If production assets or consent fail to settle.
    """
    dismiss = page.get_by_role("button", name="Not now", exact=True)
    if dismiss.is_visible():
        dismiss.click()
        expect(dismiss).to_be_hidden()
    _wait_for_actual_fonts(page)
    page.wait_for_function("""() => [...document.fonts].some(face =>
        face.family.includes('Montserrat') && face.status === 'loaded')""")
    page.keyboard.press("Home")
    page.wait_for_function("() => scrollY === 0")


def _assert_fallback(page: Page, hook: str, expected: str) -> None:
    """Require the full sentence in actual readable native text rectangles.

    :param page: Existing production page. Example: Development list.
    :param hook: Semantic fallback hook. Example: expert-numeric-fallback.
    :param expected: Exact independent sentence. Example: 2 released playbooks · 47 copies.
    :return: None once all actual text is visible and unobscured.
    :raises AssertionError: For changed text, clipping, overlap or style drift.
    """
    node = page.get_by_test_id(hook)
    expect(node).to_have_text(expected)
    node.scroll_into_view_if_needed()
    bounds = node.bounding_box()
    assert bounds is not None
    header = page.get_by_test_id("realm-navbar").bounding_box()
    assert header is not None
    if bounds["y"] < header["height"]:
        page.mouse.wheel(0, bounds["y"] - header["height"] - _READ_MARGIN_PX)
    expect(node).to_have_css(
        "font-family", "Montserrat, system-ui, -apple-system, sans-serif"
    )
    page.wait_for_function(_READABLE_TEXT, arg=hook, timeout=_SETTLE_TIMEOUT_MS)
    assert (
        node.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
        >= _MINIMUM_HINT_FONT_PX
    )
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")


_READABLE_TEXT = """hook => {
    const element=document.querySelector(`[data-testid="${hook}"]`);
    const range=document.createRange();range.selectNodeContents(element);
    const rect=element.getBoundingClientRect(), lines=[...range.getClientRects()];
    const top=Math.max(0,document.querySelector('[data-testid="realm-navbar"]').getBoundingClientRect().bottom);
    return lines.length && lines.every(line => line.top>=top && line.bottom<=innerHeight &&
        line.left>=rect.left-1 && line.right<=rect.right+1 &&
        line.top>=rect.top-1 && line.bottom<=rect.bottom+1 &&
        [line.left+1,(line.left+line.right)/2,line.right-1].every(x=>{
            const hit=document.elementFromPoint(x,(line.top+line.bottom)/2);
            return hit===element || element.contains(hit);
        }));
}"""


@contextmanager
def _observe_reads(
    page: Page, caplog: pytest.LogCaptureFixture
) -> Iterator[_ReadAudit]:
    """Observe real browser GET SQL, callbacks and whole persisted state.

    :param page: Actual isolated browser. Example: public or signed-in Mike.
    :param caplog: Actual generation logger collector. Example: no GET trigger.
    :return: Live-server observations without SQL parameters or private values.
    :raises AssertionError: For writes, callbacks, generation or state/mail changes.
    """
    audit = _ReadAudit()
    start = partial(_begin_read_request, audit)
    finish = partial(_finish_read_request, audit)
    before, callbacks = _fingerprint(), tuple(connection.run_on_commit)
    session = _session_identity(page)
    request_started.connect(start, weak=False)
    request_finished.connect(finish, weak=False)
    try:
        with capture_experts_logs(caplog, (_GENERATION_LOGGER,)):
            yield audit
            page.wait_for_load_state("networkidle")
    finally:
        request_started.disconnect(start)
        request_finished.disconnect(finish)
    assert audit.requests and all(row["finished"] for row in audit.requests)
    assert audit.commands and set(audit.commands) <= _READ_COMMANDS
    assert _fingerprint() == before, "Browser GET changed domain/session/mail state."
    assert _session_identity(page) == session, "Browser GET changed session identity."
    assert tuple(connection.run_on_commit) == callbacks
    assert not any(record.name == _GENERATION_LOGGER for record in caplog.records)


def _session_identity(page: Page) -> dict[str, Any]:
    """Decode the actual browser session instead of comparing expiry signatures.

    :param page: Actual browser context. Example: signed-in Mike or anonymous Bob.
    :return: In-memory decoded identity. Example: stable authentication fields or {}.
    :raises AssertionError: If these E2E tests use a different session backend.
    """
    assert settings.SESSION_ENGINE == "django.contrib.sessions.backends.signed_cookies"
    cookie = next(
        (
            row
            for row in page.context.cookies()
            if row["name"] == settings.SESSION_COOKIE_NAME
        ),
        None,
    )
    return SessionStore(session_key=cookie["value"]).load() if cookie else {}


def _begin_read_request(audit: _ReadAudit, sender: object, **kwargs: Any) -> None:
    """Attach an observer to the actual live-server request connection.

    :param audit: Owned observations. Example: an empty command list.
    :param sender: Real Django request-start sender. Example: WSGIHandler.
    :param kwargs: Actual signal fields. Example: method/path environ.
    :return: None after wrapping the unchanged native execution chain.
    :raises AssertionError: If a read window receives a non-GET request.
    """
    environ = kwargs["environ"]
    assert environ["REQUEST_METHOD"] == "GET"
    row = {"path": environ["PATH_INFO"], "finished": False}
    audit.requests.append(row)
    wrapper = partial(_record_read_query, audit, get_ident())
    audit.thread.row, audit.thread.wrapper = row, wrapper
    connection.execute_wrappers.append(wrapper)


def _record_read_query(
    audit: _ReadAudit,
    request_thread: int,
    execute: Callable[..., Any],
    sql: str,
    params: object,
    many: bool,
    context: Mapping[str, object],
) -> Any:
    """Record only command verbs and execute the original database call.

    :param audit: Actual query audit. Example: SELECT observations.
    :param request_thread: Real request owner thread ID.
    :param execute: Original actual database execution chain.
    :param sql: Actual statement; its body is never exported.
    :param params: Original parameters passed through unchanged.
    :param many: Actual executemany flag. Example: False.
    :param context: Actual Django context, passed through unchanged.
    :return: Original execution result. Example: SQLite cursor result.
    :raises DatabaseError: Original unchanged backend failure.
    """
    if get_ident() == request_thread:
        audit.commands.append(sql.lstrip().split(maxsplit=1)[0].upper())
    return execute(sql, params, many, context)


def _finish_read_request(audit: _ReadAudit, sender: object, **kwargs: Any) -> None:
    """Remove this request's observer and inspect pending actual callbacks.

    :param audit: Owned request audit. Example: one active WSGI request.
    :param sender: Actual request-finished sender.
    :param kwargs: Actual signal metadata; no body is recorded.
    :return: None with a completed actual read observation.
    :raises AssertionError: For queued work or a missing observer.
    """
    assert not connection.run_on_commit, "Browser GET queued post-commit work."
    wrapper = audit.thread.wrapper
    assert wrapper in connection.execute_wrappers
    connection.execute_wrappers.remove(wrapper)
    audit.thread.row["finished"] = True
