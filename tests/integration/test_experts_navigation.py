from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse
from pytest import LogCaptureFixture

from tests.support.experts_data import CedarDataset
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story


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
    client: Client, cedar_dataset: CedarDataset, caplog: LogCaptureFixture
) -> None:
    """Prove the authenticated Experts shell log story.

    :param client: Real Django client. Example: authenticated Elena client.
    :param cedar_dataset: Real Cedar baseline. Example: Elena is esvensson.
    :param caplog: INFO capture fixture. Example: captured shell records.
    :return: None. Example: None.
    :raises AssertionError: If response or a Section E beat is missing.
    """
    client.force_login(cedar_dataset.users_by_username["esvensson"])
    with capture_experts_logs(caplog, ("methodology.context_processors",)):
        response = client.get(reverse("experts_list"))
    assert response.status_code == 200
    assert response.context["nav_section"] == "experts"
    assert response.context["chrome"] == "authenticated"
    assert_log_story(
        caplog,
        where="primary_nav_section",
        beats={
            "entry": ("entry", "path=/experts/"),
            "branch": ("branch", "chrome=authenticated"),
            "exit": ("exit", "nav_section=experts"),
        },
    )
