"""Actual Chromium clipboard and successful receipt certification."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from http import HTTPStatus
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.core.mail import EmailMessage
from django.db.models import Sum
from django.urls import reverse
from e2e_helpers import login, open_content_browser
from playwright.sync_api import BrowserContext, Locator, Page, Request, expect

from accounts.models import UserEmailVerification, UserOnboardingState
from methodology.models import (
    Activity,
    AgentInteraction,
    EventChannel,
    ExpertProfile,
    KarmaAward,
)
from methodology.services.copy_prompt_service import CopyPromptService
from methodology.services.experts_service import ExpertProjection, ExpertsService
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset

ACTIVITY_ID = 6203
WORKFLOW_ID = 6202
PLAYBOOK_ID = 6201
MARIA_USERNAME = "mrodriguez"
MIKE_USERNAME = "mchen"
CLIPBOARD_MARKER = "Cedar clipboard before copying activity 6203"
COPY_RECEIPT_TIMEOUT_MS = 10_000
COPY_RECEIPT_MAX_ATTEMPTS = 2
_BASELINE_TOTALS = (8200, 12450)
_BASELINE_GUI_COPIES = 47
_COPY_POINTS = 5
_AWARDED_TOTALS = (8205, 12455)
_MARIA_BASELINE_DEVELOPMENT = 1000
_DOMAIN_MODELS = (
    User,
    UserEmailVerification,
    UserOnboardingState,
    Session,
    ExpertProfile,
    AgentInteraction,
    Activity,
    KarmaAward,
)


@dataclass(frozen=True)
class _CopyState:
    """Persisted values and live account projections around one copy journey."""

    rows: dict[type, dict[int | str, tuple[object, ...]]]
    projections: dict[int, ExpertProjection]


@pytest.fixture
def expected_activity_prompt(cedar_dataset: CedarDataset) -> str:
    """Build the oracle from real ORM fields before browser interaction starts.

    :param cedar_dataset: Loaded, transactionally isolated Cedar data.
    :return: Full Copy Prompt service text for Mike's activity 6203.
    """
    activity = Activity.objects.select_related("workflow__playbook").get(
        pk=cedar_dataset.activities_by_pk[ACTIVITY_ID].pk
    )
    prompt = CopyPromptService.build_activity_prompt(activity)
    assert prompt and prompt != CLIPBOARD_MARKER
    return prompt


@pytest.mark.django_db(transaction=True)
def test_copy_prompt_with_maria_copies_actual_prompt_and_credits_pair(
    expected_activity_prompt: str,
    cedar_dataset: CedarDataset,
    page: Page,
    context: BrowserContext,
    live_server_url: str,
) -> None:
    """Copy activity 6203 in the real browser and verify clipboard plus ledger.

    :param expected_activity_prompt: Full server-built Cedar activity prompt.
    :param cedar_dataset: Transactionally isolated Maria and Mike baseline.
    :param page: Existing isolated browser page. Example: activity detail.
    :param context: Existing browser context. Example: granted clipboard permissions.
    :param live_server_url: Existing real live server URL. Example: localhost origin.
    :return: None after exact prompt, receipt and 8205/12455 assertions.
    :raises AssertionError: If clipboard contents or domain effects differ.
    """
    assert _karma_totals(cedar_dataset) == (8200, 12450)
    _login_for_copy(page, context, live_server_url)
    detail_path = reverse(
        "activity_detail",
        kwargs={
            "playbook_pk": PLAYBOOK_ID,
            "workflow_pk": WORKFLOW_ID,
            "activity_pk": ACTIVITY_ID,
        },
    )
    response = page.goto(f"{live_server_url}{detail_path}")
    assert response is not None and response.ok
    copy_button = page.get_by_test_id("activity-header-actions").get_by_test_id(
        "copy-prompt-btn"
    )
    receipt_url = f"{live_server_url}{reverse('karma_copy_receipt')}"
    event_uuid = _copy_activity_prompt(
        copy_button, expected_activity_prompt, receipt_url
    )

    _assert_copy_awards(cedar_dataset, event_uuid)
    assert _karma_totals(cedar_dataset) == (8205, 12455)


@pytest.mark.django_db(transaction=True)
def test_copy_prompt_with_list_and_embed_surfaces_reports_same_entity(
    expected_activity_prompt: str,
    cedar_dataset: CedarDataset,
    page: Page,
    context: BrowserContext,
    live_server_url: str,
) -> None:
    """Certify existing row/embed controls identify the copied real activity.

    :param expected_activity_prompt: Full server-built Cedar activity prompt.
    :param cedar_dataset: Transactionally isolated Maria and Mike baseline.
    :param page: Existing isolated page. Example: activity list or embed.
    :param context: Existing clipboard-enabled context. Example: Chromium.
    :param live_server_url: Existing live server URL. Example: localhost origin.
    :return: None after actual clipboard and authorized receipt assertions.
    :raises AssertionError: If either surface loses entity metadata or prompt content.
    """
    assert _karma_totals(cedar_dataset) == (8200, 12450)
    _login_for_copy(page, context, live_server_url)
    list_path = reverse(
        "activity_list", kwargs={"playbook_pk": PLAYBOOK_ID, "workflow_pk": WORKFLOW_ID}
    )
    response = page.goto(f"{live_server_url}{list_path}")
    assert response is not None and response.ok
    receipt_url = f"{live_server_url}{reverse('karma_copy_receipt')}"
    row_button = page.get_by_test_id(f"copy-prompt-btn-activity-{ACTIVITY_ID}")
    row_event = _copy_activity_prompt(row_button, expected_activity_prompt, receipt_url)
    _assert_copy_awards(cedar_dataset, row_event)
    assert _karma_totals(cedar_dataset) == (8205, 12455)

    embed_button = _open_activity_embed(page, live_server_url)
    embed_event = _copy_activity_prompt(
        embed_button, expected_activity_prompt, receipt_url
    )
    assert embed_event != row_event
    _assert_copy_awards(cedar_dataset, embed_event)
    assert _karma_totals(cedar_dataset) == (8210, 12460)


def _login_for_copy(page: Page, context: BrowserContext, live_server_url: str) -> None:
    """Grant native clipboard permissions and log into the real browser session.

    :param page: Isolated Playwright browser page.
    :param context: Context that owns the page and its clipboard permissions.
    :param live_server_url: Function-scoped loopback Django origin.
    :return: None once Maria is authenticated.
    """
    context.grant_permissions(
        ["clipboard-read", "clipboard-write"], origin=live_server_url
    )
    login(page, live_server_url, MARIA_USERNAME, CEDAR_PASSWORD)


def _open_activity_embed(page: Page, live_server_url: str) -> Locator:
    """Open Mike's activity through the actual Content Browser structure tree.

    :param page: Authenticated Chromium page.
    :param live_server_url: Loopback Django origin.
    :return: Copy Prompt button inside the loaded activity panel.
    """
    open_content_browser(page, live_server_url, PLAYBOOK_ID)
    tree = page.get_by_test_id("browser-structure-tree")
    rows = tree.get_by_test_id("browser-tree-row")
    workflow = rows.and_(page.locator(f'[data-node-id="workflow:{WORKFLOW_ID}"]'))
    workflow.locator(".browser-tree-toggle").click()
    activity = rows.and_(page.locator(f'[data-node-id="activity:{ACTIVITY_ID}"]'))
    activity.click()
    panel = page.get_by_test_id("browser-detail-panel").get_by_test_id("activity-embed")
    return panel.get_by_test_id("copy-prompt-btn")


def _copy_activity_prompt(
    button: Locator, expected_prompt: str, receipt_url: str
) -> UUID:
    """Click the real button and read the native clipboard and real receipt traffic.

    :param button: Actual rendered Copy Prompt action for activity 6203.
    :param expected_prompt: Complete text from the real server prompt builder.
    :param receipt_url: Exact local Django success-receipt URL.
    :return: UUID generated by the application for this deliberate click.
    :raises AssertionError: If clipboard, receipt, or observed retry data differ.
    """
    page = button.page
    # The list and embed share one prompt, so stale clipboard text could pass.
    page.evaluate("text => navigator.clipboard.writeText(text)", CLIPBOARD_MARKER)
    assert page.evaluate("() => navigator.clipboard.readText()") == CLIPBOARD_MARKER
    attempts: list[Request] = []

    def observe_receipt(request: Request) -> None:
        """Collect the real endpoint's requests for this one click."""
        if request.url == receipt_url:
            attempts.append(request)

    page.on("request", observe_receipt)
    try:
        with page.expect_response(
            lambda response: (
                response.url == receipt_url
                and response.request.method == "POST"
                and response.ok
            ),
            timeout=COPY_RECEIPT_TIMEOUT_MS,
        ) as receipt:
            button.click()
        assert receipt.value.status == 200
        assert receipt.value.json() == {"status": "applied"}
        assert page.evaluate("() => navigator.clipboard.readText()") == expected_prompt
        expect(page.get_by_test_id("copy-prompt-toast")).to_be_visible()
    finally:
        page.remove_listener("request", observe_receipt)
    return _assert_copy_requests(attempts)


