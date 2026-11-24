"""Living-spec checks for completed local MCP exports and their awards."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import UUID

import httpx
from asgiref.sync import async_to_sync
from behave import given, then, when
from behave.runner import Context
from django.db import connection
from pytest_django.live_server_helper import LiveServer
from rest_framework.authtoken.models import Token

from mcp_integration.facade.client import get_client
from methodology.models import EventChannel, KarmaAward
from tests.support.experts_exports import (
    assert_complete_self_export,
    assert_owned_export_source,
    assert_self_export_karma_unchanged,
    capture_export_karma_state,
)
from tests.support.karma_mcp import MCPClientFactory, MCPDataset, decode_tool_payload

logger = logging.getLogger(__name__)

_WORKFLOW_ID = 6202
_ACTIVITY_ID = 6203
_FOLDER = "cedar"
_BUNDLE = f"/api/workflows/{_WORKFLOW_ID}/export/"
_RECEIPT = "/api/consumption-receipts/"
_POINTS_PER_AWARD = 5


@when("she exports Mike's public released workflow 6202 into multiple local files")
def export_mikes_workflow(context: Context) -> None:
    """Call the real registered export tool and retain actual temp-file evidence.

    :param context: Isolated Cedar/token context. Example: context.cedar_dataset.
    :return: None with export result/event evidence stored. Example: None.
    :raises AssertionError: If the original released workflow or export differs.
    """
    dataset = context.mcp_dataset
    workflow = dataset.cedar.workflows_by_pk[_WORKFLOW_ID]
    mike = dataset.cedar.users_by_username["mchen"]
    assert workflow.playbook.author_id == mike.pk
    assert (workflow.playbook.status, workflow.playbook.visibility) == (
        "released",
        "public",
    )
    assert connection.vendor == "sqlite" and connection.is_in_memory_db()
    workspace = TemporaryDirectory(prefix="mimir-experts-export-")
    context.add_cleanup(workspace.cleanup)
    root = Path(workspace.name).resolve()
    server = LiveServer("127.0.0.1")
    try:
        factory = MCPClientFactory(dataset, server.url, [])
        result, event_identity, receipt_files = async_to_sync(_call_workflow_export)(
            factory, context.mcp_actor.username, root
        )
    finally:
        server.stop()
    context.export_root, context.export_result = root, result
    context.export_event_identity = event_identity
    context.export_receipt_files = receipt_files


async def _call_workflow_export(
    factory: MCPClientFactory,
    actor_username: str,
    root: Path,
    *,
    response_hook: Callable[[httpx.Response], None] | None = None,
    receipt_bytes: dict[Path, bytes] | None = None,
) -> tuple[dict[str, object], UUID, set[Path]]:
    """Run the registered facade and retain its real HTTP request evidence.

    :param factory: Bound to the real test-owned Django live server.
    :param actor_username: Cedar token owner. Example: "mrodriguez".
    :param root: Authorized temporary workspace. Example: Path("/tmp/t").
    :param response_hook: Optional observer for the actual HTTP responses.
    :param receipt_bytes: Optional output for exact file bytes at receipt dispatch.
    :return: Actual tool payload, receipt UUID and files present at receipt time.
    :raises AssertionError: Missing successful response or expected HTTP requests.
    """
    receipts: list[tuple[dict[str, object], set[Path]]] = []
    async with factory.open(
        actor_username=actor_username, entrypoint="facade"
    ) as session:
        hooks = get_client().event_hooks
        hooks["request"].append(
            partial(_observe_receipt, receipts, root, receipt_bytes=receipt_bytes)
        )
        if response_hook is not None:
            hooks["response"].append(response_hook)
        result = decode_tool_payload(
            await session.client.call_tool(
                "export_workflow_to_local",
                {
                    "workflow_id": _WORKFLOW_ID,
                    "target_directory": str(root / "workflows"),
                    "folder_name": _FOLDER,
                },
            )
        )
        assert session.request_paths == [("POST", _BUNDLE), ("POST", _RECEIPT)]
    assert isinstance(result, dict) and result["status"] == "exported"
    [(receipt, files)] = receipts
    event_identity = UUID(str(receipt["event_identity"]))
    assert receipt == {
        "event_identity": str(event_identity),
        "entity_type": "workflow",
        "entity_id": _WORKFLOW_ID,
        "channel": EventChannel.EXPORT,
    }
    return result, event_identity, files


def _observe_receipt(
    receipts: list[tuple[dict[str, object], set[Path]]],
    root: Path,
    request: httpx.Request,
    *,
    receipt_bytes: dict[Path, bytes] | None = None,
) -> None:
    """Observe real receipt content and files at dispatch without handling requests.

    :param receipts: Destination for the observed receipt and file paths.
    :param root: Owned workspace that may already contain export files.
    :param request: Actual outgoing request. Example: the token-authenticated POST.
    :param receipt_bytes: Optional destination for observed bytes within the workspace.
    :return: None after recording receipt fields without headers or credentials.
    :raises AssertionError: A file to be observed escapes the workspace.
    :raises ValueError: The outgoing receipt lacks valid JSON.
    """
    if request.url.path == _RECEIPT:
        files = _export_files(root)
        receipts.append((json.loads(request.content), files))
        if receipt_bytes is not None:
            for path in files:
                assert path.resolve() == path and path.is_relative_to(root)
                receipt_bytes[path] = path.read_bytes()


def _export_files(root: Path) -> set[Path]:
    """Return real file paths under the owned workspace. Example: workflows/_workflow.md.

    :param root: Owned workspace to inspect.
    :return: Actual file paths present in the workspace.
    """
    return {path for path in root.rglob("*") if path.is_file()}


@then("the actual export files are written within the authorized export root")
def assert_confined_actual_export_files(context: Context) -> None:
    """Read actual produced files and verify each resolved authorized root.

    :param context: Context containing export result/root. Example: context.
    :return: None after actual filesystem assertions. Example: None.
    :raises AssertionError: If content is missing or any destination escapes.
    """
    root = context.export_root
    exported_root = root / "workflows" / _FOLDER
    result = context.export_result
    assert result["workflow_id"] == _WORKFLOW_ID
    assert result["export_path"] == str(exported_root)
    outputs = {exported_root / name for name in result["files_created"]}
    assert len(outputs) == len(result["files_created"]) > 1
    rules = {Path(path) for path in result["rule_export_paths"]}
    assert all(path.resolve().is_relative_to(exported_root) for path in outputs)
    assert all(path.resolve().is_relative_to(root / "rules") for path in rules)
    assert outputs | rules == _export_files(root) == context.export_receipt_files
    contents = {path: path.read_text(encoding="utf-8") for path in outputs | rules}
    assert all(text.strip() for text in contents.values())
    cedar = context.cedar_dataset
    workflow = cedar.workflows_by_pk[_WORKFLOW_ID]
    assert f"# {workflow.name}" in contents[exported_root / "_workflow.md"]
    activity = cedar.activities_by_pk[_ACTIVITY_ID]
    assert any(f"# Activity: {activity.name}" in contents[path] for path in outputs)


@then("the award is per successful call rather than per generated file")
def assert_one_export_award_pair(context: Context) -> None:
    """Verify exactly two five-point rows share one export event UUID.

    :param context: Baseline and actual completed export. Example: context.
    :return: None after pair/channel/count assertions. Example: None.
    :raises AssertionError: If files or nested content multiplied awards.
    """
    actor = context.mcp_actor
    event_identity = context.export_event_identity
    identity = f"consumption:{EventChannel.EXPORT}:{actor.pk}:{event_identity}"
    playbook = context.cedar_dataset.workflows_by_pk[_WORKFLOW_ID].playbook
    before = context.mcp_awards_before
    prior_pks = [row["id"] for row in before]
    ledger = KarmaAward.objects.order_by("pk")
    assert list(ledger.filter(pk__in=prior_pks).values()) == before
    new = list(ledger.exclude(pk__in=prior_pks))
    assert len(new) == 2
    assert {(row.recipient_id, row.source_kind, row.points) for row in new} == {
        (actor.pk, KarmaAward.SourceKind.LEARNING, _POINTS_PER_AWARD),
        (playbook.author_id, KarmaAward.SourceKind.CONSUMPTION, _POINTS_PER_AWARD),
    }
    for row in new:
        assert row.event_identity == identity
        assert (row.event_channel, row.category) == (
            EventChannel.EXPORT,
            playbook.category,
        )
        assert (row.playbook_id_snapshot, row.change_id_snapshot) == (playbook.pk, None)
        assert (row.entity_type_snapshot, row.entity_id_snapshot) == (
            "workflow",
            _WORKFLOW_ID,
        )
    assert new[0].occurred_at == new[1].occurred_at


@given("Mike has a valid MCP token")
def mike_has_valid_export_token(context: Context) -> None:
    """Resolve real Cedar Mike and validate his actual token.

    :param context: Isolated AT state. Example: context.cedar_dataset.
    :return: None. Example: authenticated Mike and global baseline captured.
    :raises AssertionError: Token, ownership or baseline totals are invalid.
    """
    cedar = context.cedar_dataset
    mike = assert_owned_export_source(cedar)
    context.self_export_karma_before = capture_export_karma_state()
    token, _ = Token.objects.get_or_create(user=mike)
    response = context.client.get(
        f"/api/workflows/{_WORKFLOW_ID}/", HTTP_AUTHORIZATION=f"Token {token.key}"
    )
    assert response.status_code == 200 and response.json()["id"] == _WORKFLOW_ID
    assert response.wsgi_request.user == mike
    context.mcp_actor = mike
    context.mcp_dataset = MCPDataset(cedar, {}, {})


@when("he exports his own workflow 6202")
def export_own_workflow(context: Context) -> None:
    """Execute actual own-workflow filesystem export with cleanup.

    :param context: Real Mike/token/ORM state. Example: workflow6202.
    :return: None. Example: real successful export result and files retained.
    :raises AssertionError: Authorization, source ownership or export fails.
    """
    assert connection.vendor == "sqlite" and connection.is_in_memory_db()
    workspace = TemporaryDirectory(prefix="mimir-experts-self-export-")
    context.add_cleanup(workspace.cleanup)
    root = Path(workspace.name).resolve()
    responses: dict[str, dict[str, Any]] = {}
    receipt_bytes: dict[Path, bytes] = {}
    server = LiveServer("127.0.0.1")
    try:
        factory = MCPClientFactory(context.mcp_dataset, server.url, [])
        started = datetime.now(UTC)
        result, identity, _ = async_to_sync(_call_workflow_export)(
            factory,
            context.mcp_actor.username,
            root,
            response_hook=partial(_observe_self_export_response, responses),
            receipt_bytes=receipt_bytes,
        )
        finished = datetime.now(UTC)
    finally:
        server.stop()
    context.export_root = root
    context.export_result = result
    context.export_event_identity = identity
    context.self_export_times = (started, finished)
    context.self_export_responses = responses
    context.self_export_receipt_bytes = receipt_bytes


def _observe_self_export_response(
    responses: dict[str, dict[str, Any]], response: httpx.Response
) -> None:
    """Capture successful bundle and receipt responses without substituting either.

    :param responses: Observed response bodies keyed by route. Example: _BUNDLE.
    :param response: Actual authenticated HTTP response. Example: export bundle.
    :return: None. Example: retain the served content and original receipt outcome.
    :raises AssertionError: An unexpected response or repeat requests occur.
    """
    path = response.request.url.path
    assert path in (_BUNDLE, _RECEIPT) and path not in responses
    assert response.status_code == 200
    response.read()
    responses[path] = response.json()


@then("his total remains 12450")
def assert_own_export_changes_no_karma(context: Context) -> None:
    """Verify complete bytes first, then all unchanged ledger projections.

    :param context: Actual completed export state. Example: Mike/workflow6202.
    :return: None. Example: Mike12450, GUI47 and global ledger unchanged.
    :raises AssertionError: Incomplete output or any award/projection mutation.
    """
    root = context.export_root
    started, finished = context.self_export_times
    responses = context.self_export_responses
    assert_complete_self_export(
        result=context.export_result,
        bundle=responses[_BUNDLE],
        workspace=root,
        started_at=started,
        finished_at=finished,
        folder=_FOLDER,
        facade=True,
    )
    receipt_bytes = context.self_export_receipt_bytes
    assert receipt_bytes == {path: path.read_bytes() for path in _export_files(root)}
    assert responses[_RECEIPT] == {
        "event_identity": str(context.export_event_identity),
        "status": "skipped",
        "created_count": 0,
        "reason": "self_consumption",
    }
    assert_self_export_karma_unchanged(context.self_export_karma_before)
    logger.info(
        "self_workflow_export_at | exit | actor_id=%s workflow_id=%s "
        "event_identity=%s file_count=%s receipt_reason=%s",
        context.mcp_actor.pk,
        _WORKFLOW_ID,
        context.export_event_identity,
        len(receipt_bytes),
        responses[_RECEIPT]["reason"],
    )
