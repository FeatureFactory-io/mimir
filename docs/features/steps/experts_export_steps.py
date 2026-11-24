"""Living-spec checks for completed local MCP exports and their awards."""

from __future__ import annotations

import json
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

import httpx
from asgiref.sync import async_to_sync
from behave import given, then, when
from behave.runner import Context
from django.db import connection
from pytest_django.live_server_helper import LiveServer

from mcp_integration.facade.client import get_client
from methodology.models import EventChannel, KarmaAward
from tests.support.karma_mcp import MCPClientFactory, decode_tool_payload

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
    factory: MCPClientFactory, actor_username: str, root: Path
) -> tuple[dict[str, object], UUID, set[Path]]:
    """Run the registered facade and retain its real HTTP request evidence.

    :param factory: Bound to the real test-owned Django live server.
    :param actor_username: Cedar token owner. Example: "mrodriguez".
    :param root: Authorized temporary workspace. Example: Path("/tmp/t").
    :return: Actual tool payload, receipt UUID and files present at receipt time.
    :raises AssertionError: Missing successful response or expected HTTP requests.
    """
    receipts: list[tuple[dict[str, object], set[Path]]] = []
    async with factory.open(
        actor_username=actor_username, entrypoint="facade"
    ) as session:
        get_client().event_hooks["request"].append(
            partial(_observe_receipt, receipts, root)
        )
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
) -> None:
    """Observe real receipt content and files at dispatch without handling requests.

    :param receipts: Destination for the observed receipt and file paths.
    :param root: Owned workspace that may already contain export files.
    :param request: Actual outgoing request. Example: the token-authenticated POST.
    :return: None after recording receipt fields without headers or credentials.
    :raises ValueError: The outgoing receipt lacks valid JSON.
    """
    if request.url.path == _RECEIPT:
        receipts.append((json.loads(request.content), _export_files(root)))


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
    raise NotImplementedError()


@when("he exports his own workflow 6202")
def export_own_workflow(context: Context) -> None:
    """Execute actual own-workflow filesystem export with cleanup.

    :param context: Real Mike/token/ORM state. Example: workflow6202.
    :return: None. Example: real successful export result and files retained.
    :raises AssertionError: Authorization, source ownership or export fails.
    """
    raise NotImplementedError()


@then("his total remains 12450")
def assert_own_export_changes_no_karma(context: Context) -> None:
    """Verify complete bytes first, then all unchanged ledger projections.

    :param context: Actual completed export state. Example: Mike/workflow6202.
    :return: None. Example: Mike12450, GUI47 and global ledger unchanged.
    :raises AssertionError: Incomplete output or any award/projection mutation.
    """
    raise NotImplementedError()