def _assert_copy_requests(attempts: list[Request]) -> UUID:
    """Require legitimate target data and one identity across observed attempts.

    :param attempts: Passively observed requests to the receipt endpoint.
    :return: Canonical version-four action UUID shared by all attempts.
    :raises AssertionError: If the client changes the payload or sends attribution.
    """
    assert 1 <= len(attempts) <= COPY_RECEIPT_MAX_ATTEMPTS
    payload = attempts[0].post_data_json
    raw_uuid = payload["event_identity"]
    event_uuid = UUID(raw_uuid)
    assert raw_uuid == str(event_uuid) and event_uuid.version == 4
    assert payload == {
        "entity_type": "activity",
        "entity_id": ACTIVITY_ID,
        "event_identity": raw_uuid,
    }
    for attempt in attempts:
        assert attempt.method == "POST"
        assert attempt.post_data == attempts[0].post_data
    return event_uuid


def _assert_copy_awards(cedar_dataset: CedarDataset, event_uuid: UUID) -> None:
    """Require the exact paired ledger rows recorded for one browser action.

    :param cedar_dataset: Real fixture with the registered user IDs.
    :param event_uuid: Action identity observed in the actual browser POST.
    :return: None after verifying recipients, category, provenance and snapshots.
    :raises AssertionError: If any persisted award attribute differs.
    """
    maria = cedar_dataset.users_by_username[MARIA_USERNAME]
    mike = cedar_dataset.users_by_username[MIKE_USERNAME]
    identity = f"consumption:gui_copy:{maria.pk}:{event_uuid}"
    awards = list(KarmaAward.objects.filter(event_identity=identity))
    assert len(awards) == 2
    assert {(award.recipient_id, award.source_kind) for award in awards} == {
        (maria.pk, KarmaAward.SourceKind.LEARNING),
        (mike.pk, KarmaAward.SourceKind.CONSUMPTION),
    }
    for award in awards:
        assert award.points == 5
        assert award.category == "development"
        assert award.event_channel == EventChannel.GUI_COPY
        assert award.playbook_id_snapshot == PLAYBOOK_ID
        assert award.entity_type_snapshot == "activity"
        assert award.entity_id_snapshot == ACTIVITY_ID
        assert award.change_id_snapshot is None
    assert awards[0].occurred_at == awards[1].occurred_at


