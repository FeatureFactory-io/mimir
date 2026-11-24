"""Real registered MCP/HTTP/DB and stdio support; no domain or HTTP doubles."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from collections.abc import Mapping, Sequence
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    AsyncExitStack,
    ExitStack,
    closing,
)
from dataclasses import asdict, dataclass, field
from functools import partial
from importlib import import_module
from pathlib import Path
from select import select
from subprocess import PIPE, CompletedProcess, Popen, TimeoutExpired
from tempfile import TemporaryDirectory, TemporaryFile
from threading import Lock
from time import monotonic
from types import TracebackType
from typing import BinaryIO, Literal, Self
from urllib.parse import urlsplit

import httpx
import pytest
from asgiref.sync import sync_to_async
from django.apps import apps
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from django.db.models import Model, Q
from fastmcp import Client, FastMCP
from fastmcp.client.client import CallToolResult
from mcp.types import (
    LATEST_PROTOCOL_VERSION,
    JSONRPCMessage,
    JSONRPCNotification,
    JSONRPCResponse,
    TextContent,
)
from pydantic import ValidationError
from pytest_django.live_server_helper import LiveServer
from rest_framework.authtoken.models import Token

from mcp_integration.context import _current_user, set_current_user
from mcp_integration.facade import client as facade_client
from mcp_integration.facade.server import _build_mcp
from methodology.models import (
    Activity,
    Agent,
    Artifact,
    Phase,
    Playbook,
    ProcessImprovementProposal,
    Rule,
    Skill,
    Workflow,
)
from methodology.services.activity_service import ActivityService
from methodology.services.agent_service import AgentService
from methodology.services.artifact_service import ArtifactService
from methodology.services.experts_service import ExpertsService
from methodology.services.phase_service import PhaseService
from methodology.services.pip_service import PIPService
from methodology.services.playbook_service import PlaybookService
from methodology.services.rule_service import RuleService
from methodology.services.skill_service import SkillService
from methodology.services.workflow_service import WorkflowService
from tests.support.experts_data import (
    CedarDatabaseScope,
    CedarDataset,
    _resolve_database_scope,
    _verify_sqlite_target,
)

MCPEntrypoint = Literal["facade", "legacy"]
_UNSAFE_ORM_FLAG = "DJANGO_ALLOW_ASYNC_UNSAFE"
_MCP_RUNTIME_LOCK = Lock()
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STDIO_TIMEOUT_SECONDS = 30.0
_STDIO_EXIT_TIMEOUT_SECONDS = 5.0
_STDIO_READ_SIZE = 65536
_STDIO_STDERR_LIMIT = 65536
_LEGACY_SETTINGS = "karma_mcp_subprocess_settings"
_LEGACY_DATABASE_FILENAME = "mimir.sqlite3"


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


@pytest.fixture(name="mcp_dataset")
def mcp_dataset(cedar_dataset: CedarDataset) -> MCPDataset:
    """Add only supplementary real phase/skill/rule/agent/artifact fixture rows.

    :param cedar_dataset: Real independent baseline. Example: Mike playbook 6201.
    :return: Real fixture references/content. Example: mike_phase and maria_design_pip.
    :raises AssertionError: Required fixture relationship or baseline differs.
    """
    return _prepare_mcp_entities(cedar_dataset)


def _prepare_mcp_entities(dataset: CedarDataset) -> MCPDataset:
    """Create deterministic supporting ORM fixtures without live award hooks.

    :param dataset: Imported real baseline. Example: public released Mike playbook.
    :return: Named real IDs and expected content. Example: mike_rule ID/content.
    :raises AssertionError: Fixture cannot satisfy actual model constraints.
    """
    book = dataset.playbooks_by_pk[6201]
    activity = dataset.activities_by_pk[6203]
    phase = Phase.objects.create(
        playbook=book, name="Cedar Review Phase", description="Review evidence"
    )
    activity.phase = phase
    activity.save(update_fields=["phase"])
    entities = {
        "mike_playbook": book,
        "mike_workflow": dataset.workflows_by_pk[6202],
        "mike_activity": activity,
        "mike_phase": phase,
        "mike_agent": Agent.objects.create(
            playbook=book, name="Cedar Review Agent", description="Review evidence"
        ),
        "mike_skill": Skill.objects.create(
            playbook=book, title="Cedar Review Skill", content="Verify review evidence"
        ),
        "mike_rule": Rule.objects.create(
            playbook=book,
            title="Cedar Review Rule",
            slug="cedar-review-rule",
            content="Check review evidence",
        ),
        "mike_artifact": Artifact.objects.create(
            playbook=book,
            name="Cedar Evidence Checklist",
            produced_by=activity,
            description="Checklist evidence",
        ),
        "maria_design_pip": dataset.pips_by_key["HIST-MARIA-DESIGN-01"],
        "maria_dev_pip": dataset.pips_by_key["HIST-MARIA-DEV-01"],
    }
    content = {}
    for key, entity in entities.items():
        persisted_fields = {field.name for field in entity._meta.concrete_fields}
        title_field = "title" if hasattr(entity, "title") else "name"
        content[key] = {
            title_field: getattr(entity, title_field),
            **{
                field: getattr(entity, field)
                for field in ("description", "guidance", "summary", "content")
                if field in persisted_fields
            },
        }
    return MCPDataset(
        dataset, {key: entity.pk for key, entity in entities.items()}, content
    )


@pytest.fixture(name="mcp_request_paths")
def mcp_request_paths() -> list[tuple[str, str]]:
    """Provide body-free observations from actual httpx request hooks.

    :return: Method/path observations. Example: [("GET", "/api/activities/")].
    :raises RuntimeError: Observation storage unavailable.
    """
    return []


def record_mcp_request(paths: list[tuple[str, str]], request: httpx.Request) -> None:
    """Observe actual requests without recording headers, bodies or query values.

    :param paths: Observation destination. Example: [].
    :param request: Actual outgoing request. Example: receipt POST.
    :return: None. Example: ("POST", "/api/consumption-receipts/") appended.
    :raises ValueError: Request has no usable path.
    """
    paths.append((request.method, request.url.path))


@pytest.fixture(name="mcp_client_factory")
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
    return MCPClientFactory(mcp_dataset, live_server.url, mcp_request_paths)


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
        self.dataset = dataset
        self.server_url = server_url
        self.request_paths = request_paths

    def open(
        self, *, actor_username: str, entrypoint: MCPEntrypoint
    ) -> MCPClientContext:
        """Build an actor-specific context; no actor is selected implicitly.

        :param actor_username: Existing fixture actor. Example: "mchen".
        :param entrypoint: Actual registration. Example: "facade".
        :return: Async context. Example: context yielding connected Client.
        :raises ValueError: Missing actor or unknown entrypoint.
        """
        if not actor_username or entrypoint not in ("facade", "legacy"):
            raise ValueError(
                "An explicit actor and supported MCP entrypoint are required."
            )
        return MCPClientContext(self, actor_username, entrypoint)


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
        self._factory = factory
        self._actor_username = actor_username
        self._entrypoint = entrypoint
        self._state: MCPRuntimeState | None = None
        self._resources = AsyncExitStack()

    async def __aenter__(self) -> MCPClientSession:
        """Acquire runtime lease, prepare real auth/server and enter Client.

        :return: Connected actual session. Example: Client(transport=initialize_mcp()).
        :raises RuntimeError: Setup/connect failure after safe rollback.
        """
        _acquire_mcp_runtime()
        try:
            self._state = _capture_mcp_runtime()
            actor, token = await sync_to_async(_load_actor_and_token)(
                self._factory.dataset, self._actor_username
            )
            if self._entrypoint == "facade":
                mcp = await self._prepare_facade(actor, token)
            else:
                mcp = await self._prepare_legacy(actor)
            client = await self._resources.enter_async_context(Client(mcp))
            return MCPClientSession(
                client,
                self._actor_username,
                self._entrypoint,
                self._factory.request_paths,
            )
        except BaseException as error:
            await self.__aexit__(type(error), error, error.__traceback__)
            raise

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
        try:
            await self._close_owned_clients()
        except Exception:
            if exc is None:
                raise
            exc.add_note("An owned MCP client failed during cleanup.")
        finally:
            try:
                if self._state is not None:
                    self._restore_runtime(self._state)
            finally:
                _release_mcp_runtime()
        return False

    async def _prepare_facade(self, actor: User, token: str) -> FastMCP:
        """Configure actual httpx singleton, attach real hook and call _build_mcp.

        :param actor: Explicit loaded actor. Example: Mike.
        :param token: Real DRF test token; never logged. Example: actor token key.
        :return: Actual existing facade registration. Example: _build_mcp().
        :raises RuntimeError: Configuration/registration fails.
        """
        facade_client.configure(self._factory.server_url, token)
        client = facade_client.get_client()
        self._resources.callback(client.close)
        client.event_hooks["request"].append(
            partial(record_mcp_request, self._factory.request_paths)
        )
        return _build_mcp()

    async def _prepare_legacy(self, actor: User) -> FastMCP:
        """Use actual context functions and initialize_mcp, then enforce ORM safety.

        :param actor: Explicit loaded actor. Example: Maria.
        :return: Existing real legacy registration. Example: initialize_mcp().
        :raises RuntimeError: Context/registration preparation fails.
        """
        legacy_tools = import_module("mcp_integration.tools")
        os.environ.pop(_UNSAFE_ORM_FLAG, None)
        set_current_user(actor)
        # Register on an owned component map and restore the exact original map.
        provider = legacy_tools.mcp.local_provider
        components = provider._components
        self._resources.callback(setattr, provider, "_components", components)
        provider._components = components.copy()
        return legacy_tools.initialize_mcp()

    async def _close_owned_clients(self) -> None:
        """Exit FastMCP Client and close only this context's created httpx client.

        :return: None. Example: preexisting client remains open.
        :raises RuntimeError: Owned-resource cleanup fails.
        """
        await self._resources.aclose()

    def _restore_runtime(self, state: MCPRuntimeState) -> None:
        """Clear/restore actual ContextVar, exact facade globals and prior env flag.

        :param state: Original runtime snapshot. Example: no previous actor/client.
        :return: None. Example: previous context restored without account logging.
        :raises RuntimeError: Restoration fails.
        """
        _current_user.set(state.legacy_user)
        facade_client._server_url = state.facade.server_url
        facade_client._token = state.facade.token
        facade_client._http_client = state.facade.client
        if state.unsafe_environment_value is None:
            os.environ.pop(_UNSAFE_ORM_FLAG, None)
        else:
            os.environ[_UNSAFE_ORM_FLAG] = state.unsafe_environment_value


def _acquire_mcp_runtime() -> None:
    """Acquire a process-local shared lease for singleton/context-sensitive setup.

    :return: None. Example: exclusive fixture runtime acquired.
    :raises RuntimeError: Lease acquisition fails.
    """
    if not _MCP_RUNTIME_LOCK.acquire(blocking=False):
        raise RuntimeError("Another MCP client context owns the shared runtime.")


def _release_mcp_runtime() -> None:
    """Release a lease acquired by this support context.

    :return: None. Example: next explicit actor context may open.
    :raises RuntimeError: Context does not own the lease.
    """
    _MCP_RUNTIME_LOCK.release()


def _capture_mcp_runtime() -> MCPRuntimeState:
    """Snapshot real facade globals, prior actor and original unsafe-env value.

    :return: Original state. Example: previously unconfigured facade.
    :raises RuntimeError: Runtime cannot be inspected safely.
    """
    return MCPRuntimeState(
        FacadeConfiguration(
            facade_client._server_url, facade_client._token, facade_client._http_client
        ),
        _current_user.get(),
        os.environ.get(_UNSAFE_ORM_FLAG),
    )


def _load_actor_and_token(dataset: MCPDataset, actor_username: str) -> tuple[User, str]:
    """Resolve actual actor and real DRF token inside synchronous ORM execution.

    :param dataset: Real fixture references. Example: Cedar Mike/Maria.
    :param actor_username: Explicit requested username. Example: "mchen".
    :return: Fully loaded actor and real token. Example: existing staff Mike/token.
    :raises ValueError: Actor missing or inactive; no privilege changes.
    """
    actor = dataset.cedar.users_by_username.get(actor_username)
    if actor is None or not actor.is_active:
        raise ValueError("The requested Cedar actor does not exist or is inactive.")
    token, _ = Token.objects.get_or_create(user=actor)
    return actor, token.key


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
    entity_type = tool_name.removeprefix("get_")
    if not tool_name.startswith("get_") or entity_type not in {
        "playbook",
        "workflow",
        "activity",
        "phase",
        "skill",
        "rule",
        "agent",
        "artifact",
        "pip",
    }:
        raise ValueError("The tool is not a supported detail tool.")
    if actor_username not in dataset.cedar.users_by_username:
        raise ValueError("An explicit Cedar actor is required.")
    if fixture_key not in dataset.entity_ids or not fixture_key.endswith(
        ("_" + entity_type,)
    ):
        raise ValueError("The fixture does not match the tool's entity type.")
    entity_id = dataset.entity_ids[fixture_key]
    resource = "activities" if entity_type == "activity" else f"{entity_type}s"
    return MCPCase(
        tool_name,
        actor_username,
        tool_name,
        fixture_key,
        {f"{entity_type}_id": entity_id},
        f"/api/{resource}/{entity_id}/",
        dataset.expected_content[fixture_key],
    )


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
    _collection_parameter_validation(tool_name, dataset, actor_username, entrypoint)
    arguments = _collection_arguments(tool_name, dataset)
    rows = _collection_expected_objects(tool_name, dataset, actor_username, entrypoint)
    expected = [_collection_metadata(row, tool_name, entrypoint) for row in rows]
    return MCPCase(
        tool_name,
        actor_username,
        tool_name,
        f"collection:{tool_name}",
        arguments,
        f"/api/{_COLLECTION_RESOURCES[tool_name]}/",
        {"rows": expected, "entrypoint": entrypoint},
    )


def collection_service_result(case: MCPCase, dataset: MCPDataset) -> object:
    """Invoke the actual native collection service without any consumption writer.

    :param case: Explicit collection contract. Example: list_workflows.
    :param dataset: Real actor/parent fixtures. Example: Mike playbook6201.
    :return: Actual native result fully materialized. Example: authorized workflow rows.
    :raises PermissionError: Existing collection permission denies the request.
    """
    _collection_parameter_validation(
        case.tool_name, dataset, case.actor_username, case.expected["entrypoint"]
    )
    return _collection_native_rows(case, dataset)


def decode_tool_payload(result: object) -> object:
    """Decode actual FastMCP/JSON-RPC result without masking tool errors.

    :param result: Real call result. Example: structured content or JSON text block.
    :return: Actual decoded payload. Example: list of authorized metadata.
    :raises AssertionError: Tool error, missing payload or malformed result.
    """
    if isinstance(result, CallToolResult):
        assert (
            not result.is_error
        ), "Registered MCP call did not return a successful result."
        if result.structured_content is not None:
            return result.structured_content
        blocks = result.content
    else:
        assert isinstance(result, Mapping) and result.get("isError") is not True
        if result.get("structuredContent") is not None:
            return result["structuredContent"]
        blocks = result["content"]
    assert len(blocks) == 1, "Expected one JSON MCP result block."
    block = blocks[0]
    if isinstance(block, TextContent):
        return json.loads(block.text)
    assert isinstance(block, Mapping) and block.get("type") == "text"
    return json.loads(block["text"])


def karma_snapshot(*, include_summaries: bool = False) -> MCPInvariantSnapshot:
    """Copy all awards/projections and optional complete persisted summary state.

    :param include_summaries: Require S23 schema when true. Example: False for S39.
    :return: Canonical immutable state. Example: every award field ordered by PK.
    :raises AssertionError: Requested schema/projection unavailable.
    """
    activity_access = Activity.objects.order_by("pk").values_list(
        "pk", "last_accessed_at"
    )
    return MCPInvariantSnapshot(
        awards_json=_canonical_model_rows("methodology.KarmaAward"),
        projections_json=_canonical_karma_projections(),
        activity_access_json=json.dumps(list(activity_access), default=str),
        summaries_json=(
            _canonical_model_rows("methodology.ExpertProfile")
            if include_summaries
            else None
        ),
        interactions_json=(
            _canonical_model_rows("methodology.AgentInteraction")
            if include_summaries
            else None
        ),
    )


def _canonical_model_rows(model_label: str) -> str:
    """Serialize every field of every real row in stable PK/key order.

    :param model_label: Existing model label. Example: "methodology.KarmaAward".
    :return: Canonical JSON string. Example: all ledger snapshots/timestamps.
    :raises LookupError: Required model/schema unavailable.
    """
    rows = apps.get_model(model_label).objects.order_by("pk").values_list()
    return json.dumps(list(rows), default=str, sort_keys=True)


def _canonical_karma_projections() -> str:
    """Capture S03's live total/category/source projections for every recipient.

    :return: Canonical projection JSON. Example: all recipients including Hana.
    :raises AssertionError: Projection cannot be computed from the actual ledger.
    """
    service = ExpertsService()
    users = User.objects.order_by("pk").values_list("pk", flat=True)
    return json.dumps([asdict(service.project_user(user)) for user in users])


def collection_snapshot() -> MCPInvariantSnapshot:
    """Require complete award/profile/interaction invariants for S41.

    :return: Complete snapshot. Example: summaries and interactions included.
    :raises AssertionError: Required S23 schema unavailable.
    """
    snapshot = karma_snapshot(include_summaries=True)
    assert (
        snapshot.summaries_json is not None and snapshot.interactions_json is not None
    )
    return snapshot


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
    assert before.summaries_json is not None and before.interactions_json is not None
    assert (
        after == before
    ), "Collection changed complete awards, all projections, access times or summaries."
    assert (
        isinstance(payload, list) and payload
    ), "Primary collection must return genuine nonempty metadata."
    assert (
        payload == case.expected["rows"]
    ), "Native metadata, identity, field set or order differs."
    if case.tool_name == "list_activities":
        assert all("guidance" not in row for row in payload)


def _write_subprocess_settings(root: Path, database_path: Path) -> str:
    """Write test settings with explicit SQLite, locmem mail and receipt diagnostics.

    :param root: Pytest-owned directory. Example: tmp_path/"legacy".
    :param database_path: Explicit temporary DB. Example: root/"mimir.sqlite3".
    :return: Importable temporary settings name. Example: "karma_mcp_subprocess_settings".
    :raises OSError: Temporary settings cannot be written.
    """
    settings = root / f"{_LEGACY_SETTINGS}.py"
    with settings.open("x", encoding="utf-8") as stream:
        stream.write(
            "from mimir.settings.test import *\n"
            f"DATABASES['default']['NAME'] = {str(database_path)!r}\n"
            "LOGGING['handlers']['karma_stderr'] = {'class': 'logging.StreamHandler'}\n"
            "LOGGING['loggers'] = {'methodology.services.karma_service': "
            "{'handlers': ['karma_stderr'], 'level': 'INFO', 'propagate': False}}\n"
        )
    return _LEGACY_SETTINGS


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
    if database_path.parent != root or settings_module != _LEGACY_SETTINGS:
        raise ValueError("Legacy settings and database must share the owned root.")
    return {
        "PATH": os.defpath,
        "PYTHONPATH": os.pathsep.join((str(root), str(_PROJECT_ROOT))),
        "PYTHONIOENCODING": "utf-8",
        "DJANGO_SETTINGS_MODULE": settings_module,
        "MIMIR_ENV": "test",
        "MIMIR_MCP_MODE": "1",
    }


def _run_management(
    database: MCPSubprocessDatabase, arguments: Sequence[str]
) -> CompletedProcess[str]:
    """Run actual manage.py with current test interpreter and isolated settings.

    :param database: Explicit temporary backend. Example: migrated legacy DB.
    :param arguments: Argument vector, never shell text. Example: ("migrate", "--noinput").
    :return: Actual captured process result. Example: successful migration.
    :raises RuntimeError: Nonzero exit; diagnostics are credential-safe.
    """
    try:
        result = subprocess.run(
            (sys.executable, str(_PROJECT_ROOT / "manage.py"), *arguments),
            env=database.environment,
            cwd=database.root,
            check=False,
            capture_output=True,
            text=True,
            timeout=_STDIO_TIMEOUT_SECONDS,
        )
    except TimeoutExpired:
        raise RuntimeError("Isolated legacy management command timed out.") from None
    if result.returncode != 0:
        raise RuntimeError(
            f"Isolated legacy {arguments[0]} command exited {result.returncode}."
        )
    return result


def provision_mcp_subprocess_database(root: Path) -> MCPSubprocessDatabase:
    """Copy a migrated, Cedar-populated runner database into an owned SQLite file.

    :param root: Pytest-owned directory. Example: tmp_path/"legacy".
    :return: Isolated backend and reserved private manifest location.
    :raises RuntimeError: Migration/bootstrap or isolation verification fails.
    """
    _resolve_database_scope(None)
    if not root.is_absolute() or root.resolve() != root or any(root.iterdir()):
        raise ValueError("Legacy database requires an empty owned directory.")
    if not connection.get_autocommit() or connection.in_atomic_block:
        raise RuntimeError(
            "Commit the runner fixture before copying it for legacy MCP."
        )
    path = root / _LEGACY_DATABASE_FILENAME
    settings = _write_subprocess_settings(root, path)
    database = MCPSubprocessDatabase(
        root,
        path,
        root / "fixtures.json",
        settings,
        _subprocess_environment(root, path, settings),
    )
    if connection.vendor == "sqlite":
        with closing(sqlite3.connect(path)) as target:
            connection.connection.backup(target)
    else:
        _copy_runner_rows_to_sqlite(database)
    return database


def _copy_runner_rows_to_sqlite(database: MCPSubprocessDatabase) -> None:
    """Transfer test rows through Django fixtures on PostgreSQL CI.

    :param database: Fresh owned SQLite destination. Example: provisioned MCP DB.
    :return: None after migrating and loading the private fixture.
    :raises RuntimeError: Migration or fixture loading failed.
    """
    fixture = database.root / "runner-rows.xml"
    try:
        _run_management(database, ("migrate", "--noinput"))
        call_command(
            "dumpdata",
            all=True,
            format="xml",  # Django's JSON fixture encoder truncates microseconds.
            use_natural_foreign_keys=True,
            exclude=("contenttypes", "auth.permission"),
            output=str(fixture),
        )
        _run_management(database, ("loaddata", str(fixture)))
    finally:
        fixture.unlink(missing_ok=True)


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
    database = Path(connection.settings_dict["NAME"])
    if (
        connection.vendor != "sqlite"
        or os.environ.get("DJANGO_SETTINGS_MODULE") != _LEGACY_SETTINGS
        or database != destination.parent / _LEGACY_DATABASE_FILENAME
        or database.resolve() != database
        or not database.is_file()
    ):
        raise ValueError("Legacy snapshot requires the owned SQLite database.")
    _verify_sqlite_target(str(database))
    snapshot = karma_snapshot(include_summaries=include_summaries)
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(asdict(snapshot), stream)


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

    :param entrypoint: Existing server owned by this proof. Example: "facade".
    :param actor_username: Explicit existing actor. Example: "mchen".
    :return: Argument vector. Example: python -m mcp_integration.facade.server --transport=stdio.
    :raises ValueError: Unsupported entrypoint or actor identifier.
    """
    if actor_username and entrypoint == "facade":
        return (
            sys.executable,
            "-m",
            "mcp_integration.facade.server",
            "--transport=stdio",
        )
    if actor_username and entrypoint == "legacy":
        return (
            sys.executable,
            str(_PROJECT_ROOT / "manage.py"),
            "mcp_server",
            f"--user={actor_username}",
        )
    raise ValueError("Stdio requires a supported entrypoint and explicit actor.")


