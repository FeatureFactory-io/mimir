"""Export full playbooks to local IDE workspace trees."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from django.core.exceptions import ObjectDoesNotExist

from methodology.models import Agent, Artifact, Playbook, Rule, Skill, Workflow
from methodology.services.playbook_service import PlaybookService
from methodology.services.rule_export_formatters import (
    build_ade_rule_files,
    build_inline_rules_markdown,
    normalize_ade_targets,
    validate_ade_export_params,
)
from methodology.services.workflow_export_service import WorkflowExportService

logger = logging.getLogger(__name__)


class PlaybookExportService:
    """Orchestrate playbook-level markdown export for AI IDE workspaces."""

    @staticmethod
    def export_playbook_to_local(
        playbook_id: int,
        target_directory: str,
        folder_name: Optional[str] = None,
        additional_targets: Optional[list[str]] = None,
        sync_root_rules: bool = False,
        ade_targets: Optional[list[str]] = None,
        force_apply: bool = False,
        ade_target: Optional[str] = None,
        user=None,
    ) -> dict:
        """
        Export a playbook and all nested entities to markdown under ``target_directory``.

        :param playbook_id: Playbook primary key
        :param target_directory: Base directory (e.g. ``.cursor/playbooks``)
        :param folder_name: Playbook folder name (defaults to slugified playbook name)
        :param additional_targets: Optional extra roots receiving a copy of the tree
        :param sync_root_rules: Copy apply-on rules to ADE load paths from ``ade_targets``
        :param ade_targets: ADE keys (cursor, devin, claude, copilot); ≥1 when sync/force
        :param force_apply: Apply-on frontmatter for ADE copies even when DB flag is false
        :param ade_target: Singular alias normalized into ``ade_targets``
        :param user: Authenticated user for read permission checks
        :return: Summary dict with counts and file paths
        """
        try:
            normalized_targets = validate_ade_export_params(
                ade_targets=ade_targets,
                sync_root_rules=sync_root_rules,
                force_apply=force_apply,
                ade_target=ade_target,
            )
        except ValueError as exc:
            logger.error(
                "PlaybookExportService.export_playbook_to_local | error | "
                "ade_targets required | %s",
                exc,
            )
            raise
        ade_targets_str = ",".join(normalized_targets) if normalized_targets else ""
        logger.info(
            "PlaybookExportService.export_playbook_to_local | entry | "
            "playbook_id=%s target=%s folder=%s sync_root_rules=%s "
            "ade_targets=%s force_apply=%s",
            playbook_id,
            target_directory,
            folder_name,
            sync_root_rules,
            ade_targets_str,
            force_apply,
        )
        bundle = PlaybookExportService.generate_playbook_export_bundle(
            playbook_id=playbook_id,
            folder_name=folder_name,
            ade_targets=normalized_targets,
            force_apply=force_apply,
            user=user,
        )
        targets = [target_directory] + list(additional_targets or [])
        export_paths = []
        all_files: list[str] = []

        for target in targets:
            export_root = Path(target) / bundle["folder_name"]
            export_root.mkdir(parents=True, exist_ok=True)
            files_written = PlaybookExportService._write_bundle_to_disk(
                bundle, export_root
            )
            export_paths.append(str(export_root.absolute()))
            all_files.extend(files_written)
            logger.info(
                "Playbook export wrote playbook_id=%s path=%s files=%s",
                playbook_id,
                export_root,
                len(files_written),
            )

        if sync_root_rules:
            PlaybookExportService._sync_ade_root_rules(
                bundle,
                Path(target_directory),
                force_apply=force_apply,
            )

        inline_md = bundle.get("inline_rules_markdown") or ""
        ade_files = bundle.get("ade_rule_files") or []
        result = {
            "status": "exported",
            "playbook_id": bundle["playbook_id"],
            "playbook_name": bundle["playbook_name"],
            "export_paths": export_paths,
            "workflows": bundle["counts"]["workflows"],
            "activities": bundle["counts"]["activities"],
            "rules": bundle["counts"]["rules"],
            "skills": bundle["counts"]["skills"],
            "agents": bundle["counts"]["agents"],
            "artifacts": bundle["counts"]["artifacts"],
            "files_created": all_files,
            "ade_rule_files": ade_files,
            "inline_rules_markdown": inline_md,
            "message": "Playbook exported successfully.",
        }
        logger.info(
            "PlaybookExportService.export_playbook_to_local | exit | "
            "playbook_id=%s workflows=%s rules=%s files=%s ade_files=%s inline=%s",
            playbook_id,
            result["workflows"],
            result["rules"],
            len(all_files),
            len(ade_files),
            bool(inline_md),
        )
        return result

    @staticmethod
    def generate_playbook_export_bundle(
        playbook_id: int,
        folder_name: Optional[str] = None,
        ade_targets: Optional[list[str]] = None,
        force_apply: bool = False,
        ade_target: Optional[str] = None,
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
    def _write_bundle_to_disk(bundle: dict, export_root: Path) -> list[str]:
        written: list[str] = []

        def _write(rel_dir: str, filename: str, content: str) -> None:
            folder = export_root / rel_dir if rel_dir else export_root
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / filename
            path.write_text(content, encoding="utf-8")
            rel = f"{rel_dir}/{filename}" if rel_dir else filename
            written.append(rel)
            logger.info("Playbook export file %s", path)

        _write("", bundle["playbook_md"]["filename"], bundle["playbook_md"]["content"])
        for rule in bundle["rule_files"]:
            _write("rules", rule["filename"], rule["content"])
        for agent in bundle["agent_files"]:
            _write("agents", agent["filename"], agent["content"])
        for skill in bundle["skill_files"]:
            _write("skills", skill["filename"], skill["content"])
        for artifact in bundle["artifact_files"]:
            _write("artifacts", artifact["filename"], artifact["content"])
        for wf in bundle["workflows"]:
            for wf_file in wf["workflow_files"]:
                _write(wf["folder_name"], wf_file["filename"], wf_file["content"])
        return written

    @staticmethod
    def _resolve_dev_root(target_directory: Path) -> Path:
        """Project dev root from a ``.cursor/playbooks`` (or similar) export target."""
        resolved = target_directory.resolve()
        if resolved.name == "playbooks" and resolved.parent.name == ".cursor":
            return resolved.parent.parent
        return resolved.parent

    @staticmethod
    def _sync_ade_root_rules(
        bundle: dict, target_directory: Path, *, force_apply: bool = False
    ) -> None:
        dev_root = PlaybookExportService._resolve_dev_root(target_directory)
        for entry in bundle.get("ade_rule_files") or []:
            rel = entry["path"]
            dest = dev_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(entry["content"], encoding="utf-8")
            logger.info(
                "PlaybookExportService._sync_ade_root_rules | processing | "
                "path=%s slug=%s force_apply=%s",
                rel,
                entry.get("slug"),
                force_apply,
            )

    @staticmethod
    def _generate_playbook_md(playbook, workflows, activity_count: int) -> str:
        export_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        wf_lines = "\n".join(
            f"- **{wf.name}** (order {wf.order})" for wf in workflows
        ) or "- _(no workflows)_"
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
