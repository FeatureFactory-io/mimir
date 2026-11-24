"""Export full playbooks to local IDE workspace trees."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
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
from methodology.models import Agent, Artifact, Playbook, Rule, Skill, Workflow
from methodology.services.karma_service import KarmaService
from methodology.services.playbook_service import PlaybookService
from methodology.services.rule_export_formatters import (
    ade_root_relative_path,
    build_ade_rule_files,
    build_inline_rules_markdown,
    normalize_ade_targets,
    validate_ade_export_params,
)
from methodology.services.workflow_export_service import WorkflowExportService

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser, User

logger = logging.getLogger(__name__)
_EXPORT_LOG = "PlaybookExportService.export_playbook_to_local"


class PlaybookExportService:
    """Orchestrate playbook-level markdown export for AI IDE workspaces."""

    @staticmethod
    def export_playbook_to_local(
        playbook_id: int,
        target_directory: str,
        folder_name: str | None = None,
        additional_targets: list[str] | None = None,
        sync_root_rules: bool = False,
        ade_targets: list[str] | None = None,
        force_apply: bool = False,
        ade_target: str | None = None,
        user: User | AnonymousUser | None = None,
    ) -> dict:
        """Export a playbook tree and any requested IDE rule copies.

        :param playbook_id: Existing playbook ID. Example: 6201.
        :param target_directory: Approved local base. Example: ".cursor/playbooks".
        :param folder_name: Relative output folder. Example: "Cedar".
        :param additional_targets: Extra roots for copies of the canonical tree.
        :param sync_root_rules: Also write apply-on rules to the requested ADE paths.
        :param ade_targets: ADE keys. Example: ["cursor", "devin"].
        :param force_apply: Force apply-on for ADE copies while retaining canonical flags.
        :param ade_target: Singular alias for an ADE target. Example: "cursor".
        :param user: Existing read actor, or None for non-awarding export.
        :return: Existing summary with export paths, counts and ADE content.
        :raises PermissionError: If the actor cannot read the playbook.
        :raises ValueError: If export options or destinations are invalid.
        :raises OSError: If a filesystem operation fails.
        """
        operation = uuid4()
        trace = (
            f"operation_uuid={operation} entity_type=playbook entity_id={playbook_id}"
            f" actor_id={getattr(user, 'pk', None)}"
        )
        service = PlaybookExportService
        bundle = service._prepare_export_bundle(
            playbook_id,
            folder_name,
            sync_root_rules,
            ade_targets,
            force_apply,
            ade_target,
            user,
            trace,
        )
        targets = tuple(
            Path(path).absolute()
            for path in [target_directory, *(additional_targets or [])]
        )
        result = service._write_bundle_to_disk(bundle, targets, sync_root_rules, trace)
        service._record_completed_export(
            user=user,
            playbook_id=bundle["playbook_id"],
            event_identity=operation,
            ade_files=len(result["ade_rule_files"]),
            inline=bool(result["inline_rules_markdown"]),
        )
        return result

    @staticmethod
    def _prepare_export_bundle(
        playbook_id: int,
        folder_name: str | None,
        sync_root_rules: bool,
        ade_targets: list[str] | None,
        force_apply: bool,
        ade_target: str | None,
        user: User | AnonymousUser | None,
        trace: str,
    ) -> dict:
        """Validate ADE options and generate content through the existing read boundary."""
        try:
            normalized = validate_ade_export_params(
                ade_targets=ade_targets,
                sync_root_rules=sync_root_rules,
                force_apply=force_apply,
                ade_target=ade_target,
            )
        except ValueError:
            reason = (
                "ade_targets required"
                if not (ade_target or ade_targets)
                else "invalid ADE options"
            )
            logger.error(
                "%s | error | %s reason=%s completed_file_count=0 receipt_sent=false",
                _EXPORT_LOG,
                trace,
                reason,
            )
            raise
        logger.info(
            "%s | entry | %s sync_root_rules=%s ade_targets=%s force_apply=%s",
            _EXPORT_LOG,
            trace,
            sync_root_rules,
            ",".join(normalized),
            force_apply,
        )
        try:
            return PlaybookExportService.generate_playbook_export_bundle(
                playbook_id=playbook_id,
                folder_name=folder_name,
                ade_targets=normalized,
                force_apply=force_apply,
                user=user,
            )
        except ObjectDoesNotExist, PermissionError:
            logger.info(
                "%s | error | %s reason=unavailable completed_file_count=0 receipt_sent=false",
                _EXPORT_LOG,
                trace,
            )
            raise

    @staticmethod
    def _playbook_export_result(
        bundle: dict, targets: tuple[Path, ...], files: list[str]
    ) -> dict:
        """Return the existing canonical/mirror summary without counting ADE copies twice."""
        return {
            "status": "exported",
            "playbook_id": bundle["playbook_id"],
            "playbook_name": bundle["playbook_name"],
            "export_paths": [str(target / bundle["folder_name"]) for target in targets],
            "workflows": bundle["counts"]["workflows"],
            "activities": bundle["counts"]["activities"],
            "rules": bundle["counts"]["rules"],
            "skills": bundle["counts"]["skills"],
            "agents": bundle["counts"]["agents"],
            "artifacts": bundle["counts"]["artifacts"],
            "files_created": files,
            "ade_rule_files": bundle.get("ade_rule_files") or [],
            "inline_rules_markdown": bundle.get("inline_rules_markdown") or "",
            "message": "Playbook exported successfully.",
        }

    @staticmethod
    def generate_playbook_export_bundle(
        playbook_id: int,
        folder_name: str | None = None,
        ade_targets: list[str] | None = None,
        force_apply: bool = False,
        ade_target: str | None = None,
        sync_root_rules: bool = False,
        user=None,
    ) -> dict:
        """Build export payload without filesystem writes (for API / facade)."""
        if sync_root_rules or force_apply:
            normalized_targets = validate_ade_export_params(
                ade_targets=ade_targets,
                sync_root_rules=sync_root_rules,
                force_apply=force_apply,
                ade_target=ade_target,
            )
        else:
            normalized_targets = normalize_ade_targets(
                ade_targets, ade_target=ade_target
            )
        playbook = PlaybookExportService._load_playbook(playbook_id, user)
        if not folder_name:
            folder_name = WorkflowExportService._slugify(playbook.name)

        workflows = list(
            Workflow.objects.filter(playbook=playbook).order_by("order", "name")
        )
        workflow_bundles = []
        activity_count = 0
        for wf in workflows:
            wf_bundle = WorkflowExportService.generate_workflow_files(
                workflow_id=wf.pk,
                folder_name=WorkflowExportService._slugify(wf.name),
            )
            wf_files = wf_bundle["workflow_files"]
            activity_count += max(len(wf_files) - 1, 0)
            workflow_bundles.append(
                {
                    "workflow_id": wf.pk,
                    "folder_name": wf_bundle["folder_name"],
                    "workflow_files": wf_files,
                }
            )

        rules = list(Rule.objects.filter(playbook=playbook).order_by("slug"))
        skills = list(Skill.objects.filter(playbook=playbook).order_by("title"))
        agents = list(Agent.objects.filter(playbook=playbook).order_by("name"))
        artifacts = list(
            Artifact.objects.filter(playbook=playbook)
            .select_related("produced_by")
            .order_by("name")
        )

        playbook_md = PlaybookExportService._generate_playbook_md(
            playbook, workflows, activity_count
        )
        rule_files = [
            {
                "filename": f"{rule.slug}.mdc",
                "content": WorkflowExportService._format_rule_mdc(rule),
            }
            for rule in rules
        ]
        agent_files = [
            {
                "filename": f"{PlaybookExportService._slugify(agent.name)}.md",
                "content": PlaybookExportService._format_agent_md(agent),
            }
            for agent in agents
        ]
        skill_files = [
            {
                "filename": f"{PlaybookExportService._slugify(skill.title)}.md",
                "content": PlaybookExportService._format_skill_md(skill),
            }
            for skill in skills
        ]
        artifact_files = [
            {
                "filename": f"{PlaybookExportService._slugify(artifact.name)}.md",
                "content": PlaybookExportService._format_artifact_md(artifact),
            }
            for artifact in artifacts
        ]

        ade_rule_files = build_ade_rule_files(
            rules, normalized_targets, force_apply=force_apply
        )
        for entry in ade_rule_files:
            logger.info(
                "PlaybookExportService._format_ade_rule_files | processing | "
                "slug=%s ade_targets=%s",
                entry["slug"],
                entry["ade_target"],
            )

        inline_rules_markdown = ""
        if any(t in normalized_targets for t in ("claude", "copilot")):
            inline_rules_markdown = build_inline_rules_markdown(
                rules, force_apply=force_apply
            )
            logger.info(
                "PlaybookExportService._build_inline_rules_markdown | processing | "
                "rule_count=%s",
                len(rules),
            )

        return {
            "playbook_id": playbook.pk,
            "playbook_name": playbook.name,
            "folder_name": folder_name,
            "playbook_md": {"filename": "playbook.md", "content": playbook_md},
            "rule_files": rule_files,
            "agent_files": agent_files,
            "skill_files": skill_files,
            "artifact_files": artifact_files,
            "workflows": workflow_bundles,
            "ade_rule_files": ade_rule_files,
            "inline_rules_markdown": inline_rules_markdown,
            "counts": {
                "workflows": len(workflows),
                "activities": activity_count,
                "rules": len(rules),
                "skills": len(skills),
                "agents": len(agents),
                "artifacts": len(artifacts),
            },
        }

    @staticmethod
    def _load_playbook(playbook_id: int, user) -> Playbook:
        try:
            if user is not None:
                return PlaybookService.get_playbook(playbook_id, user)
            return Playbook.objects.get(pk=playbook_id)
        except Playbook.DoesNotExist as exc:
            raise ObjectDoesNotExist(
                f"Playbook with ID {playbook_id} does not exist"
            ) from exc
        except PermissionError:
            raise PermissionError(f"Cannot read playbook {playbook_id}") from None

    @staticmethod
    def _write_bundle_to_disk(
        bundle: dict, targets: tuple[Path, ...], sync_root_rules: bool, trace: str
    ) -> dict:
        """Write the planned files after preflight and report their legacy result."""
        completed = 0
        files: list[str] = []
        try:
            destinations = PlaybookExportService._validate_export_destinations(
                bundle=bundle,
                targets=targets,
                sync_root_rules=sync_root_rules,
            )
            logger.info(
                "%s | validation | %s destination_count=%s",
                _EXPORT_LOG,
                trace,
                len(destinations),
            )
            for root, relative, content, summary_name, path in destinations:
                if confined_export_path(root, relative) != path:
                    raise ValueError("Export destination changed after validation.")
                path.parent.mkdir(parents=True, exist_ok=True)
                if confined_export_path(root, relative) != path:
                    raise ValueError("Export destination changed after validation.")
                path.write_text(content, encoding="utf-8")
                completed += 1
                if summary_name is not None:
                    files.append(summary_name)
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
        return PlaybookExportService._playbook_export_result(bundle, targets, files)

    @staticmethod
    def _bundle_files(bundle: dict) -> Iterator[tuple[str, dict[str, str]]]:
        """Enumerate the canonical bundle in its established write order."""
        yield "", bundle["playbook_md"]
        for folder, key in (
            ("rules", "rule_files"),
            ("agents", "agent_files"),
            ("skills", "skill_files"),
            ("artifacts", "artifact_files"),
        ):
            for entry in bundle[key]:
                yield folder, entry
        for workflow in bundle["workflows"]:
            for entry in workflow["workflow_files"]:
                yield workflow["folder_name"], entry

    @staticmethod
    def _resolve_dev_root(target_directory: Path) -> Path:
        """Project dev root from a ``.cursor/playbooks`` (or similar) export target."""
        resolved = target_directory.resolve()
        if resolved.name == "playbooks" and resolved.parent.name == ".cursor":
            return resolved.parent.parent
        return resolved.parent

    @staticmethod
    def _generate_playbook_md(playbook, workflows, activity_count: int) -> str:
        export_date = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        wf_lines = (
            "\n".join(f"- **{wf.name}** (order {wf.order})" for wf in workflows)
            or "- _(no workflows)_"
        )
        return f"""# {playbook.name}

