from __future__ import annotations

"""Distinct S40 bindings; reuse undecorated support, never import step modules."""
import hashlib
import json
from uuid import uuid4

from behave import given, then, when
from behave.runner import Context
from django.apps import apps
from django.urls import reverse
from rest_framework.authtoken.models import Token

from tests.support.experts_mcp_self import (
    assert_self_fetch_content,
    assert_self_fetch_unchanged,
    resolve_self_fetch_case,
    snapshot_karma_state,
)

_UNCHANGED_DATABASE = (
    "Self-fetch changed persisted content, profiles, roles or other database state."
)


@given("{consumer} has a valid MCP token and existing permission for {content}")
def given_self_fetch_permission(context: Context, consumer: str, content: str) -> None:
    """Resolve real Cedar content, token and pre-operation ledger state.

    :param context: Existing transactional AT context. Example: cedar_dataset.
    :param consumer: Literal actor. Example: "Mike".
    :param content: Exact outline content. Example: "Mike's Activity".
    :return: None. Example: genuine permission and snapshot established.
    :raises AssertionError: Fixture role, token or permission is wrong.
    :raises ValueError: The consumer/content pair is not one of the ten literals.
    :raises TypeError: The consumer or content is not a string.
    """
    case = resolve_self_fetch_case(context.cedar_dataset, consumer, content)
    token, _ = Token.objects.get_or_create(user=case.actor)
    context.self_fetch_case = case
    context.self_fetch_authorization = f"Token {token.key}"
    context.self_fetch_action = str(uuid4())
    context.self_fetch_karma_before = snapshot_karma_state()
    context.self_fetch_database_before = _self_fetch_database_fingerprint()
    assert_self_fetch_unchanged(context.self_fetch_karma_before, case)


@when("the consumer successfully uses {tool} on that content")
def when_self_fetch_succeeds(context: Context, tool: str) -> None:
    """Exercise real authorized detail GET and shared token receipt boundary.

    :param context: Prepared case/client. Example: Mike activity self-fetch.
    :param tool: Existing detail tool name. Example: "get_activity".
    :return: None. Example: actual content and successful zero-award receipt.
    :raises AssertionError: Wrong tool, denied read or failed receipt.
    """
    case = context.self_fetch_case
    assert tool == case.tool_name, "Outline tool must match its real content."
    headers = {"HTTP_AUTHORIZATION": context.self_fetch_authorization}
    response = context.client.get(
        reverse(f"api-{case.entity_type}-detail", args=[case.entity_id]), **headers
    )
    assert response.status_code == 200, response.content.decode()
    context.self_fetch_payload = response.json()
    assert_self_fetch_content(context.self_fetch_payload, case)
    payload = {
        "entity_type": case.entity_type,
        "entity_id": case.entity_id,
        "event_identity": context.self_fetch_action,
        "channel": "mcp_detail",
    }
    receipt = context.client.post(
        reverse("api_consumption_receipt"),
        data=json.dumps(payload),
        content_type="application/json",
        **headers,
    )
    assert receipt.status_code == 200, receipt.content.decode()
    context.self_fetch_receipt = receipt.json()
    assert context.self_fetch_receipt == {
        "event_identity": context.self_fetch_action,
        "status": "skipped",
        "created_count": 0,
        "reason": "self_consumption",
    }


@then("the consumer total remains {total:d} and no paired author award is created")
def then_self_fetch_preserves_karma(context: Context, total: int) -> None:
    """Assert full-ledger equality and all-user totals after the real request.

    :param context: Completed operation and snapshot. Example: Maria PIP.
    :param total: Literal expected total. Example: 8200.
    :return: None. Example: actor, target author and entire ledger unchanged.
    :raises AssertionError: Content was not successful or any award changed.
    """
    case = context.self_fetch_case
    assert type(total) is int and total == case.expected_total
    assert_self_fetch_content(context.self_fetch_payload, case)
    assert context.self_fetch_receipt["created_count"] == 0
    assert_self_fetch_unchanged(context.self_fetch_karma_before, case)
    after = _self_fetch_database_fingerprint()
    assert after == context.self_fetch_database_before, _UNCHANGED_DATABASE


def _self_fetch_database_fingerprint() -> str:
    """Hash every real application row, including automatic relationship tables.

    :return: Private deterministic digest. Example: SHA256 of unchanged Cedar rows.
    :raises TypeError: A model cannot expose deterministic primary-key ordered rows.
    """
    models = sorted(
        apps.get_models(include_auto_created=True), key=lambda m: m._meta.label
    )
    rows = [
        (model._meta.label, list(model._default_manager.order_by("pk").values_list()))
        for model in models
    ]
    serialized = json.dumps(rows, default=str, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()
