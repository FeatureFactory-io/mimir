from __future__ import annotations

"""Real HTTP certification for the anonymous Experts sidebar contract."""
import pytest
from django.test import Client


@pytest.mark.django_db
def test_guest_navigation_with_sidebar_href_reaches_public_experts(
    client: Client,
) -> None:
    """Follow the real guest shell link without authenticating.

    :param client: Real Django Client. Example: a fresh anonymous client.
    :return: None. Example: public 200 response and unchanged account counts.
    :raises AssertionError: Navigation, default category or privacy fails.
    """
    raise NotImplementedError()