def _valid_stdio_server(entrypoint: MCPEntrypoint, server_url: str) -> bool:
    """Require a loopback listener for the facade and an empty URL for legacy.

    :param entrypoint: Intended MCP executable. Example: "facade".
    :param server_url: Candidate listener. Example: "http://127.0.0.1:8000".
    :return: True for the entrypoint's expected backend configuration.
    :raises ValueError: The URL is invalid.
    """
    if entrypoint == "legacy":
        return not server_url
    url = urlsplit(server_url)
    return (
        entrypoint == "facade"
        and url.scheme == "http"
        and url.hostname in {"localhost", "127.0.0.1"}
        and bool(url.port)
        and url.netloc == f"{url.hostname}:{url.port}"
        and url.path in {"", "/"}
        and not (url.query or url.fragment)
    )


class StdioMCPClient(AbstractContextManager["StdioMCPClient"]):
    """Real protocol client over either existing stdio subprocess."""

    def __init__(
        self,
        *,
        entrypoint: MCPEntrypoint,
        actor_username: str,
        dataset: MCPDataset,
        server_url: str,
        root: Path,
        include_summaries: bool = False,
        database_scope: CedarDatabaseScope | None = None,
    ) -> None:
        """Capture explicit backend, actor and owned subprocess paths.

        :param entrypoint: Actual executable surface. Example: "facade".
        :param actor_username: Explicit actor. Example: "mchen".
        :param dataset: In-process HTTP-backend fixture references. Example: Cedar.
        :param server_url: Real facade backend, or empty for legacy. Example: live_server.url.
        :param root: Pytest-owned subprocess directory. Example: tmp_path.
        :param include_summaries: Complete S23 invariants required. Example: True.
        :param database_scope: Explicit live file-runner proof, or None for normal runners.
        :return: None. Example: unopened protocol client.
        :raises ValueError: Invalid dependencies/ownership.
        """
        if (
            actor_username not in dataset.cedar.users_by_username
            or not _valid_stdio_server(entrypoint, server_url)
            or not root.is_dir()
            or root.is_symlink()
        ):
            raise ValueError(
                "Stdio requires a fixture actor, an isolated backend and an owned directory."
            )
        self.entrypoint, self.actor_username = entrypoint, actor_username
        self.dataset, self.server_url, self.root = dataset, server_url, root
        self.include_summaries = include_summaries
        self.database_scope = database_scope
        self._process: Popen[bytes] | None = None
        self._database: MCPSubprocessDatabase | None = None
        self._resources = ExitStack()
        self._stderr_file: BinaryIO | None = None
        self._token = ""
        self._request_id = 0
        self._pending_stdout = b""
        self.stderr = ""
        self.stdout_messages: list[Mapping[str, object]] = []

    def __enter__(self) -> Self:
        """Prepare isolated backend, launch existing server and complete handshake.

        :return: Connected actual stdio client. Example: initialized facade server.
        :raises RuntimeError: Startup/handshake failure after resource cleanup.
        """
        try:
            self._prepare_backend()
            self._start_process()
            self.initialize()
        except BaseException as error:
            self.__exit__(type(error), error, error.__traceback__)
            raise
        return self

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
        try:
            self._stop_process()
        except (AssertionError, OSError, RuntimeError, TimeoutExpired):
            if exc is None:
                raise
            exc.add_note("Facade stdio cleanup also failed.")
        return False

    def initialize(self) -> Mapping[str, object]:
        """Perform real initialize request followed by initialized notification.

        :return: Actual initialization result. Example: serverInfo/protocolVersion.
        :raises AssertionError: Invalid handshake or incompatible response.
        """
        result = self._request(
            "initialize",
            {
                "protocolVersion": LATEST_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "mimir-karma-integration", "version": "1"},
            },
        )
        assert result.get("protocolVersion") == LATEST_PROTOCOL_VERSION
        server_info = result.get("serverInfo")
        assert isinstance(server_info, dict)
        assert server_info.get("name") == "Mimir Methodology Assistant"
        assert (
            isinstance(result.get("capabilities"), dict)
            and "tools" in result["capabilities"]
        )
        self._notify("notifications/initialized", {})
        return result

    def list_tools(self) -> tuple[Mapping[str, object], ...]:
        """Read actual registered tool schemas via tools/list.

        :return: Real schema entries. Example: get_pip input schema.
        :raises AssertionError: Missing/malformed tool list.
        """
        tools = self._request("tools/list", {}).get("tools")
        assert (
            isinstance(tools, list) and tools
        ), "No registered MCP tools were returned."
        assert all(
            isinstance(tool, dict) and isinstance(tool.get("inputSchema"), dict)
            for tool in tools
        )
        return tuple(tools)

    def call(self, case: MCPCase) -> object:
        """Call an actual tool with the actor authenticated at startup.

        :param case: Explicit invocation. Example: Mike reading Maria Design PIP.
        :return: Actual decoded content. Example: historical changes.
        :raises AssertionError: Tool error, malformed result or wrong actor context.
        """
        assert (
            case.actor_username == self.actor_username
        ), "Case actor differs from the stdio token actor."
        result = self._request(
            "tools/call", {"name": case.tool_name, "arguments": dict(case.arguments)}
        )
        return decode_tool_payload(result)

    def snapshot(self) -> MCPInvariantSnapshot:
        """Read actual HTTP-backend or independent legacy DB invariants.

        :return: Actual canonical state. Example: complete award pair after fetch.
        :raises AssertionError: Backend isolation or required state unavailable.
        """
        if self.entrypoint == "facade":
            return karma_snapshot(include_summaries=self.include_summaries)
        database = self._database
        if database is None or not database.database_path.is_file():
            raise RuntimeError("An active legacy database is required for a snapshot.")
        destination = database.root / "snapshot.json"
        try:
            script = (
                "from pathlib import Path\n"
                "from tests.support.karma_mcp import write_mcp_subprocess_snapshot\n"
                f"write_mcp_subprocess_snapshot(Path({str(destination)!r}), "
                f"include_summaries={self.include_summaries!r})"
            )
            _run_management(database, ("shell", "--no-imports", "-c", script))
            return MCPInvariantSnapshot(
                **json.loads(destination.read_text(encoding="utf-8"))
            )
        finally:
            destination.unlink(missing_ok=True)

    def assert_protocol_clean(self) -> None:
        """Require every observed stdout message to be valid protocol JSON.

        :return: None. Example: requests/results/notifications only.
        :raises AssertionError: Banner, log line, malformed JSON or unmatched result.
        """
        assert self._process is not None and self._process.returncode == 0
        assert (
            not self._pending_stdout
        ), "Child wrote more stdout after its last matched response."
        response_ids = [
            message["id"] for message in self.stdout_messages if "id" in message
        ]
        assert response_ids == list(range(1, self._request_id + 1))

    def _prepare_backend(self) -> None:
        """Prepare isolated legacy state or a real token against the HTTP backend.

        :return: None. Example: actor token placed in private facade environment.
        :raises RuntimeError: Actor/backend/ownership preparation fails.
        """
        if self.entrypoint == "legacy":
            directory = self._resources.enter_context(
                TemporaryDirectory(prefix="mimir-mcp-legacy-")
            )
            self._database = provision_mcp_subprocess_database(
                Path(directory).resolve()
            )
            return
        _resolve_database_scope(self.database_scope)
        _, self._token = _load_actor_and_token(self.dataset, self.actor_username)

    def _start_process(self) -> None:
        """Launch the real entrypoint with protocol pipes and separate temporary stderr.

        :return: None. Example: live child process with owned streams.
        :raises RuntimeError: Child exits or cannot start.
        """
        command = _stdio_command(self.entrypoint, self.actor_username)
        self._stderr_file = self._resources.enter_context(
            TemporaryFile(dir=self.root)  # noqa: SIM115 — ExitStack owns the file.
        )
        self._process = Popen(
            command,
            cwd=self.root,
            env=self._stdio_environment(),
            stdin=PIPE,
            stdout=PIPE,
            stderr=self._stderr_file,
        )

    def _stdio_environment(self) -> Mapping[str, str]:
        """Expose only the environment required by this MCP child.

        :return: An allowlisted environment. Example: private URL and token for facade.
        """
        if self._database is not None:
            return self._database.environment
        return {
            "PATH": os.defpath,
            "PYTHONPATH": str(_PROJECT_ROOT),
            "PYTHONIOENCODING": "utf-8",
            "MIMIR_SERVER_URL": self.server_url,
            "MIMIR_TOKEN": self._token,
        }

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
        self._request_id += 1
        self._write_message(
            {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": method,
                "params": dict(parameters),
            }
        )
        try:
            message = self._read_response(self._request_id, _STDIO_TIMEOUT_SECONDS)
        except ValidationError:
            raise AssertionError(
                "Facade stdout contained invalid protocol output."
            ) from None
        result = message["result"]
        assert isinstance(result, dict)
        return result

    def _notify(self, method: str, parameters: Mapping[str, object]) -> None:
        """Send a notification without waiting for a nonexistent response.

        :param method: Notification name. Example: "notifications/initialized".
        :param parameters: Notification parameters. Example: {}.
        :return: None. Example: initialized notification written.
        :raises RuntimeError: Child input unavailable.
        """
        self._write_message(
            {"jsonrpc": "2.0", "method": method, "params": dict(parameters)}
        )

    def _write_message(self, message: Mapping[str, object]) -> None:
        """Write one actual JSON-RPC line and flush the child input.

        :param message: Protocol envelope. Example: initialize request.
        :return: None. Example: one complete JSON line flushed.
        :raises RuntimeError: Closed/broken child input.
        """
        if self._process is None or self._process.stdin is None:
            raise RuntimeError("Facade stdio input is unavailable.")
        self._process.stdin.write(json.dumps(dict(message)).encode("utf-8") + b"\n")
        self._process.stdin.flush()

    def _read_response(
        self, request_id: int, timeout_seconds: float
    ) -> Mapping[str, object]:
        """Read bounded actual output, retaining valid intervening notifications.

        :param request_id: Expected response identity. Example: 3.
        :param timeout_seconds: Named bounded deadline. Example: 30.0.
        :return: Matched response. Example: tools/call result.
        :raises TimeoutError: No matching result before deadline.
        :raises AssertionError: Unexpected response or child failure.
        :raises ValidationError: Malformed JSON-RPC line.
        """
        process = self._process
        assert process is not None and process.stdout is not None
        descriptor = process.stdout.fileno()
        deadline = monotonic() + timeout_seconds
        while (remaining := deadline - monotonic()) > 0:
            line, separator, tail = self._pending_stdout.partition(b"\n")
            if not separator:
                ready, _, _ = select([descriptor], [], [], remaining)
                if not ready:
                    break
                chunk = os.read(descriptor, _STDIO_READ_SIZE)
                if not chunk:
                    raise AssertionError(
                        "Facade stdout closed before its JSON-RPC response."
                    )
                self._pending_stdout += chunk
                continue
            self._pending_stdout = tail
            if self._token and self._token.encode("utf-8") in line:
                raise AssertionError("Facade stdout exposed its test credential.")
            message = JSONRPCMessage.model_validate_json(line).root
            envelope = message.model_dump(mode="json", exclude_unset=True)
            self.stdout_messages.append(envelope)
            if isinstance(message, JSONRPCResponse) and message.id == request_id:
                return envelope
            assert isinstance(
                message, JSONRPCNotification
            ), "Unexpected facade JSON-RPC message."
        raise TimeoutError(f"No facade JSON-RPC response for request {request_id}.")

    def _drain_stderr(self) -> None:
        """Read bounded diagnostics after the child has closed its stderr.

        :return: None. Example: bounded diagnostic buffer retained privately.
        :raises AssertionError: Excessive output or a leaked test credential.
        """
        if self._stderr_file is None:
            return
        self._stderr_file.seek(0)
        stderr = self._stderr_file.read(_STDIO_STDERR_LIMIT + 1)
        if len(stderr) > _STDIO_STDERR_LIMIT:
            raise AssertionError("Facade emitted excessive diagnostic output.")
        if self._token and self._token.encode("utf-8") in stderr:
            raise AssertionError("Facade stderr exposed its test credential.")
        self.stderr = stderr.decode("utf-8", errors="replace")

    def _stop_process(self) -> None:
        """Close child input, reap the process and close its diagnostic stream.

        :return: None. Example: no remaining child or stream resources.
        :raises RuntimeError: Child/resource cleanup cannot complete.
        """
        try:
            if self._process is not None:
                # Closing stdin gives the server an EOF. communicate drains residual
                # stdout and reaps the process before any assertion inspects stderr.
                try:
                    stdout, _ = self._process.communicate(
                        timeout=_STDIO_EXIT_TIMEOUT_SECONDS
                    )
                except TimeoutExpired:
                    self._process.kill()
                    self._process.communicate(timeout=_STDIO_EXIT_TIMEOUT_SECONDS)
                    raise RuntimeError(
                        "Facade stdio process failed to stop on EOF."
                    ) from None
                trailing = self._pending_stdout + stdout
                if self._token and self._token.encode("utf-8") in trailing:
                    raise AssertionError("Facade stdout exposed its test credential.")
                self._pending_stdout = trailing
            self._drain_stderr()
        finally:
            self._resources.close()
            self._token = ""


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


