"""Unit tests for rule_export_formatters."""

import pytest

from methodology.models import Playbook, Rule
from methodology.services.rule_export_formatters import (
    ade_root_relative_path,
    build_ade_rule_files,
    build_inline_rules_markdown,
    format_rule_for_ade,
    normalize_ade_targets,
    validate_ade_export_params,
)


@pytest.mark.django_db
class TestRuleExportFormatters:
    @pytest.fixture
    def rule(self, django_user_model):
        user = django_user_model.objects.create_user(
            username="fmt_user", email="f@test.com", password="pass"
        )
        pb = Playbook.objects.create(
            name="Fmt PB",
            description="d",
            category="development",
            author=user,
            status="released",
            version="1.0",
        )
        return Rule.objects.create(
            playbook=pb,
            title="Test First",
            slug="do-test-first",
            content="Write tests before code.",
            always_apply=False,
        )

    def test_format_rule_for_ade_cursor_force_apply(self, rule):
        body = format_rule_for_ade(rule, "cursor", force_apply=True)
        assert "alwaysApply: true" in body
        assert "Write tests before code." in body

    def test_format_rule_for_ade_cursor_stored_false(self, rule):
        body = format_rule_for_ade(rule, "cursor", force_apply=False)
        assert "alwaysApply: false" in body

    def test_format_rule_for_ade_devin_extension(self, rule):
        body = format_rule_for_ade(rule, "devin", force_apply=True)
        assert "alwaysApply" not in body
        assert "# Test First" in body
        assert "Write tests before code." in body

    def test_ade_root_relative_path(self):
        assert ade_root_relative_path("cursor", "do-test-first") == (
            ".cursor/rules/do-test-first.mdc"
        )
        assert ade_root_relative_path("devin", "do-test-first") == (
            ".windsurf/rules/do-test-first.md"
        )

    def test_build_inline_rules_markdown_force_apply(self, rule):
        md = build_inline_rules_markdown([rule], force_apply=True)
        assert md.startswith("## Playbook Rules")
        assert "do-test-first" in md
        assert "Write tests before code." in md

    def test_build_inline_rules_markdown_skips_false_without_force(self, rule):
        assert build_inline_rules_markdown([rule], force_apply=False) == ""

    def test_build_ade_rule_files_multi_target(self, rule):
        files = build_ade_rule_files(
            [rule], ["cursor", "devin"], force_apply=True
        )
        paths = {f["path"] for f in files}
        assert ".cursor/rules/do-test-first.mdc" in paths
        assert ".windsurf/rules/do-test-first.md" in paths

    def test_validate_ade_export_params_requires_targets_when_sync(self):
        with pytest.raises(ValueError, match="ade_targets required"):
            validate_ade_export_params(
                ade_targets=[], sync_root_rules=True, force_apply=False
            )

    def test_validate_ade_export_params_requires_targets_when_force(self):
        with pytest.raises(ValueError, match="ade_targets required"):
            validate_ade_export_params(
                ade_targets=None, sync_root_rules=False, force_apply=True
            )

    def test_normalize_ade_targets_singular_alias(self):
        assert normalize_ade_targets(None, ade_target="cursor") == ["cursor"]

    def test_normalize_ade_targets_invalid(self):
        with pytest.raises(ValueError, match="Invalid ade_target"):
            normalize_ade_targets(["not-an-ade"])
