"""Successful GUI-copy receipt boundary."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from methodology.services.karma_service import (
    AWARD_CORRELATION_ID,
    GUI_COPY_ENTITY_TYPES,
    MAX_CONSUMPTION_ENTITY_ID,
    KarmaService,
)

logger = logging.getLogger(__name__)
_RECEIPT_LOG = "copy_success_receipt"
_COPY_FIELDS = {"entity_type", "entity_id", "event_identity"}
_MAX_COPY_RECEIPT_BYTES = 512
_REJECTION_STATUS = {
    "invalid_payload": 400,
    "unauthenticated": 401,
    "access_denied": 404,
    "event_conflict": 409,
}


@dataclass(frozen=True)
class CopyReceiptPayload:
    """Allowlisted client report; actor and attribution are never client fields."""

    entity_type: str
    entity_id: int
    event_identity: UUID


@require_POST
@csrf_protect
def copy_success_receipt(request: HttpRequest) -> JsonResponse:
    """Accept a session-authenticated report of a successful clipboard write.

    :param request: CSRF-protected same-origin JSON request. Example: activity 6203.
    :return: Safe receipt outcome. Example: {"status": "applied"}.
    """
    request_id = AWARD_CORRELATION_ID.fullmatch(getattr(request, "request_id", ""))
    trace = f"request_id={request_id.group() if request_id else 'unavailable'}"
    operation = _RECEIPT_LOG
    actor = request.user
    if not (actor.is_authenticated and actor.is_active):
        logger.info(f"{operation} | branch | {trace} reason=unauthenticated awards=0")
        return _copy_receipt_error("unauthenticated", 401)
    logger.info(f"{operation} | entry | {trace} actor_id={actor.pk} operation=gui_copy")
    try:
        payload = _parse_copy_receipt(request)
        target = f"entity_type={payload.entity_type} entity_id={payload.entity_id}"
        event = f"action_uuid={payload.event_identity}"
        logger.info(f"{operation} | validation | {trace} {target} {event} validated")
        award = KarmaService.award_successful_consumption
        target_args = payload.entity_type, payload.entity_id, payload.event_identity
        outcomes = award(actor, *target_args, channel="gui_copy")
    except ValueError:
        reason = "invalid_payload"
    except (ObjectDoesNotExist, PermissionError):
        reason = "access_denied"
    except ValidationError:
        reason = "event_conflict"
    else:
        receipt = {"status": "skipped", "reason": "self_consumption"}
        if outcomes:
            receipt = {"status": "applied" if outcomes[0].created else "replayed"}
        logger.info(f"{operation} | exit | {trace} {event} status={receipt['status']}")
        return JsonResponse(receipt)
    logger.info(f"{operation} | branch | {trace} reason={reason} awards=0")
    return _copy_receipt_error(reason, _REJECTION_STATUS[reason])


def _parse_copy_receipt(request: HttpRequest) -> CopyReceiptPayload:
    """Parse a bounded JSON object with an exact field allowlist.

    :param request: JSON request with entity kind/id and UUID. Example: activity 6203.
    :return: Validated payload. Example: CopyReceiptPayload("activity", 6203, uuid).
    :raises ValueError: For malformed JSON, unknown keys or invalid field values.
    """
    if request.content_type != "application/json":
        raise ValueError("A JSON copy receipt is required.")
    body = request.read(_MAX_COPY_RECEIPT_BYTES + 1)
    if len(body) > _MAX_COPY_RECEIPT_BYTES:
        raise ValueError("Copy receipt exceeds the size limit.")

    # Preserve JSON member pairs so duplicate fields cannot silently override inputs.
    pairs = json.loads(body.decode("utf-8"), object_pairs_hook=tuple)
    if not isinstance(pairs, tuple) or len(pairs) != len(_COPY_FIELDS):
        raise ValueError("Copy receipt must contain exactly the permitted fields.")
    data = dict(pairs)
    if data.keys() != _COPY_FIELDS:
        raise ValueError("Copy receipt must contain exactly the permitted fields.")
    entity_type, entity_id, action = (
        data["entity_type"],
        data["entity_id"],
        data["event_identity"],
    )
    if not isinstance(entity_type, str) or entity_type not in GUI_COPY_ENTITY_TYPES:
        raise ValueError("Unsupported copy entity type.")
    if type(entity_id) is not int or not 0 < entity_id <= MAX_CONSUMPTION_ENTITY_ID:
        raise ValueError("A positive copy entity ID is required.")
    if not isinstance(action, str) or len(action) != 36:
        raise ValueError("A canonical copy action UUID is required.")
    action_uuid = UUID(action)
    if str(action_uuid) != action.lower():
        raise ValueError("A canonical copy action UUID is required.")
    return CopyReceiptPayload(entity_type, entity_id, action_uuid)


def _copy_receipt_error(reason: str, status: int) -> JsonResponse:
    """Serialize a body-free safe receipt rejection.

    :param reason: Stable non-sensitive reason. Example: "access_denied".
    :param status: HTTP error status. Example: 404.
    :return: Safe error response. Example: {"status": "rejected", "reason": "access_denied"}.
    :raises ValueError: If the reason or status is not allowlisted.
    """
    if _REJECTION_STATUS.get(reason) != status:
        raise ValueError("Unsupported copy receipt rejection.")
    return JsonResponse({"status": "rejected", "reason": reason}, status=status)
