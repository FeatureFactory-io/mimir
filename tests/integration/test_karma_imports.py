"""S44: real-file import certification without new runtime behavior."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from asgiref.sync import sync_to_async
from fastmcp.exceptions import ToolError
from pytest import LogCaptureFixture
from pytest_django.live_server_helper import LiveServer
from rest_framework.authtoken.models import Token

from methodology.models import Workflow
from methodology.services.workflow_import_service import WorkflowImportService
from tests.support.experts_data import CedarDataset
from tests.support.experts_imports import (
    ExpertsImportState,
    ImportCase,
    _assert_experts_unchanged,
    _assert_import_protocol,
    _prepare_import_case,
    _snapshot_experts_state,
)
from tests.support.experts_logs import capture_experts_logs
from tests.support.karma_mcp import (
    MCPClientFactory,
    MCPDataset,
    MCPEntrypoint,
    decode_tool_payload,
)
from tests.support.log_story import assert_log_story

pytestmark = pytest.mark.django_db(transaction=True)
_IMPORT_PARAMETERS = {"workflow_id", "source_directory", "auto_apply"}
_IMPORT_LOGGERS = (
    "mcp_integration.facade.tools_http",
    "methodology.services.workflow_import_service",
    "methodology.services.karma_service",
    "methodology.services.contribution_summary_service",
    "methodology.services.contribution_summary_boundary",
)


def test_import_service_t2_with_exported_files_generates_protocol_without_awards(
    tmp_path: Path,
    cedar_dataset: CedarDataset,
) -> None:
    """Certify real positive service import with unchanged global Experts state.

    :param tmp_path: Actual temporary files. Example: exported Cedar source.
    :param cedar_dataset: Real independent baseline. Example: Maria8200/Mike12450.
    :return: None. Example: positive draft protocol and zero new awards.
    :raises AssertionError: Protocol evidence or state invariants fail.
    """
    case = _prepare_import_case(cedar_dataset, tmp_path)
    before = _snapshot_experts_state()
    result = WorkflowImportService.import_workflow_from_markdown(
        case.workflow_id, str(case.source_directory)
    )
    _assert_import_outcome(result, case, before, applied=False)


async def test_import_facade_t1_with_owned_draft_returns_protocol_without_awards(
    tmp_path: Path, live_server: LiveServer, cedar_dataset: CedarDataset
) -> None:
    """Call the registered facade through real HTTP with Maria's actual token.

    :param tmp_path: Shared local source root. Example: temporary exported files.
    :param live_server: Isolated real backend. Example: http://localhost:54321.
    :param cedar_dataset: Existing actors. Example: Maria with a real test token.
    :return: None. Example: actual protocol returned and state unchanged.
    :raises AssertionError: Registration, content, response or state differs.
    """
    case = await sync_to_async(_prepare_import_case)(cedar_dataset, tmp_path)
    before = await sync_to_async(_snapshot_experts_state)()
    result = await _registered_import(case, cedar_dataset, live_server.url, "facade")
    await sync_to_async(_assert_import_outcome)(result, case, before, applied=False)


@pytest.mark.parametrize("auto_apply", [False, True])
async def test_import_legacy_registration_with_owned_draft_preserves_zero_awards(
    tmp_path: Path, auto_apply: bool, cedar_dataset: CedarDataset
) -> None:
    """Prove both legacy draft modes through actual FastMCP registration.

    :param tmp_path: Actual source files. Example: exported Markdown directory.
    :param auto_apply: Existing legacy option. Example: True.
    :param cedar_dataset: Real persisted baseline. Example: existing nonstaff Maria.
    :return: None. Example: requested application occurs with zero awards.
    :raises AssertionError: Protocol/application or global state differs.
    """
    case = await sync_to_async(_prepare_import_case)(cedar_dataset, tmp_path)
    before = await sync_to_async(_snapshot_experts_state)()
    result = await _registered_import(case, cedar_dataset, "", "legacy", auto_apply)
    assert result.get("auto_applied", False) is auto_apply
    if auto_apply:
        assert result["apply_result"]["status"] == "applied"
        assert result["apply_result"]["workflow_id"] == case.workflow_id
        assert result["apply_result"]["changes_applied"]["new"] == 1
        assert result["apply_result"]["changes_applied"]["total"] == 1
    await sync_to_async(_assert_import_outcome)(
        result, case, before, applied=auto_apply
    )


async def test_import_facade_with_auto_apply_flag_preserves_existing_protocol_only_semantics(
    tmp_path: Path, live_server: LiveServer, cedar_dataset: CedarDataset
) -> None:
    """Record the current facade compatibility behavior without fixing it.

    :param tmp_path: Actual import source. Example: source containing one new activity.
    :param live_server: Isolated HTTP backend. Example: local random port.
    :param cedar_dataset: Existing source actors. Example: Maria and Mike.
    :return: None. Example: protocol generated, no activity applied or award.
    :raises AssertionError: Existing response semantics or state differs.
    """
    case = await sync_to_async(_prepare_import_case)(cedar_dataset, tmp_path)
    before = await sync_to_async(_snapshot_experts_state)()
    result = await _registered_import(
        case, cedar_dataset, live_server.url, "facade", True
    )
    assert "auto_applied" not in result and "apply_result" not in result
    await sync_to_async(_assert_import_outcome)(result, case, before, applied=False)


def test_import_stdio_t3_with_success_returns_clean_jsonrpc_without_awards(
    tmp_path: Path, live_server: LiveServer
) -> None:
    """Certify actual facade stdio and real isolated backend/file effects.

    :param tmp_path: Subprocess-visible source. Example: absolute temporary path.
    :param live_server: Actual test backend. Example: localhost random port.
    :return: None. Example: protocol-only stdout and unchanged Experts state.
    :raises AssertionError: Transport, import result or global invariants fail.
    """
    raise NotImplementedError()


async def test_import_with_missing_source_rejects_without_awards(
    tmp_path: Path, live_server: LiveServer, cedar_dataset: CedarDataset
) -> None:
    """Prove existing rejection separately from the positive import contract.

    :param tmp_path: Parent of nonexistent source. Example: tmp_path / "missing".
    :param live_server: Isolated backend. Example: local test server.
    :param cedar_dataset: Actual fixture. Example: restored Maria8200.
    :return: None. Example: no protocol, application or Experts state changes.
    :raises AssertionError: Rejection or unchanged-state checks fail.
    """
    case = await sync_to_async(_prepare_import_case)(cedar_dataset, tmp_path)
    before = await sync_to_async(_snapshot_experts_state)()
    missing = replace(case, source_directory=tmp_path / "missing")
    with pytest.raises(ToolError, match="not exist"):
        await _registered_import(missing, cedar_dataset, live_server.url, "facade")
    assert not (case.source_directory / "_Upload_Protocol.md").exists()
    assert not (missing.source_directory / "_Upload_Protocol.md").exists()
    await sync_to_async(_assert_import_target)(case, applied=False)
    await sync_to_async(_assert_experts_unchanged)(before)


async def test_import_log_story_happy(
    tmp_path: Path,
    live_server: LiveServer,
    caplog: LogCaptureFixture,
    cedar_dataset: CedarDataset,
) -> None:
    """Assert actual import-window log fragments with assert_log_story.

    :param tmp_path: Real source root. Example: exported fixture directory.
    :param live_server: Real backend. Example: localhost random port.
    :param caplog: Actual captured logs. Example: detected changes and protocol path.
    :param cedar_dataset: Real source objects. Example: Mike's own workflow6202.
    :return: None. Example: all declared existing beats, no token/guidance body.
    :raises AssertionError: Missing required evidence or sensitive body logging.
    """
    case = await sync_to_async(_prepare_import_case)(cedar_dataset, tmp_path)
    before = await sync_to_async(_snapshot_experts_state)()
    caplog.clear()
    with capture_experts_logs(caplog, _IMPORT_LOGGERS):
        result = await _registered_import(
            case, cedar_dataset, live_server.url, "facade"
        )
    await sync_to_async(_assert_import_outcome)(result, case, before, applied=False)
    await sync_to_async(_assert_import_log_story)(caplog, case)


def test_import_acceptance_with_exact_contract_runs_one_scenario() -> None:
    """Execute the scoped Make target and reject empty/skipped acceptance runs.

    :return: None. Example: exactly one successful KARMA-EXPORT-03 execution.
    :raises AssertionError: Wrong selection, failure, undefined step or zero runs.
    """
    raise NotImplementedError()


async def _registered_import(
    case: ImportCase,
    cedar: CedarDataset,
    server_url: str,
    entrypoint: MCPEntrypoint,
    auto_apply: bool = False,
) -> dict[str, object]:
    """Call only the actual registered import tool with explicit actor context.

    :param case: Actual files and owned target. Example: CEDAR draft.
    :param cedar: Independent real actors. Example: Maria and Mike.
    :param server_url: Actual backend for facade. Example: live_server.url.
    :param entrypoint: Existing registration. Example: "legacy".
    :param auto_apply: Existing option. Example: True only applies in legacy.
    :return: Native successful response. Example: changes_count=1.
    :raises AssertionError: Tool schema, payload or HTTP boundary differs.
    :raises ToolError: The real registered tool rejects its input.
    """
    factory = MCPClientFactory(MCPDataset(cedar, {}, {}), server_url, [])
    async with factory.open(
        actor_username="mrodriguez", entrypoint=entrypoint
    ) as session:
        schema = next(
            tool.inputSchema
            for tool in await session.client.list_tools()
            if tool.name == "import_workflow_from_local"
        )
        assert set(schema["properties"]) == _IMPORT_PARAMETERS
        assert schema["required"] == ["workflow_id", "source_directory"]
        payload = decode_tool_payload(
            await session.client.call_tool(
                "import_workflow_from_local",
                {
                    "workflow_id": case.workflow_id,
                    "source_directory": str(case.source_directory),
                    "auto_apply": auto_apply,
                },
            )
        )
        expected = [("POST", f"/api/workflows/{case.workflow_id}/import_workflow/")]
        assert session.request_paths == (expected if entrypoint == "facade" else [])
        assert isinstance(payload, dict)
        return payload


def _assert_import_outcome(
    result: dict[str, object],
    case: ImportCase,
    before: ExpertsImportState,
    *,
    applied: bool,
) -> None:
    """Require positive protocol, exact application semantics and full invariants.

    :param result: Actual tool/service response. Example: changes_detected.
    :param case: Prepared real case. Example: Maria's owned draft.
    :param before: Complete post-setup state. Example: all2129 historical rows.
    :param applied: Requested existing behavior. Example: False for facade.
    :return: None. Example: protocol generated with Maria8200/Mike12450.
    :raises AssertionError: Protocol, actual content or any Experts state differs.
    """
    _assert_import_protocol(result, case)
    _assert_import_target(case, applied=applied)
    _assert_experts_unchanged(before)


def _assert_import_target(case: ImportCase, *, applied: bool) -> None:
    """Check the actual draft and exact optional new-activity application.

    :param case: Existing target identity. Example: Maria's CEDAR workflow.
    :param applied: Whether the requested legacy path applied content. Example: True.
    :return: None. Example: one exact imported name and normalized empty guidance.
    :raises AssertionError: Ownership, draft status, count or complete guidance differs.
    """
    workflow = Workflow.objects.select_related("playbook__author").get(
        pk=case.workflow_id
    )
    assert workflow.playbook.status == "draft"
    assert workflow.playbook.author.username == "mrodriguez"
    assert not workflow.playbook.author.is_staff
    rows = tuple(workflow.activities.order_by("pk").values_list("name", "guidance"))
    expected = ((case.added_activity_name, case.expected_guidance),) if applied else ()
    assert rows == expected


def _assert_import_log_story(caplog: LogCaptureFixture, case: ImportCase) -> None:
    """Check actual import beats while excluding credentials and award/generation.

    :param caplog: Import-window actual logs. Example: workflow ID and positive diff.
    :param case: Real target/source. Example: _Upload_Protocol.md.
    :return: None. Example: four existing semantic beats and no private payload.
    :raises AssertionError: Missing beat, unexpected award/summary or leaked token.
    """
    stories = (
        (
            "HTTP Tool: import_workflow_from_local",
            "entry",
            [f"workflow={case.workflow_id}"],
        ),
        ("Importing workflow", "entry", [str(case.workflow_id)]),
        ("Detected changes:", "processing", ["'new': 1", "'total': 1"]),
        ("Generated upload protocol at", "exit", ["_Upload_Protocol.md"]),
    )
    for where, beat, fragments in stories:
        assert_log_story(caplog, where=where, beats={beat: fragments})
    messages = tuple(record.getMessage() for record in caplog.records)
    tokens = tuple(Token.objects.values_list("key", flat=True))
    assert all(token not in message for token in tokens for message in messages)
    forbidden = (
        "KarmaService.award_",
        "ContributionSummaryService.refresh",
        "PublicContributionSummaryBoundary.complete",
    )
    assert not any(word in message for word in forbidden for message in messages)
    if case.expected_guidance:
        assert all(case.expected_guidance not in message for message in messages)
