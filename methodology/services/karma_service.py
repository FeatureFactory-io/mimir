from __future__ import annotations

from typing import Literal
from uuid import UUID
from django.contrib.auth.models import AnonymousUser, User
from methodology.models import Playbook

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

    @staticmethod
    def award_successful_consumption(
        actor: User | AnonymousUser,
        entity_type: str,
        entity_id: int,
        event_identity: UUID,
        *,
        channel: ConsumptionChannel,
    ) -> tuple[AwardOutcome, ...]:
        """Persist eligible learner/author awards after a successful operation.

        :param actor: Server-authenticated actor. Example: Maria.
        :param entity_type: Allowlisted entity kind. Example: "activity".
        :param entity_id: Positive entity identifier. Example: 6203.
        :param event_identity: Action identity retained across retries. Example: UUID4.
        :param channel: Trusted server operation kind. Example: "gui_copy".
        :return: Atomic pair or empty excluded outcome. Example: two AwardOutcome values.
        :raises ValueError: If identity, channel or entity input is invalid.
        :raises PermissionError: If existing access policy denies the target.
        """
        raise NotImplementedError()

    @staticmethod
    def _validate_consumption_input(
        entity_type: str,
        entity_id: int,
        event_identity: UUID,
        channel: ConsumptionChannel,
    ) -> None:
        """Validate bounded consumption inputs.

        :param entity_type: Existing allowlisted kind. Example: "activity".
        :param entity_id: Positive integer, excluding bool. Example: 6203.
        :param event_identity: Action UUID. Example: UUID4.
        :param channel: Trusted operation kind. Example: "gui_copy".
        :return: None on valid input.
        :raises ValueError: If any boundary input is invalid.
        """
        raise NotImplementedError()

    @staticmethod
    def _resolve_consumption_target(
        actor: User, entity_type: str, entity_id: int
    ) -> ConsumptionTarget:
        """Reload and authorize through existing entity services.

        :param actor: Authenticated service caller. Example: Maria.
        :param entity_type: Authorized entity kind. Example: "activity".
        :param entity_id: Target identifier. Example: 6203.
        :return: Target carrying its real playbook. Example: activity 6203/playbook 6201.
        :raises PermissionError: If the existing reader rejects access.
        :raises ObjectDoesNotExist: If the entity is absent.
        """
        raise NotImplementedError()

    @staticmethod
    def _consumption_exclusion(
        actor: User | AnonymousUser, target: ConsumptionTarget | None
    ) -> str | None:
        """Determine guest/self exclusion without assigning points.

        :param actor: Server actor. Example: Mike.
        :param target: Authorized target, or None for a guest. Example: activity 6203.
        :return: Exclusion reason or None. Example: "self_consumption".
        :raises ValueError: If an authenticated actor has no target.
        """
        raise NotImplementedError()

    @staticmethod
    def _canonical_consumption_identity(
        actor_id: int, event_identity: UUID, channel: ConsumptionChannel
    ) -> str:
        """Identify one action independently of its target.

        :param actor_id: Authenticated actor PK. Example: 42.
        :param event_identity: Retry-stable action UUID. Example: UUID(int=45).
        :param channel: Trusted operation. Example: "gui_copy".
        :return: Canonical key. Example: "consumption:gui_copy:42:<uuid>".
        :raises ValueError: Invalid actor, UUID, channel or resulting length.
        """
        raise NotImplementedError()

    @staticmethod
    def _build_consumption_specs(
        actor: User, target: ConsumptionTarget, canonical_identity: str
    ) -> tuple[AwardSpec, ...]:
        """Build the learner and author five-point immutable award specifications.

        :param actor: Authenticated learner. Example: Maria.
        :param target: Authorized target with real author/category. Example: Mike/Development.
        :param canonical_identity: Scoped stable ledger key. Example: "consumption:gui_copy:…".
        :return: Learning then Consumption specifications. Example: a two-item tuple.
        :raises ValueError: If attribution is missing or not recognized.
        """
        raise NotImplementedError()


ConsumptionChannel = Literal["gui_copy", "mcp_detail", "export"]


@dataclass(frozen=True)
class ConsumptionTarget:
    """Authorized entity and immutable attribution inputs."""

    entity_type: str
    entity_id: int
    playbook: Playbook
    pip_creator_id: int | None = None