_COLLECTION_FIELDS = {
    "facade": {
        "list_playbooks": (
            "id",
            "name",
            "status",
            "version",
            "category",
            "visibility",
            "workflow_count",
        ),
        "list_workflows": (
            "id",
            "playbook_id",
            "name",
            "description",
            "abbreviation",
            "order",
            "activity_count",
            "activities",
        ),
        "list_activities": (
            "id",
            "workflow_id",
            "name",
            "phase_id",
            "order",
            "predecessor_id",
            "predecessor_name",
            "agent_id",
            "agent_name",
            "skills",
        ),
        "list_phases": (
            "id",
            "playbook_id",
            "name",
            "description",
            "order",
            "activity_count",
        ),
        "list_skills": (
            "id",
            "playbook_id",
            "title",
            "content",
            "capability_domain",
            "technology_stack",
            "activity_count",
        ),
        "list_rules": ("id", "playbook_id", "title", "slug", "content", "always_apply"),
        "list_agents": ("id", "playbook_id", "name", "description", "activity_count"),
        "list_artifacts": (
            "id",
            "playbook_id",
            "produced_by_id",
            "name",
            "description",
            "type",
            "is_required",
            "consumer_count",
        ),
        "list_pips": (
            "id",
            "playbook_id",
            "title",
            "summary",
            "status",
            "submitted_by_username",
            "submitted_at",
            "status_changed_at",
            "changes_count",
        ),
    },
    "legacy": {
        "list_playbooks": (
            "id",
            "name",
            "description",
            "category",
            "status",
            "version",
            "visibility",
        ),
        "list_workflows": (
            "id",
            "name",
            "description",
            "abbreviation",
            "order",
            "playbook_id",
        ),
        "list_activities": (
            "id",
            "name",
            "phase_id",
            "order",
            "workflow_id",
            "predecessor_id",
            "successor_id",
        ),
        "list_phases": (
            "id",
            "name",
            "description",
            "order",
            "playbook_id",
            "created_at",
            "updated_at",
        ),
        "list_skills": (
            "id",
            "title",
            "capability_domain",
            "technology_stack",
            "activity_count",
            "playbook_id",
        ),
        "list_rules": (
            "id",
            "title",
            "slug",
            "always_apply",
            "activity_count",
            "playbook_id",
        ),
        "list_agents": ("id", "name", "description", "activity_count", "playbook_id"),
        "list_artifacts": (
            "id",
            "name",
            "type",
            "is_required",
            "produced_by_id",
            "playbook_id",
        ),
        "list_pips": (
            "id",
            "title",
            "summary",
            "status",
            "playbook_id",
            "submitted_by_username",
            "submitted_at",
            "status_changed_at",
            "changes_count",
        ),
    },
}
_COLLECTION_RESOURCES = {
    tool: tool.removeprefix("list_") for tool in _COLLECTION_FIELDS["facade"]
}
_COLLECTION_MODELS = {
    "list_workflows": Workflow,
    "list_activities": Activity,
    "list_phases": Phase,
    "list_skills": Skill,
    "list_rules": Rule,
    "list_agents": Agent,
    "list_artifacts": Artifact,
}
_COLLECTION_ORDER = {
    "list_workflows": ("order",),
    "list_activities": ("order",),
    "list_phases": ("order",),
    "list_skills": ("title",),
    "list_rules": ("title",),
    "list_agents": ("name",),
    "list_artifacts": ("name",),
}


