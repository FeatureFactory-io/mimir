"""Contract tests for scripts/integrate.sh guards."""

from __future__ import annotations

import textwrap

import pytest

from tests.support.factory_test_helpers import (
    CODE_TASK_TEMPLATE,
    DEFAULT_PATH,
    MANUAL_TASK_TEMPLATE,
    init_factory_repo,
    run_script,
    write_task,
)


@pytest.fixture
def factory_repo(tmp_path):
    init_factory_repo(tmp_path)
    return tmp_path


def _stub_gh(bin_dir, pr_state="OPEN", mergeable="MERGEABLE", merge_state="CLEAN"):
    (bin_dir / "gh").write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            if [[ "$1" == "pr" && "$2" == "view" ]]; then
              echo '{{"state":"{pr_state}","mergeable":"{mergeable}","mergeStateStatus":"{merge_state}","statusCheckRollup":[]}}'
              exit 0
            fi
            if [[ "$1" == "pr" && "$2" == "merge" ]]; then exit 0; fi
            if [[ "$1" == "pr" && "$2" == "diff" ]]; then
              echo "src/example.py"
              exit 0
            fi
            exit 1
            """
        ),
        encoding="utf-8",
    )
    (bin_dir / "gh").chmod(0o755)
    (bin_dir / "jq").write_text("#!/usr/bin/env bash\n/usr/bin/jq \"$@\"\n", encoding="utf-8")
    (bin_dir / "jq").chmod(0o755)


def test_integrate_validate_manual_task(factory_repo):
    write_task(
        factory_repo,
        "done",
        "T-M01",
        MANUAL_TASK_TEMPLATE.format(task_id="T-M01", status="passed"),
    )
    proc = run_script("scripts/integrate.sh", "validate", "T-M01", cwd=factory_repo)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    content = (factory_repo / "factory/tasks/done/T-M01.md").read_text(encoding="utf-8")
    assert "status: validated" in content


def test_integrate_merge_rejects_non_mergeable_pr(factory_repo):
    write_task(
        factory_repo,
        "done",
        "T-C01",
        CODE_TASK_TEMPLATE.format(
            task_id="T-C01",
            deps="[]",
            status="passed",
            branch="factory/T-C01",
            mr="10",
            sha="abc1234",
        ),
    )
    bin_dir = factory_repo / "bin"
    bin_dir.mkdir()
    _stub_gh(bin_dir, mergeable="CONFLICTING", merge_state="DIRTY")

    proc = run_script(
        "scripts/integrate.sh",
        "merge",
        "T-C01",
        cwd=factory_repo,
        env={
            "PATH": f"{bin_dir}:{DEFAULT_PATH}",
            "FACTORY_SKIP_POST_MERGE": "1",
        },
    )
    assert proc.returncode == 1
    assert "not mergeable" in proc.stderr


def test_integrate_merge_marks_integrated(factory_repo):
    body = CODE_TASK_TEMPLATE.format(
        task_id="T-C02",
        deps="[]",
        status="passed",
        branch="factory/T-C02",
        mr="11",
        sha="def5678",
    )
    body = body.replace(
        "depends_on: []",
        "depends_on: []\nfiles_in_scope:\n  - src/example.py",
    )
    write_task(factory_repo, "done", "T-C02", body)

    bin_dir = factory_repo / "bin"
    bin_dir.mkdir()
    _stub_gh(bin_dir)

    proc = run_script(
        "scripts/integrate.sh",
        "merge",
        "T-C02",
        cwd=factory_repo,
        env={
            "PATH": f"{bin_dir}:{DEFAULT_PATH}",
            "FACTORY_SKIP_POST_MERGE": "1",
        },
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    content = (factory_repo / "factory/tasks/done/T-C02.md").read_text(encoding="utf-8")
    assert "status: integrated" in content


def test_integrate_merge_rejects_unintegrated_dependency(factory_repo):
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
            sha="aaa",
        ),
    )
    write_task(
        factory_repo,
        "done",
        "T-002",
        textwrap.dedent(
            """\
            ---
            id: T-002
            role: feature-builder
            attempt: 1
            depends_on: [T-001]
            branch: factory/T-002
            files_in_scope:
              - src/example.py
            ---
            ## Goal
            Second task.

            # Result

            status: passed
            branch: factory/T-002
            mr: 12
            commit_sha: bbb
            """
        ),
    )
    bin_dir = factory_repo / "bin"
    bin_dir.mkdir()
    _stub_gh(bin_dir)

    proc = run_script(
        "scripts/integrate.sh",
        "merge",
        "T-002",
        cwd=factory_repo,
        env={
            "PATH": f"{bin_dir}:{DEFAULT_PATH}",
            "FACTORY_SKIP_POST_MERGE": "1",
        },
    )
    assert proc.returncode == 1
    assert "dependency T-001 not integrated" in proc.stderr
