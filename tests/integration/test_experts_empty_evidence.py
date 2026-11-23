from __future__ import annotations

"""Real-DB certification of positive Experts profiles without eligible evidence."""
import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


def test_expert_detail_with_positive_sam_without_public_playbooks_returns_profile(
    client: Client,
) -> None:
    """Certify Sam's real positive profile and explicit empty evidence.

    :param client: Real Django client. Example: Elena-authenticated client.
    :return: None. Example: status, identity, evidence and no-write checks pass.
    :raises AssertionError: If Sam is rejected, misrepresented or GET awards points.
    """
    raise NotImplementedError()


@pytest.mark.parametrize(
    ("visibility", "status"),
    [("private", "released"), ("public", "draft"), ("public", "disabled")],
)
def test_expert_detail_with_only_ineligible_current_playbook_keeps_positive_profile(
    client: Client, visibility: str, status: str
) -> None:
    """Certify current evidence filtering without rewriting historical Karma.

    :param client: Real Django client. Example: Elena-authenticated client.
    :param visibility: Current 6101 visibility. Example: "private".
    :param status: Current 6101 status. Example: "released".
    :return: None. Example: Maria remains 8,200 with empty current evidence.
    :raises AssertionError: If ineligible evidence leaks or positive eligibility changes.
    """
    raise NotImplementedError()
