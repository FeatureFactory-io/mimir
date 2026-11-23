from __future__ import annotations

"""S23 adapter contracts; implement after PIN GO."""


def test_s23_normalize_response_with_text_and_usage_returns_port_response() -> None:
    """Prove normalized content, usage, model and stop reason.

    :return: None. Example: None after normalization assertions.
    :raises AssertionError: For a lost or invented normalized value.
    """
    raise NotImplementedError()


def test_s23_adapter_with_invalid_request_rejects_before_provider() -> None:
    """Prove invalid request rejection before any SDK operation.

    :return: None. Example: None after boundary assertions.
    :raises AssertionError: If invalid arguments reach the provider.
    """
    raise NotImplementedError()


def test_s23_normalize_response_with_empty_or_truncated_text_preserves_usage() -> None:
    """Retain actual usage/model/stop reason before S27 rejects invalid public prose.

    :return: None. Example: max_tokens response retains known supplied usage.
    :raises AssertionError: Empty/truncated response discards measured usage or invents prose.
    """
    raise NotImplementedError()
