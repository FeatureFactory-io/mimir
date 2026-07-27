"""Unit tests for PlaybookExportService."""

import pytest
from pathlib import Path

from methodology.models import Agent, Artifact, Playbook, Rule, Skill, Workflow, Activity
from methodology.services.playbook_export_service import PlaybookExportService


@pytest.mark.django_db
class TestPlaybookExportService:
    @pytest.fixture
    def playbook_bundle(self, django_user_model, create_test_phases):
        user = django_user_model.objects.create_user(
            username="export_user",
            email="export@test.com",
            password="pass",
        )
        pb = Playbook.objects.create(
            name="Export Playbook",
            description="For export tests",
            category="development",
            author=user,
            status="released",
            version="1.0",
        )
        wf = Workflow.objects.create(
            playbook=pb,
            name="Main Flow",
            description="wf",
            order=1,
        )
        phases = create_test_phases(pb)
        act = Activity.objects.create(
            workflow=wf,
            name="Step One",
            guidance="guidance text here",
            order=1,
            phase=phases["Planning"],
        )
        Rule.objects.create(
            playbook=pb,
            title="Global Rule",
            slug="global-rule",
            content="Always apply this",
            always_apply=True,
        )
        Skill.objects.create(
            playbook=pb,
            title="Test Skill",
            capability_domain="TEST",
            technology_stack="Pytest",
            content="Skill body",
        )
        Agent.objects.create(playbook=pb, name="Test Agent", description="Agent body")
        Artifact.objects.create(
            playbook=pb,
            produced_by=act,
            name="Deliverable Doc",
            type="Document",
            is_required=True,
        )
        return user, pb, wf, act

    def test_export_writes_playbook_tree(self, playbook_bundle, tmp_path):
        user, pb, wf, _act = playbook_bundle
        result = PlaybookExportService.export_playbook_to_local(
            playbook_id=pb.pk,
            target_directory=str(tmp_path),
            folder_name="ExportPB",
            user=user,
        )

        export_root = Path(tmp_path) / "ExportPB"
        assert export_root.exists()
        assert (export_root / "playbook.md").exists()
        assert (export_root / "rules" / "global-rule.mdc").exists()
        assert (export_root / "agents" / "Test_Agent.md").exists()
        assert (export_root / "skills" / "Test_Skill.md").exists()
        assert (export_root / "artifacts" / "Deliverable_Doc.md").exists()
        assert (export_root / "Main_Flow" / "_workflow.md").exists()
        assert result["workflows"] == 1
        assert result["rules"] == 1
        assert result["agents"] == 1
        assert result["skills"] == 1
        assert result["artifacts"] == 1
        assert len(result["files_created"]) >= 6

    def test_generate_bundle_includes_unlinked_rules(self, playbook_bundle):
        user, pb, _wf, _act = playbook_bundle
        bundle = PlaybookExportService.generate_playbook_export_bundle(
            playbook_id=pb.pk,
            user=user,
        )
        assert bundle["counts"]["rules"] == 1
        assert bundle["rule_files"][0]["filename"] == "global-rule.mdc"
