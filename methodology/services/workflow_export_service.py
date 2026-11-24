"""Workflow Export Service - Export workflows to markdown files."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import DatabaseError

from mcp_integration.facade.export_paths import (
    confined_export_path,
    validate_export_destinations,
)
from methodology.models import Workflow
from methodology.services.karma_service import KarmaService
from methodology.services.workflow_service import WorkflowService

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser, User

logger = logging.getLogger(__name__)
_EXPORT_LOG = "WorkflowExportService.export_workflow_to_markdown"


class WorkflowExportService:
    """Service for exporting workflows to markdown files."""

    @staticmethod
    def export_workflow_to_markdown(
        workflow_id: int,
        target_directory: str,
        folder_name: str | None = None,
        user: User | AnonymousUser | None = None,
        skip_rules: bool = False,
    ) -> dict:
        """Export a workflow and its linked rules as Markdown files.

        :param workflow_id: Existing workflow ID. Example: 6202.
        :param target_directory: Approved local base. Example: ".windsurf/workflows".
        :param folder_name: Relative output folder. Example: "Frontend".
        :param user: Existing read actor, or None for non-awarding export.
        :param skip_rules: Exclude linked rule files. Example: False.
        :return: Existing export summary. Example: {"status": "exported", ...}.
        :raises ObjectDoesNotExist: If the workflow does not exist.
        :raises PermissionError: If access is denied.
        :raises ValueError: If a requested path is invalid.
        :raises OSError: If a filesystem operation fails.
        """
        operation = uuid4()
        trace = (
            f"operation_uuid={operation} entity_type=workflow entity_id={workflow_id}"
            f" actor_id={getattr(user, 'pk', None)}"
        )
        logger.info("%s | entry | %s", _EXPORT_LOG, trace)
        service = WorkflowExportService
        try:
            workflow = service._load_workflow(workflow_id, user)
            bundle = service._workflow_bundle(
                workflow, folder_name, skip_rules=skip_rules
            )
        except (ObjectDoesNotExist, PermissionError):
            logger.info(
                "%s | error | %s reason=unavailable completed_file_count=0 receipt_sent=false",
                _EXPORT_LOG,
                trace,
            )
            raise
        target = Path(target_directory).absolute()
        result = service._write_workflow_export(bundle, target, trace)
        service._record_completed_export(
            user=user, workflow_id=workflow.pk, event_identity=operation
        )
        return result

    @staticmethod
    def _load_workflow(workflow_id: int, user: User | AnonymousUser | None) -> Workflow:
        """Load the existing workflow under its normal read permission."""
        try:
            if user is not None:
                return WorkflowService.get_workflow_for_user(
                    workflow_id, user, write=False, prefetch_activities=False
                )
            return Workflow.objects.select_related("playbook").get(pk=workflow_id)
        except ObjectDoesNotExist as exc:
            raise ObjectDoesNotExist(
                f"Workflow with ID {workflow_id} does not exist"
            ) from exc

    @staticmethod
    def _write_workflow_export(bundle: dict, target: Path, trace: str) -> dict:
        """Validate all workflow/rule files, write them, and return the legacy summary."""
        completed = 0
        try:
            destinations = WorkflowExportService._validate_export_destinations(
                bundle, target
            )
            logger.info(
                "%s | validation | %s destination_count=%s",
                _EXPORT_LOG,
                trace,
                len(destinations),
            )
            for root, relative, content, path in destinations:
                if confined_export_path(root, relative) != path:
                    raise ValueError("Export destination changed after validation.")
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                except OSError as exc:
                    raise PermissionError(
                        f"Cannot create directory {path.parent}: {exc}"
                    ) from exc
                if confined_export_path(root, relative) != path:
                    raise ValueError("Export destination changed after validation.")
                path.write_text(content, encoding="utf-8")
                completed += 1
        except (ValueError, OSError) as exc:
            reason = (
                "invalid_destination"
                if isinstance(exc, ValueError)
                else "filesystem_failure"
            )
            logger.info(
                "%s | error | %s reason=%s completed_file_count=%s receipt_sent=false",
                _EXPORT_LOG,
                trace,
                reason,
                completed,
            )
            raise
        logger.info(
            "%s | processing | %s file_count=%s files_written=true",
            _EXPORT_LOG,
            trace,
            completed,
        )
        return WorkflowExportService._workflow_export_result(bundle, target)

    @staticmethod
    def _workflow_export_result(bundle: dict, target: Path) -> dict:
        """Preserve filenames, rule paths and the existing export response shape."""
        export_path = target / bundle["folder_name"]
        rule_files = [f"rules/{entry['filename']}" for entry in bundle["rule_files"]]
        rules_dir = target.resolve().parent / "rules" if rule_files else None
        rule_export_paths = (
            [str(rules_dir / Path(name).name) for name in rule_files]
            if rules_dir
            else []
        )
        return {
            "status": "exported",
            "workflow_id": bundle["workflow_id"],
            "workflow_name": bundle["workflow_name"],
            "export_path": str(export_path),
            "rules_export_path": str(rules_dir) if rules_dir else "",
            "files_created": [entry["filename"] for entry in bundle["workflow_files"]]
            + rule_files,
            "rule_files_created": rule_files,
            "rule_export_paths": rule_export_paths,
            "message": (
                f"Workflow exported to {export_path}."
                + (
                    f" {len(rule_export_paths)} linked rules were written to "
                    f'{rules_dir} ({", ".join(rule_files)}).'
                    if rule_files
                    else " No linked rules."
                )
                + " Edit files locally and use import_workflow_from_local to apply changes."
            ),
        }

    @staticmethod
    def generate_workflow_files(
        workflow_id: int,
        folder_name: str | None = None,
    ) -> dict:
        """
        Generate workflow export file contents without filesystem I/O.

        :param workflow_id: Workflow ID. Example: 42
        :param folder_name: Folder name. Example: "FFE" (defaults to workflow slug)
        :return: Dict with workflow_files and rule_files content lists
        :raises ObjectDoesNotExist: If workflow does not exist
        """
        workflow = WorkflowExportService._load_workflow(workflow_id, None)
        return WorkflowExportService._workflow_bundle(workflow, folder_name)

    @staticmethod
    def _workflow_bundle(
        workflow: Workflow, folder_name: str | None, *, skip_rules: bool = False
    ) -> dict:
        """Generate one consistent workflow plan for the bundle and filesystem paths."""
        activities = list(
            workflow.activities.select_related("agent")
            .prefetch_related("skills", "rules")
            .prefetch_related(
                "output_artifacts",
                "input_artifacts__artifact",
                "rules",
            )
            .order_by("order")
        )
        logger.info(f"Found {len(activities)} activities in workflow '{workflow.name}'")

        if not folder_name:
            folder_name = WorkflowExportService._slugify(workflow.name)

        workflow_files = []
        workflow_md = WorkflowExportService._generate_workflow_metadata_md(
            workflow, len(activities)
        )
        workflow_files.append({"filename": "_workflow.md", "content": workflow_md})

        slug_prefix = folder_name
        for activity in activities:
            filename, content = WorkflowExportService._generate_activity_md(
                activity, activity.order, slug_prefix
            )
            workflow_files.append({"filename": filename, "content": content})

        rule_files = (
            []
            if skip_rules
            else WorkflowExportService._generate_rule_files_for_workflow(activities)
        )
        return {
            "workflow_id": workflow.pk,
            "workflow_name": workflow.name,
            "folder_name": folder_name,
            "workflow_files": workflow_files,
            "rule_files": rule_files,
        }

    @staticmethod
    def _generate_workflow_metadata_md(workflow, activity_count: int) -> str:
        """Generate _workflow.md content with metadata."""
        playbook = workflow.playbook
        export_date = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        has_phases = any(a.phase_id for a in workflow.activities.all())
        phase_info = "Uses phases" if has_phases else "No phase organization"

        md = f"""# {workflow.name}

