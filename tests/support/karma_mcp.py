from __future__ import annotations

"""Real registered MCP/HTTP/DB and stdio support; no domain or HTTP doubles."""
from collections.abc import Mapping, Sequence
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path
from subprocess import CompletedProcess
from types import TracebackType
from typing import Literal
from uuid import UUID
import httpx
import pytest
from django.contrib.auth.models import User
from fastmcp import Client, FastMCP
from pytest_django.live_server_helper import LiveServer
from tests.support.experts_data import CedarDataset

MCPEntrypoint = Literal["facade", "legacy"]


@dataclass(frozen=True)
class MCPDataset:
    """Real Cedar baseline plus supplementary playbook-backed entities."""

    cedar: CedarDataset
    entity_ids: Mapping[str, int]
    expected_content: Mapping[str, object]


@dataclass(frozen=True)
class MCPCase:
    """An invocation with explicit actor and stable semantic fixture reference."""

    name: str
    actor_username: str
    tool_name: str
    fixture_key: str
    arguments: Mapping[str, object]
    route: str
    expected: Mapping[str, object]


@dataclass(frozen=True)
class MCPInvariantSnapshot:
    """Canonical immutable copies; no lazy ORM objects cross this boundary."""

    awards_json: str
    projections_json: str
    activity_access_json: str
    summaries_json: str | None
    interactions_json: str | None


@dataclass(frozen=True)
class FacadeConfiguration:
    """Exact prior real-client singleton configuration, never logged."""

    server_url: str
    token: str = field(repr=False)
    client: httpx.Client | None = field(repr=False)


@dataclass(frozen=True)
class MCPRuntimeState:
    """State restored even if client preparation or entry fails."""

    facade: FacadeConfiguration
    legacy_user: User | None = field(repr=False)
    unsafe_environment_value: str | None


@dataclass(frozen=True)
class MCPClientSession:
    """A genuinely connected registered client for one explicit actor."""

    client: Client
    actor_username: str
    entrypoint: MCPEntrypoint
    request_paths: list[tuple[str, str]]


@dataclass(frozen=True)
class MCPSubprocessDatabase:
    """Temporary migrated backend and private bootstrap manifest."""

    root: Path
    database_path: Path
    manifest_path: Path
    settings_module: str
    environment: Mapping[str, str] = field(repr=False)


@dataclass(frozen=True)
class MCPProtocolEvidence:
    """Actual protocol/content/state evidence without credential fields."""

    schemas: tuple[Mapping[str, object], ...]
    payload: object
    before: MCPInvariantSnapshot
    after: MCPInvariantSnapshot
    stdout_messages: tuple[Mapping[str, object], ...]


@pytest.fixture
def mcp_dataset(cedar_dataset: CedarDataset) -> MCPDataset:
    """Add only supplementary real phase/skill/rule/agent/artifact fixture rows.

    :param cedar_dataset: Real independent baseline. Example: Mike playbook 6201.
    :return: Real fixture references/content. Example: mike_phase and maria_design_pip.
    :raises AssertionError: Required fixture relationship or baseline differs.
    """
    raise NotImplementedError()


def _prepare_mcp_entities(dataset: CedarDataset) -> MCPDataset:
    """Create deterministic supporting ORM fixtures without live award hooks.

    :param dataset: Imported real baseline. Example: public released Mike playbook.
    :return: Named real IDs and expected content. Example: mike_rule ID/content.
    :raises AssertionError: Fixture cannot satisfy actual model constraints.
    """
    raise NotImplementedError()


@pytest.fixture
def mcp_request_paths() -> list[tuple[str, str]]:
    """Provide body-free observations from actual httpx request hooks.

    :return: Method/path observations. Example: [("GET", "/api/activities/")].
    :raises RuntimeError: Observation storage unavailable.
    """
    raise NotImplementedError()


def record_mcp_request(paths: list[tuple[str, str]], request: httpx.Request) -> None:
    """Observe actual requests without recording headers, bodies or query values.

    :param paths: Observation destination. Example: [].
    :param request: Actual outgoing request. Example: receipt POST.
    :return: None. Example: ("POST", "/api/consumption-receipts/") appended.
    :raises ValueError: Request has no usable path.
    """
    raise NotImplementedError()


