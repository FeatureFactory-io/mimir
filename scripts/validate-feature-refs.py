#!/usr/bin/env python3
"""Validate feature file references in GitHub issue bodies for factory preflight."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FEATURE_PATH_RE = re.compile(r"docs/features/[^\s\)]+\.feature")
SCENARIO_RE = re.compile(r"^\s*Scenario(?: Outline)?:\s*(.+)$", re.MULTILINE)
URL_IN_STEP_RE = re.compile(r"(/auth/[^\s\"']+|/dashboard/[^\s\"']+)")


def extract_feature_paths(text: str) -> list[str]:
    return sorted(set(FEATURE_PATH_RE.findall(text)))


def validate_feature_file(repo_root: Path, rel_path: str) -> list[str]:
    errors: list[str] = []
    path = repo_root / rel_path
    if not path.is_file():
        errors.append(f"missing file: {rel_path}")
        return errors

    content = path.read_text(encoding="utf-8")
    scenarios = SCENARIO_RE.findall(content)
    if not scenarios:
        errors.append(f"no Scenario blocks in {rel_path}")

    titles = [s.strip() for s in scenarios]
    if len(titles) != len(set(titles)):
        errors.append(f"duplicate Scenario titles in {rel_path}")

    urls = URL_IN_STEP_RE.findall(content)
    auth_login = [u for u in urls if "login" in u.lower()]
    if len(set(auth_login)) > 1:
        errors.append(
            f"conflicting login URLs in {rel_path}: {sorted(set(auth_login))}"
        )

    vague = [
        "guided through",
        "sees highlights",
        "proceeds with the tour",
    ]
    for phrase in vague:
        if phrase in content.lower():
            errors.append(f"vague step wording in {rel_path}: contains '{phrase}'")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate issue feature references")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root (default: cwd)",
    )
    parser.add_argument(
        "--issues-json",
        default="-",
        help="GitHub issues JSON on stdin or path",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if args.issues_json == "-":
        issues = json.load(sys.stdin)
    else:
        issues = json.loads(Path(args.issues_json).read_text(encoding="utf-8"))

    if not isinstance(issues, list) or not issues:
        print("error: no issues provided", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    checked_paths: set[str] = set()

    for issue in issues:
        number = issue.get("number", "?")
        body = (issue.get("title") or "") + "\n" + (issue.get("body") or "")
        paths = extract_feature_paths(body)
        if not paths:
            if os.environ.get("PREFLIGHT_ALLOW_MISSING_FEATUREFILE_REF") == "1":
                continue
            all_errors.append(f"issue #{number}: no docs/features/*.feature reference")
            continue
        for rel in paths:
            checked_paths.add(rel)
            for err in validate_feature_file(repo_root, rel):
                all_errors.append(f"issue #{number}: {err}")

    if all_errors:
        for err in all_errors:
            print(f"error: {err}", file=sys.stderr)
        return 1

    print(
        f"feature refs ok: {len(issues)} issue(s), "
        f"{len(checked_paths)} unique feature file(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