**Playbook**: {playbook.name} v{playbook.version} ({playbook.status.capitalize()})
**Workflow ID**: {workflow.id}
**Description**: {workflow.description or 'No description provided'}
**Phase Organization**: {phase_info}
**Total Activities**: {activity_count}
**Export Date**: {export_date}

## Activities

See individual activity files in this directory.

## Editing Instructions

- **Add activity**: Create new file with pattern PREFIX-XX-Name.md
- **Remove activity**: Delete the .md file
- **Reorder**: Rename files to change order numbers
- **Edit content**: Modify description, guidance, dependencies
- **Change phase**: Update the Phase field

After editing, use import_workflow_from_local MCP tool to import changes.
"""
        return md

    @staticmethod
    def _generate_activity_md(activity, order: int, slug_prefix: str) -> tuple[str, str]:
        """
        Generate activity markdown file with agent, skill, and artifacts.
        
        :param activity: Activity instance with prefetched agent, skill, artifacts
        :param order: Activity order number
        :param slug_prefix: Prefix for filename
        :return: Tuple of (filename, content)
        """
        slug = WorkflowExportService._slugify(activity.name)
        filename = f"{slug_prefix}-{order:02d}-{slug}.md"
        
        dependencies = []
        if activity.predecessor:
            dependencies.append(f"Predecessor: Activity {activity.predecessor.id} ({activity.predecessor.name})")
        if activity.successor:
            dependencies.append(f"Successor: Activity {activity.successor.id} ({activity.successor.name})")
        
        dependencies_text = "\n".join(dependencies) if dependencies else "None"
        phase_text = activity.phase.name if activity.phase else "None"
        
        # Build agent section (Issue #72)
        if activity.agent:
            agent_text = f"""**Name**: {activity.agent.name}
