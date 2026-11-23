"""CAP-004 ordered model responses for tests only; never a runtime fallback."""

import logging
from collections.abc import Sequence

from methodology.llm.base import LLMError, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class ScriptedLLM:
    """Replay an explicit finite queue while leaving domain collaborators real."""

    model_id = "scripted"

    def __init__(self, responses: Sequence[str | LLMResponse | LLMError]) -> None:
        """Copy the finite response script.

        :param responses: Ordered text, normalized responses or explicit errors.
        :raises ValueError: When the script is empty or contains invalid values.
        :return: None.
        """
        if (
            isinstance(responses, (str, bytes))
            or not responses
            or any(not isinstance(r, (str, LLMResponse, LLMError)) for r in responses)
        ):
            raise ValueError("ScriptedLLM requires a nonempty valid response queue")
        self._responses = tuple(responses)
        self._index = 0

    def complete(
        self,
        messages: Sequence[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Return exactly the next queued response or fail loudly.

        :param messages: Real orchestrator messages, retained only in test memory.
        :param system: System prompt from the real orchestrator.
        :param max_tokens: Positive output limit.
        :param temperature: Sampling value between zero and one.
        :return: Next normalized scripted response.
        :raises LLMError: On explicit scripted failure or exhausted queue.
        :raises ValueError: For invalid request arguments.
        """
        _validate_request(messages, system, max_tokens, temperature)
        if self._index >= len(self._responses):
            raise LLMError(f"ScriptedLLM exhausted after {self._index} calls")
        response = self._responses[self._index]
        self._index += 1
        logger.info("ScriptedLLM.complete | exit | turn=%s", self._index)
        if isinstance(response, LLMError):
            raise response
        if isinstance(response, LLMResponse):
            return response
        return LLMResponse(content=response, model=self.model_id)


def _validate_request(
    messages: Sequence[LLMMessage], system: str, max_tokens: int, temperature: float
) -> None:
    """Reject invalid requests without consuming a model turn.

    :param messages: Nonempty normalized messages.
    :param system: String system prompt.
    :param max_tokens: Positive integer limit.
    :param temperature: Number in the supported zero-to-one interval.
    :raises ValueError: For invalid request data.
    :return: None.
    """
    valid_messages = messages and all(
        isinstance(m, LLMMessage)
        and m.role in {"system", "user", "assistant"}
        and isinstance(m.content, str)
        for m in messages
    )
    if not valid_messages or not isinstance(system, str):
        raise ValueError("Expected nonempty normalized messages and string system")
    if (
        not isinstance(max_tokens, int)
        or isinstance(max_tokens, bool)
        or max_tokens <= 0
    ):
        raise ValueError("max_tokens must be a positive integer")
    if not isinstance(temperature, (float, int)) or not 0 <= temperature <= 1:
        raise ValueError("temperature must be between zero and one")
