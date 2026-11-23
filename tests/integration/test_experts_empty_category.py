from __future__ import annotations

import pytest
from django.test import Client
from tests.support.experts_data import load_cedar_baseline
from tests.support.experts_html import (
    assert_no_expert_cards,
    assert_other_empty_message,
    element_text,
    find_by_test_id,
    _walk_elements,
)


@pytest.mark.django_db
@pytest.mark.parametrize("authenticated", [True, False], ids=["elena", "guest"])
def test_experts_other_with_baseline_renders_exact_empty_state(
    client: Client, authenticated: bool
) -> None:
    """Prove empty Other using real records and rendered production HTML.

    :param client: Isolated real client. Example: pytest client fixture.
    :param authenticated: Whether to force-login Elena. Example: True.
    :return: None after status, current category, zero-card and text assertions.
    :raises AssertionError: If the production response violates the contract.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_experts_design_with_baseline_omits_empty_state(client: Client) -> None:
    """Prove populated categories do not render the empty branch.

    :param client: Isolated real client. Example: pytest client fixture.
    :return: None after Design-current, five-card and empty-element absence checks.
    :raises AssertionError: If populated Design is rendered as empty.
    """
    raise NotImplementedError()
