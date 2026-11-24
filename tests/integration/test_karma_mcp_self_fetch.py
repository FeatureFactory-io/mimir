from __future__ import annotations

"""Ten-row real MCP/HTTP/database self-fetch proofs."""
import json
import re
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
from pytest import LogCaptureFixture
from pytest_django.live_server_helper import LiveServer
from rest_framework.authtoken.models import Token

from methodology.services.karma_service import KarmaService
from tests.support.experts_acceptance import run_exact_acceptance
from tests.support.experts_data import load_cedar_baseline
from tests.support.experts_logs import capture_experts_logs
from tests.support.experts_mcp_self import (
    KarmaSnapshot,
    SelfFetchCase,
    assert_self_fetch_content,
    assert_self_fetch_unchanged,
    resolve_self_fetch_case,
    snapshot_karma_state,
)
from tests.support.karma_mcp import (
    MCPCase,
    MCPClientFactory,
    MCPDataset,
    MCPEntrypoint,
    MCPInvariantSnapshot,
    StdioMCPClient,
    _capture_mcp_runtime,
    decode_tool_payload,
    karma_snapshot,
)
from tests.support.log_story import assert_log_story

ACTION_ID = UUID("ed59b358-59c8-4664-bd47-d1ff63f52040")
PRIVATE_SENTINEL = "private-forged-self-fetch-payload"
SERVICE_LOG = "KarmaService.award_successful_consumption"
type ProtocolState = tuple[
    KarmaSnapshot, MCPInvariantSnapshot, tuple[tuple[int, bool, bool, bool], ...]
]

LOGGERS = ("methodology.services.karma_service", "methodology.api.consumption_views")
SELF_ROWS = (
    ("Mike", "Mike's Playbook"),
    ("Mike", "Mike's Workflow"),
    ("Mike", "Mike's Phase"),
    ("Mike", "Mike's Activity"),
    ("Mike", "Mike's Skill"),
    ("Mike", "Mike's Rule"),
    ("Mike", "Mike's Agent"),
    ("Mike", "Mike's Artifact"),
    ("Mike", "Maria's historical PIP targeting Mike's playbook"),
    ("Maria", "Maria's historical PIP targeting Hana's playbook"),
)

HAPPY_BEATS = {
    "entry": (
        "| entry |",
        "actor_id={actor_id}",
        "action_uuid={identity}",
        "channel=mcp_detail",
        "entity_type={entity_type}",
        "entity_id={entity_id}",
    ),
    "validation": (
        "| validation |",
        "actor_id={actor_id}",
        "playbook_id={book_id}",
        "authorized",
    ),
    "branch": (
        "| branch |",
        "actor_id={actor_id}",
        "author_id={author_id}",
        "pip_creator_id={creator_id}",
        "exclusion_role={role}",
        "reason=self_consumption",
    ),
    "exit": (
        "| exit |",
        "actor_id={actor_id}",
        "action_uuid={identity}",
        "exclusion_role={role}",
        "created_count=0",
    ),
}


@pytest.mark.parametrize("case_index", range(10))
@pytest.mark.django_db(transaction=True)
async def test_self_fetch_with_registered_facade_returns_content_without_awards(
    case_index: int, live_server: LiveServer
) -> None:
    """Prove registered facade T1 with live HTTP and real DB.

    :param case_index: Literal outline position. Example: 9 for Maria's PIP.
    :param live_server: Actual Django backend. Example: localhost random port.
    :return: None. Example: authorized content, unchanged complete ledger.
    :raises AssertionError: Registration, content or award invariant fails.
    """
    await _run_registered_self_fetch(case_index, "facade", live_server.url)


@pytest.mark.parametrize("case_index", range(10))
@pytest.mark.django_db
def test_self_fetch_with_shared_service_returns_no_awards(case_index: int) -> None:
    """Prove T2 using S36's real shared consumption service.

    :param case_index: Exact outline position. Example: 8 for Mike's PIP.
    :return: None. Example: empty outcomes and unchanged author total.
    :raises AssertionError: Eligibility, permission or ledger differs.
    """
    case = _self_case(case_index)
    before = snapshot_karma_state()
    outcomes = KarmaService.award_successful_consumption(
        case.actor, case.entity_type, case.entity_id, ACTION_ID, channel="mcp_detail"
    )
    assert outcomes == ()
    assert_self_fetch_unchanged(before, case)


