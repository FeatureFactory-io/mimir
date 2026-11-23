from __future__ import annotations

from typing import TYPE_CHECKING
import pytest
from django.test import Client

if TYPE_CHECKING:
    from tests.support.experts_data import CedarDataset


@pytest.mark.django_db
@pytest.mark.parametrize("username", ("no-such-cedar-user", "nberg"))
def test_expert_detail_with_missing_or_zero_karma_subject_returns_404(
    client: Client, username: str
) -> None:
    """Certify absent and zero-total subjects through the real detail route.

    :param client: Real anonymous Django client. Example: Client().
    :param username: Exact outline subject. Example: "nberg".
    :return: None after 404, no-redirect and read-only assertions pass.
    :raises AssertionError: If eligibility, status or privacy assertions fail.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_expert_detail_with_ineligible_subject_hides_account_existence(
    client: Client,
) -> None:
    """Compare generic rejection content without exposing the existing account.

    :param client: Real anonymous Django client. Example: Client().
    :return: None after equivalent safe content and sensitive-value checks.
    :raises AssertionError: If Nora's existence or private data is exposed.
    """
    raise NotImplementedError()


@pytest.mark.django_db
@pytest.mark.parametrize("username", ("no-such-cedar-user", "nberg"))
def test_expert_detail_with_rejected_subject_log_story_reject(
    client: Client, caplog: pytest.LogCaptureFixture, username: str
) -> None:
    """Prove S17's correlated, uniformly sanitized rejection narrative.

    :param client: Real anonymous Django client. Example: Client().
    :param caplog: Real pytest logging capture. Example: INFO capture.
    :param username: Exact rejection subject. Example: "nberg".
    :return: None after entry, rejection and exit beats are verified.
    :raises AssertionError: If a required beat or privacy safeguard fails.
    """
    raise NotImplementedError()
