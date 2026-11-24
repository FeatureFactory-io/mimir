"""Immutable contribution award commands shared by Django domain services."""

from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser, User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from methodology.models import (
    EventChannel,
    KarmaAward,
    PipChange,
    Playbook,
    PlaybookVersion,
    ProcessImprovementProposal,
    VersionSource,
)
from methodology.models.karma_award import CATEGORY_SLUGS, first_release_identity
from methodology.services.pip_link_service import relationship_endpoint_types

if TYPE_CHECKING:
    from django.db import OperationalError

logger = logging.getLogger(__name__)
KarmaSource = Literal["release", "major", "minor", "consumption", "learning"]
FIRST_RELEASE_POINTS = 5000
FIRST_RELEASE_VERSION = Decimal("1.0")
AWARD_CORRELATION_ID = re.compile(r"[A-Za-z0-9._:-]{1,100}")

_RELEASE_LOG = "KarmaService.award_first_release"
_PERSIST_LOG = "KarmaService.persist_awards"
_ACCEPTED_CHANGE_LOG = "KarmaService.award_accepted_changes"
_ACCEPTED_POLICY_LOG = "KarmaService._accepted_change_policy"
_ACCEPTED_MAJOR_POINTS = 500
_ACCEPTED_MINOR_POINTS = 100
_VERSION_NUMBER = re.compile(r"[0-9]{1,4}\.[0-9]")
_MAJOR_ADD_ENTITIES = frozenset(
    {PipChange.ENTITY_ACTIVITY, PipChange.ENTITY_SKILL, PipChange.ENTITY_ARTIFACT}
)
_MINOR_ADD_ENTITIES = frozenset(
    {
        PipChange.ENTITY_WORKFLOW,
        PipChange.ENTITY_PHASE,
        PipChange.ENTITY_AGENT,
        PipChange.ENTITY_RULE,
    }
)
_EDITABLE_ENTITIES = _MAJOR_ADD_ENTITIES | _MINOR_ADD_ENTITIES
_RELATIONSHIP_OPERATIONS = frozenset({PipChange.CHANGE_LINK, PipChange.CHANGE_UNLINK})
_ACCEPTED_STATES = (
    ProcessImprovementProposal.STATUS_ACCEPTED,
    ProcessImprovementProposal.STATUS_ACCEPTED_PARTIAL,
)
_FIRST_RELEASE_POLICY = f"source_kind=release points={FIRST_RELEASE_POINTS}"
_PAIRED_SOURCES = (KarmaAward.SourceKind.CONSUMPTION, KarmaAward.SourceKind.LEARNING)
_AWARD_IDENTITY_COLLISIONS = frozenset(
    {
        ("23505", "karma_unique_event_recipient"),
        ("23505", "karma_unique_first_release"),
        ("23505", "karma_live_event_anchor_unique"),
        (
            sqlite3.SQLITE_CONSTRAINT_UNIQUE,
            "methodology_karmaaward.event_identity, methodology_karmaaward.recipient_id",
        ),
        (
            sqlite3.SQLITE_CONSTRAINT_UNIQUE,
            "methodology_karmaaward.playbook_id_snapshot",
        ),
        (sqlite3.SQLITE_CONSTRAINT_UNIQUE, "methodology_karmaaward.event_identity"),
    }
)
_SQLITE_UNIQUE_PREFIX = "UNIQUE constraint failed: "
_CONSUMPTION_LOG = "KarmaService.award_successful_consumption"
_CONSUMPTION_POINTS = 5
_CONSUMPTION_CHANNELS = (
    EventChannel.GUI_COPY,
    EventChannel.MCP_DETAIL,
    EventChannel.EXPORT,
)
MAX_CONSUMPTION_ENTITY_ID = (1 << 63) - 1
GUI_COPY_ENTITY_TYPES = frozenset(
    {"activity", "agent", "artifact", "pip", "rule", "skill"}
)
# Reader services depend on PlaybookService, which imports this writer for releases.
_CONSUMPTION_READERS = {
    "activity": ("activity_service.ActivityService", "get_activity_for_user"),
    "agent": ("agent_service.AgentService", "get_agent_for_user"),
    "artifact": ("artifact_service.ArtifactService", "get_artifact_for_user"),
    "phase": ("phase_service.PhaseService", "get_phase_for_user"),
    "pip": ("pip_service.PIPService", "get_pip"),
    "playbook": ("playbook_service.PlaybookService", "get_playbook"),
    "rule": ("rule_service.RuleService", "get_rule_for_user"),
    "skill": ("skill_service.SkillService", "get_skill_for_user"),
    "workflow": ("workflow_service.WorkflowService", "get_workflow_for_user"),
}


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
    :param event_channel: Trusted event origin. Example: "release".
    :param entity_type_snapshot: Optional content kind. Example: None.
    :param entity_id_snapshot: Optional durable content reference. Example: None.
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
        return first_release_identity(playbook_id)

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
        KarmaService._validate_batch((), correlation_id)
        if (
            not isinstance(release_version, PlaybookVersion)
            or release_version._state.adding
        ):
            raise ValidationError("A persisted publication receipt is required.")
        receipt = PlaybookVersion.objects.filter(pk=release_version.pk).first()
        if receipt is None:
            raise ValidationError("A persisted publication receipt is required.")
        if not KarmaService._validate_release_receipt(playbook, receipt, actor):
            return AwardOutcome(None, False, "previously_released")

        spec = KarmaService._first_release_specification(playbook, receipt)
        trace = f"correlation_id={correlation_id}"
        logger.info("%s | config | %s %s", _RELEASE_LOG, _FIRST_RELEASE_POLICY, trace)
        (outcome,) = KarmaService.persist_awards((spec,), correlation_id=correlation_id)
        if not outcome.created:
            result = f"event_identity={spec.event_identity} created=false additional_points=0"
            logger.info("%s | branch | %s %s", _RELEASE_LOG, result, trace)
        recipient = f"recipient_id={spec.recipient_id} category={spec.category}"
        points = spec.points if outcome.created else 0
        result = f"created={str(outcome.created).lower()} points={points}"
        logger.info("%s | exit | %s %s %s", _RELEASE_LOG, recipient, result, trace)
        return outcome

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
        KarmaService._validate_batch(specifications, correlation_id)
        logger.info(
            "%s | entry | award_count=%s correlation_id=%s",
            _PERSIST_LOG,
            len(specifications),
            correlation_id,
        )
        with transaction.atomic():
            outcomes = tuple(
                KarmaService._insert_or_get_award(spec) for spec in specifications
            )
            logger.info(
                "%s | exit | award_count=%s created_count=%s transaction=pending correlation_id=%s",
                _PERSIST_LOG,
                len(outcomes),
                sum(outcome.created for outcome in outcomes),
                correlation_id,
            )
            return outcomes

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
        if not isinstance(correlation_id, str) or not AWARD_CORRELATION_ID.fullmatch(
            correlation_id
        ):
            raise ValidationError("A safe award correlation ID is required.")
        if not isinstance(specifications, tuple):
            raise ValidationError(
                "An immutable tuple of award specifications is required."
            )
        seen: dict[str, list[AwardSpec]] = {}
        for spec in specifications:
            KarmaService._validate_specification(spec)
            prior_specs = seen.setdefault(spec.event_identity, [])
            if any(
                prior.recipient_id == spec.recipient_id
                or prior.source_kind not in _PAIRED_SOURCES
                or spec.source_kind not in _PAIRED_SOURCES
                for prior in prior_specs
            ):
                raise ValidationError(
                    "Award event has conflicting recipients.",
                    code="award_recipient_conflict",
                )
            prior_specs.append(spec)

    @staticmethod
    def _validate_specification(specification: AwardSpec) -> None:
        """Validate positive points, canonical source/category and references.

        :param specification: Candidate award. Example: a 5000-point Product release.
        :return: None for a valid specification.
        :raises ValidationError: If an amount, kind, category or ID is invalid.
        """
        if not isinstance(specification, AwardSpec):
            raise ValidationError("A valid award specification is required.")
        award = KarmaAward(**asdict(specification))
        award.clean()
        award.clean_fields()
        if award.event_channel == EventChannel.RELEASE and (
            award.points != FIRST_RELEASE_POINTS
            or award.change_id_snapshot is not None
            or award.entity_type_snapshot is not None
        ):
            raise ValidationError("Invalid first-release award amount or snapshots.")

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
        if not isinstance(playbook, Playbook) or playbook._state.adding:
            raise ValidationError("A persisted released playbook is required.")
        if not isinstance(actor, AbstractBaseUser) or actor.pk != playbook.author_id:
            raise PermissionError(
                "You don't have permission to award this playbook's release."
            )
        if not Playbook.objects.filter(
            pk=playbook.pk, status="released", author_id=actor.pk
        ).exists():
            raise ValidationError(
                "A released playbook with the original author is required."
            )
        if (
            release_version.playbook_id != playbook.pk
            or release_version.created_by_id != actor.pk
            or release_version.source != VersionSource.RELEASE
            or not release_version.is_major
        ):
            raise ValidationError(
                "The publication receipt must match the playbook and its author."
            )
        if release_version.version_number != FIRST_RELEASE_VERSION:
            return False
        snapshot = release_version.snapshot_data
        before = snapshot.get("before_release") if isinstance(snapshot, dict) else None
        if not isinstance(before, dict) or before.get("status") != "draft":
            raise ValidationError(
                "The first publication receipt must record the prior draft."
            )
        return True

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
        category = release_version.snapshot_data.get("category")
        if category not in CATEGORY_SLUGS:
            raise ValidationError("The release receipt lacks a recognized category.")
        return AwardSpec(
            recipient_id=playbook.author_id,
            source_kind="release",
            points=FIRST_RELEASE_POINTS,
            category=category,
            event_identity=KarmaService.first_release_identity(playbook.pk),
            playbook_id_snapshot=playbook.pk,
            change_id_snapshot=None,
            occurred_at=release_version.created_at,
            event_channel=EventChannel.RELEASE,
            entity_type_snapshot=None,
            entity_id_snapshot=None,
        )

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
        rows = KarmaAward.objects.filter(event_identity=specification.event_identity)
        if specification.source_kind in _PAIRED_SOURCES:
            rows = rows.filter(recipient_id=specification.recipient_id)
        existing = list(rows[:2])
        if not existing:
            try:
                with transaction.atomic():
                    award = KarmaAward.objects.create(**asdict(specification))
            except IntegrityError as error:
                cause = error.__cause__
                sqlstate = getattr(cause, "sqlstate", None)
                diagnostics = getattr(cause, "diag", None)
                postgres_key = sqlstate, getattr(diagnostics, "constraint_name", None)
                sqlite_code = getattr(cause, "sqlite_errorcode", None)
                sqlite_key = sqlite_code, str(cause).removeprefix(_SQLITE_UNIQUE_PREFIX)
                if _AWARD_IDENTITY_COLLISIONS.isdisjoint((postgres_key, sqlite_key)):
                    raise
                existing = list(rows[:2])
                if not existing:
                    raise
            else:
                return AwardOutcome(award, True, "created")
        if len(existing) != 1:
            raise ValidationError(
                "Award event identity matches multiple existing awards."
            )
        KarmaService._assert_matching_payload(existing[0], specification)
        return AwardOutcome(existing[0], False, "duplicate")

    @staticmethod
    def _assert_matching_payload(award: KarmaAward, specification: AwardSpec) -> None:
        """Reject identity reuse that would change immutable award meaning.

        :param award: Existing ledger row. Example: first_release:6302 for Nora.
        :param specification: Requested payload. Example: the same release_spec.
        :return: None when logical values agree; retain the stored original time.
        :raises ValidationError: If recipient, points or attribution conflicts.
        """
        requested = asdict(specification)
        requested.pop("occurred_at")
        if any(getattr(award, field) != value for field, value in requested.items()):
            raise ValidationError(
                "Award event identity conflicts with its recorded payload.",
                code="award_payload_conflict",
            )

    @staticmethod
    @transaction.atomic
    def award_successful_consumption(
        actor: User | AnonymousUser,
        entity_type: str,
        entity_id: int,
        event_identity: UUID,
        *,
        channel: ConsumptionChannel,
    ) -> tuple[AwardOutcome, ...]:
        """Persist eligible learner/author awards after a successful operation.

        Check existing recipients before delegating row comparison and writes.

        :param actor: Server-authenticated actor. Example: Maria.
        :param entity_type: Allowlisted entity kind. Example: "activity".
        :param entity_id: Positive entity identifier. Example: 6203.
        :param event_identity: Action identity retained across retries. Example: UUID4.
        :param channel: Trusted server operation kind. Example: "gui_copy".
        :return: Atomic pair or empty excluded outcome. Example: two AwardOutcome values.
        :raises ValueError: If identity, channel or entity input is invalid.
        :raises PermissionError: If existing access policy denies the target.
        :raises ObjectDoesNotExist: If the authenticated actor's target no longer exists.
        :raises ValidationError: If the action key conflicts with immutable evidence.
        """
        service = KarmaService
        validate_input = service._validate_consumption_input
        validate_input(entity_type, entity_id, event_identity, channel)
        operation = _CONSUMPTION_LOG
        trace = f"channel={channel} action_uuid={event_identity}"
        if isinstance(actor, AnonymousUser):
            service._consumption_exclusion(actor, None, None, trace=trace)
            return ()
        target = service._resolve_consumption_target(actor, entity_type, entity_id)
        canonical_id = service._canonical_consumption_identity
        identity = canonical_id(actor.pk, event_identity, channel)
        trace += f" actor_id={actor.pk} playbook_id={target.playbook.pk}"
        logger.info(f"{operation} | validation | {trace} authorized")
        if service._consumption_exclusion(actor, target, identity, trace=trace):
            return ()
        build_specs = service._build_consumption_specs
        specs = build_specs(actor, target, identity, channel=channel)
        outcomes = service.persist_awards(specs, correlation_id=identity)
        award = outcomes[0].award
        assert award is not None
        status = "applied" if outcomes[0].created else "replayed"
        recipients = f"learner_id={actor.pk} author_id={specs[1].recipient_id}"
        details = f"{recipients} points={_CONSUMPTION_POINTS} status={status}"
        event = f"event_identity={identity}"
        logger.info(f"{operation} | processing | {event} {details}")
        created = sum(outcome.created for outcome in outcomes)
        result = f"created_count={created}" if created else "duplicate"
        timestamp = f"occurred_at={award.occurred_at.isoformat()}"
        logger.info(f"{operation} | exit | {event} {result} {timestamp}")
        return outcomes

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
        if not isinstance(entity_type, str) or entity_type not in _CONSUMPTION_READERS:
            raise ValueError("Unsupported consumption entity type.")
        if type(entity_id) is not int or not 0 < entity_id <= MAX_CONSUMPTION_ENTITY_ID:
            raise ValueError("A positive consumption entity ID is required.")
        if not isinstance(event_identity, UUID) or channel not in _CONSUMPTION_CHANNELS:
            raise ValueError("A consumption UUID and recognized channel are required.")

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
        if not isinstance(actor, User) or actor._state.adding or not actor.is_active:
            raise PermissionError("An active persisted consumption actor is required.")
        service_path, reader_name = _CONSUMPTION_READERS[entity_type]
        service = import_string(f"methodology.services.{service_path}")
        entity = getattr(service, reader_name)(entity_id, actor)
        if entity_type == "playbook":
            return ConsumptionTarget(entity_type, entity_id, entity)
        if entity_type == "activity":
            return ConsumptionTarget(entity_type, entity_id, entity.workflow.playbook)
        creator_id = entity.created_by_id if entity_type == "pip" else None
        return ConsumptionTarget(entity_type, entity_id, entity.playbook, creator_id)

    @staticmethod
    def _consumption_exclusion(
        actor: User | AnonymousUser,
        target: ConsumptionTarget | None,
        canonical_identity: str | None,
        *,
        trace: str,
    ) -> str | None:
        """Revalidate attribution and existing recipients, then report eligibility.

        :param actor: Server actor. Example: Mike.
        :param target: Authorized target, or None for a guest. Example: activity 6203.
        :param canonical_identity: Scoped ledger key, or None for a guest.
        :param trace: Validated action and actor context. Example: "channel=gui_copy …".
        :return: Exclusion reason or None. Example: "self_consumption".
        :raises ValueError: If an authenticated actor has no target or event key.
        :raises ValidationError: If attribution is invalid or existing recipients conflict.
        """
        operation = _CONSUMPTION_LOG
        if isinstance(actor, AnonymousUser):
            logger.info(f"{operation} | branch | {trace} reason=guest awards=0")
            return "guest"
        if target is None or canonical_identity is None:
            raise ValueError("An authorized target and event key are required.")
        book = target.playbook
        is_self = actor.pk in (book.author_id, target.pip_creator_id)
        if not is_self and (
            book.author_id is None or book.category not in CATEGORY_SLUGS
        ):
            raise ValidationError("Consumption target has invalid award attribution.")
        rows = KarmaAward.objects.filter(event_identity=canonical_identity)
        existing = set(rows.values_list("recipient_id", flat=True))
        expected = set() if is_self else {actor.pk, book.author_id}
        if existing and existing != expected:
            raise ValidationError("Event conflict.", code="award_payload_conflict")
        if is_self:
            logger.info(
                f"{operation} | branch | {trace} author_id={book.author_id} "
                "reason=self_consumption awards=0"
            )
            return "self_consumption"
        attribution = f"author_id={book.author_id} category={book.category}"
        event = f"event_identity={canonical_identity}"
        logger.info(
            f"{operation} | branch | {trace} {event} {attribution} reason=eligible"
        )
        return None

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
        if type(actor_id) is not int or not 0 < actor_id <= MAX_CONSUMPTION_ENTITY_ID:
            raise ValueError("A positive consumption actor ID is required.")
        if not isinstance(event_identity, UUID) or channel not in _CONSUMPTION_CHANNELS:
            raise ValueError("A consumption UUID and recognized channel are required.")
        identity = f"consumption:{channel}:{actor_id}:{event_identity}"
        if not AWARD_CORRELATION_ID.fullmatch(identity):
            raise ValueError("The consumption identity is too long.")
        return identity

    @staticmethod
    def _build_consumption_specs(
        actor: User,
        target: ConsumptionTarget,
        canonical_identity: str,
        *,
        channel: ConsumptionChannel,
    ) -> tuple[AwardSpec, ...]:
        """Build five-point immutable award specifications for an eligible event.

        :param actor: Authenticated learner. Example: Maria.
        :param target: Authorized target with real author/category. Example: Mike/Development.
        :param canonical_identity: Scoped stable ledger key. Example: "consumption:gui_copy:…".
        :param channel: Explicit server-selected provenance. Example: "gui_copy".
        :return: Learning then Consumption specifications. Example: a two-item tuple.
        """
        book = target.playbook
        learner_spec = AwardSpec(
            recipient_id=actor.pk,
            source_kind=KarmaAward.SourceKind.LEARNING,
            points=_CONSUMPTION_POINTS,
            category=book.category,
            event_identity=canonical_identity,
            playbook_id_snapshot=book.pk,
            change_id_snapshot=None,
            occurred_at=timezone.now(),
            event_channel=channel,
            entity_type_snapshot=target.entity_type,
            entity_id_snapshot=target.entity_id,
        )
        author_spec = replace(
            learner_spec,
            recipient_id=book.author_id,
            source_kind=KarmaAward.SourceKind.CONSUMPTION,
        )
        return learner_spec, author_spec

    @staticmethod
    @transaction.atomic
    def award_accepted_changes(
        *, pip: ProcessImprovementProposal, correlation_id: str
    ) -> tuple[AwardOutcome, ...]:
        """Award approved changes from a persisted PIP publication.

        :param pip: Persisted proposal. Example: accepted PIP targeting playbook 6106.
        :param correlation_id: Safe operation identifier. Example: "pip_finalize:42".
        :return: Immutable persistence outcomes. Example: one created 500-point outcome.
        :raises ValueError: If the proposal is unsaved.
        :raises ValidationError: If the trace ID or recorded award batch conflicts.
        """
        KarmaService._validate_batch((), correlation_id)
        pip = KarmaService._load_awardable_accepted_pip(pip)
        trace = f"pip_id={pip.pk} correlation_id={correlation_id}"
        logger.info("%s | entry | %s", _ACCEPTED_CHANGE_LOG, trace)
        try:
            specifications = KarmaService._accepted_change_specs(pip, trace=trace)
            outcomes = (
                KarmaService.persist_awards(
                    specifications, correlation_id=correlation_id
                )
                if specifications
                else ()
            )
        except (ValidationError, IntegrityError):
            logger.error(
                "%s | error | reason=award_batch_failed %s", _ACCEPTED_CHANGE_LOG, trace
            )
            raise
        created_count = sum(outcome.created for outcome in outcomes)
        logger.info(
            "%s | exit | created_count=%s existing_count=%s transaction=pending %s",
            _ACCEPTED_CHANGE_LOG,
            created_count,
            len(outcomes) - created_count,
            trace,
        )
        return outcomes

    @staticmethod
    def _load_awardable_accepted_pip(
        pip: ProcessImprovementProposal,
    ) -> ProcessImprovementProposal:
        """Reload and lock the proposal while validating publication and recording awards.

        :param pip: Persisted input proposal. Example: PIP 42.
        :return: Locked proposal and current target. Example: accepted PIP 42.
        :raises ValueError: If the input is unsaved or malformed.
        :raises ProcessImprovementProposal.DoesNotExist: If the proposal was deleted.
        """
        if (
            not isinstance(pip, ProcessImprovementProposal)
            or pip._state.adding
            or not pip.pk
        ):
            raise ValueError("A persisted proposal is required.")
        return (
            ProcessImprovementProposal.objects.select_for_update(of=("self",))
            .select_related("playbook")
            .get(pk=pip.pk)
        )

    @staticmethod
    def _accepted_change_specs(
        pip: ProcessImprovementProposal,
        *,
        trace: str,
    ) -> tuple[AwardSpec, ...]:
        """Build a complete immutable batch from the proposal's published ACCEPT rows.

        :param pip: Reloaded locked proposal. Example: accepted PIP 42.
        :param trace: Safe proposal and correlation identifiers for logs.
        :return: Immutable complete batch. Example: (Activity ADD specification,).
        :raises ValidationError: If existing ledger data is incomplete or contradictory.
        """
        eligibility = KarmaService._accepted_publication(pip)
        if isinstance(eligibility, str):
            logger.info(
                "%s | branch | reason=%s %s", _ACCEPTED_CHANGE_LOG, eligibility, trace
            )
            return ()
        category, changes = eligibility
        specifications = []
        for change in changes:
            spec = KarmaService._accepted_change_spec(pip, change, category=category)
            if spec is None:
                logger.info(
                    "%s | branch | reason=unsupported_change change_id=%s %s",
                    _ACCEPTED_CHANGE_LOG,
                    change.pk,
                    trace,
                )
            else:
                specifications.append(spec)
        recorded_identities = set(
            KarmaAward.objects.filter(
                event_identity__in=[
                    f"accepted_change:{change.pk}" for change in changes
                ]
            ).values_list("event_identity", flat=True)
        )
        if recorded_identities and recorded_identities != {
            spec.event_identity for spec in specifications
        }:
            raise ValidationError(
                "The accepted-change award batch is partially recorded."
            )
        return tuple(specifications)

    @staticmethod
    def _accepted_publication(
        pip: ProcessImprovementProposal,
    ) -> tuple[str, tuple[PipChange, ...]] | str:
        """Find authoritative applied changes and their category, or a safe skip reason.

        :param pip: Persisted proposal locked by the caller.
        :return: Receipt category and applied changes or a stable reason. Example: "decision_ineligible".
        """
        if pip.status not in _ACCEPTED_STATES or pip.decided_at is None:
            return "decision_ineligible"
        if pip.created_by_id is None:
            return "missing_submitter"
        changes = tuple(pip.changes.select_for_update().order_by("order", "pk"))
        accepted = tuple(
            change
            for change in changes
            if change.admin_decision == PipChange.ADMIN_ACCEPT
        )
        rejected_count = sum(
            change.admin_decision == PipChange.ADMIN_REJECT for change in changes
        )
        if (
            not accepted
            or len(accepted) + rejected_count != len(changes)
            or (pip.status == pip.STATUS_ACCEPTED_PARTIAL) != bool(rejected_count)
        ):
            return "decisions_inconsistent"
        category = KarmaService._accepted_publication_category(pip, accepted)
        if category is None:
            return "publication_ineligible"
        return category, accepted

    @staticmethod
    def _accepted_publication_category(
        pip: ProcessImprovementProposal,
        accepted: tuple[PipChange, ...],
    ) -> str | None:
        """Verify the original major publication and its entire applied change set.

        :param pip: Persisted proposal locked by the caller.
        :param accepted: Ordered stored approvals from that proposal.
        :return: Canonical receipt category, if valid. Example: "design".
        """
        receipts = tuple(
            pip.playbook_versions.select_for_update().filter(
                source=VersionSource.PIP_SOURCE
            )[:2]
        )
        if len(receipts) != 1:
            return None
        (receipt,) = receipts
        snapshot = receipt.snapshot_data
        if (
            receipt.playbook_id != pip.playbook_id
            or not receipt.is_major
            or receipt.version_number > pip.playbook.version
            or receipt.created_at > pip.decided_at
            or not isinstance(snapshot, dict)
            or type(snapshot.get("pip_id")) is not int
            or snapshot["pip_id"] != pip.pk
            or snapshot.get("version_after") != str(receipt.version_number)
        ):
            return None
        before = snapshot.get("version_before")
        if not isinstance(before, str) or not _VERSION_NUMBER.fullmatch(before):
            return None
        previous_version = Decimal(before)
        if (
            previous_version < FIRST_RELEASE_VERSION
            or int(previous_version) + 1 != receipt.version_number
        ):
            return None
        applied_ids = snapshot.get("accepted_change_ids")
        expected_ids = {change.pk for change in accepted}
        if (
            not isinstance(applied_ids, list)
            or any(type(change_id) is not int for change_id in applied_ids)
            or len(applied_ids) != len(expected_ids)
            or set(applied_ids) != expected_ids
        ):
            return None
        category = snapshot.get("category")
        return category if category in CATEGORY_SLUGS else None

    @staticmethod
    def _accepted_change_spec(
        pip: ProcessImprovementProposal,
        change: PipChange,
        *,
        category: str,
    ) -> AwardSpec | None:
        """Reuse a matching event or snapshot a newly eligible accepted change.

        :param pip: Eligible proposal. Example: PIP 42 submitted by Maria.
        :param change: Persisted accepted child. Example: ADD Activity change 81.
        :param category: Category declared by the original publication. Example: "design".
        :return: Immutable specification or None. Example: 500 Design points.
        :raises ValidationError: If existing award data conflicts with the publication.
        """
        policy = KarmaService._accepted_change_policy(change)
        if policy is None:
            return None
        source_kind, points = policy
        event_identity = f"accepted_change:{change.pk}"
        recorded = KarmaService._recorded_accepted_change_spec(
            event_identity=event_identity,
            recipient_id=pip.created_by_id,
        )
        # ADD does not populate its new entity ID. Historical imports can attest a known one.
        has_target = change.change_type in (
            PipChange.CHANGE_ALTER,
            PipChange.CHANGE_DROP,
        )
        if recorded is not None and recorded.entity_id_snapshot is not None:
            has_target = True
        target_id = change.target_id if has_target else None
        spec = AwardSpec(
            recipient_id=pip.created_by_id,
            source_kind=source_kind,
            points=points,
            category=category,
            event_identity=event_identity,
            playbook_id_snapshot=pip.playbook_id,
            change_id_snapshot=change.pk,
            occurred_at=pip.decided_at,
            event_channel=EventChannel.ACCEPTED_CHANGE,
            entity_type_snapshot=change.entity_type if target_id else None,
            entity_id_snapshot=target_id,
        )
        if recorded is None:
            return spec
        if recorded != replace(spec, occurred_at=recorded.occurred_at):
            raise ValidationError(
                "The accepted-change award conflicts with its publication."
            )
        return recorded

    @staticmethod
    def _accepted_change_policy(
        change: PipChange,
    ) -> tuple[Literal["major", "minor"], int] | None:
        """Classify the supported operation, entity and relationship matrix.

        :param change: Persisted typed change. Example: ADD Activity change 81.
        :return: Source and points or None. Example: ("major", 500).
        :raises TypeError: If change is not a PipChange.
        """
        if not isinstance(change, PipChange):
            raise TypeError("A PIP change is required.")
        operation, entity = change.change_type, change.entity_type
        relationship = change.relationship_type
        source_kind: Literal["major", "minor"] = "minor"
        points = _ACCEPTED_MINOR_POINTS
        if operation in _RELATIONSHIP_OPERATIONS:
            if not KarmaService._has_awardable_relationship(change):
                return None
        elif relationship:
            return None
        elif operation == PipChange.CHANGE_ADD and entity in _MAJOR_ADD_ENTITIES:
            source_kind, points = "major", _ACCEPTED_MAJOR_POINTS
        elif not (
            (operation == PipChange.CHANGE_ADD and entity in _MINOR_ADD_ENTITIES)
            or (
                operation in (PipChange.CHANGE_ALTER, PipChange.CHANGE_DROP)
                and entity in _EDITABLE_ENTITIES
            )
        ):
            return None
        logger.info(
            "%s | processing | pip_id=%s change_id=%s operation=%s entity=%s relationship_type=%s source_kind=%s points=%s",
            _ACCEPTED_POLICY_LOG,
            change.pip_id,
            change.pk,
            operation,
            entity,
            relationship,
            source_kind,
            points,
        )
        return source_kind, points

    @staticmethod
    def _has_awardable_relationship(change: PipChange) -> bool:
        """Check the canonical relationship and endpoint type shape used by PIP apply.

        :param change: LINK or UNLINK change. Example: skill_activity LINK.
        :return: Whether the relationship type and endpoint types are supported.
        """
        if change.entity_type:
            return False
        try:
            endpoints = relationship_endpoint_types(change.relationship_type)
        except ValidationError:
            return False
        return endpoints == (change.source_entity_type, change.target_entity_type)

    @staticmethod
    def _recorded_accepted_change_spec(
        *, event_identity: str, recipient_id: int
    ) -> AwardSpec | None:
        """Recover the original immutable payload for a retry.

        :param event_identity: Stable change event. Example: "accepted_change:81".
        :param recipient_id: Submitter account identifier. Example: Maria's actual user pk.
        :return: Original specification or None. Example: original Design event and timestamp.
        :raises ValidationError: For a conflicting event identity, recipient or channel.
        """
        rows = tuple(
            KarmaAward.objects.filter(event_identity=event_identity).values(
                *AwardSpec.__dataclass_fields__
            )[:2]
        )
        if not rows:
            return None
        if (
            len(rows) != 1
            or rows[0]["recipient_id"] != recipient_id
            or rows[0]["event_channel"] != EventChannel.ACCEPTED_CHANGE
        ):
            raise ValidationError(
                "The accepted-change identity has a conflicting award."
            )
        return AwardSpec(**rows[0])

    @staticmethod
    def _partition_event_specs(
        specifications: tuple[AwardSpec, ...],
    ) -> tuple[tuple[AwardSpec, ...], ...]:
        """Group validated specs deterministically without losing input ordering.

        :param specifications: Immutable batch. Example: (learner_spec, author_spec).
        :return: Groups ordered by identity. Example: ((learner_spec, author_spec),).
        :raises ValidationError: Invalid singleton/pair or duplicate recipient.
        """
        raise NotImplementedError()

    @staticmethod
    def _existing_event_rows(event_identity: str) -> tuple[KarmaAward, ...]:
        """Load every row for an identity, including imported historical rows.

        :param event_identity: Canonical key. Example: "first_release:6302".
        :return: Recipient-ordered real rows. Example: (stored_release_award,).
        :raises ValidationError: Empty or malformed identity.
        """
        raise NotImplementedError()

    @staticmethod
    def _logical_award_payload(specification: AwardSpec) -> tuple[object, ...]:
        """Return immutable logical fields, excluding request-generated time.

        :param specification: Validated input. Example: learning spec for Maria.
        :return: Comparable field tuple. Example: (42, "learning", 5, ...).
        :raises ValidationError: Invalid snapshot/source/channel values.
        """
        raise NotImplementedError()

    @staticmethod
    def _assert_matching_event(
        existing: tuple[KarmaAward, ...], requested: tuple[AwardSpec, ...]
    ) -> tuple[AwardOutcome, ...]:
        """Compare complete event shape and payload; retain stored timestamps.

        Convert stored rows to existing AwardSpec values for logical comparison.
        Compare recipient sets and every logical field. Reject partial events.
        Never update rows or compare fresh request time with stored original time.

        :param existing: Entire stored event. Example: learner/author pair.
        :param requested: Complete requested event. Example: same pair at newer time.
        :return: Existing outcomes in request order. Example: two created=False rows.
        :raises ValidationError: Changed recipient, target, attribution or shape.
        """
        raise NotImplementedError()

    @staticmethod
    def _insert_event_rows(
        specifications: tuple[AwardSpec, ...],
    ) -> tuple[AwardOutcome, ...]:
        """Delegate row insertion to S30's writer, abandoning on any duplicate.

        Caller owns an event savepoint. Reuse _insert_or_get_award; an existing
        outcome raises EventInsertRace before proceeding to another recipient.

        :param specifications: Complete validated event. Example: two five-point specs.
        :return: All-created outcomes. Example: learner and author created=True.
        :raises EventInsertRace: Another writer owns any event row.
        :raises IntegrityError: Database constraint failure; caller handles savepoint.
        """
        raise NotImplementedError()

    @staticmethod
    def _is_event_identity_collision(error: IntegrityError) -> bool:
        """Recognize only expected ledger identity/first-release unique violations.

        PostgreSQL uses SQLSTATE/constraint diagnostics; SQLite uses native unique
        error category plus the exact affected ledger column signature. Do not
        classify foreign-key, check or unrelated unique failures as replay.

        :param error: Actual database error. Example: anchor unique violation.
        :return: Whether race reconciliation applies. Example: True.
        :raises TypeError: Unsupported input. Example: a ValueError.
        """
        raise NotImplementedError()

    @staticmethod
    def _persist_event_atomic(
        specifications: tuple[AwardSpec, ...], *, correlation_id: str
    ) -> tuple[AwardOutcome, ...]:
        """Preflight an event and insert/reconcile using a nested savepoint.

        On expected collision or EventInsertRace, exit the failed savepoint before
        rereading all rows. Empty reread or unrelated failure must propagate.

        :param specifications: One complete event. Example: learner/author pair.
        :param correlation_id: Safe trace ID. Example: "receipt-45".
        :return: Entire created/replayed outcome. Example: two existing outcomes.
        :raises ValidationError: Winner payload differs or stored event is partial.
        :raises IntegrityError: Unrelated constraint or unexplained missing winner.
        :raises OperationalError: Contention must escape to transaction owner.
        """
        raise NotImplementedError()

    @staticmethod
    def _persist_batch_atomic(
        groups: tuple[tuple[AwardSpec, ...], ...], *, correlation_id: str
    ) -> tuple[AwardOutcome, ...]:
        """Perform one whole-batch attempt inside an atomic transaction.

        Preflight every existing group before writing missing groups; any later
        conflict rolls back every new row from this attempt. Preserve input order
        when existing persist_awards assembles its return value.

        :param groups: Identity-ordered groups. Example: two accepted-change events.
        :param correlation_id: Safe trace ID. Example: "decision-45".
        :return: Complete batch outcomes. Example: two singleton awards.
        :raises ValidationError: Any group conflicts.
        :raises IntegrityError: Database invariant violation.
        :raises OperationalError: Database contention or failure.
        """
        raise NotImplementedError()

    @staticmethod
    def _is_retryable_database_busy(error: OperationalError) -> bool:
        """Classify SQLite native busy/locked codes without masking other errors.

        :param error: Actual driver-wrapped exception. Example: SQLITE_BUSY_SNAPSHOT.
        :return: Recognized transient SQLite contention. Example: True.
        :raises TypeError: Input is not an OperationalError.
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


class EventInsertRace(RuntimeError):
    """Internal signal: abandon this savepoint and inspect the winning event."""
