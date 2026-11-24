"""The single composition point for summary processing and provider injection."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from time import monotonic
from types import MappingProxyType

from django.conf import settings

from methodology.llm.anthropic_adapter import AnthropicAdapter
from methodology.llm.base import BaseLLM
from methodology.models.agent_interaction import _CREDENTIAL
from methodology.services.contribution_summary_boundary import (
    _MODEL_ID,
    PublicContributionSummaryBoundary,
)
from methodology.services.contribution_summary_service import ContributionSummaryService
from methodology.services.public_contribution_evidence import (
    _SENSITIVE_TEXT,
    PublicContributionEvidenceService,
)

logger = logging.getLogger(__name__)


def resolve_processing_llm(injected: BaseLLM | None = None) -> BaseLLM | None:
    """Resolve explicit/scoped injection without changing legacy default selection.

    Precedence: explicit argument, CONTRIBUTION_SUMMARY_LLM setting, then None.
    None means the summary factory uses the configured production adapter,
    while existing Galdr assessment retains its existing client selection.

    :param injected: Optional explicit port. Example: ScriptedLLM([...]).
    :return: Selected injected port or None. Example: the scoped ScriptedLLM.
    :raises ValueError: For an injected/configured object outside BaseLLM.
    """
    selected = injected if injected is not None else settings.CONTRIBUTION_SUMMARY_LLM
    if selected is None:
        logger.info("resolve_processing_llm | config | source=default")
        return None
    port = _validate_port(selected)
    logger.info(
        "resolve_processing_llm | config | source=%s",
        "explicit" if injected is not None else "setting",
    )
    return port


def build_contribution_summary_service(
    llm: BaseLLM | None = None,
) -> ContributionSummaryService:
    """Assemble the real S27 boundary and S23 storage orchestrator.

    No evidence, prompt, validator, scheduler or ORM collaborator is replaced
    by the test setting. Callers resolve any scoped port before dispatch.

    :param llm: Optional selected port. Example: ScriptedLLM([...]).
    :return: Real orchestrator. Example: ContributionSummaryService(...).
    :raises ValueError: For invalid dependencies or configured rates.
    """
    selected = _configured_summary_llm() if llm is None else _validate_port(llm)
    rates = configured_summary_rates()
    logger.info(
        "build_contribution_summary_service | config | workflow=contribution_summary rate_models=%s",
        len(rates),
    )
    return ContributionSummaryService(
        boundary=PublicContributionSummaryBoundary(PublicContributionEvidenceService()),
        llm=selected,
        rates=rates,
        clock=monotonic,
    )


def _configured_summary_llm() -> BaseLLM:
    """Create the configured server-side Anthropic adapter without calling it.

    :return: Provider port. Example: AnthropicAdapter(settings.GALDR_MODEL).
    :raises ValueError: For invalid model configuration.
    """
    return _validate_port(AnthropicAdapter(settings.GALDR_MODEL))


def configured_summary_rates() -> Mapping[str, tuple[Decimal, Decimal]]:
    """Read optional per-model USD rates per million input/output tokens.

    An absent model/rate is unknown. Empty settings must not generate a
    zero-price entry.

    :return: Validated rates. Example: {"scripted": (Decimal("3"), Decimal("15"))}.
    :raises ValueError: For malformed, negative or nonfinite rates.
    """
    raw = settings.CONTRIBUTION_SUMMARY_MODEL_RATES
    if isinstance(raw, str):
        try:
            raw = json.loads(raw, parse_float=Decimal) if raw.strip() else {}
        except ValueError:
            raise ValueError("Invalid contribution summary model rates JSON.") from None
    return _parse_model_rates(raw)


def _parse_model_rates(
    raw: object,
) -> Mapping[str, tuple[Decimal, Decimal]]:
    """Validate and freeze explicitly configured model rate pairs.

    :param raw: Decoded model-to-rate pairs. Example: {"scripted": ("3", "15")}.
    :return: Decimal rates. Example: {"scripted": (Decimal("3"), Decimal("15"))}.
    :raises ValueError: For invalid keys, incomplete pairs or invalid amounts.
    """
    if not isinstance(raw, Mapping):
        raise ValueError(  # noqa: TRY004
            "Contribution summary model rates must be a model-to-pair mapping."
        )
    rates: dict[str, tuple[Decimal, Decimal]] = {}
    for model, pair in raw.items():
        if (
            not isinstance(model, str)
            or not _MODEL_ID.fullmatch(model)
            or _SENSITIVE_TEXT.search(model)
            or not isinstance(pair, (list, tuple))
            or len(pair) != 2
            or any(type(value) not in (Decimal, float, int, str) for value in pair)
        ):
            raise ValueError(
                "Contribution summary model rates require a valid model and two amounts."
            )
        try:
            per_input, per_output = (Decimal(str(value)) for value in pair)
        except InvalidOperation:
            raise ValueError(
                "Contribution summary model rates must be numeric."
            ) from None
        if any(
            not amount.is_finite() or amount < 0 for amount in (per_input, per_output)
        ):
            raise ValueError(
                "Contribution summary model rates must be finite and nonnegative."
            )
        rates[model] = (per_input, per_output)
    return MappingProxyType(rates)


def _validate_port(value: object) -> BaseLLM:
    """Require the actual CAP-001 complete protocol and a model identifier.

    :param value: Candidate provider. Example: ScriptedLLM([...]).
    :return: Validated provider. Example: the same ScriptedLLM instance.
    :raises ValueError: For invalid port objects.
    """
    if (
        not isinstance(value, BaseLLM)
        or not callable(value.complete)
        or not isinstance(value.model_id, str)
        or not _MODEL_ID.fullmatch(value.model_id)
        or _SENSITIVE_TEXT.search(value.model_id)
        or _CREDENTIAL.search(value.model_id)
    ):
        raise ValueError("A completion port with a safe model ID is required.")
    return value
