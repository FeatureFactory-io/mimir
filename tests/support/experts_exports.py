from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class ExportKarmaState:
    """Immutable real-ledger/projection snapshot for successful-export proofs."""

    ledger_rows: tuple[tuple[object, ...], ...]
    user_totals: tuple[tuple[int, int], ...]
    category_source_totals: tuple[tuple[object, ...], ...]
    mike_gui_copy_count: int


def capture_export_karma_state() -> ExportKarmaState:
    """Capture every award field and all live numeric projections.

    :return: Immutable snapshot. Example: Mike=12450 and GUI copies=47.
    :raises AssertionError: Cedar baseline or required projection is absent.
    """
    raise NotImplementedError()


def assert_complete_self_export(
    *,
    result: Mapping[str, object],
    bundle: Mapping[str, object],
    workspace: Path,
    started_at: datetime,
    finished_at: datetime,
) -> None:
    """Verify complete confined files, bytes, formats and source content.

    :param result: Real successful export result. Example: status='exported'.
    :param bundle: Real authorized content bundle. Example: workflow_id=6202.
    :param workspace: Real isolated root. Example: tmp_path / 'workspace'.
    :param started_at: Invocation start. Example: UTC 2026-11-23T12:00:00.
    :param finished_at: Invocation completion. Example: UTC 2026-11-23T12:00:02.
    :return: None. Example: every expected file and inline output verified.
    :raises AssertionError: Missing/extra file, invalid timestamp, bytes or format.
    """
    raise NotImplementedError()


def assert_self_export_karma_unchanged(before: ExportKarmaState) -> None:
    """Compare complete persisted state after a verified successful self-export.

    :param before: Pre-invocation state. Example: Mike=12450, GUI copies=47.
    :return: None. Example: global ledger and projections remain identical.
    :raises AssertionError: Any row, recipient, total, timestamp or count changed.
    """
    raise NotImplementedError()
