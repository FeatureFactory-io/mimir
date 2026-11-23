from __future__ import annotations

"""The single composition point for summary processing and provider injection."""
from collections.abc import Mapping
from decimal import Decimal
from typing import Any
from methodology.llm.base import BaseLLM
from methodology.services.contribution_summary_service import ContributionSummaryService


def resolve_processing_llm(injected: BaseLLM | None = None) -> BaseLLM | None:
    """Resolve explicit/scoped injection without changing legacy default selection.

    Precedence: explicit argument, CONTRIBUTION_SUMMARY_LLM setting, then None.
    None means the summary factory uses the configured production adapter,
    while existing Galdr assessment retains its existing client selection.

    :param injected: Optional explicit port. Example: ScriptedLLM([...]).
    :return: Selected injected port or None. Example: the scoped ScriptedLLM.
    :raises ValueError: For an injected/configured object outside BaseLLM.
    """
    raise NotImplementedError()


def build_contribution_summary_service(
    llm: BaseLLM | None = None,
) -> ContributionSummaryService:
    """Assemble the real S27 boundary and S23 storage orchestrator.

    No evidence, prompt, validator, scheduler or ORM collaborator is replaced
    by the test setting. The selected port is the only substitution.

    :param llm: Optional selected port. Example: ScriptedLLM([...]).
    :return: Real orchestrator. Example: ContributionSummaryService(...).
    :raises ValueError: For invalid dependencies or configured rates.
    """
    raise NotImplementedError()


def _configured_summary_llm() -> BaseLLM:
    """Create the configured server-side Anthropic adapter without calling it.

    :return: Provider port. Example: AnthropicAdapter(settings.GALDR_MODEL).
    :raises ValueError: For invalid model configuration.
    """
    raise NotImplementedError()


def configured_summary_rates() -> Mapping[str, tuple[Decimal, Decimal]]:
    """Read optional per-model USD rates per million input/output tokens.

    An absent model/rate is unknown. Empty settings must not generate a
    zero-price entry.

    :return: Validated rates. Example: {"scripted": (Decimal("3"), Decimal("15"))}.
    :raises ValueError: For malformed, negative or nonfinite rates.
    """
    raise NotImplementedError()


def _parse_model_rates(
    raw: Mapping[str, tuple[str, str]],
) -> Mapping[str, tuple[Decimal, Decimal]]:
    """Validate and freeze explicitly configured model rate pairs.

    :param raw: Model-to-string-rate pairs. Example: {"scripted": ("3", "15")}.
    :return: Decimal rates. Example: {"scripted": (Decimal("3"), Decimal("15"))}.
    :raises ValueError: For invalid keys, incomplete pairs or invalid amounts.
    """
    raise NotImplementedError()


def _validate_port(value: Any) -> BaseLLM:
    """Require the actual CAP-001 complete protocol and a model identifier.

    :param value: Candidate provider. Example: ScriptedLLM([...]).
    :return: Validated provider. Example: the same ScriptedLLM instance.
    :raises ValueError: For invalid port objects.
    """
    raise NotImplementedError()
