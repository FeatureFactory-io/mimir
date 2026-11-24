"""Real MCP/HTTP/DB proofs for the nine eligible detail tools."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from django.contrib.auth.models import User
from django.db.models import Model, Sum
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
from pytest import LogCaptureFixture
from pytest_django.live_server_helper import LiveServer
from rest_framework.authtoken.models import Token

from methodology.api.consumption_views import ReceiptChannel
from methodology.models import Agent, Artifact, KarmaAward, Phase, Playbook, Rule, Skill
from methodology.services.karma_service import KarmaService
from tests.support.experts_data import CedarDataset
from tests.support.log_story import assert_log_story

if TYPE_CHECKING:
    from tests.support.karma_mcp import MCPClientFactory, MCPDataset

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


@pytest.mark.parametrize("tool_name", DETAIL_TOOLS)
@pytest.mark.django_db(transaction=True)
async def test_mcp_detail_with_authorized_fixture_returns_content_and_pair(
    tool_name: str, live_server: LiveServer
) -> None:
    """Prove T1 against real registered facade, token, HTTP and DB.

    :param tool_name: Independent Cedar case. Example: "get_pip".
    :param live_server: Real Django HTTP server. Example: local random port.
    :return: None. Example: all content/award assertions pass.
    :raises AssertionError: Content, schema, recipient or totals differ.
    """
    raise NotImplementedError()


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
    tool_name: str,
) -> None:
    """Exercise the existing legacy FastMCP registration and real service.

    :param tool_name: Registered detail tool. Example: "get_activity".
    :return: None. Example: original content and exact paired awards.
    :raises AssertionError: Legacy registration bypasses the shared path.
    """
    raise NotImplementedError()


@pytest.mark.parametrize("tool_name", DETAIL_TOOLS)
@pytest.mark.django_db(transaction=True)
def test_mcp_detail_with_stdio_transport_returns_clean_jsonrpc(
    tool_name: str, live_server: LiveServer
) -> None:
    """Prove T3 with real facade subprocess and isolated HTTP backend.

    :param tool_name: Registered detail tool. Example: "get_rule".
    :param live_server: Real Django HTTP backend. Example: local random port.
    :return: None. Example: protocol-only stdout and exact persisted pair.
    :raises AssertionError: Protocol noise, missing content or wrong awards.
    """
    raise NotImplementedError()


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
async def test_mcp_detail_with_history_options_records_one_pair(
    live_server: LiveServer,
) -> None:
    """Preserve playbook version/history semantics and failed-version behavior.

    :param live_server: Real Django HTTP backend. Example: local random port.
    :return: None. Example: successful historical fetch awards once.
    :raises AssertionError: Nested data duplicates awards or failure awards.
    """
    raise NotImplementedError()


@pytest.mark.django_db(transaction=True)
async def test_mcp_detail_log_story_happy(
    live_server: LiveServer, caplog: LogCaptureFixture
) -> None:
    """Assert successful boundary/service beats using assert_log_story.

    :param live_server: Real HTTP backend. Example: local random port.
    :param caplog: Captured actual logs. Example: receipt validation records.
    :return: None. Example: declared happy beats present.
    :raises AssertionError: Required beat absent or sensitive data logged.
    """
    raise NotImplementedError()


@pytest.mark.django_db(transaction=True)
async def test_mcp_detail_log_story_reject(
    live_server: LiveServer, caplog: LogCaptureFixture
) -> None:
    """Assert denied/invalid paths without award-success or private log bodies.

    :param live_server: Real HTTP backend. Example: local random port.
    :param caplog: Captured actual logs. Example: denied receipt records.
    :return: None. Example: rejection beats and absence checks pass.
    :raises AssertionError: Missing rejection or leaked secret/private body.
    """
    raise NotImplementedError()


@pytest.mark.django_db(transaction=True)
async def test_mcp_client_factory_with_different_actors_restores_context_and_auth(
    mcp_client_factory: MCPClientFactory, mcp_dataset: MCPDataset
) -> None:
    """Prove actor selection and teardown using actual registered calls.

    :param mcp_client_factory: Explicit actor/entrypoint factory. Example: Mike then Maria.
    :param mcp_dataset: Real actor/target fixtures. Example: both PIP self cases.
    :return: None. Example: no token/context/client crossover.
    :raises AssertionError: Wrong actor, leaked singleton/context or unclosed owned client.
    """
    raise NotImplementedError()


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
    raise NotImplementedError()


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
    raise NotImplementedError()


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
    raise NotImplementedError()


pytest_plugins = ["tests.support.karma_mcp"]