@pytest.fixture
def mcp_client_factory(
    live_server: LiveServer,
    mcp_dataset: MCPDataset,
    mcp_request_paths: list[tuple[str, str]],
) -> MCPClientFactory:
    """Provide actor-explicit contexts over actual registered servers.

    :param live_server: Real Django HTTP backend. Example: random localhost port.
    :param mcp_dataset: Real actor/entity fixtures. Example: Mike and Maria.
    :param mcp_request_paths: Body-free HTTP observations. Example: [].
    :return: Context factory. Example: open(actor_username="mchen", entrypoint="legacy").
    :raises RuntimeError: Real fixture/server prerequisites unavailable.
    """
    raise NotImplementedError()


class MCPClientFactory:
    """Factory; each context selects its own actor and existing entrypoint."""

    def __init__(
        self, dataset: MCPDataset, server_url: str, request_paths: list[tuple[str, str]]
    ) -> None:
        """Capture explicit real dependencies.

        :param dataset: Actual fixtures. Example: independent Cedar baseline.
        :param server_url: Real HTTP URL. Example: live_server.url.
        :param request_paths: Request observations. Example: [].
        :return: None. Example: factory ready.
        :raises ValueError: Invalid dependencies.
        """
        raise NotImplementedError()

    def open(
        self, *, actor_username: str, entrypoint: MCPEntrypoint
    ) -> MCPClientContext:
        """Build an actor-specific context; no actor is selected implicitly.

        :param actor_username: Existing fixture actor. Example: "mchen".
        :param entrypoint: Actual registration. Example: "facade".
        :return: Async context. Example: context yielding connected Client.
        :raises ValueError: Missing actor or unknown entrypoint.
        """
        raise NotImplementedError()


class MCPClientContext(AbstractAsyncContextManager[MCPClientSession]):
    """Serialize singleton setup, connect real Client, and restore owned state."""

    def __init__(
        self, factory: MCPClientFactory, actor_username: str, entrypoint: MCPEntrypoint
    ) -> None:
        """Capture one explicit session request.

        :param factory: Real dependency factory. Example: mcp_client_factory.
        :param actor_username: Requested actor. Example: "mrodriguez".
        :param entrypoint: Existing server kind. Example: "legacy".
        :return: None. Example: unopened context.
        :raises ValueError: Invalid session request.
        """
        raise NotImplementedError()

    async def __aenter__(self) -> MCPClientSession:
        """Acquire runtime lease, prepare real auth/server and enter Client.

        :return: Connected actual session. Example: Client(transport=initialize_mcp()).
        :raises RuntimeError: Setup/connect failure after safe rollback.
        """
        raise NotImplementedError()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        """Close owned clients and restore singleton/context/environment state.

        :param exc_type: Body error type. Example: AssertionError.
        :param exc: Body error. Example: mismatched totals.
        :param traceback: Body traceback. Example: captured test stack.
        :return: False. Example: original assertion remains visible.
        :raises RuntimeError: Cleanup failure when no earlier error exists.
        """
        raise NotImplementedError()

    async def _prepare_facade(self, actor: User, token: str) -> FastMCP:
        """Configure actual httpx singleton, attach real hook and call _build_mcp.

        :param actor: Explicit loaded actor. Example: Mike.
        :param token: Real DRF test token; never logged. Example: actor token key.
        :return: Actual existing facade registration. Example: _build_mcp().
        :raises RuntimeError: Configuration/registration fails.
        """
        raise NotImplementedError()

    async def _prepare_legacy(self, actor: User) -> FastMCP:
        """Use actual context functions and initialize_mcp, then enforce ORM safety.

        :param actor: Explicit loaded actor. Example: Maria.
        :return: Existing real legacy registration. Example: initialize_mcp().
        :raises RuntimeError: Context/registration preparation fails.
        """
        raise NotImplementedError()

    async def _close_owned_clients(self) -> None:
        """Exit FastMCP Client and close only this context's created httpx client.

        :return: None. Example: preexisting client remains open.
        :raises RuntimeError: Owned-resource cleanup fails.
        """
        raise NotImplementedError()

    def _restore_runtime(self, state: MCPRuntimeState) -> None:
        """Clear/restore actual ContextVar, exact facade globals and prior env flag.

        :param state: Original runtime snapshot. Example: no previous actor/client.
        :return: None. Example: previous context restored without account logging.
        :raises RuntimeError: Restoration fails.
        """
        raise NotImplementedError()