@pytest.mark.parametrize("case_index", range(10))
@pytest.mark.django_db(transaction=True)
async def test_self_fetch_with_registered_legacy_returns_content_without_awards(
    case_index: int,
) -> None:
    """Call real initialize_mcp registration through FastMCP Client.

    :param case_index: Exact outline position. Example: 0 for get_playbook.
    :return: None. Example: content returned, server context cleared.
    :raises AssertionError: Registration, actual wrapper or awards differ.
    """
    await _run_registered_self_fetch(case_index, "legacy", "")


@pytest.mark.parametrize("case_index", range(10))
@pytest.mark.django_db(transaction=True)
def test_self_fetch_with_facade_stdio_returns_clean_protocol_without_awards(
    case_index: int, live_server: LiveServer
) -> None:
    """Prove T3 with actual facade subprocess and live backend.

    :param case_index: Exact outline position. Example: 7 for get_artifact.
    :param live_server: Real isolated HTTP backend. Example: localhost.
    :return: None. Example: JSON-RPC success with zero ledger changes.
    :raises AssertionError: Protocol noise, content error or award appears.
    """
    case, dataset = _protocol_setup(case_index)
    before = _protocol_state()
    with (
        TemporaryDirectory(prefix="mimir-self-fetch-") as directory,
        StdioMCPClient(
            entrypoint="facade",
            actor_username=case.actor.username,
            dataset=dataset,
            server_url=live_server.url,
            root=Path(directory),
            include_summaries=True,
        ) as wire,
    ):
        schemas = {tool["name"]: tool["inputSchema"] for tool in wire.list_tools()}
        _assert_self_schema(schemas[case.tool_name], case)
        assert wire.snapshot() == before[1]
        _assert_protocol_state(before, case)
        payload = wire.call(_self_invocation(case))
        assert wire.snapshot() == before[1]
    wire.assert_protocol_clean()
    _assert_stdio_self_fetch(wire, case, live_server.url)
    assert_self_fetch_content(payload, case)
    _assert_protocol_state(before, case)


@pytest.mark.parametrize("case_index", range(10))
@pytest.mark.django_db
def test_self_fetch_with_bare_rest_get_does_not_award(case_index: int) -> None:
    """Keep ordinary authorized REST GETs award-free.

    :param case_index: Exact outline position. Example: 3 for activity.
    :return: None. Example: HTTP 200 and identical ledger.
    :raises AssertionError: GET fails or creates any award.
    """
    case = _self_case(case_index)
    before = snapshot_karma_state()
    payload = _detail_payload(case)
    assert_self_fetch_content(payload, case)
    assert_self_fetch_unchanged(before, case)


@pytest.mark.django_db
def test_self_fetch_with_forged_actor_receipt_rejects_without_awards() -> None:
    """Reject caller-supplied actor and award fields.

    :return: None. Example: HTTP 400 and unchanged ledger.
    :raises AssertionError: Receipt changes actor or persists awards.
    """
    case = _self_case(0)
    before = snapshot_karma_state()
    other_id = User.objects.get(username="mrodriguez").pk
    overrides = {
        "actor": other_id,
        "actor_id": other_id,
        "recipient": other_id,
        "recipient_id": other_id,
        "category": "development",
        "points": 5,
    }
    for field, value in overrides.items():
        response = _post_receipt(case, {**_receipt_payload(case), field: value})
        assert response.status_code == 400
        assert response.json()["reason"] == "invalid_payload"
        assert PRIVATE_SENTINEL not in response.content.decode()
        assert_self_fetch_unchanged(before, case)


