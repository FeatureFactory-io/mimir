"""Real HTTP regressions for safe rejected-receipt correlation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

import pytest
from django.conf import settings
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
from pytest import LogCaptureFixture
from rest_framework.authtoken.models import Token

from methodology.models import KarmaAward
from tests.support.experts_data import CedarDataset
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

_ACTION = UUID("a1b2c3d4-1234-5678-9abc-123456789abc")
_REQUEST = "receipt-rejection-distinct-request"
_PRIVATE_TEXT = "never-log-rejected-request-text"
_RECEIPT_LOGGERS = ("methodology.karma_views", "methodology.api.consumption_views")


@dataclass(frozen=True)
class ReceiptClient:
    """Actual authenticated HTTP surface and its established log names."""

    client: Client
    surface: Literal["gui", "token"]
    csrf: str = ""

    @property
    def operation(self) -> str:
        """Return the existing logger operation, e.g. copy_success_receipt."""
        return (
            "copy_success_receipt"
            if self.surface == "gui"
            else "ConsumptionReceiptView.post"
        )

    @property
    def event_field(self) -> str:
        """Return the established event field, e.g. action_uuid."""
        return "action_uuid" if self.surface == "gui" else "event_identity"


@pytest.fixture(params=("gui", "token"))
def receipt_client(
    request: pytest.FixtureRequest, cedar_dataset: CedarDataset
) -> ReceiptClient:
    """Create real authenticated session/CSRF or token credentials.

    :param request: Parametrized transport, e.g. gui.
    :param cedar_dataset: Actual test-owned Cedar history and users.
    :return: A client that calls the production URL, e.g. token API client.
    """
    actor = cedar_dataset.users_by_username["mrodriguez"]
    client = Client(enforce_csrf_checks=True)
    if request.param == "token":
        token, _ = Token.objects.get_or_create(user=actor)
        client.defaults["HTTP_AUTHORIZATION"] = f"Token {token.key}"
        return ReceiptClient(client, "token")
    client.force_login(actor)
    assert client.get("/auth/user/profile/").status_code == 200
    return ReceiptClient(client, "gui", client.cookies[settings.CSRF_COOKIE_NAME].value)


def _payload(surface: ReceiptClient) -> dict[str, object]:
    """Return an authorized target with an uppercase canonical UUID.

    :param surface: Actual receipt surface, e.g. gui.
    :return: Existing allowed body fields, e.g. activity 6203.
    """
    result = {
        "entity_type": "activity",
        "entity_id": 6203,
        "event_identity": str(_ACTION).upper(),
    }
    if surface.surface == "token":
        result["channel"] = "mcp_detail"
    return result


def _post(
    surface: ReceiptClient, body: str | bytes, content_type: str = "application/json"
) -> None:
    """Send one real request and require controlled rejection.

    :param surface: Authenticated HTTP client with real credentials.
    :param body: Exact wire bytes, e.g. forged JSON object.
    :param content_type: Actual request media type, e.g. application/json.
    :return: None after observing HTTP400; caller checks logs and persistence.
    """
    response = _send(surface, body, content_type)
    assert response.status_code == 400
    assert response.json() == {"status": "rejected", "reason": "invalid_payload"}


def _send(
    surface: ReceiptClient, body: str | bytes, content_type: str = "application/json"
) -> HttpResponse:
    """Use the existing receipt URL with actual request and CSRF headers.

    :param surface: Real authenticated client, e.g. session Maria.
    :param body: Exact wire body, e.g. json.dumps(payload).
    :param content_type: Actual media type, e.g. application/json.
    :return: Real HTTP response from the owning production view.
    """
    endpoint = (
        reverse("karma_copy_receipt")
        if surface.surface == "gui"
        else "/api/consumption-receipts/"
    )
    return surface.client.post(
        endpoint,
        data=body,
        content_type=content_type,
        HTTP_X_REQUEST_ID=_REQUEST,
        HTTP_X_CSRFTOKEN=surface.csrf,
    )


def _ledger() -> tuple[tuple[object, ...], ...]:
    """Snapshot all persisted ledger fields in stable primary-key order.

    :return: Complete global state, e.g. every Cedar award including timestamp.
    """
    return tuple(KarmaAward.objects.order_by("pk").values_list())


def _branch_messages(caplog: LogCaptureFixture, surface: ReceiptClient) -> list[str]:
    """Select the exact existing boundary's controlled rejection records.

    :param caplog: Actual production records.
    :param surface: Existing operation spelling, e.g. token.
    :return: Safe branch messages for this distinct request ID.
    """
    return [
        record.getMessage()
        for record in caplog.records
        if surface.operation in record.getMessage()
        and "| branch |" in record.getMessage()
        and f"request_id={_REQUEST}" in record.getMessage()
    ]


@pytest.mark.parametrize(
    "forgery",
    ("unknown_fields", "duplicate_target", "invalid_target", "invalid_channel"),
)
def test_receipt_with_forged_fields_log_story_reject_retains_only_safe_uuid(
    receipt_client: ReceiptClient,
    caplog: LogCaptureFixture,
    forgery: str,
) -> None:
    """Reject actual forged attribution while retaining only normalized identity.

    :param receipt_client: Real CSRF or token client.
    :param caplog: Actual owner logs at INFO.
    :param forgery: Invalid wire semantics, e.g. duplicate_target.
    :return: None; entire ledger and controlled response remain unchanged.
    """
    body = _forged_body(receipt_client, forgery)
    before = _ledger()
    with capture_experts_logs(caplog, _RECEIPT_LOGGERS):
        _post(receipt_client, body)
    assert_log_story(
        caplog,
        where=receipt_client.operation,
        beats={
            "rejected": (
                "| branch |",
                f"request_id={_REQUEST}",
                "reason=invalid_payload",
                "awards=0",
                f"{receipt_client.event_field}={_ACTION}",
            )
        },
    )
    assert _ledger() == before
    messages = "\n".join(_branch_messages(caplog, receipt_client))
    assert _PRIVATE_TEXT not in caplog.text and "987654321" not in messages
    assert "entity_id=" not in messages and "status=applied" not in messages


def _forged_body(surface: ReceiptClient, forgery: str) -> str:
    """Keep exactly one valid UUID while rejecting all invalid attribution fields.

    :param surface: Existing receipt shape, e.g. token.
    :param forgery: Named failure, e.g. duplicate_target.
    :return: Wire JSON that must never authorize an award.
    """
    payload = _payload(surface)
    if forgery == "duplicate_target":
        return json.dumps(payload)[:-1] + ',"entity_id":987654321}'
    if forgery == "invalid_target":
        payload["entity_id"] = True
    elif forgery == "invalid_channel":
        payload["channel"] = _PRIVATE_TEXT
    else:
        payload.update(actor_id=987654321, prompt=_PRIVATE_TEXT)
    return json.dumps(payload)


@pytest.mark.parametrize("target", ("private", "missing"))
def test_receipt_with_unavailable_target_log_story_reject_retains_validated_target(
    receipt_client: ReceiptClient,
    cedar_dataset: CedarDataset,
    caplog: LogCaptureFixture,
    target: str,
) -> None:
    """Keep normalized target/action on real permission and missing-object denial.

    :param receipt_client: Real authenticated reader other than Mike.
    :param cedar_dataset: Actual related target and owner records.
    :param caplog: Actual receipt records.
    :param target: Real denial kind, e.g. private.
    :return: None; no ledger row is changed or added.
    """
    payload = _payload(receipt_client)
    if target == "private":
        book = cedar_dataset.playbooks_by_pk[6201]
        book.visibility = "private"
        book.save(update_fields=["visibility"])
    else:
        payload["entity_id"] = 987654321
    before = _ledger()
    with capture_experts_logs(caplog, _RECEIPT_LOGGERS):
        response = _send(receipt_client, json.dumps(payload))
    assert response.status_code == 404
    assert_log_story(
        caplog,
        where=receipt_client.operation,
        beats={
            "denied": (
                "| branch |",
                f"request_id={_REQUEST}",
                "awards=0",
                f"{receipt_client.event_field}={_ACTION}",
                "entity_type=activity",
                f"entity_id={payload['entity_id']}",
            )
        },
    )
    assert _ledger() == before


@pytest.mark.parametrize(
    "invalid",
    (
        "duplicate_uuid",
        "missing_uuid",
        "malformed_uuid",
        "nested_uuid",
        "array",
        "malformed_json",
        "invalid_utf8",
        "oversize",
        "content_type",
    ),
)
def test_receipt_with_untrusted_identity_rejects_without_logging_identity(
    receipt_client: ReceiptClient,
    caplog: LogCaptureFixture,
    invalid: str,
) -> None:
    """Reject nonunique/unparsed/oversized identity without reflecting wire input.

    :param receipt_client: Existing GUI/token client.
    :param caplog: Actual production owner records.
    :param invalid: Wire-level negative case, e.g. duplicate_uuid.
    :return: None; controlled rejection and global ledger preservation.
    """
    body, content_type = _invalid_body(receipt_client, invalid)
    before = _ledger()
    with capture_experts_logs(caplog, _RECEIPT_LOGGERS):
        _post(receipt_client, body, content_type)
    messages = _branch_messages(caplog, receipt_client)
    assert messages and all(f"{receipt_client.event_field}=" not in m for m in messages)
    assert _PRIVATE_TEXT not in caplog.text and str(_ACTION) not in "\n".join(messages)
    assert _ledger() == before


def _invalid_body(surface: ReceiptClient, invalid: str) -> tuple[str | bytes, str]:
    """Construct exact malformed bodies without touching request/parser behavior.

    :param surface: Existing receipt shape, e.g. token.
    :param invalid: Named adversarial case, e.g. oversize.
    :return: Raw bytes and media type to send over the actual Django boundary.
    """
    payload = _payload(surface)
    payload["event_identity"] = (
        {"uuid": str(_ACTION)} if invalid == "nested_uuid" else _PRIVATE_TEXT
    )
    if invalid == "missing_uuid":
        payload.pop("event_identity")
        raw = json.dumps(payload)
    elif invalid == "duplicate_uuid":
        raw = (
            json.dumps(_payload(surface))[:-1]
            + ',"event_identity":"'
            + str(_ACTION)
            + '"}'
        )
    elif invalid == "array":
        raw = json.dumps([_payload(surface)])
    elif invalid == "malformed_json":
        raw = '{"event_identity":"' + str(_ACTION) + '"'
    elif invalid == "invalid_utf8":
        raw = b"\xff"
    elif invalid in {"oversize", "content_type"}:
        raw = json.dumps(
            {
                **_payload(surface),
                "prompt": _PRIVATE_TEXT * (40 if invalid == "oversize" else 1),
            }
        )
    else:
        raw = json.dumps(payload)
    return raw, "text/plain" if invalid == "content_type" else "application/json"
