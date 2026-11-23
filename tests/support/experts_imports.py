from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import pytest
from pytest import LogCaptureFixture
from pytest_django.live_server_helper import LiveServer
from tests.support.experts_data import CedarDataset


@dataclass(frozen=True)
class ImportCase:
    """Prepared real source and an existing owned draft import target."""

    workflow_id: int
    source_directory: Path
    added_activity_name: str
    expected_guidance: str


@dataclass(frozen=True)
class ExpertsImportState:
    """Complete ordered ORM snapshots; retain every stored field."""

    ledger: tuple[tuple[object, ...], ...]
    profiles: tuple[tuple[object, ...], ...]
    interactions: tuple[tuple[object, ...], ...]


def _prepare_import_case(cedar: CedarDataset, root: Path) -> ImportCase:
    """Self-export Mike's source and prepare Maria's real owned draft.

    :param cedar: Restored dataset. Example: users_by_username["mchen"].
    :param root: Isolated filesystem root. Example: tmp_path.
    :return: Ready import case. Example: target draft and actual Markdown files.
    :raises AssertionError: Setup awards points or lacks actual exported guidance.
    """
    raise NotImplementedError()


def _snapshot_experts_state() -> ExpertsImportState:
    """Snapshot all ledger, profile and interaction rows in primary-key order.

    :return: Immutable complete state. Example: original historical award rows.
    :raises AssertionError: Expected Cedar schema or baseline is unavailable.
    """
    raise NotImplementedError()


def _assert_import_protocol(result: Mapping[str, object], case: ImportCase) -> None:
    """Verify a positive real import result and generated protocol contents.

    :param result: Actual response. Example: status="changes_detected".
    :param case: Prepared source/target. Example: added_activity_name="Cedar Import".
    :return: None. Example: correct draft, positive diff and protocol verified.
    :raises AssertionError: Wrong target, empty diff or absent protocol content.
    """
    raise NotImplementedError()


def _assert_experts_unchanged(before: ExpertsImportState) -> None:
    """Compare global stored state and actual Maria/Mike ledger totals.

    :param before: Snapshot after non-awarding setup. Example: baseline state.
    :return: None. Example: identical rows and totals 8200/12450.
    :raises AssertionError: Any award, summary metadata or interaction changed.
    """
    raise NotImplementedError()