@pytest.mark.django_db
def test_self_fetch_with_target_author_without_pip_permission_rejects() -> None:
    """Preserve creator-or-staff PIP permission for nonstaff target author.

    :return: None. Example: Hana cannot read Maria's historical PIP.
    :raises AssertionError: Authorship broadens access or awards occur.
    """
    dataset = load_cedar_baseline()
    creator_case = resolve_self_fetch_case(dataset, *SELF_ROWS[9])
    hana = dataset.users_by_username["hkim"]
    case = replace(creator_case, actor=hana, expected_total=5800)
    assert case.target_author_id == hana.pk != case.creator_id and not hana.is_staff
    before = snapshot_karma_state()
    client, _ = _token_client(hana)
    response = client.get(reverse("api-pip-detail", args=[case.entity_id]))
    assert response.status_code == 403
    assert "HIST-MARIA-DESIGN-01" not in response.content.decode()
    with pytest.raises(PermissionError):
        KarmaService.award_successful_consumption(
            hana, "pip", case.entity_id, ACTION_ID, channel="mcp_detail"
        )
    receipt = _post_receipt(case, _receipt_payload(case))
    assert (
        receipt.status_code == 404 and receipt.json()["reason"] == "target_unavailable"
    )
    assert_self_fetch_unchanged(before, case)


@pytest.mark.parametrize("case_index", range(10))
@pytest.mark.django_db
def test_self_fetch_log_story_happy(case_index: int, caplog: LogCaptureFixture) -> None:
    """Assert authorized exclusion beats through the real shared service.

    :param case_index: Exact outline position. Example: 9 creator exclusion.
    :param caplog: Real log capture. Example: service INFO records.
    :return: None. Example: self reason and created_count=0 proven.
    :raises AssertionError: Required beats absent or sensitive data logged.
    """
    case = _self_case(case_index)
    before = snapshot_karma_state()
    with capture_experts_logs(caplog, LOGGERS):
        assert (
            KarmaService.award_successful_consumption(
                case.actor,
                case.entity_type,
                case.entity_id,
                ACTION_ID,
                channel="mcp_detail",
            )
            == ()
        )
    values = {
        "actor_id": case.actor.pk,
        "identity": ACTION_ID,
        "role": case.exclusion_reason,
        "entity_type": case.entity_type,
        "entity_id": case.entity_id,
        "author_id": case.target_author_id,
        "creator_id": case.creator_id,
        "book_id": 6106 if case.exclusion_reason == "self_creator" else 6201,
    }
    beats = {
        beat: tuple(item.format(**values) for item in items)
        for beat, items in HAPPY_BEATS.items()
    }
    assert_log_story(caplog, where=SERVICE_LOG, beats=beats)
    _assert_safe_logs(caplog, case)
    assert_self_fetch_unchanged(before, case)


@pytest.mark.django_db
def test_self_fetch_log_story_reject(caplog: LogCaptureFixture) -> None:
    """Assert denied PIP/invalid receipt emits no award-success story.

    :param caplog: Real boundary/service logs. Example: safe denial.
    :return: None. Example: rejection and zero awards established.
    :raises AssertionError: Missing rejection, success beat or disclosure.
    """
    creator_case = _self_case(9)
    hana = User.objects.get(username="hkim")
    case = replace(creator_case, actor=hana, expected_total=5800)
    before = snapshot_karma_state()
    with capture_experts_logs(caplog, LOGGERS):
        denied = _post_receipt(case, _receipt_payload(case))
        forged = _post_receipt(
            case, {**_receipt_payload(case), "actor_id": PRIVATE_SENTINEL}
        )
    assert (denied.status_code, forged.status_code) == (404, 400)
    assert_log_story(
        caplog,
        where="ConsumptionReceiptView.post",
        beats={
            "denied": (
                "| branch |",
                f"actor_id={hana.pk}",
                "reason=target_unavailable",
                "awards=0",
            ),
            "forged": (
                "| branch |",
                f"actor_id={hana.pk}",
                "reason=invalid_payload",
                "awards=0",
            ),
        },
    )
    _assert_safe_logs(caplog, case)
    assert_self_fetch_unchanged(before, case)


def test_self_fetch_acceptance_with_exact_outline_executes_ten_rows(
    tmp_path: Path,
) -> None:
    """Execute scoped Behave through acceptance settings and inspect JSON.

    :param tmp_path: Isolated report location. Example: temporary results.json.
    :return: None. Example: exactly ten passed, none skipped/undefined.
    :raises AssertionError: Nonzero exit, wrong selection or incomplete rows.
    """
    result = run_exact_acceptance(
        Path("docs/features/act-18-experts/karma-accrual.feature"), "KARMA-MCP-03", 10
    )
    (tmp_path / "self-fetch-results.json").write_text(json.dumps(result.output))
    assert (
        result.scenario_count,
        result.step_count,
        result.skipped_count,
        result.undefined_count,
    ) == (10, 40, 0, 0)


