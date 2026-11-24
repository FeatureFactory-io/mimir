"""Anthropic Claude client for Galdr PIP assessments."""

from __future__ import annotations

import json
import logging
import re

from django.conf import settings

from methodology.llm.base import BaseLLM, LLMError, LLMMessage, LLMResponse
from methodology.services.contribution_summary_factory import _configured_summary_llm
from methodology.services.galdr_prompts import HOLISTIC_SYSTEM_PROMPT, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_SINGLE_CHANGE_MAX_TOKENS = 4096
_HOLISTIC_MAX_TOKENS = 16384  # Allow complete diagnostics for large (e.g. 58-row) PIPs.
_ASSESSMENT_TEMPERATURE = 1.0  # Preserve the earlier SDK default.


class GaldrLLMError(Exception):
    """API failure or malformed model output."""


class GaldrClient:
    """
    Thin wrapper around Anthropic Claude for per-change verdicts.

    Example:
        rec, why = GaldrClient().evaluate_change("...")
    """

    def evaluate_change(self, user_prompt: str) -> tuple[str, str]:
        """
        Ask the model for a JSON verdict.

        :param user_prompt: User message describing playbook + one change.
        :return: ``(recommendation, reasoning)`` where recommendation is ACCEPT|REJECT|NEEDS_CLARIFICATION.
        :raises GaldrLLMError: on transport or parsing errors.
        """
        raw = self._call_llm_raw(user_prompt, system=SYSTEM_PROMPT)
        return self._parse_response(raw)

    def evaluate_pip_holistically(
        self,
        user_prompt: str,
    ) -> tuple[dict[str, str], list[tuple[int, str, str]]]:
        """
        Ask the model for a holistic PIP verdict with per-change diagnostics.

        :param user_prompt: User message with current + target state and all changes.
        :return: ``(holistic_assessment, change_payloads)`` where payloads are
            ``(change_pk, recommendation, reasoning)`` tuples.
        :raises GaldrLLMError: on transport or parsing errors.
        """
        raw = self._call_llm_raw(user_prompt, system=HOLISTIC_SYSTEM_PROMPT)
        return self._parse_holistic_response(raw)

    _llm: BaseLLM | None = None

    def _call_llm_raw(self, user_prompt: str, *, system: str = SYSTEM_PROMPT) -> str:
        """Ask the selected port for the private assessment response.

        :param user_prompt: Existing Galdr prompt. Example: a change review.
        :param system: Existing evaluation policy. Example: SYSTEM_PROMPT.
        :return: Assessment JSON text.
        :raises GaldrLLMError: For failed or truncated assessment.
        """
        llm = self._llm
        if llm is None:
            try:
                llm = _configured_summary_llm()
            except ValueError:
                raise GaldrLLMError(
                    "Galdr provider configuration is invalid."
                ) from None
        max_tokens = (
            _HOLISTIC_MAX_TOKENS
            if system == HOLISTIC_SYSTEM_PROMPT
            else _SINGLE_CHANGE_MAX_TOKENS
        )
        return self._complete_via_port(llm, user_prompt, system, max_tokens)

    @classmethod
    def _from_port(cls, llm: BaseLLM) -> GaldrClient:
        """Attach a provider port to the existing assessment parser client.

        Do not add a raising constructor that changes current instantiation.

        :param llm: Valid provider port. Example: ScriptedLLM([...]).
        :return: Existing parser client using that port. Example: GaldrClient().
        :raises ValueError: For an invalid provider port.
        """
        if not isinstance(llm, BaseLLM) or not callable(llm.complete):
            raise ValueError("Galdr requires a completion port.")
        client = cls()
        client._llm = llm
        return client

    def _complete_via_port(
        self, llm: BaseLLM, user_prompt: str, system: str, max_tokens: int
    ) -> str:
        """Request private assessment text for the existing unchanged parsers.

        Preserve existing assessment token limits and convert LLMError to the
        existing GaldrLLMError contract. No public-evidence filtering belongs here:
        authorized private assessment and public summary are distinct requests.

        :param llm: Selected provider port. Example: ScriptedLLM([...]).
        :param user_prompt: Existing assessment prompt. Example: "Change [7]...".
        :param system: Existing assessment system policy. Example: HOLISTIC_SYSTEM_PROMPT.
        :param max_tokens: Existing bound. Example: 16384.
        :return: Raw text for existing parsing. Example: valid holistic verdict JSON.
        :raises GaldrLLMError: For provider, empty or truncated assessment output.
        """
        try:
            response = llm.complete(
                (LLMMessage("user", user_prompt),),
                system=system,
                max_tokens=max_tokens,
                temperature=_ASSESSMENT_TEMPERATURE,
            )
        except (LLMError, ValueError):
            raise GaldrLLMError("Galdr assessment provider failed.") from None
        if not isinstance(response, LLMResponse):
            raise GaldrLLMError("Galdr assessment returned invalid metadata.")
        if response.stop_reason == "max_tokens":
            raise GaldrLLMError(
                "Galdr assessment was truncated at the output token limit."
            )
        if not isinstance(response.content, str) or not response.content.strip():
            raise GaldrLLMError("Galdr assessment returned no text.")
        return response.content

    @staticmethod
    def _strip_code_fences(raw: str) -> str:
        s = raw.strip()
        fence = re.match(r"^```(?:json)?\s*(.*?)```", s, re.DOTALL | re.IGNORECASE)
        return fence.group(1).strip() if fence else s

    def _parse_response(self, raw: str) -> tuple[str, str]:
        blob = self._strip_code_fences(raw)
        try:
            payload = json.loads(blob)
        except json.JSONDecodeError as exc:
            logger.warning("Galdr parse JSON failure reason=invalid_json")
            raise GaldrLLMError("Invalid JSON from model") from exc
        rec = str(payload.get("recommendation", "")).strip().upper()
        why = str(payload.get("reasoning", "")).strip()
        ok = {"ACCEPT", "REJECT", "NEEDS_CLARIFICATION"}
        if rec not in ok or not why:
            raise GaldrLLMError("Missing recommendation or reasoning in JSON payload")
        return rec, why

    def _parse_holistic_response(
        self,
        raw: str,
    ) -> tuple[dict[str, str], list[tuple[int, str, str]]]:
        blob = self._strip_code_fences(raw)
        try:
            payload = json.loads(blob)
        except json.JSONDecodeError as exc:
            logger.warning("Galdr holistic parse JSON failure reason=invalid_json")
            raise GaldrLLMError("Invalid JSON from model") from exc

        holistic_raw = payload.get("holistic_assessment") or {}
        coherence = str(holistic_raw.get("overall_coherence", "")).strip().upper()
        holistic_reason = str(holistic_raw.get("reasoning", "")).strip()
        if coherence not in {"COHERENT", "INCOHERENT"} or not holistic_reason:
            raise GaldrLLMError("Missing holistic_assessment in JSON payload")

        ok = {"ACCEPT", "REJECT", "NEEDS_CLARIFICATION"}
        payloads: list[tuple[int, str, str]] = []
        for item in payload.get("change_assessments") or []:
            cid = item.get("change_id")
            rec = str(item.get("recommendation", "")).strip().upper()
            why = str(item.get("reasoning", "")).strip()
            if cid is None or rec not in ok or not why:
                raise GaldrLLMError("Invalid change_assessments entry in JSON payload")
            payloads.append((int(cid), rec, why))

        if not payloads:
            raise GaldrLLMError("change_assessments must not be empty")

        holistic = {
            "overall_coherence": coherence,
            "reasoning": holistic_reason,
        }
        return holistic, payloads


