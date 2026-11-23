from __future__ import annotations

"""Real Django-client contract for EXPERTS-LIST-07."""
import pytest
from django.test import Client


@pytest.mark.django_db
def test_experts_list_with_anonymous_design_request_matches_public_ranking(
    client: Client,
) -> None:
    """Compare public cards and prove the anonymous account boundary.

    :param client: Real Django Client. Example: unauthenticated client.
    :return: None. Example: equal cards, valid banner, unchanged DB counts.
    :raises AssertionError: Ranking, account privacy or read-only state fails.
    """
    raise NotImplementedError()
