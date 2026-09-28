"""Log story for the FOB shell context processor."""

import logging

import pytest

from tests.support.log_story import assert_log_story


@pytest.mark.django_db
def test_app_shell_log_story_happy(client, django_user_model, caplog):
    user = django_user_model.objects.create_user(username="shell_log", password="pass")
    client.force_login(user)
    with caplog.at_level(logging.INFO, logger="methodology.context_processors"):
        response = client.get("/playbooks/")
    assert response.status_code == 200
    assert_log_story(
        caplog,
        where="primary_nav_section",
        beats={
            "entry": ["entry", "path=/playbooks/"],
            "branch": ["branch", "chrome=authenticated"],
            "exit": ["exit", "nav_section=playbooks"],
        },
    )


@pytest.mark.django_db
def test_app_shell_log_story_guest(client, caplog):
    with caplog.at_level(logging.INFO, logger="methodology.context_processors"):
        response = client.get("/")
    assert response.status_code == 200
    assert_log_story(
        caplog,
        where="primary_nav_section",
        beats={
            "entry": ["entry", "path=/"],
            "branch": ["branch", "chrome=guest"],
            "exit": ["exit", "nav_section=none"],
        },
    )
