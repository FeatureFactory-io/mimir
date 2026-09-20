"""
Regression tests for issues #181, #183, #184, #179:

PATCH /api/workflows/{id}/ silently ignored `order` because
WorkflowSerializer.Meta.read_only_fields included 'order'. HTTP MCP
update_workflow sent the field; DRF dropped it and returned 200 with the
old value.

Mirror of tests/integration/test_activity_order_patch.py (issue #117).
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
        username="wf_order_user", email="wf-order@test.com", password="pass"
    )


@pytest.fixture
def auth_client(user):
    client = Client()
    client.login(username="wf_order_user", password="pass")
    return client


@pytest.fixture
def draft_playbook(user):
    return Playbook.objects.create(
        name="Workflow Order Bug Playbook",
        description="",
        category="development",
        status="draft",
        source="owned",
        author=user,
    )


@pytest.fixture
def workflows(draft_playbook):
    first = Workflow.objects.create(
        name="Early Feasibility",
        description="",
        playbook=draft_playbook,
        order=1,
        abbreviation="EFY",
    )
    inserted = Workflow.objects.create(
        name="IDA Demand Assessment",
        description="",
        playbook=draft_playbook,
        order=11,
        abbreviation="IDA",
    )
    return first, inserted


@pytest.mark.django_db
class TestWorkflowOrderPatch:
    """Issues #181/#183/#184 — order must persist via PATCH API."""

    def test_patch_order_persists_in_response(self, auth_client, workflows):
        """PATCH with order=2 must return order=2 (was silently returning 11)."""
        _first, inserted = workflows
        url = f"/api/workflows/{inserted.pk}/"
        resp = auth_client.patch(
            url, data=json.dumps({"order": 2}), content_type="application/json"
        )
        assert resp.status_code == 200, resp.content
        data = resp.json()
        assert data["order"] == 2, (
            f"Expected order=2 in response, got {data['order']}. "
            "Likely cause: 'order' is still in read_only_fields on WorkflowSerializer."
        )

    def test_patch_order_persists_in_database(self, auth_client, workflows):
        """PATCH with order=2 must commit the value to the database."""
        _first, inserted = workflows
        url = f"/api/workflows/{inserted.pk}/"
        resp = auth_client.patch(
            url, data=json.dumps({"order": 2}), content_type="application/json"
        )
        assert resp.status_code == 200, resp.content
        inserted.refresh_from_db()
        assert inserted.order == 2, (
            f"DB order is still {inserted.order} after PATCH with order=2."
        )

    def test_patch_order_does_not_affect_other_fields(self, auth_client, workflows):
        """Changing only order must leave name and abbreviation untouched."""
        _first, inserted = workflows
        original_name = inserted.name
        original_abbr = inserted.abbreviation
        url = f"/api/workflows/{inserted.pk}/"
        resp = auth_client.patch(
            url, data=json.dumps({"order": 3}), content_type="application/json"
        )
        assert resp.status_code == 200, resp.content
        inserted.refresh_from_db()
        assert inserted.name == original_name
        assert inserted.abbreviation == original_abbr
        assert inserted.order == 3

    def test_list_workflows_reflects_patched_order(self, auth_client, workflows, draft_playbook):
        """list_workflows sequence must change after PATCH order (issue #184)."""
        _first, inserted = workflows
        resp = auth_client.patch(
            f"/api/workflows/{inserted.pk}/",
            data=json.dumps({"order": 0}),
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.content

        listed = auth_client.get("/api/workflows/", {"playbook_id": draft_playbook.pk})
        assert listed.status_code == 200, listed.content
        body = listed.json()
        rows = body.get("results", body)
        orders_by_id = {row["id"]: row["order"] for row in rows}
        assert orders_by_id[inserted.pk] == 0
