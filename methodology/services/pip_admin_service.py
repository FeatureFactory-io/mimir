"""Administrative finalisation — apply typed PIP changes + major version bump."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import transaction
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


class PIPAdminService:
    """Apply administrator decisions atomically."""

    @staticmethod
    @transaction.atomic
    def finalize_pip(
        pip: ProcessImprovementProposal, actor: AbstractBaseUser | None
    ) -> ProcessImprovementProposal:
        """Apply reviewed choices, award eligible changes and schedule decision mail.

        :param pip: Reviewed proposal with per-change decisions. Example: PIP 42.
        :param actor: Staff user invoking finalisation. Example: mchen.
        :return: Persisted proposal in a terminal state. Example: accepted PIP 42.
        :raises ValidationError: For insufficient permission, invalid decisions or award conflicts.
        """
        if actor is None or not actor.is_staff:
            raise ValidationError("Only staff administrators can finalise PIPs.")

        locked = (
            ProcessImprovementProposal.objects.select_for_update(of=("self",))
            .select_related("playbook", "created_by")
            .get(pk=pip.pk)
        )
        accepted, rejected_count = PIPAdminService._reviewed_decisions(locked)
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
    def _reviewed_decisions(
        pip: ProcessImprovementProposal,
    ) -> tuple[list[PipChange], int]:
        """Read decisions under lock so apply and publication use the same approvals.

        :param pip: Locked target proposal. Example: reviewed PIP 42.
        :return: Ordered accepted changes and rejected count. Example: ([change], 1).
        :raises ValidationError: If the proposal or its decisions are incomplete.
        """
        if pip.status != ProcessImprovementProposal.STATUS_REVIEWED:
            raise ValidationError("PIP must be in Reviewed state before finalising.")
        changes = list(pip.changes.select_for_update().order_by("order", "pk"))
        if not changes:
            raise ValidationError("No changes recorded for this PIP.")
        if any(
            change.admin_decision
            not in (PipChange.ADMIN_ACCEPT, PipChange.ADMIN_REJECT)
            for change in changes
        ):
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
