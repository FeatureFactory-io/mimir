from __future__ import annotations

import pytest
from django.test import Client
from tests.support.experts_data import CedarDataset


@pytest.fixture
def cedar_guest_contact_dataset(db: None) -> CedarDataset:
    """Load the real shared Cedar baseline for one server-contract test.

    :param db: Isolated pytest database fixture. Example: enabled test transaction.
    :return: CedarDataset from load_cedar_baseline(); example: users_by_username["mrodriguez"].
    :raises ValueError: If the Cedar adapter rejects inconsistent source data.
    """
    raise NotImplementedError()


def test_guest_list_contact_with_anonymous_request_restricts_contact(
    client: Client, cedar_guest_contact_dataset: CedarDataset
) -> None:
    """Prove initial production guest HTML and the available profile link.

    :param client: Anonymous real Django client. Example: no authenticated session.
    :param cedar_guest_contact_dataset: Real baseline. Example: Maria has 8200 total Karma.
    :return: None when HTTP 200, shared guest markup/privacy and profile-link assertions pass.
    :raises AssertionError: If contact is available, email leaks or the profile action is unavailable.
    """
    raise NotImplementedError()


def test_guest_list_contact_with_authenticated_then_guest_requests_does_not_leak_email(
    client: Client, cedar_guest_contact_dataset: CedarDataset
) -> None:
    """Detect contact data leaking from a prior authenticated list request.

    :param client: Real client reused across login/logout. Example: authenticated Elena followed by guest.
    :param cedar_guest_contact_dataset: Real baseline. Example: users_by_username["esvensson"].
    :return: None after authenticated mailto is observed, logout occurs and guest privacy checks pass.
    :raises AssertionError: If the guest request retains authentication or any contact destination/email.
    """
    raise NotImplementedError()
