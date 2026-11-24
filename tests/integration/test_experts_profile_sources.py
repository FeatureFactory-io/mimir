"""Verify profile score sources against the isolated Cedar award ledger."""

from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus

import pytest
from django.db.models import Sum
from django.test import Client, TestCase
from django.test.html import Element
from django.urls import reverse

from methodology.models import AgentInteraction, EventChannel, ExpertProfile, KarmaAward
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
from tests.support.experts_html import (
    assert_karma_source_rows,
    element_text,
    find_by_test_id,
)

_CEDAR_SOURCES = {"Released": 5000, "PIP": 1600, "Consumption": 1200, "Learning": 400}
_PUBLIC_CEDAR_SOURCES = {
    "Released playbooks": 5000,
    "PIP contributions": 1600,
    "Consumption": 1200,
    "Learning": 400,
}
_CEDAR_TOTAL = 8200
_CEDAR_AWARD_KINDS = {
    "release": 5000,
    "major": 1500,
    "minor": 100,
    "consumption": 1200,
    "learning": 400,
}
_CATEGORY_TOTALS = {"design": 7200, "development": 1000}
_TOTAL_TEST_ID = "profile-karma-total"
_AWARD_POINTS = 5
_HISTORICAL_TIME = datetime(2026, 11, 23, tzinfo=UTC)
_HISTORICAL_LEARNING = {
    "event_identity": "historical:s12:profile-learning",
    "source_kind": KarmaAward.SourceKind.LEARNING,
    "event_channel": EventChannel.HISTORICAL,
    "category": "design",
    "points": _AWARD_POINTS,
    "occurred_at": _HISTORICAL_TIME,
}
_LAST_GOOD_SUMMARY = {
    "summary_updated_at": _HISTORICAL_TIME,
    "summary_status": ExpertProfile.SummaryStatus.SUCCESS,
    "last_summary_correlation_id": "s12-historical-summary",
}
_UPDATED_SOURCES = _CEDAR_SOURCES | {
    "Learning": _CEDAR_SOURCES["Learning"] + _AWARD_POINTS
}
_UPDATED_TOTAL = _CEDAR_TOTAL + _AWARD_POINTS
_POST_AWARD_GET_COUNT = 2


@pytest.mark.django_db
def test_profile_sources_with_cedar_ledger_reconcile(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove baseline ORM source arithmetic matches actual profile HTTP.

    :param client: Real Django test client. Example: authenticated Maria.
    :param cedar_dataset: Imported Cedar ledger and accounts. Example: CedarDataset.
    :return: None. Example: 5000 + 1600 + 1200 + 400 equals rendered 8200.
    :raises AssertionError: If ORM, production HTML or source ordering differs.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    awards = KarmaAward.objects.filter(recipient=maria)
    by_kind = dict(awards.values_list("source_kind").annotate(points_sum=Sum("points")))
    assert by_kind == _CEDAR_AWARD_KINDS
    sources = {
        "Released": by_kind["release"],
        "PIP": by_kind["major"] + by_kind["minor"],
        "Consumption": by_kind["consumption"],
        "Learning": by_kind["learning"],
    }
    assert sources == _CEDAR_SOURCES and sum(sources.values()) == _CEDAR_TOTAL
    assert (
        dict(awards.values_list("category").annotate(points_sum=Sum("points")))
        == _CATEGORY_TOTALS
    )

    assert client.login(username=maria.username, password=CEDAR_PASSWORD)
    response = client.get(reverse("profile"))
    assert response.status_code == HTTPStatus.OK
    assert "accounts/profile.html" in [template.name for template in response.templates]
    assert_karma_source_rows(response.text, sources, _TOTAL_TEST_ID, _CEDAR_TOTAL)
    category = find_by_test_id(response.content, "profile-karma-category-breakdown")
    assert category.name == "dl"
    assert [
        (child.name, element_text(child))
        for child in category.children
        if isinstance(child, Element)
    ] == [("dt", "Design"), ("dd", "7200"), ("dt", "Development"), ("dd", "1000")]


@pytest.mark.django_db
def test_profile_sources_with_public_detail_reconcile_grouped_values(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove the shared assertion works on the actual guest-facing profile.

    :param client: Real Django test client. Example: an anonymous visitor.
    :param cedar_dataset: Imported Cedar ledger and accounts. Example: CedarDataset.
    :return: None. Example: public sources display 5,000/1,600/1,200/400.
    :raises AssertionError: If the public response or reconciliation differs.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    response = client.get(reverse("expert_detail", args=[maria.username]))
    assert response.status_code == HTTPStatus.OK
    assert not response.context["user"].is_authenticated
    assert "experts/detail.html" in [template.name for template in response.templates]
    assert_karma_source_rows(
        response.text, _PUBLIC_CEDAR_SOURCES, "expert-karma-total", _CEDAR_TOTAL
    )


@pytest.mark.django_db
def test_profile_sources_with_new_learning_award_refresh_values(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove numeric presentation reads current ledger without GET awards.

    :param client: Real Django test client. Example: Maria after a test learning award.
    :param cedar_dataset: Imported Cedar ledger and accounts. Example: CedarDataset.
    :return: None. Example: Learning 405 and total 8205 without prose changes.
    :raises AssertionError: If values are cached, summary changes or GET writes awards.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    assert client.login(username=maria.username, password=CEDAR_PASSWORD)
    profiles = ExpertProfile.objects.filter(user=maria).values()
    profiles.update(**_LAST_GOOD_SUMMARY)
    stored_profile = profiles.get()
    interactions = AgentInteraction.objects.order_by("pk").values()
    history = tuple(interactions)
    awards = KarmaAward.objects.order_by("pk").values()
    ledger = tuple(awards)
    with TestCase.captureOnCommitCallbacks() as callbacks:
        response = client.get(reverse("profile"))
        assert response.status_code == HTTPStatus.OK
        assert_karma_source_rows(
            response.text, _CEDAR_SOURCES, _TOTAL_TEST_ID, _CEDAR_TOTAL
        )
        assert tuple(awards.all()) == ledger
        KarmaAward.objects.create(recipient=maria, **_HISTORICAL_LEARNING)
        ledger = tuple(awards.all())
        for _ in range(_POST_AWARD_GET_COUNT):
            response = client.get(reverse("profile"))
            assert response.status_code == HTTPStatus.OK
            assert_karma_source_rows(
                response.text, _UPDATED_SOURCES, _TOTAL_TEST_ID, _UPDATED_TOTAL
            )
            summary = find_by_test_id(response.content, "profile-contribution-summary")
            assert element_text(summary) == stored_profile["contribution_summary"]
            assert tuple(awards.all()) == ledger
    assert profiles.get() == stored_profile
    assert tuple(interactions.all()) == history
    assert not callbacks
