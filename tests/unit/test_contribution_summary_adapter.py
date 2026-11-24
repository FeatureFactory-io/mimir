"""S23 provider transport, composition and body-free interaction contracts."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping
from decimal import Decimal
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import anthropic
import httpx
import pytest
from django.core.exceptions import ValidationError

from methodology.llm.anthropic_adapter import AnthropicAdapter
from methodology.llm.base import LLMError, LLMMessage, LLMResponse
from methodology.models import AgentInteraction
from methodology.services.contribution_summary_factory import (
    _configured_summary_llm,
    configured_summary_rates,
    resolve_processing_llm,
)
from tests.support.scripted_llm import ScriptedLLM

if TYPE_CHECKING:
    from pytest_django.fixtures import SettingsWrapper

_MODEL = "configured-model"
_RESOLVED_MODEL = "resolved-model-20261124"
_MESSAGES = (LLMMessage("user", "Example public material."),)
_SYSTEM = "Use only the example public material."
_SECRET = "provider error detail that must stay out of logs"


@pytest.fixture
def sdk_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[Callable[[httpx.Request], httpx.Response]], None]:
    """Install only a unit HTTP transport under the real Anthropic SDK.

    :param monkeypatch: Restores the SDK constructor after the test.
    :return: Transport installer. Example: install(handler).
    """
    sdk_constructor = anthropic.Anthropic

    def install(handler: Callable[[httpx.Request], httpx.Response]) -> None:
        def create_client(*, max_retries: int) -> anthropic.Anthropic:
            return sdk_constructor(
                api_key="unit-test-api-key",
                max_retries=max_retries,
                http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            )

        monkeypatch.setattr(anthropic, "Anthropic", create_client)

    return install


def _message_body(*, content: list[dict[str, str]], stop_reason: str) -> dict[str, Any]:
    return {
        "id": "unit-test-message",
        "type": "message",
        "role": "assistant",
        "model": _RESOLVED_MODEL,
        "content": content,
        "stop_reason": stop_reason,
        "usage": {"input_tokens": 120, "output_tokens": 40},
    }


def test_s23_normalize_response_with_text_and_usage_returns_port_response(
    sdk_transport: Callable[[Callable[[httpx.Request], httpx.Response]], None],
) -> None:
    """Prove normalized content, usage, model and stop reason.

    :param sdk_transport: HTTP-only seam under the real SDK.
    :return: None after normalization assertions.
    :raises AssertionError: For a lost or invented normalized value.
    """
    bodies: list[dict[str, Any]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(
            200,
            json=_message_body(
                content=[
                    {"type": "text", "text": "Published "},
                    {"type": "redacted_thinking", "data": "discarded"},
                    {"type": "text", "text": "guidance."},
                ],
                stop_reason="end_turn",
            ),
        )

    sdk_transport(respond)
    actual = AnthropicAdapter(_MODEL).complete(_MESSAGES, _SYSTEM, 1024, 0.2)
    assert bodies == [
        {
            "model": _MODEL,
            "messages": [{"role": "user", "content": _MESSAGES[0].content}],
            "system": _SYSTEM,
            "max_tokens": 1024,
            "temperature": 0.2,
        }
    ]
    assert actual == LLMResponse(
        "Published guidance.",
        model=_RESOLVED_MODEL,
        usage={"input_tokens": 120, "output_tokens": 40},
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"messages": None},
        {"messages": ()},
        {"messages": "facts"},
        {"messages": (LLMMessage("system", "invalid role"),)},
        {"messages": (LLMMessage("user", "   "),)},
        {"system": None},
        {"max_tokens": 0},
        {"max_tokens": True},
        {"temperature": -0.1},
        {"temperature": 1.1},
        {"temperature": float("nan")},
        {"temperature": True},
    ],
)
def test_s23_adapter_with_invalid_request_rejects_before_provider(
    monkeypatch: pytest.MonkeyPatch, overrides: dict[str, Any]
) -> None:
    """Prove invalid request rejection before any SDK operation.

    :param monkeypatch: Installs a guard in place of the SDK constructor.
    :param overrides: One malformed request argument.
    :return: None after boundary assertions.
    :raises AssertionError: If invalid arguments reach the provider.
    """

    def unexpected_client(**kwargs: Any) -> None:
        pytest.fail("Invalid arguments reached the SDK constructor")

    monkeypatch.setattr(anthropic, "Anthropic", unexpected_client)
    request: dict[str, Any] = {"messages": _MESSAGES, **overrides}
    with pytest.raises(ValueError):
        AnthropicAdapter(_MODEL).complete(**request)


@pytest.mark.parametrize(
    ("content", "reason"),
    [("", "end_turn"), ("Incomplete published", "max_tokens")],
)
def test_s23_normalize_response_with_empty_or_truncated_text_preserves_usage(
    sdk_transport: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    content: str,
    reason: str,
) -> None:
    """Retain actual usage/model/stop reason before S27 evaluates the prose.

    :param sdk_transport: HTTP-only seam under the real SDK.
    :param content: An empty or incomplete string.
    :param reason: The provider's stop reason.
    :return: None after preservation assertions.
    :raises AssertionError: For invented prose or lost usage.
    """
    sdk_transport(
        lambda request: httpx.Response(
            200,
            json=_message_body(
                content=[{"type": "text", "text": content}] if content else [],
                stop_reason=reason,
            ),
        )
    )
    actual = AnthropicAdapter(_MODEL).complete(_MESSAGES)
    assert actual.content == content
    assert actual.stop_reason == reason
    assert actual.model == _RESOLVED_MODEL
    assert actual.usage == {"input_tokens": 120, "output_tokens": 40}


def test_s23_adapter_with_missing_metadata_preserves_unknown_usage_and_stop() -> None:
    """Normalize a received envelope with sparse metadata without inventing success.

    :return: None after checking the normalized response.
    """
    response = anthropic.types.Message.model_construct(
        content=[],
        usage=anthropic.types.Usage.model_construct(output_tokens=0),
        stop_reason=None,
    )
    actual = AnthropicAdapter(_MODEL)._normalize_response(response)
    assert actual.model == _MODEL
    assert actual.stop_reason == "unknown"
    assert actual.usage == {"output_tokens": 0}


@pytest.mark.parametrize("invalid_usage", [-1, True, "10"])
def test_s23_adapter_with_invalid_supplied_usage_rejects_normalization(
    invalid_usage: Any,
) -> None:
    """Reject supplied token counts that cannot be trusted.

    :param invalid_usage: Malformed count, such as a negative number.
    :return: None after rejecting the invalid provider envelope.
    """
    response = anthropic.types.Message.model_construct(
        content=[],
        usage=anthropic.types.Usage.model_construct(input_tokens=invalid_usage),
    )
    with pytest.raises(LLMError, match="usage"):
        AnthropicAdapter(_MODEL)._normalize_response(response)


def test_s23_adapter_with_provider_error_logs_safe_reason_and_does_not_retry(
    sdk_transport: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Probe a real SDK overload error without leaking bodies or retrying the turn.

    :param sdk_transport: HTTP-only seam under the real SDK.
    :param caplog: Captured application logs.
    :return: None after the sanitized exception and logs are checked.
    """
    calls: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(529, json={"error": {"message": _SECRET}})

    sdk_transport(respond)
    with (
        caplog.at_level(logging.INFO, logger="methodology.llm.anthropic_adapter"),
        pytest.raises(LLMError, match="provider") as caught,
    ):
        AnthropicAdapter(_MODEL).complete(_MESSAGES, _SYSTEM)
    assert len(calls) == 1
    assert caught.value.__context__ is None
    assert "reason_code=provider_failed" in caplog.text
    assert _SECRET not in str(caught.value) + caplog.text
    assert _SYSTEM not in caplog.text
    assert _MESSAGES[0].content not in caplog.text
    assert "unit-test-api-key" not in caplog.text


