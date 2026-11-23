from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from django.test import Client
from tests.support.experts_data import CedarDataset


@dataclass(frozen=True)
class SummaryState:
    """Immutable persisted prose/refresh/interaction evidence."""

    profile_values: Mapping[str, Any]
    interaction_values: tuple[Mapping[str, Any], ...]


def capture_summary_state(subject_id: int) -> SummaryState:
    """Read complete summary metadata and actual interaction rows.
    :param subject_id: Positive profile owner ID. Example: Maria's user PK.
    :return: Immutable state. Example: nine sentences and successful metadata.
    :raises ValueError: For invalid/missing subject.
    """
    raise NotImplementedError()


def post_authorized_copy(client: Client, cedar: CedarDataset) -> str:
    """GET activity 6203 and POST S36's real CSRF-valid receipt.
    :param client: Real authenticated strict client. Example: Maria's session.
    :param cedar: Real ORM baseline. Example: CEDAR-RFP-01.
    :return: Applied action UUID string. Example: a new UUID4 string.
    :raises AssertionError: For missing prompt/CSRF or unsuccessful receipt.
    """
    raise NotImplementedError()


def assert_live_displays(client: Client, cedar: CedarDataset) -> None:
    """Assert post-copy actual HTML totals, sources, category and stored text.
    :param client: Real Maria client. Example: authenticated Django client.
    :param cedar: Real baseline with oracle paragraph. Example: CEDAR-RFP-01.
    :return: None. Example: all rendered values reconcile to 8205/12455.
    :raises AssertionError: For stale score, changed prose or side effects.
    """
    raise NotImplementedError()
