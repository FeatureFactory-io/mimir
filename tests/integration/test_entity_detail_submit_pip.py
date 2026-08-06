"""Submit PIP on released agent/skill/rule detail pages."""

import logging
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from methodology.models import Agent, Playbook, Rule, Skill

User = get_user_model()


@pytest.fixture
def owner(db):
    return User.objects.create_user(username="ent_pip_owner", password="pwENT")


@pytest.fixture
def released_playbook(db, owner):
    return Playbook.objects.create(
        name="Released Entity PB",
        description="x" * 30,
        category="development",
        author=owner,
        status="released",
        version=Decimal("2.0"),
    )


@pytest.fixture
def draft_playbook(db, owner):
    return Playbook.objects.create(
        name="Draft Entity PB",
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
        description="On released playbook",
    )


@pytest.fixture
def agent_draft(db, draft_playbook):
    return Agent.objects.create(
        playbook=draft_playbook,
        name="Draft Agent",
        description="On draft playbook",
    )


@pytest.fixture
def skill_released(db, released_playbook):
    return Skill.objects.create(
        playbook=released_playbook,
        title="Released Skill",
        content="Skill body",
    )


@pytest.fixture
def skill_draft(db, draft_playbook):
    return Skill.objects.create(
        playbook=draft_playbook,
        title="Draft Skill",
        content="Skill body",
    )


@pytest.fixture
def rule_released(db, released_playbook):
    return Rule.objects.create(
        playbook=released_playbook,
        title="Released Rule",
        slug="released-rule",
        content="Rule body",
    )


@pytest.fixture
def rule_draft(db, draft_playbook):
    return Rule.objects.create(
        playbook=draft_playbook,
        title="Draft Rule",
        slug="draft-rule",
        content="Rule body",
    )


@pytest.mark.django_db
def test_agent_detail_released_owner_sees_submit_pip_not_edit(
    owner, released_playbook, agent_released
):
    client = Client()
    client.force_login(owner)
    url = reverse("agent_detail", kwargs={"pk": agent_released.pk})
    rsp = client.get(url)
    assert rsp.status_code == 200
    body = rsp.content.decode()
    assert 'data-testid="agent-submit-pip-btn"' in body
    assert 'data-testid="edit-agent-btn"' not in body
    assert f"playbook={released_playbook.pk}" in body


@pytest.mark.django_db
def test_agent_detail_draft_owner_sees_edit_not_pip(owner, agent_draft):
    client = Client()
    client.force_login(owner)
    url = reverse("agent_detail", kwargs={"pk": agent_draft.pk})
    rsp = client.get(url)
    assert rsp.status_code == 200
    body = rsp.content.decode()
    assert 'data-testid="edit-agent-btn"' in body
    assert 'data-testid="agent-submit-pip-btn"' not in body


@pytest.mark.django_db
def test_agent_detail_released_logs_can_submit_pip(owner, agent_released, caplog):
    caplog.set_level(logging.INFO, logger="methodology.agent_views")
    client = Client()
    client.force_login(owner)
    client.get(reverse("agent_detail", kwargs={"pk": agent_released.pk}))
    exit_logs = [
        r.message for r in caplog.records if "Agent detail rendered" in r.message
    ]
    assert exit_logs
    assert "can_submit_pip=True" in exit_logs[-1]


@pytest.mark.django_db
def test_skill_detail_released_owner_sees_submit_pip_not_edit(
    owner, released_playbook, skill_released
):
    client = Client()
    client.force_login(owner)
    url = reverse(
        "skill_detail",
        kwargs={"playbook_pk": released_playbook.pk, "skill_pk": skill_released.pk},
    )
    rsp = client.get(url)
    assert rsp.status_code == 200
    body = rsp.content.decode()
    assert 'data-testid="skill-submit-pip-btn"' in body
    assert 'data-testid="edit-skill-btn"' not in body
    assert f"playbook={released_playbook.pk}" in body


@pytest.mark.django_db
def test_skill_detail_draft_owner_sees_edit_not_pip(
    owner, draft_playbook, skill_draft
):
    client = Client()
    client.force_login(owner)
    url = reverse(
        "skill_detail",
        kwargs={"playbook_pk": draft_playbook.pk, "skill_pk": skill_draft.pk},
    )
    rsp = client.get(url)
    assert rsp.status_code == 200
    body = rsp.content.decode()
    assert 'data-testid="edit-skill-btn"' in body
    assert 'data-testid="skill-submit-pip-btn"' not in body


@pytest.mark.django_db
def test_skill_detail_released_logs_can_submit_pip(
    owner, released_playbook, skill_released, caplog
):
    caplog.set_level(logging.INFO, logger="methodology.skill_views")
    client = Client()
    client.force_login(owner)
    client.get(
        reverse(
            "skill_detail",
            kwargs={"playbook_pk": released_playbook.pk, "skill_pk": skill_released.pk},
        )
    )
    exit_logs = [
        r.message for r in caplog.records if "viewing skill" in r.message
    ]
    assert exit_logs
    assert "can_submit_pip=True" in exit_logs[-1]


@pytest.mark.django_db
def test_rule_detail_released_owner_sees_submit_pip_not_edit(
    owner, released_playbook, rule_released
):
    client = Client()
    client.force_login(owner)
    url = reverse(
        "rule_detail",
        kwargs={"playbook_pk": released_playbook.pk, "rule_pk": rule_released.pk},
    )
    rsp = client.get(url)
    assert rsp.status_code == 200
    body = rsp.content.decode()
    assert 'data-testid="rule-submit-pip-btn"' in body
    assert 'data-testid="edit-rule-btn"' not in body
    assert f"playbook={released_playbook.pk}" in body


@pytest.mark.django_db
def test_rule_detail_draft_owner_sees_edit_not_pip(
    owner, draft_playbook, rule_draft
):
    client = Client()
    client.force_login(owner)
    url = reverse(
        "rule_detail",
        kwargs={"playbook_pk": draft_playbook.pk, "rule_pk": rule_draft.pk},
    )
    rsp = client.get(url)
    assert rsp.status_code == 200
    body = rsp.content.decode()
    assert 'data-testid="edit-rule-btn"' in body
    assert 'data-testid="rule-submit-pip-btn"' not in body


@pytest.mark.django_db
def test_rule_detail_released_logs_can_submit_pip(
    owner, released_playbook, rule_released, caplog
):
    caplog.set_level(logging.INFO, logger="methodology.rule_views")
    client = Client()
    client.force_login(owner)
    client.get(
        reverse(
            "rule_detail",
            kwargs={"playbook_pk": released_playbook.pk, "rule_pk": rule_released.pk},
        )
    )
    exit_logs = [
        r.message for r in caplog.records if "viewing rule" in r.message
    ]
    assert exit_logs
    assert "can_submit_pip=True" in exit_logs[-1]
