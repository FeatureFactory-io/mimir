"""Integration tests for ADE-aware export_playbook_to_local (#176)."""

from decimal import Decimal

import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from methodology.models import Playbook, Rule, Workflow
from mcp_integration.context import set_current_user
from mcp_integration.tools import export_playbook_to_local


@pytest.mark.django_db(transaction=True)
class TestMcpExportPlaybookAde:
    @pytest.fixture
    def maria(self, django_user_model):
        return django_user_model.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="testpass123",
        )

    @pytest.fixture
    def edda_like(self, maria):
        pb = Playbook.objects.create(
            name="Edda",
            description="Released playbook",
            category="development",
            author=maria,
            status="released",
            version=Decimal("70.0"),
        )
        Workflow.objects.create(
            playbook=pb,
            name="Build Feature",
            description="BPE",
            abbreviation="BPE",
            order=1,
        )
        Rule.objects.create(
            playbook=pb,
            title="Test First",
            slug="do-test-first",
            content="Always test first.",
            always_apply=False,
        )
        return pb

    @pytest.fixture
    def api_client(self, maria):
        token, _ = Token.objects.get_or_create(user=maria)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return client

    @pytest.fixture
    def user_context(self, maria):
        set_current_user(maria)
        return maria

    def test_export_local_api_ade_params(self, api_client, edda_like):
        """FOB-WORKFLOWS-EXPORT_IMPORT-30/32: API returns ADE bundle fields."""
        response = api_client.post(
            f"/api/playbooks/{edda_like.pk}/export-local/",
            {
                "folder_name": "edda",
                "ade_targets": ["cursor"],
                "force_apply": True,
                "sync_root_rules": True,
            },
            format="json",
        )
        assert response.status_code == 200, response.data
        assert response.data["folder_name"] == "edda"
        assert len(response.data["ade_rule_files"]) == 1
        assert response.data["ade_rule_files"][0]["path"] == (
            ".cursor/rules/do-test-first.mdc"
        )
        assert "alwaysApply: true" in response.data["ade_rule_files"][0]["content"]
        assert "alwaysApply: false" in response.data["rule_files"][0]["content"]

        claude_resp = api_client.post(
            f"/api/playbooks/{edda_like.pk}/export-local/",
            {
                "folder_name": "edda",
                "ade_targets": ["claude"],
                "force_apply": True,
            },
            format="json",
        )
        assert claude_resp.status_code == 200
        assert claude_resp.data["inline_rules_markdown"]
        assert "do-test-first" in claude_resp.data["inline_rules_markdown"]
        assert claude_resp.data["ade_rule_files"] == []

    def test_export_local_api_ade_validation_error(self, api_client, edda_like):
        """FOB-WORKFLOWS-EXPORT_IMPORT-34: missing ade_targets returns 400."""
        response = api_client.post(
            f"/api/playbooks/{edda_like.pk}/export-local/",
            {"sync_root_rules": True, "force_apply": True},
            format="json",
        )
        assert response.status_code == 400
        assert "ade_targets required" in response.data["detail"]

    @pytest.mark.asyncio
    async def test_mcp_export_playbook_to_local_ade_t1(
        self, user_context, edda_like, tmp_path
    ):
        """MCP tool accepts ade_targets and returns inline_rules_markdown."""
        playbooks = tmp_path / ".cursor" / "playbooks"
        playbooks.mkdir(parents=True)
        result = await export_playbook_to_local(
            playbook_id=edda_like.pk,
            target_directory=str(playbooks),
            folder_name="edda",
            ade_targets=["claude"],
            force_apply=True,
        )
        assert result["inline_rules_markdown"]
        assert "do-test-first" in result["inline_rules_markdown"]

    @pytest.mark.asyncio
    async def test_mcp_export_playbook_to_local_ade_t2(
        self, user_context, edda_like, tmp_path
    ):
        """MCP tool writes force_apply cursor rules to disk."""
        project = tmp_path / "proj"
        playbooks = project / ".cursor" / "playbooks"
        playbooks.mkdir(parents=True)

        result = await export_playbook_to_local(
            playbook_id=edda_like.pk,
            target_directory=str(playbooks),
            folder_name="edda",
            ade_targets=["cursor"],
            sync_root_rules=True,
            force_apply=True,
        )
        cursor_file = project / ".cursor" / "rules" / "do-test-first.mdc"
        assert cursor_file.exists()
        assert "alwaysApply: true" in cursor_file.read_text()
        canonical = playbooks / "edda" / "rules" / "do-test-first.mdc"
        assert "alwaysApply: false" in canonical.read_text()
        assert len(result["ade_rule_files"]) == 1

    @pytest.mark.asyncio
    async def test_mcp_export_devin_only_no_cursor(
        self, user_context, edda_like, tmp_path
    ):
        """FOB-WORKFLOWS-EXPORT_IMPORT-31: devin target writes windsurf only."""
        project = tmp_path / "proj"
        playbooks = project / ".cursor" / "playbooks"
        playbooks.mkdir(parents=True)

        await export_playbook_to_local(
            playbook_id=edda_like.pk,
            target_directory=str(playbooks),
            folder_name="edda",
            ade_targets=["devin"],
            sync_root_rules=True,
            force_apply=True,
        )
        assert (project / ".windsurf" / "rules" / "do-test-first.md").exists()
        assert not (project / ".cursor" / "rules" / "do-test-first.mdc").exists()

    @pytest.mark.asyncio
    async def test_mcp_export_multi_target(self, user_context, edda_like, tmp_path):
        """ade_targets cursor+devin writes both ADE paths."""
        project = tmp_path / "proj"
        playbooks = project / ".cursor" / "playbooks"
        playbooks.mkdir(parents=True)

        await export_playbook_to_local(
            playbook_id=edda_like.pk,
            target_directory=str(playbooks),
            folder_name="edda",
            ade_targets=["cursor", "devin"],
            sync_root_rules=True,
            force_apply=True,
        )
        assert (project / ".cursor" / "rules" / "do-test-first.mdc").exists()
        assert (project / ".windsurf" / "rules" / "do-test-first.md").exists()

    @pytest.mark.asyncio
    async def test_mcp_export_ade_target_singular_alias(
        self, user_context, edda_like, tmp_path
    ):
        """Singular ade_target alias works like one-element ade_targets."""
        project = tmp_path / "proj"
        playbooks = project / ".cursor" / "playbooks"
        playbooks.mkdir(parents=True)

        await export_playbook_to_local(
            playbook_id=edda_like.pk,
            target_directory=str(playbooks),
            folder_name="edda",
            ade_target="cursor",
            sync_root_rules=True,
            force_apply=True,
        )
        assert (project / ".cursor" / "rules" / "do-test-first.mdc").exists()
