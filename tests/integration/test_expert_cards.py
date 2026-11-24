"""Real HTTP contracts for readable public cards."""

from __future__ import annotations

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.html import escape

from methodology.models import ExpertProfile
from tests.support.experts_data import CedarDataset
from tests.support.experts_html import element_text, find_by_test_id

_DESIGN_PATH = "/experts/?category=design"
_MARIA_CARD = "experts-card-mrodriguez"
_PROFILE_TABLE = f'FROM "{ExpertProfile._meta.db_table}"'


@pytest.mark.django_db
def test_experts_card_with_cedar_baseline_shows_readable_signals(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove Maria's scoped card identity, total, hint and action destinations.

    :param client: Real Django client. Example: Elena requests Design.
    :param cedar_dataset: Imported contributor profiles and public Karma events.
    :return: None. Example: rank 2, 8,200, Design and both actions verified.
    :raises AssertionError: If rendered public signals or destinations differ.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    stored = ExpertProfile.objects.get(user=maria).contribution_summary
    client.force_login(cedar_dataset.users_by_username["esvensson"])
    with CaptureQueriesContext(connection) as queries:
        response = client.get(_DESIGN_PATH)

    assert response.status_code == 200
    card = find_by_test_id(response.content, _MARIA_CARD)
    assert card.name == "article"
    html = str(card)
    assert stored in element_text(card)
    assert element_text(find_by_test_id(html, "expert-card-rank")) == "2"
    assert element_text(find_by_test_id(html, "expert-card-name")) == "Maria Rodriguez"
    assert element_text(find_by_test_id(html, "expert-card-karma")) == "8,200"
    assert element_text(find_by_test_id(html, "expert-card-category")) == "Design"
    assert (
        element_text(find_by_test_id(html, "experts-card-initials-mrodriguez")) == "MR"
    )
    hint = find_by_test_id(html, "experts-card-hint-mrodriguez")
    assert hint.name == "p" and hint.children == [stored]
    assert "accessibility" in element_text(hint).lower()
    profile = find_by_test_id(html, "experts-view-profile-mrodriguez")
    assert element_text(profile) == "View profile"
    assert dict(profile.attributes)["href"] == reverse(
        "expert_detail", args=[maria.username]
    )
    contact = find_by_test_id(html, "experts-reach-out-mrodriguez")
    assert element_text(contact) == "Reach out"
    assert dict(contact.attributes)["href"] == "mailto:maria.rodriguez@example.com"
    assert sum(_PROFILE_TABLE in query["sql"] for query in queries) == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "markup", ["", '<script>alert("Cedar")</script> & '], ids=["stored", "escaped"]
)
def test_experts_card_with_stored_caveat_adds_no_suitability_claim(
    client: Client, cedar_dataset: CedarDataset, markup: str
) -> None:
    """Preserve approved prose while rejecting added inferred claims.

    :param client: Real Django client. Example: Design list request.
    :param cedar_dataset: Imported contributor profiles including Maria's public prose.
    :param markup: Optional stored markup that must render as text.
    :return: None. Example: stored caveat retained with no recommendation badge.
    :raises AssertionError: If extra suitability/availability claims appear.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    profile = ExpertProfile.objects.get(user=maria)
    stored = markup + profile.contribution_summary
    if markup:
        ExpertProfile.objects.filter(pk=profile.pk).update(contribution_summary=stored)
    client.force_login(cedar_dataset.users_by_username["esvensson"])
    response = client.get(_DESIGN_PATH)

    assert response.status_code == 200
    card = find_by_test_id(response.content, _MARIA_CARD)
    hint = find_by_test_id(str(card), "experts-card-hint-mrodriguez")
    assert hint.children == [stored]
    assert stored.endswith("availability and project fit still require a conversation.")
    assert element_text(card) == (
        f"2 MR Maria Rodriguez Design {stored} 8,200 Karma View profile Reach out"
    )
    if markup:
        assert escape(stored).encode() in response.content
        assert markup.encode() not in response.content


@pytest.mark.django_db
def test_experts_card_with_missing_profile_shows_live_counts(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Read public counts for a guest without fetching account email addresses.

    :param client: Real anonymous Django client. Example: Bob browsing Development.
    :param cedar_dataset: Imported Mike and his real public books and award rows.
    :return: None after verifying the numeric fallback and guest query boundary.
    :raises AssertionError: If the fallback, batched reads or guest boundary differ.
    """
    mike = cedar_dataset.users_by_username["mchen"]
    ExpertProfile.objects.get(user=mike).delete()
    with CaptureQueriesContext(connection) as queries:
        response = client.get(reverse("experts_list"))

    assert response.status_code == 200
    card = find_by_test_id(response.content, "experts-card-mchen")
    hint = find_by_test_id(str(card), "experts-card-hint-mchen")
    assert element_text(hint) == "2 released playbooks · 47 copies"
    assert sum(_PROFILE_TABLE in query["sql"] for query in queries) == 1
    assert all(
        f'"{mike._meta.db_table}"."email"' not in query["sql"] for query in queries
    )
    assert (
        b"mailto:" not in response.content
        and mike.email.encode() not in response.content
    )
