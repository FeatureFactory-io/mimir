from __future__ import annotations

"""Real HTTP contracts for readable public cards."""
import pytest
from django.test import Client


@pytest.mark.django_db
def test_experts_card_with_cedar_baseline_shows_readable_signals(
    client: Client,
) -> None:
    """Prove Maria's scoped card identity, total, hint and action destinations.

    :param client: Real Django client. Example: Elena requests Design.
    :return: None. Example: rank 2, 8,200, Design and both actions verified.
    :raises AssertionError: If rendered public signals or destinations differ.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_experts_card_with_stored_caveat_adds_no_suitability_claim(
    client: Client,
) -> None:
    """Preserve approved prose while rejecting added inferred claims.

    :param client: Real Django client. Example: Design list request.
    :return: None. Example: stored caveat retained with no recommendation badge.
    :raises AssertionError: If extra suitability/availability claims appear.
    """
    raise NotImplementedError()
