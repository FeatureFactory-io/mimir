from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.support.experts_data import CedarDataset
    from pytest_django.live_server_helper import LiveServer
    from pytest import LogCaptureFixture
    from pathlib import Path

import pytest
from tests.support.karma_mcp import MCPClientFactory


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
async def test_collection_with_registered_tool_preserves_metadata_and_state(
    tool_name: str,
    entrypoint: str,
    mcp_client_factory: MCPClientFactory,
    cedar_dataset: CedarDataset,
    mcp_request_paths: list[tuple[str, str]],
) -> None:
    """Prove registered T1 metadata and global invariance.
    :param tool_name: One of nine actual lists; example: list_workflows.
    :param entrypoint: Actual registration; example: facade.
    :param registered_mcp_client: Connected real client; example: FastMCP Client.
    :param cedar_dataset: Independent baseline; example: Mike playbook 6201.
    :param mcp_request_paths: Real HTTP observations; example: collection GET only.
    :return: None; example: complete metadata and zero award/summary mutations.
    :raises AssertionError: Schema, content, internal detail invocation or state differs.
    """
    raise NotImplementedError()


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
def test_collection_with_direct_service_preserves_awards(tool_name: str) -> None:
    """Prove T2 with the real collection service and Cedar DB.
    :param tool_name: Native collection mapping; example: list_activities.
    :return: None; example: real activity rows with unchanged global snapshot.
    :raises AssertionError: Rows, access or award/summary invariants differ.
    """
    raise NotImplementedError()


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
def test_collection_with_plain_rest_preserves_awards(tool_name: str) -> None:
    """Prove ordinary collection GETs remain award-free.
    :param tool_name: Existing REST collection mapping; example: list_workflows.
    :return: None; example: actual authorized metadata and unchanged rows.
    :raises AssertionError: GET creates awards or changes summary state.
    """
    raise NotImplementedError()


@pytest.mark.parametrize("entrypoint", ["facade", "legacy"])
@pytest.mark.parametrize("case_name", ["empty", "private_parent", "denied"])
async def test_collection_with_empty_or_denied_scope_preserves_awards(
    case_name: str, entrypoint: str, mcp_client_factory: MCPClientFactory
) -> None:
    """Preserve real empty/error/access behavior.
    :param case_name: Case selector; example: private_parent.
    :param entrypoint: Actual registration; example: legacy.
    :param registered_mcp_client: Real connected client; example: Maria context.
    :return: None; example: protected response and unchanged global state.
    :raises AssertionError: Disclosure, widened permission or state mutation.
    """
    raise NotImplementedError()


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


@pytest.mark.parametrize("entrypoint", ["facade", "legacy"])
async def test_collection_log_story_happy(
    entrypoint: str, mcp_client_factory: MCPClientFactory, caplog: LogCaptureFixture
) -> None:
    """Assert existing list beats and absence of detail/award/summary invocation.
    :param entrypoint: Registered surface; example: facade.
    :param registered_mcp_client: Real client; example: Maria context.
    :param caplog: Listing-only records; example: list_activities entry.
    :return: None; example: declared beats present with no forbidden calls.
    :raises AssertionError: Missing beat, forbidden invocation or credential leakage.
    """
    raise NotImplementedError()


def test_collection_with_exact_acceptance_executes_one_contract() -> None:
    """Run scoped real Behave acceptance with explicit WIP override.
    :return: None; example: one scenario, three steps, zero skips/undefined.
    :raises AssertionError: Nonzero exit, missing execution or incorrect counts.
    """
    raise NotImplementedError()


pytest_plugins = ["tests.support.karma_mcp"]
