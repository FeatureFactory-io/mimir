"""Capture actual disabled-by-settings loggers without replacing production logging."""
from __future__ import annotations
from collections.abc import Sequence
from contextlib import AbstractContextManager
from pytest import LogCaptureFixture

def capture_experts_logs(caplog: LogCaptureFixture, logger_names: Sequence[str]) -> AbstractContextManager[None]:
    """Temporarily enable real named loggers at INFO and restore all prior state on exit.

    :param caplog: Actual pytest capture fixture. Example: caplog.
    :param logger_names: Exact bounded production logger names. Example: ("methodology.services.experts_service",).
    :return: Context manager over the actual logger configuration. Example: with capture_experts_logs(...).
    :raises ValueError: Invalid or unbounded logger names.
    """
    raise NotImplementedError()