def _self_case(case_index: int) -> SelfFetchCase:
    """Restore a separate baseline for one exact outline row.

    :param case_index: Literal row position. Example: 9 for creator-only PIP.
    :return: Authorized real fixture case. Example: Maria's PIP.
    :raises ValueError: Row index falls outside the ten-case contract.
    """
    if type(case_index) is not int or not 0 <= case_index < len(SELF_ROWS):
        raise ValueError("An exact self-fetch row index is required.")
    return resolve_self_fetch_case(load_cedar_baseline(), *SELF_ROWS[case_index])


def _token_client(actor: User) -> tuple[Client, str]:
    """Configure actual token authentication without session substitution.

    :param actor: Persisted fixture account. Example: Mike.
    :return: Real Django HTTP client and token. Example: DRF Authorization.
    :raises AssertionError: Actor is not an active persisted account.
    """
    assert actor.pk and actor.is_active
    token, _ = Token.objects.get_or_create(user=actor)
    return Client(HTTP_AUTHORIZATION=f"Token {token.key}"), token.key


def _detail_payload(case: SelfFetchCase) -> dict[str, object]:
    """Retrieve successful actual content through the existing detail endpoint.

    :param case: Authorized real target. Example: Mike's Skill.
    :return: Decoded native detail object. Example: full skill content.
    :raises AssertionError: HTTP fails or payload is not a content object.
    """
    client, _ = _token_client(case.actor)
    response = client.get(
        reverse(f"api-{case.entity_type}-detail", args=[case.entity_id])
    )
    assert response.status_code == 200, response.content.decode()
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


def _receipt_payload(case: SelfFetchCase) -> dict[str, object]:
    """Declare the four permitted fields independently of production parsing.

    :param case: Actual target. Example: activity 6203.
    :return: Canonical real receipt payload. Example: mcp_detail event.
    :raises AssertionError: The case has no positive real target ID.
    """
    assert case.entity_id > 0
    return {
        "entity_type": case.entity_type,
        "entity_id": case.entity_id,
        "event_identity": str(ACTION_ID),
        "channel": "mcp_detail",
    }


def _post_receipt(case: SelfFetchCase, payload: dict[str, object]) -> HttpResponse:
    """Post real token-authenticated JSON through the receipt view.

    :param case: Server-authenticated actor fixture. Example: Mike.
    :param payload: Independent receipt or forged fields. Example: actor_id sentinel.
    :return: Actual HTTP response. Example: rejected HTTP400.
    :raises TypeError: Payload cannot be JSON encoded.
    """
    client, _ = _token_client(case.actor)
    return client.post(
        reverse("api_consumption_receipt"),
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_REQUEST_ID="s40-self-fetch",
    )


def _assert_safe_logs(caplog: LogCaptureFixture, case: SelfFetchCase) -> None:
    """Reject award-success stories and disclosure in actual captured records.

    :param caplog: Actual service/boundary log capture.
    :param case: Current actor/content fixture. Example: historical PIP title.
    :return: None when logs contain no secret or award-success.
    :raises AssertionError: A private value or award-success beat appears.
    """
    token = Token.objects.filter(user=case.actor).first()
    forbidden = [
        PRIVATE_SENTINEL,
        case.actor.email,
        "created_count=2",
        "status=staged",
        "KarmaService.persist_awards",
    ]
    if token is not None:
        forbidden.append(token.key)
    forbidden.extend(User.objects.exclude(email="").values_list("email", flat=True))
    assert all(value not in caplog.text for value in forbidden if value)
    messages = [r.getMessage() for r in caplog.records if SERVICE_LOG in r.getMessage()]
    if any("exclusion_role=" in message for message in messages):
        assert [message.split(" | ")[1] for message in messages] == [
            "entry",
            "validation",
            "branch",
            "exit",
        ]
    for field in ("title", "name", "content", "guidance", "summary"):
        value = case.expected_content.get(field)
        if isinstance(value, str) and value:
            assert value not in caplog.text


