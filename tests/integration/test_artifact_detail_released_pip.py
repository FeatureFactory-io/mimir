"""Artifact detail: Submit PIP on released owned playbook; edit when draft."""

import logging
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from methodology.models import Activity, Artifact, Playbook, Workflow

User = get_user_model()


@pytest.fixture
def owner(db):
    return User.objects.create_user(username="art_rel_owner", password="pwART")


@pytest.fixture
def released_playbook(db, owner):
    return Playbook.objects.create(
        name="Released Art PB",
        description="x" * 30,
        category="development",
        author=owner,
        status="released",
        version=Decimal("2.0"),
    )


@pytest.fixture
def draft_playbook(db, owner):
    return Playbook.objects.create(
        name="Draft Art PB",
        description="x" * 30,
        category="development",
        author=owner,
        status="draft",
        version=Decimal("0.1"),
    )


@pytest.fixture
def wf_released(db, released_playbook):
    return Workflow.objects.create(
        name="WF",
        playbook=released_playbook,
        order=1,
    )


@pytest.fixture
def wf_draft(db, draft_playbook):
    return Workflow.objects.create(
        name="WFD",
        playbook=draft_playbook,
        order=1,
    )


@pytest.fixture
def producer_released(db, wf_released):
    return Activity.objects.create(
        workflow=wf_released,
        name="Producer",
        guidance="G",
        order=1,
    )


@pytest.fixture
def producer_draft(db, wf_draft):
    return Activity.objects.create(
        workflow=wf_draft,
        name="DraftProducer",
        guidance="D",
        order=1,
    )


@pytest.fixture
def artifact_released(db, released_playbook, producer_released):
    return Artifact.objects.create(
        playbook=released_playbook,
        produced_by=producer_released,
        name="Bug Report",
        description="Issue template",
        type="Document",
    )


@pytest.fixture
def artifact_draft(db, draft_playbook, producer_draft):
    return Artifact.objects.create(
        playbook=draft_playbook,
        produced_by=producer_draft,
        name="Draft Artifact",
        description="Draft doc",
        type="Document",
    )


@pytest.mark.django_db
def test_artifact_detail_released_owner_sees_submit_pip_not_edit(
    owner, released_playbook, wf_released, producer_released, artifact_released
):
    client = Client()
    client.force_login(owner)
    url = reverse("artifact_detail", kwargs={"pk": artifact_released.pk})
    rsp = client.get(url)
    assert rsp.status_code == 200
    body = rsp.content.decode()
    assert 'data-testid="artifact-submit-pip-btn"' in body
    assert 'data-testid="edit-btn"' not in body
    assert (
        f"pips/create/?playbook={released_playbook.pk}&amp;workflow={wf_released.pk}&amp;activity={producer_released.pk}"
        in body
        or f"activity={producer_released.pk}" in body
    )


@pytest.mark.django_db
def test_artifact_detail_draft_owner_sees_edit(
    owner, draft_playbook, artifact_draft
):
    client = Client()
    client.force_login(owner)
    url = reverse("artifact_detail", kwargs={"pk": artifact_draft.pk})
    rsp = client.get(url)
    assert rsp.status_code == 200
    body = rsp.content.decode()
    assert 'data-testid="edit-btn"' in body
    assert 'data-testid="artifact-submit-pip-btn"' not in body


@pytest.mark.django_db
def test_artifact_edit_released_owner_redirects(
    owner, artifact_released
):
    client = Client()
    client.force_login(owner)
    url = reverse("artifact_edit", kwargs={"pk": artifact_released.pk})
    rsp = client.get(url)
    assert rsp.status_code == 302
    assert rsp.url == reverse("artifact_detail", kwargs={"pk": artifact_released.pk})


@pytest.mark.django_db
def test_artifact_create_released_blocked(
    owner, released_playbook
):
    client = Client()
    client.force_login(owner)
    url = reverse("artifact_create", kwargs={"playbook_pk": released_playbook.pk})
    rsp = client.get(url)
    assert rsp.status_code == 302
    assert rsp.url == reverse("playbook_detail", kwargs={"pk": released_playbook.pk})


@pytest.mark.django_db
def test_artifact_list_released_hides_create_and_row_mutations(
    owner, released_playbook, artifact_released
):
    client = Client()
    client.force_login(owner)
    url = reverse("artifact_list", kwargs={"playbook_id": released_playbook.pk})
    rsp = client.get(url)
    assert rsp.status_code == 200
    body = rsp.content.decode()
    assert 'data-testid="btn-create-artifact"' not in body
    edit_path = reverse("artifact_edit", kwargs={"pk": artifact_released.pk})
    assert edit_path not in body
    delete_path = reverse("artifact_delete", kwargs={"pk": artifact_released.pk})
    assert delete_path not in body


@pytest.mark.django_db
def test_artifact_detail_released_logs_permission_branch(
    owner, artifact_released, caplog
):
    caplog.set_level(logging.INFO, logger="methodology.artifact_views")
    client = Client()
    client.force_login(owner)
    url = reverse("artifact_detail", kwargs={"pk": artifact_released.pk})
    client.get(url)
    exit_logs = [
        r.message
        for r in caplog.records
        if "Artifact detail rendered" in r.message
    ]
    assert exit_logs, "expected artifact detail exit log"
    msg = exit_logs[-1]
    assert "can_edit=False" in msg
    assert "can_submit_pip=True" in msg


@pytest.mark.django_db
def test_artifact_edit_released_logs_reject_warning(
    owner, artifact_released, caplog
):
    caplog.set_level(logging.WARNING, logger="methodology.artifact_views")
    client = Client()
    client.force_login(owner)
    url = reverse("artifact_edit", kwargs={"pk": artifact_released.pk})
    client.get(url)
    warnings = [
        r.message
        for r in caplog.records
        if "released_playbook_pip_required" in r.message
    ]
    assert warnings
