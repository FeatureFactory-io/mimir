"""Certify native collection metadata without consumption or summary effects."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from asgiref.sync import sync_to_async
from django.db.models import Model
from django.test import Client
from fastmcp.exceptions import ToolError
from pytest import LogCaptureFixture
from pytest_django.live_server_helper import LiveServer
from rest_framework.authtoken.models import Token

from tests.support.experts_data import CedarDataset
from tests.support.experts_logs import capture_experts_logs
from tests.support.karma_mcp import (
    MCPCase,
    MCPClientFactory,
    MCPClientSession,
    MCPDataset,
    MCPEntrypoint,
    assert_collection_result,
    collection_case,
    collection_service_result,
    collection_snapshot,
    decode_tool_payload,
)
from tests.support.karma_mcp import (
    mcp_client_factory as _mcp_client_factory,  # noqa: F401 — pytest fixture
)
from tests.support.karma_mcp import (
    mcp_dataset as _mcp_dataset,  # noqa: F401 — pytest fixture
)
from tests.support.karma_mcp import (
    mcp_request_paths as _mcp_request_paths,  # noqa: F401 — pytest fixture dependency
)
from tests.support.log_story import assert_log_story

COLLECTION_TOOLS = (
    "list_playbooks",
    "list_workflows",
    "list_phases",
    "list_activities",
    "list_skills",
    "list_rules",
    "list_agents",
    "list_artifacts",
    "list_pips",
)
_COLLECTION_LOGGERS = (
    "mcp_integration.facade.tools_http",
    "mcp_integration.tools",
    "methodology.services.karma_service",
    "methodology.services.contribution_summary_service",
    "methodology.services.contribution_summary_boundary",
    "methodology.api.consumption_views",
)
_FORBIDDEN_LOG_FRAGMENTS = (
    "MCP Tool: get_",
    "HTTP Tool: get_",
    "_complete_mcp_detail",
    "_complete_legacy_mcp_detail",
    "KarmaService.award_",
    "ContributionSummaryService.refresh",
    "PublicContributionSummaryBoundary.complete",
)
pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("entrypoint", ["facade", "legacy"])
@pytest.mark.parametrize("tool_name", COLLECTION_TOOLS)
async def test_collection_with_registered_tool_preserves_metadata_and_state(
    tool_name: str,
    entrypoint: MCPEntrypoint,
    mcp_client_factory: MCPClientFactory,
    cedar_dataset: CedarDataset,
    mcp_request_paths: list[tuple[str, str]],
    caplog: LogCaptureFixture,
) -> None:
    """Prove registered native T1 metadata and complete invariant retention.

    :param tool_name: Actual registered collection. Example: "list_workflows".
    :param entrypoint: Existing server. Example: "facade".
    :param mcp_client_factory: Real server/client dependencies. Example: Maria token.
    :param cedar_dataset: Independent baseline. Example: Mike playbook6201.
    :param mcp_request_paths: Body-free actual requests. Example: collection GET.
    :param caplog: Actual enabled records. Example: list entry without detail entry.
    :return: None. Example: native metadata with unchanged all-user awards/summaries.
    :raises AssertionError: Schema, content, request boundary or invariant differs.
    """
    assert cedar_dataset is mcp_client_factory.dataset.cedar
    case = await sync_to_async(collection_case)(
        tool_name,
        mcp_client_factory.dataset,
        actor_username="mrodriguez",
        entrypoint=entrypoint,
    )
    async with mcp_client_factory.open(
        actor_username=case.actor_username, entrypoint=entrypoint
    ) as session:
        before = await sync_to_async(collection_snapshot)()
        with capture_experts_logs(caplog, _COLLECTION_LOGGERS):
            mcp_request_paths.clear()
            payload = await _call_registered_collection(session, case)
        after = await sync_to_async(collection_snapshot)()
        assert_collection_result(case, payload, before, after)
        _assert_collection_paths(session, case)
        _assert_no_detail_effect_logs(caplog)


@pytest.mark.parametrize("tool_name", COLLECTION_TOOLS)
def test_collection_with_direct_service_preserves_awards(
    tool_name: str, mcp_dataset: MCPDataset
) -> None:
    """Prove T2 through real collection services and independent ORM expectations.

    :param tool_name: Native service mapping. Example: "list_activities".
    :param mcp_dataset: Real supporting entities. Example: Mike workflow6202.
    :return: None. Example: exact actual identities, all global invariants unchanged.
    :raises AssertionError: Native content or persisted state differs.
    """
    case = collection_case(
        tool_name, mcp_dataset, actor_username="mrodriguez", entrypoint="legacy"
    )
    before = collection_snapshot()
    rows = collection_service_result(case, mcp_dataset)
    assert (
        isinstance(rows, tuple) and rows and all(isinstance(row, Model) for row in rows)
    )
    assert [row.pk for row in rows] == [row["id"] for row in case.expected["rows"]]
    for actual, expected in zip(rows, case.expected["rows"], strict=True):
        assert getattr(actual, "title", getattr(actual, "name", None)) == expected.get(
            "title", expected.get("name")
        )
    assert collection_snapshot() == before


@pytest.mark.parametrize("tool_name", COLLECTION_TOOLS)
def test_collection_with_plain_rest_preserves_awards(
    tool_name: str, mcp_dataset: MCPDataset
) -> None:
    """Prove actual token collection GET metadata and absence of consumption.

    :param tool_name: Existing REST mapping. Example: "list_workflows".
    :param mcp_dataset: Real actors and entities. Example: Maria, publicMike.
    :return: None. Example: ordinary actual response and unchanged ledger/prose.
    :raises AssertionError: HTTP, metadata or state differs.
    """
    case = collection_case(
        tool_name, mcp_dataset, actor_username="mrodriguez", entrypoint="facade"
    )
    before = collection_snapshot()
    payload = _real_collection_get(case, mcp_dataset)
    assert_collection_result(case, payload, before, collection_snapshot())


@pytest.mark.parametrize("entrypoint", ["facade", "legacy"])
@pytest.mark.parametrize("case_name", ["empty", "private_parent", "denied"])
async def test_collection_with_empty_or_denied_scope_preserves_awards(
    case_name: str,
    entrypoint: MCPEntrypoint,
    mcp_client_factory: MCPClientFactory,
    caplog: LogCaptureFixture,
) -> None:
    """Preserve native empty/private-parent/staff-only collection behavior.

    :param case_name: Actual scope boundary. Example: "private_parent".
    :param entrypoint: Real registration. Example: "legacy".
    :param mcp_client_factory: Real actor/server context. Example: nonstaffMaria.
    :param caplog: Enabled actual collection records. Example: no detail invocation.
    :return: None. Example: native empty/error, no disclosure or state mutation.
    :raises AssertionError: Access semantics, metadata or invariant differs.
    """
    case = await sync_to_async(_adverse_collection_case)(
        case_name, entrypoint, mcp_client_factory.dataset
    )
    async with mcp_client_factory.open(
        actor_username=case.actor_username, entrypoint=entrypoint
    ) as session:
        before = await sync_to_async(collection_snapshot)()
        session.request_paths.clear()
        with capture_experts_logs(caplog, _COLLECTION_LOGGERS):
            if case_name == "denied" or (
                case_name == "private_parent" and entrypoint == "legacy"
            ):
                with pytest.raises(
                    ToolError, match="[Ss]taff only|not found|[Pp]ermission|[Aa]ccess"
                ):
                    await _call_registered_collection(session, case)
            else:
                assert await _call_registered_collection(session, case) == []
        assert await sync_to_async(collection_snapshot)() == before
        _assert_collection_paths(session, case)
        _assert_no_detail_effect_logs(caplog)


@pytest.mark.parametrize("entrypoint", ["facade", "legacy"])
async def test_collection_log_story_happy(
    entrypoint: MCPEntrypoint,
    mcp_client_factory: MCPClientFactory,
    caplog: LogCaptureFixture,
) -> None:
    """Prove existing collection-entry and lightweight legacy-return log beats.

    :param entrypoint: Real registration. Example: "facade".
    :param mcp_client_factory: Real actor/client. Example: Maria.
    :param caplog: Actual listing-window records. Example: workflow6202 entry.
    :return: None. Example: exact beats, no detail/award/summary or credential logs.
    :raises AssertionError: Required entry/exit or invariant differs.
    """
    case = await sync_to_async(collection_case)(
        "list_activities",
        mcp_client_factory.dataset,
        actor_username="mrodriguez",
        entrypoint=entrypoint,
    )
    async with mcp_client_factory.open(
        actor_username=case.actor_username, entrypoint=entrypoint
    ) as session:
        before = await sync_to_async(collection_snapshot)()
        with capture_experts_logs(caplog, _COLLECTION_LOGGERS):
            caplog.clear()
            session.request_paths.clear()
            payload = await _call_registered_collection(session, case)
        assert_collection_result(
            case, payload, before, await sync_to_async(collection_snapshot)()
        )
        _assert_collection_paths(session, case)
        _assert_no_detail_effect_logs(caplog)
        _assert_collection_log_story(caplog, entrypoint, len(payload))


async def _call_registered_collection(
    session: MCPClientSession, case: MCPCase
) -> object:
    """Validate actual registration and call its real transport.

    :param session: Genuinely connected FastMCP client. Example: facadeHTTP.
    :param case: Explicit source contract. Example: list_activities6202.
    :return: Actual decoded result. Example: lightweight metadata list.
    :raises AssertionError: Registration or safe schema differs.
    :raises ToolError: Existing scope permission rejects the actual invocation.
    """
    tools = {tool.name: tool for tool in await session.client.list_tools()}
    assert case.tool_name in tools
    schema = tools[case.tool_name].inputSchema
    assert set(case.arguments) <= set(schema["properties"])
    assert not {
        "actor_id",
        "recipient_id",
        "points",
        "category",
        "timestamp",
        "event_identity",
    } & set(schema["properties"])
    result = await session.client.call_tool(case.tool_name, dict(case.arguments))
    payload = decode_tool_payload(result)
    if isinstance(payload, dict) and set(payload) == {"result"}:
        return payload["result"]
    return payload


def _assert_collection_paths(session: MCPClientSession, case: MCPCase) -> None:
    """Reject hidden detail fetches and receipt writes using real HTTP hooks.

    :param session: Actual observed client. Example: Maria facade.
    :param case: Expected collection. Example: /api/activities/.
    :return: None. Example: exactly one collectionGET, or noHTTP forlegacy.
    :raises AssertionError: Additional/different resource or method is observed.
    """
    assert session.request_paths == (
        [("GET", case.route)] if session.entrypoint == "facade" else []
    )


def _assert_no_detail_effect_logs(caplog: LogCaptureFixture) -> None:
    """Require no detail, receipt, award or generation entry during listing.

    :param caplog: Actual enabled listing records. Example: list only.
    :return: None. Example: safe metadata logs, no forbidden effect entry.
    :raises AssertionError: Forbidden operation or credential-shaped log found.
    """
    messages = [
        record.getMessage()
        for record in caplog.records
        if record.name in _COLLECTION_LOGGERS
    ]
    assert messages
    assert not any(
        fragment in message
        for message in messages
        for fragment in _FORBIDDEN_LOG_FRAGMENTS
    )
    assert not any(
        "Authorization" in message or "Token " in message or "@" in message
        for message in messages
    )


def _real_collection_get(case: MCPCase, dataset: MCPDataset) -> object:
    """Read the actual API with a real provisioned token, excluding no permission checks.

    :param case: Explicit HTTP collection. Example: /api/activities/.
    :param dataset: Imported real actor. Example: Maria.
    :return: Actual JSON rows. Example: nonempty metadata.
    :raises AssertionError: API response is unsuccessful.
    """
    actor = dataset.cedar.users_by_username[case.actor_username]
    token, _ = Token.objects.get_or_create(user=actor)
    response = Client().get(
        case.route, dict(case.arguments), HTTP_AUTHORIZATION=f"Token {token.key}"
    )
    assert response.status_code == 200
    payload = response.json()
    return payload.get("results", payload) if isinstance(payload, dict) else payload


def _adverse_collection_case(
    name: str, entrypoint: MCPEntrypoint, dataset: MCPDataset
) -> MCPCase:
    """Resolve native empty/private/staff-restricted cases from actual Cedar rows.

    :param name: Existing boundary. Example: "private_parent".
    :param entrypoint: Existing registration. Example: "facade".
    :param dataset: Imported actual entities. Example: Nora private draft6302.
    :return: Actual arguments and native empty/error expectation. Example: nonstaffallPIPs.
    :raises ValueError: Unknown case selector.
    :raises AssertionError: Intended private/role fixture is not real.
    """
    if name == "empty":
        case = collection_case(
            "list_skills", dataset, actor_username="mrodriguez", entrypoint=entrypoint
        )
        return replace(
            case, arguments={**case.arguments, "search": "CEDAR-NO-MATCH-COLLECTION-91"}
        )
    if name == "private_parent":
        book = dataset.cedar.playbooks_by_pk[6302]
        actor = dataset.cedar.users_by_username["mrodriguez"]
        assert (
            book.visibility == "private"
            and book.author_id != actor.pk
            and not actor.is_staff
        )
        case = collection_case(
            "list_workflows",
            dataset,
            actor_username="mrodriguez",
            entrypoint=entrypoint,
        )
        return replace(case, arguments={"playbook_id": book.pk})
    if name == "denied":
        assert not dataset.cedar.users_by_username["mrodriguez"].is_staff
        case = collection_case(
            "list_pips", dataset, actor_username="mrodriguez", entrypoint=entrypoint
        )
        return replace(case, arguments={"scope": "all"})
    raise ValueError("Unknown collection boundary.")


@pytest.mark.parametrize("entrypoint", ["facade", "legacy"])
@pytest.mark.parametrize(
    "tool_name",
    [
        "list_playbooks",
        "list_workflows",
        "list_phases",
        "list_activities",
        "list_skills",
        "list_rules",
        "list_agents",
        "list_artifacts",
        "list_pips",
    ],
)
def test_collection_with_stdio_entrypoint_preserves_protocol_and_state(
    tool_name: str, entrypoint: str, tmp_path: Path, live_server: LiveServer
) -> None:
    """Prove T3 through actual stdio startup and collection call.
    :param tool_name: Registered list; example: list_activities.
    :param entrypoint: Actual executable surface; example: facade.
    :param tmp_path: Isolated subprocess storage; example: temporary SQLite.
    :param live_server: Real facade HTTP backend; example: random local port.
    :return: None; example: valid JSON-RPC and unchanged global invariants.
    :raises AssertionError: Protocol noise, missing content or mutations.
    """
    raise NotImplementedError()


def test_collection_with_exact_acceptance_executes_one_contract() -> None:
    """Run scoped real Behave acceptance with explicit WIP override.
    :return: None; example: one scenario, three steps, zero skips/undefined.
    :raises AssertionError: Nonzero exit, missing execution or incorrect counts.
    """
    raise NotImplementedError()


def _assert_collection_log_story(
    caplog: LogCaptureFixture, entrypoint: MCPEntrypoint, row_count: int
) -> None:
    """Require actual native parent entry and legacy guidance-exclusion exit.

    :param caplog: Actual captured collection records. Example: workflow6202 entry.
    :param entrypoint: Existing registered surface. Example: "legacy".
    :param row_count: Actual decoded list size. Example: 1.
    :return: None when required actual beats exist. Example: safe lightweight exit.
    :raises AssertionError: Required native log beat is absent.
    """
    label = "HTTP Tool:" if entrypoint == "facade" else "MCP Tool:"
    parent = "workflow=6202" if entrypoint == "facade" else "workflow_id=6202"
    assert_log_story(
        caplog, where=f"{label} list_activities", beats={"entry": (parent,)}
    )
    if entrypoint == "legacy":
        assert_log_story(
            caplog,
            where="MCP Tool: Returning",
            beats={"exit": (f"{row_count} activities", "guidance excluded")},
        )