def _protocol_setup(case_index: int) -> tuple[SelfFetchCase, MCPDataset]:
    """Resolve actual fixtures once and adapt them to the existing real clients.

    :param case_index: Literal row position. Example: 8 for target-author PIP.
    :return: Actual case and dataset references. Example: Mike plus real PIP ID.
    :raises ValueError: The row is outside the exact ten-case outline.
    """
    if type(case_index) is not int or not 0 <= case_index < len(SELF_ROWS):
        raise ValueError("An exact self-fetch row index is required.")
    dataset = load_cedar_baseline()
    case = resolve_self_fetch_case(dataset, *SELF_ROWS[case_index])
    key = f"self_{case.entity_type}"
    return case, MCPDataset(
        dataset, {key: case.entity_id}, {key: case.expected_content}
    )


def _self_invocation(case: SelfFetchCase) -> MCPCase:
    """Pass only the actual entity ID and stable optional operation identity.

    :param case: Real authorized outline target. Example: Maria's historical PIP.
    :return: Existing client's request object. Example: get_pip with actual PK.
    :raises AssertionError: The target has no positive persisted identity.
    """
    assert case.entity_id > 0
    return MCPCase(
        case.tool_name,
        case.actor.username,
        case.tool_name,
        f"self_{case.entity_type}",
        {f"{case.entity_type}_id": case.entity_id, "event_identity": str(ACTION_ID)},
        reverse(f"api-{case.entity_type}-detail", args=[case.entity_id]),
        case.expected_content,
    )


def _assert_self_schema(schema: Mapping[str, object], case: SelfFetchCase) -> None:
    """Require the shipped detail schema and no caller-supplied award fields.

    :param schema: Actual tools/list input schema. Example: get_activity schema.
    :param case: Requested real entity. Example: Mike's Activity.
    :return: None. Example: only entity, optional event identity and playbook flags.
    :raises AssertionError: Registry/schema is missing or exposes award overrides.
    """
    entity_parameter = f"{case.entity_type}_id"
    optional = (
        {"include_history", "version"} if case.entity_type == "playbook" else set()
    )
    assert schema["type"] == "object"
    assert set(schema["properties"]) == {entity_parameter, "event_identity"} | optional
    assert schema["properties"][entity_parameter]["type"] == "integer"
    assert schema.get("required", []) == [entity_parameter]
    assert schema["properties"]["event_identity"]["default"] is None


def _protocol_state() -> ProtocolState:
    """Capture every award/projection/profile/interaction and existing actor roles.

    :return: Immutable real snapshots. Example: all 2129 historical ledger rows.
    :raises AssertionError: The real seeded ledger or projection is inconsistent.
    """
    roles = tuple(
        User.objects.order_by("pk").values_list(
            "pk", "is_active", "is_staff", "is_superuser"
        )
    )
    return snapshot_karma_state(), karma_snapshot(include_summaries=True), roles


def _assert_protocol_state(before: ProtocolState, case: SelfFetchCase) -> None:
    """Reject any persisted award, public/private profile, interaction or role drift.

    :param before: Complete pre-operation copies. Example: real baseline state.
    :param case: Expected actor total. Example: Maria remains 8200.
    :return: None. Example: exact full-row and timestamp equality.
    :raises AssertionError: Any tracked state or total differs.
    """
    assert_self_fetch_unchanged(before[0], case)
    assert before == _protocol_state(), "Self-fetch changed full state or actor roles."


