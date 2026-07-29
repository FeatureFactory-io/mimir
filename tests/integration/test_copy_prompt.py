"""Integration tests for Copy Prompt (Act 17)."""

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from methodology.models import Activity, Playbook, Workflow


@pytest.mark.django_db
class TestCopyPromptIntegration:
    def _fixture(self):
        user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="SecurePass123",
        )
        playbook = Playbook.objects.create(
            name="React Frontend Development",
            description="Playbook",
            category="development",
            author=user,
            visibility="public",
            status="released",
            version=1.2,
        )
        workflow = Workflow.objects.create(
            playbook=playbook,
            name="Component Development",
            description="Build components",
            abbreviation="CD",
            order=1,
        )
        activity = Activity.objects.create(
            workflow=workflow,
            name="Setup component structure",
            guidance="## Overview\nScaffold folders.",
            order=1,
        )
        return user, playbook, workflow, activity

    def test_activity_detail_renders_copy_prompt_button_and_hidden_text(self):
        user, playbook, workflow, activity = self._fixture()
        client = Client()
        client.force_login(user)

        url = reverse(
            "activity_detail",
            kwargs={
                "playbook_pk": playbook.pk,
                "workflow_pk": workflow.pk,
                "activity_pk": activity.pk,
            },
        )
        response = client.get(url)
        html = response.content.decode("utf-8")

        assert response.status_code == 200
        assert 'data-testid="copy-prompt-btn"' in html
        assert 'data-testid="activity-header-actions"' in html
        assert f'data-testid="copy-prompt-text-activity-{activity.pk}"' in html
        assert "Setup component structure" in html
        assert "Scaffold folders." in html
        assert "Copy prompt to use in your ADE" in html

    def test_activity_list_row_includes_copy_prompt_button(self):
        user, playbook, workflow, activity = self._fixture()
        client = Client()
        client.force_login(user)

        url = reverse(
            "activity_list",
            kwargs={"playbook_pk": playbook.pk, "workflow_pk": workflow.pk},
        )
        response = client.get(url)
        html = response.content.decode("utf-8")

        assert response.status_code == 200
        assert f'data-testid="copy-prompt-btn-activity-{activity.pk}"' in html
        assert f'data-testid="copy-prompt-text-activity-{activity.pk}"' in html

    def test_activity_embed_includes_copy_prompt_button(self):
        user, playbook, workflow, activity = self._fixture()
        client = Client()
        client.force_login(user)

        url = reverse(
            "activity_detail",
            kwargs={
                "playbook_pk": playbook.pk,
                "workflow_pk": workflow.pk,
                "activity_pk": activity.pk,
            },
        )
        response = client.get(url, {"embed": "1"})
        html = response.content.decode("utf-8")

        assert response.status_code == 200
        assert 'data-testid="copy-prompt-btn"' in html
        assert 'data-testid="activity-embed"' in html

    def test_guest_activity_detail_includes_copy_prompt_without_edit(self):
        _, playbook, workflow, activity = self._fixture()
        client = Client()

        url = reverse(
            "activity_detail",
            kwargs={
                "playbook_pk": playbook.pk,
                "workflow_pk": workflow.pk,
                "activity_pk": activity.pk,
            },
        )
        response = client.get(url)
        html = response.content.decode("utf-8")

        assert response.status_code == 200
        assert 'data-testid="copy-prompt-btn"' in html
        assert 'data-testid="edit-btn"' not in html