def _acquire_mcp_runtime() -> None:
    """Acquire a process-local shared lease for singleton/context-sensitive setup.

    :return: None. Example: exclusive fixture runtime acquired.
    :raises RuntimeError: Lease acquisition fails.
    """
    raise NotImplementedError()


def _release_mcp_runtime() -> None:
    """Release a lease acquired by this support context.

    :return: None. Example: next explicit actor context may open.
    :raises RuntimeError: Context does not own the lease.
    """
    raise NotImplementedError()


def _capture_mcp_runtime() -> MCPRuntimeState:
    """Snapshot real facade globals, prior actor and original unsafe-env value.

    :return: Original state. Example: previously unconfigured facade.
    :raises RuntimeError: Runtime cannot be inspected safely.
    """
    raise NotImplementedError()


def _load_actor_and_token(dataset: MCPDataset, actor_username: str) -> tuple[User, str]:
    """Resolve actual actor and real DRF token inside synchronous ORM execution.

    :param dataset: Real fixture references. Example: Cedar Mike/Maria.
    :param actor_username: Explicit requested username. Example: "mchen".
    :return: Fully loaded actor and real token. Example: existing staff Mike/token.
    :raises ValueError: Actor missing or inactive; no privilege changes.
    """
    raise NotImplementedError()


def detail_case(
    tool_name: str, dataset: MCPDataset, *, actor_username: str, fixture_key: str
) -> MCPCase:
    """Resolve an explicit eligible/self/denied detail fixture without actor defaults.

    :param tool_name: Existing detail tool. Example: "get_pip".
    :param dataset: Real fixtures. Example: imported historical proposals.
    :param actor_username: Explicit consumer. Example: "mchen".
    :param fixture_key: Semantic target. Example: "maria_design_pip".
    :return: Actual arguments and expectations. Example: Mike12455/Hana5805.
    :raises ValueError: Unsupported tool, actor or target fixture.
    """
    raise NotImplementedError()


def collection_case(
    tool_name: str,
    dataset: MCPDataset,
    *,
    actor_username: str,
    entrypoint: MCPEntrypoint,
) -> MCPCase:
    """Resolve native collection arguments and entrypoint-specific metadata.

    :param tool_name: Existing list tool. Example: "list_activities".
    :param dataset: Real fixtures. Example: workflow6202.
    :param actor_username: Explicit actor. Example: "mrodriguez".
    :param entrypoint: Native schema selector. Example: "facade".
    :return: Actual collection contract. Example: authorized lightweight activity rows.
    :raises ValueError: Unsupported tool/fixture.
    """
    raise NotImplementedError()


def collection_service_result(case: MCPCase, dataset: MCPDataset) -> object:
    """Invoke the actual native collection service without any consumption writer.

    :param case: Explicit collection contract. Example: list_workflows.
    :param dataset: Real actor/parent fixtures. Example: Mike playbook6201.
    :return: Actual native result fully materialized. Example: authorized workflow rows.
    :raises PermissionError: Existing collection permission denies the request.
    """
    raise NotImplementedError()


def decode_tool_payload(result: object) -> object:
    """Decode actual FastMCP/JSON-RPC result without masking tool errors.

    :param result: Real call result. Example: structured content or JSON text block.
    :return: Actual decoded payload. Example: list of authorized metadata.
    :raises AssertionError: Tool error, missing payload or malformed result.
    """
    raise NotImplementedError()


def karma_snapshot(*, include_summaries: bool = False) -> MCPInvariantSnapshot:
    """Copy all awards/projections and optional complete persisted summary state.

    :param include_summaries: Require S23 schema when true. Example: False for S39.
    :return: Canonical immutable state. Example: every award field ordered by PK.
    :raises AssertionError: Requested schema/projection unavailable.
    """
    raise NotImplementedError()


