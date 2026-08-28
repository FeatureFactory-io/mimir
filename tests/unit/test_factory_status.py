"""Contract tests for factory state helpers and serialized git transitions."""

from __future__ import annotations

import os
import subprocess
import textwrap

import pytest

from tests.support.factory_test_helpers import init_factory_repo, run_script, write_task


@pytest.fixture
def factory_repo(tmp_path):
    init_factory_repo(tmp_path)
    return tmp_path


def test_factory_common_dep_terminal_status(factory_repo):
    proc = subprocess.run(
        [
            "bash",
            "-c",
            textwrap.dedent(
                """\
                set -e
                source scripts/lib/factory-common.sh
                check() {
                  factory_dep_terminal_status "$1"
                }
                for s in integrated validated monitoring; do
                  f=$(mktemp)
                  printf '%s\\n' '# Result' "status: $s" > "$f"
                  check "$f"
                done
                f=$(mktemp)
                printf '%s\\n' 'role: manual-tester' '# Result' 'status: passed' > "$f"
                check "$f"
                f=$(mktemp)
                printf '%s\\n' '# Result' 'status: passed' > "$f"
                if check "$f"; then exit 1; fi
                """
            ),
        ],
        cwd=factory_repo,
        env={"FACTORY_REPO_ROOT": str(factory_repo), "PATH": os.environ.get("PATH", "")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_factory_result_kind_classification(factory_repo):
    write_task(
        factory_repo,
        "claimed",
        "manual",
        textwrap.dedent(
            """\
            ---
            role: manual-tester
            ---
            # Result
            status: passed
            branch: none
            mr: 0
            commit_sha: none
            """
        ),
    )
    proc = subprocess.run(
        [
            "bash",
            "-c",
            'source scripts/lib/factory-common.sh; factory_result_kind "factory/tasks/claimed/manual.md"',
        ],
        cwd=factory_repo,
        capture_output=True,
        text=True,
    )
    assert proc.stdout.strip() == "manual"


def test_factory_git_serializes_commits(factory_repo):
    write_task(
        factory_repo,
        "pending",
        "T-001",
        textwrap.dedent(
            """\
            ---
            id: T-001
            role: feature-builder
            attempt: 1
            depends_on: []
            branch: factory/T-001
            ---
            ## Goal
            Queue task.
            """
        ),
    )
    proc = run_script(
        "scripts/factory-git.sh",
        "factory: test commit",
        cwd=factory_repo,
        env={"FACTORY_SKIP_PUSH": "1"},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout

    log = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=factory_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "factory: test commit" in log.stdout
