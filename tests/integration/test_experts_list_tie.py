"""Real database and Django-client proof of equal-total ordering."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import replace
from http import HTTPStatus
from typing import Any, cast

import pytest
from django.contrib.auth.models import User
from django.db.models import Sum
from django.test import Client
from django.test.html import Element

from methodology.models import KarmaAward, Playbook
from methodology.services.experts_service import ExpertsService
from tests.support.experts_data import CedarDataset
from tests.support.experts_html import _walk_elements, element_text, find_by_test_id
from tests.support.experts_tie_data import apply_cedar_tie03

pytestmark = pytest.mark.django_db

_DESIGN_PATH = "/experts/?category=design"
_CARD_PREFIX = "experts-card-"
_DESIGN_RANKING = [
    ("apark", "15,400"),
    ("sreed", "15,400"),
    ("mrodriguez", "8,200"),
    ("pnair", "7,600"),
    ("dortiz", "6,900"),
]
_REPEATED_REQUESTS = 3


def test_cedar_tie03_with_real_awards_preserves_sofia_and_matches_equal_totals(
    cedar_baseline: CedarDataset,
) -> None:
    """Prove the equal totals reconcile to immutable imported history.

    :param cedar_baseline: Loaded baseline. Example: the S03 CedarDataset.
    :return: None. Example: Sofia and Alina each aggregate to 15400.
    :raises AssertionError: If history, insertion order or baseline changes.
    """
    oracle = deepcopy(cedar_baseline.oracle)
    tie_variants = cast(list[dict[str, Any]], oracle["tie_variants"])
    tie = next(row for row in tie_variants if row["id"] == "TIE03")
    baseline_ledger = _ledger_snapshot()
    variant = apply_cedar_tie03(cedar_baseline)

    alina = variant.users_by_username["apark"]
    assert variant.user_ids == cedar_baseline.user_ids | {"apark": alina.pk}
    assert alina.pk > variant.user_ids["sreed"]
    assert "apark" not in cedar_baseline.users_by_username
    assert variant.oracle is cedar_baseline.oracle
    assert variant.oracle == oracle
    assert variant.playbook_ids == cedar_baseline.playbook_ids
    assert [
        row for row in _ledger_snapshot() if row["recipient_id"] != alina.pk
    ] == baseline_ledger
    for expected in tie["users"]:
        contributor = variant.users_by_username[expected["username"]]
        points = KarmaAward.objects.filter(recipient=contributor).aggregate(
            total=Sum("points")
        )
        projection = ExpertsService().project_user(contributor.pk)
        assert points["total"] == projection.total_points == expected["total_karma"]
        assert projection.primary_category == expected["primary_category"].lower()
        if contributor == alina:
            _assert_alina_history(alina, expected)


@pytest.mark.parametrize(
    "missing_from_database", [False, True], ids=["mapping", "database"]
)
def test_cedar_tie03_with_missing_sofia_rejects_without_partial_writes(
    cedar_baseline: CedarDataset, missing_from_database: bool
) -> None:
    """Prove a missing account in either layer leaves stored history untouched.

    :param cedar_baseline: Loaded baseline. Example: the S03 CedarDataset.
    :param missing_from_database: Delete Sofia's actual row when true. Example: True.
    :return: None. Example: no Alina or awards appear on rejection.
    :raises AssertionError: If validation accepts missing Sofia or leaks writes.
    """
    if missing_from_database:
        User.objects.filter(pk=cedar_baseline.user_ids["sreed"]).delete()
    else:
        users = dict(cedar_baseline.users_by_username)
        users.pop("sreed")
        cedar_baseline = replace(cedar_baseline, users_by_username=users)
    original_ledger = _ledger_snapshot()
    original_users = list(User.objects.order_by("pk").values())

    with pytest.raises(ValueError, match="Sofia"):
        apply_cedar_tie03(cedar_baseline)

    assert list(User.objects.order_by("pk").values()) == original_users
    assert _ledger_snapshot() == original_ledger


@pytest.mark.parametrize(
    "variant_already_applied", [False, True], ids=["reserved-username", "reapply"]
)
def test_cedar_tie03_with_existing_alina_rejects_without_duplicate_awards(
    cedar_baseline: CedarDataset, variant_already_applied: bool
) -> None:
    """Prove both an existing account and a repeated import are rejected.

    :param cedar_baseline: Loaded baseline. Example: the S03 CedarDataset.
    :param variant_already_applied: Import the variant before retry when true. Example: True.
    :return: None. Example: identical full user and award payloads after rejection.
    :raises AssertionError: If existing users are changed or awards are written.
    """
    if variant_already_applied:
        apply_cedar_tie03(cedar_baseline)
    else:
        User.objects.create_user(username="apark")
    original_ledger = _ledger_snapshot()
    original_users = list(User.objects.order_by("pk").values())

    with pytest.raises(ValueError, match="Alina"):
        apply_cedar_tie03(cedar_baseline)

    assert list(User.objects.order_by("pk").values()) == original_users
    assert _ledger_snapshot() == original_ledger


def test_experts_list_with_equal_totals_orders_username_ascending(
    client: Client, cedar_baseline: CedarDataset
) -> None:
    """Prove actual production HTML ranks equal totals by username.

    :param client: Real Django client. Example: Client().
    :param cedar_baseline: Loaded baseline. Example: the S03 CedarDataset.
    :return: None. Example: apark, sreed, mrodriguez, pnair, dortiz.
    :raises AssertionError: If status, category, totals, ranks or DOM order differ.
    """
    variant = apply_cedar_tie03(cedar_baseline)
    client.force_login(variant.users_by_username["esvensson"])
    ranking = _rendered_design_ranking(client)

    assert ranking == _DESIGN_RANKING
    assert variant.user_ids["apark"] > variant.user_ids["sreed"]


def test_experts_list_with_equal_totals_repeated_requests_preserve_order_and_awards(
    client: Client, cedar_baseline: CedarDataset
) -> None:
    """Prove repeated GETs retain ordering and do not award points.

    :param client: Real Django client. Example: Client().
    :param cedar_baseline: Loaded baseline. Example: the S03 CedarDataset.
    :return: None. Example: identical cards and ledger after three GETs.
    :raises AssertionError: If rank changes or GET mutates historical awards.
    """
    variant = apply_cedar_tie03(cedar_baseline)
    client.force_login(variant.users_by_username["esvensson"])
    original_ledger = _ledger_snapshot()

    for _ in range(_REPEATED_REQUESTS):
        assert _rendered_design_ranking(client) == _DESIGN_RANKING
        assert _ledger_snapshot() == original_ledger


def _ledger_snapshot() -> list[dict[str, Any]]:
    """Read every stored award field in stable PK order.

    :return: Complete row payloads. Example: [{"id": 1, ...}].
    """
    return list(KarmaAward.objects.order_by("pk").values())


def _assert_alina_history(contributor: User, expected: dict[str, Any]) -> None:
    """Reconcile Alina's award counts, provenance, identity and unknown refs.

    :param contributor: Imported variant account. Example: Alina Park.
    :param expected: Independent TIE03 person record. Example: the oracle's apark.
    :return: None. Example: 34 historical change awards with null source references.
    :raises AssertionError: If event amounts, identifiers or references differ.
    """
    awards = list(KarmaAward.objects.filter(recipient=contributor))
    assert contributor.get_full_name() == expected["name"]
    assert Counter(
        (award.category, award.source_kind, award.event_channel, award.points)
        for award in awards
    ) == {
        (
            row["category"].lower(),
            row["event"],
            row["event_channel"],
            row["points_each"],
        ): row["count"]
        for row in expected["historical_ledger_fixture"]
    }
    assert len({award.event_identity for award in awards}) == len(awards)
    assert all(
        award.playbook_id_snapshot is None
        and award.change_id_snapshot is None
        and award.entity_type_snapshot is None
        and award.entity_id_snapshot is None
        for award in awards
    )
    assert not Playbook.objects.filter(author=contributor).exists()


def _rendered_design_ranking(client: Client) -> list[tuple[str, str]]:
    """Read visible rank and totals in actual leaderboard DOM order.

    :param client: Signed-in Django client. Example: Elena's Client().
    :return: Ordered username and display total pairs. Example: [("apark", "15,400")].
    :raises AssertionError: If status, current category or displayed ranks differ.
    """
    response = client.get(_DESIGN_PATH)
    assert response.status_code == HTTPStatus.OK
    category = find_by_test_id(response.content, "experts-category-design")
    assert ("aria-current", "page") in category.attributes
    leaderboard = find_by_test_id(response.content, "experts-leaderboard")
    cards: list[tuple[str, Element]] = [
        (test_id.removeprefix(_CARD_PREFIX), node)
        for node in _walk_elements(leaderboard)
        for key, test_id in node.attributes
        if key == "data-testid" and test_id.startswith(_CARD_PREFIX)
    ]
    ranking = []
    for rank, (username, card) in enumerate(cards, start=1):
        rank_label = find_by_test_id(str(card), "expert-card-rank")
        assert ("aria-label", f"Rank {rank}") in rank_label.attributes
        assert element_text(rank_label) == str(rank)
        ranking.append(
            (username, element_text(find_by_test_id(str(card), "expert-card-karma")))
        )
    return ranking