def _canonical_model_rows(model_label: str) -> str:
    """Serialize every field of every real row in stable PK/key order.

    :param model_label: Existing model label. Example: "methodology.KarmaAward".
    :return: Canonical JSON string. Example: all ledger snapshots/timestamps.
    :raises LookupError: Required model/schema unavailable.
    """
    raise NotImplementedError()


def _canonical_karma_projections() -> str:
    """Capture S03's live total/category/source projections for every recipient.

    :return: Canonical projection JSON. Example: all recipients including Hana.
    :raises AssertionError: Projection cannot be computed from the actual ledger.
    """
    raise NotImplementedError()


def collection_snapshot() -> MCPInvariantSnapshot:
    """Require complete award/profile/interaction invariants for S41.

    :return: Complete snapshot. Example: summaries and interactions included.
    :raises AssertionError: Required S23 schema unavailable.
    """
    raise NotImplementedError()


def assert_collection_result(
    case: MCPCase,
    payload: object,
    before: MCPInvariantSnapshot,
    after: MCPInvariantSnapshot,
) -> None:
    """Assert actual native metadata and explicit unchanged invariant snapshots.

    :param case: Entrypoint-specific contract. Example: facade workflow metadata.
    :param payload: Actual decoded result. Example: nonempty activity list.
    :param before: Complete pre-call snapshot. Example: every award/summary row.
    :param after: Complete post-call snapshot. Example: unchanged award/summary rows.
    :return: None. Example: exact content and no consumption effects asserted.
    :raises AssertionError: Metadata, disclosure, access timestamp or invariant differs.
    """
    raise NotImplementedError()


def _write_subprocess_settings(root: Path, database_path: Path) -> str:
    """Write temporary test settings with explicit SQLite, locmem mail and local logs.

    :param root: Pytest-owned directory. Example: tmp_path/"legacy".
    :param database_path: Explicit temporary DB. Example: root/"mimir.sqlite3".
    :return: Importable temporary settings name. Example: "karma_mcp_subprocess_settings".
    :raises OSError: Temporary settings cannot be written.
    """
    raise NotImplementedError()


def _subprocess_environment(
    root: Path, database_path: Path, settings_module: str
) -> dict[str, str]:
    """Build explicit test environment without inherited database/provider credentials.

    :param root: Temporary settings/manifest directory. Example: tmp_path.
    :param database_path: Sole intended DB. Example: tmp_path/"mimir.sqlite3".
    :param settings_module: Temporary isolated settings. Example: generated test module.
    :return: Explicit subprocess environment. Example: local PYTHONPATH/test settings.
    :raises ValueError: Paths/settings escape temporary ownership.
    """
    raise NotImplementedError()


def _run_management(
    database: MCPSubprocessDatabase, arguments: Sequence[str]
) -> CompletedProcess[str]:
    """Run actual manage.py with current test interpreter and isolated settings.

    :param database: Explicit temporary backend. Example: migrated legacy DB.
    :param arguments: Argument vector, never shell text. Example: ("migrate", "--noinput").
    :return: Actual captured process result. Example: successful migration.
    :raises RuntimeError: Nonzero exit; diagnostics are credential-safe.
    """
    raise NotImplementedError()


def provision_mcp_subprocess_database(root: Path) -> MCPSubprocessDatabase:
    """Create real isolated schema and bootstrap Cedar/supplementary fixtures.

    :param root: Pytest-owned directory. Example: tmp_path/"legacy".
    :return: Migrated backend and private manifest location.
    :raises RuntimeError: Migration/bootstrap or isolation verification fails.
    """
    raise NotImplementedError()


def bootstrap_mcp_subprocess_dataset(manifest_path: Path) -> None:
    """Load real baseline/entities/tokens and write a private fixture-reference manifest.

    :param manifest_path: Temporary private file. Example: root/"fixtures.json".
    :return: None. Example: actors and semantic target IDs recorded.
    :raises AssertionError: Baseline, effective DB or fixture relationships differ.
    """
    raise NotImplementedError()