def _karma_totals(cedar_dataset: CedarDataset) -> tuple[int, int]:
    """Read Maria's and Mike's actual totals, in that order.

    :param cedar_dataset: Isolated Cedar fixture whose users own the ledger rows.
    :return: Current Maria/Mike totals, for example (8205, 12455).
    """
    user_ids = cedar_dataset.user_ids
    maria_id, mike_id = user_ids[MARIA_USERNAME], user_ids[MIKE_USERNAME]
    totals = dict(
        KarmaAward.objects.filter(recipient_id__in=(maria_id, mike_id))
        .values_list("recipient_id")
        .annotate(total=Sum("points"))
    )
    return totals[maria_id], totals[mike_id]


@pytest.mark.django_db(transaction=True)
def test_copy_prompt_with_mike_copies_actual_prompt_without_awards(
    expected_activity_prompt: str,
    cedar_dataset: CedarDataset,
    mailoutbox: list[EmailMessage],
    page: Page,
    context: BrowserContext,
    live_server_url: str,
) -> None:
    """Certify KARMA-COPY-03 through real browser clipboard and network.

    :param expected_activity_prompt: Full prompt built from the restored activity.
    :param cedar_dataset: Independently loaded Cedar baseline.
    :param mailoutbox: Local mail outbox. Example: empty.
    :param page: Existing fresh page; authenticates real Cedar mchen.
    :param context: Existing context granted origin-scoped clipboard permissions.
    :param live_server_url: Existing function-scoped Django live server origin.
    :return: None after full prompt, real self receipt and unchanged ledger proofs.
    :raises AssertionError: If clipboard, receipt, totals or copy count differs.
    """
    _certify_s38_copy(
        page,
        context,
        live_server_url,
        cedar_dataset,
        MIKE_USERNAME,
        expected_activity_prompt,
    )
    assert not mailoutbox


