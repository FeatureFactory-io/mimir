"""Contract tests for scripts/release.sh guards."""

from __future__ import annotations

import subprocess
import textwrap

import pytest

from tests.support.factory_test_helpers import (
    CODE_TASK_TEMPLATE,
    MANUAL_TASK_TEMPLATE,
    commit_all,
    init_factory_repo,
    run_script,
    write_task,
)


@pytest.fixture
def factory_repo(tmp_path):
    init_factory_repo(tmp_path)
    return tmp_path


def test_release_rejects_non_terminal_done_tasks(factory_repo):
    write_task(
        factory_repo,
        "done",
        "T-C01",
        CODE_TASK_TEMPLATE.format(
            task_id="T-C01",
            deps="[]",
            status="passed",
            branch="factory/T-C01",
            mr="1",
            sha="abc",
        ),
    )
    proc = run_script("scripts/release.sh", "1.0.0", "--dry-run", cwd=factory_repo)
    assert proc.returncode == 1
    assert "not in terminal status" in proc.stderr


def test_release_accepts_integrated_code_and_validated_manual(factory_repo):
    write_task(
        factory_repo,
        "done",
        "T-C01",
        CODE_TASK_TEMPLATE.format(
            task_id="T-C01",
            deps="[]",
            status="integrated",
            branch="factory/T-C01",
            mr="1",
            sha="abc",
        ),
    )
    write_task(
        factory_repo,
        "done",
        "T-M01",
        textwrap.dedent(
            """\
            ---
            id: T-M01
            role: manual-tester
            attempt: 1
            depends_on: []
            branch: none
            ---
            ## Goal
            Manual validated.

            # Result

            status: validated
            branch: none
            mr: 0
            commit_sha: none

            ## Evidence

            | Scenario | Status | Evidence |
            | One | PASS | factory/logs/x.png |
            """
        ),
    )
    commit_all(factory_repo)
    proc = run_script("scripts/release.sh", "1.0.0", "--dry-run", cwd=factory_repo)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "DRY RUN" in proc.stdout


def test_release_rejects_dirty_main(factory_repo):
    write_task(
        factory_repo,
        "done",
        "T-C01",
        CODE_TASK_TEMPLATE.format(
            task_id="T-C01",
            deps="[]",
            status="integrated",
            branch="factory/T-C01",
            mr="1",
            sha="abc",
        ),
    )
    (factory_repo / "untracked.txt").write_text("x", encoding="utf-8")
    proc = run_script("scripts/release.sh", "1.0.0", "--dry-run", cwd=factory_repo)
    assert proc.returncode == 1
    assert "working tree not clean" in proc.stderr


def test_release_target_sha_guard(factory_repo):
    write_task(
        factory_repo,
        "done",
        "T-C01",
        CODE_TASK_TEMPLATE.format(
            task_id="T-C01",
            deps="[]",
            status="integrated",
            branch="factory/T-C01",
            mr="1",
            sha="abc",
        ),
    )
    commit_all(factory_repo)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=factory_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    proc = run_script(
        "scripts/release.sh",
        "1.0.0",
        "--dry-run",
        "--target-sha",
        "deadbeef",
        cwd=factory_repo,
    )
    assert proc.returncode == 1
    assert "does not match HEAD" in proc.stderr

    proc_ok = run_script(
        "scripts/release.sh",
        "1.0.0",
        "--dry-run",
        "--target-sha",
        head[:8],
        cwd=factory_repo,
    )
    assert proc_ok.returncode == 0, proc_ok.stderr