**Description**: {activity.agent.description if activity.agent.description else 'No description'}"""
        else:
            agent_text = "None"
        
        # Build skill section (Issue #72)
        linked_skills = list(activity.skills.all())
        if linked_skills:
            skill_lines = []
            for skill in linked_skills:
                skill_lines.append(f"**Title**: {skill.title}")
                if skill.capability_domain:
                    skill_lines.append(f"**Capability Domain**: {skill.capability_domain}")
                if skill.technology_stack:
                    skill_lines.append(f"**Technology Stack**: {skill.technology_stack}")
                skill_lines.append("")
            skill_text = "\n".join(skill_lines).strip()
        else:
            skill_text = "None"

        rule_links = list(activity.rules.all())
        if rule_links:
            rules_lines = [f"- **{r.title}** (`{r.slug}`)" for r in sorted(rule_links, key=lambda x: x.slug)]
            rules_text = "\n".join(rules_lines)
        else:
            rules_text = "None"

        # Build artifacts produced section (Issue #72)
        output_artifacts = list(activity.output_artifacts.all())
        if output_artifacts:
            artifacts_produced_lines = []
            for artifact in output_artifacts:
                req_text = "Required" if artifact.is_required else "Optional"
                artifacts_produced_lines.append(
                    f"- **{artifact.name}** ({artifact.type}) - {req_text}"
                )
            artifacts_produced_text = "\n".join(artifacts_produced_lines)
        else:
            artifacts_produced_text = "None"
        
        # Build artifacts consumed section (Issue #72)
        input_artifact_inputs = list(activity.input_artifacts.all())
        if input_artifact_inputs:
            artifacts_consumed_lines = []
            for ai in input_artifact_inputs:
                req_text = "Required" if ai.is_required else "Optional"
                artifacts_consumed_lines.append(
                    f"- **{ai.artifact.name}** ({ai.artifact.type}) - {req_text}"
                )
            artifacts_consumed_text = "\n".join(artifacts_consumed_lines)
        else:
            artifacts_consumed_text = "None"
        
        content = f"""# Activity: {activity.name}

**Activity ID**: {activity.id}
**Order**: {order}
**Phase**: {phase_text}
**Dependencies**: {dependencies_text}

## Description

{activity.name}

## Guidance

{activity.guidance if activity.guidance else 'No guidance provided.'}

## Agent

{agent_text}

## Skill

{skill_text}

## Rules

{rules_text}

## Artifacts Produced

{artifacts_produced_text}

## Artifacts Consumed

{artifacts_consumed_text}

## Notes

