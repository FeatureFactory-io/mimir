"""Actual Chromium clipboard and successful receipt certification."""

from __future__ import annotations

from uuid import UUID

import pytest
from django.db.models import Sum
from django.urls import reverse
from e2e_helpers import login, open_content_browser
from playwright.sync_api import BrowserContext, Locator, Page, Request, expect

from methodology.models import Activity, EventChannel, KarmaAward
from methodology.services.copy_prompt_service import CopyPromptService
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset

ACTIVITY_ID = 6203
WORKFLOW_ID = 6202
PLAYBOOK_ID = 6201
MARIA_USERNAME = "mrodriguez"
MIKE_USERNAME = "mchen"
CLIPBOARD_MARKER = "Cedar clipboard before copying activity 6203"
COPY_RECEIPT_TIMEOUT_MS = 10_000
COPY_RECEIPT_MAX_ATTEMPTS = 2


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
    page: Page, context: BrowserContext, live_server_url: str
) -> None:
    """Certify KARMA-COPY-03 through real browser clipboard and network.

    :param page: Existing fresh page; authenticates real Cedar mchen.
    :param context: Existing context granted origin-scoped clipboard permissions.
    :param live_server_url: Existing function-scoped Django live server origin.
    :return: None after full prompt, real self receipt and unchanged ledger proofs.
    :raises AssertionError: If clipboard, receipt, totals or copy count differs.
    """
    raise NotImplementedError()


@pytest.mark.parametrize("actor_username", ["mrodriguez", None, "mchen"])
@pytest.mark.django_db(transaction=True)
def test_copy_uat_with_independent_baseline_lanes_matches_contract(
    page: Page,
    context: BrowserContext,
    live_server_url: str,
    actor_username: str | None,
) -> None:
    """Compose scripted UAT-18-04 with a fresh baseline for every actor lane.

    :param page: Existing fresh page for this parametrized invocation.
    :param context: Existing isolated clipboard-enabled browser context.
    :param live_server_url: Existing real function-scoped server origin.
    :param actor_username: Cedar Maria, anonymous guest or Mike; e.g. "mchen".
    :return: None after actual clipboard and lane-specific real domain assertions.
    :raises AssertionError: If isolation, receipt policy or expected effects differ.
    """
    raise NotImplementedError()
