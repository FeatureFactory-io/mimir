"""Real Django-client certification of the Design-to-Maria handoff."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from django.core.mail import EmailMessage
from django.test import Client

from methodology.models import AgentInteraction, ExpertProfile, KarmaAward
from tests.support.expert_profile_handoff import extract_maria_profile_href
from tests.support.experts_data import CedarDataset
from tests.support.experts_html import find_by_test_id

_DESIGN_PATH = "/experts/?category=design"
_CEDAR_SENTENCE_COUNT = 9


@pytest.mark.django_db
def test_maria_profile_handoff_with_design_card_displays_full_paragraph(
    client: Client, cedar_dataset: CedarDataset, mailoutbox: list[EmailMessage]
) -> None:
    """Follow Maria's actual rendered anchor and verify the complete paragraph.

    :param client: Real Django client. Example: authenticated Cedar Elena.
    :param cedar_dataset: Imported profiles and independent Cedar oracle. Example: Maria.
    :param mailoutbox: Real locmem outbox. Example: no mail during the handoff.
    :return: None. Example: Maria detail returns 200 with the full stored prose.
    :raises AssertionError: Navigation, stored prose or read-only behavior differs.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    stored = ExpertProfile.objects.get(user=maria).contribution_summary
    oracle = next(
        row["summary"]
        for row in cedar_dataset.oracle["people"]
        if row["username"] == maria.username
    )
    assert stored == oracle and stored.count(".") == _CEDAR_SENTENCE_COUNT
    award_count = KarmaAward.objects.count()
    interaction_count = AgentInteraction.objects.count()
    elena = cedar_dataset.users_by_username["esvensson"]
    client.force_login(elena)
    headers = {"X-Request-ID": "cedar-s05"}

    listing = client.get(_DESIGN_PATH, headers=headers)
    assert listing.status_code == HTTPStatus.OK
    href = extract_maria_profile_href(listing.content)
    detail = client.get(href, headers=headers)

    assert detail.status_code == HTTPStatus.OK
    assert detail.wsgi_request.path == href
    assert detail.context["person"]["subject_id"] == maria.pk
    for response in (listing, detail):
        assert response.wsgi_request.user == elena
        assert response.headers["X-Request-ID"] == headers["X-Request-ID"]
    paragraph = find_by_test_id(detail.content, "expert-contribution-summary")
    assert paragraph.name == "p" and paragraph.children == [stored]
    assert KarmaAward.objects.count() == award_count
    assert AgentInteraction.objects.count() == interaction_count
    assert not mailoutbox