def test_s23_resolve_processing_llm_with_explicit_and_scoped_ports_preserves_priority(
    settings: SettingsWrapper,
) -> None:
    """Select the serving seam once, before normal dispatch.

    :param settings: Scoped override of the server-only setting.
    :return: None after resolving each source of configuration.
    """
    assert resolve_processing_llm() is None
    scoped = ScriptedLLM(["scoped output"])
    explicit = ScriptedLLM(["explicit output"])
    settings.CONTRIBUTION_SUMMARY_LLM = scoped
    assert resolve_processing_llm() is scoped
    assert resolve_processing_llm(explicit) is explicit
    settings.CONTRIBUTION_SUMMARY_LLM = SimpleNamespace(
        model_id="scripted", complete="noncallable"
    )
    with pytest.raises(ValueError, match="completion port"):
        resolve_processing_llm()
    assert scoped.calls == explicit.calls == ()


def test_s23_configured_provider_with_galdr_model_builds_without_transport(
    settings: SettingsWrapper, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Use the existing server model configuration without connecting.

    :param settings: Scoped server settings object.
    :param monkeypatch: Guard against initializing the provider client.
    :return: None after verifying lazy adapter construction.
    """
    settings.GALDR_MODEL = _MODEL

    def unexpected_client(**kwargs: Any) -> None:
        pytest.fail("Composing the provider must not construct an SDK client")

    monkeypatch.setattr(anthropic, "Anthropic", unexpected_client)
    port = _configured_summary_llm()
    assert isinstance(port, AnthropicAdapter)
    assert port.model_id == _MODEL


def test_s23_resolve_processing_llm_with_unpersistable_model_rejects_port() -> None:
    """Reject an explicit port whose model identifier would fail storage."""
    explicit = ScriptedLLM(["unused"])
    explicit.model_id = "model" + ("1" * 48)
    with pytest.raises(ValueError, match="safe model ID") as caught:
        resolve_processing_llm(explicit)
    assert explicit.model_id not in str(caught.value)
    assert not explicit.calls


@pytest.mark.parametrize(
    "rates",
    ['{"resolved-model-20261124": ["0", "1.25"]}', {_RESOLVED_MODEL: ("0", "1.25")}],
)
def test_s23_configured_summary_rates_with_model_pair_returns_decimal_rates(
    settings: SettingsWrapper, rates: str | Mapping[str, Any]
) -> None:
    """Read explicit USD pairs and preserve missing rates as unknown.

    :param settings: Scoped server settings object.
    :param rates: Sample JSON or Python model-rate map.
    :return: None after checking decimal rates.
    """
    settings.CONTRIBUTION_SUMMARY_MODEL_RATES = ""
    assert configured_summary_rates() == {}
    settings.CONTRIBUTION_SUMMARY_MODEL_RATES = rates
    assert configured_summary_rates() == {
        _RESOLVED_MODEL: (Decimal(0), Decimal("1.25"))
    }


@pytest.mark.parametrize(
    "rates",
    [
        "[1, 2]",
        "{invalid json}",
        {_MODEL: ("3",)},
        {_MODEL: ("-3", "4")},
        {_MODEL: ("NaN", "4")},
    ],
)
def test_s23_configured_summary_rates_with_invalid_pair_raises(
    settings: SettingsWrapper, rates: str | Mapping[str, Any]
) -> None:
    """Fail configuration validation on incomplete or unbillable rates.

    :param settings: Scoped server settings object.
    :param rates: Malformed raw rate configuration.
    :return: None after rejecting the rates.
    """
    settings.CONTRIBUTION_SUMMARY_MODEL_RATES = rates
    with pytest.raises(ValueError, match="rates"):
        configured_summary_rates()


def _interaction(**overrides: Any) -> AgentInteraction:
    return AgentInteraction(
        **{
            "model": _MODEL,
            "subject_id": 42,
            "pip_id": 73,
            "correlation_id": "s23-attempt-1",
            "latency_ms": Decimal(0),
            "outcome": AgentInteraction.Outcome.FAILURE,
            "error_code": "provider_failed",
            "events": [
                {
                    "beat": "entry",
                    "details": "subject_id=42 correlation_id=s23-attempt-1",
                },
                {
                    "beat": "llm_call",
                    "details": f"model={_MODEL} tools=none max_tokens=1024",
                },
                {"beat": "failure", "details": "reason_code=provider_failed"},
                {"beat": "exit", "details": "outcome=failure"},
            ],
            **overrides,
        }
    )


def test_s23_interaction_with_unknown_usage_accepts_body_free_trace() -> None:
    """Validate metadata for a failure with unavailable billing usage.

    :return: None after validating the canonical metadata shape.
    """
    _interaction().clean()


@pytest.mark.parametrize(
    "overrides",
    [
        {"workflow_id": "private-workflow"},
        {"correlation_id": "private@example.invalid"},
        {"input_tokens": True},
        {"output_tokens": -1},
        {"latency_ms": Decimal("NaN")},
        {"estimated_cost_usd": Decimal(0)},
        {"events": [{"beat": "exit", "details": "outcome=failure", "body": _SECRET}]},
        {"events": [{"beat": "exit", "details": "outcome=failure Leakage follows."}]},
        {
            "events": [
                {"beat": "failure", "details": "reason_code=arbitrary-private-body"}
            ]
        },
    ],
)
def test_s23_interaction_with_invalid_metadata_rejects_without_leaking_details(
    overrides: dict[str, Any],
) -> None:
    """Reject unsafe metadata even when the JSON would otherwise be valid.

    :param overrides: Invalid interaction field values.
    :return: None after rejection without a sensitive echo.
    """
    with pytest.raises(ValidationError) as caught:
        _interaction(**overrides).clean()
    assert _SECRET not in str(caught.value)
