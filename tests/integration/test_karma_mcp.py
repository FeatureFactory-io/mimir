"""Real MCP/HTTP/DB proofs for the nine eligible detail tools."""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, replace
from importlib import import_module
from pathlib import Path
from uuid import UUID

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.core.exceptions import SynchronousOnlyOperation
from django.db.models import Model, Sum
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
from fastmcp import Client as RegisteredMCPClient
from fastmcp.exceptions import ToolError
from httpx import Client as HTTPClient
from pytest import LogCaptureFixture
from pytest_django.live_server_helper import LiveServer
from rest_framework.authtoken.models import Token

from mcp_integration.context import (
    _current_user,
    clear_current_user,
    get_current_user,
    set_current_user,
)
from mcp_integration.facade import client as facade_client
from methodology.api.consumption_views import ReceiptChannel
from methodology.models import Agent, Artifact, KarmaAward, Phase, Playbook, Rule, Skill
from methodology.services.karma_service import KarmaService
from methodology.services.phase_service import PhaseService
from tests.support.experts_data import CedarDataset
from tests.support.experts_logs import capture_experts_logs
from tests.support.karma_mcp import (
    MCPCase,
    MCPClientFactory,
    MCPDataset,
    MCPEntrypoint,
    MCPRuntimeState,
    StdioMCPClient,
    _capture_mcp_runtime,
    decode_tool_payload,
    detail_case,
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

DETAIL_TOOLS: tuple[str, ...] = (
    "get_playbook",
    "get_workflow",
    "get_phase",
    "get_activity",
    "get_skill",
    "get_rule",
    "get_agent",
    "get_artifact",
    "get_pip",
)


RECEIPT_UUID = UUID("55f41062-b673-4698-bf16-91f871b6408f")
RECEIPT_RETRY_UUID = UUID("ec7fd558-e398-4c81-9c40-b5b06e103a85")
RECEIPT_REQUEST_ID = "cedar-mcp-receipt-01"
RECEIPT_VIEW = "ConsumptionReceiptView.post"
CEDAR_PLAYBOOK_ID = 6201
CEDAR_WORKFLOW_ID = 6202
CEDAR_ACTIVITY_ID = 6203


@dataclass(frozen=True)
class _ReceiptDetailCase:
    entity: Model
    playbook: Playbook
    actor: User
    author: User
    display_field: str
    category: str
    expected_totals: tuple[int, int]


def _receipt_detail_case(tool_name: str, dataset: CedarDataset) -> _ReceiptDetailCase:
    """Use the Cedar owners and imported targets, supplying absent resource kinds."""
    entity_type = tool_name.removeprefix("get_")
    if entity_type == "pip":
        pip = dataset.pips_by_key["HIST-MARIA-DESIGN-01"]
        return _ReceiptDetailCase(
            pip,
            dataset.playbooks_by_pk[6106],
            dataset.users_by_username["mchen"],
            dataset.users_by_username["hkim"],
            "title",
            "design",
            (12455, 5805),
        )

    playbook = dataset.playbooks_by_pk[CEDAR_PLAYBOOK_ID]
    activity = dataset.activities_by_pk[CEDAR_ACTIVITY_ID]
    entities = {
        "playbook": playbook,
        "workflow": dataset.workflows_by_pk[CEDAR_WORKFLOW_ID],
        "activity": activity,
    }
    entity = entities.get(entity_type)
    display_field = "name"
    if entity is None:
        model, fields = {
            "phase": (Phase, {"name": "Review phase"}),
            "skill": (
                Skill,
                {"title": "Review skill", "content": "Cedar skill guidance"},
            ),
            "rule": (Rule, {"title": "Review rule", "slug": "review-rule"}),
            "agent": (Agent, {"name": "Review agent"}),
            "artifact": (
                Artifact,
                {"name": "Evidence checklist", "produced_by": activity},
            ),
        }[entity_type]
        entity = model.objects.create(playbook=playbook, **fields)
        if "title" in fields:
            display_field = "title"
    return _ReceiptDetailCase(
        entity,
        playbook,
        dataset.users_by_username["mrodriguez"],
        dataset.users_by_username["mchen"],
        display_field,
        "development",
        (8205, 12455),
    )


def _token_header(actor: User) -> str:
    """Return the actual provisioned DRF authorization header."""
    token, _ = Token.objects.get_or_create(user=actor)
    return f"Token {token.key}"


def _receipt_payload() -> dict[str, object]:
    """Build an independent valid activity receipt for Django HTTP proofs."""
    return {
        "entity_type": "activity",
        "entity_id": CEDAR_ACTIVITY_ID,
        "event_identity": str(RECEIPT_UUID),
        "channel": "mcp_detail",
    }


def _post_receipt(
    client: Client, payload: object, authorization: str | None = None
) -> HttpResponse:
    """Post a real JSON request, optionally with the actual token header."""
    headers = {"HTTP_X_REQUEST_ID": RECEIPT_REQUEST_ID}
    if authorization is not None:
        headers["HTTP_AUTHORIZATION"] = authorization
    return client.post(
        reverse("api_consumption_receipt"),
        data=payload if isinstance(payload, str) else json.dumps(payload),
        content_type="application/json",
        **headers,
    )


def _receipt_awards(actor: User, channel: str, identity: UUID) -> list[KarmaAward]:
    """Read the exact canonical award pair from the real ledger."""
    return list(
        KarmaAward.objects.filter(
            event_identity=f"consumption:{channel}:{actor.pk}:{identity}"
        ).order_by("pk")
    )


def _total_points(user: User) -> int:
    """Read an actual recipient's aggregate ledger points."""
    return user.karma_awards.aggregate(points=Sum("points", default=0))["points"]


def _assert_receipt_log(
    caplog: LogCaptureFixture,
    beat: str,
    actor: User,
    *fragments: str,
) -> None:
    """Assert an INFO beat ties the authenticated actor to a stable request ID."""
    assert_log_story(
        caplog,
        where=RECEIPT_VIEW,
        beats={
            beat: (
                f"| {beat} |",
                f"actor_id={actor.pk}",
                f"request_id={RECEIPT_REQUEST_ID}",
                *fragments,
            )
        },
    )


MCP_LOGGERS = (
    "mcp_integration.context",
    "mcp_integration.facade.tools_http",
    "mcp_integration.tools",
    "methodology.api.consumption_views",
    "methodology.services.karma_service",
    "methodology.services.phase_service",
)
UNSAFE_ORM_FLAG = "DJANGO_ALLOW_ASYNC_UNSAFE"
CONSUMPTION_LOG = "KarmaService.award_successful_consumption"
RECEIPT_PATH = "/api/consumption-receipts/"


def _eligible_mcp_case(tool_name: str, dataset: MCPDataset) -> MCPCase:
    """Select the independent Cedar actor and authorized fixture for each tool."""
    entity_type = tool_name.removeprefix("get_")
    actor, fixture_key = (
        ("mchen", "maria_design_pip")
        if entity_type == "pip"
        else ("mrodriguez", f"mike_{entity_type}")
    )
    return detail_case(
        tool_name, dataset, actor_username=actor, fixture_key=fixture_key
    )


def _assert_mcp_content(
    case: MCPCase, payload: object, entrypoint: MCPEntrypoint
) -> None:
    """Check the actual ID and source content returned before crediting a read."""
    assert isinstance(payload, dict)
    assert payload["id"] == next(iter(case.arguments.values()))
    assert all(payload.get(field) == value for field, value in case.expected.items())
    if case.tool_name == "get_pip":
        assert [row["name"] for row in payload["changes"]] == [
            "Keyboard Navigation Audit",
            "Error Message Review",
        ]
        assert payload["submitted_by_username"] == "mrodriguez"
    if case.tool_name == "get_phase" and entrypoint == "legacy":
        assert payload["activities"][0]["activities"][0]["id"] == CEDAR_ACTIVITY_ID
        assert payload["artifacts"][0]["name"] == "Cedar Evidence Checklist"


def _assert_mcp_pair(case: MCPCase, dataset: MCPDataset, before_count: int) -> str:
    """Read persisted learner and author awards, including their exact timestamp."""
    users = dataset.cedar.users_by_username
    actor = users[case.actor_username]
    is_pip = case.tool_name == "get_pip"
    author = users["hkim" if is_pip else "mchen"]
    playbook_id, category = (6106, "design") if is_pip else (6201, "development")
    awards = _receipt_awards(actor, "mcp_detail", RECEIPT_UUID)
    assert KarmaAward.objects.count() == before_count + 2
    assert len(awards) == 2
    assert {(row.recipient_id, row.source_kind, row.points) for row in awards} == {
        (actor.pk, KarmaAward.SourceKind.LEARNING, 5),
        (author.pk, KarmaAward.SourceKind.CONSUMPTION, 5),
    }
    assert awards[0].occurred_at == awards[1].occurred_at
    for row in awards:
        assert row.category == category
        assert row.event_channel == "mcp_detail"
        assert row.playbook_id_snapshot == playbook_id
        assert row.entity_type_snapshot == case.tool_name.removeprefix("get_")
        assert row.entity_id_snapshot == next(iter(case.arguments.values()))
        assert row.change_id_snapshot is None
    if is_pip:
        assert _total_points(users["mrodriguez"]) == 8200
    totals = (12455, 5805) if is_pip else (8205, 12455)
    assert (_total_points(actor), _total_points(author)) == totals
    return awards[0].occurred_at.isoformat()


def _assert_mcp_success_logs(
    caplog: LogCaptureFixture,
    case: MCPCase,
    dataset: MCPDataset,
    entrypoint: MCPEntrypoint,
    timestamp: str,
) -> None:
    """Check real boundary and service records for the same immutable action."""
    users = dataset.cedar.users_by_username
    actor, author = users[case.actor_username], users["hkim"]
    identity = f"event_identity={RECEIPT_UUID}"
    entity = f"entity_id={case.arguments['pip_id']}"
    boundary = (
        "_complete_mcp_detail"
        if entrypoint == "facade"
        else "_complete_legacy_mcp_detail"
    )
    assert_log_story(
        caplog,
        where=boundary,
        beats={
            "entry": (
                "| entry |",
                "tool=get_pip",
                "entity_type=pip",
                entity,
                identity,
                "channel=mcp_detail",
            )
        },
    )
    if entrypoint == "facade":
        assert_log_story(
            caplog,
            where=RECEIPT_VIEW,
            beats={
                "validation": (
                    "| validation |",
                    f"actor_id={actor.pk}",
                    f"request_id={RECEIPT_UUID}",
                    "entity_type=pip",
                    entity,
                    identity,
                    "channel=mcp_detail",
                )
            },
        )
    canonical = f"event_identity=consumption:mcp_detail:{actor.pk}:{RECEIPT_UUID}"
    assert_log_story(
        caplog,
        where=CONSUMPTION_LOG,
        beats={
            "branch": (
                "| branch |",
                canonical,
                f"actor_id={actor.pk}",
                "playbook_id=6106",
                f"author_id={author.pk}",
                "category=design",
                "reason=eligible",
            ),
            "applied": (
                "| exit |",
                canonical,
                "created_count=2",
                f"occurred_at={timestamp}",
            ),
            "duplicate": (
                "| exit |",
                canonical,
                "duplicate",
                f"occurred_at={timestamp}",
            ),
        },
    )
    ordered_beats = [
        ("entry", boundary),
        *((("validation", RECEIPT_VIEW),) if entrypoint == "facade" else ()),
        ("branch", CONSUMPTION_LOG),
        ("exit", CONSUMPTION_LOG),
    ]
    actual_beats = [
        (beat, logger)
        for record in caplog.records
        for beat, logger in ordered_beats
        if logger in record.getMessage()
        and f"| {beat} |" in record.getMessage()
        and str(RECEIPT_UUID) in record.getMessage()
    ]
    assert actual_beats == ordered_beats * 2


@pytest.mark.parametrize("tool_name", DETAIL_TOOLS)
@pytest.mark.django_db(transaction=True)
async def test_mcp_detail_with_authorized_fixture_returns_content_and_pair(
    tool_name: str, mcp_client_factory: MCPClientFactory, mcp_dataset: MCPDataset
) -> None:
    """Prove T1 against real registered facade, token, HTTP and DB.

    :param tool_name: Independent Cedar case. Example: "get_pip".
    :param mcp_client_factory: Actor-explicit real registered client factory.
    :param mcp_dataset: Genuine independently seeded Cedar fixture data.
    :return: None. Example: all content/award assertions pass.
    :raises AssertionError: Content, schema, recipient or totals differ.
    """
    case = _eligible_mcp_case(tool_name, mcp_dataset)
    before = await KarmaAward.objects.acount()
    async with mcp_client_factory.open(
        actor_username=case.actor_username, entrypoint="facade"
    ) as session:
        schema = next(
            tool.inputSchema
            for tool in await session.client.list_tools()
            if tool.name == tool_name
        )
        assert "event_identity" in schema["properties"]
        assert "event_identity" not in schema.get("required", [])
        assert set(schema["properties"]) == {*case.arguments, "event_identity"} | (
            {"include_history", "version"} if tool_name == "get_playbook" else set()
        )
        result = await session.client.call_tool(
            tool_name, {**case.arguments, "event_identity": str(RECEIPT_UUID)}
        )
        assert session.request_paths == [("GET", case.route), ("POST", RECEIPT_PATH)]

    _assert_mcp_content(case, decode_tool_payload(result), "facade")
    await sync_to_async(_assert_mcp_pair)(case, mcp_dataset, before)


@pytest.mark.parametrize("tool_name", DETAIL_TOOLS)
@pytest.mark.django_db
def test_consumption_service_with_authorized_fixture_records_pair(
    tool_name: str,
    cedar_dataset: CedarDataset,
) -> None:
    """Prove both awards and immutable snapshots for a real authorized read.

    :param tool_name: Independent Cedar case. Example: "get_phase".
    :param cedar_dataset: Genuine historical baseline. Example: Mike's playbook.
    :return: None. Example: exactly two five-point awards.
    :raises AssertionError: Pair, snapshots or category attribution differs.
    """
    case = _receipt_detail_case(tool_name, cedar_dataset)
    entity_type = tool_name.removeprefix("get_")
    outcomes = KarmaService.award_successful_consumption(
        case.actor,
        entity_type,
        case.entity.pk,
        RECEIPT_UUID,
        channel="mcp_detail",
    )
    awards = _receipt_awards(case.actor, "mcp_detail", RECEIPT_UUID)

    assert len(outcomes) == len(awards) == 2
    assert all(outcome.created for outcome in outcomes)
    assert {outcome.award for outcome in outcomes} == set(awards)
    assert {
        (award.recipient_id, award.source_kind, award.points) for award in awards
    } == {
        (case.actor.pk, KarmaAward.SourceKind.LEARNING, 5),
        (case.author.pk, KarmaAward.SourceKind.CONSUMPTION, 5),
    }
    assert awards[0].occurred_at == awards[1].occurred_at
    for award in awards:
        assert award.category == case.category
        assert award.event_channel == "mcp_detail"
        assert award.playbook_id_snapshot == case.playbook.pk
        assert award.entity_type_snapshot == entity_type
        assert award.entity_id_snapshot == case.entity.pk
        assert award.change_id_snapshot is None
    assert (
        _total_points(case.actor),
        _total_points(case.author),
    ) == case.expected_totals
    assert (
        case.actor.username != "mchen"
        or _total_points(cedar_dataset.users_by_username["mrodriguez"]) == 8200
    )


@pytest.mark.parametrize("tool_name", DETAIL_TOOLS)
@pytest.mark.django_db(transaction=True)
async def test_mcp_detail_with_legacy_registration_returns_content_and_pair(
    tool_name: str, mcp_client_factory: MCPClientFactory, mcp_dataset: MCPDataset
) -> None:
    """Exercise the existing legacy FastMCP registration and real service.

    :param tool_name: Registered detail tool. Example: "get_activity".
    :return: None. Example: original content and exact paired awards.
    :raises AssertionError: Legacy registration bypasses the shared path.
    """
    case = _eligible_mcp_case(tool_name, mcp_dataset)
    before, environment = await KarmaAward.objects.acount(), os.environ.get(
        UNSAFE_ORM_FLAG
    )
    async with mcp_client_factory.open(
        actor_username=case.actor_username, entrypoint="legacy"
    ) as session:
        assert UNSAFE_ORM_FLAG not in os.environ
        schema = next(
            tool.inputSchema
            for tool in await session.client.list_tools()
            if tool.name == tool_name
        )
        assert "event_identity" in schema["properties"]
        assert "event_identity" not in schema.get("required", [])
        result = await session.client.call_tool(
            tool_name, {**case.arguments, "event_identity": str(RECEIPT_UUID)}
        )
        assert not session.request_paths

    assert os.environ.get(UNSAFE_ORM_FLAG) == environment
    _assert_mcp_content(case, decode_tool_payload(result), "legacy")
    await sync_to_async(_assert_mcp_pair)(case, mcp_dataset, before)


@pytest.mark.parametrize("tool_name", DETAIL_TOOLS)
@pytest.mark.django_db(transaction=True)
def test_mcp_detail_with_stdio_transport_returns_clean_jsonrpc(
    tool_name: str, live_server: LiveServer, mcp_dataset: MCPDataset, tmp_path: Path
) -> None:
    """Prove T3 with real facade subprocess and isolated HTTP backend.

    :param tool_name: Registered detail tool. Example: "get_rule".
    :param live_server: Real Django HTTP backend. Example: local random port.
    :param mcp_dataset: Independent Cedar fixture data. Example: Mike playbook 6201.
    :param tmp_path: Owned subprocess directory. Example: one per detail case.
    :return: None. Example: protocol-only stdout and exact persisted pair.
    :raises AssertionError: Protocol noise, missing content or wrong awards.
    """
    case = _eligible_mcp_case(tool_name, mcp_dataset)
    arguments = {**case.arguments, "event_identity": str(RECEIPT_UUID)}
    optional = {"include_history", "version"} if tool_name == "get_playbook" else set()
    before = KarmaAward.objects.count()
    roles = User.objects.order_by("pk").values_list("pk", "is_staff", "is_superuser")
    initial_roles = list(roles)
    with StdioMCPClient(
        entrypoint="facade",
        actor_username=case.actor_username,
        dataset=mcp_dataset,
        server_url=live_server.url,
        root=tmp_path,
    ) as wire:
        schemas = {tool["name"]: tool["inputSchema"] for tool in wire.list_tools()}
        schema = schemas[tool_name]
        assert set(schema["properties"]) == arguments.keys() | optional
        assert "event_identity" not in schema.get("required", [])
        assert KarmaAward.objects.count() == before
        payload = wire.call(replace(case, arguments=arguments))

    wire.assert_protocol_clean()
    requests = re.findall(r"HTTP Request: (.+)", wire.stderr)
    assert requests == [
        f'GET {live_server.url}{case.route} "HTTP/1.1 200 OK"',
        f'POST {live_server.url}{RECEIPT_PATH} "HTTP/1.1 200 OK"',
    ]
    _assert_mcp_content(case, payload, "facade")
    _assert_mcp_pair(case, mcp_dataset, before)
    assert list(roles.all()) == initial_roles


@pytest.mark.parametrize("tool_name", DETAIL_TOOLS)
@pytest.mark.django_db
def test_detail_rest_get_with_authorized_token_does_not_award(
    tool_name: str, client: Client, cedar_dataset: CedarDataset
) -> None:
    """Ensure bare authorized REST detail retrieval returns actual content award-free.

    :param tool_name: Detail route selector. Example: "get_skill".
    :param client: Real Django HTTP client. Example: Django's test client.
    :param cedar_dataset: Genuine historical baseline. Example: Mike's playbook.
    :return: None. Example: content returned with unchanged ledger.
    :raises AssertionError: GET creates any consumption award or hides valid content.
    """
    case = _receipt_detail_case(tool_name, cedar_dataset)
    url = reverse(f"api-{tool_name.removeprefix('get_')}-detail", args=[case.entity.pk])
    before = KarmaAward.objects.count()

    response = client.get(url, HTTP_AUTHORIZATION=_token_header(case.actor))

    assert response.status_code == 200
    assert response.json()["id"] == case.entity.pk
    assert response.json()[case.display_field] == getattr(
        case.entity, case.display_field
    )
    assert KarmaAward.objects.count() == before


@pytest.mark.parametrize(
    "override",
    [
        {field: "forged-private-body"}
        for field in (
            "actor",
            "actor_id",
            "user_id",
            "recipient",
            "recipient_id",
            "category",
            "points",
            "occurred_at",
            "event_channel",
            "gui_copy",
        )
    ]
    + [
        {"entity_type": "user"},
        {"entity_type": []},
        {"entity_id": True},
        {"entity_id": "6203"},
        {"entity_id": 0},
        {"entity_id": 2**63},
        {"channel": "gui_copy"},
        {"channel": []},
        {"event_identity": "forged-private-body"},
        {"event_identity": None},
    ],
)
@pytest.mark.django_db
def test_consumption_receipt_with_invalid_request_rejects_without_awards(
    client: Client,
    cedar_dataset: CedarDataset,
    caplog: LogCaptureFixture,
    override: dict[str, object],
) -> None:
    """Reject invalid and forged receipt fields without echoing private content.

    :param client: Real Django HTTP client. Example: client.
    :param cedar_dataset: Genuine historical baseline. Example: Maria's token.
    :param caplog: Actual receipt logs. Example: invalid_payload.
    :param override: Malformed/forged fields. Example: {"actor_id": 3}.
    :return: None. Example: invalid gui_copy channel creates no awards.
    :raises AssertionError: Invalid request writes awards or exposes data.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    authorization = _token_header(maria)
    before = KarmaAward.objects.count()
    with caplog.at_level(logging.INFO):
        response = _post_receipt(
            client, {**_receipt_payload(), **override}, authorization
        )

    assert response.status_code == 400
    assert response.json() == {"status": "rejected", "reason": "invalid_payload"}
    assert KarmaAward.objects.count() == before
    _assert_receipt_log(caplog, "branch", maria, "reason=invalid_payload")
    assert "forged-private-body" not in caplog.text + response.content.decode()
    assert authorization.split()[1] not in caplog.text
    assert not any(
        RECEIPT_VIEW in record.message and "| exit |" in record.message
        for record in caplog.records
    )


@pytest.mark.django_db
def test_consumption_receipt_with_noncanonical_json_rejects_without_awards(
    client: Client,
    cedar_dataset: CedarDataset,
) -> None:
    """Reject nonobject, malformed, missing, oversized and repeated members.

    :param client: Real Django HTTP client. Example: client.
    :param cedar_dataset: Genuine historical baseline. Example: Maria's token.
    :return: None. Example: JSON with duplicated entity ID is rejected.
    :raises AssertionError: Any malformed payload reaches persistence.
    """
    authorization = _token_header(cedar_dataset.users_by_username["mrodriguez"])
    payload = _receipt_payload()
    before = KarmaAward.objects.count()
    candidates = (
        [],
        42,
        "{broken",
        str(RECEIPT_UUID),
        {key: value for key, value in payload.items() if key != "channel"},
        json.dumps(payload)[:-1] + ', "entity_id": 6203}',
        json.dumps(payload) + " " * 1024,
    )

    for candidate in candidates:
        assert _post_receipt(client, candidate, authorization).status_code == 400
    assert KarmaAward.objects.count() == before


@pytest.mark.django_db
def test_consumption_receipt_with_missing_or_bad_token_rejects_session_actor(
    client: Client,
    cedar_dataset: CedarDataset,
) -> None:
    """Require the HTTP token even if Django already has a valid GUI session.

    :param client: Real Django HTTP client. Example: Maria's browser session.
    :param cedar_dataset: Genuine historical baseline. Example: Maria's account.
    :return: None. Example: rejected session-only request.
    :raises AssertionError: A missing/invalid token can write points.
    """
    client.force_login(cedar_dataset.users_by_username["mrodriguez"])
    before = KarmaAward.objects.count()
    for authorization in (None, "Token invalid-token"):
        response = _post_receipt(client, _receipt_payload(), authorization)
        assert response.status_code == 401
        assert response["WWW-Authenticate"] == "Token"
    assert KarmaAward.objects.count() == before


@pytest.mark.django_db
def test_consumption_receipt_with_inaccessible_target_rechecks_permission(
    client: Client,
    cedar_dataset: CedarDataset,
    caplog: LogCaptureFixture,
) -> None:
    """Revalidate revoked, missing and creator-or-staff-only content.

    :param client: Real Django HTTP client. Example: Maria's token-based client.
    :param cedar_dataset: Genuine historical baseline. Example: Hana's target book.
    :param caplog: Actual receipt logs. Example: target_unavailable.
    :return: None. Example: a successful earlier GET confers zero receipt authority.
    :raises AssertionError: Any ineligible request reveals private content or writes points.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    hana = cedar_dataset.users_by_username["hkim"]
    authorization = _token_header(maria)
    url = reverse("api-activity-detail", args=[CEDAR_ACTIVITY_ID])
    assert client.get(url, HTTP_AUTHORIZATION=authorization).status_code == 200
    book = cedar_dataset.playbooks_by_pk[CEDAR_PLAYBOOK_ID]
    book.visibility = "private"
    book.save(update_fields=["visibility"])
    pip = cedar_dataset.pips_by_key["HIST-MARIA-DESIGN-01"]
    pip_payload = {**_receipt_payload(), "entity_type": "pip", "entity_id": pip.pk}
    before = KarmaAward.objects.count()

    with caplog.at_level(logging.INFO):
        denied = _post_receipt(client, _receipt_payload(), authorization)
        missing = _post_receipt(
            client, {**_receipt_payload(), "entity_id": 2**63 - 1}, authorization
        )
        denied_pip = _post_receipt(client, pip_payload, _token_header(hana))

    assert denied.status_code == missing.status_code == 404
    assert denied.json() == missing.json()
    assert denied_pip.status_code == 404
    assert KarmaAward.objects.count() == before
    _assert_receipt_log(
        caplog,
        "branch",
        maria,
        "reason=target_unavailable",
        f"entity_id={CEDAR_ACTIVITY_ID}",
    )
    _assert_receipt_log(
        caplog, "branch", hana, "reason=target_unavailable", f"entity_id={pip.pk}"
    )
    assert pip.title not in denied_pip.content.decode() + caplog.text
    assert book.name not in denied.content.decode() + caplog.text


@pytest.mark.parametrize("channel", ["mcp_detail", "export"])
@pytest.mark.django_db
def test_consumption_receipt_with_retry_preserves_awards_and_timestamp(
    client: Client,
    cedar_dataset: CedarDataset,
    caplog: LogCaptureFixture,
    channel: ReceiptChannel,
) -> None:
    """Keep first attribution and original time through replay and conflict.

    :param client: Real Django HTTP client. Example: token-authenticated client.
    :param cedar_dataset: Genuine historical baseline. Example: Maria and Mike.
    :param caplog: Actual receipt logs. Example: parsed target and replay status.
    :param channel: Accepted token channel. Example: "mcp_detail".
    :return: None. Example: replay retains the original pair and timestamp.
    :raises AssertionError: Retry duplicates, mutates or misattributes awards.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    mike = cedar_dataset.users_by_username["mchen"]
    client.force_login(mike)
    authorization = _token_header(maria)
    payload = {**_receipt_payload(), "channel": channel}
    if channel == "export":
        payload.update(entity_type="workflow", entity_id=CEDAR_WORKFLOW_ID)
    with caplog.at_level(logging.INFO):
        first = _post_receipt(client, payload, authorization)
        awards = _receipt_awards(maria, channel, RECEIPT_UUID)
        replay = _post_receipt(client, payload, authorization)

    assert first.status_code == replay.status_code == 200
    assert len(awards) == 2
    assert {award.recipient_id for award in awards} == {maria.pk, mike.pk}
    assert all(award.event_channel == channel and award.points == 5 for award in awards)
    assert first.json() == {
        "status": "applied",
        "created_count": 2,
        "event_identity": str(RECEIPT_UUID),
        "occurred_at": awards[0].occurred_at.isoformat(),
    }
    assert replay.json() == {**first.json(), "status": "replayed", "created_count": 0}
    _assert_receipt_log(
        caplog,
        "validation",
        maria,
        f"channel={channel}",
        f"event_identity={RECEIPT_UUID}",
        f"entity_type={payload['entity_type']}",
        f"entity_id={payload['entity_id']}",
    )
    _assert_receipt_log(
        caplog,
        "exit",
        maria,
        "status=replayed",
        f"occurred_at={awards[0].occurred_at.isoformat()}",
    )
    _assert_receipt_conflict_and_new_action(
        client, payload, authorization, maria, awards
    )
    assert (_total_points(maria), _total_points(mike)) == (8210, 12460)


def _assert_receipt_conflict_and_new_action(
    client: Client,
    payload: dict[str, object],
    authorization: str,
    actor: User,
    awards: list[KarmaAward],
) -> None:
    """Check a nearby target cannot reuse an event, while an independent action can."""
    conflict = {**payload, "entity_type": "playbook", "entity_id": CEDAR_PLAYBOOK_ID}
    response = _post_receipt(client, conflict, authorization)
    assert response.status_code == 409
    assert response.json() == {"status": "rejected", "reason": "event_conflict"}
    assert list(
        KarmaAward.objects.filter(event_identity=awards[0].event_identity)
        .order_by("pk")
        .values_list("pk", "occurred_at")
    ) == [(award.pk, award.occurred_at) for award in awards]

    new = _post_receipt(
        client, {**payload, "event_identity": str(RECEIPT_RETRY_UUID)}, authorization
    )
    assert new.status_code == 200
    assert new.json()["status"] == "applied"
    assert len(_receipt_awards(actor, awards[0].event_channel, RECEIPT_RETRY_UUID)) == 2


@pytest.mark.parametrize(
    ("actor_username", "pip_key"),
    [
        ("mrodriguez", "HIST-MARIA-DESIGN-01"),
        ("mchen", "HIST-MARIA-DEV-01"),
    ],
)
@pytest.mark.django_db
def test_consumption_receipt_with_pip_self_excludes_creator_and_author(
    client: Client,
    cedar_dataset: CedarDataset,
    actor_username: str,
    pip_key: str,
) -> None:
    """Allow authorized creator/staff receipts while excluding both PIP self cases.

    :param client: Real Django HTTP client. Example: client.
    :param cedar_dataset: Genuine historical baseline. Example: Maria's Design PIP.
    :param actor_username: Authorized owner or staff. Example: "mchen".
    :param pip_key: Historical fixture key. Example: "HIST-MARIA-DEV-01".
    :return: None. Example: both self paths record zero live rows.
    :raises AssertionError: A PIP creator or target-playbook author receives a pair.
    """
    actor = cedar_dataset.users_by_username[actor_username]
    pip = cedar_dataset.pips_by_key[pip_key]
    before = KarmaAward.objects.count()
    payload = {**_receipt_payload(), "entity_type": "pip", "entity_id": pip.pk}

    response = _post_receipt(client, payload, _token_header(actor))

    assert response.status_code == 200
    assert response.json() == {
        "status": "skipped",
        "created_count": 0,
        "event_identity": str(RECEIPT_UUID),
        "reason": "self_consumption",
    }
    assert KarmaAward.objects.count() == before


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("entrypoint", ["facade", "legacy"])
async def test_mcp_detail_with_history_options_records_one_pair(
    entrypoint: MCPEntrypoint,
    mcp_client_factory: MCPClientFactory,
    mcp_dataset: MCPDataset,
) -> None:
    """Preserve playbook version/history semantics and failed-version behavior.

    :param mcp_client_factory: Actor-explicit real registered client factory.
    :param mcp_dataset: Genuine independently seeded Cedar fixture data.
    :param entrypoint: Registered transport path under test.
    :return: None. Example: successful historical fetch awards once.
    :raises AssertionError: Nested data duplicates awards or failure awards.
    """
    case = _eligible_mcp_case("get_playbook", mcp_dataset)
    before = await KarmaAward.objects.acount()
    async with mcp_client_factory.open(
        actor_username=case.actor_username, entrypoint=entrypoint
    ) as session:
        result = await session.client.call_tool(
            case.tool_name, {**case.arguments, "include_history": True}
        )
        versioned = decode_tool_payload(result)
        assert versioned["versions"]
        assert await KarmaAward.objects.acount() == before + 2

        snapshot_args = {
            **case.arguments,
            "include_history": True,
            "version": versioned["versions"][0]["version_number"],
        }
        snapshot = decode_tool_payload(
            await session.client.call_tool(case.tool_name, snapshot_args)
        )
        assert snapshot["version_number"] == snapshot_args["version"]
        assert "snapshot_data" in snapshot and "versions" not in snapshot
        assert await KarmaAward.objects.acount() == before + 4

        with pytest.raises(ToolError, match="not found"):
            await session.client.call_tool(
                case.tool_name, {**case.arguments, "version": "999.9"}
            )
        if entrypoint == "facade":
            assert session.request_paths.count(("POST", RECEIPT_PATH)) == 2
    assert await KarmaAward.objects.acount() == before + 4


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("entrypoint", ["facade", "legacy"])
async def test_mcp_detail_log_story_happy(
    entrypoint: MCPEntrypoint,
    mcp_client_factory: MCPClientFactory,
    mcp_dataset: MCPDataset,
    caplog: LogCaptureFixture,
) -> None:
    """Assert successful boundary/service beats using assert_log_story.

    :param mcp_client_factory: Actor-explicit real registered client factory.
    :param mcp_dataset: Genuine independently seeded Cedar fixture data.
    :param entrypoint: Registered transport path under test.
    :param caplog: Captured actual logs. Example: receipt validation records.
    :return: None. Example: declared happy beats present.
    :raises AssertionError: Required beat absent or sensitive data logged.
    """
    case = _eligible_mcp_case("get_pip", mcp_dataset)
    before = await KarmaAward.objects.acount()
    arguments = {**case.arguments, "event_identity": str(RECEIPT_UUID)}
    with capture_experts_logs(caplog, MCP_LOGGERS):
        async with mcp_client_factory.open(
            actor_username=case.actor_username, entrypoint=entrypoint
        ) as session:
            result = await session.client.call_tool(case.tool_name, arguments)
            timestamp = await sync_to_async(_assert_mcp_pair)(case, mcp_dataset, before)
            replay = await session.client.call_tool(case.tool_name, arguments)
            assert decode_tool_payload(result) == decode_tool_payload(replay)
    assert await sync_to_async(_assert_mcp_pair)(case, mcp_dataset, before) == timestamp
    _assert_mcp_success_logs(caplog, case, mcp_dataset, entrypoint, timestamp)
    actor = mcp_dataset.cedar.users_by_username[case.actor_username]
    token = await Token.objects.aget(user_id=actor.pk)
    assert token.key not in caplog.text
    assert case.expected["title"] not in caplog.text
    assert all(
        user.email not in caplog.text
        for user in mcp_dataset.cedar.users_by_username.values()
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("entrypoint", ["facade", "legacy"])
async def test_mcp_detail_log_story_reject(
    entrypoint: MCPEntrypoint,
    mcp_client_factory: MCPClientFactory,
    mcp_dataset: MCPDataset,
    caplog: LogCaptureFixture,
) -> None:
    """Assert denied/invalid paths without award-success or private log bodies.

    :param mcp_client_factory: Actor-explicit real registered client factory.
    :param mcp_dataset: Genuine independently seeded Cedar fixture data.
    :param entrypoint: Registered transport path under test.
    :param caplog: Captured actual logs. Example: denied receipt records.
    :return: None. Example: rejection beats and absence checks pass.
    :raises AssertionError: Missing rejection or leaked secret/private body.
    """
    denied = detail_case(
        "get_pip", mcp_dataset, actor_username="hkim", fixture_key="maria_design_pip"
    )
    before = await KarmaAward.objects.acount()
    secret_identity = "private-invalid-identity-sentinel"
    with capture_experts_logs(caplog, MCP_LOGGERS):
        async with mcp_client_factory.open(
            actor_username=denied.actor_username, entrypoint=entrypoint
        ) as session:
            with pytest.raises(ToolError):
                await session.client.call_tool(
                    denied.tool_name,
                    {**denied.arguments, "event_identity": secret_identity},
                )
            assert not session.request_paths
            with pytest.raises(ToolError) as rejected:
                await session.client.call_tool(
                    denied.tool_name,
                    {**denied.arguments, "event_identity": str(RECEIPT_UUID)},
                )
            assert denied.expected["title"] not in str(rejected.value)
            assert ("POST", RECEIPT_PATH) not in session.request_paths
    assert await KarmaAward.objects.acount() == before
    assert_log_story(
        caplog,
        where="consumption_event_identity",
        beats={
            "invalid": ("| branch |", "reason=invalid_event_identity"),
        },
    )
    assert_log_story(
        caplog,
        where="get_pip",
        beats={
            "denied": (
                "| branch |",
                f"entity_id={denied.arguments['pip_id']}",
                "reason=read_rejected",
            ),
        },
    )
    assert secret_identity not in caplog.text
    assert denied.expected["title"] not in caplog.text
    assert not any(
        "created_count=2" in record.getMessage() for record in caplog.records
    )
    actor = mcp_dataset.cedar.users_by_username[denied.actor_username]
    token = await Token.objects.aget(user_id=actor.pk)
    assert token.key not in caplog.text

    # A second authorized detail with an already-used UUID must reject its receipt.
    original = _eligible_mcp_case("get_workflow", mcp_dataset)
    conflicting = _eligible_mcp_case("get_skill", mcp_dataset)
    action = {"event_identity": str(RECEIPT_RETRY_UUID)}
    async with mcp_client_factory.open(
        actor_username=original.actor_username, entrypoint=entrypoint
    ) as session:
        await session.client.call_tool(
            original.tool_name, {**original.arguments, **action}
        )
        caplog.clear()
        with capture_experts_logs(caplog, MCP_LOGGERS), pytest.raises(ToolError):
            await session.client.call_tool(
                conflicting.tool_name, {**conflicting.arguments, **action}
            )
    where = (
        "_post_consumption_receipt"
        if entrypoint == "facade"
        else "_complete_legacy_mcp_detail"
    )
    assert_log_story(
        caplog,
        where=where,
        beats={
            "conflict": (
                "| branch |",
                "reason=receipt_rejected",
                f"event_identity={RECEIPT_RETRY_UUID}",
                "entity_type=skill",
            )
        },
    )
    if entrypoint == "facade":
        assert_log_story(
            caplog,
            where=RECEIPT_VIEW,
            beats={
                "conflict": (
                    "| branch |",
                    "reason=event_conflict",
                    f"event_identity={RECEIPT_RETRY_UUID}",
                    "awards=0",
                )
            },
        )
    assert await KarmaAward.objects.acount() == before + 2
    assert not any(
        "created_count=2" in record.getMessage() for record in caplog.records
    )


@contextmanager
def _configured_mcp_runtime(
    server_url: str, actor: User, token_key: str
) -> Iterator[None]:
    """Provide a borrowed real HTTP singleton and unrelated legacy user.

    :param server_url: Actual live server, with a distinct borrowed base path.
    :param actor: Persisted prior user for the caller's context.
    :param token_key: Actual DRF key against the borrowed HTTP client.
    :return: Scoped configuration that restores the original runtime on exit.
    """
    previous_facade = _capture_mcp_runtime().facade
    previous_user = _current_user.set(actor)
    try:
        facade_client.configure(server_url, token_key)
        with facade_client.get_client(), pytest.MonkeyPatch.context() as environment:
            environment.setenv(UNSAFE_ORM_FLAG, "s39-prior-test-value")
            yield
    finally:
        _current_user.reset(previous_user)
        facade_client._server_url = previous_facade.server_url
        facade_client._token = previous_facade.token
        facade_client._http_client = previous_facade.client


def _assert_mcp_runtime_restored(previous: MCPRuntimeState) -> None:
    """Require exact client/config identity, caller context and prior environment."""
    current = _capture_mcp_runtime()
    assert current.facade.client is previous.facade.client
    if current.facade != previous.facade:
        raise AssertionError("Facade connection settings were not restored.")
    assert current.legacy_user is previous.legacy_user
    assert current.unsafe_environment_value == previous.unsafe_environment_value
    if previous.facade.client is not None:
        assert not previous.facade.client.is_closed


async def _assert_factory_session_auth(
    factory: MCPClientFactory,
    case: MCPCase,
    entrypoint: MCPEntrypoint,
    previous: MCPRuntimeState,
) -> HTTPClient | None:
    """Prove actor binding while the actual session is still connected."""
    actor = factory.dataset.cedar.users_by_username[case.actor_username]
    if entrypoint == "legacy":
        assert get_current_user() is actor
        assert _capture_mcp_runtime().facade.client is previous.facade.client
        assert UNSAFE_ORM_FLAG not in os.environ
        return None
    assert _current_user.get() is previous.legacy_user
    assert facade_client.get_server_url() == factory.server_url
    owned_http = facade_client.get_client()
    assert owned_http is not previous.facade.client
    assert not owned_http.is_closed
    token = await Token.objects.aget(user_id=actor.pk)
    if owned_http.headers.get("Authorization") != f"Token {token.key}":
        raise AssertionError("Facade client used a token from a different actor.")
    return owned_http


async def _assert_factory_actor_case(
    factory: MCPClientFactory,
    actor_username: str,
    entrypoint: MCPEntrypoint,
    *,
    is_authorized: bool,
) -> None:
    """Exercise a successful or denied real call and require resource teardown."""
    case = detail_case(
        "get_pip",
        factory.dataset,
        actor_username=actor_username,
        fixture_key="maria_design_pip",
    )
    previous = _capture_mcp_runtime()
    connected_client = None
    owned_http = None
    expected_result = (
        nullcontext()
        if is_authorized
        else pytest.raises(ToolError, match="Not allowed to view this PIP")
    )
    with expected_result:
        async with factory.open(
            actor_username=actor_username, entrypoint=entrypoint
        ) as session:
            assert session.actor_username == actor_username
            connected_client = session.client
            assert connected_client.is_connected()
            owned_http = await _assert_factory_session_auth(
                factory, case, entrypoint, previous
            )
            result = await connected_client.call_tool(
                case.tool_name, dict(case.arguments)
            )
            _assert_mcp_content(case, decode_tool_payload(result), entrypoint)
    assert connected_client is not None and not connected_client.is_connected()
    if entrypoint == "facade":
        assert owned_http is not None and owned_http.is_closed
    _assert_mcp_runtime_restored(previous)


@contextmanager
def _legacy_orm_guard_enabled() -> Iterator[None]:
    """Clear the unsafe override after actual legacy registration import."""
    previous = os.environ.get(UNSAFE_ORM_FLAG)
    try:
        import_module("mcp_integration.tools")
        os.environ.pop(UNSAFE_ORM_FLAG, None)
        yield
    finally:
        if previous is None:
            os.environ.pop(UNSAFE_ORM_FLAG, None)
        else:
            os.environ[UNSAFE_ORM_FLAG] = previous


async def _assert_legacy_collections(
    client: RegisteredMCPClient, dataset: MCPDataset
) -> None:
    """Read real rows for all nine collections with original lightweight schemas."""
    book = {"playbook_id": dataset.entity_ids["mike_playbook"]}
    workflow = {"workflow_id": dataset.entity_ids["mike_workflow"]}
    arguments = (
        ("list_playbooks", {}, "mike_playbook", "name", "workflows"),
        ("list_workflows", book, "mike_workflow", "name", "activities"),
        ("list_activities", workflow, "mike_activity", "name", "guidance"),
        ("list_phases", book, "mike_phase", "name", "activities"),
        ("list_skills", book, "mike_skill", "title", "content"),
        ("list_rules", book, "mike_rule", "title", "content"),
        ("list_agents", book, "mike_agent", "name", "system_prompt"),
        ("list_artifacts", book, "mike_artifact", "name", "content"),
        ("list_pips", {"scope": "mine"}, "maria_design_pip", "title", "changes"),
    )
    for tool, params, fixture_key, display_field, omitted_field in arguments:
        result = decode_tool_payload(await client.call_tool(tool, params))
        assert isinstance(result, dict) and isinstance(result["result"], list), tool
        row = next(
            row
            for row in result["result"]
            if row["id"] == dataset.entity_ids[fixture_key]
        )
        assert (
            row[display_field] == dataset.expected_content[fixture_key][display_field]
        ), tool
        assert omitted_field not in row, tool
        if tool == "list_pips":
            assert row["submitted_by_username"] == "mrodriguez"
            assert row["changes_count"] == 2


@pytest.mark.django_db(transaction=True)
async def test_mcp_client_factory_with_different_actors_restores_context_and_auth(
    mcp_client_factory: MCPClientFactory, mcp_dataset: MCPDataset
) -> None:
    """Prove actor selection and teardown using actual registered calls.

    :param mcp_client_factory: Explicit actor/entrypoint factory. Example: Mike then Hana.
    :param mcp_dataset: Real actor/target fixtures. Example: Cedar historical Design PIP.
    :return: None. Example: no token/context/client crossover.
    :raises AssertionError: Wrong actor, leaked singleton/context or unclosed owned client.
    """
    users = mcp_dataset.cedar.users_by_username
    prior_actor = users["mrodriguez"]
    token, _ = await Token.objects.aget_or_create(user=prior_actor)
    original_context = _current_user.set(None)
    clean = _capture_mcp_runtime()
    try:
        with _configured_mcp_runtime(
            f"{mcp_client_factory.server_url}/api", prior_actor, token.key
        ):
            for entrypoint in ("facade", "legacy"):
                await _assert_factory_actor_case(
                    mcp_client_factory, "mchen", entrypoint, is_authorized=True
                )
                await _assert_factory_actor_case(
                    mcp_client_factory, "hkim", entrypoint, is_authorized=False
                )
        with pytest.raises(ValueError, match="does not exist"):
            async with mcp_client_factory.open(
                actor_username="unknown-cedar-actor", entrypoint="facade"
            ):
                pytest.fail("A missing actor entered a real MCP session.")
        await _assert_factory_actor_case(
            mcp_client_factory, "mrodriguez", "legacy", is_authorized=True
        )
        _assert_mcp_runtime_restored(clean)
        with pytest.raises(ValueError, match="No user context"):
            get_current_user()
    finally:
        _current_user.reset(original_context)


@pytest.mark.django_db(transaction=True)
async def test_legacy_detail_and_collections_with_async_guard_use_safe_orm(
    mcp_client_factory: MCPClientFactory, mcp_dataset: MCPDataset
) -> None:
    """Exercise touched detail/list matrices with the imported unsafe flag cleared.

    :param mcp_client_factory: Real legacy registration factory. Example: Maria/Mike sessions.
    :param mcp_dataset: Actual phase/PIP/resource fixtures. Example: lazy artifact relations.
    :return: None. Example: all real calls succeed without async ORM bypass.
    :raises AssertionError: Unsafe flag survives or any touched serialization fails.
    """
    case = _eligible_mcp_case("get_phase", mcp_dataset)
    all_awards = KarmaAward.objects.order_by("pk").values()
    environment = os.environ.get(UNSAFE_ORM_FLAG)
    with _legacy_orm_guard_enabled():
        with pytest.raises(SynchronousOnlyOperation):
            all_awards.count()
        async with mcp_client_factory.open(
            actor_username=case.actor_username, entrypoint="legacy"
        ) as session:
            assert UNSAFE_ORM_FLAG not in os.environ
            before = [row async for row in all_awards]
            await _assert_legacy_collections(session.client, mcp_dataset)
            assert [row async for row in all_awards.all()] == before
            result = await session.client.call_tool(
                case.tool_name, {**case.arguments, "event_identity": str(RECEIPT_UUID)}
            )
            assert UNSAFE_ORM_FLAG not in os.environ
            assert not session.request_paths
        assert UNSAFE_ORM_FLAG not in os.environ
    assert os.environ.get(UNSAFE_ORM_FLAG) == environment
    _assert_mcp_content(case, decode_tool_payload(result), "legacy")
    await sync_to_async(_assert_mcp_pair)(case, mcp_dataset, len(before))


@pytest.mark.django_db
def test_set_current_user_with_account_metadata_logs_only_safe_context(
    mcp_dataset: MCPDataset, caplog: LogCaptureFixture
) -> None:
    """Call actual set/get/clear and assert safe INFO logs and unchanged context semantics.

    :param mcp_dataset: Actual persisted actor. Example: unique email/name sentinels.
    :param caplog: Captured actual context logs. Example: user ID and flags.
    :return: None. Example: no email/username/full-name metadata appears.
    :raises AssertionError: Personal metadata leaks or ContextVar behavior changes.
    """
    actor = mcp_dataset.cedar.users_by_username["mrodriguez"]
    prior = _current_user.set(None)
    try:
        with capture_experts_logs(caplog, ("mcp_integration.context",)):
            set_current_user(actor)
            assert get_current_user() is actor
            clear_current_user()
        with pytest.raises(ValueError, match="No user context"):
            get_current_user()
    finally:
        _current_user.reset(prior)
    assert_log_story(
        caplog,
        where="MCP context",
        beats={
            "context": (f"user_id={actor.pk}", "is_active=True", "is_staff=False"),
        },
    )
    assert actor.email not in caplog.text
    assert actor.username not in caplog.text
    assert actor.get_full_name() not in caplog.text


@pytest.mark.django_db
def test_phase_detail_with_actor_email_logs_only_identifiers(
    mcp_dataset: MCPDataset, caplog: LogCaptureFixture
) -> None:
    """Call actual phase service and assert bounded identifier-only read logs.

    :param mcp_dataset: Real actor and phase. Example: Maria reading Mike phase.
    :param caplog: Actual phase-service logs. Example: phase_id/actor_id.
    :return: None. Example: actual phase returned without actor email logging.
    :raises AssertionError: Sensitive account metadata appears or read behavior changes.
    """
    actor = mcp_dataset.cedar.users_by_username["mrodriguez"]
    phase_id = mcp_dataset.entity_ids["mike_phase"]
    with capture_experts_logs(caplog, ("methodology.services.phase_service",)):
        result = PhaseService.get_phase_with_activities(phase_id, actor)
    assert result["phase"].pk == phase_id
    assert_log_story(
        caplog,
        where="phase",
        beats={
            "entry": (f"phase_id={phase_id}", f"actor_id={actor.pk}"),
        },
    )
    assert actor.email not in caplog.text
    assert actor.username not in caplog.text
