"""Persisted contribution awards with durable event-time content snapshots."""

from __future__ import annotations

from typing import Any
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from methodology.models.playbook import Playbook


class EventChannel(models.TextChoices):
    """Explicit provenance; never infer a channel from an identity string."""

    HISTORICAL = ("historical", "Historical import")
    RELEASE = ("release", "Release")
    ACCEPTED_CHANGE = ("accepted_change", "PIP decision")
    GUI_COPY = ("gui_copy", "GUI copy")
    MCP_DETAIL = ("mcp_detail", "MCP detail")
    EXPORT = ("export", "Export")


class KarmaAward(models.Model):
    """One immutable positive award; content snapshots do not prevent deletion."""

    class SourceKind(models.TextChoices):
        RELEASE = ("release", "Released playbook")
        MAJOR = ("major", "Major accepted change")
        MINOR = ("minor", "Minor accepted change")
        CONSUMPTION = ("consumption", "Content consumed")
        LEARNING = ("learning", "Learning")

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="karma_awards"
    )
    event_identity = models.CharField(max_length=255)
    source_kind = models.CharField(max_length=20, choices=SourceKind.choices)
    event_channel = models.CharField(max_length=20, choices=EventChannel.choices)
    points = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    category = models.CharField(max_length=50, choices=Playbook.CATEGORY_CHOICES)
    playbook_id_snapshot = models.PositiveBigIntegerField(null=True, blank=True)
    change_id_snapshot = models.PositiveBigIntegerField(null=True, blank=True)
    entity_type_snapshot = models.CharField(max_length=32, null=True, blank=True)
    entity_id_snapshot = models.PositiveBigIntegerField(null=True, blank=True)
    occurred_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event_identity", "recipient"],
                name="karma_unique_event_recipient",
            ),
            models.UniqueConstraint(
                fields=["playbook_id_snapshot"],
                condition=models.Q(source_kind="release")
                & models.Q(playbook_id_snapshot__isnull=False),
                name="karma_unique_first_release",
            ),
            models.UniqueConstraint(
                fields=["event_identity"],
                condition=models.Q(
                    source_kind__in=("release", "major", "minor", "learning")
                )
                & ~models.Q(event_channel="historical"),
                name="karma_live_event_anchor_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(points__gt=0), name="karma_points_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    entity_type_snapshot__isnull=True, entity_id_snapshot__isnull=True
                )
                | models.Q(
                    entity_type_snapshot__isnull=False,
                    entity_id_snapshot__isnull=False,
                    entity_id_snapshot__gt=0,
                )
                & ~models.Q(entity_type_snapshot=""),
                name="karma_entity_snapshot_pair",
            ),
            models.CheckConstraint(
                condition=models.Q(playbook_id_snapshot__isnull=True)
                | models.Q(playbook_id_snapshot__gt=0),
                name="karma_playbook_snapshot_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(change_id_snapshot__isnull=True)
                | models.Q(change_id_snapshot__gt=0),
                name="karma_change_snapshot_positive",
            ),
            models.CheckConstraint(
                condition=~models.Q(source_kind="release")
                | models.Q(event_channel="historical")
                | models.Q(playbook_id_snapshot__isnull=False),
                name="karma_live_release_has_book",
            ),
            models.CheckConstraint(
                condition=models.Q(event_channel="historical")
                | models.Q(event_channel="release", source_kind="release")
                | models.Q(
                    event_channel="accepted_change", source_kind__in=("major", "minor")
                )
                | models.Q(
                    event_channel__in=("gui_copy", "mcp_detail", "export"),
                    source_kind__in=("consumption", "learning"),
                ),
                name="karma_channel_source_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=["recipient", "category"], name="karma_recipient_category"
            ),
            models.Index(
                fields=["recipient", "source_kind", "event_channel"],
                name="karma_recipient_source_channel",
            ),
        ]

    def clean(self) -> None:
        """Validate recognized values, paired snapshots and event-time semantics.

        :return: None. Example: None.
        :raises ValidationError: For invalid source, channel, amount or snapshots.
        """
        raise NotImplementedError()

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save a valid new award without altering an existing event snapshot.

        :param args: Django save arguments. Example: ().
        :param kwargs: Django save options. Example: {"using": "default"}.
        :return: None. Example: None.
        :raises ValidationError: For invalid data or changed persisted fields.
        """
        raise NotImplementedError()

    def _validate_entity_snapshot_pair(self) -> None:
        """Require both entity fields together with positive ID and nonblank kind.

        :return: None. Example: None.
        :raises ValidationError: If one field is missing or invalid.
        """
        raise NotImplementedError()

    def _validate_channel_source(self) -> None:
        """Validate explicit channel/source combinations independently of keys.

        :return: None. Example: None.
        :raises ValidationError: For an unsupported channel/source combination.
        """
        raise NotImplementedError()

    def _validate_release_identity(self) -> None:
        """Require canonical identity for known books and live release references.

        :return: None. Example: None.
        :raises ValidationError: For a live missing book or mismatched known key.
        """
        raise NotImplementedError()

    def _validate_occurred_at(self) -> None:
        """Require an explicit timezone-aware original event timestamp.

        :return: None. Example: None.
        :raises ValidationError: For a missing or naive event time.
        """
        raise NotImplementedError()

    def _validate_persisted_snapshot(self) -> None:
        """Reject changes to stored event identity, time or logical award fields.

        :return: None. Example: None.
        :raises ValidationError: If an existing snapshot would change.
        """
        raise NotImplementedError()


def first_release_identity(playbook_id: int) -> str:
    """Build the shared canonical identity for a known playbook's first release.

    :param playbook_id: Real positive playbook PK. Example: 6101.
    :return: Canonical identity. Example: "first_release:6101".
    :raises ValueError: For a noninteger, boolean or nonpositive identifier.
    """
    raise NotImplementedError()
