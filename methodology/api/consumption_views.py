"""Token-authenticated receipt boundary for successful consumption."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from rest_framework import status
from rest_framework.authentication import (
    TokenAuthentication as HeaderTokenAuthentication,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from methodology.services.karma_service import (
    AWARD_CORRELATION_ID,
    MAX_CONSUMPTION_ENTITY_ID,
    AwardOutcome,
    KarmaService,
)

logger = logging.getLogger(__name__)
_RECEIPT_LOG = "ConsumptionReceiptView.post"
_MAX_RECEIPT_BYTES = 512
_CANONICAL_UUID_LENGTH = 36
_RECEIPT_FIELDS = frozenset({"entity_type", "entity_id", "event_identity", "channel"})
_ENTITY_TYPES = frozenset(
    {
        "activity",
        "agent",
        "artifact",
        "phase",
        "pip",
        "playbook",
        "rule",
        "skill",
        "workflow",
    }
)
_RECEIPT_ERRORS = (ValueError, ObjectDoesNotExist, PermissionError, ValidationError)
ReceiptChannel = Literal["mcp_detail", "export"]


class _RejectedReceiptPayload(ValueError):
    """A controlled parse failure carrying only a validated optional action UUID."""

    def __init__(self, event_identity: UUID | None) -> None:
        """Keep safe identity apart from rejected body content.

        :param event_identity: Unique canonical UUID, or None when untrusted.
        :return: None; the exception message contains no request values.
        """
        super().__init__("Consumption receipt has invalid fields.")
        self.event_identity = event_identity


@dataclass(frozen=True)
class ConsumptionReceiptPayload:
    """Validated receipt fields; actor and award properties are absent."""

    entity_type: str
    entity_id: int
    event_identity: UUID
    channel: ReceiptChannel


class ConsumptionReceiptView(APIView):
    """Accept explicit authenticated consumption attestations."""

    authentication_classes = (HeaderTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request: Request) -> Response:
        """Validate receipt and delegate once to the shared consumption service.

        :param request: Token-authenticated request. Example: activity 6203.
        :return: Safe receipt response. Example: {"status": "applied", "created_count": 2}.
        :raises RuntimeError: Unexpected persistence failure; no success response.
        """
        actor = request.user
        request_id = AWARD_CORRELATION_ID.fullmatch(getattr(request, "request_id", ""))
        trace = f"actor_id={actor.pk} request_id={request_id.group() if request_id else 'unavailable'}"
        logger.info("%s | entry | %s", _RECEIPT_LOG, trace)
        try:
            receipt = self._parse_receipt(request)
            trace += (
                f" entity_type={receipt.entity_type} entity_id={receipt.entity_id}"
                f" event_identity={receipt.event_identity} channel={receipt.channel}"
            )
            logger.info("%s | validation | %s", _RECEIPT_LOG, trace)
            args = receipt.entity_type, receipt.entity_id, receipt.event_identity
            outcomes = KarmaService.award_successful_consumption(
                actor, *args, channel=receipt.channel
            )
        except _RECEIPT_ERRORS as error:
            return self._rejected_response(error, trace)
        result = self._result_payload(outcomes, receipt.event_identity)
        counts = f"status={result['status']} created_count={result['created_count']}"
        outcome = f"{counts} occurred_at={result.get('occurred_at')}"
        logger.info("%s | exit | %s %s", _RECEIPT_LOG, trace, outcome)
        return Response(result)

    def _rejected_response(self, error: Exception, trace: str) -> Response:
        """Log a recognized rejection with only validated safe identity metadata.

        :param error: Controlled boundary failure, e.g. unknown payload fields.
        :param trace: Safe actor/request and any already validated target fields.
        :return: Existing sanitized response, e.g. invalid_payload HTTP400.
        :raises Exception: An unrecognized error, e.g. unexpected persistence failure.
        """
        if (
            isinstance(error, _RejectedReceiptPayload)
            and error.event_identity is not None
        ):
            trace += f" event_identity={error.event_identity}"
        response = self._error_response(error)
        logger.info(
            "%s | branch | %s reason=%s awards=0",
            _RECEIPT_LOG,
            trace,
            response.data["reason"],
        )
        return response

    def _parse_receipt(self, request: Request) -> ConsumptionReceiptPayload:
        """Parse exactly the four allowed fields.

        :param request: Bounded UTF-8 JSON request. Example: a complete activity receipt.
        :return: Validated immutable receipt. Example: mcp_detail receipt.
        :raises ValueError: Nonobject, missing, unknown or invalid fields.
        """
        media_type = request.content_type.partition(";")[0].strip().lower()
        if media_type != "application/json":
            raise ValueError("A JSON consumption receipt is required.")
        payload = request.read(_MAX_RECEIPT_BYTES + 1)
        if len(payload) > _MAX_RECEIPT_BYTES:
            raise ValueError("Consumption receipt exceeds the size limit.")
        # Retain pairs until both uniqueness and the field allowlist are checked.
        pairs = json.loads(payload.decode("utf-8"), object_pairs_hook=tuple)
        try:
            return self._validate_receipt_pairs(pairs)
        except ValueError as error:
            raise _RejectedReceiptPayload(self._rejected_identity(pairs)) from error

    def _validate_receipt_pairs(self, pairs: object) -> ConsumptionReceiptPayload:
        """Validate exact fields before treating any client reference as trusted.

        :param pairs: Decoded JSON object pairs, e.g. four permitted fields.
        :return: Immutable validated consumption payload.
        :raises ValueError: Nonobject/duplicate/unknown fields or invalid values.
        """
        if not isinstance(pairs, tuple) or len(pairs) != len(_RECEIPT_FIELDS):
            raise ValueError("A receipt must specify exactly the permitted fields.")
        fields = dict(pairs)
        self._validate_field_names(fields)
        entity_type, entity_id = self._parse_entity_reference(
            fields["entity_type"], fields["entity_id"]
        )
        return ConsumptionReceiptPayload(
            entity_type,
            entity_id,
            self._parse_event_identity(fields["event_identity"]),
            self._parse_channel(fields["channel"]),
        )

    def _rejected_identity(self, pairs: object) -> UUID | None:
        """Extract one canonical action for correlation without accepting the body.

        :param pairs: Bounded, successfully decoded JSON object pairs.
        :return: Safe normalized UUID, or None for duplicate/invalid identity.
        """
        if not isinstance(pairs, tuple):
            return None
        actions = [value for key, value in pairs if key == "event_identity"]
        if len(actions) != 1:
            return None
        try:
            return self._parse_event_identity(actions[0])
        except ValueError:
            return None

    def _validate_field_names(self, payload: Mapping[str, object]) -> None:
        """Reject unknown fields, including actor and award overrides.

        :param payload: Receipt fields. Example: {"actor_id": 4}.
        :return: None. Example: exactly four approved keys accepted.
        :raises ValueError: Missing/unknown key; example: points or recipient.
        """
        if payload.keys() != _RECEIPT_FIELDS:
            raise ValueError("A receipt must specify exactly the permitted fields.")

    def _parse_entity_reference(
        self, entity_type: object, entity_id: object
    ) -> tuple[str, int]:
        """Validate the nine supported entity kinds and a positive integer ID.

        :param entity_type: Kind value. Example: "pip".
        :param entity_id: Identifier value. Example: 6203.
        :return: Kind and ID. Example: ("activity", 6203).
        :raises ValueError: Unsupported kind, boolean, noninteger or nonpositive ID.
        """
        if not isinstance(entity_type, str) or entity_type not in _ENTITY_TYPES:
            raise ValueError("Unsupported consumption entity type.")
        if type(entity_id) is not int or not 0 < entity_id <= MAX_CONSUMPTION_ENTITY_ID:
            raise ValueError("A positive consumption entity ID is required.")
        return entity_type, entity_id

    def _parse_event_identity(self, value: object) -> UUID:
        """Require an explicit valid action UUID.

        :param value: JSON UUID string. Example: "00000000-0000-0000-0000-000000000001".
        :return: Parsed UUID. Example: UUID(int=1).
        :raises ValueError: Missing or malformed UUID.
        """
        if not isinstance(value, str) or len(value) != _CANONICAL_UUID_LENGTH:
            raise ValueError("A canonical consumption action UUID is required.")
        event_identity = UUID(value)
        if str(event_identity) != value.lower():
            raise ValueError("A canonical consumption action UUID is required.")
        return event_identity

    def _parse_channel(self, value: object) -> ReceiptChannel:
        """Accept only this endpoint's MCP-detail and export channels.

        :param value: Channel value. Example: "export".
        :return: Trusted allowlisted channel. Example: "mcp_detail".
        :raises ValueError: Unknown channel; example: "gui_copy".
        """
        if value == "mcp_detail":
            return "mcp_detail"
        if value == "export":
            return "export"
        raise ValueError("Unsupported consumption receipt channel.")

    def _result_payload(
        self, outcomes: tuple[AwardOutcome, ...], event_identity: UUID
    ) -> dict[str, object]:
        """Project outcomes without exposing ledger/private domain objects.

        :param outcomes: Shared-service result. Example: two created outcomes or ().
        :param event_identity: Original action UUID. Example: UUID(int=1).
        :return: Safe DTO. Example: {"status": "skipped", "created_count": 0, "reason": "self_consumption"}.
        :raises RuntimeError: Inconsistent partial-pair result.
        """
        result: dict[str, object] = {"event_identity": str(event_identity)}
        if not outcomes:
            return {
                **result,
                "status": "skipped",
                "created_count": 0,
                "reason": "self_consumption",
            }
        if len(outcomes) != 2:
            raise RuntimeError("Consumption service returned an incomplete award pair.")
        learner, author = outcomes
        if (
            learner.award is None
            or author.award is None
            or learner.created != author.created
            or learner.award.occurred_at != author.award.occurred_at
        ):
            raise RuntimeError(
                "Consumption service returned inconsistent award outcomes."
            )
        return {
            **result,
            "status": "applied" if learner.created else "replayed",
            "created_count": len(outcomes) if learner.created else 0,
            "occurred_at": learner.award.occurred_at.isoformat(),
        }

    def _error_response(self, error: Exception) -> Response:
        """Translate recognized failures into sanitized HTTP responses.

        :param error: Domain/input failure. Example: PermissionError("denied").
        :return: Safe 400/404/409 response. Example: an unavailable target.
        :raises Exception: Unrecognized programming/persistence error.
        """
        if isinstance(error, ValueError):
            reason, code = "invalid_payload", status.HTTP_400_BAD_REQUEST
        elif isinstance(error, (ObjectDoesNotExist, PermissionError)):
            reason, code = "target_unavailable", status.HTTP_404_NOT_FOUND
        elif (
            isinstance(error, ValidationError)
            and getattr(error, "code", None) == "award_payload_conflict"
        ):
            reason, code = "event_conflict", status.HTTP_409_CONFLICT
        else:
            raise error
        return Response({"status": "rejected", "reason": reason}, status=code)
