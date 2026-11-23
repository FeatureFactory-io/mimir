from __future__ import annotations

"""Undecorated, real-ORM self-fetch certification support."""
from dataclasses import dataclass
from typing import Mapping
from django.contrib.auth.models import User
from tests.support.experts_data import CedarDataset


@dataclass(frozen=True)
class SelfFetchCase:
    actor: User
    tool_name: str
    entity_type: str
    entity_id: int
    target_author_id: int
    creator_id: int | None
    expected_total: int
    expected_content: Mapping[str, object]
    exclusion_reason: str


@dataclass(frozen=True)
class KarmaSnapshot:
    ledger_rows: tuple[tuple[object, ...], ...]
    totals_by_user_id: Mapping[int, int]


def resolve_self_fetch_case(
    dataset: CedarDataset, consumer: str, content: str
) -> SelfFetchCase:
    """Resolve one literal outline row using actual Cedar ORM relationships.

    :param dataset: Restored baseline. Example: load_cedar_baseline().
    :param consumer: Literal name. Example: "Maria".
    :param content: Literal content label. Example: "Mike's Activity".
    :return: Immutable real entity/actor case. Example: activity 6203.
    :raises ValueError: Unknown/ambiguous row or missing real fixture relation.
    """
    raise NotImplementedError()


def snapshot_karma_state() -> KarmaSnapshot:
    """Capture complete ledger payloads and projected totals for all users.

    :return: Deterministic snapshot. Example: Mike total 12450.
    :raises AssertionError: Baseline ledger/projection is inconsistent.
    """
    raise NotImplementedError()


def assert_self_fetch_content(
    payload: Mapping[str, object], case: SelfFetchCase
) -> None:
    """Assert successful actual content, not an error or empty placeholder.

    :param payload: Decoded actual tool response. Example: activity dict.
    :param case: Real fixture case. Example: get_activity for 6203.
    :return: None. Example: IDs and stored content match.
    :raises AssertionError: Response identity/content or success differs.
    """
    raise NotImplementedError()


def assert_self_fetch_unchanged(before: KarmaSnapshot, case: SelfFetchCase) -> None:
    """Compare full current ledger and every total with the captured state.

    :param before: Pre-operation snapshot. Example: baseline Cedar ledger.
    :param case: Expected actor/author case. Example: Maria remains 8200.
    :return: None. Example: no learner or author row was inserted.
    :raises AssertionError: Any award, payload, timestamp or total changed.
    """
    raise NotImplementedError()
