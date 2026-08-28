"""Contract tests for scripts/verify-result.sh."""

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


def test_verify_result_rejects_missing_result_block(factory_repo):
    write_task(
        factory_repo,
        "claimed",
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
            No result yet.
            """
        ),
    )
    proc = run_script("scripts/verify-result.sh", "T-001", cwd=factory_repo)
    assert proc.returncode == 2
    assert "reason:result_block" in proc.stderr


def test_verify_result_accepts_manual_with_evidence(factory_repo):
    write_task(
        factory_repo,
        "claimed",
        "T-M01",
        MANUAL_TASK_TEMPLATE.format(task_id="T-M01", status="passed"),
    )
    proc = run_script("scripts/verify-result.sh", "T-M01", cwd=factory_repo)
    assert proc.returncode == 0, proc.stderr
    assert "manual validation" in proc.stdout


def test_verify_result_rejects_manual_without_evidence(factory_repo):
    body = MANUAL_TASK_TEMPLATE.format(task_id="T-M02", status="passed")
    body = body.replace("## Evidence\n", "")
    write_task(factory_repo, "claimed", "T-M02", body)
    proc = run_script("scripts/verify-result.sh", "T-M02", cwd=factory_repo)
    assert proc.returncode == 2
    assert "reason:evidence" in proc.stderr


def test_verify_result_accepts_monitoring(factory_repo):
    write_task(
        factory_repo,
        "claimed",
        "T-REL",
        textwrap.dedent(
            """\
            ---
            id: T-REL
            role: release-engineer
            attempt: 1
            depends_on: []
            branch: release/1.0.0
            ---
            ## Goal
            Watch pipeline.

            # Result

            status: monitoring
            branch: release/1.0.0
            mr: 0
            commit_sha: monitoring
            """
        ),
    )
    proc = run_script("scripts/verify-result.sh", "T-REL", cwd=factory_repo)
    assert proc.returncode == 0, proc.stderr


def test_verify_result_code_requires_remote_branch_and_pr(factory_repo, monkeypatch):
    write_task(
        factory_repo,
        "claimed",
        "T-C01",
        CODE_TASK_TEMPLATE.format(
            task_id="T-C01",
            deps="[]",
            status="passed",
            branch="factory/T-C01-slug",
            mr="99",
            sha="deadbeef",
        ),
    )

    bin_dir = factory_repo / "bin"
    bin_dir.mkdir()
    (bin_dir / "git").write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            if [[ "$1" == "ls-remote" ]]; then
              echo "deadbeefdeadbeefdeadbeefdeadbeef\\trefs/heads/factory/T-C01-slug"
              exit 0
            fi
            exec /usr/bin/git "$@"
            """
        ),
        encoding="utf-8",
    )
    (bin_dir / "git").chmod(0o755)
    (bin_dir / "gh").write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            if [[ "$1" == "pr" && "$2" == "view" ]]; then
              for arg in "$@"; do
                if [[ "$arg" == ".state" ]]; then
                  echo OPEN
                  exit 0
                fi
              done
              echo '{"state":"OPEN","mergeable":"MERGEABLE","mergeStateStatus":"CLEAN","statusCheckRollup":[]}'
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

    proc = run_script(
        "scripts/verify-result.sh",
        "T-C01",
        cwd=factory_repo,
        env={"PATH": f"{bin_dir}:{DEFAULT_PATH}"},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_verify_result_code_rejects_missing_remote_branch(factory_repo):
    write_task(
        factory_repo,
        "claimed",
        "T-C02",
        CODE_TASK_TEMPLATE.format(
            task_id="T-C02",
            deps="[]",
            status="passed",
            branch="factory/missing",
            mr="1",
            sha="abc1234",
        ),
    )
    bin_dir = factory_repo / "bin"
    bin_dir.mkdir()
    (bin_dir / "git").write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            if [[ "$1" == "ls-remote" ]]; then exit 2; fi
            /usr/bin/git "$@"
            """
        ),
        encoding="utf-8",
    )
    (bin_dir / "git").chmod(0o755)
    (bin_dir / "jq").write_text("#!/usr/bin/env bash\n/usr/bin/jq \"$@\"\n", encoding="utf-8")
    (bin_dir / "jq").chmod(0o755)

    proc = run_script(
        "scripts/verify-result.sh",
        "T-C02",
        cwd=factory_repo,
        env={"PATH": f"{bin_dir}:{DEFAULT_PATH}"},
    )
    assert proc.returncode == 2
    assert "reason:branch" in proc.stderr
