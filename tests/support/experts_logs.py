"""Capture actual disabled-by-settings loggers without replacing production logging."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator, Sequence
from contextlib import ExitStack, contextmanager

from pytest import LogCaptureFixture

_LOGGER_NAME = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+")


@contextmanager
def capture_experts_logs(
    caplog: LogCaptureFixture, logger_names: Sequence[str]
) -> Iterator[None]:
    """Temporarily enable real named loggers and restore their configuration.

    :param caplog: Actual pytest capture fixture. Example: caplog.
    :param logger_names: Exact dotted names. Example: ("methodology.expert_views",).
    :return: Context over the actual loggers at INFO. Example: used in a with block.
    :raises ValueError: For absent or invalid logger names.
    """
    if not logger_names or any(
        not isinstance(name, str) or not _LOGGER_NAME.fullmatch(name)
        for name in logger_names
    ):
        raise ValueError("Provide exact, dotted logger names.")
    with ExitStack() as stack:
        for name in dict.fromkeys(logger_names):
            logger = logging.getLogger(name)
            stack.callback(setattr, logger, "disabled", logger.disabled)
            stack.callback(setattr, logger, "propagate", logger.propagate)
            stack.enter_context(caplog.at_level(logging.INFO, logger=name))
            logger.disabled = False
            logger.propagate = True
        yield
