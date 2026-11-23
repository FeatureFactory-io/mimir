"""Stored public contribution prose; numeric values remain live projections."""

from __future__ import annotations

from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

_INVALID_SUMMARY = "Invalid last good summary."


class ExpertProfile(models.Model):
    """Last good public paragraph and refresh metadata for one account."""

    class SummaryStatus(models.TextChoices):
        NEVER = ("never", "Never refreshed")
        SUCCESS = ("success", "Successful")
        FAILURE = ("failure", "Failed")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="expert_profile",
    )
    contribution_summary = models.TextField(blank=True, default="")
    summary_updated_at = models.DateTimeField(null=True, blank=True)
    summary_status = models.CharField(
        max_length=20, choices=SummaryStatus.choices, default=SummaryStatus.NEVER
    )
    summary_error_code = models.CharField(max_length=100, blank=True, default="")
    last_summary_correlation_id = models.CharField(
        max_length=100, blank=True, default=""
    )

    def clean(self) -> None:
        """Validate summary metadata without changing last good prose.

        :return: None. Example: None.
        :raises ValidationError: For inconsistent metadata or invalid field values.
        """
        super().clean()
        status = self.summary_status
        statuses = self.SummaryStatus
        if status not in statuses.values:
            raise ValidationError({"summary_status": "Unrecognized summary status."})
        updated_at = self.summary_updated_at
        if updated_at is None and status == statuses.SUCCESS:
            raise ValidationError({"summary_updated_at": "Missing success timestamp."})
        if updated_at is not None and (
            status == statuses.NEVER
            or not isinstance(updated_at, datetime)
            or timezone.is_naive(updated_at)
        ):
            raise ValidationError({"summary_updated_at": "Invalid refresh timestamp."})
        summary = self.contribution_summary
        if not isinstance(summary, str) or (
            updated_at is not None and not summary.strip()
        ):
            raise ValidationError({"contribution_summary": _INVALID_SUMMARY})

        for field_name, required in (
            ("summary_error_code", status == statuses.FAILURE),
            ("last_summary_correlation_id", status != statuses.NEVER),
        ):
            value = getattr(self, field_name)
            max_length = self._meta.get_field(field_name).max_length
            if not isinstance(value, str) or len(value) > max_length:
                raise ValidationError({field_name: "Invalid refresh metadata."})
            if (required and not value.strip()) or (not required and value):
                raise ValidationError({field_name: "Metadata does not match status."})
