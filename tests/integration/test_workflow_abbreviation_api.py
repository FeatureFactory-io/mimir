"""
Regression tests for issue #182:

workflow abbreviation is auto-assigned at create, not settable via MCP/API,
and frozen on rename. create_workflow / update_workflow must accept an
explicit abbreviation (e.g. IDA instead of auto IAN).
"""

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from methodology.models import Playbook, Workflow

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="wf_abbr_user", email="wf-abbr@test.com", password="pass"
    )


@pytest.fixture
def auth_client(user):
    client = Client()
    client.login(username="wf_abbr_user", password="pass")
    return client


@pytest.fixture
def draft_playbook(user):
    return Playbook.objects.create(
        name="Abbreviation Bug Playbook",
        description="",
        category="development",
        status="draft",
        source="owned",
        author=user,
    )


@pytest.mark.django_db
class TestWorkflowAbbreviationApi:
    """Issue #182 — abbreviation is first-class on create and update."""

    def test_post_create_accepts_explicit_abbreviation(self, auth_client, draft_playbook):
        """POST with abbreviation=IDA must persist IDA, not the auto IAN code."""
        resp = auth_client.post(
            "/api/workflows/",
            data=json.dumps(
                {
                    "playbook_id": draft_playbook.pk,
                    "name": "Investigate the Demand Assumption",
                    "description": "",
                    "abbreviation": "IDA",
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 201, resp.content
        data = resp.json()
        assert data["abbreviation"] == "IDA", (
            f"Expected abbreviation=IDA, got {data.get('abbreviation')!r}. "
            "create_workflow must accept an explicit code."
        )
        stored = Workflow.objects.get(pk=data["id"])
        assert stored.abbreviation == "IDA"

    def test_patch_abbreviation_corrects_bad_auto_code(self, auth_client, draft_playbook):
        """PATCH abbreviation must replace a wrong auto-generated code."""
        workflow = Workflow.objects.create(
            name="Investigate the Demand Assumption",
            playbook=draft_playbook,
            order=1,
        )
        assert workflow.abbreviation != "IDA"

        resp = auth_client.patch(
            f"/api/workflows/{workflow.pk}/",
            data=json.dumps({"abbreviation": "IDA"}),
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.content
        assert resp.json()["abbreviation"] == "IDA"
        workflow.refresh_from_db()
        assert workflow.abbreviation == "IDA"

    def test_rename_does_not_clobber_explicit_abbreviation(self, auth_client, draft_playbook):
        """Renaming a workflow must keep an explicitly set abbreviation."""
        workflow = Workflow.objects.create(
            name="IDA Demand Assessment",
            playbook=draft_playbook,
            order=1,
            abbreviation="IDA",
        )
        resp = auth_client.patch(
            f"/api/workflows/{workflow.pk}/",
            data=json.dumps({"name": "Idea Demand Assessment"}),
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.content
        workflow.refresh_from_db()
        assert workflow.abbreviation == "IDA"
        assert workflow.name == "Idea Demand Assessment"

    def test_create_rejects_duplicate_abbreviation(self, auth_client, draft_playbook):
        """Two workflows in the same playbook cannot share an explicit code."""
        Workflow.objects.create(
            name="Existing IDA",
            playbook=draft_playbook,
            order=1,
            abbreviation="IDA",
        )
        resp = auth_client.post(
            "/api/workflows/",
            data=json.dumps(
                {
                    "playbook_id": draft_playbook.pk,
                    "name": "Another Demand",
                    "abbreviation": "IDA",
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 400, resp.content
