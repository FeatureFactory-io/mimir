"""Read-only public-summary completion; lifecycle and persistence live elsewhere."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any

from django.db import DatabaseError

from methodology.llm.base import BaseLLM, LLMError, LLMResponse
from methodology.services.contribution_summary_prompts import (
    SummaryPrompt,
    build_summary_prompt,
    validate_summary_response,
)
from methodology.services.public_contribution_evidence import (
    _MAX_DATABASE_ID,
    _SENSITIVE_TEXT,
    PublicContributionEvidenceService,
)

logger = logging.getLogger(__name__)

_COMPLETE = "PublicContributionSummaryBoundary.complete"
_CORRELATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
_MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}")
_STOP_REASON = re.compile(r"[a-z][a-z0-9_]{0,39}")
_FAILURE_CODES = frozenset(
    {
        "invalid_request",
        "public_evidence_failed",
        "provider_failed",
        "output_validation_failed",
    }
)
_TOKEN_USAGE_KEYS = ("input_tokens", "output_tokens")


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
        :param response: Body-free received metadata or None. Example: response usage on rejection.
        :return: None.
        :raises ValueError: For invalid failure metadata.
        """
        if (
            not isinstance(code, str)
            or code not in _FAILURE_CODES
            or not isinstance(trace, tuple)
            or any(not isinstance(event, SummaryTraceEvent) for event in trace)
            or (response is not None and not isinstance(response, LLMResponse))
        ):
            raise ValueError("Invalid summary failure metadata.")
        super().__init__(code)
        self.code = code
        self.trace = trace
        self.response = (
            replace(response, content="", thinking="") if response is not None else None
        )


