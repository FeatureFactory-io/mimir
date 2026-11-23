from __future__ import annotations

import pytest
from django.test import Client
from pytest import LogCaptureFixture


@pytest.mark.django_db
def test_experts_navigation_with_authenticated_elena_shows_default_page(
    client: Client,
) -> None:
    """Follow the rendered sidebar link against the real Cedar database.

    :param client: Real Django client. Example: authenticated Elena client.
    :return: None. Example: None.
    :raises AssertionError: If route, title, subtitle or default state differs.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_experts_navigation_log_story_happy(
    client: Client, caplog: LogCaptureFixture
) -> None:
    """Prove the authenticated Experts shell log story.

    :param client: Real Django client. Example: authenticated Elena client.
    :param caplog: INFO capture fixture. Example: captured shell records.
    :return: None. Example: None.
    :raises AssertionError: If response or a Section E beat is missing.
    """
    raise NotImplementedError()