@pytest.mark.parametrize(
    "actor_username",
    [
        pytest.param(MARIA_USERNAME, id="A01-maria"),
        pytest.param(None, id="A02-guest-bob"),
        pytest.param(MIKE_USERNAME, id="A03-mike"),
    ],
)
@pytest.mark.django_db(transaction=True)
def test_copy_uat_with_independent_baseline_lanes_matches_contract(
    expected_activity_prompt: str,
    cedar_dataset: CedarDataset,
    mailoutbox: list[EmailMessage],
    page: Page,
    context: BrowserContext,
    live_server_url: str,
    actor_username: str | None,
) -> None:
    """Compose scripted UAT-18-04 with a fresh baseline for every actor lane.

    :param expected_activity_prompt: Full prompt built from this lane's activity.
    :param cedar_dataset: New Cedar import in this case's transactional test DB.
    :param mailoutbox: Local mail outbox. Example: empty.
    :param page: Existing fresh page for this parametrized invocation.
    :param context: Existing isolated clipboard-enabled browser context.
    :param live_server_url: Existing real function-scoped server origin.
    :param actor_username: Cedar Maria, anonymous guest or Mike; e.g. "mchen".
    :return: None after actual clipboard and lane-specific real domain assertions.
    :raises AssertionError: If isolation, receipt policy or expected effects differ.
    """
    _certify_s38_copy(
        page,
        context,
        live_server_url,
        cedar_dataset,
        actor_username,
        expected_activity_prompt,
    )
    assert not mailoutbox


def _certify_s38_copy(
    page: Page,
    context: BrowserContext,
    origin: str,
    cedar: CedarDataset,
    actor: str | None,
    expected_prompt: str,
) -> None:
    """Perform one native copy from an independently restored Cedar baseline.

    :param page: Existing blank page for the current test.
    :param context: Existing context without login state.
    :param origin: Function-scoped live server origin.
    :param cedar: Imported data, including Mike's public activity 6203.
    :param actor: Cedar account to sign in as, or None for the anonymous lane.
    :param expected_prompt: Complete text from the server prompt builder.
    :return: None after the browser and database agree on the outcome.
    :raises AssertionError: If isolation, feedback, traffic, or persistence differs.
    """
    receipt_url = f"{origin}{reverse('karma_copy_receipt')}"
    attempts: list[Request] = []

    def observe_receipt(request: Request) -> None:
        """Retain real receipt traffic from before the first navigation."""
        if urlsplit(request.url).path == urlsplit(receipt_url).path:
            attempts.append(request)

    assert page.url == "about:blank" and not context.cookies()
    page.on("request", observe_receipt)
    context.grant_permissions(["clipboard-read", "clipboard-write"], origin=origin)
    try:
        if actor is not None:
            login(page, origin, actor, CEDAR_PASSWORD)
        # Real authentication updates last_login. Snapshot before opening the activity.
        before = _copy_state()
        _assert_copy_baseline(before, cedar)
        button = _open_s38_activity(page, origin, cedar, actor)
        assert not attempts
        _click_s38_copy(button, expected_prompt, receipt_url, actor)
        _assert_public_copy_totals(page, origin, actor)
        _assert_copy_effects(before, cedar, actor, attempts, receipt_url)
        if actor is None:
            assert all(
                cookie["name"] != settings.SESSION_COOKIE_NAME
                for cookie in context.cookies()
            )
    finally:
        page.remove_listener("request", observe_receipt)


