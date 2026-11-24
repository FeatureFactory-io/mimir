"""CAP-101 metadata for summary attempts; never store model bodies."""

from __future__ import annotations

import re
import uuid
from decimal import Decimal
from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

_WORKFLOW = "contribution_summary"
_CORRELATION = r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}"
_MODEL = r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}"
_CREDENTIAL = re.compile(
    r"(?:api[-_]?(?:key|token)|access[-_]?token|auth[-_]?token|client[-_]?secret|password):.+|"
    r"(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_-]{12,}|"
    r"github_pat_[A-Za-z0-9_-]{12,}|xox[baprs]-[A-Za-z0-9_-]{12,}|"
    r"(?:AKIA|ASIA)[A-Z0-9]{16}|eyJ[\w-]+\.[\w-]+\.[\w-]+|[a-f0-9]{40})",
    re.IGNORECASE,
)
_FAILURE_CODES = (
    "invalid_request",
    "public_evidence_failed",
    "provider_failed",
    "output_validation_failed",
    "storage_failed",
)
_MAX_TOKEN_COUNT = 2**31 - 1
_POSITIVE_ID = r"[1-9][0-9]{0,18}"
_PUBLIC_IDS = rf"(?:none|{_POSITIVE_ID}(?:,{_POSITIVE_ID})*)"
_BOOL = r"(?:true|false)"
_EVENT_FIELDS: dict[str, dict[str, str]] = {
    "entry": {
        "subject_id": rf"(?:{_POSITIVE_ID}|unvalidated)",
        "pip_id": _POSITIVE_ID,
        "correlation_id": _CORRELATION,
    },
    "public_evidence": {
        "scope": "public_released",
        "visibility": "public_released",
        "fact_count": r"[0-9]+",
        "evidence_chars": r"[0-9]+",
        "public_playbook_ids": _PUBLIC_IDS,
        "public_change_ids": _PUBLIC_IDS,
    },
    "llm_call": {"model": _MODEL, "tools": "none", "max_tokens": "1024"},
    "validation": {
        "status": "accepted",
        "sentence_count": r"[0-9]+",
        "limit": "14",
    },
    "domain_write": {"profile_id": _POSITIVE_ID, "summary_updated": "true"},
    "failure": {
        "reason_code": "|".join(_FAILURE_CODES),
        "last_good_retained": "true",
    },
    "exit": {
        "outcome": r"(?:success|failure)",
        "summary_updated": _BOOL,
        "karma_awarded": "0",
        "pip_lifecycle": "unchanged",
    },
}


class AgentInteraction(models.Model):
    """One persisted bounded-summary attempt and its authentic safe trace."""

    class Outcome(models.TextChoices):
        SUCCESS = ("success", "Success")
        FAILURE = ("failure", "Failure")

    call_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    subject = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="summary_interactions",
    )
    pip = models.ForeignKey(
        "methodology.ProcessImprovementProposal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="summary_interactions",
    )
    correlation_id = models.CharField(max_length=100, db_index=True)
    workflow_id = models.CharField(max_length=64, default=_WORKFLOW, editable=False)
    model = models.CharField(max_length=200)
    input_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)
    latency_ms = models.DecimalField(max_digits=16, decimal_places=3)
    estimated_cost_usd = models.DecimalField(
        max_digits=20, decimal_places=10, null=True, blank=True
    )
    outcome = models.CharField(max_length=20, choices=Outcome.choices)
    error_code = models.CharField(max_length=100, blank=True, default="")
    events = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["created_at", "pk"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(latency_ms__gte=Decimal(0)),
                name="summary_interaction_latency_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(estimated_cost_usd__isnull=True)
                | models.Q(estimated_cost_usd__gte=Decimal(0)),
                name="summary_interaction_cost_nonnegative",
            ),
        ]

    def clean(self) -> None:
        """Validate safe metadata before persistence.

        :return: None. Example: None for a valid success record.
        :raises ValidationError: For invalid identifiers, usage or trace.
        """
        super().clean()
        self._validate_identifiers()
        self._validate_measurements()
        self._validate_events()

    def _validate_identifiers(self) -> None:
        """Require safe bounded correlation, model and workflow identifiers.

        :return: None. Example: None for correlation_id="cedar-submit-01".
        :raises ValidationError: For missing or unsafe identifiers.
        """
        for field, pattern in (("correlation_id", _CORRELATION), ("model", _MODEL)):
            value = getattr(self, field)
            if (
                not isinstance(value, str)
                or not re.fullmatch(pattern, value)
                or _CREDENTIAL.search(value)
            ):
                raise ValidationError({field: "A safe bounded identifier is required."})
        if self.workflow_id != _WORKFLOW:
            raise ValidationError(
                {"workflow_id": "Invalid contribution summary workflow."}
            )
        if not isinstance(self.call_id, uuid.UUID):
            raise ValidationError({"call_id": "A call UUID is required."})
        if self.outcome == self.Outcome.SUCCESS and self.error_code == "":
            return
        if (
            self.outcome != self.Outcome.FAILURE
            or self.error_code not in _FAILURE_CODES
        ):
            raise ValidationError(
                {"error_code": "Invalid contribution summary outcome metadata."}
            )

    def _validate_measurements(self) -> None:
        """Reject negative/nonfinite measurements and invented missing usage.

        :return: None. Example: None with unknown tokens and null cost.
        :raises ValidationError: For invalid tokens, latency or cost.
        """
        for field in ("input_tokens", "output_tokens"):
            tokens = getattr(self, field)
            if tokens is not None and (
                type(tokens) is not int or not 0 <= tokens <= _MAX_TOKEN_COUNT
            ):
                raise ValidationError(
                    {field: "Token count must be nonnegative or absent."}
                )
        for field in ("latency_ms", "estimated_cost_usd"):
            amount = getattr(self, field)
            if field == "estimated_cost_usd" and amount is None:
                continue
            if type(amount) is int:
                amount = Decimal(amount)
            if not isinstance(amount, Decimal) or not amount.is_finite() or amount < 0:
                raise ValidationError(
                    {field: "A finite nonnegative measurement is required."}
                )
        if self.estimated_cost_usd is not None and None in (
            self.input_tokens,
            self.output_tokens,
        ):
            raise ValidationError(
                {"estimated_cost_usd": "Cost requires measured input and output usage."}
            )

    def _validate_events(self) -> None:
        """Require body-free beat/details objects from the production trace.

        :return: None. Example: None for entry through exit events.
        :raises ValidationError: For invalid events or disallowed metadata.
        """
        invalid_trace = ValidationError(
            {"events": "Invalid contribution summary trace metadata."}
        )
        if not isinstance(self.events, list) or not self.events:
            raise invalid_trace
        for event in self.events:
            if not isinstance(event, dict) or event.keys() != {"beat", "details"}:
                raise invalid_trace
            beat = event["beat"]
            details = event["details"]
            if (
                not isinstance(beat, str)
                or beat not in _EVENT_FIELDS
                or not isinstance(details, str)
            ):
                raise invalid_trace
            fields = _EVENT_FIELDS[beat]
            seen: set[str] = set()
            for item in details.split(" "):
                key, separator, value = item.partition("=")
                if (
                    not separator
                    or key in seen
                    or key not in fields
                    or not re.fullmatch(fields[key], value)
                    or (
                        key in {"model", "correlation_id"} and _CREDENTIAL.search(value)
                    )
                ):
                    raise invalid_trace
                seen.add(key)
