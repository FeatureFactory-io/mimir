"""
Playbook Service - Business logic for playbook operations.

Generic service layer used by both UI views and MCP tools.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q

from methodology.models import (
    KarmaAward,
    Playbook,
    PlaybookVersion,
    VersionSource,
    Workflow,
)
from methodology.models.karma_award import CATEGORY_SLUGS
from methodology.services.karma_service import (
    AWARD_CORRELATION_ID,
    FIRST_RELEASE_VERSION,
    AwardOutcome,
    KarmaService,
)

logger = logging.getLogger(__name__)

_PLAYBOOK_VISIBILITY_ALLOWED = frozenset({"private", "public"})
_RELEASE_LOG = "PlaybookService.release_playbook_with_award"
_NOTES_FIELD = "release_description"
_RELEASE_VALIDATION = "%s | validation | owner_valid=true workflow_present=true %s"
_RELEASE_ERRORS = (
    ValidationError,
    PermissionError,
    Playbook.DoesNotExist,
    IntegrityError,
)


def _validate_playbook_visibility(visibility: str) -> None:
    """Raise ValidationError if visibility is not allowed for GUI/MCP creates and updates."""
    if visibility not in _PLAYBOOK_VISIBILITY_ALLOWED:
        logger.warning(
            "Rejected playbook visibility value %r (allowed=%s)",
            visibility,
            _PLAYBOOK_VISIBILITY_ALLOWED,
        )
        raise ValidationError("Visibility must be private or public.")


def _playbook_release_snapshot(playbook: Playbook) -> dict:
    """JSON-serializable snapshot of playbook structure for PlaybookVersion."""
    workflows = Workflow.objects.filter(playbook=playbook).order_by(
        "order", "created_at"
    )
    return {
        "name": playbook.name,
        "description": playbook.description,
        "category": playbook.category,
        "status": playbook.status,
        "version": str(playbook.version),
        "workflows": [
            {
                "id": w.pk,
                "name": w.name,
                "order": w.order,
                "abbreviation": w.abbreviation,
            }
            for w in workflows
        ],
    }


class PlaybookService:
    """Service class for playbook CRUD operations."""

    @staticmethod
    def create_playbook(
        name,
        description,
        category,
        author,
        status="draft",
        visibility="private",
        source="owned",
    ):
        """
        Create playbook with validation.

        Used by both UI and MCP.

        :param name: Playbook name (max 100 chars, unique per author)
        :param description: Description (max 500 chars)
        :param category: Category (product/development/research/design/other)
        :param author: User instance
        :param status: draft/active/released/disabled (default: draft)
        :param visibility: private or public (default: private)
        :param source: owned/downloaded (default: owned)
        :returns: Created Playbook instance
        :raises ValidationError: If validation fails

        Example:
            >>> playbook = PlaybookService.create_playbook(
            ...     name="React Development",
            ...     description="Modern React patterns",
            ...     category="development",
            ...     author=user
            ... )
        """
        logger.info(
            f"Creating playbook '{name}' for author {author.id}, status={status}"
        )

        # Validate name
        if not name or not name.strip():
            logger.warning("Playbook creation failed: empty name")
            raise ValidationError("Playbook name cannot be empty")

        _validate_playbook_visibility(visibility)

        # Set initial version based on status
        initial_version = (
            Decimal("1.0") if status in ["released", "active"] else Decimal("0.1")
        )

        try:
            playbook = Playbook.objects.create(
                name=name.strip(),
                description=description.strip() if description else "",
                category=category,
                author=author,
                status=status,
                version=initial_version,
                visibility=visibility,
                source=source,
            )

            # Create initial version record for non-draft playbooks (active and released both
            # start at version 1.0 and need an audit trail entry from day one).
            if status in ["released", "active"]:
                PlaybookVersion.objects.create(
                    playbook=playbook,
                    version_number=Decimal("1.0"),
                    snapshot_data={
                        "name": playbook.name,
                        "version": str(playbook.version),
                    },
                    change_summary="Initial version",
                    description="Initial version",
                    is_major=True,
                    source=VersionSource.RELEASE,
                    created_by=author,
                )

            logger.info(
                f"Created playbook '{name}' (id={playbook.id}, version={playbook.version})"
            )
            return playbook

        except IntegrityError as e:
            logger.error(
                f"Playbook creation failed: duplicate name '{name}' for author {author.id}"
            )
            raise ValidationError(f"Playbook '{name}' already exists") from e

    @staticmethod
    def get_playbook(playbook_id, user, *, prefetch_workflows: bool = False):
        """
        Get playbook by ID if ``user`` may view it (owner or public non-draft per ``can_view``).

        :param playbook_id: Playbook ID
        :param user: Requesting Django user
        :param prefetch_workflows: When True, prefetch ``workflows`` for list/detail responses
        :returns: Playbook instance
        :raises Playbook.DoesNotExist: If playbook row is missing
        :raises PermissionError: If user may not view this playbook (treated as not found by MCP)
        """
        qs = Playbook.objects
        if prefetch_workflows:
            qs = qs.prefetch_related("workflows")
        logger.info(
            "Retrieving playbook id=%s for user id=%s (prefetch_workflows=%s)",
            playbook_id,
            getattr(user, "pk", user),
            prefetch_workflows,
        )
        try:
            playbook = qs.get(pk=playbook_id)
        except Playbook.DoesNotExist:
            logger.info("Playbook id=%s not found", playbook_id)
            raise
        if not playbook.can_view(user):
            logger.info(
                "User id=%s denied view on playbook id=%s (visibility=%s)",
                getattr(user, "pk", user),
                playbook_id,
                playbook.visibility,
            )
            raise PermissionError(f"Playbook {playbook_id} not found")
        return playbook

    @staticmethod
    def get_owned_playbook(playbook_id, user):
        """
        Return playbook only if ``user`` is the author (for mutating operations).

        :param playbook_id: Playbook primary key
        :param user: Django user
        :returns: Playbook instance
        :raises Playbook.DoesNotExist: If missing or not owned by user
        """
        try:
            playbook = Playbook.objects.get(pk=playbook_id, author=user)
        except Playbook.DoesNotExist:
            logger.info(
                "get_owned_playbook: playbook id=%s not found for user id=%s",
                playbook_id,
                getattr(user, "pk", user),
            )
            raise Playbook.DoesNotExist(
                f"Playbook with id={playbook_id} does not exist."
            ) from None
        return playbook

    @staticmethod
    def list_playbooks(author, status=None):
        """
        List playbooks for author, optionally filtered by status.

        :param author: User instance
        :param status: Optional status filter (draft/released/active/disabled)
        :returns: QuerySet of Playbook instances

        Example:
            >>> draft_playbooks = PlaybookService.list_playbooks(user, status='draft')
        """
        logger.info(f"Listing playbooks for author {author.id}, status_filter={status}")

        queryset = Playbook.objects.filter(author=author)
        if status:
            queryset = queryset.filter(status=status)

        playbooks = list(queryset)
        logger.info(f"Found {len(playbooks)} playbooks")
        return playbooks

    @staticmethod
    def list_public_playbooks(exclude_author):
        """
        Public, non-draft playbooks authored by other users (FOB browse list).

        Draft playbooks stay owner-only even when visibility is Public.

        :param exclude_author: Current user; their own playbooks appear in the owned list.
        :returns: List of Playbook instances, newest first
        """
        qs = (
            Playbook.objects.filter(visibility="public")
            .exclude(status="draft")
            .exclude(author=exclude_author)
            .select_related("author")
            .order_by("-updated_at")
        )
        rows = list(qs)
        logger.info(
            "Listed %s public playbooks for user id=%s (excluding own and draft)",
            len(rows),
            getattr(exclude_author, "pk", exclude_author),
        )
        return rows

    @staticmethod
    def list_public_playbooks_for_guest():
        """Released public playbooks visible to anonymous guests (browse list).

        :returns: List of Playbook instances, newest first.
        """
        qs = (
            Playbook.objects.filter(visibility="public", status="released")
            .select_related("author")
            .order_by("-updated_at")
        )
        rows = list(qs)
        logger.info(
            "Listed %s released public playbooks for anonymous guest", len(rows)
        )
        return rows

    @staticmethod
    def get_guest_readable_playbook_ids():
        """Primary keys of playbooks anonymous guests may read.

        :returns: Set of int playbook IDs.
        """
        ids = set(
            Playbook.objects.filter(visibility="public", status="released").values_list(
                "id", flat=True
            )
        )
        logger.info("Guest-readable playbook count=%s", len(ids))
        return ids

    @staticmethod
    def list_team_playbooks_for_user(user):
        """
        Released playbooks shared via team membership (excludes own-authored).

        :param user: User whose team playbooks to retrieve.
        :returns: List of Playbook instances accessible via teams.
        """
        from methodology.models import TeamMembership, TeamPlaybook

        logger.info(f"Listing team playbooks for user {user.id}")

        # Get all teams where user is a member
        team_ids = TeamMembership.objects.filter(user=user).values_list(
            "team_id", flat=True
        )

        # Get all playbooks linked to those teams (excluding own-authored)
        playbook_ids = TeamPlaybook.objects.filter(team_id__in=team_ids).values_list(
            "playbook_id", flat=True
        )

        qs = (
            Playbook.objects.filter(pk__in=playbook_ids)
            .exclude(author=user)
            .select_related("author")
            .order_by("-updated_at")
        )
        rows = list(qs)
        logger.info(f"Found {len(rows)} team playbooks for user {user.id}")
        return rows

    @staticmethod
    def get_accessible_playbook_ids(user):
        """
        Get IDs of all playbooks accessible to user (owned + public + team).

        Useful for filtering related objects (workflows, activities, etc.) to only
        show items from playbooks the user can access.

        :param user: User whose accessible playbooks to retrieve.
        :returns: Set of playbook IDs.
        """
        from methodology.models import TeamMembership, TeamPlaybook

        logger.info(f"Getting accessible playbook IDs for user {user.id}")

        # Get owned playbook IDs
        owned_ids = set(
            Playbook.objects.filter(author=user).values_list("id", flat=True)
        )

        # Get public playbook IDs (non-draft, excluding own)
        public_ids = set(
            Playbook.objects.filter(visibility="public")
            .exclude(status="draft")
            .exclude(author=user)
            .values_list("id", flat=True)
        )

        # Get team playbook IDs
        team_ids = list(
            TeamMembership.objects.filter(user=user).values_list("team_id", flat=True)
        )
        team_playbook_ids = set(
            TeamPlaybook.objects.filter(team_id__in=team_ids).values_list(
                "playbook_id", flat=True
            )
        )

        # Get Django auth Group shared playbook IDs (API group sharing)
        group_playbook_ids = set(
            Playbook.objects.filter(shared_with_groups__in=user.groups.all())
            .exclude(author=user)
            .values_list("id", flat=True)
        )

        # Combine all IDs
        all_ids = owned_ids | public_ids | team_playbook_ids | group_playbook_ids

        logger.info(
            f"User {user.id} has access to {len(all_ids)} playbooks "
            f"({len(owned_ids)} owned, {len(public_ids)} public, {len(team_playbook_ids)} team, "
            f"{len(group_playbook_ids)} group-shared)"
        )
        return all_ids

    @staticmethod
    def author_has_playbook_named(user, name):
        """
        Check whether user already owns a playbook with the given name.

        :param user: Playbook author
        :param name: Playbook name to check
        :returns: True if a duplicate name exists for this author
        """
        exists = Playbook.objects.filter(author=user, name=name).exists()
        logger.info(
            "Duplicate name check for user id=%s name=%r: %s",
            getattr(user, "pk", user),
            name,
            exists,
        )
        return exists

    @staticmethod
    @transaction.atomic
    def update_playbook(playbook_id, **data):
        """
        Update playbook fields with validation.

        :param playbook_id: Playbook ID
        :param data: Fields to update (name, description, category, etc.)
        :returns: Updated Playbook instance
        :raises ValidationError: If validation fails

        Example:
            >>> playbook = PlaybookService.update_playbook(
            ...     playbook_id=1,
            ...     name="New Name",
            ...     description="Updated description"
            ... )
        """
        logger.info(f"Updating playbook {playbook_id}")

        playbook = Playbook.objects.get(pk=playbook_id)

        if "visibility" in data:
            _validate_playbook_visibility(data["visibility"])

        # Check for duplicate name if changing name
        if "name" in data and data["name"] != playbook.name:
            if Playbook.objects.filter(
                author=playbook.author, name=data["name"]
            ).exists():
                logger.warning(
                    f"Playbook update failed: duplicate name '{data['name']}'"
                )
                raise ValidationError(f"Playbook '{data['name']}' already exists")

        # Update fields
        for field, value in data.items():
            if hasattr(playbook, field):
                setattr(playbook, field, value)

        playbook.save()
        logger.info(f"Playbook {playbook_id} updated")
        return playbook

    @staticmethod
    @transaction.atomic
    def delete_playbook(playbook_id):
        """
        Delete playbook (cascades to workflows and activities).

        :param playbook_id: Playbook ID

        Example:
            >>> PlaybookService.delete_playbook(1)
        """
        logger.info(f"Deleting playbook {playbook_id}")
        playbook = Playbook.objects.get(pk=playbook_id)
        playbook_name = playbook.name
        playbook.delete()
        logger.info(f"Playbook '{playbook_name}' (id={playbook_id}) deleted")

    @staticmethod
    @transaction.atomic
    def duplicate_playbook(playbook_id, new_name, author):
        """
        Duplicate playbook (deep copy with workflows and activities).

        :param playbook_id: Original playbook ID
        :param new_name: Name for duplicate
        :param author: User instance (owner of duplicate)
        :returns: Duplicated Playbook instance
        :raises ValidationError: If new name already exists

        Example:
            >>> duplicate = PlaybookService.duplicate_playbook(
            ...     playbook_id=1,
            ...     new_name="My Copy",
            ...     author=user
            ... )
        """
        logger.info(f"Duplicating playbook {playbook_id} as '{new_name}'")

        original = Playbook.objects.get(pk=playbook_id)

        # Check for duplicate name
        if Playbook.objects.filter(author=author, name=new_name).exists():
            logger.warning(f"Duplicate failed: name '{new_name}' already exists")
            raise ValidationError(f"Playbook '{new_name}' already exists")

        # Create duplicate (workflows/activities handled by UI views currently)
        duplicate = Playbook.objects.create(
            name=new_name,
            description=original.description,
            category=original.category,
            author=author,
            status="draft",  # Always start as draft
            version=Decimal("0.1"),  # Reset version
            visibility=original.visibility,
            source="owned",
        )

        logger.info(f"Playbook duplicated as {duplicate.pk}")
        return duplicate

    @staticmethod
    def release_playbook(
        playbook_id: int, author: AbstractBaseUser, *, description: str
    ) -> Playbook:
        """Publish a draft or advance a released playbook, returning the playbook.

        :param playbook_id: Existing playbook PK. Example: 6302.
        :param author: Acting owner. Example: Nora.
        :param description: Required release notes. Example: "Initial release".
        :return: Published playbook. Example: Playbook(pk=6302, version=1.0).
        :raises ValidationError: If publication or its award is invalid.
        :raises PermissionError: If the actor does not own the playbook.
        """
        return PlaybookService.release_playbook_with_award(
            playbook_id, author, description=description, correlation_id=str(uuid4())
        ).playbook

    @staticmethod
    @transaction.atomic
    def revert_released_playbook_to_draft(
        playbook_id, *, actor, reason: str
    ) -> Playbook:
        """
        Staff transition: ``released`` → ``draft``, keeping the current playbook version.

        When no ``PlaybookVersion`` row exists yet for ``playbook.version``, inserts an
        admin-sourced audit row (unique constraint is per ``(playbook, version_number)``).
        """
        text = (reason or "").strip()
        if not text:
            raise ValidationError("Revert reason is required.")

        if not getattr(actor, "is_staff", False):
            raise PermissionError("Only staff can revert a released playbook to draft.")

        playbook = Playbook.objects.get(pk=playbook_id)
        if playbook.status != "released":
            raise ValidationError(
                "Only released playbooks can be reverted to draft "
                f"(current status: {playbook.status})."
            )

        hold_version = playbook.version
        playbook.status = "draft"
        playbook.save(update_fields=["status", "updated_at"])

        if not PlaybookVersion.objects.filter(
            playbook=playbook, version_number=hold_version
        ).exists():
            PlaybookVersion.objects.create(
                playbook=playbook,
                version_number=hold_version,
                snapshot_data={
                    "event": "admin_revert_to_draft",
                    "version": str(hold_version),
                    "name": playbook.name,
                },
                change_summary=text,
                description=text,
                is_major=False,
                source=VersionSource.ADMIN,
                created_by=actor,
            )

        logger.info(
            "Playbook id=%s reverted released → draft at v%s",
            playbook_id,
            hold_version,
        )
        return playbook

    @staticmethod
    @transaction.atomic
    def release_playbook_with_award(
        playbook_id: int,
        author: AbstractBaseUser,
        *,
        description: str,
        correlation_id: str,
    ) -> ReleaseOutcome:
        """Publish and stage its eligible award in one atomic transaction.

        The existing release_playbook entrypoint returns this outcome's playbook.

        :param playbook_id: Target ID. Example: 6302.
        :param author: Authenticated owner. Example: Nora.
        :param description: Required release notes. Example: "Initial release".
        :param correlation_id: Request/run ID. Example: "release-01".
        :return: Publication outcome. Example: first award created for 5000 points.
        :raises Playbook.DoesNotExist: If the target does not exist.
        :raises PermissionError: If the actor does not own the target.
        :raises ValidationError: If publication or award validation fails.
        """
        if not isinstance(correlation_id, str) or not AWARD_CORRELATION_ID.fullmatch(
            correlation_id
        ):
            raise ValidationError("A safe release correlation ID is required.")
        if type(playbook_id) is not int or playbook_id < 1:
            raise ValidationError("A positive playbook ID is required.")
        actor_id = author.pk if isinstance(author, AbstractBaseUser) else None
        trace = f"playbook_id={playbook_id} correlation_id={correlation_id}"
        logger.info("%s | entry | actor_id=%s %s", _RELEASE_LOG, actor_id, trace)
        try:
            text = PlaybookService._validated_release_description(description)
            playbook = PlaybookService._locked_release_target(playbook_id, author)
            PlaybookService._validate_release_target(playbook)
            first = PlaybookService._is_first_publication(playbook)
            validated = f"first_publication={str(first).lower()} {trace}"
            logger.info(_RELEASE_VALIDATION, _RELEASE_LOG, validated)
            receipt = PlaybookService._publish_release_version(playbook, author, text)
            award = PlaybookService._first_publication_award_outcome(
                playbook,
                receipt,
                author,
                first_publication=first,
                correlation_id=correlation_id,
            )
        except _RELEASE_ERRORS as error:
            detail = getattr(error, "error_dict", {}).get(_NOTES_FIELD, [error])[0]
            reason = getattr(detail, "code", None) or type(error).__name__
            logger.info("%s | error | reason=%s %s", _RELEASE_LOG, reason, trace)
            raise
        return ReleaseOutcome(playbook, award)

    @staticmethod
    def _validated_release_description(description: str) -> str:
        """Validate and normalize notes with existing error semantics.

        :param description: Candidate notes. Example: " Initial release ".
        :return: Nonempty notes. Example: "Initial release".
        :raises ValidationError: If notes are empty or invalid.
        """
        description_clean = description.strip() if isinstance(description, str) else ""
        if not description_clean:
            raise ValidationError(
                {
                    _NOTES_FIELD: ValidationError(
                        "Release description is required.",
                        code="release_description_required",
                    ),
                }
            )
        return description_clean

    @staticmethod
    def _locked_release_target(playbook_id: int, author: AbstractBaseUser) -> Playbook:
        """Retrieve the target for publication and retain owner authorization.

        :param playbook_id: Persisted target ID. Example: 6302.
        :param author: Authenticated acting user. Example: Nora.
        :return: Authorized target in the current transaction. Example: draft 6302.
        :raises Playbook.DoesNotExist: If missing.
        :raises PermissionError: If actor is not the owner.
        :raises ValidationError: If the ID is malformed.
        """
        playbook = Playbook.objects.select_for_update().get(pk=playbook_id)
        if not isinstance(author, AbstractBaseUser) or playbook.author_id != author.pk:
            raise PermissionError("You don't have permission to release this playbook")
        return playbook

    @staticmethod
    def _validate_release_target(playbook: Playbook) -> None:
        """Preserve allowed-status and required-workflow release guards.

        :param playbook: Authorized publication target. Example: Nora's draft.
        :return: None when publication prerequisites hold.
        :raises ValidationError: If status or workflow prerequisites fail.
        """
        if playbook.status not in ("draft", "released"):
            raise ValidationError(
                f"Release is only available for draft or released playbooks "
                f"(current status: {playbook.status})",
                code="invalid_release_status",
            )
        if not Workflow.objects.filter(playbook=playbook).exists():
            raise ValidationError(
                "Add at least one workflow before releasing this playbook.",
                code="release_requires_workflow",
            )

    @staticmethod
    def _is_first_publication(playbook: Playbook) -> bool:
        """Inspect pre-release state without backfilling historical awards.

        Check current status/version, prior released history and the canonical
        first-release ledger marker. A reverted v1+ draft remains historical.
        This decision is made before changing the target's version.

        :param playbook: Locked pre-release target. Example: draft v0.2.
        :return: First-publication eligibility. Example: True for Nora.
        :raises ValidationError: If an otherwise eligible first publication lacks a recognized category.
        """
        if playbook.status != "draft" or playbook.version >= FIRST_RELEASE_VERSION:
            return False
        if playbook.versions.filter(
            Q(source=VersionSource.RELEASE)
            | Q(version_number__gte=FIRST_RELEASE_VERSION)
        ).exists():
            return False
        if KarmaAward.objects.filter(
            source_kind=KarmaAward.SourceKind.RELEASE, playbook_id_snapshot=playbook.pk
        ).exists():
            return False
        if playbook.category not in CATEGORY_SLUGS:
            raise ValidationError(
                "Choose a valid playbook category before releasing.",
                code="release_requires_category",
            )
        return True

    @staticmethod
    def _publish_release_version(
        playbook: Playbook, author: AbstractBaseUser, description: str
    ) -> PlaybookVersion:
        """Extract existing status/version/snapshot publication behavior.

        Reuse compute_next_major_line_version and _playbook_release_snapshot.
        Save one major release receipt with the current notes/source semantics.

        :param playbook: Authorized validated target. Example: draft 6302.
        :param author: Release actor. Example: Nora.
        :param description: Clean required notes. Example: "Initial release".
        :return: Saved release receipt. Example: PlaybookVersion(version_number=1.0).
        :raises IntegrityError: If publication history cannot be persisted.
        """
        version = playbook.compute_next_major_line_version()
        snapshot_before = _playbook_release_snapshot(playbook)
        update_fields = ["version", "updated_at"]
        if playbook.status == "draft":
            playbook.status = "released"
            update_fields.append("status")
        playbook.version = version
        playbook.save(update_fields=update_fields)
        playbook.refresh_from_db()

        return PlaybookVersion.objects.create(
            playbook=playbook,
            version_number=version,
            snapshot_data={
                **_playbook_release_snapshot(playbook),
                "before_release": snapshot_before,
            },
            change_summary=description,
            description=description,
            is_major=True,
            source=VersionSource.RELEASE,
            created_by=author,
        )

    @staticmethod
    def _first_publication_award_outcome(
        playbook: Playbook,
        release_version: PlaybookVersion,
        author: AbstractBaseUser,
        *,
        first_publication: bool,
        correlation_id: str,
    ) -> AwardOutcome:
        """Delegate eligible publication or return an explicit zero-award result.

        :param playbook: Published target. Example: released 6302.
        :param release_version: Receipt from this operation. Example: v1.0.
        :param author: Authenticated owner. Example: Nora.
        :param first_publication: Pre-release decision. Example: True.
        :param correlation_id: Request/run ID. Example: "release-01".
        :return: Award result. Example: AwardOutcome(row, True, "created").
        :raises ValidationError: If eligible award validation fails.
        """
        trace = f"playbook_id={playbook.pk} correlation_id={correlation_id}"
        if first_publication:
            outcome = KarmaService.award_first_release(
                playbook, release_version, author, correlation_id=correlation_id
            )
            if outcome.award is None:
                raise ValidationError(
                    "First publication did not produce a valid Karma award."
                )
            points = outcome.award.points if outcome.created else 0
        else:
            logger.info(
                "%s | branch | reason=previously_released award_points=0 %s",
                _RELEASE_LOG,
                trace,
            )
            outcome = AwardOutcome(None, False, "previously_released")
            points = 0

        logger.info(
            "%s | processing | version=%s award_points=%s transaction=pending %s",
            _RELEASE_LOG,
            playbook.version,
            points,
            trace,
        )
        return outcome


@dataclass(frozen=True)
class ReleaseOutcome:
    """Publication result retaining the legacy Playbook-only entrypoint."""

    playbook: Playbook
    first_release_award: AwardOutcome