def _collection_arguments(tool_name: str, dataset: MCPDataset) -> Mapping[str, object]:
    """Resolve actual parent identifiers, preserving the ordinary list API.

    :param tool_name: Supported collection. Example: "list_activities".
    :param dataset: Real fixture relationships. Example: Mike workflow6202.
    :return: Actual tool arguments. Example: {"workflow_id": 6202}.
    :raises KeyError: Required real fixture is missing.
    """
    if tool_name == "list_playbooks":
        return {"status": "all"}
    if tool_name == "list_pips":
        return {"scope": "mine"}
    parent = "workflow_id" if tool_name == "list_activities" else "playbook_id"
    fixture = "mike_workflow" if parent == "workflow_id" else "mike_playbook"
    return {parent: dataset.entity_ids[fixture]}


def _collection_expected_objects(
    tool_name: str, dataset: MCPDataset, actor_username: str, entrypoint: MCPEntrypoint
) -> list[Model]:
    """Read independent ORM identities/order without calling wrappers or serializers.

    :param tool_name: Supported collection. Example: "list_rules".
    :param dataset: Real fixture. Example: Mike's public released book.
    :param actor_username: Explicit active actor. Example: "mrodriguez".
    :param entrypoint: Existing ordering contract. Example: "legacy".
    :return: Actual expected objects in native order. Example: one Rule.
    :raises LookupError: Expected model or actor is missing.
    """
    actor = dataset.cedar.users_by_username[actor_username]
    if tool_name == "list_playbooks":
        allowed = Q(author=actor) | Q(
            visibility="public", status__in=("released", "disabled")
        )
        return list(Playbook.objects.filter(allowed).order_by("-updated_at"))
    if tool_name == "list_pips":
        return list(
            ProcessImprovementProposal.objects.filter(created_by=actor).order_by(
                "-updated_at", "-pk"
            )
        )
    arguments = _collection_arguments(tool_name, dataset)
    order = _COLLECTION_ORDER[tool_name]
    if entrypoint == "legacy" and tool_name == "list_rules":
        order = ("slug",)
    if entrypoint == "legacy" and tool_name == "list_artifacts":
        order = ("produced_by__order", "name")
    return list(
        _COLLECTION_MODELS[tool_name].objects.filter(**arguments).order_by(*order)
    )


