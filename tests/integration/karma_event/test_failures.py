"""Real ORM, HTTP, registered MCP and filesystem failure certification."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from functools import partial
from http import HTTPStatus
from pathlib import Path
from threading import Event
from typing import Literal
from uuid import UUID, uuid4

import httpx
import pytest
from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum
from django.http import HttpResponse
from django.test import Client as DjangoClient
from django.urls import reverse
from fastmcp.client.client import CallToolResult
from mcp.types import TextContent
from pytest import LogCaptureFixture
from pytest_django.live_server_helper import LiveServer
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from mcp_integration.facade.client import get_client
from mcp_integration.facade.tools_http import _post_consumption_receipt
from methodology.models import Activity, KarmaAward, Playbook, Rule
from methodology.services.karma_service import KarmaService
from methodology.services.playbook_export_service import PlaybookExportService
from methodology.services.workflow_export_service import WorkflowExportService
from tests.support.experts_data import (
    CedarDatabaseScope,
    CedarDataset,
    _resolve_database_scope,
)
from tests.support.experts_logs import capture_experts_logs
from tests.support.karma_failures import (
    DENIED_ACTOR,
    ENTITY_TYPES,
    MISSING_ENTITY_ID,
    PRIVATE_BODY,
    SIGNAL_WAIT_SECONDS,
    LedgerSnapshot,
    assert_global_ledger_unchanged,
    assert_no_private_data,
    prepare_denied_target,
    revoke_token_on_next_request_finish,
    snapshot_global_ledger,
)
from tests.support.karma_mcp import (
    MCPCase,
    MCPClientFactory,
    MCPClientSession,
    MCPDataset,
    MCPEntrypoint,
    StdioMCPClient,
)
from tests.support.log_story import assert_log_story

pytestmark = pytest.mark.django_db(transaction=True)

_ACTOR = "mrodriguez"
_AUTHOR = "mchen"
_PLAYBOOK = 6201
_WORKFLOW = 6202
_ACTIVITY = 6203
_AWARD_POINTS = 5
_BASELINE_TOTALS = {_ACTOR: 8200, _AUTHOR: 12450}
_RECEIPT = "/api/consumption-receipts/"
_BUNDLES = {
    "workflow": f"/api/workflows/{_WORKFLOW}/export/",
    "playbook": f"/api/playbooks/{_PLAYBOOK}/export-local/",
}
_EXPORT_IDS = {"workflow": _WORKFLOW, "playbook": _PLAYBOOK}
_EXPORT_FOLDER = "cedar"
_RULE_SLUG = "cedar-failure-check"
_FILE_BLOCKER = b"existing regular file"
_CONFINEMENT_FAILURES = {"traversal", "symlink"}
_EXPORT_FAILURE_TEXT = {
    "traversal": "relative",
    "symlink": "escapes",
    "parent": "File exists|Not a directory",
    "rules_parent": "File exists|Not a directory",
    "partial": "Is a directory",
    "mirror": "Is a directory",
    "ade": "Is a directory",
}
_DETAIL_LOGGERS = (
    "methodology.karma_views",
    "methodology.api.consumption_views",
    "methodology.services.playbook_service",
    "methodology.services.karma_service",
)
_EXPORT_LOGGERS = (
    "mcp_integration.facade.tools_http",
    "methodology.api.consumption_views",
    "methodology.services.karma_service",
    "methodology.services.playbook_export_service",
)
ReceiptSurface = Literal["gui", "token"]
ExportKind = Literal["workflow", "playbook"]
ExportSurface = Literal["facade", "legacy"]
FileSnapshot = dict[Path, tuple[bytes, int]]


@pytest.fixture(name="live_server")
def _guarded_live_server(
    transactional_db: None,
    django_db_setup: CedarDatabaseScope | None,
) -> Iterator[LiveServer]:
    """Start pytest-django's real HTTP server only after the nested DB activates.

    :param transactional_db: Active runner alias. Example: real transactional_db.
    :param django_db_setup: Nested fixture ownership. Example: private file scope.
    :return: Actual loopback pytest-django server. Example: localhost ephemeral port.
    :raises ValueError: The active runner database is not owned by this test.
    """
    _resolve_database_scope(django_db_setup)
    server = LiveServer("localhost")
    try:
        yield server
    finally:
        server.stop()


@pytest.mark.parametrize("failure", ("private", "missing"))
@pytest.mark.parametrize("entity_type", ENTITY_TYPES)
def test_consumption_with_denied_or_missing_target_preserves_global_ledger(
    cedar_dataset: CedarDataset, entity_type: str, failure: str
) -> None:
    """Exercise the complete T2 kind/failure matrix against the shared writer.

    :param cedar_dataset: Independently restored Cedar fixture. Example: CEDAR-RFP-01.
    :param entity_type: Stored content kind. Example: "activity".
    :param failure: Authorization or existence failure. Example: "private".
    :return: None. Example: denied PIP preserves all awards.
    :raises AssertionError: Access succeeds, content leaks or ledger changes.
    """
    actor, target = prepare_denied_target(cedar_dataset, entity_type, failure)
    before = snapshot_global_ledger()
    error_type = PermissionError if failure == "private" else ObjectDoesNotExist
    with pytest.raises(error_type) as denied:
        KarmaService.award_successful_consumption(
            actor, entity_type, target, uuid4(), channel="mcp_detail"
        )
    assert_no_private_data(cedar_dataset, str(denied.value))
    assert_global_ledger_unchanged(before)
    _assert_cedar_totals(cedar_dataset)


@pytest.mark.parametrize("entrypoint", ("facade", "legacy"))
@pytest.mark.parametrize("failure", ("private", "missing"))
@pytest.mark.parametrize("entity_type", ENTITY_TYPES)
async def test_mcp_detail_with_denied_or_missing_target_preserves_global_ledger(
    cedar_dataset: CedarDataset,
    live_server: LiveServer,
    entity_type: str,
    failure: str,
    entrypoint: MCPEntrypoint,
) -> None:
    """Exercise the T1 nine-tool matrix through both real registrations.

    :param cedar_dataset: Independently restored records. Example: Cedar.
    :param live_server: Isolated real HTTP backend. Example: localhost port.
    :param entity_type: Registered detail kind. Example: "playbook".
    :param failure: Private or absent target. Example: "missing".
    :param entrypoint: Actual registered surface. Example: "legacy".
    :return: None. Example: missing activity returns a safe tool error.
    :raises AssertionError: Registration, denial or complete-ledger proof fails.
    """
    actor, target = await sync_to_async(prepare_denied_target)(
        cedar_dataset, entity_type, failure
    )
    before = await sync_to_async(snapshot_global_ledger)()
    factory = _mcp_factory(cedar_dataset, live_server)
    observed = []
    async with factory.open(
        actor_username=actor.username, entrypoint=entrypoint
    ) as session:
        result = await _call_registered_detail(session, entity_type, target, observed)
    text = _tool_error(result, _detail_denial_text(entity_type, failure))
    await sync_to_async(_assert_detail_response)(
        cedar_dataset,
        factory,
        entrypoint,
        entity_type,
        target,
        failure,
        observed,
        text,
    )
    await sync_to_async(_assert_no_awards)(cedar_dataset, before)


@pytest.mark.parametrize("credential", ("invalid", "absent"))
async def test_mcp_detail_with_invalid_token_preserves_global_ledger(
    cedar_dataset: CedarDataset, live_server: LiveServer, credential: str
) -> None:
    """Reject invalid and absent credentials on a protected real tool.

    :param cedar_dataset: Real private target owner. Example: Maria.
    :param live_server: Real HTTP backend. Example: isolated test server.
    :param credential: Authentication variant. Example: "invalid".
    :return: None. Example: tool execution fails authentication.
    :raises AssertionError: Invalid credentials obtain content or awards.
    """
    before = await sync_to_async(snapshot_global_ledger)()
    pip = cedar_dataset.pips_by_key["HIST-MARIA-DESIGN-01"]
    fake_token = uuid4().hex
    factory = _mcp_factory(cedar_dataset, live_server)
    observed = []
    async with factory.open(actor_username=_ACTOR, entrypoint="facade") as session:
        headers = get_client().headers
        if credential == "absent":
            del headers["Authorization"]
        else:
            headers["Authorization"] = f"Token {fake_token}"
        result = await _call_registered_detail(session, "pip", pip.pk, observed)
    text = _tool_error(result, "HTTP 401")
    [(status, body)] = observed
    assert status == HTTPStatus.UNAUTHORIZED
    await sync_to_async(assert_no_private_data)(
        cedar_dataset, text + body, extras=(fake_token, pip.title, pip.summary)
    )
    assert factory.request_paths == [("GET", f"/api/pips/{pip.pk}/")]
    await sync_to_async(_assert_no_awards)(cedar_dataset, before)


@pytest.mark.parametrize("surface", ("gui", "token"))
def test_receipt_with_forged_fields_or_revoked_access_preserves_global_ledger(
    cedar_dataset: CedarDataset, surface: ReceiptSurface
) -> None:
    """Reject forged attribution and stale access through actual receipt views.

    :param cedar_dataset: Real receiver, author and alternate actor. Example: Cedar.
    :param surface: Receipt transport. Example: "gui" uses enforced CSRF.
    :return: None. Example: another authorized actor/channel is independent.
    :raises AssertionError: An attempt mutates a preexisting award.
    """
    actor = cedar_dataset.users_by_username[_ACTOR]
    author = cedar_dataset.users_by_username[_AUTHOR]
    other = cedar_dataset.users_by_username[DENIED_ACTOR]
    browser = _gui_for(actor)
    client = _receipt_client(surface, actor, browser=browser)
    alternate = Activity.objects.create(
        workflow_id=_WORKFLOW, name="Other receipt target", order=50
    )
    target = _receipt_selection(surface, _ACTIVITY, uuid4())
    before = snapshot_global_ledger()
    _assert_applied(_send_receipt(client, surface, target), surface)
    _assert_added_pairs(before, actor, author, target, _receipt_channel(surface))
    original = snapshot_global_ledger()
    _assert_applied(_send_receipt(client, surface, target), surface, replayed=True)
    _assert_receipt_rejections(cedar_dataset, client, surface, target, alternate.pk)
    assert_global_ledger_unchanged(original)
    _assert_independent_receipts(cedar_dataset, surface, actor, other, author, target)
    _assert_revoked_receipt(cedar_dataset, browser, client, surface, target)


@pytest.mark.parametrize(
    ("entity", "failure"),
    (
        ("workflow", "parent"),
        ("workflow", "partial"),
        ("workflow", "traversal"),
        ("workflow", "symlink"),
        ("playbook", "parent"),
        ("playbook", "rules_parent"),
        ("playbook", "mirror"),
        ("playbook", "ade"),
        ("playbook", "traversal"),
        ("playbook", "symlink"),
    ),
)
@pytest.mark.parametrize("surface", ("facade", "legacy"))
async def test_export_with_real_filesystem_failure_preserves_global_ledger(
    cedar_dataset: CedarDataset,
    live_server: LiveServer,
    tmp_path: Path,
    entity: ExportKind,
    failure: str,
    surface: ExportSurface,
) -> None:
    """Run both registered facade exports and both legacy filesystem services.

    :param cedar_dataset: Real Cedar exportable content. Example: workflow 6202.
    :param live_server: Actual facade backend. Example: isolated HTTP origin.
    :param tmp_path: Confined workspace. Example: rules parent is a file.
    :param entity: Export kind. Example: "playbook".
    :param failure: Actual obstruction or escape. Example: "mirror".
    :param surface: Real execution path. Example: "legacy".
    :return: None. Example: actual filesystem failure creates no receipt.
    :raises AssertionError: Incomplete export awards or file integrity differs.
    """
    actor = cedar_dataset.users_by_username[_ACTOR]
    before = await sync_to_async(snapshot_global_ledger)()
    await sync_to_async(_install_export_rule)()
    factory = _mcp_factory(cedar_dataset, live_server)
    setup = await sync_to_async(_prepare_failed_export)(
        actor, tmp_path, entity, failure
    )
    if surface == "facade":
        await _assert_facade_export_failed(cedar_dataset, factory, entity, setup)
    else:
        error = ValueError if setup.confined_failure else OSError
        with pytest.raises(error, match=setup.error_text):
            await sync_to_async(_legacy_export)(actor, setup, entity)
        _assert_failed_files(setup)
    await sync_to_async(_assert_no_awards)(cedar_dataset, before)


async def test_export_with_receipt_authentication_failure_preserves_completed_files(
    cedar_dataset: CedarDataset, live_server: LiveServer, tmp_path: Path
) -> None:
    """Distinguish completed files from failed receipt and recover the same UUID.

    :param cedar_dataset: Authorized Maria and Mike. Example: CEDAR-RFP-01.
    :param live_server: Real bundle and receipt endpoints. Example: localhost.
    :param tmp_path: Actual export workspace. Example: completed canonical tree.
    :return: None. Example: receipt-only retry awards one pair.
    :raises AssertionError: Files are rewritten, UUID lost or awards duplicate.
    """
    await _exercise_receipt_recovery(cedar_dataset, live_server, tmp_path)


@pytest.mark.parametrize("failure", ("denied_read", "failed_export"))
def test_mcp_stdio_with_denied_read_or_failed_export_returns_safe_error(
    cedar_dataset: CedarDataset,
    live_server: LiveServer,
    tmp_path: Path,
    django_db_setup: CedarDatabaseScope | None,
    failure: str,
) -> None:
    """Prove T3 failure results through real isolated facade stdio children.

    :param cedar_dataset: Real Cedar database. Example: private reader and exporter.
    :param live_server: Real token-authenticated backend. Example: localhost.
    :param tmp_path: Workspace containing a file-as-parent failure.
    :param django_db_setup: Explicit active runner ownership. Example: private file scope.
    :param failure: Actual tool operation. Example: "denied_read".
    :return: None. Example: valid JSON-RPC error and unchanged ledger.
    :raises AssertionError: Protocol pollution, secret leak or award appears.
    """
    case, expected = _stdio_failure_case(cedar_dataset, tmp_path, failure)
    dataset = MCPDataset(cedar_dataset, {}, {})
    before = snapshot_global_ledger()
    files = _snapshot_files(tmp_path)
    with StdioMCPClient(
        entrypoint="facade",
        actor_username=case.actor_username,
        dataset=dataset,
        server_url=live_server.url,
        root=tmp_path,
        database_scope=django_db_setup,
    ) as stdio:
        schemas = {tool["name"]: tool["inputSchema"] for tool in stdio.list_tools()}
        assert case.tool_name in schemas
        # The success decoder rejects tool errors; the captured envelope is still real.
        with pytest.raises(AssertionError):
            stdio.call(case)
    stdio.assert_protocol_clean()
    envelope = _assert_stdio_error(stdio, expected)
    assert_no_private_data(
        cedar_dataset,
        json.dumps(stdio.stdout_messages) + stdio.stderr,
        extras=(str(tmp_path), str(tmp_path.resolve())),
    )
    assert _snapshot_files(tmp_path) == files
    _assert_no_awards(cedar_dataset, before)
    print(
        f"stdio {failure}: initialize=1 tools/list=2 tools/call={json.dumps(envelope)}"
    )


@pytest.mark.parametrize("surface", ("gui", "token"))
def test_consumption_failure_log_story_reject(
    cedar_dataset: CedarDataset,
    caplog: LogCaptureFixture,
    tmp_path: Path,
    surface: ReceiptSurface,
) -> None:
    """Assert real denial/export-error beats and sensitive-data exclusions.

    :param cedar_dataset: Real actors and private content. Example: Cedar.
    :param caplog: Actual captured owner logs. Example: INFO beat records.
    :param tmp_path: Real failed-export destination. Example: file-as-parent.
    :param surface: Actual receipt boundary. Example: "gui".
    :return: None. Example: rejected invocation has no award-success beat.
    :raises AssertionError: Required beat absent or secret content logged.
    """
    actor, private_id = prepare_denied_target(cedar_dataset, "activity", "private")
    client = _receipt_client(surface, actor)
    before = snapshot_global_ledger()
    with capture_experts_logs(caplog, _DETAIL_LOGGERS + _EXPORT_LOGGERS):
        _exercise_rejected_receipt_logs(caplog, client, actor, private_id, surface)
        _assert_filesystem_reject_log(
            caplog, tmp_path, cedar_dataset.users_by_username[_ACTOR]
        )
    assert_no_private_data(cedar_dataset, _log_text(caplog), extras=(str(tmp_path),))
    assert_global_ledger_unchanged(before)
    _assert_cedar_totals(cedar_dataset)
    _print_story(
        caplog,
        (
            "copy_success_receipt",
            "ConsumptionReceiptView.post",
            "PlaybookExportService.export_playbook_to_local",
        ),
    )


async def test_consumption_receipt_failure_log_story_recovery(
    cedar_dataset: CedarDataset,
    caplog: LogCaptureFixture,
    live_server: LiveServer,
    tmp_path: Path,
) -> None:
    """Assert completed-files failure and same-UUID receipt recovery beats.

    :param cedar_dataset: Real test database. Example: Cedar actors and workflow.
    :param caplog: Actual captured boundary and domain logs. Example: INFO records.
    :param live_server: Real bundle and receipt endpoints. Example: localhost.
    :param tmp_path: Actual completed export tree. Example: a pytest-owned workspace.
    :return: None. Example: files_written=true then one recovered pair.
    :raises AssertionError: Error classification or retry story is false.
    """
    with capture_experts_logs(caplog, _EXPORT_LOGGERS):
        identity, file_count, rejected_token = await _exercise_receipt_recovery(
            cedar_dataset, live_server, tmp_path
        )
    actor_id = cedar_dataset.users_by_username[_ACTOR].pk
    _assert_recovery_story(caplog, identity, file_count, actor_id)
    await sync_to_async(assert_no_private_data)(
        cedar_dataset,
        _log_text(caplog),
        extras=(str(tmp_path.resolve()), rejected_token),
    )
    _print_story(
        caplog,
        (
            "facade_export",
            "export_receipt",
            "_post_consumption_receipt",
            "ConsumptionReceiptView.post",
            "KarmaService.award_successful_consumption",
        ),
    )


def _mcp_factory(dataset: CedarDataset, live_server: LiveServer) -> MCPClientFactory:
    """Use the shared real registrations with this node's own ORM fixtures.

    :param dataset: Actual Cedar actors. Example: Elena and Maria.
    :param live_server: Test backend. Example: local pytest-django server.
    :return: Shared session lifecycle. Example: factory.open(...).
    """
    return MCPClientFactory(MCPDataset(dataset, {}, {}), live_server.url, [])


async def _call_registered_detail(
    session: MCPClientSession,
    entity: str,
    target: int,
    observed: list[tuple[int, str]],
) -> CallToolResult:
    """Discover the native registered schema, observe HTTP if present and call it.

    :param session: Shared real registered context. Example: legacy or facade.
    :param entity: Detail kind. Example: "phase".
    :param target: Existing private or absent primary key. Example: 900046.
    :param observed: In-memory actual HTTP evidence. Example: [(404, "{...}")].
    :return: Real registered success/error envelope. Example: masked error.
    :raises AssertionError: The registered schema is unavailable.
    """
    tool = f"get_{entity}"
    schemas = {
        entry.name: entry.inputSchema for entry in await session.client.list_tools()
    }
    assert f"{entity}_id" in schemas[tool]["required"]
    assert "event_identity" in schemas[tool]["properties"]
    if session.entrypoint == "facade":
        get_client().event_hooks["response"].append(
            partial(_record_detail_response, observed)
        )
    return await session.client.call_tool(
        tool,
        {f"{entity}_id": target, "event_identity": str(uuid4())},
        raise_on_error=False,
    )


def _record_detail_response(
    observed: list[tuple[int, str]], response: httpx.Response
) -> None:
    """Record actual response status/body without replacing HTTP or exposing headers.

    :param observed: Private in-memory evidence. Example: initially empty list.
    :param response: Actual denied HTTP response. Example: PIP 403.
    :return: None. Example: a response status/body pair is appended.
    """
    response.read()
    observed.append((response.status_code, response.text))


def _assert_detail_response(
    dataset: CedarDataset,
    factory: MCPClientFactory,
    entrypoint: MCPEntrypoint,
    entity: str,
    target: int,
    failure: str,
    observed: list[tuple[int, str]],
    text: str,
) -> None:
    """Prove safe denial came from the relevant route and produced no receipt.

    :param dataset: Real Cedar fixture. Example: private book and token.
    :param factory: Existing real MCP transport harness. Example: facade or legacy.
    :param entrypoint: Registration surface. Example: "facade".
    :param entity: Content kind. Example: "pip".
    :param target: Requested primary key. Example: private proposal ID.
    :param failure: Existence or permission variant. Example: "private".
    :param observed: Actual HTTP status/body pairs. Example: [(403, "...")].
    :param text: Genuine tool error. Example: masked not found.
    :return: None. Example: no receipt request followed a masked 404.
    :raises AssertionError: Unexpected transport, disclosure or unsafe error.
    """
    if entrypoint == "legacy":
        assert not factory.request_paths and not observed
        assert_no_private_data(dataset, text)
        return
    [(status, body)] = observed
    expected = (
        HTTPStatus.FORBIDDEN
        if (entity, failure) == ("pip", "private")
        else HTTPStatus.NOT_FOUND
    )
    assert status == expected
    assert factory.request_paths == [("GET", _detail_route(entity, target))]
    assert_no_private_data(dataset, text + body)


def _assert_no_awards(dataset: CedarDataset, before: LedgerSnapshot) -> None:
    """Check the complete ledger and the independent Cedar principal totals.

    :param dataset: Actual Cedar accounts. Example: Maria and Mike.
    :param before: Complete snapshot. Example: all ordered original award rows.
    :return: None. Example: no award fields were changed.
    :raises AssertionError: Any award or recipient total differs.
    """
    assert_global_ledger_unchanged(before)
    _assert_cedar_totals(dataset)


def _detail_route(entity_type: str, target: int) -> str:
    """Return the current registered detail REST path.

    :param entity_type: Supported detail kind. Example: "activity".
    :param target: Real or absent primary key. Example: 6203.
    :return: Detail path. Example: "/api/activities/6203/".
    """
    plural = "activities" if entity_type == "activity" else f"{entity_type}s"
    return f"/api/{plural}/{target}/"


def _detail_denial_text(entity_type: str, failure: str) -> str:
    """Check the protected detail rather than a tool schema/framework failure.

    :param entity_type: Detail kind. Example: "pip".
    :param failure: Failure mode. Example: "private".
    :return: Existing safe error pattern. Example: "not found".
    """
    if entity_type == "pip" and failure == "private":
        return r"not allowed to view this pip|not found"
    return r"not found|no .* matches the given query"


def _tool_error(result: CallToolResult, expected: str) -> str:
    """Extract the real registered error envelope and require its safe classification.

    :param result: Actual FastMCP response. Example: denied get_activity.
    :param expected: Action-specific safe message pattern. Example: "not found".
    :return: Actual error body. Example: masked denial text.
    :raises AssertionError: Successful result, wrong error or unexpected structure.
    """
    if result.is_error is not True or result.structured_content is not None:
        raise AssertionError("Expected one safe registered tool error.")
    if len(result.content) != 1 or not isinstance(result.content[0], TextContent):
        raise AssertionError("Expected one text block in the registered tool error.")
    message = result.content[0].text
    if not re.search(expected, message, re.IGNORECASE):
        raise AssertionError("Wrong MCP tool error classification.")
    return message


def _assert_cedar_totals(dataset: CedarDataset) -> None:
    """Reconcile Maria's and Mike's untouched independent Cedar totals.

    :param dataset: Actual Cedar users. Example: Maria and Mike.
    :return: None. Example: totals of 8200 and 12450.
    :raises AssertionError: Either Cedar total diverges.
    """
    for username, points in _BASELINE_TOTALS.items():
        actor = dataset.users_by_username[username]
        assert KarmaAward.objects.filter(recipient=actor).aggregate(
            total=Sum("points")
        ) == {"total": points}


def _gui_for(actor: User) -> DjangoClient:
    """Open an eligible activity using a session with real enforced CSRF.

    :param actor: Existing nonself Cedar reader. Example: Maria.
    :return: Authenticated Django client with actual CSRF cookie.
    :raises AssertionError: The real activity or cookie is unavailable.
    """
    client = DjangoClient(enforce_csrf_checks=True)
    client.force_login(actor)
    assert client.get(_activity_path()).status_code == HTTPStatus.OK
    assert client.cookies[settings.CSRF_COOKIE_NAME].value
    return client


def _activity_path() -> str:
    """Resolve the actual Cedar GUI detail.

    :return: Django route to activity 6203. Example: the Copy Prompt page.
    """
    return reverse(
        "activity_detail",
        kwargs={
            "playbook_pk": _PLAYBOOK,
            "workflow_pk": _WORKFLOW,
            "activity_pk": _ACTIVITY,
        },
    )


def _receipt_client(
    surface: ReceiptSurface, actor: User, *, browser: DjangoClient | None = None
) -> DjangoClient:
    """Use the appropriate real authentication for a selected receipt route.

    :param surface: Receipt transport. Example: "token".
    :param actor: Existing actor. Example: Elena.
    :param browser: Optional already authenticated GUI session. Example: _gui_for(actor).
    :return: Configured Django client. Example: token-authenticated APIClient.
    """
    if surface == "gui":
        return browser if browser is not None else _gui_for(actor)
    token, _ = Token.objects.get_or_create(user=actor)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


def _receipt_channel(surface: ReceiptSurface) -> Literal["gui_copy", "mcp_detail"]:
    """Name the canonical channel established by this receipt surface.

    :param surface: Supported boundary. Example: "gui".
    :return: Channel used for this proof. Example: "gui_copy".
    """
    return "gui_copy" if surface == "gui" else "mcp_detail"


def _receipt_selection(
    surface: ReceiptSurface, target: int, identity: UUID
) -> dict[str, object]:
    """Assemble an otherwise legitimate receipt for an activity.

    :param surface: Receipt transport. Example: "token".
    :param target: Activity reference. Example: 6203.
    :param identity: Original or retry UUID. Example: uuid4().
    :return: Actual request fields. Example: activity and same action UUID.
    """
    payload: dict[str, object] = {
        "entity_type": "activity",
        "entity_id": target,
        "event_identity": str(identity),
    }
    if surface == "token":
        payload["channel"] = _receipt_channel(surface)
    return payload


def _send_receipt(
    client: DjangoClient,
    surface: ReceiptSurface,
    payload: Mapping[str, object],
    *,
    request_id: str | None = None,
) -> HttpResponse:
    """Send actual session CSRF or token receipt request with an explicit correlation.

    :param client: Authenticated Django test client. Example: a browser session.
    :param surface: Actual endpoint selection. Example: "gui".
    :param payload: Receipt request fields. Example: activity 6203.
    :param request_id: Optional request header distinct from the action UUID.
    :return: Actual Django or DRF response. Example: JsonResponse 409.
    """
    headers = {"X-Request-ID": request_id or str(payload["event_identity"])}
    path = _RECEIPT
    if surface == "gui":
        path = reverse("karma_copy_receipt")
        headers["X-CSRFToken"] = client.cookies[settings.CSRF_COOKIE_NAME].value
    return client.post(
        path, dict(payload), content_type="application/json", headers=headers
    )


def _assert_applied(
    response: HttpResponse, surface: ReceiptSurface, *, replayed: bool = False
) -> None:
    """Prove a legitimate request reached this endpoint with its credentials.

    :param response: Actual receipt response. Example: Django 200.
    :param surface: Kind of response contract. Example: "token".
    :param replayed: Whether the existing action is replayed. Example: True.
    :return: None. Example: positively acknowledged receipt.
    :raises AssertionError: Incorrect response or pair count.
    """
    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["status"] == ("replayed" if replayed else "applied")
    if surface == "token":
        assert payload["created_count"] == (0 if replayed else 2)


def _assert_receipt_rejection(
    dataset: CedarDataset, response: HttpResponse, status: HTTPStatus, reason: str
) -> None:
    """Check actual rejected receipt envelopes and reject any private disclosure.

    :param dataset: Real Cedar fixtures. Example: protected report and credentials.
    :param response: Rejected HTTP request. Example: 404.
    :param status: Correct HTTP rejection. Example: HTTPStatus.NOT_FOUND.
    :param reason: Grounded producer reason. Example: "target_unavailable".
    :return: None. Example: masked rejection.
    :raises AssertionError: Wrong parsing/access decision or disclosure.
    """
    assert_no_private_data(dataset, response.content.decode())
    assert response.status_code == status
    assert response.json() == {"status": "rejected", "reason": reason}


def _assert_receipt_rejections(
    dataset: CedarDataset,
    client: DjangoClient,
    surface: ReceiptSurface,
    receipt: Mapping[str, object],
    alternate_id: int,
) -> None:
    """Exercise forgery, hidden/missing targets and changed-target replay.

    :param dataset: Real Cedar baseline. Example: fixture private playbook owner.
    :param client: Authenticated session/token. Example: _gui_for(Maria).
    :param surface: Endpoint being positively exercised. Example: "gui".
    :param receipt: Existing legitimate request. Example: applied activity receipt.
    :param alternate_id: Another eligible activity, same playbook. Example: new PK.
    :return: None. Example: conflicting reuse preserves the original pair.
    :raises AssertionError: An adversarial receipt succeeds or mutates awards.
    """
    protected_actor = dataset.users_by_username[DENIED_ACTOR]
    _, private_id = prepare_denied_target(dataset, "activity", "private")
    unavailable = "access_denied" if surface == "gui" else "target_unavailable"
    forged_fields = {
        "actor_id": protected_actor.pk,
        "author_id": protected_actor.pk,
        "recipient_id": protected_actor.pk,
        "category": "design",
        "points": 5000,
        "source_kind": "release",
        "occurred_at": "2026-11-22T00:00:00Z",
        "channel": "export" if surface == "gui" else "gui_copy",
    }
    before = snapshot_global_ledger()
    new = {**receipt, "event_identity": str(uuid4())}
    for field, value in forged_fields.items():
        response = _send_receipt(client, surface, {**new, field: value})
        _assert_receipt_rejection(
            dataset, response, HTTPStatus.BAD_REQUEST, "invalid_payload"
        )
        assert_global_ledger_unchanged(before)
    for target in (private_id, MISSING_ENTITY_ID):
        # This private activity belongs to Maria. Only Elena can exercise denial here.
        outsider = _receipt_client(surface, protected_actor)
        response = _send_receipt(outsider, surface, {**receipt, "entity_id": target})
        _assert_receipt_rejection(dataset, response, HTTPStatus.NOT_FOUND, unavailable)
        assert_global_ledger_unchanged(before)
    response = _send_receipt(client, surface, {**receipt, "entity_id": alternate_id})
    _assert_receipt_rejection(dataset, response, HTTPStatus.CONFLICT, "event_conflict")
    assert_global_ledger_unchanged(before)


def _assert_independent_receipts(
    dataset: CedarDataset,
    surface: ReceiptSurface,
    actor: User,
    alternate: User,
    author: User,
    receipt: Mapping[str, object],
) -> None:
    """Prove a legitimate UUID is scoped to the server-authenticated actor and channel.

    :param dataset: Real Cedar actors/account data. Example: CEDAR-RFP-01.
    :param surface: Already applied boundary. Example: "gui".
    :param actor: Original actor. Example: Maria.
    :param alternate: Different authorized actor. Example: Elena.
    :param author: Original playbook author. Example: Mike.
    :param receipt: Same action UUID and target. Example: original activity.
    :return: None. Example: two distinct legitimate pairs preserve the original.
    :raises AssertionError: Cross-actor or cross-channel identity is conflated.
    """
    other_surface: ReceiptSurface = "token" if surface == "gui" else "gui"
    for entry, consumer in ((surface, alternate), (other_surface, actor)):
        before = snapshot_global_ledger()
        assert consumer.pk in dataset.user_ids.values()
        client = _receipt_client(entry, consumer)
        payload = _receipt_selection(
            entry, _ACTIVITY, UUID(str(receipt["event_identity"]))
        )
        _assert_applied(_send_receipt(client, entry, payload), entry)
        _assert_added_pairs(before, consumer, author, payload, _receipt_channel(entry))


def _assert_revoked_receipt(
    dataset: CedarDataset,
    browser: DjangoClient,
    client: DjangoClient,
    surface: ReceiptSurface,
    receipt: Mapping[str, object],
) -> None:
    """Revoke access after a successful real read and reject both fresh and replayed UUIDs.

    :param dataset: Cedar source and actor fixture. Example: Mike's original playbook.
    :param browser: Session read authority. Example: CSRF-valid Maria.
    :param client: Actual receipt client. Example: Maria's token.
    :param surface: Receipt boundary under test. Example: "token".
    :param receipt: Legitimate receipt already applied. Example: activity 6203.
    :return: None. Example: stale reads and known UUIDs confer no new authorization.
    :raises AssertionError: The read or subsequent masked denial fails.
    """
    before = snapshot_global_ledger()
    read_client = browser if surface == "gui" else client
    route = (
        _activity_path() if surface == "gui" else _detail_route("activity", _ACTIVITY)
    )
    assert read_client.get(route).status_code == HTTPStatus.OK
    assert (
        Playbook.objects.filter(pk=_PLAYBOOK, visibility="public").update(
            visibility="private"
        )
        == 1
    )
    assert read_client.get(route).status_code == HTTPStatus.NOT_FOUND
    unavailable = "access_denied" if surface == "gui" else "target_unavailable"
    for attempt in (receipt, {**receipt, "event_identity": str(uuid4())}):
        response = _send_receipt(client, surface, attempt)
        _assert_receipt_rejection(dataset, response, HTTPStatus.NOT_FOUND, unavailable)
        assert_global_ledger_unchanged(before)


def _assert_added_pairs(
    before: LedgerSnapshot,
    actor: User,
    author: User,
    receipt: Mapping[str, object],
    channel: str,
) -> None:
    """Verify precisely one new canonical pair while preserving every previous row.

    :param before: Complete original award ledger. Example: Cedar.
    :param actor: Recipient of learning award. Example: Maria.
    :param author: Recipient of consumption award. Example: Mike.
    :param receipt: Verified action UUID and target. Example: activity 6203.
    :param channel: Actual persisted event channel. Example: "export".
    :return: None. Example: two immutable 5-point rows.
    :raises AssertionError: A row, field, attribution or identity is wrong.
    """
    action = receipt["event_identity"]
    canonical = f"consumption:{channel}:{actor.pk}:{action}"
    entries = list(KarmaAward.objects.filter(event_identity=canonical).order_by("pk"))
    assert len(entries) == 2
    assert {(entry.recipient_id, entry.source_kind) for entry in entries} == {
        (actor.pk, KarmaAward.SourceKind.LEARNING),
        (author.pk, KarmaAward.SourceKind.CONSUMPTION),
    }
    assert {entry.occurred_at for entry in entries} == {entries[0].occurred_at}
    for entry in entries:
        assert entry.event_channel == channel
        assert entry.points == _AWARD_POINTS and entry.category == "development"
        assert (
            entry.playbook_id_snapshot == _PLAYBOOK and entry.change_id_snapshot is None
        )
        assert (entry.entity_type_snapshot, entry.entity_id_snapshot) == (
            receipt["entity_type"],
            receipt["entity_id"],
        )
    current = snapshot_global_ledger()
    assert current[:-2] == before and len(current) == len(before) + 2


@dataclass(frozen=True)
class _ExportSetup:
    """Confined destinations, genuine obstructions and a real reference bundle."""

    workspace: Path
    target: Path
    mirror: Path
    folder: str
    blocked: Path
    arguments: dict[str, object]
    expected_files: dict[Path, bytes]
    previous_files: FileSnapshot
    prior_paths: frozenset[Path]
    confined_failure: bool
    error_text: str


class _ExportObservation:
    """Capture the genuine HTTP bundle and statuses without copying credentials."""

    def __init__(self, revoked: Event | None = None) -> None:
        """Optionally wait for the correlated bundle's real request_finished receiver.

        :param revoked: Revocation event when this call simulates a token change.
        :return: None. Example: empty statuses before tool execution.
        """
        self.statuses: list[tuple[str, int]] = []
        self.bundle: dict = {}
        self.receipts: list[dict] = []
        self.revoked = revoked

    def record(self, response: httpx.Response) -> None:
        """Observe actual HTTP responses and ensure revocation precedes the next call.

        :param response: Genuine httpx response. Example: successful bundle POST.
        :return: None. Example: HTTP 401 recorded for a failed receipt.
        :raises AssertionError: The correlated server revocation timed out.
        """
        path = response.request.url.path
        self.statuses.append((path, response.status_code))
        if path in _BUNDLES.values() and response.is_success:
            response.read()
            self.bundle = response.json()
            if self.revoked is not None:
                # The body must drain before Django can close the response and signal.
                assert self.revoked.wait(
                    SIGNAL_WAIT_SECONDS
                ), "The real bundle did not finish."
        elif path == _RECEIPT:
            receipt = json.loads(response.request.content)
            assert response.headers["X-Request-ID"] == receipt["event_identity"]
            self.receipts.append(receipt)


async def _assert_facade_export_failed(
    dataset: CedarDataset,
    factory: MCPClientFactory,
    entity: ExportKind,
    setup: _ExportSetup,
) -> None:
    """Prove the registered facade consumed a genuine bundle and sent no receipt.

    :param dataset: Actual Cedar fixtures. Example: protected body and tokens.
    :param factory: Real registered facade context. Example: loopback HTTP.
    :param entity: Existing export tool kind. Example: "playbook".
    :param setup: Real obstruction and output expectations. Example: mirror failure.
    :return: None. Example: earlier canonical files exactly match that live bundle.
    :raises AssertionError: Tool result, output or receipt observations differ.
    """
    async with factory.open(actor_username=_ACTOR, entrypoint="facade") as session:
        observation = _ExportObservation()
        get_client().event_hooks["response"].append(observation.record)
        result = await session.client.call_tool(
            f"export_{entity}_to_local",
            setup.arguments,
            raise_on_error=False,
        )
    message = _tool_error(result, setup.error_text)
    await sync_to_async(assert_no_private_data)(
        dataset, message, extras=(str(setup.workspace),)
    )
    assert factory.request_paths == [("POST", _BUNDLES[entity])]
    assert observation.statuses == [(_BUNDLES[entity], HTTPStatus.OK)]
    expected = _bundle_files(
        entity, observation.bundle, setup.workspace, setup.target, setup.mirror
    )
    _assert_failed_files(setup, expected)


def _install_export_rule() -> None:
    """Attach an actual linked rule so mirror and ADE requests have concrete outputs.

    :return: None. Example: an explicit .mdc export becomes available.
    :raises ValueError: Rule or fixture activity could not be persisted.
    """
    rule = Rule.objects.create(
        playbook_id=_PLAYBOOK,
        title="S46 export checks",
        slug=_RULE_SLUG,
        content="Inspect the exported workflow files.",
        always_apply=False,
    )
    Activity.objects.get(pk=_ACTIVITY).rules.add(rule)


def _playbook_export_options(mirror: Path) -> dict[str, object]:
    """Request a real mirror and both file-based ADE copies.

    :param mirror: Confined approved mirror root. Example: workspace / "mirror".
    :return: Existing registered tool arguments. Example: sync_root_rules=True.
    """
    return {
        "additional_targets": [str(mirror)],
        "sync_root_rules": True,
        "ade_targets": ["devin"],
        "ade_target": "cursor",
        "force_apply": True,
    }


def _prepare_failed_export(
    actor: User,
    workspace: Path,
    entity: ExportKind,
    failure: str,
) -> _ExportSetup:
    """Use genuine bundle filenames to place a real filesystem conflict.

    :param actor: Authorized Cedar reader. Example: Maria.
    :param workspace: Pytest-owned workspace. Example: tmp_path.
    :param entity: Existing tool kind. Example: "playbook".
    :param failure: Required conflict or escape. Example: "rules_parent".
    :return: Artifact expectation and tool inputs. Example: blocked rules parent.
    :raises AssertionError: A needed canonical, mirror or ADE output is unavailable.
    """
    workspace = workspace.resolve()
    target = workspace / (
        ".cursor/playbooks" if entity == "playbook" else ".windsurf/workflows"
    )
    mirror = workspace / "mirror"
    folder = "../../outside" if failure == "traversal" else _EXPORT_FOLDER
    options = _playbook_export_options(mirror) if entity == "playbook" else {}
    reference = _fetch_reference_bundle(actor, entity, _EXPORT_FOLDER, options)
    files = _bundle_files(entity, reference, workspace, target, mirror)
    blocked = _obstruct_export(failure, workspace, target, mirror, reference)
    arguments = {
        f"{entity}_id": _EXPORT_IDS[entity],
        "target_directory": str(target),
        "folder_name": folder,
        **options,
    }
    return _ExportSetup(
        workspace,
        target,
        mirror,
        folder,
        blocked,
        arguments,
        files,
        _snapshot_files(workspace),
        frozenset(workspace.rglob("*")),
        failure in _CONFINEMENT_FAILURES,
        _EXPORT_FAILURE_TEXT[failure],
    )


def _fetch_reference_bundle(
    actor: User,
    entity: ExportKind,
    folder: str,
    options: Mapping[str, object],
) -> dict:
    """Read a real server-generated reference bundle without doing a filesystem export.

    :param actor: Authorized token identity. Example: Maria.
    :param entity: Bundle kind. Example: "workflow".
    :param folder: Actual folder name. Example: "cedar".
    :param options: Real ADE options. Example: cursor and devin for playbook.
    :return: Bundle payload. Example: workflow_files and linked rule_files.
    :raises AssertionError: Backend did not generate an eligible reference.
    """
    client = _receipt_client("token", actor)
    data = {key: value for key, value in options.items() if key != "additional_targets"}
    response = client.post(
        _BUNDLES[entity],
        {"folder_name": folder, **data},
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.OK
    return response.json()


def _bundle_files(
    entity: ExportKind,
    bundle: dict,
    workspace: Path,
    target: Path,
    mirror: Path,
) -> dict[Path, bytes]:
    """Map genuine response entries onto the selected export roots.

    :param entity: Export kind. Example: "workflow".
    :param bundle: Genuine export response. Example: a linked rule bundle.
    :param workspace: Owned common root. Example: pytest tmp_path.
    :param target: Approved canonical root. Example: .cursor/playbooks.
    :param mirror: Approved mirror root. Example: workspace / "mirror".
    :return: Ordered expected file bytes. Example: canonical Markdown then copies.
    :raises AssertionError: The fixture did not include requested output kinds.
    """
    assert bundle["rule_files"], "The real Cedar rule was absent from the bundle."
    folder = _EXPORT_FOLDER
    if entity == "workflow":
        return {
            **_markdown_entries(target / folder, bundle["workflow_files"]),
            **_markdown_entries(target.parent / "rules", bundle["rule_files"]),
        }
    tree = _canonical_playbook_files(bundle)
    ade = bundle["ade_rule_files"]
    assert {entry["ade_target"] for entry in ade} == {"cursor", "devin"}
    return {
        **{target / folder / path: content for path, content in tree.items()},
        **{mirror / folder / path: content for path, content in tree.items()},
        **{workspace / entry["path"]: entry["content"].encode() for entry in ade},
    }


def _markdown_entries(parent: Path, entries: list[dict]) -> dict[Path, bytes]:
    """Associate real response entry filenames and bytes with their requested root.

    :param parent: Approved directory. Example: sibling linked rules.
    :param entries: Actual markdown response rows. Example: workflow_files.
    :return: Expected content by destination path. Example: one _workflow.md entry.
    """
    return {parent / item["filename"]: item["content"].encode() for item in entries}


def _canonical_playbook_files(bundle: dict) -> dict[Path, bytes]:
    """Read ordered canonical file entries independently of the local writer.

    :param bundle: Actual playbook export DTO. Example: playbook_md and workflows.
    :return: Relative tree bytes. Example: playbook.md and rules/check.mdc.
    """
    files = _markdown_entries(Path(), [bundle["playbook_md"]])
    for directory in ("rule", "agent", "skill", "artifact"):
        files.update(
            _markdown_entries(Path(f"{directory}s"), bundle[f"{directory}_files"])
        )
    for workflow in bundle["workflows"]:
        files.update(
            _markdown_entries(Path(workflow["folder_name"]), workflow["workflow_files"])
        )
    return files


def _obstruct_export(
    failure: str,
    workspace: Path,
    target: Path,
    mirror: Path,
    bundle: dict,
) -> Path:
    """Install a real required-parent/file mismatch or an actual confinement escape.

    :param failure: Boundary to exercise. Example: "ade".
    :param workspace: Private pytest root. Example: tmp_path.
    :param target: Canonical root. Example: .cursor/playbooks.
    :param mirror: Secondary root. Example: mirror.
    :param bundle: Genuine filename source. Example: second workflow output.
    :return: Persistent existing obstruction. Example: regular file named rules.
    :raises AssertionError: Unexpected failure mode or missing reference.
    """
    if failure in _CONFINEMENT_FAILURES:
        return _install_escape(failure, workspace, target)
    destination = target / _EXPORT_FOLDER
    if failure in ("parent", "rules_parent"):
        blocked = destination if failure == "parent" else destination / "rules"
        blocked.parent.mkdir(parents=True)
        blocked.write_bytes(_FILE_BLOCKER)
        return blocked
    if failure == "partial":
        blocked = destination / bundle["workflow_files"][1]["filename"]
    elif failure == "mirror":
        blocked = mirror / _EXPORT_FOLDER / bundle["playbook_md"]["filename"]
    else:
        assert failure == "ade"
        blocked = workspace / bundle["ade_rule_files"][-1]["path"]
    blocked.mkdir(parents=True)
    return blocked


def _install_escape(failure: str, workspace: Path, target: Path) -> Path:
    """Preserve an outside sentinel while testing traversal or a directory alias.

    :param failure: Actual invalid path. Example: "symlink".
    :param workspace: Owned common parent. Example: tmp_path.
    :param target: Canonical export root. Example: workspace / ".cursor/playbooks".
    :return: Outside sentinel path. Example: workspace / "outside/unchanged.md".
    """
    outside = workspace / "outside"
    outside.mkdir()
    sentinel = outside / "unchanged.md"
    sentinel.write_bytes(_FILE_BLOCKER)
    if failure == "symlink":
        target.mkdir(parents=True)
        (target / _EXPORT_FOLDER).symlink_to(outside, target_is_directory=True)
    return sentinel


def _legacy_export(actor: User, setup: _ExportSetup, entity: ExportKind) -> None:
    """Invoke the existing ORM-backed local exporters under real actor access.

    :param actor: Authorized Cedar reader. Example: Maria.
    :param setup: Real failing destinations. Example: a requested mirror.
    :param entity: Service entrypoint. Example: "workflow".
    :return: None. Example: any successful export would make the test fail.
    :raises OSError: An actual filesystem operation fails.
    :raises ValueError: The confinement guard rejects a destination.
    """
    if entity == "workflow":
        WorkflowExportService.export_workflow_to_markdown(
            _WORKFLOW, str(setup.target), folder_name=setup.folder, user=actor
        )
    else:
        PlaybookExportService.export_playbook_to_local(
            _PLAYBOOK,
            str(setup.target),
            folder_name=setup.folder,
            user=actor,
            **_playbook_export_options(setup.mirror),
        )


def _snapshot_files(workspace: Path) -> FileSnapshot:
    """Record real files with exact bytes and nanosecond modification timestamps.

    :param workspace: Owned recursively scanned tree. Example: the complete export.
    :return: Snapshot by existing regular path. Example: {path: (data, timestamp)}.
    """
    return {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in workspace.rglob("*")
        if not path.is_symlink() and path.is_file()
    }


def _assert_failed_files(
    setup: _ExportSetup,
    files: Mapping[Path, bytes] | None = None,
) -> None:
    """Distinguish confinement rejection, early write failure and measured partial writes.

    :param setup: Actual obstruction and before-image. Example: a regular rules parent.
    :param files: Genuine same-invocation HTTP bundle when recorded. Example: facade.
    :return: None. Example: earlier canonical bytes survived a late ADE failure.
    :raises AssertionError: Unexpected writes, removal, exposure or changed sentinel.
    """
    current = _snapshot_files(setup.workspace)
    assert {
        path: current[path] for path in setup.previous_files
    } == setup.previous_files
    if setup.confined_failure:
        assert frozenset(setup.workspace.rglob("*")) == setup.prior_paths
        return
    expected = {}
    for path, content in (files if files is not None else setup.expected_files).items():
        if path == setup.blocked or setup.blocked in path.parents:
            break
        expected[path] = content
    actual = {
        path: data
        for path, (data, _) in current.items()
        if path not in setup.previous_files
    }
    if files is None:
        # The real legacy generator stamps the current minute in both invocations.
        assert _mask_export_timestamp(actual) == _mask_export_timestamp(expected)
    else:
        assert actual == expected
    assert setup.blocked.exists()


def _mask_export_timestamp(files: Mapping[Path, bytes]) -> dict[Path, bytes]:
    """Normalize only the separately generated export date when comparing references.

    :param files: Actual path/byte map. Example: legacy Markdown output.
    :return: Content with generated minute normalized. Example: timestamp marker.
    """
    return {
        path: re.sub(
            rb"(?m)^(\*\*Export Date\*\*: )\d{4}-\d\d-\d\d \d\d:\d\d UTC$",
            rb"\1<export minute>",
            content,
        )
        for path, content in files.items()
    }


async def _exercise_receipt_recovery(
    dataset: CedarDataset,
    live_server: LiveServer,
    workspace: Path,
) -> tuple[UUID, int, str]:
    """Complete files, force a real receipt 401, then restore auth for the original UUID.

    :param dataset: Cedar consumer and author. Example: Maria and Mike.
    :param live_server: Actual HTTP backend. Example: pytest-django localhost.
    :param workspace: Owned export tree. Example: tmp_path.
    :return: Operation UUID, file count and deleted token for redaction checks.
    :raises AssertionError: HTTP lifecycle, file preservation or exact persistence fails.
    """
    workspace = workspace.resolve()
    actor, author = (dataset.users_by_username[name] for name in (_ACTOR, _AUTHOR))
    await sync_to_async(_install_recovery_content)()
    before = await sync_to_async(snapshot_global_ledger)()
    factory = _mcp_factory(dataset, live_server)
    target = workspace / ".windsurf/workflows"
    async with factory.open(actor_username=_ACTOR, entrypoint="facade") as session:
        token = await sync_to_async(Token.objects.get)(user=actor)
        tool_result, observed = await _run_revoked_export(
            session, get_client(), actor, target
        )
        message = _tool_error(
            tool_result, r"files were written.*retry only the receipt"
        )
        action = _assert_outage_identity(observed, message)
        await sync_to_async(assert_no_private_data)(
            dataset, message, extras=(token.key, str(workspace))
        )
        files = _verify_completed_files(observed.bundle, workspace, target)
        await sync_to_async(_assert_no_awards)(dataset, before)
        receipt_result = await _retry_original_receipt(token, actor, action)
    _assert_recovered_export(factory, observed, action, receipt_result)
    assert _snapshot_files(workspace) == files
    await sync_to_async(_assert_added_pairs)(
        before, actor, author, observed.receipts[0], "export"
    )
    print(
        f"real export receipt recovery: HTTP statuses={observed.statuses} action={action} files={len(files)}"
    )
    return action, len(files), token.key


def _install_recovery_content() -> None:
    """Place real workflow and rule content in the actual recoverable bundle.

    :return: None. Example: the recovery trace can detect emitted prompt text.
    :raises AssertionError: The real exportable activity is missing.
    """
    _install_export_rule()
    assert Activity.objects.filter(pk=_ACTIVITY).update(guidance=PRIVATE_BODY) == 1


def _verify_completed_files(
    bundle: dict, workspace: Path, target: Path
) -> FileSnapshot:
    """Compare the genuine completed file tree to the one actual delivered bundle.

    :param bundle: Server's real workflow export response. Example: workflow files and rules.
    :param workspace: Outer test-owned workspace. Example: tmp_path.resolve().
    :param target: Expected canonical workflow parent. Example: .windsurf/workflows.
    :return: Exact bytes and mtimes for later no-rewrite verification.
    :raises AssertionError: A canonical or linked rule file differs.
    """
    files = _snapshot_files(workspace)
    expected = _bundle_files(
        "workflow", bundle, workspace, target, workspace / "mirror"
    )
    assert any(PRIVATE_BODY.encode() in content for content in expected.values())
    assert {path: data for path, (data, _) in files.items()} == expected
    return files


async def _run_revoked_export(
    session: MCPClientSession,
    http: httpx.Client,
    actor: User,
    target: Path,
) -> tuple[CallToolResult, _ExportObservation]:
    """Invoke one real export under a signal-bounded real credential change.

    :param session: Already registered and authenticated facade client.
    :param http: The shared actual facade HTTP client. Example: get_client().
    :param actor: Token owner. Example: Maria.
    :param target: Actual export path. Example: .windsurf/workflows.
    :return: Registered call result and genuine response statuses.
    :raises AssertionError: The real bundle never completes or revokes the token.
    """
    request_id = str(uuid4())
    http.headers["X-Request-ID"] = request_id
    with revoke_token_on_next_request_finish(
        actor.pk,
        path=_BUNDLES["workflow"],
        request_id=request_id,
    ) as revoked:
        observation = _ExportObservation(revoked)
        http.event_hooks["response"].append(observation.record)
        result = await session.client.call_tool(
            "export_workflow_to_local",
            {
                "workflow_id": _WORKFLOW,
                "target_directory": str(target),
                "folder_name": _EXPORT_FOLDER,
            },
            raise_on_error=False,
        )
    return result, observation


def _assert_outage_identity(observed: _ExportObservation, message: str) -> UUID:
    """Identify the only recoverable UUID from both HTTP and the real tool error.

    :param observed: Actual transport observations. Example: POST 200 then POST 401.
    :param message: Safe remote tool error text. Example: retry only the receipt.
    :return: Original export operation UUID. Example: a generated UUID4.
    :raises AssertionError: Bundle, 401 receipt or operation identity is inaccurate.
    """
    assert observed.statuses == [
        (_BUNDLES["workflow"], HTTPStatus.OK),
        (_RECEIPT, HTTPStatus.UNAUTHORIZED),
    ]
    identity = re.search(r"event_identity=([0-9a-f-]{36})", message)
    assert identity
    action = UUID(identity.group(1))
    assert action.version == 4
    assert observed.receipts == [
        {
            "entity_type": "workflow",
            "entity_id": _WORKFLOW,
            "event_identity": str(action),
            "channel": "export",
        }
    ]
    return action


async def _retry_original_receipt(
    token: Token, actor: User, action: UUID
) -> dict[str, object]:
    """Restore the deleted token and use the existing receipt-only dispatcher.

    :param token: Originally used real token. Example: Maria's key.
    :param actor: Actual token owner. Example: Maria.
    :param action: Original failed receipt UUID. Example: the UUID returned by the call.
    :return: Actual accepted receipt outcome. Example: status applied, created count two.
    :raises AssertionError: The original token was never revoked.
    """
    assert not await Token.objects.filter(user=actor).aexists()
    await Token.objects.acreate(key=token.key, user=actor)
    return await sync_to_async(_post_consumption_receipt)(
        entity_type="workflow",
        entity_id=_WORKFLOW,
        event_identity=action,
        channel="export",
    )


def _assert_recovered_export(
    factory: MCPClientFactory,
    observed: _ExportObservation,
    identity: UUID,
    result: Mapping[str, object],
) -> None:
    """Check the receipt-only 200 follows a real 401 with the exact original payload.

    :param factory: Actual facade transport. Example: observed paths and methods.
    :param observed: Actual transport trace. Example: bundle, 401 and retry.
    :param identity: Original export UUID. Example: returned recovery identifier.
    :param result: Parsed real token response. Example: applied.
    :return: None. Example: exactly one receipt-only recovery request.
    :raises AssertionError: Rewriting, changed UUID or receipt acknowledgement mismatch.
    """
    assert factory.request_paths == [
        ("POST", _BUNDLES["workflow"]),
        ("POST", _RECEIPT),
        ("POST", _RECEIPT),
    ]
    assert observed.statuses == [
        (_BUNDLES["workflow"], HTTPStatus.OK),
        (_RECEIPT, HTTPStatus.UNAUTHORIZED),
        (_RECEIPT, HTTPStatus.OK),
    ]
    first_receipt, retry = observed.receipts
    assert first_receipt == retry
    assert result["event_identity"] == str(identity)
    assert result["status"] == "applied" and result["created_count"] == 2


def _stdio_failure_case(
    dataset: CedarDataset,
    workspace: Path,
    failure: str,
) -> tuple[MCPCase, str]:
    """Prepare real registered calls with a genuine denied target or file obstruction.

    :param dataset: Cedar token actors and private playbook. Example: Elena.
    :param workspace: Owned child working directory. Example: tmp_path.
    :param failure: Failure surface. Example: "failed_export".
    :return: Actual stdio call arguments and safe error pattern.
    :raises AssertionError: Expected action is unavailable.
    """
    if failure == "denied_read":
        actor, target = prepare_denied_target(dataset, "playbook", "private")
        return MCPCase(
            failure,
            actor.username,
            "get_playbook",
            failure,
            {"playbook_id": target},
            _detail_route("playbook", target),
            {},
        ), _detail_denial_text("playbook", "private")
    assert failure == "failed_export"
    actor = dataset.users_by_username[_ACTOR]
    _install_export_rule()
    setup = _prepare_failed_export(actor, workspace, "workflow", "parent")
    return (
        MCPCase(
            failure,
            actor.username,
            "export_workflow_to_local",
            failure,
            setup.arguments,
            _BUNDLES["workflow"],
            {},
        ),
        setup.error_text,
    )


def _assert_stdio_error(stdio: StdioMCPClient, expected: str) -> Mapping[str, object]:
    """Check the captured protocol response describes the intended tool-level failure.

    :param stdio: Actual closed child and raw parsed protocol replies.
    :param expected: Stable safe error text. Example: "not found".
    :return: Actual response envelope. Example: isError=true.
    :raises AssertionError: Tool failure is missing, malformed or unsafe.
    """
    envelope = stdio.stdout_messages[-1]
    assert envelope["id"] == 3 and envelope["jsonrpc"] == "2.0"
    result = envelope["result"]
    if not isinstance(result, dict) or result.get("isError") is not True:
        raise AssertionError("Expected a safe stdio tool error.")
    assert result.get("structuredContent") is None
    content = result["content"]
    if len(content) != 1 or content[0]["type"] != "text":
        raise AssertionError("Expected one text block in the stdio tool error.")
    if not re.search(expected, content[0]["text"], re.IGNORECASE):
        raise AssertionError("Wrong stdio tool error classification.")
    return envelope


def _exercise_rejected_receipt_logs(
    caplog: LogCaptureFixture,
    client: DjangoClient,
    actor: User,
    private_id: int,
    surface: ReceiptSurface,
) -> None:
    """Check individual real receipt invocations and their correlated rejection beats.

    :param caplog: Actual production log messages. Example: token receipt records.
    :param client: Real authenticated client. Example: CSRF-valid Elena.
    :param actor: Authenticated reader. Example: Elena.
    :param private_id: Existing inaccessible activity ID.
    :param surface: Transport. Example: "token".
    :return: None. Example: two masked target denials and one invalid payload.
    :raises AssertionError: A correlated log beat or success exclusion is missing.
    """
    where = (
        "copy_success_receipt" if surface == "gui" else "ConsumptionReceiptView.post"
    )
    unavailable = "access_denied" if surface == "gui" else "target_unavailable"
    channel = "operation=gui_copy" if surface == "gui" else "channel=mcp_detail"
    attempts = (
        (private_id, unavailable),
        (MISSING_ENTITY_ID, unavailable),
        (_ACTIVITY, "invalid_payload"),
    )
    for target, reason in attempts:
        action, request_id = uuid4(), str(uuid4())
        payload = _receipt_selection(surface, target, action)
        forged = reason == "invalid_payload"
        if forged:
            payload.update(actor_id=actor.pk + 1, prompt=PRIVATE_BODY)
        response = _send_receipt(client, surface, payload, request_id=request_id)
        assert response.status_code == (
            HTTPStatus.BAD_REQUEST if forged else HTTPStatus.NOT_FOUND
        )
        _assert_receipt_log(
            caplog,
            where,
            request_id,
            actor.pk,
            channel,
            reason,
            action,
            target,
        )


def _assert_receipt_log(
    caplog: LogCaptureFixture,
    where: str,
    request_id: str,
    actor_id: int,
    channel: str,
    reason: str,
    action: UUID,
    target: int,
) -> None:
    """Require actual safe target or parser rejection records under one request ID.

    :param caplog: Actual collected logs. Example: owner receipt records.
    :param where: Exact existing boundary. Example: copy_success_receipt.
    :param request_id: Explicit HTTP correlation. Example: independent request UUID.
    :param actor_id: Authenticated actor. Example: Elena's PK.
    :param channel: Existing channel field spelling. Example: "operation=gui_copy".
    :param reason: Stable controlled rejection. Example: "invalid_payload".
    :param action: Actual action UUID. Example: payload identifier.
    :param target: Stored or missing target primary key. Example: 900046.
    :return: None. Example: branch with safe details and no success.
    :raises AssertionError: Wrong correlation, absent beat or evidence of a success.
    """
    event_key = "action_uuid" if channel == "operation=gui_copy" else "event_identity"
    trace = f"request_id={request_id}"
    entry = ("| entry |", trace, f"actor_id={actor_id}")
    rejection = (
        "| branch |",
        trace,
        f"reason={reason}",
        "awards=0",
        f"{event_key}={action}",
    )
    beats = {"entry": (*entry, channel) if channel == "operation=gui_copy" else entry}
    if reason == "invalid_payload":
        beats["parser"] = rejection
    else:
        target_trace = ("entity_type=activity", f"entity_id={target}")
        beats["resolver"] = (*rejection, *target_trace)
        if channel != "operation=gui_copy":
            beats["channel"] = (
                "| validation |",
                trace,
                f"actor_id={actor_id}",
                channel,
                *target_trace,
            )
    assert_log_story(caplog, where=where, beats=beats)
    linked = [
        record.getMessage() for record in caplog.records if trace in record.getMessage()
    ]
    assert not any(
        "| exit |" in message or "status=applied" in message for message in linked
    )


def _assert_filesystem_reject_log(
    caplog: LogCaptureFixture, workspace: Path, actor: User
) -> None:
    """Require the real partial filesystem failure's count, UUID and unsent receipt.

    :param caplog: Actual export owner logs captured at INFO.
    :param workspace: Actual temporary destinations. Example: a regular rules file.
    :param actor: Real authorized export actor. Example: Maria.
    :return: None. Example: one written file, no receipt.
    :raises AssertionError: Export logs claim completion or lose invocation identity.
    """
    _install_export_rule()
    setup = _prepare_failed_export(actor, workspace, "playbook", "rules_parent")
    with pytest.raises(OSError, match=setup.error_text):
        _legacy_export(actor, setup, "playbook")
    _assert_failed_files(setup)
    where = "PlaybookExportService.export_playbook_to_local"
    messages = [r.getMessage() for r in caplog.records if where in r.getMessage()]
    entry = next(message for message in messages if "| entry |" in message)
    identity = re.search(r"operation_uuid=([0-9a-f-]{36})", entry)
    assert identity and UUID(identity.group(1)).version == 4
    trace = f"operation_uuid={identity.group(1)}"
    assert_log_story(
        caplog,
        where=where,
        beats={
            "entry": ("| entry |", trace, f"actor_id={actor.pk}"),
            "error": (
                "| error |",
                trace,
                "reason=filesystem_failure",
                "completed_file_count=1",
                "receipt_sent=false",
            ),
        },
    )
    assert not any(
        "files_written=true" in msg or "outcome=awarded" in msg for msg in messages
    )


def _assert_recovery_story(
    caplog: LogCaptureFixture,
    identity: UUID,
    file_count: int,
    actor_id: int,
) -> None:
    """Require the correlated completed-files, 401, retry and staged pair beats in order.

    :param caplog: Actual facade/receipt/ledger INFO records.
    :param identity: Original operation UUID. Example: parsed from the tool error.
    :param file_count: Number of observed completed actual files.
    :param actor_id: Authenticated retry actor. Example: Maria's PK.
    :return: None. Example: one staged pair and one accepted HTTP response.
    :raises AssertionError: Missing beats, changed identity or premature success.
    """
    event = f"event_identity={identity}"
    trace = ("entity_type=workflow", f"entity_id={_WORKFLOW}", "channel=export", event)
    before = _export_failure_beats(trace, f"file_count={file_count}")
    after = _receipt_retry_beats(trace, identity, actor_id)
    _assert_ordered_beats(caplog, before + after)
    accepted = (
        msg
        for record in caplog.records
        if "status=applied" in (msg := record.getMessage()) and event in msg
    )
    assert len(tuple(accepted)) == 1
    assert not any(
        message.startswith("export_receipt | exit |") and event in message
        for message in (record.getMessage() for record in caplog.records)
    )


def _export_failure_beats(
    trace: tuple[str, ...],
    count: str,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Describe existing operations before the independently retried receipt.

    :param trace: Shared action metadata. Example: workflow, ID, channel, UUID.
    :param count: Verified complete file count. Example: "file_count=5".
    :return: Ordered existing owner beats. Example: writer, 401, receipt error.
    """
    return (
        ("facade_export", ("| processing |", *trace, count, "files_written=true")),
        (
            "_post_consumption_receipt",
            ("| branch |", *trace, "reason=receipt_rejected", "status_code=401"),
        ),
        (
            "export_receipt",
            ("| error |", *trace, count, "files_written=true", "receipt_status=failed"),
        ),
    )