No additional notes.
"""
        
        return filename, content

    @staticmethod
    def _generate_rule_files_for_workflow(activities) -> list:
        """
        Build rule file contents for activities without filesystem I/O.

        :returns: List of {"filename": str, "content": str} dicts
        """
        seen = {}
        for activity in activities:
            for rule in activity.rules.all():
                seen[rule.id] = rule
        if not seen:
            logger.info(
                "No rules linked to workflow activities; skipping rule generation"
            )
            return []

        rule_files = []
        for rule in sorted(seen.values(), key=lambda r: r.slug):
            fname = f"{rule.slug}.mdc"
            body = WorkflowExportService._format_rule_mdc(rule)
            rule_files.append({"filename": fname, "content": body})
            logger.info("Generated rule file content for %s", fname)

        return rule_files

    @staticmethod
    def _format_rule_mdc(rule) -> str:
        """Cursor-style .mdc body with YAML front matter."""
        aa = "true" if rule.always_apply else "false"
        fm = f"---\nalwaysApply: {aa}\n---\n\n"
        content = rule.content.strip() if rule.content else ""
        return fm + content + ("\n" if content and not content.endswith("\n") else "")

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to slug format."""
        slug = text.replace(" ", "_")
        slug = re.sub(r"[^\w\-]", "", slug)
        slug = re.sub(r"_+", "_", slug)
        slug = slug.strip("_")
        return slug

    @staticmethod
    def _validate_export_destinations(
        bundle: dict, target: Path
    ) -> tuple[tuple[Path, str, str, Path], ...]:
        """Preflight this workflow bundle and every requested linked-rule destination.

        :param bundle: Existing authorized export content. Example: a workflow bundle.
        :param target: Explicit base. Example: Path("/tmp/workflows").
        :return: Ordered immutable file writes and their validated absolute paths.
        :raises ValueError: If any destination escapes its approved root.
        """
        folder = bundle["folder_name"]
        export_root = confined_export_path(target, folder)
        writes = []
        for entry in bundle["workflow_files"]:
            name = entry["filename"]
            confined_export_path(export_root, name)
            writes.append((target, str(Path(folder) / name), entry["content"]))
        if bundle["rule_files"]:
            parent = target.resolve().parent
            rules_root = parent / "rules"
            if confined_export_path(parent, "rules") != rules_root:
                raise ValueError(
                    "Linked rules directory must remain a sibling of workflows."
                )
            writes.extend(
                (rules_root, entry["filename"], entry["content"])
                for entry in bundle["rule_files"]
            )
        approved = validate_export_destinations(
            [(root, relative) for root, relative, _ in writes]
        )
        return tuple(
            (*write, path) for write, path in zip(writes, approved, strict=True)
        )

    @staticmethod
    def _record_completed_export(
        *, user: User | AnonymousUser | None, workflow_id: int, event_identity: UUID
    ) -> None:
        """Delegate a successful authenticated workflow export to S36.

        :param user: Existing service actor. Example: Maria, or None.
        :param workflow_id: Exported workflow ID. Example: 6202.
        :param event_identity: Single invocation UUID. Example: UUID(int=42).
        :return: None after shared domain decision.
        :raises PermissionError: If domain revalidation rejects the actor.
        :raises ValueError: If event identity or entity is invalid.
        """
        trace = (
            f"operation_uuid={event_identity} entity_type=workflow entity_id={workflow_id}"
            f" actor_id={getattr(user, 'pk', None)} channel=export"
        )
        try:
            outcomes = (
                KarmaService.award_successful_consumption(
                    user, "workflow", workflow_id, event_identity, channel="export"
                )
                if user is not None
                else ()
            )
        except (
            ObjectDoesNotExist,
            PermissionError,
            ValueError,
            ValidationError,
            DatabaseError,
        ):
            logger.info(
                "%s | error | %s files_written=true receipt_status=failed",
                _EXPORT_LOG,
                trace,
            )
            raise
        created = sum(row.created for row in outcomes)
        status = "awarded" if created else ("idempotent" if outcomes else "ineligible")
        logger.info(
            "%s | exit | %s outcome=%s created_count=%s",
            _EXPORT_LOG,
            trace,
            status,
            created,
        )
