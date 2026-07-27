"""Shared caplog assertions for Log Story Script rows."""

from __future__ import annotations

import logging
from typing import Mapping, Sequence


def assert_log_story(
    caplog,
    *,
    where: str,
    beats: Mapping[str, Sequence[str]],
    level: str = "INFO",
) -> None:
    """Assert each beat has a matching log record for ``where``.

    :param caplog: pytest ``caplog`` fixture
    :param where: stable substring that must appear in the log message
    :param beats: beat name → required substrings (all in one record)
    :param level: minimum level name (INFO default)
    :raises AssertionError: naming the missing beat / substring
    """
    min_level = getattr(logging, level.upper(), logging.INFO)
    records = [
        r
        for r in caplog.records
        if r.levelno >= min_level and where in r.getMessage()
    ]
    messages = [r.getMessage() for r in records]
    for beat, needles in beats.items():
        matched = [msg for msg in messages if all(n in msg for n in needles)]
        if not matched:
            raise AssertionError(
                f"Log story beat {beat!r} missing for where={where!r}; "
                f"need {list(needles)!r} in one record; got: {messages!r}"
            )
