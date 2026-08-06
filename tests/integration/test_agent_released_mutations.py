"""Agent mutations on released playbooks: block direct create/edit/delete."""

import logging
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from methodology.models import Agent, Playbook

User = get_user_model()


@pytest.fixture
def owner(db):
    return User.objects.create_user(username="ag_rel_owner", password="pwAG")


@pytest.fixture
def released_playbook(db, owner):
    return Playbook.objects.create(
        name="Released Agent PB",
        description="x" * 30,
        category="development",
        author=owner,
        status="released",
        version=Decimal("2.0"),
    )


@pytest.fixture
def draft_playbook(db, owner):
    return Playbook.objects.create(
        name="Draft Agent PB",
        description="x" * 30,
        category="development",
        author=owner,
        status="draft",
        version=Decimal("0.1"),
    )


@pytest.fixture
def agent_released(db, released_playbook):
    return Agent.objects.create(
        playbook=released_playbook,
        name="Released Agent",
        description="Agent on released playbook",
    )


@pytest.fixture
def agent_draft(db, draft_playbook):
    return Agent.objects.create(
        playbook=draft_playbook,
        name="Draft Agent",
        description="Agent on draft playbook",
    )


@pytest.mark.django_db
def test_agent_create_released_owner_redirects(owner, released_playbook):
    client = Client()
    client.force_login(owner)
    url = reverse("agent_create", kwargs={"playbook_pk": released_playbook.pk})
    rsp = client.get(url)
    assert rsp.status_code == 302
    assert rsp.url == reverse("playbook_detail", kwargs={"pk": released_playbook.pk})


@pytest.mark.django_db
def test_agent_edit_released_owner_redirects(owner, agent_released):
    client = Client()
    client.force_login(owner)
    url = reverse("agent_edit", kwargs={"pk": agent_released.pk})
    rsp = client.get(url)
    assert rsp.status_code == 302
    assert rsp.url == reverse("agent_detail", kwargs={"pk": agent_released.pk})


@pytest.mark.django_db
def test_agent_delete_released_owner_redirects(owner, agent_released):
    client = Client()
    client.force_login(owner)
    url = reverse("agent_delete", kwargs={"pk": agent_released.pk})
    rsp = client.get(url)
    assert rsp.status_code == 302
    assert rsp.url == reverse("agent_detail", kwargs={"pk": agent_released.pk})


@pytest.mark.django_db
def test_agent_detail_draft_owner_still_editable(owner, agent_draft):
    client = Client()
    client.force_login(owner)
    url = reverse("agent_detail", kwargs={"pk": agent_draft.pk})
    rsp = client.get(url)
    assert rsp.status_code == 200
    body = rsp.content.decode()
    assert 'data-testid="edit-agent-btn"' in body


@pytest.mark.django_db
def test_agent_create_released_logs_reject_warning(owner, released_playbook, caplog):
    caplog.set_level(logging.WARNING, logger="methodology.agent_views")
    client = Client()
    client.force_login(owner)
    url = reverse("agent_create", kwargs={"playbook_pk": released_playbook.pk})
    client.get(url)
    warnings = [
        r.message
        for r in caplog.records
        if "released_playbook_pip_required" in r.message
    ]
    assert warnings


@pytest.mark.django_db
def test_agent_edit_released_logs_reject_warning(owner, agent_released, caplog):
    caplog.set_level(logging.WARNING, logger="methodology.agent_views")
    client = Client()
    client.force_login(owner)
    url = reverse("agent_edit", kwargs={"pk": agent_released.pk})
    client.get(url)
    warnings = [
        r.message
        for r in caplog.records
        if "released_playbook_pip_required" in r.message
    ]
    assert warnings