def write_mcp_subprocess_snapshot(
    destination: Path, *, include_summaries: bool
) -> None:
    """Serialize actual isolated ORM invariants for the parent test process.

    :param destination: Temporary snapshot file. Example: root/"after.json".
    :param include_summaries: Require complete S23 state. Example: True for S41.
    :return: None. Example: canonical snapshot written without token fields.
    :raises AssertionError: Isolation/schema/projection failure.
    """
    raise NotImplementedError()


def _read_subprocess_manifest(database: MCPSubprocessDatabase) -> Mapping[str, object]:
    """Read actual bootstrap references privately without printing credentials.

    :param database: Migrated temporary backend. Example: legacy case database.
    :return: Validated actor/entity references and private test token material.
    :raises ValueError: Missing/malformed manifest or unexpected ownership.
    """
    raise NotImplementedError()


def _remap_subprocess_case(case: MCPCase, manifest: Mapping[str, object]) -> MCPCase:
    """Resolve semantic fixture IDs inside the subprocess DB, preserving explicit paths/UUIDs.

    :param case: Original semantic invocation. Example: maria_design_pip.
    :param manifest: Actual independent DB references. Example: imported PIP PK.
    :return: Rebased invocation. Example: actual legacy pip_id, unchanged event_identity.
    :raises ValueError: Required fixture/argument mapping is unavailable.
    """
    raise NotImplementedError()


def _stdio_command(entrypoint: MCPEntrypoint, actor_username: str) -> tuple[str, ...]:
    """Select the existing executable using the current test interpreter.

    :param entrypoint: Existing server. Example: "legacy".
    :param actor_username: Explicit legacy context. Example: "mchen".
    :return: Argument vector. Example: python/manage.py/mcp_server/--user=mchen.
    :raises ValueError: Unsupported entrypoint or actor identifier.
    """
    raise NotImplementedError()


