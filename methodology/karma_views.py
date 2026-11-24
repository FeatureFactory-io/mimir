"""Successful GUI-copy receipt boundary."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from uuid import UUID

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from methodology.services.karma_service import (
    AWARD_CORRELATION_ID,
    GUI_COPY_ENTITY_TYPES,
    MAX_CONSUMPTION_ENTITY_ID,
    AwardOutcome,
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


class _RejectedCopyPayload(ValueError):
    """A controlled parse failure carrying only a validated optional action UUID."""

    def __init__(self, event_identity: UUID | None) -> None:
        """Keep safe identity apart from rejected body content.

        :param event_identity: Unique canonical UUID, or None when untrusted.
        :return: None; the exception message contains no request values.
        """
        super().__init__("Copy receipt has invalid fields.")
        self.event_identity = event_identity


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
    request_trace = trace
    operation = _RECEIPT_LOG
    actor = request.user
    if not (actor.is_authenticated and actor.is_active):
        logger.info(f"{operation} | branch | {trace} reason=unauthenticated awards=0")
        return _copy_receipt_error("unauthenticated", 401)
    logger.info(f"{operation} | entry | {trace} actor_id={actor.pk} operation=gui_copy")
    try:
        payload = _parse_copy_receipt(request)
        trace += (
            f" entity_type={payload.entity_type} entity_id={payload.entity_id}"
            f" action_uuid={payload.event_identity}"
        )
        logger.info(f"{operation} | validation | {trace} validated")
        outcomes = _award_copy_receipt(actor, payload)
    except ValueError as error:
        reason = "invalid_payload"
        if isinstance(error, _RejectedCopyPayload) and error.event_identity is not None:
            trace += f" action_uuid={error.event_identity}"
    except (ObjectDoesNotExist, PermissionError):
        reason = "access_denied"
    except ValidationError:
        reason = "event_conflict"
    else:
        return _copy_receipt_success(outcomes, request_trace, payload)
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

    # Preserve pairs: a duplicate UUID must never acquire a correlation identity.
    pairs = json.loads(body.decode("utf-8"), object_pairs_hook=tuple)
    try:
        return _validate_copy_receipt(pairs)
    except ValueError as error:
        raise _RejectedCopyPayload(_copy_rejected_identity(pairs)) from error


def _validate_copy_receipt(pairs: object) -> CopyReceiptPayload:
    """Validate the exact field set before accepting any attribution reference.

    :param pairs: Decoded JSON object pairs, e.g. three approved fields.
    :return: Immutable validated target and action UUID.
    :raises ValueError: Nonobject, duplicate/unknown fields or invalid reference.
    """
    if not isinstance(pairs, tuple) or len(pairs) != len(_COPY_FIELDS):
        raise ValueError("Copy receipt must contain exactly the permitted fields.")
    data = dict(pairs)
    if data.keys() != _COPY_FIELDS:
        raise ValueError("Copy receipt must contain exactly the permitted fields.")
    entity_type, entity_id = data["entity_type"], data["entity_id"]
    if not isinstance(entity_type, str) or entity_type not in GUI_COPY_ENTITY_TYPES:
        raise ValueError("Unsupported copy entity type.")
    if type(entity_id) is not int or not 0 < entity_id <= MAX_CONSUMPTION_ENTITY_ID:
        raise ValueError("A positive copy entity ID is required.")
    return CopyReceiptPayload(
        entity_type, entity_id, _parse_copy_identity(data["event_identity"])
    )


def _parse_copy_identity(value: object) -> UUID:
    """Accept only the existing canonical UUID spelling.

    :param value: Wire identity, e.g. a 36-character UUID string.
    :return: Normalized UUID suitable for safe logs and persistence.
    :raises ValueError: A malformed/noncanonical/nonstring value.
    """
    if not isinstance(value, str) or len(value) != 36:
        raise ValueError("A canonical copy action UUID is required.")
    action_uuid = UUID(value)
    if str(action_uuid) != value.lower():
        raise ValueError("A canonical copy action UUID is required.")
    return action_uuid


def _copy_rejected_identity(pairs: object) -> UUID | None:
    """Extract one safe identity without accepting other rejected fields.

    :param pairs: Bounded, successfully decoded object pairs.
    :return: Unique canonical UUID, or None for absent/duplicate/invalid identity.
    """
    if not isinstance(pairs, tuple):
        return None
    actions = [value for key, value in pairs if key == "event_identity"]
    if len(actions) != 1:
        return None
    try:
        return _parse_copy_identity(actions[0])
    except ValueError:
        return None


def _award_copy_receipt(
    actor: User, payload: CopyReceiptPayload
) -> tuple[AwardOutcome, ...]:
    """Delegate the validated GUI receipt to the single existing award writer.

    :param actor: Session-authenticated active user, e.g. Maria.
    :param payload: Validated target/action, e.g. Mike's activity 6203.
    :return: Existing atomic service outcomes, e.g. one learner/author pair.
    :raises ObjectDoesNotExist: Target cannot be found or remains masked.
    :raises PermissionError: Actor is not authorized for the target.
    :raises ValidationError: The action conflicts with its existing event.
    """
    args = payload.entity_type, payload.entity_id, payload.event_identity
    return KarmaService.award_successful_consumption(actor, *args, channel="gui_copy")


def _copy_receipt_success(
    outcomes: tuple[AwardOutcome, ...], trace: str, payload: CopyReceiptPayload
) -> JsonResponse:
    """Serialize only a successful shared-service result.

    :param outcomes: Actual atomic award outcomes, e.g. one learner/author pair.
    :param trace: Original safe request trace, e.g. request_id=cedar-copy-receipt-01.
    :param payload: Accepted action reference, e.g. the normalized activity UUID.
    :return: Existing applied/replayed/self-consumption response unchanged.
    """
    receipt = {"status": "skipped", "reason": "self_consumption"}
    if outcomes:
        receipt = {"status": "applied" if outcomes[0].created else "replayed"}
    event = f"action_uuid={payload.event_identity}"
    logger.info(
        "%s | exit | %s %s status=%s", _RECEIPT_LOG, trace, event, receipt["status"]
    )
    return JsonResponse(receipt)


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
