"""Format playbook rules for ADE-specific export surfaces."""

from __future__ import annotations

from typing import Iterable, Sequence

VALID_ADE_TARGETS = frozenset({"cursor", "devin", "claude", "copilot"})
FILE_ADE_TARGETS = frozenset({"cursor", "devin"})


def normalize_ade_targets(
    ade_targets: Sequence[str] | None,
    *,
    ade_target: str | None = None,
) -> list[str]:
    """Normalize singular alias and validate known target names.

    :param ade_targets: List of ADE keys. Example: ["cursor", "devin"]
    :param ade_target: Optional singular alias merged into the list
    :return: Normalized list (may be empty)
    :raises ValueError: if an unknown target name is provided
    """
    merged: list[str] = list(ade_targets or [])
    if ade_target:
        merged.append(ade_target)
    normalized: list[str] = []
    for target in merged:
        key = (target or "").strip().lower()
        if not key:
            continue
        if key not in VALID_ADE_TARGETS:
            raise ValueError(
                f"Invalid ade_target {target!r}; must be one of: "
                f"{', '.join(sorted(VALID_ADE_TARGETS))}"
            )
        if key not in normalized:
            normalized.append(key)
    return normalized


def validate_ade_export_params(
    *,
    ade_targets: Sequence[str] | None,
    sync_root_rules: bool,
    force_apply: bool,
    ade_target: str | None = None,
) -> list[str]:
    """Validate ADE export params and return normalized ade_targets.

    :raises ValueError: when sync/force_apply set but ade_targets is empty
    """
    normalized = normalize_ade_targets(ade_targets, ade_target=ade_target)
    if (sync_root_rules or force_apply) and not normalized:
        raise ValueError("ade_targets required when sync_root_rules or force_apply is enabled")
    return normalized


def format_rule_for_ade(rule, ade_target: str, *, force_apply: bool = False) -> str:
    """Format one rule for a file-based ADE target.

    :param rule: Rule model instance
    :param ade_target: ``cursor`` or ``devin``
    :param force_apply: When true, Cursor copy uses alwaysApply true
    :return: File body string
    """
    target = ade_target.lower()
    content = (rule.content or "").strip()
    if target == "cursor":
        apply = force_apply or bool(rule.always_apply)
        aa = "true" if apply else "false"
        body = f"---\nalwaysApply: {aa}\n---\n\n"
        body += content
        if content and not content.endswith("\n"):
            body += "\n"
        return body
    if target == "devin":
        title = rule.title or rule.slug
        body = f"# {title}\n\n"
        body += content
        if content and not content.endswith("\n"):
            body += "\n"
        return body
    raise ValueError(f"format_rule_for_ade does not support ade_target={ade_target!r}")


def ade_root_relative_path(ade_target: str, slug: str) -> str:
    """Relative path from dev root for an apply-on rule file."""
    target = ade_target.lower()
    if target == "cursor":
        return f".cursor/rules/{slug}.mdc"
    if target == "devin":
        return f".windsurf/rules/{slug}.md"
    raise ValueError(f"No file path for ade_target={ade_target!r}")


def build_inline_rules_markdown(rules: Iterable, *, force_apply: bool = False) -> str:
    """Build markdown section for Claude/Copilot inline rule injection.

    :param rules: Rule queryset or list
    :param force_apply: When true, include every rule; else only always_apply rules
    :return: Markdown string (empty when no qualifying rules)
    """
    sections: list[str] = []
    for rule in rules:
        if not force_apply and not rule.always_apply:
            continue
        title = rule.title or rule.slug
        content = (rule.content or "").strip()
        sections.append(f"### {title} (`{rule.slug}`)\n\n{content}\n")
    if not sections:
        return ""
    return "## Playbook Rules\n\n" + "\n".join(sections)


def build_ade_rule_files(
    rules: Iterable,
    ade_targets: Sequence[str],
    *,
    force_apply: bool = False,
) -> list[dict]:
    """Build apply-on file entries for file-based ADE targets."""
    files: list[dict] = []
    for target in ade_targets:
        if target not in FILE_ADE_TARGETS:
            continue
        for rule in rules:
            if not force_apply and not rule.always_apply:
                continue
            content = format_rule_for_ade(rule, target, force_apply=force_apply)
            rel_path = ade_root_relative_path(target, rule.slug)
            filename = rel_path.rsplit("/", 1)[-1]
            files.append(
                {
                    "filename": filename,
                    "content": content,
                    "path": rel_path,
                    "ade_target": target,
                    "slug": rule.slug,
                }
            )
    return files