class StubGaldrClient(GaldrClient):
    """Deterministic client for CI / tests."""

    STUB_SENTENCE = "Galdr stub — automated ACCEPT for integration tests."

    def _call_llm_raw(self, user_prompt: str, *, system: str = SYSTEM_PROMPT) -> str:
        logger.info("StubGaldrClient returning canned ACCEPT")
        return json.dumps(
            {"recommendation": "ACCEPT", "reasoning": self.STUB_SENTENCE},
        )

    def evaluate_pip_holistically(
        self,
        user_prompt: str,
    ) -> tuple[dict[str, str], list[tuple[int, str, str]]]:
        change_ids = [
            int(m)
            for m in re.findall(r"^Change \[(\d+)\] order=", user_prompt, re.MULTILINE)
        ]
        logger.info(
            "StubGaldrClient holistic ACCEPT for change_ids=%s",
            change_ids,
        )
        holistic = {
            "overall_coherence": "COHERENT",
            "reasoning": self.STUB_SENTENCE,
        }
        payloads = [(cid, "ACCEPT", self.STUB_SENTENCE) for cid in change_ids]
        if not payloads:
            raise GaldrLLMError("Stub could not find change IDs in prompt")
        return holistic, payloads


def get_galdr_client() -> GaldrClient:
    """
    Prefer Anthropic when enabled; otherwise deterministic stub.

    :return: Concrete client instance.
    """
    if getattr(settings, "GALDR_USE_ANTHROPIC", False):
        logger.info("Galdr using Anthropic client")
        return GaldrClient()
    logger.info("Galdr using stub client (no live LLM)")
    return StubGaldrClient()


def _select_galdr_port(injected: BaseLLM | None) -> tuple[BaseLLM | None, bool]:
    """Capture the selected provider and any default configuration failure.

    A disabled default preserves the existing StubGaldrClient path. A failed
    default is captured separately so the committed submission can retry even
    if the setting changes before dispatch.

    :param injected: Optional explicit provider. Example: ScriptedLLM([...]).
    :return: Port and invalid-config flag. Example: (None, True) for a bad model.
    :raises ValueError: For an invalid injected port.
    """
    if injected is not None:
        if not isinstance(injected, BaseLLM) or not callable(injected.complete):
            raise ValueError("Galdr requires a completion port.")
        return injected, False
    if not settings.GALDR_USE_ANTHROPIC:
        return None, False
    try:
        return _configured_summary_llm(), False
    except ValueError:
        return None, True
