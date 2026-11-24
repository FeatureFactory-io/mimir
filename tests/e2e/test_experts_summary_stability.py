"""Real clipboard, own-profile reading and stable-summary browser proof."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from functools import partial
from threading import local
from typing import Any

import pytest
from django.apps import apps
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.mail import EmailMessage
from django.core.signals import request_finished, request_started
from django.db import connection
from django.test import Client, TestCase
from django.urls import reverse
from e2e_helpers import login
from playwright.sync_api import BrowserContext, CDPSession, Page, expect

from methodology.llm.base import LLMResponse
from methodology.models import AgentInteraction, KarmaAward, PipChange
from methodology.services.copy_prompt_service import CopyPromptService
from tests.e2e.test_experts_stored_summary import (
    _certify_card_and_public_summary,
    _certify_own_summary,
    _domain_state,
    _open_document,
)
from tests.e2e.test_karma_copy import _copy_activity_prompt
from tests.integration.test_experts_summary_stability import _assert_award_pair
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
from tests.support.experts_html import assert_karma_source_rows
from tests.support.experts_privacy import _assert_private_markers_absent
from tests.support.experts_summary_data import (
    SUMMARY_SCRIPTS,
    load_summary_script,
    prepare_summary_submission,
    summary_processing_scope,
)
from tests.support.experts_summary_stability import (
    _assert_s28_generation_story,
    _oracle_paragraph,
    capture_summary_state,
)
from tests.support.scripted_llm import ScriptedLLM

_MARIA = "mrodriguez"
_MIKE = "mchen"
_ACTIVITY = 6203
_VIEWPORT = {"width": 1280, "height": 800}
_READ_VERBS = {"SELECT", "BEGIN", "COMMIT", "SAVEPOINT", "RELEASE"}
_BASE_TOTAL = 8200
_COPY_POINTS = 5
_GENERATION_CALLS = 2


@dataclass
class _ReadAudit:
    """Parameter-free observations of actual live-server SQL and callbacks."""

    verbs: list[str] = field(default_factory=list)
    requests: list[dict[str, object]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    thread: local = field(default_factory=local)


@pytest.fixture
def generated_summary(
    cedar_dataset: CedarDataset, client: Client
) -> Iterator[tuple[CedarDataset, ScriptedLLM, str]]:
    """Generate through S23 while retaining its actual finite captured port.

    :param cedar_dataset: Runner-owned real baseline. Example: CEDAR-RFP-01.
    :param client: Real setup client. Example: Maria's actual HTTP session.
    :return: Dataset, captured port and paragraph. Example: nine exact sentences.
    :raises AssertionError: For failed generation or a later extra model attempt.
    """
    paragraph = _oracle_paragraph(cedar_dataset)
    pip = prepare_summary_submission(cedar_dataset)
    summary, assessment = load_summary_script(
        SUMMARY_SCRIPTS / "PRF-EXPERTS-01/happy.json", pip.changes.get().pk
    )
    assert isinstance(summary, LLMResponse)
    summary = replace(summary, content=paragraph)
    with summary_processing_scope((summary, assessment)) as llm:
        _generate_summary(client, pip.pk, cedar_dataset)
        calls = llm.calls
        assert len(calls) == _GENERATION_CALLS
        yield cedar_dataset, llm, paragraph
        assert settings.CONTRIBUTION_SUMMARY_LLM is llm
        assert llm.calls == calls, "Browser reading/copy requested model completion."


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_s28_browser_with_successful_copy_updates_score_and_preserves_paragraph(
    generated_summary: tuple[CedarDataset, ScriptedLLM, str],
    page: Page,
    context: BrowserContext,
    live_server_url: str,
    mailoutbox: list[EmailMessage],
) -> None:
    """Expand, copy the actual prompt and reload the same stored public evidence.

    :param generated_summary: Completed real refresh and captured finite port.
    :param page: Real Chromium page. Example: Maria's authenticated session.
    :param context: Context containing the actual clipboard, not a replacement.
    :param live_server_url: Function server origin. Example: http://localhost:50123.
    :param mailoutbox: Existing notification capture. Example: setup messages.
    :return: None. Example: clipboard exact;8205/12455; unchanged prose/history.
    :raises AssertionError: For clipboard, receipt, display or state mismatch.
    """
    cedar, llm, paragraph = generated_summary
    page.set_viewport_size(_VIEWPORT)
    login(page, live_server_url, _MARIA, CEDAR_PASSWORD)
    _open_document(page, live_server_url + reverse("profile"))
    with _observe_reads(page, mailoutbox):
        _read_own_profile(page, live_server_url, paragraph, _BASE_TOTAL)
    subject_id = cedar.users_by_username[_MARIA].pk
    before, calls = capture_summary_state(subject_id), llm.calls
    protected = _protected_state(mailoutbox)
    ledger = tuple(KarmaAward.objects.order_by("pk").values())
    action = _copy_in_browser(page, context, live_server_url, cedar)
    _assert_award_pair(ledger, subject_id, cedar.users_by_username[_MIKE].pk, action)
    assert _protected_state(mailoutbox) == protected
    assert capture_summary_state(subject_id) == before and llm.calls == calls
    with _observe_reads(page, mailoutbox):
        _read_changed_displays(page, live_server_url, paragraph, cedar)
    assert capture_summary_state(subject_id) == before and llm.calls == calls
    assert _protected_state(mailoutbox) == protected


def _generate_summary(client: Client, pip_id: int, cedar: CedarDataset) -> None:
    """Submit the real draft and inspect its persisted successful trace.

    :param client: Real setup client. Example: authenticated Maria.
    :param pip_id: Actual created draft key. Example: new PIP primary key.
    :param cedar: Real baseline handles. Example: Maria and her submitted draft.
    :return: None. Example: Reviewed PIP, no acceptance award on submission.
    :raises AssertionError: For bypassed processing or an incomplete actual trace.
    """
    client.force_login(cedar.users_by_username[_MARIA])
    with TestCase.captureOnCommitCallbacks(execute=True):
        response = client.post(
            reverse("pip_submit_review", args=[pip_id]),
            headers={"X-Request-ID": "s28-real-generation"},
        )
    assert response.status_code == 302
    interaction = AgentInteraction.objects.get(pip_id=pip_id)
    _assert_s28_generation_story(
        interaction, cedar.users_by_username[_MARIA].pk, pip_id
    )
    change = PipChange.objects.get(pip_id=pip_id)
    assert change.pip.status == change.pip.STATUS_REVIEWED
    assert change.galdr_recommendation == PipChange.GALDR_ACCEPT


def _read_own_profile(page: Page, origin: str, paragraph: str, total: int) -> None:
    """Read exact sources and use real keyboard expansion/collapse.

    :param page: Actual Maria browser. Example: own contributions card.
    :param origin: Runner-owned server origin. Example: localhost.
    :param paragraph: Full independent oracle. Example: nine sentences.
    :param total: Expected live total. Example:8200 or8205.
    :return: None. Example: full paragraph, native expansion, source reconciliation.
    :raises AssertionError: For wrong score, lost text or inaccessible controls.
    """
    _certify_own_summary(page, origin, paragraph)
    expect(page.get_by_test_id("profile-karma-total")).to_have_text(f"{total:,}")
    expect(page.get_by_test_id("profile-primary-category")).to_have_text("Design")
    _assert_sources(page, total, own=True)


def _assert_sources(page: Page, total: int, *, own: bool) -> None:
    """Reconcile the actual source/category DOM independently of total score.

    :param page: Real own/public document. Example: Maria profile.
    :param total: Expected live score. Example:8205.
    :param own: Whether existing own-profile labels apply. Example: True.
    :return: None. Example:5000+1600+1200+405=8205; category7200/1005.
    :raises AssertionError: For wrong or absent source/category data.
    """
    learning = 400 + total - _BASE_TOTAL
    prefix = "profile-" if own else ""
    sources = {
        "Released" if own else "Released playbooks": 5000,
        "PIP" if own else "PIP contributions": 1600,
        "Consumption": 1200,
        "Learning": learning,
    }
    total_id = "profile-karma-total" if own else "expert-karma-total"
    assert_karma_source_rows(page.content(), sources, total_id, total)
    table = page.get_by_test_id(f"{prefix}karma-source-breakdown")
    table.scroll_into_view_if_needed()
    expect(table).to_be_in_viewport(ratio=1)
    category = page.get_by_test_id(f"{prefix}karma-category-breakdown")
    expected = ["Design", "7200", "Development", str(1000 + total - _BASE_TOTAL)]
    if not own:
        expected = [expected[0], "7,200", expected[2], f"{int(expected[3]):,}"]
    expect(category.locator("dt, dd")).to_have_text(expected)


def _copy_in_browser(
    page: Page, context: BrowserContext, origin: str, cedar: CedarDataset
) -> str:
    """Use the native UI copy, inspect full clipboard and await real receipt.

    :param page: Actual signed-in browser. Example: Maria session.
    :param context: Actual owning browser context. Example: Chromium.
    :param origin: Owned application origin. Example: localhost.
    :param cedar: Actual activity/workflow handles. Example: Mike activity6203.
    :return: Application-generated UUID string. Example: one deliberate click.
    :raises AssertionError: For a clipboard/receipt mismatch or wrong route.
    """
    activity = cedar.activities_by_pk[_ACTIVITY]
    expected = CopyPromptService.build_activity_prompt(activity)
    path = reverse(
        "activity_detail",
        args=[activity.workflow.playbook_id, activity.workflow_id, activity.pk],
    )
    _open_document(page, origin + path)
    expect(page.get_by_test_id("activity-title")).to_have_text(activity.name)
    session = _grant_native_clipboard(context, page, origin)
    try:
        control = page.get_by_test_id("activity-header-actions").get_by_test_id(
            "copy-prompt-btn"
        )
        action = _copy_activity_prompt(
            control, expected, origin + reverse("karma_copy_receipt")
        )
        assert page.evaluate("() => navigator.clipboard.readText()") == expected
        return str(action)
    finally:
        session.detach()


def _grant_native_clipboard(
    context: BrowserContext, page: Page, origin: str
) -> CDPSession:
    """Grant native permissions and retain their CDP owner until copying ends.

    :param context: Current isolated context. Example: page.context.
    :param page: Actual local document. Example: activity detail.
    :param origin: Exact authorized origin. Example: localhost HTTP origin.
    :return: Active native CDP session. Example: detach after clipboard read.
    :raises AssertionError: For a mismatched context or missing native context ID.
    """
    assert page.context is context and page.url.startswith(origin + "/")
    session = context.new_cdp_session(page)
    try:
        context_id = session.send("Target.getTargetInfo")["targetInfo"][
            "browserContextId"
        ]
        assert context_id
        for name in ("clipboard-read", "clipboard-write"):
            session.send(
                "Browser.setPermission",
                {
                    "permission": {"name": name},
                    "setting": "granted",
                    "origin": origin,
                    "browserContextId": context_id,
                },
            )
        return session
    except Exception:
        session.detach()
        raise


def _read_changed_displays(
    page: Page, origin: str, paragraph: str, cedar: CedarDataset
) -> None:
    """Reload actual own, Design, public and Development score surfaces.

    :param page: Actual browser after successful copy. Example: Maria.
    :param origin: Runner-owned origin. Example: localhost.
    :param paragraph: Exact pre-copy paragraph. Example: nine sentences.
    :param cedar: Actual privacy boundary and accounts. Example: CEDAR-RFP-01.
    :return: None. Example:8205/12455 with no generation or extra awards.
    :raises AssertionError: For stale score, changed prose or private leakage.
    """
    _read_own_profile(page, origin, paragraph, _BASE_TOTAL + _COPY_POINTS)
    _certify_card_and_public_summary(page, origin, paragraph)
    expect(page.get_by_test_id("expert-karma-total")).to_have_text("8,205")
    _assert_sources(page, 8205, own=False)
    _assert_private_markers_absent(page.content(), cedar, allow_contact=True)
    _open_document(page, origin + "/experts/?category=design")
    card = page.get_by_test_id("experts-card-mrodriguez")
    expect(card.get_by_test_id("expert-card-karma")).to_have_text("8,205")
    expect(page.get_by_test_id("experts-card-hint-mrodriguez")).to_have_js_property(
        "textContent", paragraph
    )
    _open_document(page, origin + "/experts/?category=development")
    mike = page.get_by_test_id("experts-card-mchen")
    expect(mike.get_by_test_id("expert-card-karma")).to_have_text("12,455")
    expect(page.get_by_test_id("experts-card-mrodriguez")).to_have_count(0)


def _protected_state(mailoutbox: list[EmailMessage]) -> tuple[str, ...]:
    """Fingerprint every model/M2M/session/mail row except expected new awards.

    :param mailoutbox: Existing local notification list. Example: setup messages.
    :return: Complete safe protected state hashes. Example: unchanged non-ledger.
    :raises AssertionError: For unexpected model/hash ordering or failed DB read.
    """
    models = sorted(
        apps.get_models(include_auto_created=True), key=lambda m: m._meta.label
    )
    filtered = [model for model in models if model is not Session]
    award_index = filtered.index(KarmaAward)
    state = _domain_state(mailoutbox)
    assert len(state) == len(models) + 1
    return state[:award_index] + state[award_index + 1 :]


@contextmanager
def _observe_reads(page: Page, mailoutbox: list[EmailMessage]) -> Iterator[_ReadAudit]:
    """Observe actual live-server SQL, callbacks and complete read-only state.

    :param page: Existing browser. Example: Maria's display GET window.
    :param mailoutbox: Existing local notification list. Example: setup messages.
    :return: Actual parameter-free request audit. Example: only read/session expiry.
    :raises AssertionError: For domain writes, callbacks or changed persisted state.
    """
    audit = _ReadAudit()
    start, finish = partial(_start_read, audit), partial(_finish_read, audit)
    before, callbacks = _domain_state(mailoutbox), tuple(connection.run_on_commit)
    request_started.connect(start, weak=False)
    request_finished.connect(finish, weak=False)
    try:
        yield audit
        page.wait_for_load_state("networkidle")
    finally:
        request_started.disconnect(start)
        request_finished.disconnect(finish)
    assert audit.requests and all(row["finished"] for row in audit.requests)
    assert audit.verbs and not audit.errors
    assert _domain_state(mailoutbox) == before
    assert tuple(connection.run_on_commit) == callbacks


def _start_read(audit: _ReadAudit, sender: object, **kwargs: Any) -> None:
    """Attach an observer to the actual request-thread database wrapper.

    :param audit: Owned non-sensitive observations. Example: empty request list.
    :param sender: Actual WSGI request sender. Example: Django handler.
    :param kwargs: Original signal fields. Example: environ path/method.
    :return: None. Example: native SQL observed without substitution.
    :raises KeyError: If Django omits its required request environment.
    """
    environ = kwargs["environ"]
    if environ["REQUEST_METHOD"] != "GET":
        audit.errors.append("Non-GET request entered the read window.")
    row = {"path": environ["PATH_INFO"], "finished": False}
    audit.requests.append(row)
    wrapper = partial(_record_read_sql, audit)
    audit.thread.row, audit.thread.wrapper = row, wrapper
    connection.execute_wrappers.append(wrapper)


def _record_read_sql(
    audit: _ReadAudit,
    execute: Callable[..., Any],
    sql: str,
    params: object,
    many: bool,
    context: Mapping[str, object],
) -> Any:
    """Pass actual SQL unchanged, retaining only its safe command verb.

    :param audit: Owned read-window observations. Example: SELECT commands.
    :param execute: Original Django execution chain, never replaced.
    :param sql: Actual statement, never retained or exported.
    :param params: Actual parameters, unchanged and never recorded.
    :param many: Actual executemany flag. Example: False.
    :param context: Actual backend context, passed through unchanged.
    :return: Original database result. Example: cursor execution result.
    :raises DatabaseError: Original unchanged backend failure.
    """
    command = sql.lstrip().upper()
    verb = command.split(maxsplit=1)[0]
    audit.verbs.append(verb)
    if verb not in _READ_VERBS and not command.startswith(
        'UPDATE "DJANGO_SESSION" SET '
    ):
        audit.errors.append("Domain SQL mutation during browser GET.")
    return execute(sql, params, many, context)


def _finish_read(audit: _ReadAudit, sender: object, **kwargs: Any) -> None:
    """Observe real pending callbacks and remove only this request's observer.

    :param audit: Actual same-thread request audit. Example: one active GET.
    :param sender: Real request-finished sender. Example: WSGI handler.
    :param kwargs: Actual signal metadata, without recorded response bodies.
    :return: None. Example: completed GET and empty callback queue.
    :raises AttributeError: For a mismatched real request lifecycle.
    """
    if connection.run_on_commit:
        audit.errors.append("Browser GET left scheduled callbacks.")
    wrapper = audit.thread.wrapper
    if wrapper not in connection.execute_wrappers:
        audit.errors.append("Native query observer removed prematurely.")
    else:
        connection.execute_wrappers.remove(wrapper)
    audit.thread.row["finished"] = True
