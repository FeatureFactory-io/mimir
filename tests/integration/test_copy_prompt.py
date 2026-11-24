"""Integration tests for Copy Prompt (Act 17)."""

from http import HTTPStatus
from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import User
from django.db.models import Model
from django.test import Client
from django.urls import reverse

from methodology.models import (
    Activity,
    Agent,
    Artifact,
    Playbook,
    ProcessImprovementProposal,
    Rule,
    Skill,
    Workflow,
)
from methodology.services.copy_prompt_service import CopyPromptService
from tests.support.experts_html import find_by_test_id


def _assert_copy_receipt_metadata(
    html: str, test_id: str, entity_type: str, entity_id: int
) -> None:
    """Check the receipt target and CSRF context on a rendered copy control.

    :param html: Django response HTML. Example: an activity detail page.
    :param test_id: Existing copy button selector. Example: copy-prompt-btn.
    :param entity_type: Expected server entity kind. Example: activity.
    :param entity_id: Primary key of the copied entity. Example: 6203.
    :return: None after the contract is verified.
    :raises AssertionError: If receipt metadata is missing or incorrect.
    """
    control = find_by_test_id(html, test_id)
    assert control.name == "button"
    attributes = dict(control.attributes)
    assert attributes["data-copy-receipt-url"] == reverse("karma_copy_receipt")
    assert attributes["data-copy-receipt-entity-type"] == entity_type
    assert attributes["data-copy-receipt-entity-id"] == str(entity_id)
    assert attributes["data-copy-receipt-csrf"] not in ("", "NOTPROVIDED")


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
        _assert_copy_receipt_metadata(html, "copy-prompt-btn", "activity", activity.pk)

    def test_activity_create_with_crlf_keeps_guidance_and_builds_lf_prompt(
        self,
    ) -> None:
        """Exercise the actual Add Activity POST with textarea-style form encoding.

        :return: None after checking both saved Markdown and clipboard-ready text.
        :raises AssertionError: If authoring or copying alters the Markdown content.
        """
        user = User.objects.create_user(username="copy-author")
        playbook = Playbook.objects.create(name="Authoring", author=user)
        workflow = Workflow.objects.create(playbook=playbook, name="Writing")
        name = "Prepare the résumé"
        guidance = (
            "## Guide — 京都\n\n"
            "- Keep `<draft>`, `</textarea>` and `&lt;` & Unicode ✅.\n\n"
            "```text\n    Keep indentation and internal  spacing.\n```"
        )
        posted_guidance = guidance.replace("\n", "\r\n")
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse("activity_create", args=(playbook.pk, workflow.pk)),
            urlencode({"name": name, "guidance": posted_guidance}),
            content_type="application/x-www-form-urlencoded",
        )

        assert response.status_code == HTTPStatus.FOUND
        activity = Activity.objects.get(workflow=workflow, name=name)
        assert activity.guidance == posted_guidance
        prompt = CopyPromptService.build_activity_prompt(activity)
        assert prompt.partition("\n\n")[2] == guidance
        assert "\r" not in prompt
        activity.refresh_from_db(fields=["guidance"])
        assert activity.guidance == posted_guidance

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
        _assert_copy_receipt_metadata(
            html, f"copy-prompt-btn-activity-{activity.pk}", "activity", activity.pk
        )

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
        _assert_copy_receipt_metadata(html, "copy-prompt-btn", "activity", activity.pk)

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
        assert "data-copy-receipt-" not in html
        assert f'data-testid="copy-prompt-text-activity-{activity.pk}"' in html

    def test_activity_list_with_guest_renders_prompt_without_receipt(self) -> None:
        """Keep the guest copy source and button usable on a real list response."""
        _, playbook, workflow, activity = self._fixture()
        url = reverse(
            "activity_list",
            kwargs={"playbook_pk": playbook.pk, "workflow_pk": workflow.pk},
        )

        response = Client().get(url)

        assert response.status_code == 200
        html = response.content.decode(response.charset)
        assert "data-copy-receipt-" not in html
        find_by_test_id(html, f"copy-prompt-btn-activity-{activity.pk}")
        find_by_test_id(html, f"copy-prompt-text-activity-{activity.pk}")

    @pytest.mark.parametrize(
        ("entity_type", "model", "route_pk", "fields"),
        [
            ("agent", Agent, "pk", {"name": "Copy agent"}),
            ("artifact", Artifact, "pk", {"name": "Copy artifact", "type": "Document"}),
            ("pip", ProcessImprovementProposal, "pk", {"title": "Copy PIP"}),
            ("rule", Rule, "rule_pk", {"title": "Copy rule", "slug": "copy-rule"}),
            ("skill", Skill, "skill_pk", {"title": "Copy skill"}),
        ],
    )
    def test_entity_detail_with_authenticated_user_renders_receipt_metadata(
        self,
        entity_type: str,
        model: type[Model],
        route_pk: str,
        fields: dict[str, str],
    ) -> None:
        """Verify the shared detail control receives each view's real entity."""
        user, playbook, _, activity = self._fixture()
        related_fields = {}
        if entity_type == "pip":
            related_fields["created_by"] = user
        elif entity_type == "artifact":
            related_fields["produced_by"] = activity
        entity = model.objects.create(playbook=playbook, **related_fields, **fields)
        route_args = {route_pk: entity.pk}
        if route_pk != "pk":
            route_args["playbook_pk"] = playbook.pk
        client = Client()
        client.force_login(user)

        response = client.get(reverse(f"{entity_type}_detail", kwargs=route_args))

        assert response.status_code == 200
        html = response.content.decode(response.charset)
        _assert_copy_receipt_metadata(html, "copy-prompt-btn", entity_type, entity.pk)
        find_by_test_id(html, f"copy-prompt-text-{entity_type}-{entity.pk}")