def _collection_playbooks(actor: User) -> list[Model]:
    """Materialize all three existing authorized native playbook list services.

    :param actor: Actual authenticated user. Example: Maria.
    :return: Existing combined native ordered objects. Example: owned/public/team.
    :raises PermissionError: Existing native service denies access.
    """
    rows = list(PlaybookService.list_playbooks(actor))
    rows.extend(PlaybookService.list_public_playbooks(actor))
    rows.extend(PlaybookService.list_team_playbooks_for_user(actor))
    rows.sort(
        key=lambda row: (row.updated_at is None, row.updated_at or row.created_at),
        reverse=True,
    )
    return rows


def _collection_native_rows(case: MCPCase, dataset: MCPDataset) -> tuple[Model, ...]:
    """Invoke the real service for each collection, without a consumption writer.

    :param case: Explicit native contract. Example: Maria list_workflows.
    :param dataset: Actual parent/actor references. Example: Mike book6201.
    :return: Fully materialized actual models. Example: (Workflow(...),).
    :raises PermissionError: Actor cannot read the real parent.
    :raises ValueError: Unsupported tool.
    """
    actor = dataset.cedar.users_by_username[case.actor_username]
    book = dataset.cedar.playbooks_by_pk[dataset.entity_ids["mike_playbook"]]
    if case.tool_name not in ("list_playbooks", "list_pips") and not book.can_view(
        actor
    ):
        raise PermissionError("Collection parent is unavailable.")
    calls = {
        "list_playbooks": lambda: _collection_playbooks(actor),
        "list_workflows": lambda: WorkflowService.get_workflows_for_playbook(book.pk),
        "list_activities": lambda: ActivityService.get_activities_for_workflow(
            dataset.cedar.workflows_by_pk[dataset.entity_ids["mike_workflow"]]
        ),
        "list_phases": lambda: PhaseService.list_phases(book.pk, actor),
        "list_skills": lambda: SkillService.list_skills_for_playbook(book.pk),
        "list_rules": lambda: RuleService.list_rules_for_playbook(book.pk),
        "list_agents": lambda: AgentService.list_agents_for_playbook(book.pk),
        "list_artifacts": lambda: ArtifactService.get_artifacts_for_playbook(book),
        "list_pips": lambda: PIPService.list_queryset_for_user(
            actor=actor, scope="mine"
        ),
    }
    return tuple(calls[case.tool_name]())


