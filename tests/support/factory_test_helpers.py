"""Helpers for dark-factory shell script contract tests."""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_script(
    script: str,
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a repo script; when cwd is set, treat it as FACTORY_REPO_ROOT."""
    merged = os.environ.copy()
    merged.setdefault("PATH", os.environ.get("PATH", ""))
    if cwd is not None:
        merged["FACTORY_REPO_ROOT"] = str(cwd.resolve())
    if env:
        merged.update(env)
    script_path = REPO_ROOT / script
    cmd = ["bash", str(script_path), *args]
    return subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        env=merged,
        capture_output=True,
        text=True,
        check=False,
    )


def init_factory_repo(root: Path) -> None:
    """Bootstrap a minimal git repo with factory/ layout for script tests."""
    root.mkdir(parents=True, exist_ok=True)
    for sub in (
        "factory/tasks/pending",
        "factory/tasks/claimed",
        "factory/tasks/done",
        "factory/tasks/blocked",
        "factory/tasks/rejected",
        "factory/logs",
        "scripts/lib",
        "docs/features/act-test",
    ):
        (root / sub).mkdir(parents=True, exist_ok=True)

    for name in (
        "factory-common.sh",
        "factory-git-inner.sh",
    ):
        src = REPO_ROOT / "scripts/lib" / name
        if src.is_file():
            shutil.copy2(src, root / "scripts/lib" / name)

    for script in (
        "claim.sh",
        "done.sh",
        "verify-result.sh",
        "integrate.sh",
        "release.sh",
        "rescue-result.sh",
        "factory-git.sh",
        "preflight.sh",
    ):
        src = REPO_ROOT / "scripts" / script
        if src.is_file():
            shutil.copy2(src, root / "scripts" / script)

    validator = REPO_ROOT / "scripts/validate-feature-refs.py"
    if validator.is_file():
        shutil.copy2(validator, root / "scripts/validate-feature-refs.py")

    (root / "factory/blackboard.md").write_text("# Blackboard\n", encoding="utf-8")
    (root / "Makefile").write_text(
        textwrap.dedent(
            """\
            lint:
            \t@echo lint-ok
            test:
            \t@echo test-ok
            """
        ),
        encoding="utf-8",
    )
    (root / "docs/features/act-test/sample.feature").write_text(
        textwrap.dedent(
            """\
            Feature: Sample
              Scenario: One
                Given a user
                When they act
                Then it works
            """
        ),
        encoding="utf-8",
    )

    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init factory test repo"],
        cwd=root,
        check=True,
        capture_output=True,
    )


def write_task(root: Path, lane: str, task_id: str, body: str) -> Path:
    path = root / f"factory/tasks/{lane}/{task_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


CODE_TASK_TEMPLATE = textwrap.dedent(
    """\
    ---
    id: {task_id}
    role: feature-builder
    attempt: 1
    depends_on: {deps}
    branch: {branch}
    ---

    ## Goal
    Test task.

    # Result

    status: {status}
    branch: {branch}
    mr: {mr}
    commit_sha: {sha}
    """
)

def commit_all(root: Path, message: str = "test: commit factory state") -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=root, check=True, capture_output=True)


DEFAULT_PATH = os.environ.get("PATH", "/usr/bin:/bin")

MANUAL_TASK_TEMPLATE = textwrap.dedent(
    """\
    ---
    id: {task_id}
    role: manual-tester
    attempt: 1
    depends_on: []
    branch: none
    ---

    ## Goal
    Manual validation.

    # Result

    status: {status}
    branch: none
    mr: 0
    commit_sha: none

    ## Evidence

    | Scenario | Status | Evidence |
    |----------|--------|----------|
    | One | PASS | factory/logs/evidence.png |
    """
)
