from __future__ import annotations

"""Persist the S27 boundary result without acquiring model/domain capabilities."""
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from django.utils import timezone
from methodology.llm.base import BaseLLM, LLMResponse
from methodology.models import ExpertProfile
from methodology.services.contribution_summary_boundary import (
    PublicContributionSummaryBoundary,
    SummaryBoundaryError,
    SummaryBoundaryResult,
    SummaryTraceEvent,
)


@dataclass(frozen=True)
class SummaryRefreshResult:
    """Safe attempt result; contains no generated prose or provider error body."""

    outcome: str
    summary_updated: bool
    interaction_id: int | None
    correlation_id: str


class ContributionSummaryService:
    """Delegate once, preserve last-good prose and persist independent telemetry."""

    def __init__(
        self,
        boundary: PublicContributionSummaryBoundary,
        llm: BaseLLM,
        rates: Mapping[str, tuple[Decimal, Decimal]],
        clock: Callable[[], float],
    ) -> None:
        """Inject the real completion boundary, provider, rates and monotonic clock.

        :param boundary: S27 read-only collaborator. Example: PublicContributionSummaryBoundary(...).
        :param llm: Sole provider seam. Example: ScriptedLLM([...]).
        :param rates: Optional model rates. Example: {} for unknown.
        :param clock: Monotonic seconds. Example: time.monotonic.
        :return: None. Example: None.
        :raises ValueError: For invalid dependencies.
        """
        raise NotImplementedError()

    def refresh_for_submission(
        self, pip_id: int, correlation_id: str
    ) -> SummaryRefreshResult:
        """Refresh once for a valid processing PIP, without deciding or awarding.

        Validate IDs, load the real submitter, then delegate exactly once to
        S27. Successful storage replaces text/time together. Failed attempts
        retain both last-good fields and record safe failure metadata.
        Provider work occurs outside row locks.

        :param pip_id: Processing proposal ID. Example: 7301.
        :param correlation_id: Safe ID of at most 100 characters. Example: "cedar-submit-01".
        :return: Safe outcome. Example: SummaryRefreshResult("success", True, 8, "cedar-submit-01").
        :raises ValueError: For malformed boundary identifiers.
        """
        raise NotImplementedError()

    @staticmethod
    def _validate_identifiers(pip_id: int, correlation_id: str) -> None:
        """Reject invalid IDs before querying or consuming a provider turn.

        :param pip_id: Positive proposal ID. Example: 7301.
        :param correlation_id: Safe bounded run ID. Example: "cedar-submit-01".
        :return: None. Example: None for valid IDs.
        :raises ValueError: For invalid IDs, including booleans.
        """
        raise NotImplementedError()

    @staticmethod
    def _processing_subject(pip_id: int) -> int | None:
        """Read the submitter only for an existing processing_galdr proposal.

        A stale/missing/creatorless proposal returns None without a boundary
        call. This does not expand PIP permissions or manufacture an actor.

        :param pip_id: Positive proposal ID. Example: 7301.
        :return: Real creator ID or None. Example: 42.
        :raises ValueError: For a malformed proposal ID.
        """
        raise NotImplementedError()

    def _complete_boundary(
        self, subject_id: int, correlation_id: str
    ) -> SummaryBoundaryResult:
        """Delegate once to S27 with the injected port; add no model path.

        :param subject_id: Real submitter ID. Example: 42.
        :param correlation_id: Safe run identifier. Example: "cedar-submit-01".
        :return: S27 result. Example: SummaryBoundaryResult(text, response, trace).
        :raises SummaryBoundaryError: For sanitized boundary failure.
        """
        raise NotImplementedError()

    def _store_completed(
        self,
        subject_id: int,
        pip_id: int,
        correlation_id: str,
        completed: SummaryBoundaryResult,
        started_at: float,
    ) -> SummaryRefreshResult:
        """Persist success or route storage failure through safe recovery.

        Measured latency covers the bounded completion boundary, including its
        query/prompt/validation work; it is not advertised as vendor-only latency.

        :param subject_id: Profile owner. Example: 42.
        :param pip_id: Trigger proposal. Example: 7301.
        :param correlation_id: Safe run ID. Example: "cedar-submit-01".
        :param completed: Authentic validated S27 result. Example: completed prose.
        :param started_at: Monotonic boundary start. Example: 100.0.
        :return: Stored success or recovered failure. Example: success result.
        :raises ValueError: For inconsistent internal metadata.
        """
        raise NotImplementedError()

    def _persist_success(
        self,
        subject_id: int,
        pip_id: int,
        correlation_id: str,
        completed: SummaryBoundaryResult,
        latency_ms: Decimal,
    ) -> SummaryRefreshResult:
        """Atomically update last-good fields and persist the completed trace.

        Lock/create ExpertProfile after completion. Preserve S27 events, append
        an actual domain_write after the save and an orchestration exit, then
        create AgentInteraction in the same transaction. No award writes occur.

        :param subject_id: Profile owner. Example: 42.
        :param pip_id: Trigger proposal. Example: 7301.
        :param correlation_id: Safe run ID. Example: "cedar-submit-01".
        :param completed: Validated boundary result. Example: public paragraph.
        :param latency_ms: Measured boundary duration. Example: Decimal("125.000").
        :return: Safe success result. Example: SummaryRefreshResult("success", True, 8, "cedar-submit-01").
        :raises DatabaseError: When atomic storage fails.
        """
        raise NotImplementedError()

    def _handle_boundary_failure(
        self,
        subject_id: int,
        pip_id: int,
        correlation_id: str,
        error: SummaryBoundaryError,
        started_at: float,
    ) -> SummaryRefreshResult:
        """Preserve the authentic partial trace and recover without another turn.

        :param subject_id: Profile owner. Example: 42.
        :param pip_id: Trigger proposal. Example: 7301.
        :param correlation_id: Safe run ID. Example: "cedar-submit-01".
        :param error: S27 sanitized typed error. Example: code="provider_failed".
        :param started_at: Monotonic boundary start. Example: 100.0.
        :return: Failure result. Example: SummaryRefreshResult("failure", False, 9, "cedar-submit-01").
        :raises ValueError: For inconsistent internal metadata.
        """
        raise NotImplementedError()

    def _record_failure(
        self,
        subject_id: int,
        pip_id: int,
        correlation_id: str,
        code: str,
        trace: tuple[SummaryTraceEvent, ...],
        response: LLMResponse | None,
        latency_ms: Decimal,
    ) -> SummaryRefreshResult:
        """Attempt failure storage, retaining last-good prose even if storage fails.

        Append orchestration failure/exit without rewriting S27 events. If
        recording itself fails, emit a body-free storage-failure log and return
        interaction_id=None; existing Galdr assessment must still proceed.

        :param subject_id: Profile owner. Example: 42.
        :param pip_id: Trigger proposal. Example: 7301.
        :param correlation_id: Safe run ID. Example: "cedar-submit-01".
        :param code: Sanitized reason. Example: "provider_failed".
        :param trace: Authentic partial boundary events. Example: entry and llm_call.
        :param response: Available normalized response. Example: None on provider error.
        :param latency_ms: Measured elapsed duration. Example: Decimal("125").
        :return: Safe failure result. Example: SummaryRefreshResult("failure", False, None, "cedar-submit-01").
        :raises ValueError: For an invalid internal reason code.
        """
        raise NotImplementedError()

    def _persist_failure(
        self,
        subject_id: int,
        pip_id: int,
        correlation_id: str,
        code: str,
        trace: tuple[SummaryTraceEvent, ...],
        response: LLMResponse | None,
        latency_ms: Decimal,
    ) -> int:
        """Atomically update failure metadata and create a body-free interaction.

        Do not assign contribution_summary or summary_updated_at. Record
        summary_status=FAILURE, summary_error_code and correlation only.

        :param subject_id: Profile owner. Example: 42.
        :param pip_id: Trigger proposal. Example: 7301.
        :param correlation_id: Safe run ID. Example: "cedar-submit-01".
        :param code: Sanitized reason. Example: "output_validation_failed".
        :param trace: Completed failure trace. Example: partial boundary plus failure/exit.
        :param response: Optional received response. Example: rejected LLMResponse.
        :param latency_ms: Measured duration. Example: Decimal("125").
        :return: Persisted interaction ID. Example: 9.
        :raises DatabaseError: When storage fails.
        """
        raise NotImplementedError()

    @staticmethod
    def _lock_profile(subject_id: int) -> ExpertProfile:
        """Create if needed and lock the one-to-one profile inside the caller's atomic.

        :param subject_id: Existing account ID. Example: 42.
        :return: Locked profile. Example: Maria's ExpertProfile.
        :raises DatabaseError: For failed creation/locking.
        """
        raise NotImplementedError()

    @staticmethod
    def _write_success_profile(
        profile: ExpertProfile,
        text: str,
        correlation_id: str,
        updated_at: timezone.datetime,
    ) -> None:
        """Update only canonical S03 summary fields after boundary validation.

        Set contribution_summary, summary_updated_at, SUCCESS status, empty
        error code and last_summary_correlation_id. Numeric/account data stay
        outside this write.

        :param profile: Locked profile. Example: Maria's ExpertProfile.
        :param text: Validated last-good replacement. Example: "Published facts.".
        :param correlation_id: Safe run ID. Example: "cedar-submit-01".
        :param updated_at: Successful refresh time. Example: timezone.now().
        :return: None. Example: None after saving selected fields.
        :raises DatabaseError: When the save fails.
        """
        raise NotImplementedError()

    @staticmethod
    def _write_failure_profile(
        profile: ExpertProfile, code: str, correlation_id: str
    ) -> None:
        """Update failure metadata while preserving last-good text and time.

        :param profile: Locked profile. Example: Maria's ExpertProfile.
        :param code: Sanitized error category. Example: "provider_failed".
        :param correlation_id: Safe run ID. Example: "cedar-submit-01".
        :return: None. Example: None after metadata-only save.
        :raises DatabaseError: When the metadata save fails.
        """
        raise NotImplementedError()

    @staticmethod
    def _append_event(
        trace: tuple[SummaryTraceEvent, ...], beat: str, details: str
    ) -> tuple[SummaryTraceEvent, ...]:
        """Preserve authentic S27 events and append one safe lifecycle event.

        Boundary exit events describe completion; the appended exit describes
        orchestration/storage. Do not remove/reorder existing events.

        :param trace: Authentic events. Example: completed boundary trace.
        :param beat: Lifecycle beat. Example: "domain_write".
        :param details: Safe identifiers/outcome. Example: "profile_id=42 summary_updated=true".
        :return: Extended immutable trace. Example: boundary events plus domain_write.
        :raises ValueError: For unsupported beats or unsafe details.
        """
        raise NotImplementedError()

    @staticmethod
    def _serialize_trace(trace: tuple[SummaryTraceEvent, ...]) -> list[dict[str, str]]:
        """Serialize safe event pairs without copying response/thinking bodies.

        :param trace: Authentic immutable events. Example: boundary plus domain_write.
        :return: JSON-compatible event objects. Example: [{"beat": "exit", "details": "outcome=success"}].
        :raises ValueError: For malformed or unsafe trace data.
        """
        raise NotImplementedError()

    def _interaction_values(
        self, response: LLMResponse | None, latency_ms: Decimal
    ) -> dict[str, Any]:
        """Normalize supplied usage and optional configured-rate cost.

        :param response: Available response. Example: None on provider failure.
        :param latency_ms: Measured bounded-call duration. Example: Decimal("125").
        :return: Safe measurement fields. Example: {"input_tokens": None, "estimated_cost_usd": None}.
        :raises ValueError: For invalid normalized metadata.
        """
        raise NotImplementedError()

    def _estimated_cost(
        self, model: str, input_tokens: int | None, output_tokens: int | None
    ) -> Decimal | None:
        """Calculate cost only when both usage and model rates are known.

        :param model: Normalized model ID. Example: "scripted".
        :param input_tokens: Supplied usage or unknown. Example: 120.
        :param output_tokens: Supplied usage or unknown. Example: 40.
        :return: Estimated USD or unknown. Example: None without rates.
        :raises ValueError: For invalid negative token counts.
        """
        raise NotImplementedError()

    def _elapsed_ms(self, started_at: float) -> Decimal:
        """Measure nonnegative monotonic boundary duration.

        :param started_at: Captured start. Example: 100.0.
        :return: Milliseconds. Example: Decimal("125.000").
        :raises ValueError: For invalid/nonmonotonic measurements.
        """
        raise NotImplementedError()
