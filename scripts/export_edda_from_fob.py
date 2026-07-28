#!/usr/bin/env python3
"""One-shot: export Edda playbook v55 from FOB API into .cursor/ and .windsurf/."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASE = "https://mimir.featurefactory.io/api"
TOKEN = "be326d87616bcf3ec833f19d43e6f3e465a49a84"

WORKFLOWS = [
    (8, "ESM"),
    (9, "DTA"),
    (10, "DSP"),
    (11, "EST"),
    (12, "DCI"),
    (13, "DCD"),
    (14, "BSP"),
    (15, "BPE"),
    (16, "PIN"),
    (17, "MIN"),
    (54, "TFK"),
]

REPO_RULE_SLUGS = {
    "ff-shorthand",
    "iteration-protocol",
    "do-use-project-venv",
}


def slugify_title(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug.strip("-")


def api(method: str, path: str, body: dict | None = None) -> dict | list:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def api_paginated(path: str) -> list:
    items: list = []
    url_path = path
    while url_path:
        data = api("GET", url_path)
        if isinstance(data, list):
            return data
        items.extend(data.get("results", []))
        nxt = data.get("next")
        if nxt:
            url_path = nxt.replace(BASE, "")
        else:
            break
    return items


def format_rule_mdc(rule: dict) -> str:
    aa = "true" if rule.get("always_apply") else "false"
    content = (rule.get("content") or "").strip()
    body = f"---\nalwaysApply: {aa}\n---\n\n{content}"
    if content and not content.endswith("\n"):
        body += "\n"
    return body


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def export_workflows() -> dict[str, str]:
    """Export workflows; return merged rule filename -> mdc content."""
    cursor_root = REPO / ".cursor/playbooks/Edda"
    windsurf_root = REPO / ".windsurf/workflows/Edda"
    rules_merged: dict[str, str] = {}

    for wf_id, folder in WORKFLOWS:
        data = api("POST", f"/workflows/{wf_id}/export/", {"folder_name": folder})
        for root in (cursor_root, windsurf_root):
            wf_dir = root / folder
            wf_dir.mkdir(parents=True, exist_ok=True)
            for entry in data["workflow_files"]:
                write_text(wf_dir / entry["filename"], entry["content"])
        for entry in data.get("rule_files", []):
            rules_merged[entry["filename"]] = entry["content"]
        print(f"  workflow {folder}: {len(data['workflow_files'])} files")

    return rules_merged


def write_rules(all_rules: list[dict], export_rules: dict[str, str]) -> None:
    cursor_rules = REPO / ".cursor/rules"
    windsurf_rules = REPO / ".windsurf/rules"
    edda_cursor_rules = REPO / ".cursor/playbooks/Edda/rules"
    edda_windsurf_rules = REPO / ".windsurf/workflows/Edda/rules"

    # Merge API rules (authoritative) with export snippets
    by_slug: dict[str, dict] = {r["slug"]: r for r in all_rules}
    for fname, content in export_rules.items():
        slug = fname.replace(".mdc", "")
        if slug not in by_slug:
            by_slug[slug] = {"slug": slug, "content": content, "always_apply": "alwaysApply: true" in content[:80]}

    # Wipe stale playbook rules in IDE roots (keep repo-specific)
    for rules_dir in (cursor_rules, windsurf_rules):
        if rules_dir.exists():
            for f in rules_dir.iterdir():
                if f.suffix in (".mdc", ".md") and f.stem not in REPO_RULE_SLUGS:
                    f.unlink()

    for rule in sorted(by_slug.values(), key=lambda r: r["slug"]):
        slug = rule["slug"]
        mdc = format_rule_mdc(rule) if "content" in rule and isinstance(rule["content"], str) else export_rules.get(f"{slug}.mdc", "")
        md = (rule.get("content") or "").strip()
        if md and not md.endswith("\n"):
            md += "\n"

        write_text(cursor_rules / f"{slug}.mdc", mdc)
        write_text(windsurf_rules / f"{slug}.md", md)
        write_text(edda_cursor_rules / f"{slug}.mdc", mdc)
        write_text(edda_windsurf_rules / f"{slug}.mdc", mdc)

    print(f"  rules: {len(by_slug)}")


def write_skills(skills: list[dict]) -> None:
    for root in (
        REPO / ".cursor/playbooks/Edda/skills",
        REPO / ".windsurf/workflows/Edda/skills",
    ):
        root.mkdir(parents=True, exist_ok=True)
        for skill in skills:
            fname = f"{slugify_title(skill['title'])}.md"
            content = skill.get("content") or ""
            if content and not content.endswith("\n"):
                content += "\n"
            write_text(root / fname, content)
    print(f"  skills: {len(skills)}")


def write_agents(agents: list[dict]) -> None:
    for root in (
        REPO / ".cursor/playbooks/Edda/agents",
        REPO / ".windsurf/workflows/Edda/agents",
    ):
        root.mkdir(parents=True, exist_ok=True)
        for agent in agents:
            slug = slugify_title(agent["name"])
            content = agent.get("description") or ""
            if content and not content.endswith("\n"):
                content += "\n"
            write_text(root / f"{slug}.md", content)

    dr_dobbs = next((a for a in agents if a["name"] == "dr-dobbs"), None)
    if dr_dobbs:
        agents_dir = REPO / ".cursor/agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        write_text(agents_dir / "dr-dobbs.md", dr_dobbs["description"] + "\n")

    print(f"  agents: {len(agents)}")


def write_artifacts(artifacts: list[dict]) -> None:
    for root in (
        REPO / ".cursor/playbooks/Edda/artifacts",
        REPO / ".windsurf/workflows/Edda/artifacts",
    ):
        root.mkdir(parents=True, exist_ok=True)
        for art in artifacts:
            fname = f"{slugify_title(art['name'])}.md"
            content = art.get("description") or art.get("content") or ""
            if content and not content.endswith("\n"):
                content += "\n"
            write_text(root / fname, content)
    print(f"  artifacts: {len(artifacts)}")


def write_playbook_md(pb: dict, workflows: list[dict]) -> None:
    lines = [
        f"# Edda (v{pb['version']})",
        "",
        f"**Playbook**: {pb['name']}",
        f"**Version**: {pb['version']} ({pb['status'].capitalize()})",
        f"**Purpose**: {pb['description']}",
        "",
        "---",
        "",
        "## Workflows",
        "",
        "| # | Abbr | Name | Activities |",
        "|---|------|------|------------|",
    ]
    for wf in sorted(workflows, key=lambda w: w["order"]):
        abbr = wf.get("abbreviation") or wf["name"][:3].upper()
        lines.append(
            f"| {wf['order']} | **{abbr}** | {wf['name']} | {wf.get('activity_count', '?')} |"
        )
    lines.extend(
        [
            "",
            "---",
            "",
            f"*Exported from FOB ({BASE.replace('/api', '')}) — playbook id {pb['id']}*",
            "",
        ]
    )
    body = "\n".join(lines)
    for path in (
        REPO / ".cursor/playbooks/Edda/playbook.md",
        REPO / ".windsurf/workflows/Edda/playbook.md",
    ):
        write_text(path, body)


def restore_repo_rules() -> None:
    """Re-apply repo-specific Cursor rules saved before export."""
    backups = {
        "ff-shorthand.mdc": REPO / ".cursor/rules/ff-shorthand.mdc",
        "iteration-protocol.mdc": REPO / ".cursor/rules/iteration-protocol.mdc",
        "do-use-project-venv.mdc": REPO / ".cursor/rules/do-use-project-venv.mdc",
    }
    # Files should still exist if not deleted; if wiped, user must restore from git
    for name, path in backups.items():
        if not path.exists():
            print(f"  WARN: missing repo rule {name} — restore from git if needed")


def main() -> None:
    print("Exporting Edda from FOB...")
    pb = api("GET", "/playbooks/3/")
    workflows = api_paginated("/workflows/?playbook_id=3")
    print(f"Playbook: {pb['name']} v{pb['version']} — {len(workflows)} workflows")

    export_rules = export_workflows()
    rules = api_paginated("/rules/?playbook_id=3")
    skills = api_paginated("/skills/?playbook_id=3")
    agents = api_paginated("/agents/?playbook_id=3")
    artifacts = api_paginated("/artifacts/?playbook_id=3")

    write_rules(rules, export_rules)
    write_skills(skills)
    write_agents(agents)
    write_artifacts(artifacts)
    write_playbook_md(pb, workflows)
    restore_repo_rules()
    print("Done.")


if __name__ == "__main__":
    main()