async def _run_registered_self_fetch(
    case_index: int, entrypoint: MCPEntrypoint, server_url: str
) -> None:
    """Exercise actual registered clients with strict async ORM and runtime cleanup.

    :param case_index: Literal outline row. Example: 9 for creator-only PIP.
    :param entrypoint: Actual registration. Example: legacy or facade.
    :param server_url: Actual facade listener or empty for legacy. Example: localhost.
    :return: None. Example: actual authorized content and zero side effects.
    :raises AssertionError: Protocol/content/state/runtime invariants differ.
    """
    case, dataset = await sync_to_async(_protocol_setup)(case_index)
    case = _native_self_case(case, dataset, entrypoint)
    before = await sync_to_async(_protocol_state)()
    runtime = _capture_mcp_runtime()
    paths: list[tuple[str, str]] = []
    factory = MCPClientFactory(dataset, server_url, paths)
    async with factory.open(
        actor_username=case.actor.username, entrypoint=entrypoint
    ) as session:
        schemas = {
            tool.name: tool.inputSchema for tool in await session.client.list_tools()
        }
        _assert_self_schema(schemas[case.tool_name], case)
        await sync_to_async(_assert_protocol_state)(before, case)
        result = await session.client.call_tool(
            case.tool_name, dict(_self_invocation(case).arguments)
        )
        assert paths == (
            [
                ("GET", _self_invocation(case).route),
                ("POST", "/api/consumption-receipts/"),
            ]
            if entrypoint == "facade"
            else []
        )
    assert _capture_mcp_runtime() == runtime
    assert_self_fetch_content(decode_tool_payload(result), case)
    await sync_to_async(_assert_after_self_fetch)(before, case, entrypoint)


def _assert_stdio_self_fetch(
    wire: StdioMCPClient, case: SelfFetchCase, server_url: str
) -> None:
    """Require genuine JSON-RPC responses and exactly the actual GET plus receipt.

    :param wire: Closed real facade child. Example: successful initialized session.
    :param case: Actual target/actor. Example: Mike reading his own Phase.
    :param server_url: Real isolated Django listener. Example: localhost random port.
    :return: None. Example: three matching responses and no award/provider success.
    :raises AssertionError: Protocol/HTTP boundaries or no-award state differ.
    """
    assert [row["id"] for row in wire.stdout_messages if "id" in row] == [1, 2, 3]
    requests = re.findall(r"HTTP Request: (.+)", wire.stderr)
    route = _self_invocation(case).route
    assert requests == [
        f'GET {server_url}{route} "HTTP/1.1 200 OK"',
        f'POST {server_url}/api/consumption-receipts/ "HTTP/1.1 200 OK"',
    ]
    assert all(
        value not in wire.stderr
        for value in (
            "KarmaService.persist_awards",
            "created_count=2",
            "PublicContributionSummaryBoundary.complete",
            "ContributionSummaryService.refresh",
        )
    )


def _native_self_case(
    case: SelfFetchCase, dataset: MCPDataset, entrypoint: MCPEntrypoint
) -> SelfFetchCase:
    """Account for the existing legacy playbook shape without inventing fields.

    :param case: Independent actual fixture expectation. Example: Mike's playbook.
    :param dataset: Already prepared real fixture references. Example: workflow6202.
    :param entrypoint: Actual registration. Example: legacy.
    :return: Native contract expectation. Example: workflow metadata, no author_id.
    :raises KeyError: Required independent workflow fixture is missing.
    """
    if entrypoint != "legacy" or case.entity_type != "playbook":
        return case
    expected = dict(case.expected_content)
    del expected["author_id"]
    expected["workflows"] = [
        {
            "id": dataset.cedar.workflows_by_pk[6202].pk,
            "name": "React Frontend Development",
            "description": "",
            "order": 1,
        }
    ]
    return replace(case, expected_content=expected)


def _assert_after_self_fetch(
    before: ProtocolState, case: SelfFetchCase, entrypoint: MCPEntrypoint
) -> None:
    """Preserve awards/profiles and certify the legacy activity's normal access touch.

    :param before: Complete real pre-call state. Example: 2129 awards.
    :param case: Actual returned target. Example: activity6203.
    :param entrypoint: Existing surface. Example: legacy.
    :return: None. Example: only the legitimate Recently Used timestamp advances.
    :raises AssertionError: Any unrelated state or award changes.
    """
    if entrypoint != "legacy" or case.entity_type != "activity":
        _assert_protocol_state(before, case)
        return
    assert_self_fetch_unchanged(before[0], case)
    after = _protocol_state()
    old_access = dict(json.loads(before[1].activity_access_json))
    new_access = dict(json.loads(after[1].activity_access_json))
    old_time = old_access.pop(case.entity_id)
    new_time = new_access.pop(case.entity_id)
    assert old_access == new_access
    assert new_time is not None and (old_time is None or new_time > old_time)
    expected = replace(after[1], activity_access_json=before[1].activity_access_json)
    assert (after[0], expected, after[2]) == before
