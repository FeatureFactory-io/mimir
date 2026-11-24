"""Anthropic SDK adapter for the existing provider-neutral completion port."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any

import anthropic
from anthropic.types import Message, MessageParam, Usage

from methodology.llm.base import LLMError, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)

_COMPLETE = "AnthropicAdapter.complete"
_MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}")
_STOP_REASON = re.compile(r"[a-z][a-z0-9_]{0,39}")
_TOKEN_FIELDS = ("input_tokens", "output_tokens")


class AnthropicAdapter:
    """Perform bounded model completions without tools or domain capabilities."""

    model_id: str

    def __init__(self, model_id: str) -> None:
        """Configure the model without constructing a network request.

        :param model_id: Configured model identifier. Example: "configured-model".
        :return: None. Example: None.
        :raises ValueError: For an empty or malformed model identifier.
        """
        if not isinstance(model_id, str) or not _MODEL_ID.fullmatch(model_id):
            raise ValueError("A valid Anthropic model identifier is required.")
        self.model_id = model_id

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
        logger.info("%s | entry | provider=anthropic", _COMPLETE)
        if isinstance(messages, Sequence) and not isinstance(
            messages, (str, bytes, bytearray)
        ):
            messages = tuple(messages)
        try:
            self._validate_request(messages, system, max_tokens, temperature)
        except ValueError:
            logger.info("%s | error | reason_code=invalid_request", _COMPLETE)
            raise
        logger.info(
            "%s | processing | messages=%s max_tokens=%s tools=none",
            _COMPLETE,
            len(messages),
            max_tokens,
        )
        received = self._request(messages, system, max_tokens, temperature)
        try:
            response = self._normalize_response(received)
        except LLMError:
            logger.info("%s | error | reason_code=invalid_response", _COMPLETE)
            raise
        logger.info("%s | exit | outcome=response_received", _COMPLETE)
        return response

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
        if (
            not isinstance(messages, Sequence)
            or isinstance(messages, (str, bytes, bytearray))
            or not messages
            or any(
                not isinstance(message, LLMMessage)
                or message.role not in ("user", "assistant")
                or not isinstance(message.content, str)
                or not message.content.strip()
                for message in messages
            )
        ):
            raise ValueError("Completion requires nonempty user or assistant messages.")
        if not isinstance(system, str):
            raise ValueError(  # noqa: TRY004
                "Completion system instructions must be a string."
            )
        if type(max_tokens) is not int or max_tokens <= 0:
            raise ValueError("Completion max_tokens must be a positive integer.")
        if type(temperature) not in (float, int) or not 0 <= temperature <= 1:
            raise ValueError("Completion temperature must be between zero and one.")

    def _request(
        self,
        messages: Sequence[LLMMessage],
        system: str,
        max_tokens: int,
        temperature: float,
    ) -> Message:
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
        payload: list[MessageParam] = [
            {
                "role": "user" if item.role == "user" else "assistant",
                "content": item.content,
            }
            for item in messages
        ]
        try:
            # A transport retry would consume another attempt outside Galdr's lifecycle.
            with anthropic.Anthropic(max_retries=0) as client:
                return client.messages.create(
                    model=self.model_id,
                    messages=payload,
                    system=system,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
        except Exception:  # noqa: BLE001
            # Omit the original exception, which may contain the provider body.
            logger.info("%s | error | reason_code=provider_failed", _COMPLETE)
        raise LLMError("Anthropic provider completion failed.")

    def _normalize_response(self, message: Message) -> LLMResponse:
        """Normalize every received valid response, retaining empty text and truncation usage.

        :param message: SDK response. Example: message with one text block.
        :return: Port response. Example: LLMResponse("Public facts.", usage={}).
        :raises LLMError: For a malformed response envelope; public-output validation belongs to S27.
        """
        if not isinstance(message, Message):
            raise LLMError("Malformed Anthropic response envelope.")
        model = getattr(message, "model", None)
        stop_reason = getattr(message, "stop_reason", None)
        if model is not None and (
            not isinstance(model, str) or not _MODEL_ID.fullmatch(model)
        ):
            raise LLMError("Malformed Anthropic response model.")
        if stop_reason is not None and (
            not isinstance(stop_reason, str) or not _STOP_REASON.fullmatch(stop_reason)
        ):
            raise LLMError("Malformed Anthropic response stop reason.")
        return LLMResponse(
            content=self._text_content(getattr(message, "content", None)),
            model=self.model_id if model is None else model,
            usage=self._usage_values(getattr(message, "usage", None)),
            stop_reason="unknown" if stop_reason is None else stop_reason,
        )

    @staticmethod
    def _text_content(blocks: Sequence[Any] | None) -> str:
        """Join textual blocks without inventing a fallback response.

        :param blocks: Provider blocks. Example: message.content.
        :return: Joined text. Example: "Published guidance.".
        :raises LLMError: For malformed blocks. An empty text result is preserved for S27 validation.
        """
        if not isinstance(blocks, Sequence) or isinstance(
            blocks, (str, bytes, bytearray)
        ):
            raise LLMError("Malformed Anthropic response content.")
        pieces: list[str] = []
        for block in blocks:
            kind = getattr(block, "type", None)
            if not isinstance(kind, str) or not kind:
                raise LLMError("Malformed Anthropic response block.")
            if kind == "text":
                text = getattr(block, "text", None)
                if not isinstance(text, str):
                    raise LLMError("Malformed Anthropic response text.")
                pieces.append(text)
        return "".join(pieces)

    @staticmethod
    def _usage_values(usage: Usage | None) -> Mapping[str, int]:
        """Normalize supplied input/output token counts only.

        Missing usage stays absent; booleans, negative values and malformed
        supplied counts are rejected rather than converted to measured zero.

        :param usage: Provider usage or None. Example: message.usage.
        :return: Supplied counts. Example: {"input_tokens": 120, "output_tokens": 40}.
        :raises LLMError: For invalid supplied usage.
        """
        if usage is not None and not isinstance(usage, Usage):
            raise LLMError("Malformed Anthropic response usage.")
        counts: dict[str, int] = {}
        for key in _TOKEN_FIELDS:
            value = getattr(usage, key, None)
            if value is None:
                continue
            if type(value) is not int or value < 0:
                raise LLMError("Malformed Anthropic response usage.")
            counts[key] = value
        return MappingProxyType(counts)