class StdioMCPClient(AbstractContextManager["StdioMCPClient"]):
    """Real protocol client over an actual existing server subprocess."""

    def __init__(
        self,
        *,
        entrypoint: MCPEntrypoint,
        actor_username: str,
        dataset: MCPDataset,
        server_url: str,
        root: Path,
        include_summaries: bool = False,
    ) -> None:
        """Capture explicit backend, actor and owned subprocess paths.

        :param entrypoint: Actual executable surface. Example: "facade".
        :param actor_username: Explicit actor. Example: "mchen".
        :param dataset: In-process HTTP-backend fixture references. Example: Cedar.
        :param server_url: Real facade backend. Example: live_server.url.
        :param root: Pytest-owned subprocess directory. Example: tmp_path.
        :param include_summaries: Complete S23 invariants required. Example: True.
        :return: None. Example: unopened protocol client.
        :raises ValueError: Invalid dependencies/ownership.
        """
        raise NotImplementedError()

    def __enter__(self) -> StdioMCPClient:
        """Prepare isolated backend, launch existing server and complete handshake.

        :return: Connected actual stdio client. Example: initialized legacy server.
        :raises RuntimeError: Startup/handshake failure after resource cleanup.
        """
        raise NotImplementedError()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        """Stop child, drain/close pipes and preserve original test failures.

        :param exc_type: Body failure type. Example: AssertionError.
        :param exc: Body failure. Example: unexpected award.
        :param traceback: Body traceback. Example: test stack.
        :return: False. Example: original assertion propagates.
        :raises RuntimeError: Cleanup fails without an earlier failure.
        """
        raise NotImplementedError()

    def initialize(self) -> Mapping[str, object]:
        """Perform real initialize request followed by initialized notification.

        :return: Actual initialization result. Example: serverInfo/protocolVersion.
        :raises AssertionError: Invalid handshake or incompatible response.
        """
        raise NotImplementedError()

    def list_tools(self) -> tuple[Mapping[str, object], ...]:
        """Read actual registered tool schemas via tools/list.

        :return: Real schema entries. Example: get_pip input schema.
        :raises AssertionError: Missing/malformed tool list.
        """
        raise NotImplementedError()

    def call(self, case: MCPCase) -> object:
        """Call an actual registered tool, rebasing only independent DB references.

        :param case: Explicit invocation. Example: Mike reading Maria Design PIP.
        :return: Actual decoded content. Example: historical changes.
        :raises AssertionError: Tool error, malformed result or wrong actor context.
        """
        raise NotImplementedError()

    def snapshot(self) -> MCPInvariantSnapshot:
        """Read actual HTTP-backend or independent legacy DB invariants.

        :return: Actual canonical state. Example: complete award pair after fetch.
        :raises AssertionError: Backend isolation or required state unavailable.
        """
        raise NotImplementedError()

    def assert_protocol_clean(self) -> None:
        """Require every observed stdout message to be valid protocol JSON.

        :return: None. Example: requests/results/notifications only.
        :raises AssertionError: Banner, log line, malformed JSON or unmatched result.
        """
        raise NotImplementedError()

    def _prepare_backend(self) -> None:
        """Prepare actual token HTTP backend or migrate/bootstrap a temporary legacy DB.

        :return: None. Example: actor token placed in private facade environment.
        :raises RuntimeError: Actor/backend/ownership preparation fails.
        """
        raise NotImplementedError()

    def _start_process(self) -> None:
        """Launch existing entrypoint with real pipes and bounded stderr draining.

        :return: None. Example: live child process with owned streams.
        :raises RuntimeError: Child exits or cannot start.
        """
        raise NotImplementedError()

    def _request(
        self, method: str, parameters: Mapping[str, object]
    ) -> Mapping[str, object]:
        """Send an identified request and match its actual response.

        :param method: JSON-RPC method. Example: "tools/call".
        :param parameters: Actual request parameters. Example: name/arguments.
        :return: Matching actual response envelope. Example: result for request ID.
        :raises TimeoutError: Bounded response deadline exceeded.
        :raises AssertionError: Protocol error or malformed response.
        """
        raise NotImplementedError()

    def _notify(self, method: str, parameters: Mapping[str, object]) -> None:
        """Send a notification without waiting for a nonexistent response.

        :param method: Notification name. Example: "notifications/initialized".
        :param parameters: Notification parameters. Example: {}.
        :return: None. Example: initialized notification written.
        :raises RuntimeError: Child input unavailable.
        """
        raise NotImplementedError()

    def _write_message(self, message: Mapping[str, object]) -> None:
        """Write one actual JSON-RPC line and flush the child input.

        :param message: Protocol envelope. Example: initialize request.
        :return: None. Example: one complete JSON line flushed.
        :raises RuntimeError: Closed/broken child input.
        """
        raise NotImplementedError()

    def _read_response(
        self, request_id: int, timeout_seconds: float
    ) -> Mapping[str, object]:
        """Read bounded actual output, retaining valid intervening notifications.

        :param request_id: Expected response identity. Example: 3.
        :param timeout_seconds: Named bounded deadline. Example: 30.0.
        :return: Matched response. Example: tools/call result.
        :raises TimeoutError: No matching result before deadline.
        :raises AssertionError: Nonprotocol output or child failure.
        """
        raise NotImplementedError()

    def _drain_stderr(self) -> None:
        """Drain child diagnostics without logging credentials or blocking stdout.

        :return: None. Example: bounded diagnostic buffer retained privately.
        :raises RuntimeError: Unexpected diagnostic-reader failure.
        """
        raise NotImplementedError()

    def _stop_process(self) -> None:
        """Terminate, bounded-wait/kill if needed, join reader and close owned pipes.

        :return: None. Example: no remaining child or stream resources.
        :raises RuntimeError: Child/resource cleanup cannot complete.
        """
        raise NotImplementedError()


def run_collection_stdio(
    entrypoint: MCPEntrypoint,
    case: MCPCase,
    root: Path,
    live_server: LiveServer,
    dataset: MCPDataset,
) -> MCPProtocolEvidence:
    """Exercise actual collection protocol and return explicit before/after evidence.

    :param entrypoint: Existing executable. Example: "legacy".
    :param case: Actor-explicit collection contract. Example: Maria list_activities.
    :param root: Temporary subprocess ownership. Example: tmp_path.
    :param live_server: Real facade HTTP backend. Example: random localhost port.
    :param dataset: Actual in-process fixture references. Example: Cedar.
    :return: Real schemas/content/state. Example: unchanged complete invariants.
    :raises AssertionError: Protocol, metadata or state differs.
    """
    raise NotImplementedError()
