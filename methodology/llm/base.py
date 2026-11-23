"""CAP-001 types shared by production adapters and CAP-004 test scripts."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class LLMMessage:
    """One immutable message passed across the provider-neutral boundary."""

    role: str
    content: str


@dataclass(frozen=True)
class LLMResponse:
    """Normalized response; missing usage is unknown, not measured zero usage."""

    content: str
    model: str = ""
    usage: Mapping[str, int] = field(default_factory=dict)
    stop_reason: str = "end_turn"
    thinking: str = ""


class LLMError(RuntimeError):
    """Provider failure or exhausted/invalid deterministic model script."""


@runtime_checkable
class BaseLLM(Protocol):
    """CAP-001 boundary; adapters own SDK imports and response normalization."""

    model_id: str

    def complete(
        self,
        messages: Sequence[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Complete one bounded request.

        :param messages: Ordered nonempty role/content messages.
        :param system: Foundation, identity and optional recipe instructions.
        :param max_tokens: Positive output bound.
        :param temperature: Provider-supported sampling parameter.
        :return: Normalized content/model/usage/stop reason.
        :raises LLMError: When the provider cannot return a valid response.
        """
        ...