class PublicContributionSummaryBoundary:
    """Compose one read-only completion through explicit dependencies."""

    def __init__(self, evidence_service: PublicContributionEvidenceService) -> None:
        """Inject the real evidence collaborator.

        :param evidence_service: Public DB query service. Example: real service.
        :return: None.
        :raises ValueError: For missing/invalid dependency.
        """
        if not isinstance(evidence_service, PublicContributionEvidenceService):
            raise ValueError(  # noqa: TRY004
                "A public contribution evidence service is required."
            )
        self._evidence_service = evidence_service

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
        response = None
        code = "invalid_request"
        trace: tuple[SummaryTraceEvent, ...] = ()
        try:
            self._validate_request(subject_id, llm, correlation_id)
            details = f"subject_id={subject_id} correlation_id={correlation_id}"
            trace = (SummaryTraceEvent("entry", details),)
            logger.info("%s | entry | %s", _COMPLETE, details)
            code = "public_evidence_failed"
            evidence = self._evidence_service.collect(subject_id)
            prompt = build_summary_prompt(evidence)
            public_scope = f"scope=public_released fact_count={len(evidence.facts)}"
            trace += (SummaryTraceEvent("public_evidence", public_scope),)
            code = "provider_failed"
            call = f"model={llm.model_id} tools=none max_tokens={prompt.max_tokens}"
            trace += (SummaryTraceEvent("llm_call", call),)
            logger.info("%s | processing | %s %s", _COMPLETE, details, call)
            raw_response = self._complete_once(prompt, llm)
            code = "output_validation_failed"
            response = self._freeze_response(raw_response)
            text = validate_summary_response(response, evidence)
        except (ValueError, LLMError, DatabaseError):
            failure = self._failure(code, trace, response)
        else:
            logger.info("%s | exit | %s outcome=success", _COMPLETE, details)
            validation = SummaryTraceEvent("validation", "status=accepted")
            trace += (validation, SummaryTraceEvent("exit", "outcome=success"))
            return SummaryBoundaryResult(text, replace(response, content=text), trace)
        raise failure

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
        if type(subject_id) is not int or not 0 < subject_id <= _MAX_DATABASE_ID:
            raise ValueError("A positive integer subject ID is required.")
        if (
            not isinstance(correlation_id, str)
            or not _CORRELATION_ID.fullmatch(correlation_id)
            or _SENSITIVE_TEXT.search(correlation_id)
        ):
            raise ValueError("A safe correlation ID is required.")
        if (
            not isinstance(llm, BaseLLM)
            or not callable(llm.complete)
            or not isinstance(llm.model_id, str)
            or not _MODEL_ID.fullmatch(llm.model_id)
            or _SENSITIVE_TEXT.search(llm.model_id)
        ):
            raise ValueError("A completion port with a safe model ID is required.")

    def _complete_once(self, prompt: SummaryPrompt, llm: BaseLLM) -> LLMResponse:
        """Invoke the sole provider seam with no offered tools.

        :param prompt: Valid layered request. Example: Maria's public request.
        :param llm: CAP-001 provider. Example: ScriptedLLM.
        :return: Normalized response. Example: completed public prose.
        :raises LLMError: If the provider fails.
        """
        try:
            return llm.complete(
                prompt.messages, system=prompt.system, max_tokens=prompt.max_tokens
            )
        except Exception:  # noqa: BLE001
            # Keep raw provider details out of the boundary's error contract.
            raise LLMError("Summary provider failed.") from None

    def _freeze_response(self, response: LLMResponse) -> LLMResponse:
        """Copy response usage into an immutable normalized mapping.

        :param response: Port response. Example: prose with usage metadata.
        :return: Frozen normalized response. Example: response with immutable usage.
        :raises ValueError: For malformed normalized data.
        """
        if (
            not isinstance(response, LLMResponse)
            or not isinstance(response.usage, Mapping)
            or not isinstance(response.model, str)
            or (response.model and not _MODEL_ID.fullmatch(response.model))
            or _SENSITIVE_TEXT.search(response.model)
            or not isinstance(response.stop_reason, str)
            or not _STOP_REASON.fullmatch(response.stop_reason)
            or _SENSITIVE_TEXT.search(response.stop_reason)
        ):
            raise ValueError("Malformed completion metadata.")
        usage = {
            key: response.usage[key]
            for key in _TOKEN_USAGE_KEYS
            if key in response.usage
        }
        if any(type(value) is not int or value < 0 for value in usage.values()):
            raise ValueError("Malformed completion token usage.")
        return replace(response, usage=MappingProxyType(usage), thinking="")

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
        if not trace:
            details = "subject_id=unvalidated correlation_id=unvalidated"
            trace = (SummaryTraceEvent("entry", details),)
            logger.info("%s | entry | %s", _COMPLETE, details)
        reason = f"reason_code={code}"
        outcome = "outcome=failure"
        trace += (
            SummaryTraceEvent("failure", reason),
            SummaryTraceEvent("exit", outcome),
        )
        failure = SummaryBoundaryError(code, trace, response)
        logger.info(
            "%s | error | %s %s %s", _COMPLETE, trace[0].details, reason, outcome
        )
        logger.info("%s | exit | %s %s", _COMPLETE, trace[0].details, outcome)
        return failure


def trace_as_agent_story(trace: tuple[SummaryTraceEvent, ...]) -> Mapping[str, Any]:
    """Adapt actual immutable events for the existing assertion helper.

    :param trace: Production events. Example: successful completion events.
    :return: workflow_id/events mapping. Example: contribution_summary trace.
    :raises ValueError: For invalid event shapes.
    """
    if (
        not isinstance(trace, tuple)
        or not trace
        or any(
            not isinstance(event, SummaryTraceEvent)
            or not isinstance(event.beat, str)
            or not event.beat
            or not isinstance(event.details, str)
            or not event.details
            for event in trace
        )
    ):
        raise ValueError("Invalid contribution summary trace.")
    return {
        "workflow_id": "contribution_summary",
        "events": [{"beat": event.beat, "details": event.details} for event in trace],
    }