def _collection_metadata(
    entity: Model, tool_name: str, entrypoint: MCPEntrypoint
) -> Mapping[str, object]:
    """Project explicit native field contracts from independent ORM values.

    :param entity: Real persisted row. Example: Mike's Workflow.
    :param tool_name: Actual list name. Example: "list_workflows".
    :param entrypoint: Actual surface. Example: "facade".
    :return: Exact expected native metadata. Example: workflow with lightweight activities.
    :raises AssertionError: Required expected field cannot be resolved.
    """
    fields = _COLLECTION_FIELDS[entrypoint][tool_name]
    values = {name: getattr(entity, name) for name in fields if hasattr(entity, name)}
    values.update(_collection_core_extras(entity))
    values.update(_collection_resource_extras(entity))
    values.update(_collection_pip_times(entity, entrypoint))
    if "version" in values:
        values["version"] = str(values["version"])
    return {name: values[name] for name in fields if name in values}


def _collection_core_extras(entity: Model) -> Mapping[str, object]:
    """Resolve real lightweight core relations without detail retrieval.

    :param entity: Real core object. Example: Workflow6202.
    :return: Actual related metadata. Example: activity_count and three-field children.
    :raises AttributeError: Expected real relation is missing.
    """
    if isinstance(entity, Playbook):
        return {"workflow_count": entity.workflows.count()}
    if isinstance(entity, Workflow):
        return {
            "activity_count": entity.activities.count(),
            "activities": list(
                entity.activities.order_by("order").values("id", "name", "order")
            ),
        }
    if isinstance(entity, Activity):
        data = {
            "skills": list(
                entity.skills.all().values(
                    "id", "title", "capability_domain", "technology_stack"
                )
            )
        }
        if entity.predecessor_id is not None:
            data["predecessor_name"] = entity.predecessor.name
        if entity.agent_id is not None:
            data["agent_name"] = entity.agent.name
        return data
    return {}


