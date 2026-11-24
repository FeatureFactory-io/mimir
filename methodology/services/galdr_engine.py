"""Galdr playbook assessment runner (daemon thread MVP + Anthropic staging)."""

from __future__ import annotations

import logging
import threading
from typing import ClassVar

from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone

from methodology.llm.base import BaseLLM
from methodology.models import PipChange, ProcessImprovementProposal
from methodology.models.agent_interaction import _CREDENTIAL
from methodology.services import galdr_client
from methodology.services.contribution_summary_boundary import _CORRELATION_ID
from methodology.services.contribution_summary_factory import (
    build_contribution_summary_service,
)
from methodology.services.galdr_client import GaldrClient, GaldrLLMError
from methodology.services.galdr_prompts import (
    build_change_prompt,
    build_playbook_context_summary,
    build_target_state_prompt,
)
from methodology.services.galdr_validator import GaldrStructuralValidator
from methodology.services.pip_apply_changes_service import PipApplyChangesService
from methodology.services.public_contribution_evidence import (
    _MAX_DATABASE_ID,
    _SENSITIVE_TEXT,
)

logger = logging.getLogger(__name__)


class GaldrEngine:
    """Background worker transitioning ``processing_galdr → reviewed``."""

    REC_CODE: ClassVar[dict[str, str]] = {
        "ACCEPT": PipChange.GALDR_ACCEPT,
        "REJECT": PipChange.GALDR_REJECT,
        "NEEDS_CLARIFICATION": PipChange.GALDR_NEEDS_CLARIFICATION,
    }

    @classmethod
    def schedule(
        cls,
        pip_id: int,
        *,
        llm: BaseLLM | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Dispatch Galdr synchronously or via the existing daemon thread.

        :param pip_id: Committed proposal ID. Example: 7301.
        :param llm: Captured processing port. Example: ScriptedLLM([...]).
        :param correlation_id: Submission correlation; absent for legacy assess-only calls.
        :return: None after scheduling.
        :raises ValueError: For a malformed proposal or correlation identifier.
        """
        if type(pip_id) is not int or not 0 < pip_id <= _MAX_DATABASE_ID:
            raise ValueError("A positive PIP ID is required.")
        if correlation_id is not None and (
            not isinstance(correlation_id, str)
            or not _CORRELATION_ID.fullmatch(correlation_id)
            or _SENSITIVE_TEXT.search(correlation_id)
            or _CREDENTIAL.search(correlation_id)
        ):
            raise ValueError("A safe processing correlation ID is required.")
        if settings.GALDR_EAGER:
            cls._run_scheduled_processing(pip_id, llm, correlation_id)
            return

        def _runner() -> None:
            close_old_connections()
            try:
                cls._run_scheduled_processing(pip_id, llm, correlation_id)
            finally:
                close_old_connections()

        threading.Thread(
            target=_runner, name=f"galdr-pip-{pip_id}", daemon=True
        ).start()
        logger.info("GaldrEngine.schedule dispatched pip id=%s", pip_id)

    @classmethod
    def _mark_submitted_retry(cls, pip_id: int) -> None:
        """Return PIP to Submitted state when synchronous assessment fails."""
        cls._rollback_to_submitted(pip_id, holistic_note="")

    @classmethod
    def _mark_submitted_with_errors(cls, pip_id: int, errors: list[str]) -> None:
        """Return PIP to Submitted after structural validation failures."""
        note = f"Structural validation failed: {'; '.join(errors)}"
        cls._rollback_to_submitted(pip_id, holistic_note=note)

    @classmethod
    def _rollback_to_submitted(cls, pip_id: int, *, holistic_note: str) -> None:
        try:
            with transaction.atomic():
                locked = ProcessImprovementProposal.objects.select_for_update().get(
                    pk=pip_id
                )
                if locked.status == ProcessImprovementProposal.STATUS_PROCESSING_GALDR:
                    locked.status = ProcessImprovementProposal.STATUS_SUBMITTED
                    update_fields = ["status", "updated_at"]
                    if holistic_note:
                        locked.galdr_holistic_assessment = holistic_note[:2000]
                        update_fields.append("galdr_holistic_assessment")
                    locked.save(update_fields=update_fields)
                    logger.warning(
                        "Galdr pip id=%s rolled back → submitted%s",
                        pip_id,
                        " (structural errors)" if holistic_note else " for retry",
                    )
        except ProcessImprovementProposal.DoesNotExist:
            logger.warning("Galdr failure handler: pip id=%s missing", pip_id)

    @classmethod
    def assess_sync(cls, pip_id: int, *, llm: BaseLLM | None = None) -> None:
        """
        Blocking assessment used by daemon thread and ``manage.py run_galdr``.

        Performs LLM turns **outside** DB locks to avoid holding rows open.

        :param pip_id: Processing proposal. Example: 7301.
        :param llm: Captured processing port or None for the existing client selector.
        :return: None after assessment or retry-state recovery.
        """
        holistic = getattr(settings, "GALDR_USE_TARGET_STATE", True)
        logger.info(
            "Galdr assessment pip=%s mode=%s",
            pip_id,
            "holistic" if holistic else "per_change",
        )
        if holistic:
            cls._assess_sync_holistic(pip_id, llm=llm)
        else:
            cls._assess_sync_per_change(pip_id, llm=llm)

    @classmethod
    def _assess_sync_per_change(
        cls, pip_id: int, *, llm: BaseLLM | None = None
    ) -> None:
        bootstrap = ProcessImprovementProposal.objects.select_related("playbook").get(
            pk=pip_id
        )
        if bootstrap.status != ProcessImprovementProposal.STATUS_PROCESSING_GALDR:
            logger.info(
                "Galdr skipped pip id=%s unexpected status=%s",
                pip_id,
                bootstrap.status,
            )
            return

        playbook = bootstrap.playbook
        summary_text = build_playbook_context_summary(playbook)
        client = (
            galdr_client.get_galdr_client()
            if llm is None
            else GaldrClient._from_port(llm)
        )

        payloads: list[tuple[int, str, str]] = []
        try:
            qs = PipChange.objects.filter(pip_id=pip_id).order_by("order", "pk")
            if not qs.exists():
                raise GaldrLLMError("PIP has zero changes.")

            changes = list(qs)
            for change in changes:
                user_prompt = build_change_prompt(
                    change,
                    summary_text,
                    all_changes=changes,
                )
                rec_text, reasoning = client.evaluate_change(user_prompt)
                rec_upper = rec_text.upper()
                if rec_upper not in cls.REC_CODE:
                    raise GaldrLLMError("Unsupported recommendation.")
                payloads.append((change.pk, rec_upper, reasoning))
        except GaldrLLMError:
            logger.warning(
                "Galdr assess LLM phase failed pip id=%s reason=assessment_failed",
                pip_id,
            )
            cls._mark_submitted_retry(pip_id)
            return
        # Preserve retry recovery for unexpected failures without private exception logs.
        except Exception:  # noqa: BLE001
            logger.error(
                "Galdr assess unexpected pip id=%s reason=assessment_failed", pip_id
            )
            cls._mark_submitted_retry(pip_id)
            return

        cls._persist_recommendations(pip_id, payloads, holistic_note="")

    @classmethod
    def _assess_sync_holistic(cls, pip_id: int, *, llm: BaseLLM | None = None) -> None:
        bootstrap = ProcessImprovementProposal.objects.select_related("playbook").get(
            pk=pip_id
        )
        if bootstrap.status != ProcessImprovementProposal.STATUS_PROCESSING_GALDR:
            logger.info(
                "Galdr holistic skipped pip id=%s unexpected status=%s",
                pip_id,
                bootstrap.status,
            )
            return

        playbook = bootstrap.playbook
        changes = list(
            PipChange.objects.filter(pip_id=pip_id).order_by("order", "pk"),
        )

        structural = GaldrStructuralValidator.validate_pip_structure(bootstrap)
        if not structural.ok:
            cls._mark_submitted_with_errors(pip_id, structural.errors)
            return

        try:
            current_summary = build_playbook_context_summary(playbook)
            target_summary, ref_map = PipApplyChangesService.build_target_state_context(
                pip=bootstrap,
                playbook=playbook,
            )
            prompt = build_target_state_prompt(
                bootstrap,
                current_summary,
                target_summary,
                changes,
                ref_map=ref_map,
            )
            client = (
                galdr_client.get_galdr_client()
                if llm is None
                else GaldrClient._from_port(llm)
            )
            holistic, payloads = client.evaluate_pip_holistically(prompt)
        except GaldrLLMError:
            logger.warning(
                "Galdr holistic LLM phase failed pip id=%s reason=assessment_failed",
                pip_id,
            )
            cls._mark_submitted_retry(pip_id)
            return
        # Preserve retry recovery for unexpected failures without private exception logs.
        except Exception:  # noqa: BLE001
            logger.error(
                "Galdr holistic unexpected pip id=%s reason=assessment_failed", pip_id
            )
            cls._mark_submitted_retry(pip_id)
            return

        for _cid, rec_upper, _why in payloads:
            if rec_upper not in cls.REC_CODE:
                logger.warning(
                    "Galdr holistic unsupported recommendation pip id=%s",
                    pip_id,
                )
                cls._mark_submitted_retry(pip_id)
                return

        holistic_note = f"{holistic['overall_coherence']}: {holistic['reasoning']}"
        cls._persist_recommendations(pip_id, payloads, holistic_note=holistic_note)

    @classmethod
    def _validate_assessment_batch(
        cls,
        pip: ProcessImprovementProposal,
        payloads: list[tuple[int, str, str]],
    ) -> None:
        """Require one valid verdict for every change before persisting any verdict.

        :param pip: Locked proposal being reviewed.
        :param payloads: Model verdicts, e.g. [(1, "ACCEPT", "Coherent")].
        :return: None for a complete batch.
        :raises GaldrLLMError: For missing, duplicate, foreign or invalid verdicts.
        """
        expected = set(pip.changes.values_list("pk", flat=True))
        received = [row[0] for row in payloads]
        complete = (
            bool(expected)
            and len(received) == len(expected)
            and set(received) == expected
        )
        valid = all(
            type(cid) is int and code in cls.REC_CODE and bool(reason.strip())
            for cid, code, reason in payloads
        )
        if not complete or not valid:
            logger.warning(
                "Galdr incomplete assessment pip=%s expected=%s received=%s",
                pip.pk,
                len(expected),
                len(received),
            )
            raise GaldrLLMError("Expected exactly one valid assessment per PIP change.")

    @classmethod
    def _persist_recommendations(
        cls,
        pip_id: int,
        payloads: list[tuple[int, str, str]],
        *,
        holistic_note: str,
    ) -> None:
        try:
            with transaction.atomic():
                pip = ProcessImprovementProposal.objects.select_for_update().get(
                    pk=pip_id
                )
                if pip.status != ProcessImprovementProposal.STATUS_PROCESSING_GALDR:
                    logger.info(
                        "Galdr aborted save pip id=%s status changed to=%s",
                        pip_id,
                        pip.status,
                    )
                    return
                cls._validate_assessment_batch(pip, payloads)
                for cid, code, reasoning in payloads:
                    rec_value = cls.REC_CODE[code]
                    PipChange.objects.filter(pk=cid, pip_id=pip_id).update(
                        galdr_recommendation=rec_value,
                        galdr_reasoning=reasoning,
                        updated_at=timezone.now(),
                    )
                pip.status = ProcessImprovementProposal.STATUS_REVIEWED
                pip.reviewed_at = timezone.now()
                update_fields = ["status", "reviewed_at", "updated_at"]
                if holistic_note:
                    pip.galdr_holistic_assessment = holistic_note[:2000]
                    update_fields.append("galdr_holistic_assessment")
                pip.save(update_fields=update_fields)
                logger.info("Galdr persisted pip id=%s → reviewed", pip_id)
        # Preserve retry recovery for unexpected failures without private exception logs.
        except Exception:  # noqa: BLE001
            logger.error(
                "Galdr DB persist pip id=%s reason=assessment_storage_failed", pip_id
            )
            cls._mark_submitted_retry(pip_id)

    @classmethod
    def _run_scheduled_processing(
        cls, pip_id: int, llm: BaseLLM | None, correlation_id: str | None
    ) -> None:
        """Execute the existing eager/thread worker with explicit dependencies.

        Preserve connection cleanup, missing-PIP handling and outer assessment
        error handling. Never inspect provider queue internals.

        :param pip_id: Processing proposal. Example: 7301.
        :param llm: Captured provider injection or None. Example: ScriptedLLM([...]).
        :param correlation_id: Safe run ID. Example: "cedar-submit-01".
        :return: None. Example: None after assess_sync.
        :raises ValueError: For malformed invocation arguments.
        """
        try:
            if correlation_id is not None:
                if llm is not None:
                    cls._refresh_contribution_summary(pip_id, llm, correlation_id)
                else:
                    logger.info(
                        "GaldrEngine._run_scheduled_processing | branch | pip_id=%s "
                        "correlation_id=%s reason=provider_disabled",
                        pip_id,
                        correlation_id,
                    )
            cls.assess_sync(pip_id, llm=llm)
        except ProcessImprovementProposal.DoesNotExist:
            logger.error("Galdr processing missing pip id=%s", pip_id)
        except Exception:  # noqa: BLE001
            logger.error(
                "Galdr processing failed pip id=%s reason=assessment_failed", pip_id
            )

    @classmethod
    def _processing_is_current(cls, pip_id: int) -> bool:
        """Check current processing state before a summary/provider turn.

        :param pip_id: Proposal identifier. Example: 7301.
        :return: Whether processing is current. Example: False for a reviewed PIP.
        :raises ValueError: For a malformed identifier.
        """
        if type(pip_id) is not int or not 0 < pip_id <= _MAX_DATABASE_ID:
            raise ValueError("A positive PIP ID is required.")
        return ProcessImprovementProposal.objects.filter(
            pk=pip_id, status=ProcessImprovementProposal.STATUS_PROCESSING_GALDR
        ).exists()

    @classmethod
    def _refresh_contribution_summary(
        cls, pip_id: int, llm: BaseLLM | None, correlation_id: str
    ) -> None:
        """Invoke S23 orchestration once before existing assessment work.

        Summary failure is isolated. Do not retry the completion, consume an
        assessment response, decide the PIP or replace existing assessment recovery.
        Log safe IDs/reason codes if composition/storage raises unexpectedly.

        :param pip_id: Current processing proposal. Example: 7301.
        :param llm: Shared explicit/scoped port or None. Example: ScriptedLLM([...]).
        :param correlation_id: Safe run ID. Example: "cedar-submit-01".
        :return: None. Example: None after success or isolated summary failure.
        :raises ValueError: For malformed boundary arguments.
        """
        try:
            if llm is not None and cls._processing_is_current(pip_id):
                build_contribution_summary_service(llm).refresh_for_submission(
                    pip_id, correlation_id
                )
        except Exception:  # noqa: BLE001
            # Summary composition/storage cannot interrupt existing assessment.
            logger.error(
                "GaldrEngine._refresh_contribution_summary | error | pip_id=%s "
                "correlation_id=%s reason_code=summary_refresh_failed",
                pip_id,
                correlation_id,
            )
