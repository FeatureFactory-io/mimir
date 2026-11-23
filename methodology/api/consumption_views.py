from __future__ import annotations

"""Token-authenticated receipt boundary; no award business rules."""
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, TYPE_CHECKING
from uuid import UUID
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

if TYPE_CHECKING:
    from methodology.services.karma_service import AwardOutcome
ReceiptChannel = Literal["mcp_detail", "export"]


@dataclass(frozen=True)
class ConsumptionReceiptPayload:
    """Validated receipt fields; actor and award properties are absent."""

    entity_type: str
    entity_id: int
    event_identity: UUID
    channel: ReceiptChannel


class ConsumptionReceiptView(APIView):
    """Accept explicit authenticated consumption attestations."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        """Validate receipt and delegate once to the shared consumption service.

        :param request: Token-authenticated request. Example: activity 6203.
        :return: Safe receipt response. Example: {"status": "applied", "created_count": 2}.
        :raises RuntimeError: Unexpected persistence failure; no success response.
        """
        raise NotImplementedError()

    def _parse_receipt(self, payload: object) -> ConsumptionReceiptPayload:
        """Parse exactly the four allowed fields.

        :param payload: JSON object. Example: {"entity_type": "activity", "entity_id": 6203}.
        :return: Validated immutable receipt. Example: mcp_detail receipt.
        :raises ValueError: Nonobject, missing, unknown or invalid fields.
        """
        raise NotImplementedError()

    def _validate_field_names(self, payload: Mapping[str, object]) -> None:
        """Reject unknown fields, including actor and award overrides.

        :param payload: Receipt fields. Example: {"actor_id": 4}.
        :return: None. Example: exactly four approved keys accepted.
        :raises ValueError: Missing/unknown key; example: points or recipient.
        """
        raise NotImplementedError()

    def _parse_entity_reference(
        self, entity_type: object, entity_id: object
    ) -> tuple[str, int]:
        """Validate the nine supported entity kinds and a positive integer ID.

        :param entity_type: Kind value. Example: "pip".
        :param entity_id: Identifier value. Example: 6203.
        :return: Kind and ID. Example: ("activity", 6203).
        :raises ValueError: Unsupported kind, boolean, noninteger or nonpositive ID.
        """
        raise NotImplementedError()

    def _parse_event_identity(self, value: object) -> UUID:
        """Require an explicit valid action UUID.

        :param value: JSON UUID string. Example: "00000000-0000-0000-0000-000000000001".
        :return: Parsed UUID. Example: UUID(int=1).
        :raises ValueError: Missing or malformed UUID.
        """
        raise NotImplementedError()

    def _parse_channel(self, value: object) -> ReceiptChannel:
        """Accept only this endpoint's MCP-detail and export channels.

        :param value: Channel value. Example: "export".
        :return: Trusted allowlisted channel. Example: "mcp_detail".
        :raises ValueError: Unknown channel; example: "gui_copy".
        """
        raise NotImplementedError()

    def _result_payload(
        self, outcomes: tuple[AwardOutcome, ...], event_identity: UUID
    ) -> dict[str, object]:
        """Project outcomes without exposing ledger/private domain objects.

        :param outcomes: Shared-service result. Example: two created outcomes or ().
        :param event_identity: Original action UUID. Example: UUID(int=1).
        :return: Safe DTO. Example: {"status": "skipped", "created_count": 0, "reason": "self_consumption"}.
        :raises RuntimeError: Inconsistent partial-pair result.
        """
        raise NotImplementedError()

    def _error_response(self, error: Exception) -> Response:
        """Translate recognized failures into sanitized HTTP responses.

        :param error: Domain/input failure. Example: PermissionError("denied").
        :return: Safe 400/403/404/409 response. Example: forbidden receipt.
        :raises Exception: Unrecognized programming/persistence error.
        """
        raise NotImplementedError()