def _copy_state() -> _CopyState:
    """Read every persisted row value and the actual live account projections.

    :return: Complete comparison state, including cached summaries and model interactions.
    """
    rows = {
        model: {
            values[0]: values
            for values in model.objects.order_by("pk").values_list(
                "pk",
                *(
                    field.attname
                    for field in model._meta.concrete_fields
                    if not field.primary_key
                ),
            )
        }
        for model in _DOMAIN_MODELS
    }
    experts = ExpertsService()
    projections = {user_id: experts.project_user(user_id) for user_id in rows[User]}
    return _CopyState(rows, projections)


def _assert_copy_baseline(before: _CopyState, cedar: CedarDataset) -> None:
    """Require the independent Cedar actor and content baseline before opening detail.

    :param before: Actual rows and projections captured for this case.
    :param cedar: This case's independently imported Cedar data.
    :return: None after validating the actor totals, eligible GUI count and ownership.
    :raises AssertionError: If an actor, the activity, or a projected count differs.
    """
    maria, mike = cedar.user_ids[MARIA_USERNAME], cedar.user_ids[MIKE_USERNAME]
    activity = cedar.activities_by_pk[ACTIVITY_ID]
    playbook = activity.workflow.playbook
    assert (activity.workflow_id, playbook.pk, playbook.author_id) == (
        WORKFLOW_ID,
        PLAYBOOK_ID,
        mike,
    )
    assert (playbook.visibility, playbook.status, playbook.category) == (
        "public",
        "released",
        "development",
    )
    assert _karma_totals(cedar) == _BASELINE_TOTALS
    assert (
        before.projections[maria].total_points,
        before.projections[mike].total_points,
    ) == _BASELINE_TOTALS
    assert before.projections[mike].successful_gui_copy_count == _BASELINE_GUI_COPIES
    assert not User.objects.filter(username__iexact="bob").exists()


def _open_s38_activity(
    page: Page, origin: str, cedar: CedarDataset, actor: str | None
) -> Locator:
    """Open the actual released activity and validate its navigation and actor.

    :param page: Browser page with the current actor's session, if any.
    :param origin: Function-scoped live server origin.
    :param cedar: Loaded activity names and route identifiers.
    :param actor: Authenticated Cedar username, or None for the guest.
    :return: The real Copy Prompt button on activity 6203.
    :raises AssertionError: If activity, actor, or links are incorrect.
    """
    activity = cedar.activities_by_pk[ACTIVITY_ID]
    path = reverse("activity_detail", args=(PLAYBOOK_ID, WORKFLOW_ID, ACTIVITY_ID))
    response = page.goto(f"{origin}{path}")
    assert response is not None and response.status == HTTPStatus.OK
    assert page.url == f"{origin}{path}"
    expect(page.get_by_test_id("activity-title")).to_have_text(activity.name)
    expect(page.get_by_test_id("activity-back-btn")).to_have_attribute(
        "href", reverse("activity_list", args=(PLAYBOOK_ID, WORKFLOW_ID))
    )
    breadcrumb = page.get_by_role("navigation", name="breadcrumb")
    assert [
        link.get_attribute("href")
        for link in breadcrumb.get_by_role(
            "link", name=activity.workflow.name, exact=True
        ).all()
    ] == [
        reverse("playbook_detail", args=(PLAYBOOK_ID,)),
        reverse("workflow_detail", args=(PLAYBOOK_ID, WORKFLOW_ID)),
    ]
    if actor is None:
        _assert_guest_copy_navigation(page, path)
    else:
        expect(page.get_by_test_id("user-display")).to_have_text(actor)
        expect(page.get_by_test_id("guest-auth-banner")).to_have_count(0)
    return page.get_by_test_id("activity-header-actions").get_by_test_id(
        "copy-prompt-btn"
    )


