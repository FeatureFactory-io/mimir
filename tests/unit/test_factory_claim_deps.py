"""Contract tests for scripts/claim.sh dependency eligibility."""

from __future__ import annotations

import textwrap

import pytest

from tests.support.factory_test_helpers import (
    CODE_TASK_TEMPLATE,
    init_factory_repo,
    run_script,
    write_task,
)


@pytest.fixture
def factory_repo(tmp_path):
    init_factory_repo(tmp_path)
    return tmp_path


def test_claim_succeeds_when_dependency_integrated(factory_repo):
    write_task(
        factory_repo,
        "done",
        "T-001",
        CODE_TASK_TEMPLATE.format(
            task_id="T-001",
            deps="[]",
            status="integrated",
            branch="factory/T-001",
            mr="1",
            sha="abc1234",
        ),
    )
    write_task(
        factory_repo,
        "pending",
        "T-002",
        textwrap.dedent(
            """\
            ---
            id: T-002
            role: feature-builder
            attempt: 1
            depends_on:
              - T-001
            branch: factory/T-002
            ---
            ## Goal
            Depends on integrated task.
            """
        ),
    )
    proc = run_script("scripts/claim.sh", "T-002", "feature-builder", cwd=factory_repo)
    assert proc.returncode == 0, proc.stderr
    assert (factory_repo / "factory/tasks/claimed/T-002.md").is_file()


def test_claim_fails_when_dependency_not_terminal(factory_repo):
    write_task(
        factory_repo,
        "done",
        "T-001",
        CODE_TASK_TEMPLATE.format(
            task_id="T-001",
            deps="[]",
            status="passed",
            branch="factory/T-001",
            mr="1",
            sha="abc1234",
        ),
    )
    write_task(
        factory_repo,
        "pending",
        "T-002",
        textwrap.dedent(
            """\
            ---
            id: T-002
            role: feature-builder
            attempt: 1
            depends_on: [T-001]
            branch: factory/T-002
            ---
            ## Goal
            Waiting on integration.
            """
        ),
    )
    proc = run_script("scripts/claim.sh", "T-002", "feature-builder", cwd=factory_repo)
    assert proc.returncode == 1
    assert (factory_repo / "factory/tasks/pending/T-002.md").is_file()


def test_claim_accepts_manual_dependency_validated(factory_repo):
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
            Manual done.

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
    write_task(
        factory_repo,
        "pending",
        "T-003",
        textwrap.dedent(
            """\
            ---
            id: T-003
            role: release-engineer
            attempt: 1
            depends_on: [T-M01]
            branch: release/1.0.0
            ---
            ## Goal
            After manual validation.
            """
        ),
    )
    proc = run_script("scripts/claim.sh", "T-003", "release-engineer", cwd=factory_repo)
    assert proc.returncode == 0, proc.stderr