def _receipt_retry_beats(
    trace: tuple[str, ...],
    identity: UUID,
    actor_id: int,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Describe the parsed receipt and pending pair before the HTTP acknowledgement.

    :param trace: Shared action metadata. Example: workflow, ID, channel, UUID.
    :param identity: Original export action. Example: same failed and retried UUID.
    :param actor_id: Authenticated learner. Example: Maria's PK.
    :return: Ordered existing receipt and ledger owner beats.
    """
    actor, request = f"actor_id={actor_id}", f"request_id={identity}"
    canonical = f"event_identity=consumption:export:{actor_id}:{identity}"
    view = "ConsumptionReceiptView.post"
    return (
        (view, ("| entry |", request, actor)),
        (view, ("| validation |", *trace, request, actor)),
        (
            "KarmaService.award_successful_consumption",
            ("| processing |", canonical, "transaction=pending", "status=staged"),
        ),
        (view, ("| exit |", *trace, actor, "status=applied", "created_count=2")),
    )


def _assert_ordered_beats(
    caplog: LogCaptureFixture,
    beats: tuple[tuple[str, tuple[str, ...]], ...],
) -> None:
    """Require each distinct owner beat to occur in its actual chronological order.

    :param caplog: Actual correlated log stream. Example: producer and receipt INFO.
    :param beats: Existing owner markers plus exact words in each record.
    :return: None. Example: completion precedes the confirmed receipt failure.
    :raises AssertionError: Required ordering or a declared beat is missing.
    """
    messages = [record.getMessage() for record in caplog.records]
    indices = []
    for where, needles in beats:
        assert_log_story(caplog, where=where, beats={"recovery": needles})
        indices.append(
            next(
                index
                for index, message in enumerate(messages)
                if where in message and all(needle in message for needle in needles)
            )
        )
    assert indices == sorted(set(indices))


def _log_text(caplog: LogCaptureFixture) -> str:
    """Read actual captured messages for confidentiality checks.

    :param caplog: Owner logger records. Example: INFO receipt traces.
    :return: Combined message text. Example: one line per actual record.
    """
    return "\n".join(record.getMessage() for record in caplog.records)


def _print_story(caplog: LogCaptureFixture, scopes: tuple[str, ...]) -> None:
    """Expose already checked owner beats for an opt-in pytest evidence recording.

    :param caplog: Actual captured owner logs. Example: correlated receipt traces.
    :param scopes: Existing operation messages whose exact text is safe to print.
    :return: None. Example: captured output under normal pytest execution.
    """
    for record in caplog.records:
        message = record.getMessage()
        if any(message.startswith(scope + " |") for scope in scopes):
            print(message)