def _assert_guest_copy_navigation(page: Page, activity_path: str) -> None:
    """Confirm that anonymous copying preserves the normal public affordances.

    :param page: Real guest activity detail page.
    :param activity_path: Current public activity URL path.
    :return: None after validating access and authentication links.
    :raises AssertionError: If guest controls are missing or editing is exposed.
    """
    expect(page.get_by_test_id("user-display")).to_have_count(0)
    expect(page.get_by_test_id("guest-auth-banner")).to_be_visible()
    expect(page.get_by_test_id("edit-btn")).to_have_count(0)
    expect(page.get_by_test_id("guest-banner-register")).to_have_attribute(
        "href", reverse("register")
    )
    sign_in = page.get_by_test_id("guest-banner-sign-in").get_attribute("href") or ""
    target = urlsplit(sign_in)
    assert target.path == reverse("login") and parse_qs(target.query) == {
        "next": [activity_path]
    }


def _click_s38_copy(
    button: Locator, prompt: str, receipt_url: str, actor: str | None
) -> None:
    """Copy through the native control and await the expected real response.

    :param button: Visible Copy Prompt action from the production template.
    :param prompt: Full service prompt from the fixture's exact activity.
    :param receipt_url: Exact endpoint for authenticated successful clipboard writes.
    :param actor: Authenticated Cedar username, or None for the anonymous lane.
    :return: None after clipboard and feedback succeed in this actor's lane.
    :raises AssertionError: If the browser response, clipboard, or feedback differs.
    """
    page = button.page
    toast = page.get_by_test_id("copy-prompt-toast")
    expect(toast).to_be_hidden()
    page.evaluate("text => navigator.clipboard.writeText(text)", CLIPBOARD_MARKER)
    assert page.evaluate("() => navigator.clipboard.readText()") == CLIPBOARD_MARKER
    if actor is None:
        button.click()
        _observe_s38_clipboard(page, prompt)
        # Observe the anonymous lane through the entire normal feedback interval.
        expect(toast).to_be_hidden()
    else:
        with page.expect_response(
            lambda response: (
                response.url == receipt_url and response.request.method == "POST"
            ),
            timeout=COPY_RECEIPT_TIMEOUT_MS,
        ) as receipt:
            button.click()
            _observe_s38_clipboard(page, prompt)
        assert receipt.value.status == HTTPStatus.OK
        expected = (
            {"status": "applied"}
            if actor == MARIA_USERNAME
            else {"status": "skipped", "reason": "self_consumption"}
        )
        assert receipt.value.json() == expected


def _observe_s38_clipboard(page: Page, prompt: str) -> None:
    """Check ordinary copy feedback and the Chromium clipboard bytes.

    :param page: Activity view immediately after the actual copy action.
    :param prompt: Expected complete text, including all line breaks.
    :return: None after exact clipboard and user-facing feedback assertions.
    :raises AssertionError: If clipboard does not match or error feedback appears.
    """
    toast = page.get_by_test_id("copy-prompt-toast")
    expect(toast).to_be_visible()
    expect(toast).to_have_text("Prompt copied to clipboard")
    assert page.evaluate("() => navigator.clipboard.readText()") == prompt
    expect(page.get_by_test_id("copy-prompt-error-toast")).to_be_hidden()
    expect(
        page.get_by_test_id("alert-message").filter(has_text="You earned")
    ).to_have_count(0)


