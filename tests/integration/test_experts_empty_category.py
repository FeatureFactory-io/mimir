from __future__ import annotations

from http import HTTPStatus

import pytest
from django.test import Client

from tests.support.experts_data import CedarDataset
from tests.support.experts_html import (
    _walk_elements,
    assert_no_expert_cards,
    assert_other_empty_message,
    find_by_test_id,
)

_DESIGN_CARD_COUNT = 5


@pytest.mark.django_db
@pytest.mark.parametrize("authenticated", [True, False], ids=["elena", "guest"])
def test_experts_other_with_baseline_renders_exact_empty_state(
    client: Client, cedar_dataset: CedarDataset, authenticated: bool
) -> None:
    """Prove empty Other using real records and rendered production HTML.

    :param client: Isolated real client. Example: pytest client fixture.
    :param cedar_dataset: Real imported Cedar baseline. Example: the Elena user.
    :param authenticated: Whether to force-login Elena. Example: True.
    :return: None. Example: guest and signed-in requests both render empty Other.
    :raises AssertionError: If the production response violates the contract.
    """
    if authenticated:
        client.force_login(cedar_dataset.users_by_username["esvensson"])

    response = client.get("/experts/?category=other")

    assert_no_expert_cards(response)
    assert response.wsgi_request.user.is_authenticated is authenticated
    assert response.context["selected_category"] == "other"
    assert_other_empty_message(response)


@pytest.mark.django_db
@pytest.mark.usefixtures("cedar_dataset")
def test_experts_design_with_baseline_omits_empty_state(client: Client) -> None:
    """Prove populated categories do not render the empty branch.

    :param client: Isolated real client. Example: pytest client fixture.
    :return: None. Example: Design renders five cards and no empty state.
    :raises AssertionError: If populated Design is rendered as empty.
    """
    response = client.get("/experts/?category=design")

    assert response.status_code == HTTPStatus.OK
    assert response.context["selected_category"] == "design"
    category = find_by_test_id(response.content, "experts-category-design")
    assert ("aria-current", "page") in category.attributes

    leaderboard = find_by_test_id(response.content, "experts-leaderboard")
    test_ids = [
        dict(node.attributes).get("data-testid", "")
        for node in _walk_elements(leaderboard)
    ]
    assert "experts-empty" not in test_ids
    assert (
        sum(test_id.startswith("experts-card-") for test_id in test_ids)
        == _DESIGN_CARD_COUNT
    )
