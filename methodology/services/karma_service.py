from __future__ import annotations

"""Immutable contribution award commands shared by Django domain services."""
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser
    from methodology.models import KarmaAward, Playbook, PlaybookVersion
KarmaSource = Literal["release", "major", "minor", "consumption", "learning"]
FIRST_RELEASE_POINTS = 5000


@dataclass(frozen=True)
class AwardSpec:
    """Describe one immutable ledger write.

    :param recipient_id: Persisted user ID. Example: 42.
    :param source_kind: Recognized award source. Example: "release".
    :param points: Positive integer amount. Example: 5000.
    :param category: Canonical event-time category. Example: "product".
    :param event_identity: Stable event key. Example: "first_release:6302".
    :param playbook_id_snapshot: Durable playbook reference. Example: 6302.
    :param change_id_snapshot: Optional accepted-change reference. Example: None.
    :param occurred_at: Original event time. Example: release_version.created_at.
    """

    recipient_id: int
    source_kind: KarmaSource
    points: int
    category: str
    event_identity: str
    playbook_id_snapshot: int | None
    change_id_snapshot: int | None
    occurred_at: datetime
    event_channel: str
    entity_type_snapshot: str | None
    entity_id_snapshot: int | None


@dataclass(frozen=True)
class AwardOutcome:
    """Report persistence without conflating an existing award with a new one.

    :param award: Persisted award or no eligible award. Example: KarmaAward(pk=9).
    :param created: Whether this operation inserted the award. Example: True.
    :param reason: Stable outcome reason. Example: "created".
    """

    award: KarmaAward | None
    created: bool
    reason: str


class KarmaService:
    """Validate immutable award specifications and persist them atomically."""

    @staticmethod
    def first_release_identity(playbook_id: int) -> str:
        """Build a first-release identity independent of version and actor.

        :param playbook_id: Positive persisted playbook ID. Example: 6302.
        :return: Stable event identity. Example: "first_release:6302".
        :raises ValueError: If the ID is not a positive non-Boolean integer.
        """
        raise NotImplementedError()

    @staticmethod
    def award_first_release(
        playbook: Playbook,
        release_version: PlaybookVersion,
        actor: AbstractBaseUser,
        *,
        correlation_id: str,
    ) -> AwardOutcome:
        """Award the author for an eligible, persisted first-release receipt.

        Called only by the successful domain publication path, inside its
        transaction. Validate actor ownership and receipt association/source.
        Later-major receipts return an ineligible outcome. Replaying a valid
        first receipt returns its existing award without a second write.

        :param playbook: Persisted released playbook. Example: Playbook(pk=6302).
        :param release_version: Publication receipt. Example: version 1.0.
        :param actor: Authenticated author. Example: Nora.
        :param correlation_id: Safe request/run identifier. Example: "release-01".
        :return: Award result. Example: AwardOutcome(award, True, "created").
        :raises PermissionError: If actor does not own the playbook.
        :raises ValidationError: If the receipt or award payload is invalid.
        """
        raise NotImplementedError()

    @staticmethod
    def persist_awards(
        specifications: tuple[AwardSpec, ...], *, correlation_id: str
    ) -> tuple[AwardOutcome, ...]:
        """Validate an entire batch before writing it in one transaction.

        Empty batches return an empty tuple. Preserve order. Nested use joins
        the caller's successful transaction. Existing identities must retain
        identical immutable payloads; unexpected database errors propagate.

        :param specifications: Immutable batch. Example: (release_spec,).
        :param correlation_id: Safe request/run ID. Example: "release-01".
        :return: Results in input order. Example: (AwardOutcome(row, True, "created"),).
        :raises ValidationError: If a payload is invalid or conflicts.
        :raises IntegrityError: If an unrelated database constraint fails.
        """
        raise NotImplementedError()

    @staticmethod
    def _validate_batch(
        specifications: tuple[AwardSpec, ...], correlation_id: str
    ) -> None:
        """Validate batch type, trace identifier and duplicate recipients.

        :param specifications: Candidate immutable batch. Example: (spec,).
        :param correlation_id: Safe trace ID. Example: "release-01".
        :return: None when every item can be validated.
        :raises ValidationError: If input or duplicate event payloads conflict.
        """
        raise NotImplementedError()

    @staticmethod
    def _validate_specification(specification: AwardSpec) -> None:
        """Validate positive points, canonical source/category and references.

        :param specification: Candidate award. Example: a 5000-point Product release.
        :return: None for a valid specification.
        :raises ValidationError: If an amount, kind, category or ID is invalid.
        """
        raise NotImplementedError()

    @staticmethod
    def _validate_release_receipt(
        playbook: Playbook, release_version: PlaybookVersion, actor: AbstractBaseUser
    ) -> bool:
        """Validate ownership/association and identify an eligible first receipt.

        :param playbook: Released target. Example: playbook 6302.
        :param release_version: Persisted release receipt. Example: v1.0.
        :param actor: Acting owner. Example: Nora.
        :return: Whether this is a first-major publication receipt. Example: True.
        :raises PermissionError: If actor is not the author.
        :raises ValidationError: If receipt association or state is invalid.
        """
        raise NotImplementedError()

    @staticmethod
    def _first_release_specification(
        playbook: Playbook, release_version: PlaybookVersion
    ) -> AwardSpec:
        """Snapshot author, category, stable identity and receipt timestamp.

        :param playbook: Validated released target. Example: playbook 6302.
        :param release_version: Validated first receipt. Example: v1.0.
        :return: Immutable award input. Example: Product release worth 5000.
        :raises ValidationError: If the snapshot cannot be represented.
        """
        raise NotImplementedError()

    @staticmethod
    def _insert_or_get_award(specification: AwardSpec) -> AwardOutcome:
        """Use database uniqueness to insert once or retrieve the same award.

        Handle an expected uniqueness race inside an appropriate savepoint;
        do not swallow other database failures or leave a transaction broken.

        :param specification: Validated immutable award. Example: release_spec.
        :return: Created/existing result. Example: AwardOutcome(row, False, "duplicate").
        :raises ValidationError: If an existing immutable payload differs.
        :raises IntegrityError: For unrelated database constraints.
        """
        raise NotImplementedError()

    @staticmethod
    def _assert_matching_payload(award: KarmaAward, specification: AwardSpec) -> None:
        """Reject identity reuse that would change immutable award meaning.

        :param award: Existing ledger row. Example: first_release:6302 for Nora.
        :param specification: Requested payload. Example: the same release_spec.
        :return: None when immutable values agree.
        :raises ValidationError: If recipient, points or attribution conflicts.
        """
        raise NotImplementedError()