**Playbook ID**: {playbook.id}
**Version**: {playbook.version} ({playbook.status})
**Category**: {playbook.category}
**Visibility**: {playbook.visibility}
**Export Date**: {export_date}
**Total Workflows**: {len(workflows)}
**Total Activities**: {activity_count}

## Workflows

{wf_lines}

## Directory Layout

- `rules/` — all playbook rules
- `agents/` — agent definitions
- `skills/` — skill library
- `artifacts/` — artifact catalog
- `{{workflow}}/` — per-workflow activity markdown (import via MCP)
"""

    @staticmethod
    def _format_agent_md(agent: Agent) -> str:
        body = agent.description.strip() if agent.description else "No description."
        return f"# {agent.name}\n\n{body}\n"

    @staticmethod
    def _format_skill_md(skill: Skill) -> str:
        meta = (
            f"**Capability**: {skill.capability_domain or '—'}  \n"
            f"**Stack**: {skill.technology_stack or '—'}\n\n"
        )
        content = skill.content.strip() if skill.content else "No content."
        return f"# {skill.title}\n\n{meta}{content}\n"

    @staticmethod
    def _format_artifact_md(artifact: Artifact) -> str:
        producer = artifact.produced_by.name if artifact.produced_by_id else "—"
        required = "Yes" if artifact.is_required else "No"
        desc = artifact.description.strip() if artifact.description else ""
        return (
            f"# {artifact.name}\n\n"
            f"**Type**: {artifact.type}  \n"
            f"**Required**: {required}  \n"
            f"**Produced by**: {producer}\n\n"
            f"{desc}\n"
        )

    @staticmethod
    def _slugify(text: str) -> str:
        slug = re.sub(r"[^\w\-]", "", text.replace(" ", "_"))
        slug = re.sub(r"_+", "_", slug).strip("_")
        return slug or "item"

    @staticmethod
    def _validate_export_destinations(
        *, bundle: dict, targets: tuple[Path, ...], sync_root_rules: bool
    ) -> tuple[tuple[Path, str, str, str | None, Path], ...]:
        """Preflight canonical, mirror and ADE paths for a legacy export.

        :param bundle: Generated playbook bundle with paths and contents.
        :param targets: Canonical target followed by explicitly approved mirror roots.
        :param sync_root_rules: Include requested ADE copies. Example: True.
        :return: Ordered immutable writes, summary names and validated absolute paths.
        :raises ValueError: If any requested destination escapes its root.
        """
        folder = bundle["folder_name"]
        files = tuple(PlaybookExportService._bundle_files(bundle))
        writes: list[tuple[Path, str, str, str | None]] = []
        for target in targets:
            export_root = confined_export_path(target, folder)
            for directory, entry in files:
                file_root = (
                    confined_export_path(export_root, directory)
                    if directory
                    else export_root
                )
                confined_export_path(file_root, entry["filename"])
                name = (
                    f"{directory}/{entry['filename']}"
                    if directory
                    else entry["filename"]
                )
                writes.append(
                    (target, str(Path(folder) / name), entry["content"], name)
                )
        if sync_root_rules and bundle["ade_rule_files"]:
            dev_root = PlaybookExportService._resolve_dev_root(targets[0])
            writes.extend(
                PlaybookExportService._ade_rule_writes(
                    dev_root, bundle["ade_rule_files"]
                )
            )
        approved = validate_export_destinations(
            [(root, relative) for root, relative, _, _ in writes]
        )
        return tuple(
            (*write, path) for write, path in zip(writes, approved, strict=True)
        )

    @staticmethod
    def _ade_rule_writes(
        dev_root: Path, entries: list[dict[str, str]]
    ) -> Iterator[tuple[Path, str, str, None]]:
        """Plan ADE writes beneath each IDE's own approved rules directory.

        :param dev_root: Resolved workspace root. Example: Path("/tmp/repo").
        :param entries: Generated entries. Example: a Cursor rule with a .mdc filename.
        :return: Active directory, leaf, content and absent canonical summary name.
        :raises ValueError: If a rules directory is redirected or an entry is misplaced.
        """
        for entry in entries:
            rules_directory = Path(
                ade_root_relative_path(entry["ade_target"], "")
            ).parent
            filename = entry["filename"]
            if Path(entry["path"]) != rules_directory / filename:
                raise ValueError("The ADE file must use its active rules directory.")
            rules_root = dev_root / rules_directory
            if confined_export_path(dev_root, str(rules_directory)) != rules_root:
                raise ValueError(
                    "The ADE rules directory must remain in its approved location."
                )
            yield rules_root, filename, entry["content"], None

    @staticmethod
    def _record_completed_export(
        *,
        user: User | AnonymousUser | None,
        playbook_id: int,
        event_identity: UUID,
        ade_files: int,
        inline: bool,
    ) -> None:
        """Delegate one fully successful authenticated playbook export to S36.

        :param user: Existing service actor. Example: Maria, or None.
        :param playbook_id: Source playbook ID. Example: 6201.
        :param event_identity: Single invocation UUID. Example: UUID(int=42).
        :param ade_files: Count of formatted ADE file entries. Example: 1.
        :param inline: Whether an inline rule section was generated. Example: False.
        :return: None after shared domain decision.
        :raises PermissionError: If domain revalidation rejects the actor.
        :raises ValueError: If event identity or entity is invalid.
        """
        trace = (
            f"operation_uuid={event_identity} entity_type=playbook entity_id={playbook_id}"
            f" actor_id={getattr(user, 'pk', None)} channel=export"
        )
        try:
            outcomes = (
                KarmaService.award_successful_consumption(
                    user, "playbook", playbook_id, event_identity, channel="export"
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
            "%s | exit | %s outcome=%s created_count=%s ade_files=%s inline=%s",
            _EXPORT_LOG,
            trace,
            status,
            created,
            ade_files,
            inline,
        )
