"""Stored public contribution prose; numeric values remain live projections."""

from __future__ import annotations

from django.conf import settings
from django.db import models


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
        raise NotImplementedError()
