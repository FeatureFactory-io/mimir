"""API tests for POST /api/playbooks/{id}/export-local/ (#172).

Read-only export must succeed on released playbooks (same as workflow export).
No mocks — real DB + DRF APIClient.
"""

import logging

import pytest
from rest_framework.test import APIClient

from methodology.models import Playbook, Workflow
from tests.support.log_story import assert_log_story


@pytest.mark.django_db
class TestPlaybookExportLocalAPI:
    """FOB-WORKFLOWS-EXPORT_IMPORT-29: export-local allowed on released playbooks."""

    @pytest.fixture
    def user(self, django_user_model):
        return django_user_model.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="testpass123",
        )

    @pytest.fixture
    def client(self, user):
        api = APIClient()
        api.force_authenticate(user=user)
        return api

    @pytest.fixture
    def released_playbook(self, user):
        pb = Playbook.objects.create(
            name="Edda",
            description="Released playbook for IDE sync",
            category="development",
            author=user,
            status="released",
            version="70.0",
        )
        Workflow.objects.create(
            playbook=pb,
            name="Build Feature",
            description="BPE",
            abbreviation="BPE",
            order=1,
        )
        return pb

    def test_export_local_released_playbook_returns_200(self, client, released_playbook):
        """POST export-local on a released playbook returns a bundle, not PIP error."""
        response = client.post(
            f"/api/playbooks/{released_playbook.pk}/export-local/",
            {"folder_name": "edda"},
            format="json",
        )

        assert response.status_code == 200, response.data
        assert "Cannot modify released playbook" not in str(response.data)
        assert response.data["folder_name"] == "edda"
        assert "playbook_md" in response.data
        assert response.data["counts"]["workflows"] == 1

    def test_export_local_unauthenticated_rejected(self, released_playbook):
        """Unauthenticated POST returns 401 or 403."""
        response = APIClient().post(
            f"/api/playbooks/{released_playbook.pk}/export-local/",
            {"folder_name": "edda"},
            format="json",
        )
        assert response.status_code in (401, 403)

    def test_export_local_log_story_happy(self, client, released_playbook, caplog):
        """Released export logs entry + processing with status=released."""
        caplog.set_level(logging.INFO)
        response = client.post(
            f"/api/playbooks/{released_playbook.pk}/export-local/",
            {"folder_name": "edda"},
            format="json",
        )
        assert response.status_code == 200
        assert_log_story(
            caplog,
            where="PlaybookViewSet.export_local",
            beats={
                "entry": ["playbook_id=", str(released_playbook.pk)],
                "processing": ["status=released", "folder=edda"],
            },
        )
