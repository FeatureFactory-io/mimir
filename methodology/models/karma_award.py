"""Persisted contribution awards with durable event-time content snapshots."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, router
from django.utils import timezone

from methodology.models.playbook import Playbook

logger = logging.getLogger(__name__)
CATEGORY_SLUGS = tuple(value for value, _label in Playbook.CATEGORY_CHOICES)


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
        constraints: ClassVar[list[models.BaseConstraint]] = [
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
        indexes: ClassVar[list[models.Index]] = [
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
        super().clean()
        if not isinstance(self.event_identity, str) or not self.event_identity.strip():
            raise ValidationError({"event_identity": "An event identity is required."})
        if self.source_kind not in self.SourceKind.values:
            raise ValidationError({"source_kind": "Unrecognized award source."})
        if self.category not in CATEGORY_SLUGS:
            raise ValidationError({"category": "Unrecognized playbook category."})

        for field, value, optional in (
            ("recipient", self.recipient_id, False),
            ("points", self.points, False),
            ("playbook_id_snapshot", self.playbook_id_snapshot, True),
            ("change_id_snapshot", self.change_id_snapshot, True),
        ):
            if optional and value is None:
                continue
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValidationError({field: "Enter a positive integer."})

        self._validate_entity_snapshot_pair()
        self._validate_channel_source()
        self._validate_release_identity()
        self._validate_occurred_at()
        self._validate_persisted_snapshot()

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save a valid new award without altering an existing event snapshot.

        :param args: Django save arguments. Example: ().
        :param kwargs: Django save options. Example: {"using": "default"}.
        :return: None. Example: None.
        :raises ValidationError: For invalid data or changed persisted fields.
        """
        # Field conversion can coerce booleans into integers.
        self.clean()
        self.clean_fields()

        using = (
            args[2] if len(args) > 2 else kwargs.get("using")
        ) or router.db_for_write(type(self), instance=self)
        # A fresh ORM instance may have an explicit PK. It must never update a row.
        if self._state.adding or using != self._state.db:
            if args:
                args = (True, *args[1:])
            else:
                kwargs["force_insert"] = True
        super().save(*args, **kwargs)

    def _validate_entity_snapshot_pair(self) -> None:
        """Require both entity fields together with positive ID and nonblank kind.

        :return: None. Example: None.
        :raises ValidationError: If one field is missing or invalid.
        """
        entity_type = self.entity_type_snapshot
        entity_id = self.entity_id_snapshot
        if entity_type is None and entity_id is None:
            return
        if not isinstance(entity_type, str) or not entity_type.strip():
            raise ValidationError(
                {"entity_type_snapshot": "Enter a nonblank entity type."}
            )
        if (
            not isinstance(entity_id, int)
            or isinstance(entity_id, bool)
            or entity_id <= 0
        ):
            raise ValidationError({"entity_id_snapshot": "Enter a positive entity ID."})

    def _validate_channel_source(self) -> None:
        """Validate explicit channel/source combinations independently of keys.

        :return: None. Example: None.
        :raises ValidationError: For an unsupported channel/source combination.
        """
        if self.event_channel == EventChannel.HISTORICAL:
            return
        content_channels = (
            EventChannel.GUI_COPY,
            EventChannel.MCP_DETAIL,
            EventChannel.EXPORT,
        )
        allowed_channels = {
            self.SourceKind.RELEASE: (EventChannel.RELEASE,),
            self.SourceKind.MAJOR: (EventChannel.ACCEPTED_CHANGE,),
            self.SourceKind.MINOR: (EventChannel.ACCEPTED_CHANGE,),
            self.SourceKind.CONSUMPTION: content_channels,
            self.SourceKind.LEARNING: content_channels,
        }
        if self.event_channel not in allowed_channels[self.source_kind]:
            raise ValidationError(
                {"event_channel": "Channel is incompatible with the award source."}
            )

    def _validate_release_identity(self) -> None:
        """Require canonical identity for known books and live release references.

        :return: None. Example: None.
        :raises ValidationError: For a live missing book or mismatched known key.
        """
        if self.source_kind != self.SourceKind.RELEASE:
            return
        if self.playbook_id_snapshot is None:
            if self.event_channel != EventChannel.HISTORICAL:
                raise ValidationError(
                    {"playbook_id_snapshot": "Live releases require a playbook ID."}
                )
            return
        if self.event_identity != first_release_identity(self.playbook_id_snapshot):
            raise ValidationError(
                {"event_identity": "The release identity must match its playbook ID."}
            )

    def _validate_occurred_at(self) -> None:
        """Require an explicit timezone-aware original event timestamp.

        :return: None. Example: None.
        :raises ValidationError: For a missing or naive event time.
        """
        if not isinstance(self.occurred_at, datetime) or timezone.is_naive(
            self.occurred_at
        ):
            raise ValidationError(
                {"occurred_at": "Enter the original event time with a time zone."}
            )

    def _validate_persisted_snapshot(self) -> None:
        """Reject changes to stored event identity, time or logical award fields.

        :return: None. Example: None.
        :raises ValidationError: If an existing snapshot would change.
        """
        if self._state.adding or self.pk is None:
            return

        stored = (
            type(self)
            ._base_manager.using(self._state.db)
            .filter(pk=self.pk)
            .values()
            .first()
        )
        if stored is None:
            return
        for field in self._meta.concrete_fields:
            if field.primary_key:
                continue
            current = getattr(self, field.attname)
            if field.name == "occurred_at":
                current = current.astimezone(UTC)
            if current != stored[field.attname]:
                logger.debug(
                    "KarmaAward.clean | validation | rejected=immutable_snapshot award_id=%s field=%s",
                    self.pk,
                    field.name,
                )
                raise ValidationError(
                    {field.name: "A persisted award cannot be changed."}
                )


def first_release_identity(playbook_id: int) -> str:
    """Build the shared canonical identity for a known playbook's first release.

    :param playbook_id: Real positive playbook PK. Example: 6101.
    :return: Canonical identity. Example: "first_release:6101".
    :raises ValueError: For a noninteger, boolean or nonpositive identifier.
    """
    if (
        not isinstance(playbook_id, int)
        or isinstance(playbook_id, bool)
        or playbook_id <= 0
    ):
        raise ValueError("Playbook ID must be a positive integer.")
    return f"first_release:{playbook_id}"
