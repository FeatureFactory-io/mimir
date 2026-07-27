"""Caplog tests for guest browse Log Story Script rows."""

import logging

import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from methodology.models import Playbook, Workflow
from tests.support.log_story import assert_log_story

User = get_user_model()


@pytest.fixture
def owner(db):
    return User.objects.create_user(username="logowner", password="pass")


@pytest.fixture
def public_released(owner, db):
    return Playbook.objects.create(
        name="Log Story Public",
        description="Guest readable playbook for log story tests",
        category="development",
        author=owner,
        visibility="public",
        status="released",
        version=Decimal("1.0"),
    )


@pytest.fixture
def private_playbook(owner, db):
    return Playbook.objects.create(
        name="Log Story Private",
        description="Not for guests",
        category="development",
        author=owner,
        visibility="private",
        status="released",
        version=Decimal("1.0"),
    )


@pytest.fixture
def workflow(public_released, db):
    return Workflow.objects.create(
        playbook=public_released,
        name="Log Workflow",
        description="Workflow",
        order=1,
    )


@pytest.mark.django_db
class TestGuestLogStory:
    def test_guest_read_decorator_allow(self, client, public_released, caplog):
        caplog.set_level(logging.INFO)
        client.get(reverse("playbook_list"))
        assert_log_story(
            caplog,
            where="guest_read allow",
            beats={"allow": ["method=GET", "user=anonymous"]},
        )

    def test_guest_read_decorator_post_redirect(self, client, caplog):
        caplog.set_level(logging.INFO)
        client.post(reverse("workflow_global_list"))
        assert_log_story(
            caplog,
            where="guest_read redirect login",
            beats={"redirect": ["method=POST", "user=anonymous"]},
        )

    def test_playbook_access_deny(self, client, private_playbook, caplog):
        caplog.set_level(logging.INFO)
        client.get(reverse("playbook_detail", kwargs={"pk": private_playbook.pk}))
        assert_log_story(
            caplog,
            where="denied view on playbook",
            beats={
                "deny": [
                    "anonymous",
                    f"id={private_playbook.pk}",
                    "visibility=private",
                ]
            },
        )

    def test_playbook_access_grant(self, client, public_released, caplog):
        caplog.set_level(logging.INFO)
        client.get(reverse("playbook_detail", kwargs={"pk": public_released.pk}))
        # grant path: no deny log for this playbook
        deny_logs = [
            r.getMessage()
            for r in caplog.records
            if "denied view on playbook" in r.getMessage()
            and str(public_released.pk) in r.getMessage()
        ]
        assert deny_logs == []

    def test_guest_list_branch(self, client, public_released, caplog):
        caplog.set_level(logging.INFO)
        client.get(reverse("playbook_list"))
        guest_logs = [
            r.getMessage()
            for r in caplog.records
            if "guest" in r.getMessage().lower() or "anonymous" in r.getMessage()
        ]
        assert guest_logs

    def test_scoped_list_guest_branch(
        self, client, public_released, workflow, caplog
    ):
        caplog.set_level(logging.INFO)
        url = reverse("workflow_list", kwargs={"playbook_pk": public_released.pk})
        client.get(url)
        assert_log_story(
            caplog,
            where="viewing workflows for playbook",
            beats={
                "scoped": [
                    "anonymous",
                    f"playbook {public_released.pk}",
                ]
            },
        )
