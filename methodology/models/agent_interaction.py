from __future__ import annotations

"""CAP-101 metadata for summary attempts; never store model bodies."""
import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


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
    workflow_id = models.CharField(
        max_length=64, default="contribution_summary", editable=False
    )
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
        ordering = ["created_at", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(latency_ms__gte=Decimal("0")),
                name="summary_interaction_latency_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(estimated_cost_usd__isnull=True)
                | models.Q(estimated_cost_usd__gte=Decimal("0")),
                name="summary_interaction_cost_nonnegative",
            ),
        ]

    def clean(self) -> None:
        """Validate safe metadata before persistence.

        :return: None. Example: None for a valid success record.
        :raises ValidationError: For invalid identifiers, usage or trace.
        """
        raise NotImplementedError()

    def _validate_identifiers(self) -> None:
        """Require safe bounded correlation, model and workflow identifiers.

        :return: None. Example: None for correlation_id="cedar-submit-01".
        :raises ValidationError: For missing or unsafe identifiers.
        """
        raise NotImplementedError()

    def _validate_measurements(self) -> None:
        """Reject negative/nonfinite measurements and invented missing usage.

        :return: None. Example: None with unknown tokens and null cost.
        :raises ValidationError: For invalid tokens, latency or cost.
        """
        raise NotImplementedError()

    def _validate_events(self) -> None:
        """Require body-free beat/details objects from the production trace.

        :return: None. Example: None for entry through exit events.
        :raises ValidationError: For invalid events or disallowed metadata.
        """
        raise NotImplementedError()
