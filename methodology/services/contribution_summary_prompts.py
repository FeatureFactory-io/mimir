from __future__ import annotations

"""Layered summary prompts and deterministic response validation."""
from dataclasses import dataclass
from methodology.llm.base import LLMMessage, LLMResponse
from methodology.services.public_contribution_evidence import PublicContributionEvidence

MAX_SUMMARY_TOKENS = 1024
MAX_SUMMARY_SENTENCES = 14


@dataclass(frozen=True)
class SummaryPrompt:
    """Immutable provider-neutral request with explicitly bounded output."""

    system: str
    messages: tuple[LLMMessage, ...]
    max_tokens: int = MAX_SUMMARY_TOKENS


def build_summary_prompt(evidence: PublicContributionEvidence) -> SummaryPrompt:
    """Build foundation, identity and data layers from public evidence only.

    :param evidence: Valid public snapshot. Example: Maria's published facts.
    :return: Layered immutable request. Example: SummaryPrompt(system, messages).
    :raises ValueError: For malformed or oversized evidence.
    """
    raise NotImplementedError()


def serialize_public_evidence(evidence: PublicContributionEvidence) -> str:
    """Serialize only explicit public DTO fields in deterministic order.

    :param evidence: Immutable snapshot. Example: Maria's public facts.
    :return: Bounded JSON data. Example: '{"subject_id":42,"facts":[...]}'.
    :raises ValueError: For malformed fields or serialized size above 24,000.
    """
    raise NotImplementedError()


def _foundation_policy() -> str:
    """Return safety rules separating evidence data from instructions.

    :return: Safety layer. Example: instructions prohibiting private/score prose.
    :raises RuntimeError: If the required policy is unavailable.
    """
    raise NotImplementedError()


def _identity_policy() -> str:
    """Return fixed public-summarizer identity and output requirements.

    :return: Identity layer. Example: bounded public contribution summarizer.
    :raises RuntimeError: If required role policy is unavailable.
    """
    raise NotImplementedError()


def validate_summary_response(
    response: LLMResponse, evidence: PublicContributionEvidence
) -> str:
    """Validate bounded plain public prose before any persistence.

    :param response: Normalized model result. Example: public contribution prose.
    :param evidence: Exact request snapshot. Example: Maria's published facts.
    :return: Validated paragraph. Example: "Maria maintains Accessibility Audit."
    :raises ValueError: For malformed, truncated, unsafe or overlong output.
    """
    raise NotImplementedError()


def _validate_plain_prose(response: LLMResponse) -> str:
    """Reject empty, truncated or unexpectedly marked-up output.

    :param response: Normalized model result. Example: a completed paragraph.
    :return: Stripped plain paragraph. Example: "Maria maintains Accessibility Audit."
    :raises ValueError: For invalid result shape, markup or incomplete output.
    """
    raise NotImplementedError()


def _validate_sensitive_and_score_claims(
    text: str, evidence: PublicContributionEvidence
) -> None:
    """Reject recognizable sensitive material and mutable aggregate claims.

    :param text: Plain output. Example: "Maria maintains Accessibility Audit."
    :param evidence: Exact public snapshot. Example: Maria's published facts.
    :return: None for acceptable output.
    :raises ValueError: For sensitive material or score/count claims.
    """
    raise NotImplementedError()


def _count_sentences(text: str) -> int:
    """Count prose sentences consistently for the fourteen-sentence limit.

    :param text: Plain paragraph. Example: "Maria maintains a playbook."
    :return: Sentence count. Example: 1.
    :raises ValueError: For non-string input.
    """
    raise NotImplementedError()