def _assert_public_copy_totals(page: Page, origin: str, actor: str | None) -> None:
    """Check the public effect of the copy through existing profile screens.

    :param page: Same browser after Copy Prompt and normal feedback.
    :param origin: Actual live server origin.
    :param actor: Actor that determined whether consumption awards were eligible.
    :return: None after checking both people and visible Development attribution.
    :raises AssertionError: If any public total, category or author copy count differs.
    """
    awarded = actor == MARIA_USERNAME
    maria, mike = _AWARDED_TOTALS if awarded else _BASELINE_TOTALS
    maria_development = _MARIA_BASELINE_DEVELOPMENT + _COPY_POINTS * int(awarded)
    for username, total, development in (
        (MARIA_USERNAME, maria, maria_development),
        (MIKE_USERNAME, mike, mike),
    ):
        path = reverse("expert_detail", kwargs={"username": username})
        response = page.goto(f"{origin}{path}")
        assert response is not None and response.status == HTTPStatus.OK
        expect(page.get_by_test_id("expert-karma-total")).to_have_text(f"{total:,}")
        expect(page.get_by_test_id("karma-category-breakdown")).to_contain_text(
            re.compile(rf"\bDevelopment\s*{development:,}\b"), use_inner_text=True
        )
    copy_count = _BASELINE_GUI_COPIES + int(awarded)
    expect(page.get_by_test_id("expert-numeric-fallback")).to_have_text(
        f"2 released playbooks · {copy_count} copies"
    )
    expect(page.get_by_test_id(f"expert-playbook-{PLAYBOOK_ID}")).to_have_attribute(
        "href", reverse("playbook_detail", args=(PLAYBOOK_ID,))
    )


def _assert_copy_effects(
    before: _CopyState,
    cedar: CedarDataset,
    actor: str | None,
    attempts: list[Request],
    receipt_url: str,
) -> None:
    """Compare every original row and verify the only allowed additions.

    :param before: Real domain state before activity navigation.
    :param cedar: Current Cedar account identities.
    :param actor: Maria, Mike, or the unregistered guest.
    :param attempts: Receipt requests observed since before the first navigation.
    :param receipt_url: Expected full same-origin endpoint.
    :return: None after checking persisted, projected and network effects.
    :raises AssertionError: If any unauthorized write or attempt occurs.
    """
    after = _copy_state()
    ledger_before, ledger_after = before.rows[KarmaAward], after.rows[KarmaAward]
    for model in _DOMAIN_MODELS:
        if model is not KarmaAward and before.rows[model] != after.rows[model]:
            pytest.fail(f"Copy changed persisted {model.__name__} rows.")
    if any(ledger_after.get(pk) != row for pk, row in ledger_before.items()):
        pytest.fail("Copy changed an existing award row.")
    assert not User.objects.filter(username__iexact="bob").exists()
    event_uuid = None
    if actor is None:
        assert not attempts
    else:
        assert len(attempts) == 1 and attempts[0].url == receipt_url
        assert bool(attempts[0].header_value("x-csrftoken"))
        event_uuid = _assert_copy_requests(attempts)
    if actor == MARIA_USERNAME:
        assert event_uuid is not None
        assert len(ledger_after) == len(ledger_before) + 2
        _assert_copy_awards(cedar, event_uuid)
        assert _karma_totals(cedar) == _AWARDED_TOTALS
        assert after.projections == _expected_maria_copy_projections(before, cedar)
    else:
        assert len(ledger_after) == len(ledger_before)
        assert after.projections == before.projections
        assert _karma_totals(cedar) == _BASELINE_TOTALS


def _expected_maria_copy_projections(
    before: _CopyState, cedar: CedarDataset
) -> dict[int, ExpertProjection]:
    """Derive exact category, source, and eligible copy deltas from the baseline.

    :param before: Independent live projections before activity navigation.
    :param cedar: IDs for Maria and Mike.
    :return: Expected complete projection mapping after just the two +5 rows.
    """
    expected = before.projections.copy()
    for username, source in (
        (MARIA_USERNAME, "Learning"),
        (MIKE_USERNAME, "Consumption"),
    ):
        user_id = cedar.user_ids[username]
        baseline = expected[user_id]
        expected[user_id] = replace(
            baseline,
            total_points=baseline.total_points + _COPY_POINTS,
            category_points=tuple(
                (key, points + _COPY_POINTS if key == "development" else points)
                for key, points in baseline.category_points
            ),
            source_points=tuple(
                (key, points + _COPY_POINTS if key == source else points)
                for key, points in baseline.source_points
            ),
            successful_gui_copy_count=baseline.successful_gui_copy_count
            + int(username == MIKE_USERNAME),
        )
    return expected
