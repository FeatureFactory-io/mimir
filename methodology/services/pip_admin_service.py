"""Administrative finalisation — apply typed PIP changes + major version bump."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import connections, transaction
from django.db.models import F, QuerySet
from django.db.transaction import TransactionManagementError
from django.utils import timezone

from methodology.models import PipChange, ProcessImprovementProposal
from methodology.services.karma_service import KarmaService
from methodology.services.pip_apply_changes_service import (
    PipApplyChangesService,
    bump_playbook_major_version_after_pip_apply,
)
from methodology.services.pip_notification_service import send_decision_email

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from methodology.services.karma_service import AwardOutcome

logger = logging.getLogger(__name__)

DECIDED_STATUSES = frozenset(
    (
        ProcessImprovementProposal.STATUS_ACCEPTED,
        ProcessImprovementProposal.STATUS_ACCEPTED_PARTIAL,
        ProcessImprovementProposal.STATUS_REJECTED,
    )
)
_VALID_CHOICES = (PipChange.ADMIN_ACCEPT, PipChange.ADMIN_REJECT)


class PIPAlreadyDecidedError(ValidationError):
    """The persisted proposal has already reached a staff decision."""


class PIPAdminService:
    """Apply administrator decisions atomically."""

    @staticmethod
    def lock_proposals(
        proposals: QuerySet[ProcessImprovementProposal],
    ) -> list[ProcessImprovementProposal]:
        """Reload proposals under the same lock used by staff review mutations.

        :param proposals: Parent rows to lock. Example: proposals filtered by ID.
        :return: Current proposals in primary-key order. Example: [PIP 42].
        :raises TypeError: If given something other than a PIP queryset.
        :raises TransactionManagementError: If the caller does not own an atomic block.
        """
        if (
            not isinstance(proposals, QuerySet)
            or proposals.model is not ProcessImprovementProposal
        ):
            raise TypeError("PIP review locks require a proposal queryset.")
        locked = proposals.select_for_update(of=("self",)).order_by("pk")
        connection = connections[locked.db]
        if not connection.in_atomic_block:
            raise TransactionManagementError("PIP review locks require a transaction.")
        if connection.vendor == "sqlite":
            # SQLite ignores SELECT FOR UPDATE. Take the write lock before reading
            # any proposal in this transaction to avoid a stale read snapshot.
            locked.update(status=F("status"))
        return list(locked)

    @staticmethod
    @transaction.atomic
    def save_decisions(
        pip: ProcessImprovementProposal,
        actor: AbstractBaseUser | None,
        decisions: Mapping[int, tuple[str, str]],
    ) -> None:
        """Save valid staff choices while the persisted proposal remains undecided.

        :param pip: Persisted proposal. Example: PIP 42.
        :param actor: Existing staff reviewer. Example: mchen.
        :param decisions: Choices by change ID. Example: {7: ("ACCEPT", "Looks good")}.
        :return: None. Example: recognized decisions and notes are saved.
        :raises ValidationError: For insufficient permission or a decided proposal.
        """
        locked = PIPAdminService._lock_review_proposal(pip, actor, decisions)
        if locked.status in DECIDED_STATUSES:
            raise PIPAlreadyDecidedError("This PIP has already been decided.")
        changes = locked.changes.select_for_update().filter(pk__in=decisions)
        PIPAdminService._write_choices(changes, decisions)
        logger.info(
            "PIPAdminService.save_decisions | exit | pip_id=%s actor_id=%s "
            "correlation_id=pip_review:%s transaction=pending",
            locked.pk,
            actor.pk,
            locked.pk,
        )

    @staticmethod
    @transaction.atomic
    def finalize_pip(
        pip: ProcessImprovementProposal,
        actor: AbstractBaseUser | None,
        *,
        decisions: Mapping[int, tuple[str, str]] | None = None,
    ) -> ProcessImprovementProposal:
        """Apply reviewed choices, award eligible changes and schedule decision mail.

        :param pip: Reviewed proposal with per-change decisions. Example: PIP 42.
        :param actor: Staff user invoking finalisation. Example: mchen.
        :param decisions: Optional choice and note overrides by change ID. Example: {7: ("ACCEPT", "Looks good")}.
        :return: Persisted proposal in a terminal state. Example: accepted PIP 42.
        :raises ValidationError: For insufficient permission, invalid decisions or award conflicts.
        """
        posted = {} if decisions is None else decisions
        locked = PIPAdminService._lock_review_proposal(pip, actor, posted)
        if locked.status != ProcessImprovementProposal.STATUS_REVIEWED:
            error = (
                PIPAlreadyDecidedError
                if locked.status in DECIDED_STATUSES
                else ValidationError
            )
            raise error("PIP must be in Reviewed state before finalising.")
        changes = list(locked.changes.select_for_update().order_by("order", "pk"))
        PIPAdminService._write_choices(changes, posted)
        accepted, rejected_count = PIPAdminService._reviewed_decisions(changes)
        if locked.playbook.status != "released":
            raise ValidationError("Only released playbooks consume PIPs.")
        if accepted:
            PIPAdminService._publish_accepted_changes(locked, accepted, actor)

        PIPAdminService._apply_terminal_status(locked, len(accepted), rejected_count)
        PIPAdminService._award_finalized_pip(pip=locked, actor=actor)
        logger.info(
            "PIPAdminService.finalize_pip pk=%s actor=%s accepted=%s rejected=%s",
            locked.pk,
            actor.pk,
            len(accepted),
            rejected_count,
        )
        PIPAdminService._queue_decision_email(locked.pk)
        locked.refresh_from_db()
        return locked

    @staticmethod
    def _lock_review_proposal(
        pip: ProcessImprovementProposal,
        actor: AbstractBaseUser | None,
        decisions: Mapping[int, tuple[str, str]],
    ) -> ProcessImprovementProposal:
        """Serialize review mutations and reload the proposal before checking its state.

        :param pip: Proposal identity. Example: PIP 42 from a previously loaded review.
        :param actor: Existing staff reviewer. Example: mchen.
        :param decisions: Choices to validate before locking. Example: {}.
        :return: Fresh proposal under the caller's transaction lock.
        :raises ValidationError: For unauthorized staff or invalid input.
        :raises ProcessImprovementProposal.DoesNotExist: If the row was deleted.
        """
        if actor is None or not actor.is_staff:
            raise ValidationError("Only staff administrators can finalise PIPs.")
        if (
            not isinstance(pip, ProcessImprovementProposal)
            or not isinstance(pip.pk, int)
            or pip.pk <= 0
        ):
            raise ValidationError("A saved PIP is required to record decisions.")
        if not isinstance(decisions, Mapping):
            raise ValidationError("PIP decisions must be keyed by change ID.")
        proposal = ProcessImprovementProposal.objects.filter(pk=pip.pk).select_related(
            "playbook", "created_by"
        )
        locked = PIPAdminService.lock_proposals(proposal)
        if not locked:
            raise ProcessImprovementProposal.DoesNotExist(
                f"PIP {pip.pk} does not exist."
            )
        return locked[0]

    @staticmethod
    def _write_choices(
        changes: Iterable[PipChange], decisions: Mapping[int, tuple[str, str]]
    ) -> None:
        """Persist valid posted choices on the current proposal's locked change rows.

        :param changes: ORM rows belonging to the locked proposal. Example: [change].
        :param decisions: Decision and note by change ID. Example: {7: ("REJECT", "Scope")}.
        :return: None. Example: omitted or unknown choices leave their rows alone.
        """
        for change in changes:
            choice = decisions.get(change.pk)
            if choice is not None and choice[0] in _VALID_CHOICES:
                change.admin_decision, change.admin_note = choice
                change.save(update_fields=["admin_decision", "admin_note"])

    @staticmethod
    def _reviewed_decisions(
        changes: list[PipChange],
    ) -> tuple[list[PipChange], int]:
        """Validate a complete decision using the same locked rows that will be applied.

        :param changes: Ordered and locked change rows. Example: [change].
        :return: Ordered accepted changes and rejected count. Example: ([change], 1).
        :raises ValidationError: If the proposal has no changes or incomplete decisions.
        """
        if not changes:
            raise ValidationError("No changes recorded for this PIP.")
        if any(change.admin_decision not in _VALID_CHOICES for change in changes):
            raise ValidationError(
                "Each change must have an explicit Accept/Reject decision."
            )
        accepted = [
            change
            for change in changes
            if change.admin_decision == PipChange.ADMIN_ACCEPT
        ]
        return accepted, len(changes) - len(accepted)

    @staticmethod
    def _publish_accepted_changes(
        pip: ProcessImprovementProposal,
        accepted: list[PipChange],
        actor: AbstractBaseUser,
    ) -> None:
        """Apply approved rows, then publish exactly one version for them.

        :param pip: Locked proposal for a released playbook. Example: reviewed PIP 42.
        :param accepted: Persisted approved changes. Example: one ADD Activity.
        :param actor: Staff administrator who approved publication. Example: mchen.
        :return: None. Example: changes are stored in playbook version 3.0.
        :raises ValidationError: If a change cannot safely be applied.
        """
        PipApplyChangesService.apply_changes(
            pip=pip, accepted=accepted, playbook=pip.playbook
        )
        bump_playbook_major_version_after_pip_apply(
            pip=pip,
            playbook=pip.playbook,
            actor=actor,
            summary_line=PIPAdminService._describe_apply_summary(accepted),
        )

    @staticmethod
    def _queue_decision_email(pip_id: int) -> None:
        """Use the existing mail path once the owning transaction commits.

        :param pip_id: Finalized proposal ID. Example: 42.
        :return: None. Example: one decision callback registered after publication.
        """

        def _send_email() -> None:
            refreshed = ProcessImprovementProposal.objects.prefetch_related(
                "changes"
            ).get(pk=pip_id)
            send_decision_email(refreshed)

        transaction.on_commit(_send_email)

    @staticmethod
    def _describe_apply_summary(accepted: list[PipChange]) -> str:
        parts = []
        for ch in accepted:
            if ch.change_type in {PipChange.CHANGE_LINK, PipChange.CHANGE_UNLINK}:
                lbl = ch.target_name_snapshot or f"{ch.relationship_type} link"
            else:
                lbl = (
                    ch.name.strip()
                    or ch.target_name_snapshot.strip()
                    or f"{ch.change_type}-{ch.entity_type}"
                )
            parts.append(f"{ch.change_type} {lbl}")
        return "; ".join(parts)[:495]

    @staticmethod
    def _apply_terminal_status(
        pip_locked: ProcessImprovementProposal,
        accept_cnt: int,
        rejected_cnt: int,
    ) -> None:
        decided = timezone.now()

        if accept_cnt == 0:
            pip_locked.status = ProcessImprovementProposal.STATUS_REJECTED
        elif rejected_cnt == 0:
            pip_locked.status = ProcessImprovementProposal.STATUS_ACCEPTED
        else:
            pip_locked.status = ProcessImprovementProposal.STATUS_ACCEPTED_PARTIAL

        pip_locked.decided_at = decided
        pip_locked.save(update_fields=["status", "decided_at", "updated_at"])

    @staticmethod
    def _award_finalized_pip(
        *, pip: ProcessImprovementProposal, actor: AbstractBaseUser
    ) -> tuple[AwardOutcome, ...]:
        """Delegate finalized changes to Karma without changing publication or email.

        :param pip: Terminal proposal in the current atomic transaction. Example: PIP 42.
        :param actor: Existing authorized administrator. Example: staff account mchen.
        :return: Award outcomes. Example: one Maria 500-point outcome.
        :raises ValidationError: For invalid award attribution or immutable event conflict.
        """
        correlation_id = f"pip_finalize:{pip.pk}"
        outcomes = KarmaService.award_accepted_changes(
            pip=pip, correlation_id=correlation_id
        )
        logger.info(
            "PIPAdminService._award_finalized_pip | exit | "
            "pip_id=%s actor_id=%s recipient_id=%s correlation_id=%s transaction=pending",
            pip.pk,
            actor.pk,
            pip.created_by_id,
            correlation_id,
        )
        return outcomes