def _collection_resource_extras(entity: Model) -> Mapping[str, object]:
    """Read actual relation counts required by the explicit resource schemas.

    :param entity: Real resource. Example: Skill with no linked activities.
    :return: Exact actual count metadata. Example: {"activity_count": 0}.
    :raises AttributeError: Expected real relation is missing.
    """
    if isinstance(entity, (Phase, Skill, Rule, Agent)):
        return {"activity_count": entity.activities.count()}
    if isinstance(entity, Artifact):
        return {"consumer_count": entity.inputs.count()}
    return {}


def _collection_pip_times(
    entity: Model, entrypoint: MCPEntrypoint
) -> Mapping[str, object]:
    """Preserve native phase/PIP time representations and summary metadata.

    :param entity: Actual time-bearing list row. Example: historical Maria PIP.
    :param entrypoint: Existing representation. Example: legacy ISO offset strings.
    :return: Exact nullable/empty time and PIP fields. Example: null API submitted_at.
    :raises AttributeError: Required persisted date/creator relation is absent.
    """
    if not isinstance(entity, (Phase, ProcessImprovementProposal)):
        return {}
    fields = (
        ("created_at", "updated_at")
        if isinstance(entity, Phase)
        else ("submitted_at", "status_changed_at")
    )
    data = {}
    for name in fields:
        value = getattr(entity, name)
        data[name] = (
            value.isoformat() if value else ("" if entrypoint == "legacy" else None)
        )
        if entrypoint == "facade" and isinstance(data[name], str):
            data[name] = data[name].replace("+00:00", "Z")
    if isinstance(entity, ProcessImprovementProposal):
        data.update(
            submitted_by_username=entity.created_by.username,
            changes_count=entity.changes.count(),
            summary=entity.summary or "",
        )
    return data


def _collection_parameter_validation(
    tool_name: str, dataset: MCPDataset, actor_username: str, entrypoint: MCPEntrypoint
) -> None:
    """Fail before ORM work for unsupported collection/actor/surface inputs.

    :param tool_name: Candidate list name. Example: "list_activities".
    :param dataset: Real fixture container. Example: MCPDataset(...).
    :param actor_username: Explicit known actor. Example: "mrodriguez".
    :param entrypoint: Real registration selector. Example: "facade".
    :return: None for valid contract inputs. Example: active Maria/list pair.
    :raises ValueError: Tool, actor, dataset or entrypoint is invalid.
    """
    if not isinstance(dataset, MCPDataset) or entrypoint not in _COLLECTION_FIELDS:
        raise ValueError("An actual dataset and supported MCP entrypoint are required.")
    if tool_name not in _COLLECTION_FIELDS[entrypoint]:
        raise ValueError("Unsupported collection tool.")
    actor = dataset.cedar.users_by_username.get(actor_username)
    if actor is None or not actor.is_active:
        raise ValueError("An explicit active Cedar actor is required.")
