from __future__ import annotations

"""Anthropic SDK adapter for the existing provider-neutral completion port."""
from collections.abc import Mapping, Sequence
from typing import Any
import anthropic
from methodology.llm.base import LLMMessage, LLMResponse


class AnthropicAdapter:
    """Perform bounded model completions without tools or domain capabilities."""

    model_id: str

    def __init__(self, model_id: str) -> None:
        """Configure the model without constructing a network request.

        :param model_id: Configured model identifier. Example: "configured-model".
        :return: None. Example: None.
        :raises ValueError: For an empty or malformed model identifier.
        """
        raise NotImplementedError()

    def complete(
        self,
        messages: Sequence[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Validate, request once and normalize without fallback prose.

        The adapter supports existing Galdr token limits as well as the
        summary boundary's 1024-token bound. It never offers tools.

        :param messages: Ordered messages. Example: (LLMMessage("user", "facts"),).
        :param system: System policy. Example: "Public contribution summarizer".
        :param max_tokens: Positive output limit. Example: 1024.
        :param temperature: Supported sampling value. Example: 0.2.
        :return: Normalized response. Example: LLMResponse("Published facts.").
        :raises ValueError: For invalid completion arguments.
        :raises LLMError: For provider transport or malformed response envelope.
        """
        raise NotImplementedError()

    @staticmethod
    def _validate_request(
        messages: Sequence[LLMMessage], system: str, max_tokens: int, temperature: float
    ) -> None:
        """Reject invalid requests before credentials or SDK execution.

        :param messages: Nonempty normalized messages. Example: (LLMMessage("user", "x"),).
        :param system: String instructions. Example: "Summarize public evidence".
        :param max_tokens: Positive integer bound. Example: 1024.
        :param temperature: Finite sampling value. Example: 0.2.
        :return: None. Example: None for valid arguments.
        :raises ValueError: For invalid message roles, types or bounds.
        """
        raise NotImplementedError()

    def _request(
        self,
        messages: Sequence[LLMMessage],
        system: str,
        max_tokens: int,
        temperature: float,
    ) -> anthropic.types.Message:
        """Execute exactly one server-authenticated SDK completion.

        Provider exceptions are translated to a sanitized LLMError; raw
        provider exception text must not become logs or persisted metadata.

        :param messages: Valid messages. Example: (LLMMessage("user", "facts"),).
        :param system: Valid system policy. Example: "Public summarizer".
        :param max_tokens: Valid output limit. Example: 1024.
        :param temperature: Sampling value. Example: 0.2.
        :return: SDK response. Example: client.messages.create result.
        :raises LLMError: For credentials, transport or provider failure.
        """
        raise NotImplementedError()

    def _normalize_response(self, message: anthropic.types.Message) -> LLMResponse:
        """Normalize every received valid response, retaining empty text and truncation usage.

        :param message: SDK response. Example: message with one text block.
        :return: Port response. Example: LLMResponse("Public facts.", usage={}).
        :raises LLMError: For a malformed response envelope; public-output validation belongs to S27.
        """
        raise NotImplementedError()

    @staticmethod
    def _text_content(blocks: Sequence[Any]) -> str:
        """Join textual blocks without inventing a fallback response.

        :param blocks: Provider blocks. Example: message.content.
        :return: Joined text. Example: "Published guidance.".
        :raises LLMError: For malformed blocks. An empty text result is preserved for S27 validation.
        """
        raise NotImplementedError()

    @staticmethod
    def _usage_values(usage: Any) -> Mapping[str, int]:
        """Normalize supplied input/output token counts only.

        Missing usage stays absent; booleans, negative values and malformed
        supplied counts are rejected rather than converted to measured zero.

        :param usage: Provider usage or None. Example: message.usage.
        :return: Supplied counts. Example: {"input_tokens": 120, "output_tokens": 40}.
        :raises LLMError: For invalid supplied usage.
        """
        raise NotImplementedError()
