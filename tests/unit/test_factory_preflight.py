"""Contract tests for scripts/validate-feature-refs.py and preflight guards."""

from __future__ import annotations

import json
import subprocess
import textwrap

import pytest

from tests.support.factory_test_helpers import REPO_ROOT, init_factory_repo, run_script


@pytest.fixture
def factory_repo(tmp_path):
    init_factory_repo(tmp_path)
    return tmp_path


def test_validate_feature_refs_rejects_missing_path(factory_repo):
    issues = [{"number": 1, "title": "Auth", "body": "See docs/features/act-test/missing.feature"}]
    proc = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts/validate-feature-refs.py"),
            "--repo-root",
            str(factory_repo),
        ],
        input=json.dumps(issues),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "missing file" in proc.stderr


def test_validate_feature_refs_accepts_valid_feature(factory_repo):
    issues = [
        {
            "number": 2,
            "title": "Sample",
            "body": "Implement docs/features/act-test/sample.feature",
        }
    ]
    proc = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts/validate-feature-refs.py"),
            "--repo-root",
            str(factory_repo),
        ],
        input=json.dumps(issues),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_preflight_rejects_dirty_tree(factory_repo):
    (factory_repo / "dirty.txt").write_text("x", encoding="utf-8")
    bin_dir = factory_repo / "bin"
    bin_dir.mkdir()
    for name in ("gh", "fswatch", "tmux", "rg", "python3", "jq", "curl"):
        wrapper = bin_dir / name
        wrapper.write_text(f'#!/usr/bin/env bash\necho "stub {name}"\nexit 0\n', encoding="utf-8")
        wrapper.chmod(0o755)
    (bin_dir / "cursor-agent").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (bin_dir / "cursor-agent").chmod(0o755)

    proc = run_script(
        "scripts/preflight.sh",
        "Test Milestone",
        cwd=factory_repo,
        env={"PATH": f"{bin_dir}:/usr/bin:/bin"},
    )
    assert proc.returncode == 1
    assert "working tree not clean" in proc.stderr


def test_preflight_allow_dirty_waives_clean_tree(factory_repo):
    (factory_repo / "dirty.txt").write_text("x", encoding="utf-8")
    bin_dir = factory_repo / "bin"
    bin_dir.mkdir()

    (bin_dir / "gh").write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            case "$1" in
              auth) exit 0 ;;
              repo) echo '{"nameWithOwner":"org/mimir"}' ;;
              api)
                if [[ "$2" == *milestones* ]]; then
                  echo '{"state":"open","title":"Test Milestone","number":1,"open_issues":1}'
                fi
                ;;
              issue)
                if [[ "$2" == "list" ]]; then
                  echo '[{"number":1,"title":"Sample","body":"docs/features/act-test/sample.feature"}]'
                fi
                ;;
            esac
            exit 0
            """
        ),
        encoding="utf-8",
    )
    (bin_dir / "gh").chmod(0o755)

    for name in ("fswatch", "tmux", "rg", "curl"):
        (bin_dir / name).write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        (bin_dir / name).chmod(0o755)

    (bin_dir / "python3").write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            if [[ "$1" == *validate-feature-refs.py ]]; then exit 0; fi
            /usr/bin/python3 "$@"
            """
        ),
        encoding="utf-8",
    )
    (bin_dir / "python3").chmod(0o755)
    (bin_dir / "jq").write_text("#!/usr/bin/env bash\n/usr/bin/jq \"$@\"\n", encoding="utf-8")
    (bin_dir / "jq").chmod(0o755)
    (bin_dir / "cursor-agent").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (bin_dir / "cursor-agent").chmod(0o755)

    proc = run_script(
        "scripts/preflight.sh",
        "--allow-dirty",
        "--skip-staging-check",
        "Test Milestone",
        cwd=factory_repo,
        env={"PATH": f"{bin_dir}:/usr/bin:/bin"},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
