from __future__ import annotations

"""Ten-row real MCP/HTTP/database self-fetch proofs."""
import json
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
from pytest import LogCaptureFixture
from pytest_django.live_server_helper import LiveServer
from rest_framework.authtoken.models import Token

from methodology.services.karma_service import KarmaService
from tests.support.experts_data import load_cedar_baseline
from tests.support.experts_logs import capture_experts_logs
from tests.support.experts_mcp_self import (
    SelfFetchCase,
    assert_self_fetch_content,
    assert_self_fetch_unchanged,
    resolve_self_fetch_case,
    snapshot_karma_state,
)
from tests.support.log_story import assert_log_story

ACTION_ID = UUID("ed59b358-59c8-4664-bd47-d1ff63f52040")
PRIVATE_SENTINEL = "private-forged-self-fetch-payload"
SERVICE_LOG = "KarmaService.award_successful_consumption"
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
    raise NotImplementedError()


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
    raise NotImplementedError()


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
    raise NotImplementedError()


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
    raise NotImplementedError()


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
