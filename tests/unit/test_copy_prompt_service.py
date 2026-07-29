"""Unit tests for CopyPromptService."""

import pytest
from django.contrib.auth.models import User

from methodology.models import (
    Activity,
    Agent,
    Artifact,
    PipChange,
    Playbook,
    ProcessImprovementProposal,
    Rule,
    Skill,
    Workflow,
)
from methodology.services.copy_prompt_service import CopyPromptService


@pytest.mark.django_db
class TestCopyPromptService:
    """Copy prompt builders per FOB-COPY-PROMPT-SERVICE scenarios."""

    @pytest.fixture
    def playbook(self):
        user = User.objects.create_user(username="mike", password="x")
        return Playbook.objects.create(
            name="React Frontend Development",
            description="## Frontend standards",
            category="development",
            author=user,
            visibility="public",
            status="released",
            version=1.2,
        )

    @pytest.fixture
    def workflow(self, playbook):
        return Workflow.objects.create(
            playbook=playbook,
            name="Component Development",
            description="Build UI components",
            abbreviation="CD",
            order=1,
        )

    def test_activity_prompt_includes_context_and_guidance(self, playbook, workflow):
        activity = Activity.objects.create(
            workflow=workflow,
            name="Setup component structure",
            guidance="## Overview\nScaffold the component folder structure.",
            order=1,
        )
        prompt = CopyPromptService.build_activity_prompt(activity)
        assert "React Frontend Development" in prompt
        assert "Component Development" in prompt
        assert "Setup component structure" in prompt
        assert "## Overview" in prompt
        assert "Scaffold the component folder structure." in prompt
        assert "<" not in prompt

    def test_skill_prompt_includes_metadata_and_content(self, playbook):
        skill = Skill.objects.create(
            playbook=playbook,
            title="React Form Component",
            capability_domain="GUI_FORM",
            technology_stack="React+Redux",
            content="## Patterns\nUse controlled inputs.",
        )
        prompt = CopyPromptService.build_skill_prompt(skill)
        assert "React Frontend Development" in prompt
        assert "GUI_FORM" in prompt
        assert "React+Redux" in prompt
        assert "## Patterns" in prompt
        assert "Use controlled inputs." in prompt

    def test_agent_prompt_includes_name_and_description(self, playbook):
        agent = Agent.objects.create(
            playbook=playbook,
            name="Cautious Developer (drdobbs-v2)",
            description="Prefer small diffs.",
        )
        prompt = CopyPromptService.build_agent_prompt(agent)
        assert "React Frontend Development" in prompt
        assert "Cautious Developer (drdobbs-v2)" in prompt
        assert "Prefer small diffs." in prompt

    def test_rule_prompt_includes_slug_always_apply_and_body(self, playbook):
        rule = Rule.objects.create(
            playbook=playbook,
            title="pytest-first",
            slug="pytest-first",
            always_apply=True,
            content="Write tests before implementation.",
        )
        prompt = CopyPromptService.build_rule_prompt(rule)
        assert "pytest-first" in prompt
        assert "always_apply: true" in prompt
        assert "Write tests before implementation." in prompt

    def test_artifact_prompt_includes_type_required_and_description(self, playbook, workflow):
        activity = Activity.objects.create(
            workflow=workflow,
            name="Producer",
            guidance="x",
            order=1,
        )
        artifact = Artifact.objects.create(
            playbook=playbook,
            produced_by=activity,
            name="Component Design Document",
            description="Spec for the component API.",
            type="Document",
            is_required=True,
        )
        prompt = CopyPromptService.build_artifact_prompt(artifact)
        assert "Document" in prompt
        assert "Required: true" in prompt
        assert "Spec for the component API." in prompt

    def test_pip_prompt_includes_summary_and_changes_without_galdr(self, playbook):
        pip = ProcessImprovementProposal.objects.create(
            playbook=playbook,
            title="Add Accessibility Audit",
            summary="Add WCAG coverage to the playbook.",
        )
        PipChange.objects.create(
            pip=pip,
            change_type=PipChange.CHANGE_ADD,
            entity_type=PipChange.ENTITY_ACTIVITY,
            name="Accessibility Audit",
            order=1,
            galdr_recommendation=PipChange.GALDR_ACCEPT,
            galdr_reasoning="Galdr secret reasoning",
        )
        PipChange.objects.create(
            pip=pip,
            change_type=PipChange.CHANGE_ALTER,
            entity_type=PipChange.ENTITY_ACTIVITY,
            target_name_snapshot="Component Testing",
            order=2,
        )
        prompt = CopyPromptService.build_pip_prompt(pip)
        assert f"PIP-{pip.pk}" in prompt
        assert "Add Accessibility Audit" in prompt
        assert "Add WCAG coverage to the playbook." in prompt
        assert "ADD Activity: Accessibility Audit" in prompt
        assert "ALTER Activity: Component Testing" in prompt
        assert "Galdr secret reasoning" not in prompt

    def test_empty_skill_content_still_produces_usable_prompt(self, playbook):
        skill = Skill.objects.create(
            playbook=playbook,
            title="Empty Skill",
            content="",
        )
        prompt = CopyPromptService.build_skill_prompt(skill)
        assert "Empty Skill" in prompt
        assert "Read the" in prompt
        assert "Apply its guidance" in prompt

    def test_map_activity_prompts_returns_dict_by_pk(self, playbook, workflow):
        a1 = Activity.objects.create(
            workflow=workflow, name="A1", guidance="g", order=1
        )
        a2 = Activity.objects.create(
            workflow=workflow, name="A2", guidance="g", order=2
        )
        mapped = CopyPromptService.map_activity_prompts([a1, a2])
        assert set(mapped.keys()) == {a1.pk, a2.pk}
        assert "A1" in mapped[a1.pk]
