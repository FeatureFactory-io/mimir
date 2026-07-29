"""Server-built AI instruction text for Copy Prompt (Act 17)."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List

from methodology.models import (
    Activity,
    Agent,
    Artifact,
    Phase,
    Playbook,
    ProcessImprovementProposal,
    Rule,
    Skill,
    Workflow,
)

logger = logging.getLogger(__name__)


def _join_instruction_and_body(instruction: str, body: str) -> str:
    """Combine instruction line with optional Markdown body."""
    normalized = (body or "").strip()
    if normalized:
        return f"{instruction}\n\n{normalized}"
    return instruction


def _activity_display_ref(activity: Activity) -> str:
    """Build quoted activity reference for instruction lines."""
    ref = activity.reference_label or activity.reference_name
    if ref:
        return f"'{ref} {activity.name}'"
    return f"'{activity.name}'"


class CopyPromptService:
    """Assemble clipboard-ready prompts for playbook entities."""

    @staticmethod
    def build_activity_prompt(activity: Activity) -> str:
        """Build prompt for an activity including full guidance Markdown."""
        workflow = activity.workflow
        playbook = workflow.playbook
        instruction = (
            f"Read the {_activity_display_ref(activity)} activity from playbook "
            f"'{playbook.name}' (workflow '{workflow.name}'). "
            f"Follow its guidance when assisting me."
        )
        logger.info(
            "CopyPromptService.build_activity_prompt activity=%s playbook=%s",
            activity.pk,
            playbook.pk,
        )
        return _join_instruction_and_body(instruction, activity.guidance or "")

    @staticmethod
    def build_skill_prompt(skill: Skill) -> str:
        """Build prompt for a skill including metadata and content."""
        playbook = skill.playbook
        instruction = (
            f"Read the '{skill.title}' skill from playbook '{playbook.name}'. "
            f"Apply its guidance when assisting me."
        )
        meta_lines: List[str] = []
        if skill.capability_domain:
            meta_lines.append(f"Capability domain: {skill.capability_domain}")
        if skill.technology_stack:
            meta_lines.append(f"Technology stack: {skill.technology_stack}")
        body = "\n".join(meta_lines)
        content = (skill.content or "").strip()
        if content:
            body = f"{body}\n\n{content}" if body else content
        logger.info(
            "CopyPromptService.build_skill_prompt skill=%s playbook=%s",
            skill.pk,
            playbook.pk,
        )
        return _join_instruction_and_body(instruction, body)

    @staticmethod
    def build_agent_prompt(agent: Agent) -> str:
        """Build prompt for an agent."""
        playbook = agent.playbook
        instruction = (
            f"Read the '{agent.name}' agent from playbook '{playbook.name}'. "
            f"Apply its purpose when assisting me."
        )
        logger.info(
            "CopyPromptService.build_agent_prompt agent=%s playbook=%s",
            agent.pk,
            playbook.pk,
        )
        return _join_instruction_and_body(instruction, agent.description or "")

    @staticmethod
    def build_rule_prompt(rule: Rule) -> str:
        """Build prompt for a rule including slug and always_apply."""
        playbook = rule.playbook
        apply_label = "true" if rule.always_apply else "false"
        instruction = (
            f"Read the '{rule.title}' rule from playbook '{playbook.name}'. "
            f"Slug: {rule.slug}. always_apply: {apply_label}."
        )
        logger.info(
            "CopyPromptService.build_rule_prompt rule=%s playbook=%s",
            rule.pk,
            playbook.pk,
        )
        return _join_instruction_and_body(instruction, rule.content or "")

    @staticmethod
    def build_artifact_prompt(artifact: Artifact) -> str:
        """Build prompt for an artifact."""
        playbook = artifact.playbook
        required_label = "true" if artifact.is_required else "false"
        instruction = (
            f"Read the '{artifact.name}' artifact from playbook '{playbook.name}'. "
            f"Type: {artifact.type}. Required: {required_label}."
        )
        logger.info(
            "CopyPromptService.build_artifact_prompt artifact=%s playbook=%s",
            artifact.pk,
            playbook.pk,
        )
        return _join_instruction_and_body(instruction, artifact.description or "")

    @staticmethod
    def build_workflow_prompt(workflow: Workflow) -> str:
        """Build workflow summary with activity names only (no full guidance)."""
        playbook = workflow.playbook
        instruction = (
            f"Read the '{workflow.name}' workflow from playbook '{playbook.name}'. "
            f"Use it to orient planning and execution."
        )
        activities = workflow.activities.order_by("order")
        lines: List[str] = []
        description = (workflow.description or "").strip()
        if description:
            lines.append(description)
        if activities.exists():
            lines.append("Activities (in order):")
            for act in activities:
                lines.append(f"- {act.name}")
        body = "\n".join(lines)
        logger.info(
            "CopyPromptService.build_workflow_prompt workflow=%s playbook=%s",
            workflow.pk,
            playbook.pk,
        )
        return _join_instruction_and_body(instruction, body)

    @staticmethod
    def build_phase_prompt(phase: Phase) -> str:
        """Build phase summary with assigned activity names."""
        playbook = phase.playbook
        instruction = (
            f"Read the '{phase.name}' phase from playbook '{playbook.name}'. "
            f"Use assigned activities for context."
        )
        activities = (
            Activity.objects.filter(phase=phase)
            .select_related("workflow")
            .order_by("workflow__order", "order")
        )
        lines: List[str] = []
        description = (phase.description or "").strip()
        if description:
            lines.append(description)
        if activities.exists():
            lines.append("Assigned activities (in order):")
            for act in activities:
                lines.append(f"- {act.workflow.name} › {act.name}")
        body = "\n".join(lines)
        logger.info(
            "CopyPromptService.build_phase_prompt phase=%s playbook=%s",
            phase.pk,
            playbook.pk,
        )
        return _join_instruction_and_body(instruction, body)

    @staticmethod
    def build_playbook_prompt(playbook: Playbook) -> str:
        """Build playbook overview without embedding every activity body."""
        instruction = (
            f"Read the '{playbook.name}' playbook (v{playbook.version}, "
            f"{playbook.get_status_display()}). Use its structure when assisting me."
        )
        lines: List[str] = []
        description = (playbook.description or "").strip()
        if description:
            lines.append(description)
        workflows = playbook.workflows.order_by("order")
        workflow_count = workflows.count()
        activity_count = Activity.objects.filter(workflow__playbook=playbook).count()
        lines.append(
            f"Structure: {workflow_count} workflow(s), {activity_count} activit"
            f"{'y' if activity_count == 1 else 'ies'}."
        )
        if workflow_count:
            lines.append("Workflows:")
            for wf in workflows:
                count = wf.get_activity_count()
                lines.append(f"- {wf.name} ({count} activities)")
        body = "\n".join(lines)
        logger.info("CopyPromptService.build_playbook_prompt playbook=%s", playbook.pk)
        return _join_instruction_and_body(instruction, body)

    @staticmethod
    def build_pip_prompt(pip: ProcessImprovementProposal) -> str:
        """Build PIP summary and change list without Galdr reasoning."""
        playbook = pip.playbook
        instruction = (
            f"Read PIP-{pip.pk} '{pip.title}' targeting playbook '{playbook.name}'. "
            f"Review proposed changes when assisting me."
        )
        lines: List[str] = []
        summary = (pip.summary or "").strip()
        if summary:
            lines.append(summary)
        changes = pip.changes.order_by("order", "pk")
        if changes.exists():
            lines.append("Changes:")
            for change in changes:
                target = (
                    change.name
                    or change.target_name_snapshot
                    or (f"id={change.target_id}" if change.target_id else "—")
                )
                lines.append(f"- {change.change_type} {change.entity_type}: {target}")
        body = "\n".join(lines)
        logger.info("CopyPromptService.build_pip_prompt pip=%s", pip.pk)
        return _join_instruction_and_body(instruction, body)

    @staticmethod
    def map_activity_prompts(activities: Iterable[Activity]) -> Dict[int, str]:
        """Build copy prompts keyed by activity pk for list templates."""
        return {act.pk: CopyPromptService.build_activity_prompt(act) for act in activities}

    @staticmethod
    def map_skill_prompts(skills: Iterable[Skill]) -> Dict[int, str]:
        return {s.pk: CopyPromptService.build_skill_prompt(s) for s in skills}

    @staticmethod
    def map_agent_prompts(agents: Iterable[Agent]) -> Dict[int, str]:
        return {a.pk: CopyPromptService.build_agent_prompt(a) for a in agents}

    @staticmethod
    def map_rule_prompts(rules: Iterable[Rule]) -> Dict[int, str]:
        return {r.pk: CopyPromptService.build_rule_prompt(r) for r in rules}

    @staticmethod
    def map_artifact_prompts(artifacts: Iterable[Artifact]) -> Dict[int, str]:
        return {a.pk: CopyPromptService.build_artifact_prompt(a) for a in artifacts}

    @staticmethod
    def map_workflow_prompts(workflows: Iterable[Workflow]) -> Dict[int, str]:
        return {w.pk: CopyPromptService.build_workflow_prompt(w) for w in workflows}

    @staticmethod
    def map_phase_prompts(phases: Iterable[Phase]) -> Dict[int, str]:
        return {p.pk: CopyPromptService.build_phase_prompt(p) for p in phases}

    @staticmethod
    def map_pip_prompts(pips: Iterable[ProcessImprovementProposal]) -> Dict[int, str]:
        return {p.pk: CopyPromptService.build_pip_prompt(p) for p in pips}

    @staticmethod
    def attach_copy_prompts(instances: Iterable, builder) -> None:
        """Set ``copy_prompt_text`` on each instance for list templates."""
        for item in instances:
            item.copy_prompt_text = builder(item)

    @staticmethod
    def attach_activity_copy_prompts_grouped(activities_by_phase: dict) -> None:
        """Attach copy prompts for workflow activity lists grouped by phase."""
        for activities in activities_by_phase.values():
            CopyPromptService.attach_copy_prompts(
                activities, CopyPromptService.build_activity_prompt
            )
