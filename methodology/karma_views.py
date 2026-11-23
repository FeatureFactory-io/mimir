from __future__ import annotations

"""Successful GUI-copy receipt boundary."""
from dataclasses import dataclass
from uuid import UUID
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_POST


@dataclass(frozen=True)
class CopyReceiptPayload:
    """Allowlisted client report; actor and attribution are never client fields."""

    entity_type: str
    entity_id: int
    event_identity: UUID


@require_POST
def copy_success_receipt(request: HttpRequest) -> JsonResponse:
    """Accept a session-authenticated report of a successful clipboard write.

    :param request: CSRF-protected same-origin JSON request. Example: activity 6203.
    :return: Safe receipt outcome. Example: {"status": "applied"}.
    :raises NotImplementedError: Until the approved implementation begins.
    """
    raise NotImplementedError()


def _parse_copy_receipt(request: HttpRequest) -> CopyReceiptPayload:
    """Parse a bounded JSON object with an exact field allowlist.

    :param request: JSON request with entity kind/id and UUID. Example: activity 6203.
    :return: Validated payload. Example: CopyReceiptPayload("activity", 6203, uuid).
    :raises ValueError: For malformed JSON, unknown keys or invalid field values.
    """
    raise NotImplementedError()


def _copy_receipt_error(reason: str, status: int) -> JsonResponse:
    """Serialize a body-free safe receipt rejection.

    :param reason: Stable non-sensitive reason. Example: "access_denied".
    :param status: HTTP error status. Example: 404.
    :return: Safe error response. Example: {"status": "rejected", "reason": "access_denied"}.
    :raises ValueError: If the reason or status is not allowlisted.
    """
    raise NotImplementedError()
