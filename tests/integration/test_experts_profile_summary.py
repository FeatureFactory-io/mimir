"""Real Django-client contracts for the existing own-profile summary."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from methodology.llm.base import LLMError
from methodology.models import AgentInteraction, ExpertProfile, KarmaAward
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
from tests.support.experts_html import element_text, find_by_test_id
from tests.support.scripted_llm import ScriptedLLM

pytestmark = pytest.mark.django_db
_MARIA_SUMMARY_SENTENCES = 9


def test_profile_summary_contract_with_seeded_maria_returns_complete_stored_paragraph(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove complete stored text reaches the authenticated production response.

    :param client: Real Django client. Example: Client().
    :param cedar_dataset: Isolated ORM baseline. Example: Maria under "mrodriguez".
    :return: None. Example: all nine sentences match the stored paragraph.
    :raises AssertionError: If ownership, DOM text, stored state or model use differs.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    jordan = cedar_dataset.users_by_username["jlee"]
    profiles = ExpertProfile.objects.values()
    profile = profiles.get(user=maria)
    paragraph = profile["contribution_summary"]
    oracle_people = cedar_dataset.oracle["people"]
    assert isinstance(oracle_people, list)
    summaries = {person["username"]: person["summary"] for person in oracle_people}
    assert paragraph == summaries[maria.username]
    assert len(paragraph.split(". ")) == _MARIA_SUMMARY_SENTENCES
    ledger = tuple(KarmaAward.objects.order_by("pk").values())
    interactions = AgentInteraction.objects.count()
    llm = ScriptedLLM([LLMError("A profile GET must not call the summary provider")])
    assert client.login(username=maria.username, password=CEDAR_PASSWORD)

    other_subject = {"username": jordan.username, "user_id": jordan.pk}
    with (
        override_settings(CONTRIBUTION_SUMMARY_LLM=llm),
        TestCase.captureOnCommitCallbacks() as callbacks,
    ):
        response = client.get(reverse("profile"), other_subject)

    assert response.status_code == HTTPStatus.OK
    assert response.context["username"] == maria.username
    summary = find_by_test_id(response.content, "profile-contribution-summary")
    assert element_text(summary) == paragraph
    assert profiles.get(user=maria) == profile
    assert tuple(KarmaAward.objects.order_by("pk").values()) == ledger
    assert AgentInteraction.objects.count() == interactions
    assert not callbacks and not llm.calls


def test_profile_summary_markup_with_long_paragraph_links_button_to_region(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove initial semantics without claiming browser execution.

    :param client: Real Django client. Example: Client().
    :param cedar_dataset: Isolated ORM baseline. Example: Maria's long summary.
    :return: None. Example: one native toggle controls the unique summary region.
    :raises AssertionError: If ARIA, native type, uniqueness or account hooks differ.
    :raises NotImplementedError: Until the approved proof is implemented.
    """
    raise NotImplementedError()
