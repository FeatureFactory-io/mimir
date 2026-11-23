from __future__ import annotations

"""Read-only public-summary completion; lifecycle and persistence live elsewhere."""
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from methodology.llm.base import BaseLLM, LLMResponse
from methodology.services.contribution_summary_prompts import SummaryPrompt
from methodology.services.public_contribution_evidence import (
    PublicContributionEvidenceService,
)


@dataclass(frozen=True)
class SummaryTraceEvent:
    """Body-free control event; details contain safe identifiers/reason codes."""

    beat: str
    details: str


@dataclass(frozen=True)
class SummaryBoundaryResult:
    """Successful validated text, normalized response and immutable control trace."""

    text: str
    response: LLMResponse
    trace: tuple[SummaryTraceEvent, ...]


class SummaryBoundaryError(RuntimeError):
    """Sanitized failure with partial trace and optional normalized response."""

    code: str
    trace: tuple[SummaryTraceEvent, ...]
    response: LLMResponse | None

    def __init__(
        self,
        code: str,
        trace: tuple[SummaryTraceEvent, ...],
        response: LLMResponse | None = None,
    ) -> None:
        """Construct a body-free failure without raw provider exception text.

        :param code: Stable safe reason. Example: "output_validation_failed".
        :param trace: Actual partial events. Example: entry through failure/exit.
        :param response: Normalized response or None. Example: rejected response.
        :return: None.
        :raises ValueError: For invalid failure metadata.
        """
        raise NotImplementedError()


class PublicContributionSummaryBoundary:
    """Compose one read-only completion through explicit dependencies."""

    def __init__(self, evidence_service: PublicContributionEvidenceService) -> None:
        """Inject the real evidence collaborator.

        :param evidence_service: Public DB query service. Example: real service.
        :return: None.
        :raises ValueError: For missing/invalid dependency.
        """
        raise NotImplementedError()

    def complete(
        self, subject_id: int, *, llm: BaseLLM, correlation_id: str
    ) -> SummaryBoundaryResult:
        """Collect, build, complete once and validate without domain writes.

        :param subject_id: Positive user ID. Example: 42.
        :param llm: Injected CAP-001 provider. Example: ScriptedLLM in proofs.
        :param correlation_id: Safe run identifier. Example: "s27-proof-01".
        :return: Validated result and actual trace. Example: Maria's paragraph.
        :raises SummaryBoundaryError: For sanitized preflight/provider/output failure.
        """
        raise NotImplementedError()

    def _validate_request(
        self, subject_id: int, llm: BaseLLM, correlation_id: str
    ) -> None:
        """Validate boundary inputs without consuming a model turn.

        :param subject_id: User ID. Example: 42.
        :param llm: CAP-001 collaborator. Example: ScriptedLLM.
        :param correlation_id: Safe identifier. Example: "s27-proof-01".
        :return: None when valid.
        :raises ValueError: For malformed inputs.
        """
        raise NotImplementedError()

    def _complete_once(self, prompt: SummaryPrompt, llm: BaseLLM) -> LLMResponse:
        """Invoke the sole provider seam with no offered tools.

        :param prompt: Valid layered request. Example: Maria's public request.
        :param llm: CAP-001 provider. Example: ScriptedLLM.
        :return: Normalized response. Example: completed public prose.
        :raises Exception: Provider failures are sanitized by complete.
        """
        raise NotImplementedError()

    def _freeze_response(self, response: LLMResponse) -> LLMResponse:
        """Copy response usage into an immutable normalized mapping.

        :param response: Port response. Example: prose with usage metadata.
        :return: Frozen normalized response. Example: response with immutable usage.
        :raises ValueError: For malformed normalized data.
        """
        raise NotImplementedError()

    def _failure(
        self,
        code: str,
        trace: tuple[SummaryTraceEvent, ...],
        response: LLMResponse | None,
    ) -> SummaryBoundaryError:
        """Build failure/exit trace events with a safe reason code.

        :param code: Stable reason. Example: "provider_failed".
        :param trace: Actual preceding events. Example: entry and llm_call.
        :param response: Result if one exists. Example: None on provider error.
        :return: Typed sanitized failure. Example: SummaryBoundaryError.
        :raises ValueError: For invalid failure metadata.
        """
        raise NotImplementedError()


def trace_as_agent_story(trace: tuple[SummaryTraceEvent, ...]) -> Mapping[str, Any]:
    """Adapt actual immutable events for the existing assertion helper.

    :param trace: Production events. Example: successful completion events.
    :return: workflow_id/events mapping. Example: contribution_summary trace.
    :raises ValueError: For invalid event shapes.
    """
    raise NotImplementedError()
