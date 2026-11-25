"""Exercise strict benchmark counters and owned evidence with real temporary files."""

from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

_RUNTIME = Path(__file__).resolve().parents[2] / "scripts/experts-staging"
_COUNTERS = "1024\n2048\nlow 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n"


def _load(name: str) -> ModuleType:
    """Load the real standard-library control module without executing its CLI."""
    spec = importlib.util.spec_from_file_location(name, _RUNTIME / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def metrics() -> ModuleType:
    """Use actual pure measurement parsing, without replacing a domain lifecycle."""
    return _load("benchmark_metrics")


def test_parse_memory_with_actual_counters_retains_exact_numeric_values(
    metrics: ModuleType,
) -> None:
    record = metrics.parse_memory(_COUNTERS, "browser", 2048)
    assert record == {
        "role": "browser",
        "peak_bytes": 1024,
        "limit_bytes": 2048,
        "events": {
            "low": 0,
            "high": 0,
            "max": 0,
            "oom": 0,
            "oom_kill": 0,
            "oom_group_kill": 0,
        },
    }
    metrics.require_headroom(record)


@pytest.mark.parametrize(
    "text",
    [
        "",
        _COUNTERS.replace("2048", "max"),
        _COUNTERS.replace("1024", "-1"),
        _COUNTERS.replace("1024", "2049"),
        _COUNTERS + "oom 0\n",
        _COUNTERS.replace("oom 0\n", ""),
        _COUNTERS + "secret token\n",
        _COUNTERS.replace("high 0", "high -1"),
        _COUNTERS.replace("1024", "True"),
    ],
)
def test_parse_memory_with_untrustworthy_counters_rejects_guessing(
    metrics: ModuleType, text: str
) -> None:
    with pytest.raises(ValueError):
        metrics.parse_memory(text, "web", 2048)


@pytest.mark.parametrize("role,limit", [("other", 2048), ("db", 4096), ("web", True)])
def test_parse_memory_with_wrong_role_or_limit_rejects(
    metrics: ModuleType, role: str, limit: Any
) -> None:
    with pytest.raises(ValueError):
        metrics.parse_memory(_COUNTERS, role, limit)


def test_read_memory_with_actual_files_observes_and_rejects_missing_counter(
    metrics: ModuleType, tmp_path: Path
) -> None:
    (tmp_path / "memory.peak").write_text("1024\n")
    (tmp_path / "memory.max").write_text("2048\n")
    (tmp_path / "memory.events").write_text("\n".join(_COUNTERS.splitlines()[2:]))
    assert metrics.read_memory(tmp_path, "db", 2048)["peak_bytes"] == 1024
    (tmp_path / "memory.peak").unlink()
    with pytest.raises((OSError, ValueError)):
        metrics.read_memory(tmp_path, "db", 2048)


@pytest.mark.parametrize("key", ["max", "oom", "oom_kill", "oom_group_kill"])
def test_require_headroom_with_exhaustion_events_rejects(
    metrics: ModuleType, key: str
) -> None:
    record = metrics.parse_memory(
        _COUNTERS.replace(key + " 0\n", key + " 1\n"), "db", 2048
    )
    with pytest.raises(ValueError):
        metrics.require_headroom(record)


def test_require_headroom_with_peak_at_limit_rejects(metrics: ModuleType) -> None:
    record = metrics.parse_memory(_COUNTERS.replace("1024", "2048"), "web", 2048)
    with pytest.raises(ValueError):
        metrics.require_headroom(record)


@pytest.fixture
def controls(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Wire actual standard-library modules only; do not replace Docker or the app."""
    for name in ("contract", "remote", "benchmark_metrics"):
        monkeypatch.setitem(sys.modules, name, _load(name))
    module = _load("benchmark_contract")
    monkeypatch.setitem(sys.modules, "benchmark_contract", module)
    return module


def test_validate_cache_with_exact_platform_and_digests_preserves_host_sizes(
    controls: ModuleType,
) -> None:
    rows = {
        role: {
            "Id": "sha256:" + "a" * 64,
            "RepoDigests": [reference],
            "Os": "linux",
            "Architecture": "amd64",
            "Size": 1234,
        }
        for role, reference in controls.IMAGES.items()
    }
    assert controls.validate_cache(rows) == {role: 1234 for role in rows}


@pytest.mark.parametrize(
    "field,value",
    [
        ("Architecture", "arm64"),
        ("Os", "windows"),
        ("Size", True),
        ("Size", 0),
        ("Id", "wrong"),
        ("RepoDigests", []),
    ],
)
def test_validate_cache_with_unproven_image_rejects(
    controls: ModuleType, field: str, value: Any
) -> None:
    rows = {
        role: {
            "Id": "sha256:" + "a" * 64,
            "RepoDigests": [reference],
            "Os": "linux",
            "Architecture": "amd64",
            "Size": 1234,
        }
        for role, reference in controls.IMAGES.items()
    }
    rows["web"][field] = value
    with pytest.raises(ValueError):
        controls.validate_cache(rows)


@pytest.mark.parametrize(
    "name",
    [
        "app.env",
        "tls/server.key",
        "pgdata/PG_VERSION",
        "browser-memory.json.env",
        "benchmark-notes.json",
        "screenshots/other.png",
    ],
)
def test_safe_export_with_private_or_unknown_file_rejects_before_copy(
    controls: ModuleType, tmp_path: Path, name: str
) -> None:
    source, target = tmp_path / "source", tmp_path / "public"
    source.mkdir()
    target.mkdir()
    path = source / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("DO_NOT_EXPORT")
    with pytest.raises(ValueError):
        controls.safe_export(source, target)
    assert not list(target.rglob("*"))


def test_safe_export_with_known_numeric_and_core_files_copies_original_bytes(
    controls: ModuleType, tmp_path: Path
) -> None:
    source, target = tmp_path / "source", tmp_path / "public"
    source.mkdir()
    target.mkdir()
    (source / "browser-memory.json").write_text('{"peak_bytes":1024}')
    (source / "health.json").write_text('{"status":"healthy"}')
    result = controls.safe_export(source, target)
    assert {row["path"] for row in result} == {"health.json", "browser-memory.json"}
    assert all(
        (source / row["path"]).read_bytes() == (target / row["path"]).read_bytes()
        for row in result
    )


@pytest.mark.parametrize("hardlink", [False, True])
def test_safe_export_with_linked_public_name_rejects(
    controls: ModuleType, tmp_path: Path, hardlink: bool
) -> None:
    source, target = tmp_path / "source", tmp_path / "public"
    source.mkdir()
    target.mkdir()
    secret = tmp_path / "private"
    secret.write_text("DO_NOT_EXPORT")
    if hardlink:
        (source / "health.json").hardlink_to(secret)
    else:
        (source / "health.json").symlink_to(secret)
    with pytest.raises(ValueError):
        controls.safe_export(source, target)


def test_read_json_with_array_or_symlink_rejects(
    controls: ModuleType, tmp_path: Path
) -> None:
    path = tmp_path / "input.json"
    path.write_text("[]")
    with pytest.raises(ValueError):
        controls.read_json(path)
    path.unlink()
    path.symlink_to(tmp_path / "other.json")
    with pytest.raises(ValueError):
        controls.read_json(path)


@pytest.fixture
def driver(controls: ModuleType, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load the real driver after actual control dependencies are wired."""
    return _load("benchmark")


def _plan(controls: ModuleType) -> dict[str, Any]:
    """Construct public selectors for pure validation, never a deployment receipt."""
    return {
        "status": "PREPARED_SOURCE_ONLY_NOT_DEPLOYED",
        "nonce": "a" * 32,
        "account": controls.ACCOUNT,
        "bucket": f"elasticbeanstalk-us-east-1-{controls.ACCOUNT}",
        "source_revision": controls.SOURCE,
        "runner_revision": "b" * 40,
        "build_run_id": controls.BUILD,
        "build_receipt": {},
        "web_image": controls.IMAGES["web"],
        "fixture_sha256": "c" * 64,
    }


@pytest.mark.parametrize(
    "key,value",
    [
        ("account", "000000000000"),
        ("source_revision", "b" * 40),
        ("build_run_id", "1"),
        ("web_image", "mimir:latest"),
        ("bucket", "foreign"),
        ("status", "PASS"),
        ("nonce", "../../other"),
        ("extra", "private"),
    ],
)
def test_validate_plan_shape_with_wrong_or_extended_selectors_rejects(
    controls: ModuleType, key: str, value: Any
) -> None:
    plan = _plan(controls)
    plan[key] = value
    with pytest.raises(ValueError):
        controls.validate_plan_shape(
            plan, {"source_revision": controls.SOURCE, "files": {}}
        )


def test_validate_plan_shape_with_fixed_selectors_accepts_source_only(
    controls: ModuleType,
) -> None:
    controls.validate_plan_shape(
        _plan(controls), {"source_revision": controls.SOURCE, "files": {}}
    )


@pytest.mark.parametrize("rows", [{}, {"web": {}}, {"unexpected": {}}])
def test_validate_cache_with_partial_inventory_rejects(
    controls: ModuleType, rows: dict[str, Any]
) -> None:
    with pytest.raises(ValueError):
        controls.validate_cache(rows)


def test_reviewed_bytes_with_actual_git_commit_rejects_uncommitted_change(
    controls: ModuleType, tmp_path: Path
) -> None:

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    source = tmp_path / "control.py"
    source.write_text("verified = True\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "control.py"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Benchmark",
            "-c",
            "user.email=benchmark@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    assert controls.reviewed_bytes(tmp_path, source) == b"verified = True\n"
    source.write_text("verified = False\n")
    with pytest.raises(ValueError):
        controls.reviewed_bytes(tmp_path, source)


def test_safe_export_with_existing_target_refuses_overwrite(
    controls: ModuleType, tmp_path: Path
) -> None:
    source, target = tmp_path / "source", tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / "health.json").write_text("new")
    (target / "health.json").write_text("original")
    with pytest.raises(FileExistsError):
        controls.safe_export(source, target)
    assert (target / "health.json").read_text() == "original"


def test_safe_export_with_sparse_oversized_file_rejects_before_copy(
    controls: ModuleType, tmp_path: Path
) -> None:
    source, target = tmp_path / "source", tmp_path / "target"
    source.mkdir()
    target.mkdir()
    with (source / "browser-trace.zip").open("wb") as stream:
        stream.truncate(128 * 1024 * 1024 + 1)
    with pytest.raises(ValueError):
        controls.safe_export(source, target)
    assert not list(target.iterdir())


def test_publish_owner_with_world_readable_or_unknown_entry_rejects(
    controls: ModuleType, tmp_path: Path
) -> None:
    output = tmp_path / "public"
    output.mkdir(mode=0o700)
    (output / "health.json").write_text("{}")
    with pytest.raises(ValueError):
        controls.publish_owner(output)
    (output / "health.json").chmod(0o600)
    controls.publish_owner(output)
    (output / "unknown").write_text("private")
    with pytest.raises(ValueError):
        controls.publish_owner(output)


@pytest.mark.parametrize("web_memory", [384, 256])
def test_select_envelope_with_explicit_experiment_changes_only_process_web_memory(
    driver: ModuleType, web_memory: int
) -> None:
    before = dict(driver.remote._LIMITS)
    original_bytes = (_RUNTIME / "remote.py").read_bytes()
    result = {}
    driver.select_envelope(web_memory, result)
    assert driver.remote._LIMITS["web"] == (web_memory, *before["web"][1:])
    assert {role: driver.remote._LIMITS[role] for role in ("db", "browser")} == {
        role: before[role] for role in ("db", "browser")
    }
    assert result["idle_guard_mib"] == 1400 and result["host_reserve_mib"] == 256
    assert result["experiment"] == (
        "DEFAULT_384" if web_memory == 384 else "EXPERIMENT_256"
    )
    assert (_RUNTIME / "remote.py").read_bytes() == original_bytes


@pytest.mark.parametrize("value", [True, 128, 192, 512, "256"])
def test_select_envelope_with_unsupported_choice_rejects(
    driver: ModuleType, value: Any
) -> None:
    with pytest.raises(ValueError):
        driver.select_envelope(value, {})


def _state(role: str = "web") -> dict[str, Any]:
    """Representative safe numeric Docker observations for the pure validator."""
    memory = {"web": 384, "db": 192, "browser": 512}[role] * 1024 * 1024
    return {
        "role": role,
        "oom_killed": False,
        "restarts": 0,
        "memory_bytes": memory,
        "swap_bytes": memory,
        "nano_cpus": {"web": 750000000, "db": 250000000, "browser": 1000000000}[role],
        "pids": 256 if role == "browser" else 128,
        "read_only": True,
        "cap_drop": ["ALL"],
        "security_options": ["no-new-privileges"],
        "running": role != "browser",
        "exit_code": 0,
    }


@pytest.mark.parametrize(
    "key,value",
    [
        ("oom_killed", True),
        ("restarts", 1),
        ("memory_bytes", 256),
        ("swap_bytes", -1),
        ("nano_cpus", 0),
        ("pids", 0),
        ("read_only", False),
        ("cap_drop", []),
        ("security_options", []),
        ("running", False),
    ],
)
def test_validate_container_state_with_unsafe_real_observation_rejects(
    driver: ModuleType, key: str, value: Any
) -> None:
    state = _state()
    state[key] = value
    with pytest.raises(ValueError):
        driver.validate_container_state(state)


@pytest.mark.parametrize("role", ["web", "db", "browser"])
def test_validate_container_state_with_expected_limits_accepts(
    driver: ModuleType, role: str
) -> None:
    driver.validate_container_state(_state(role))


def test_validate_container_state_with_nonzero_browser_status_rejects(
    driver: ModuleType,
) -> None:
    state = _state("browser")
    state["exit_code"] = 1
    with pytest.raises(ValueError):
        driver.validate_container_state(state)


def test_browser_text_with_extra_or_nonnumeric_fields_rejects(
    driver: ModuleType,
) -> None:
    record = {
        "role": "browser",
        "peak_bytes": 1024,
        "limit_bytes": 2048,
        "events": {"oom": 0},
        "driver_passed": True,
    }
    assert driver.browser_text(record).startswith("1024\n2048\n")
    record["peak_bytes"] = True
    with pytest.raises(ValueError):
        driver.browser_text(record)
    record["peak_bytes"] = 1024
    record["private"] = "must not export"
    with pytest.raises(ValueError):
        driver.browser_text(record)


def test_driver_with_actual_cli_wrong_host_or_user_emits_safe_failure_without_allocating(
    tmp_path: Path,
) -> None:

    output = tmp_path / "public"
    completed = subprocess.run(
        [
            sys.executable,
            str(_RUNTIME / "benchmark.py"),
            "--prepared-output",
            str(tmp_path / "missing"),
            "--web-memory-mib",
            "384",
            "--output",
            str(output),
        ],
        env={},
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 1
    result = json.loads((output / "benchmark-result.json").read_text())
    assert result["status"] == "FAILED" and result["cleanup"] == "NOT_ALLOCATED"
    assert result["exception_class"] == "ValueError"
    assert result["staging_accepted"] is False and result["uat_accepted"] is False
    assert "stderr" not in result and "Traceback" not in completed.stdout


def test_finish_with_foreign_root_preserves_private_bytes_and_reports_failed_cleanup(
    driver: ModuleType, tmp_path: Path
) -> None:
    root, public = tmp_path / "foreign", tmp_path / "public"
    (root / "output").mkdir(parents=True)
    public.mkdir(mode=0o700)
    (root / "app.env").write_text("DO_NOT_EXPORT_SECRET")
    (root / "output/health.json").write_text('{"status":"healthy"}')
    result = {"status": "FAILED", "private_root_removed": False}
    driver.finish(root, "a" * 32, {}, public, result)
    assert result["cleanup"] == "FAILED" and result["cleanup_exception"] == "ValueError"
    assert result["export"] == "SUCCESS" and result["private_root_removed"] is False
    assert (root / "app.env").read_text() == "DO_NOT_EXPORT_SECRET"
    assert {p.name for p in public.iterdir()} == {"health.json"}
    assert "DO_NOT_EXPORT_SECRET" not in json.dumps(result)


def test_validate_measurements_with_partial_or_failed_driver_rejects(
    driver: ModuleType,
) -> None:
    memory = {
        "peak_bytes": 1024,
        "limit_bytes": 2048,
        "events": {"max": 0, "oom": 0, "oom_kill": 0},
    }
    rows = {
        role: {"memory": {**memory, "role": role}, "docker": _state(role)}
        for role in ("web", "db", "browser")
    }
    rows["browser"]["memory"]["driver_passed"] = True
    driver.validate_measurements({"roles": rows})
    rows["browser"]["memory"]["driver_passed"] = False
    with pytest.raises(ValueError):
        driver.validate_measurements({"roles": rows})
    rows["browser"] = {"measurement_exception": "FileNotFoundError"}
    with pytest.raises(ValueError):
        driver.validate_measurements({"roles": rows})


def test_failure_with_private_exception_text_exports_only_safe_class(
    driver: ModuleType,
) -> None:
    assert driver.failure(RuntimeError("DATABASE_URL=DO_NOT_EXPORT")) == "RuntimeError"
    assert driver.failure(Exception("DO_NOT_EXPORT")) == "Exception"


def test_observer_and_driver_with_reviewed_source_preserve_real_browser_and_cleanup() -> (
    None
):
    observer = ast.parse((_RUNTIME / "benchmark_observer.py").read_text())
    driver_tree = ast.parse((_RUNTIME / "benchmark.py").read_text())
    calls = [ast.unparse(n.func) for n in ast.walk(observer) if isinstance(n, ast.Call)]
    assert calls.count("browser.main") == 1
    assert any(isinstance(n, ast.Try) and n.finalbody for n in ast.walk(observer))
    forbidden = {
        "pull_images",
        "bounded_pull",
        "upload_evidence",
        "archive_evidence",
        "finish_owned_run",
    }
    assert not [
        n
        for n in ast.walk(driver_tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr in forbidden
    ]
    source = (_RUNTIME / "benchmark.py").read_text()
    assert "measure_and_finish(root, nonce, names, output, result)" in source
    assert 'os.environ["DOCKER_CONFIG"] = str(root / "docker-config")' in source


def test_benchmark_workflow_with_manual_only_branch_has_no_deployment_or_ssm() -> None:
    workflow = yaml.safe_load(
        (_RUNTIME.parents[1] / ".github/workflows/build-and-deploy.yml").read_text()
    )
    trigger = workflow.get("on", workflow.get(True))
    assert set(trigger) == {"workflow_dispatch"}
    choice = trigger["workflow_dispatch"]["inputs"]["web_memory_mib"]
    assert choice["default"] == "384" and choice["options"] == ["384", "256"]
    assert set(workflow["jobs"]) == {"benchmark"}
    job = workflow["jobs"]["benchmark"]
    assert "github.event_name == 'workflow_dispatch'" in job["if"]
    assert "refs/heads/diagnostics/experts-linux-memory-benchmark-20261125" in job["if"]
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert "sudo /usr/bin/env -i /usr/bin/python3" in commands
    assert not any(
        word in commands
        for word in (
            "send-command",
            "eb deploy",
            "controller.py execute",
            "aws rds",
            "docker system prune",
        )
    )


def test_safe_export_with_container_supplied_host_result_rejects(
    controls: ModuleType, tmp_path: Path
) -> None:
    source, public = tmp_path / "source", tmp_path / "public"
    source.mkdir()
    public.mkdir()
    (source / "benchmark-result.json").write_text('{"status":"PASS"}')
    with pytest.raises(ValueError):
        controls.safe_export(source, public)
    assert not list(public.iterdir())


def test_publish_result_with_unsafe_extra_entry_retains_safe_failure(
    driver: ModuleType, tmp_path: Path
) -> None:
    public = tmp_path / "public"
    public.mkdir(mode=0o700)
    (public / "private.env").write_text("DO_NOT_EXPORT")
    result = {
        "status": "MEASURED_CORE_ONLY_NOT_STAGING_ACCEPTANCE",
        "cleanup": "SUCCESS",
    }
    driver.publish_result(public, result)
    recorded = json.loads((public / "benchmark-result.json").read_text())
    assert recorded["status"] == "FAILED" and recorded["public_ownership"] == "FAILED"
    assert recorded["publication_exception"] == "ValueError"
    assert "DO_NOT_EXPORT" not in json.dumps(recorded)
