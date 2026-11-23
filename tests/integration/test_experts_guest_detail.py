from __future__ import annotations

"""EXPERTS-REACH-03 real Django-client certification."""
import pytest
from django.test import Client


@pytest.mark.django_db
def test_guest_detail_with_anonymous_request_preserves_restricted_contact_and_public_evidence(
    client: Client,
) -> None:
    """Prove guest restriction without removing public contribution evidence.

    :param client: Real anonymous Django client. Example: Client().
    :return: None. Example: None after all real response assertions pass.
    :raises AssertionError: If contact leaks, restriction fails or evidence disappears.
    """
    raise NotImplementedError()
