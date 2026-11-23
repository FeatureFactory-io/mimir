from __future__ import annotations

"""S18 production score reconciliation proofs."""
import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


def test_public_score_breakdown_with_cedar_sources_reconciles(client: Client) -> None:
    """Prove the baseline source breakdown through a real production GET.

    :param client: Real Django client. Example: Client().
    :return: None. Example: None after 5000+1600+1200+400=8200.
    :raises AssertionError: If status, exact source rows or total differs.
    """
    raise NotImplementedError()


def test_public_score_breakdown_with_category_subtotals_keeps_separate_sections(
    client: Client,
) -> None:
    """Prove independent source and category dimensions in rendered HTML.

    :param client: Real Django client. Example: Client().
    :return: None. Example: None for Design=7200, Development=1000.
    :raises AssertionError: If categories enter source tbody or sums differ.
    """
    raise NotImplementedError()


def test_public_score_breakdown_with_new_ledger_event_reads_live_totals(
    client: Client,
) -> None:
    """Prove fresh ledger data changes numbers without changing stored prose.

    :param client: Real Django client. Example: Client().
    :return: None. Example: None for PIP=1700 and total=8300.
    :raises AssertionError: If the second GET uses stale or fixture totals.
    """
    raise NotImplementedError()


def test_public_score_breakdown_with_repeated_get_preserves_domain_state(
    client: Client,
) -> None:
    """Prove public detail reads do not award or refresh summaries.

    :param client: Real Django client. Example: Client().
    :return: None. Example: None when ledger/profile snapshots remain equal.
    :raises AssertionError: If authenticated or guest GET changes domain rows.
    """
    raise NotImplementedError()
