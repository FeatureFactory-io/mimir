"""ADE export tests for PlaybookExportService."""

import logging

import pytest

from methodology.models import Playbook, Rule, Workflow
from methodology.services.playbook_export_service import PlaybookExportService
from tests.support.log_story import assert_log_story


@pytest.mark.django_db
class TestPlaybookExportAde:
    @pytest.fixture
    def ade_playbook(self, django_user_model):
        user = django_user_model.objects.create_user(
            username="ade_user",
            email="ade@test.com",
            password="pass",
        )
        pb = Playbook.objects.create(
            name="ADE Playbook",
            description="ADE export",
            category="development",
            author=user,
            status="released",
            version="1.0",
        )
        Workflow.objects.create(
            playbook=pb,
            name="Flow",
            description="wf",
            order=1,
        )
        Rule.objects.create(
            playbook=pb,
            title="Test First",
            slug="do-test-first",
            content="Test first content.",
            always_apply=False,
        )
        Rule.objects.create(
            playbook=pb,
            title="Always On",
            slug="always-on",
            content="Always content.",
            always_apply=True,
        )
        return user, pb

    def test_sync_ade_rules_cursor_only(self, ade_playbook, tmp_path):
        user, pb = ade_playbook
        project = tmp_path / "proj"
        playbooks = project / ".cursor" / "playbooks"
        playbooks.mkdir(parents=True)

        PlaybookExportService.export_playbook_to_local(
            playbook_id=pb.pk,
            target_directory=str(playbooks),
            folder_name="ade",
            ade_targets=["cursor"],
            sync_root_rules=True,
            force_apply=True,
            user=user,
        )

        cursor_rule = project / ".cursor" / "rules" / "do-test-first.mdc"
        windsurf_rule = project / ".windsurf" / "rules" / "do-test-first.md"
        assert cursor_rule.exists()
        assert "alwaysApply: true" in cursor_rule.read_text()
        assert not windsurf_rule.exists()

    def test_sync_ade_rules_devin_only(self, ade_playbook, tmp_path):
        user, pb = ade_playbook
        project = tmp_path / "proj"
        playbooks = project / ".cursor" / "playbooks"
        playbooks.mkdir(parents=True)

        PlaybookExportService.export_playbook_to_local(
            playbook_id=pb.pk,
            target_directory=str(playbooks),
            folder_name="ade",
            ade_targets=["devin"],
            sync_root_rules=True,
            force_apply=True,
            user=user,
        )

        assert (project / ".windsurf" / "rules" / "do-test-first.md").exists()
        assert not (project / ".cursor" / "rules" / "do-test-first.mdc").exists()

    def test_sync_ade_rules_multi_target(self, ade_playbook, tmp_path):
        user, pb = ade_playbook
        project = tmp_path / "proj"
        playbooks = project / ".cursor" / "playbooks"
        playbooks.mkdir(parents=True)

        PlaybookExportService.export_playbook_to_local(
            playbook_id=pb.pk,
            target_directory=str(playbooks),
            folder_name="ade",
            ade_targets=["cursor", "devin"],
            sync_root_rules=True,
            force_apply=True,
            user=user,
        )

        assert (project / ".cursor" / "rules" / "do-test-first.mdc").exists()
        assert (project / ".windsurf" / "rules" / "do-test-first.md").exists()

    def test_canonical_tree_preserves_stored_always_apply(
        self, ade_playbook, tmp_path
    ):
        user, pb = ade_playbook
        project = tmp_path / "proj"
        playbooks = project / ".cursor" / "playbooks"
        playbooks.mkdir(parents=True)

        PlaybookExportService.export_playbook_to_local(
            playbook_id=pb.pk,
            target_directory=str(playbooks),
            folder_name="ade",
            ade_targets=["cursor"],
            sync_root_rules=True,
            force_apply=True,
            user=user,
        )

        canonical = playbooks / "ade" / "rules" / "do-test-first.mdc"
        assert canonical.exists()
        assert "alwaysApply: false" in canonical.read_text()

    def test_export_requires_ade_targets_when_sync_root_rules(
        self, ade_playbook, tmp_path
    ):
        user, pb = ade_playbook
        with pytest.raises(ValueError, match="ade_targets required"):
            PlaybookExportService.export_playbook_to_local(
                playbook_id=pb.pk,
                target_directory=str(tmp_path),
                sync_root_rules=True,
                user=user,
            )

    def test_export_requires_ade_targets_when_force_apply(
        self, ade_playbook, tmp_path
    ):
        user, pb = ade_playbook
        with pytest.raises(ValueError, match="ade_targets required"):
            PlaybookExportService.export_playbook_to_local(
                playbook_id=pb.pk,
                target_directory=str(tmp_path),
                force_apply=True,
                user=user,
            )

    def test_inline_rules_markdown_claude(self, ade_playbook):
        user, pb = ade_playbook
        bundle = PlaybookExportService.generate_playbook_export_bundle(
            playbook_id=pb.pk,
            ade_targets=["claude"],
            force_apply=True,
            user=user,
        )
        assert bundle["inline_rules_markdown"]
        assert "do-test-first" in bundle["inline_rules_markdown"]
        assert bundle["ade_rule_files"] == []

    def test_playbook_export_ade_log_story_happy(self, ade_playbook, tmp_path, caplog):
        user, pb = ade_playbook
        caplog.set_level(logging.INFO)
        project = tmp_path / "proj"
        playbooks = project / ".cursor" / "playbooks"
        playbooks.mkdir(parents=True)

        PlaybookExportService.export_playbook_to_local(
            playbook_id=pb.pk,
            target_directory=str(playbooks),
            folder_name="ade",
            ade_targets=["cursor"],
            sync_root_rules=True,
            force_apply=True,
            user=user,
        )

        assert_log_story(
            caplog,
            where="PlaybookExportService.export_playbook_to_local",
            beats={
                "entry": ["ade_targets=cursor", "force_apply=True", "sync_root_rules=True"],
                "exit": ["ade_files=", "inline="],
            },
        )

    def test_playbook_export_ade_log_story_reject(self, ade_playbook, tmp_path, caplog):
        user, pb = ade_playbook
        caplog.set_level(logging.ERROR)

        with pytest.raises(ValueError):
            PlaybookExportService.export_playbook_to_local(
                playbook_id=pb.pk,
                target_directory=str(tmp_path),
                sync_root_rules=True,
                user=user,
            )

        assert_log_story(
            caplog,
            where="PlaybookExportService.export_playbook_to_local",
            beats={"error": ["ade_targets required"]},
            level="ERROR",
        )
