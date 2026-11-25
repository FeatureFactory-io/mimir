"""Exercise strict benchmark counters and owned evidence with real temporary files."""

from __future__ import annotations

import ast
import importlib.util
import json
import os
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
    spec = importlib.util.spec_from_file_location(
        "aggregate", _RUNTIME / "aggregate.py"
    )
    assert spec and spec.loader
    actual = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "aggregate", actual)
    spec.loader.exec_module(actual)
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
    assert "measure_and_finish(root, nonce, names, output, result, owner)" in source
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


def test_host_observations_with_actual_numeric_rows_survives_extra_private_fields(
    metrics: ModuleType,
) -> None:
    record = metrics.parse_memory(_COUNTERS, "db", 2048)
    measured = {
        "roles": {
            "db": {
                "memory": record,
                "docker": {**_state("db"), "private": "DO_NOT_EXPORT"},
            },
            "web": {
                "measurement_exception": "RuntimeError",
                "measurement_reason": "UNCLASSIFIED",
            },
            "browser": {
                "measurement_exception": "ValueError",
                "measurement_reason": "INPUT_PATH_REJECTED",
            },
        }
    }
    published = metrics.host_observations(measured)
    assert published["roles"]["db"]["memory"] == record
    assert published["roles"]["db"]["docker"]["memory_bytes"] == 192 * 1024 * 1024
    assert "DO_NOT_EXPORT" not in json.dumps(published)
    assert published["roles"]["browser"]["measurement_reason"] == "INPUT_PATH_REJECTED"


def test_failure_reason_with_known_and_arbitrary_messages_exports_closed_enums(
    metrics: ModuleType,
) -> None:
    assert (
        metrics.failure_reason(ValueError("Unknown evidence directory."))
        == "EXPORT_DIRECTORY_REJECTED"
    )
    assert (
        metrics.failure_reason(ValueError("Actual role measurement is incomplete."))
        == "ROLE_MEASUREMENT_INCOMPLETE"
    )
    assert metrics.failure_reason(RuntimeError("SECRET_DATABASE_URL")) == "UNCLASSIFIED"
    assert (
        metrics.failure_reason(FileNotFoundError("PRIVATE_PATH")) == "FILE_UNAVAILABLE"
    )


def test_finish_with_rejected_export_preserves_closed_reason_without_secret_name(
    driver: ModuleType, tmp_path: Path
) -> None:
    root, public = tmp_path / "foreign", tmp_path / "public"
    (root / "output").mkdir(parents=True)
    public.mkdir(mode=0o700)
    (root / "output/PRIVATE_SECRET_NAME.env").write_text("SECRET_CONTENT")
    result = {"status": "FAILED", "observations": {"retained": True}}
    driver.finish(root, "a" * 32, {}, public, result)
    assert result["export_reason"] == "EXPORT_MEMBER_REJECTED"
    assert result["observations"] == {"retained": True}
    assert "PRIVATE_SECRET_NAME" not in json.dumps(
        result
    ) and "SECRET_CONTENT" not in json.dumps(result)
    assert result["export_rejected_shapes"] == [
        {
            "top_category": "root_file",
            "kind": "file",
            "depth": 1,
            "extension": "other",
            "rejections": ["NAME_PATTERN_MISMATCH"],
        }
    ]
    assert not list(public.iterdir())


def test_browser_failure_with_actual_traceback_exports_only_known_source_frame(
    metrics: ModuleType,
) -> None:
    source = _RUNTIME / "browser.py"
    first_line = metrics.browser_ranges(source)["capture"][0]
    text = (
        "\n" * (first_line - 1)
        + 'def capture():\n    raise AssertionError("SECRET_CONTENT")\ncapture()\n'
    )
    code = compile(text, str(source), "exec")
    try:
        exec(code, {})  # noqa: S102 - fixed literal constructs a real traceback.
    except AssertionError as error:
        record = metrics.browser_failure(error, source)
    assert record["exception_class"] == "AssertionError"
    assert record["source_frames"] == [{"function": "capture", "line": first_line + 1}]
    assert "SECRET_CONTENT" not in json.dumps(record) and str(source) not in json.dumps(
        record
    )
    assert metrics.validate_browser_failure(record) == record


@pytest.mark.parametrize(
    "field,value",
    [
        ("exception_class", "SECRET_CONTENT"),
        ("private_output_exported", True),
        ("extra", "SECRET_CONTENT"),
        ("source_frames", [{"function": "private_function", "line": 1}]),
    ],
)
def test_validate_browser_failure_with_untrusted_fields_rejects(
    metrics: ModuleType, field: str, value: Any
) -> None:
    record = {
        "status": "FAILED",
        "exception_class": "AssertionError",
        "source_frames": [],
        "private_output_exported": False,
    }
    record[field] = value
    with pytest.raises(ValueError):
        metrics.validate_browser_failure(record)


@pytest.mark.parametrize("line", [True, 0, -1, 1, 1000, 1001, "60"])
def test_validate_browser_frame_with_wrong_type_or_function_range_rejects(
    metrics: ModuleType, line: Any
) -> None:
    with pytest.raises(ValueError):
        metrics.validate_browser_frame({"function": "capture", "line": line})


def test_read_browser_diagnostic_with_link_or_extra_private_fields_rejects(
    driver: ModuleType, tmp_path: Path
) -> None:
    output = tmp_path / "output"
    output.mkdir()
    source = tmp_path / "PRIVATE_SECRET_NAME.json"
    source.write_text('{"private":"SECRET_CONTENT"}')
    diagnostic = output / "browser-diagnostic.json"
    diagnostic.symlink_to(source)
    linked = driver.read_browser_diagnostic(tmp_path)
    assert linked["status"] == "REJECTED" and linked["reason"] == "INPUT_PATH_REJECTED"
    diagnostic.unlink()
    diagnostic.write_text(source.read_text())
    invalid = driver.read_browser_diagnostic(tmp_path)
    assert invalid["reason"] == "BROWSER_DIAGNOSTIC_REJECTED"
    assert "PRIVATE_SECRET_NAME" not in json.dumps(
        invalid
    ) and "SECRET_CONTENT" not in json.dumps(invalid)


@pytest.mark.parametrize(
    "field,value",
    [
        ("memory_bytes", "SECRET_CONTENT"),
        ("pids", True),
        ("restarts", -1),
        ("exit_code", 2**64),
    ],
)
def test_host_docker_with_invalid_numeric_fields_omits_without_guessing(
    metrics: ModuleType, field: str, value: Any
) -> None:
    state = _state()
    state[field] = value
    state["private"] = "SECRET_CONTENT"
    result = metrics.host_docker(state)
    assert field not in result and "private" not in result
    assert "SECRET_CONTENT" not in json.dumps(result)


def test_host_observations_with_private_event_names_rejects_record(
    metrics: ModuleType,
) -> None:
    memory = metrics.parse_memory(_COUNTERS, "db", 2048)
    memory["events"]["PRIVATE_SECRET_NAME"] = 0
    result = metrics.host_observations({"roles": {"db": {"memory": memory}}})
    assert result["roles"]["db"] == {"measurement_reason": "OBSERVATION_REJECTED"}
    assert "PRIVATE_SECRET_NAME" not in json.dumps(result)


def test_rejected_export_shapes_with_many_unknown_members_is_closed_and_bounded(
    controls: ModuleType, tmp_path: Path
) -> None:
    for index in range(20):
        (tmp_path / f"PRIVATE_SECRET_NAME_{index}.json").write_text("SECRET_CONTENT")
    shapes = controls.rejected_export_shapes(tmp_path)
    assert len(shapes) == 16
    assert all(
        row
        == {
            "top_category": "root_file",
            "kind": "file",
            "depth": 1,
            "extension": "json",
            "rejections": ["NAME_PATTERN_MISMATCH"],
        }
        for row in shapes
    )
    assert "PRIVATE_SECRET_NAME" not in json.dumps(
        shapes
    ) and "SECRET_CONTENT" not in json.dumps(shapes)


def test_export_public_with_actual_numeric_host_data_and_rejected_member_preserves_data(
    driver: ModuleType, metrics: ModuleType, tmp_path: Path
) -> None:
    root, public = tmp_path / "owned", tmp_path / "public"
    (root / "output").mkdir(parents=True)
    public.mkdir()
    (root / "output/PRIVATE_SECRET_NAME.env").write_text("SECRET_CONTENT")
    memory = metrics.parse_memory(_COUNTERS, "db", 2048)
    result = {
        "status": "FAILED",
        "observations": metrics.host_observations(
            {"roles": {"db": {"memory": memory}}}
        ),
    }
    driver.export_public(root, public, result)
    assert (
        result["export"] == "FAILED"
        and result["export_reason"] == "EXPORT_MEMBER_REJECTED"
    )
    assert result["observations"]["roles"]["db"]["memory"] == memory
    driver.publish_result(public, result)
    saved = json.loads((public / "benchmark-result.json").read_text())
    assert saved["observations"] == result["observations"]
    assert "PRIVATE_SECRET_NAME" not in json.dumps(
        saved
    ) and "SECRET_CONTENT" not in json.dumps(saved)
    assert {p.name for p in public.iterdir()} == {"benchmark-result.json"}


def test_export_public_with_independently_rejected_diagnostic_blocks_all_mixed_files(
    driver: ModuleType, tmp_path: Path
) -> None:
    root, public = tmp_path / "owned", tmp_path / "public"
    (root / "output").mkdir(parents=True)
    public.mkdir()
    invalid = {
        "status": "FAILED",
        "exception_class": "AssertionError",
        "source_frames": [],
        "private_output_exported": False,
        "private": "INDEPENDENT_PRIVATE_SENTINEL",
    }
    original = json.dumps(invalid).encode()
    (root / "output/browser-diagnostic.json").write_bytes(original)
    (root / "output/health.json").write_text('{"status":"healthy"}')
    result = {"status": "FAILED", "observations": {"actual_numeric_control": 1024}}
    result["browser_diagnostic"] = driver.read_browser_diagnostic(root)
    assert result["browser_diagnostic"]["status"] == "REJECTED"
    driver.export_public(root, public, result)
    assert result["export"] == "FAILED"
    assert not list(public.iterdir())
    assert (root / "output/browser-diagnostic.json").read_bytes() == original
    assert "INDEPENDENT_PRIVATE_SENTINEL" not in json.dumps(result)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"status":"FAILED","exception_class":"PRIVATE_SENTINEL","exception_class":"AssertionError","source_frames":[],"private_output_exported":false}',
        b'{"status":"FAILED","exception_class":"AssertionError","source_frames":"PRIVATE_SENTINEL","source_frames":[],"private_output_exported":false}',
        b'{"status":"FAILED","exception_cl\\u0061ss":"AssertionError","source_frames":[],"private_output_exported":false}',
        b'{"status":"FAILED","exception_class":"AssertionError","source_frames":[],"private_output_exported":false} PRIVATE_SENTINEL',
        b'{"status":"FAILED","exception_class":"AssertionError","source_frames":[],"private_output_exported":false,"private":"\\u0050RIVATE_SENTINEL"}',
    ],
)
def test_safe_export_with_hidden_or_noncanonical_diagnostic_rejects_before_copy(
    controls: ModuleType, tmp_path: Path, raw: bytes
) -> None:
    source, public = tmp_path / "source", tmp_path / "public"
    source.mkdir()
    public.mkdir()
    (source / "benchmark-source.json").write_text("{}")
    (source / "health.json").write_text("{}")
    (source / "browser-diagnostic.json").write_bytes(raw)
    with pytest.raises((ValueError, UnicodeError)):
        controls.safe_export(source, public)
    assert not list(public.iterdir())
    assert (source / "browser-diagnostic.json").read_bytes() == raw


def test_safe_export_with_actual_observer_writer_bytes_copies_original_canonical_failure(
    controls: ModuleType, metrics: ModuleType, driver: ModuleType, tmp_path: Path
) -> None:
    root, public = tmp_path / "owned", tmp_path / "public"
    (root / "output").mkdir(parents=True)
    public.mkdir()
    try:
        raise AssertionError("PRIVATE_ERROR_MESSAGE")
    except AssertionError as error:
        record = metrics.browser_failure(error, _RUNTIME / "browser.py")
    path = root / "output/browser-diagnostic.json"
    metrics.write_browser_diagnostic(path, record)
    raw = path.read_bytes()
    assert (
        raw == metrics.browser_diagnostic_bytes(record)
        and "PRIVATE_ERROR_MESSAGE" not in raw.decode()
    )
    assert driver.read_browser_diagnostic(root) == record
    (root / "output/benchmark-source.json").write_text('{"source":"public-control"}')
    result = {"status": "FAILED", "observations": {"numeric_control": 1024}}
    driver.export_public(root, public, result)
    assert result["export"] == "SUCCESS" and result["status"] == "FAILED"
    assert (public / "browser-diagnostic.json").read_bytes() == raw
    assert result["observations"] == {"numeric_control": 1024}
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    "mutation",
    [
        "class_bool",
        "class_unknown",
        "line_bool",
        "line_outside_function",
        "frame_extra",
        "frames_21",
        "root_extra",
    ],
)
def test_safe_export_with_typed_schema_or_frame_violation_rejects_all_mixed_members(
    controls: ModuleType, metrics: ModuleType, tmp_path: Path, mutation: str
) -> None:
    source, public = tmp_path / "source", tmp_path / "public"
    source.mkdir()
    public.mkdir()
    record = _invalid_diagnostic(metrics, mutation)
    (source / "browser-diagnostic.json").write_text(
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    )
    (source / "benchmark-source.json").write_text("{}")
    with pytest.raises(ValueError):
        controls.safe_export(source, public)
    assert not list(public.iterdir())


@pytest.mark.parametrize("variant", ["trailing_space", "bom", "utf16", "oversized"])
def test_parse_browser_diagnostic_with_noncanonical_encoding_or_size_rejects(
    metrics: ModuleType, variant: str
) -> None:
    record = {
        "status": "FAILED",
        "exception_class": "AssertionError",
        "private_output_exported": False,
        "source_frames": [],
    }
    raw = metrics.browser_diagnostic_bytes(record)
    raw = {
        "trailing_space": raw + b" ",
        "bom": b"\xef\xbb\xbf" + raw,
        "utf16": raw.decode().encode("utf-16"),
        "oversized": raw + b" " * metrics.MAX_DIAGNOSTIC_BYTES,
    }[variant]
    with pytest.raises(ValueError):
        metrics.parse_browser_diagnostic(raw)


def test_diagnostic_snapshot_with_later_private_overwrite_copies_only_admitted_bytes(
    controls: ModuleType, metrics: ModuleType, tmp_path: Path
) -> None:
    source, public = tmp_path / "source", tmp_path / "public"
    source.mkdir()
    public.mkdir()
    path = source / "browser-diagnostic.json"
    record = {
        "status": "FAILED",
        "exception_class": "AssertionError",
        "private_output_exported": False,
        "source_frames": [],
    }
    metrics.write_browser_diagnostic(path, record)
    snapshot = controls.diagnostic_snapshots(controls.checked_export_files(source))[
        path
    ]
    path.write_text('{"private":"PRIVATE_SENTINEL"}')
    controls.copy_public_file(path, public, Path("browser-diagnostic.json"), snapshot)
    assert (public / path.name).read_bytes() == snapshot
    assert "PRIVATE_SENTINEL" not in (public / path.name).read_text()
    next_public = tmp_path / "next-public"
    next_public.mkdir()
    with pytest.raises(ValueError):
        controls.safe_export(source, next_public)
    assert not list(next_public.iterdir())


def _invalid_diagnostic(metrics: ModuleType, mutation: str) -> dict[str, Any]:
    """Construct one schema/frame counterexample for pre-copy admission."""
    record = {
        "status": "FAILED",
        "exception_class": "AssertionError",
        "private_output_exported": False,
        "source_frames": [
            {
                "function": "capture",
                "line": metrics.browser_ranges(_RUNTIME / "browser.py")["capture"][0],
            }
        ],
    }
    if mutation.startswith("class"):
        record["exception_class"] = (
            True if mutation == "class_bool" else "PRIVATE_SENTINEL"
        )
    elif mutation == "frames_21":
        record["source_frames"] *= 21
    elif mutation == "root_extra":
        record["private"] = "PRIVATE_SENTINEL"
    elif mutation == "frame_extra":
        record["source_frames"][0]["private"] = "PRIVATE_SENTINEL"
    else:
        record["source_frames"][0]["line"] = True if mutation == "line_bool" else 1
    return record


@pytest.mark.parametrize("mib", [512, 768])
def test_browser_memory_bytes_with_closed_diagnostic_choice_returns_exact_cap(
    metrics: ModuleType, mib: int
) -> None:
    assert metrics.browser_memory_bytes(mib) == mib * 1024 * 1024


@pytest.mark.parametrize("value", [True, 0, 256, 1024, "768", 768.0])
def test_browser_memory_bytes_with_unreviewed_or_wrongly_typed_choice_rejects(
    metrics: ModuleType, value: Any
) -> None:
    with pytest.raises(ValueError):
        metrics.browser_memory_bytes(value)


@pytest.mark.parametrize("browser_memory", [512, 768])
def test_select_envelope_with_browser_experiment_changes_only_local_browser_cap(
    driver: ModuleType, browser_memory: int
) -> None:
    before = dict(driver.remote._LIMITS)
    source = (_RUNTIME / "remote.py").read_bytes()
    result = {}
    driver.select_envelope(384, result, browser_memory=browser_memory)
    assert driver.remote._LIMITS["browser"] == (browser_memory, *before["browser"][1:])
    assert (
        driver.remote._LIMITS["db"] == before["db"]
        and driver.remote._LIMITS["web"] == before["web"]
    )
    assert (
        result["browser_memory_mib"] == browser_memory
        and result["host_reserve_mib"] == 256
    )
    assert result["idle_guard_mib"] == 1400 and result["scope"] == "DISPOSABLE_CI_ONLY"
    assert (_RUNTIME / "remote.py").read_bytes() == source


def test_observed_browser_arguments_with_768_experiment_binds_docker_and_observer_cap(
    driver: ModuleType, tmp_path: Path
) -> None:
    driver.select_envelope(384, {}, browser_memory=768)
    nonce = "a" * 32
    command = driver.observed_browser_arguments(
        tmp_path,
        {"nonce": nonce, "browser_image": "fixed-image"},
        driver.remote.resource_names(nonce),
    )
    assert command[command.index("--memory") + 1] == "768m"
    assert command[command.index("--memory-swap") + 1] == "768m"
    assert command[-3:] == [
        "/runtime/benchmark_observer.py",
        "--browser-memory-mib",
        "768",
    ]


def test_export_rejection_with_real_regular_name_mismatch_and_hardlink_distinguishes_closed_kinds(
    controls: ModuleType, tmp_path: Path
) -> None:
    video = tmp_path / "video"
    video.mkdir()
    unknown = video / "PRIVATE_NAME.webm"
    unknown.write_text("PRIVATE_CONTENT")
    assert controls.export_rejection_kinds(
        unknown, Path("video/PRIVATE_NAME.webm")
    ) == ["NAME_PATTERN_MISMATCH"]
    known = video / ("a" * 32 + ".webm")
    known.hardlink_to(unknown)
    assert controls.export_rejection_kinds(known, Path("video") / known.name) == [
        "HARDLINK_COUNT_NOT_ONE"
    ]
    rows = controls.rejected_export_shapes(tmp_path)
    assert all("rejections" in row for row in rows)
    assert "PRIVATE_NAME" not in json.dumps(
        rows
    ) and "PRIVATE_CONTENT" not in json.dumps(rows)


def test_benchmark_arguments_with_default_and_explicit_browser_choice_are_closed(
    driver: ModuleType, tmp_path: Path
) -> None:
    argv = [
        "--prepared-output",
        str(tmp_path),
        "--web-memory-mib",
        "384",
        "--output",
        str(tmp_path / "new"),
    ]
    assert driver.arguments(argv).browser_memory_mib == 512
    assert (
        driver.arguments([*argv, "--browser-memory-mib", "768"]).browser_memory_mib
        == 768
    )
    with pytest.raises(SystemExit):
        driver.arguments([*argv, "--browser-memory-mib", "1024"])


@pytest.mark.parametrize("mib", [512, 768])
def test_observer_memory_choice_with_explicit_closed_option_matches_enforced_cap(
    metrics: ModuleType, mib: int
) -> None:
    assert metrics.observer_memory_choice(["--browser-memory-mib", str(mib)]) == mib
    assert metrics.observer_memory_choice([]) == 512


def test_observer_memory_choice_with_unreviewed_option_rejects(
    metrics: ModuleType,
) -> None:
    with pytest.raises(SystemExit):
        metrics.observer_memory_choice(["--browser-memory-mib", "1024"])


@pytest.mark.parametrize(
    "actual,selected", [(512, 512), (768, 768), (512, 768), (768, 512)]
)
def test_browser_counter_parsing_with_selected_enforced_cap_rejects_mismatch(
    metrics: ModuleType, actual: int, selected: int
) -> None:
    text = _COUNTERS.replace("2048", str(actual * 1024 * 1024))
    if actual != selected:
        with pytest.raises(ValueError):
            metrics.parse_memory(
                text, "browser", metrics.browser_memory_bytes(selected)
            )
    else:
        assert (
            metrics.parse_memory(
                text, "browser", metrics.browser_memory_bytes(selected)
            )["limit_bytes"]
            == actual * 1024 * 1024
        )


@pytest.mark.parametrize("browser_memory,required", [(512, 1400), (768, 1600)])
def test_require_ci_capacity_with_larger_cap_preserves_full_256mib_reserve(
    driver: ModuleType, browser_memory: int, required: int
) -> None:
    driver.select_envelope(384, {}, browser_memory=browser_memory)
    driver.require_ci_capacity(required * 1024 * 1024)
    with pytest.raises(ValueError):
        driver.require_ci_capacity(required * 1024 * 1024 - 1)
    with pytest.raises(ValueError):
        driver.require_ci_capacity(True)


def test_observer_source_with_dynamic_choice_checks_actual_cgroup_limit_and_no_ambient_env() -> (
    None
):
    tree = ast.parse((_RUNTIME / "benchmark_observer.py").read_text())
    functions = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    main_calls = [
        ast.unparse(node)
        for node in ast.walk(functions["main"])
        if isinstance(node, ast.Call)
    ]
    assert (
        "observer_memory_choice()" in main_calls
        and "observe(passed, memory_mib)" in main_calls
    )
    observed = [
        ast.unparse(node)
        for node in ast.walk(functions["observe"])
        if isinstance(node, ast.Call)
    ]
    assert "browser_memory_bytes(memory_mib)" in observed
    assert not [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in {"getenv", "environ"}
    ]


def test_export_rejection_kinds_with_symlink_fifo_directory_and_alias_preserves_closed_metadata(
    controls: ModuleType, tmp_path: Path
) -> None:
    regular = tmp_path / ("a" * 32 + ".webm")
    regular.write_text("PRIVATE_CONTENT")
    linked = tmp_path / "PRIVATE_LINK.webm"
    linked.symlink_to(regular)
    assert controls.export_rejection_kinds(linked, Path("video/PRIVATE_LINK.webm")) == [
        "SYMLINK"
    ]
    fifo = tmp_path / "PRIVATE_FIFO.webm"
    os.mkfifo(fifo)
    assert controls.export_rejection_kinds(fifo, Path("video/PRIVATE_FIFO.webm")) == [
        "FILE_TYPE_NOT_REGULAR"
    ]
    directory = tmp_path / "PRIVATE_DIRECTORY"
    directory.mkdir()
    assert controls.export_rejection_kinds(directory, Path("PRIVATE_DIRECTORY")) == [
        "DIRECTORY_NOT_ADMITTED"
    ]
    actual = tmp_path / "actual"
    actual.mkdir()
    target = actual / ("b" * 32 + ".webm")
    target.write_text("PRIVATE_CONTENT")
    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    assert controls.export_rejection_kinds(
        alias / target.name, Path("video") / target.name
    ) == ["PATH_ALIAS"]
    assert controls.export_rejection_kinds(regular, Path("video") / regular.name) == []


@pytest.mark.parametrize("prefix", ["", "page@"])
def test_allowed_evidence_name_with_closed_native_video_forms_accepts_actual_source(
    controls: ModuleType, prefix: str
) -> None:
    assert controls.remote.allowed_evidence_name(
        Path("video") / (prefix + "a" * 32 + ".webm")
    )


@pytest.mark.parametrize(
    "name",
    [
        "video/page@" + "a" * 31 + ".webm",
        "video/page@" + "a" * 33 + ".webm",
        "video/page@" + "A" * 32 + ".webm",
        "video/page@@" + "a" * 32 + ".webm",
        "video/other@" + "a" * 32 + ".webm",
        "video/page%40" + "a" * 32 + ".webm",
        "video/../page@" + "a" * 32 + ".webm",
        "video/sub/page@" + "a" * 32 + ".webm",
        "video/page@" + "a" * 32 + ".webm.tmp",
        "video/page@" + "a" * 32 + ".mp4",
        "/video/page@" + "a" * 32 + ".webm",
        "video/page@" + "a" * 32 + ".webm\n",
    ],
)
def test_allowed_evidence_name_with_prefixed_video_variants_rejects(
    controls: ModuleType, name: str
) -> None:
    assert controls.remote.allowed_evidence_name(Path(name)) is False


def test_safe_export_with_closed_page_prefixed_video_preserves_original_bytes(
    controls: ModuleType, tmp_path: Path
) -> None:
    source, public = tmp_path / "source", tmp_path / "public"
    (source / "video").mkdir(parents=True)
    public.mkdir()
    path = source / "video" / ("page@" + "a" * 32 + ".webm")
    path.write_bytes(b"original owned video bytes")
    (source / "health.json").write_text('{"status":"healthy"}')
    records = controls.safe_export(source, public)
    assert {row["path"] for row in records} == {"health.json", "video/" + path.name}
    assert (public / "video" / path.name).read_bytes() == path.read_bytes()


@pytest.mark.parametrize("hardlink", [False, True])
def test_safe_export_with_page_prefixed_link_rejects_before_copy(
    controls: ModuleType, tmp_path: Path, hardlink: bool
) -> None:
    source, public = tmp_path / "source", tmp_path / "public"
    (source / "video").mkdir(parents=True)
    public.mkdir()
    private = tmp_path / "private"
    private.write_text("PRIVATE_CONTENT")
    path = source / "video" / ("page@" + "a" * 32 + ".webm")
    if hardlink:
        path.hardlink_to(private)
    else:
        path.symlink_to(private)
    with pytest.raises(ValueError):
        controls.safe_export(source, public)
    assert not list(public.iterdir())


def test_optional_parent_with_default_none_preserves_actual_common_db_browser_vectors(
    driver: ModuleType, tmp_path: Path
) -> None:
    nonce = "a" * 32
    names = driver.remote.resource_names(nonce)
    manifest = {"nonce": nonce, "browser_image": "immutable-browser"}
    for role in ("db", "web", "browser"):
        normal = driver.remote.container_arguments(nonce, names, role)
        assert normal == driver.remote.container_arguments(nonce, names, role, None)
        parented = driver.remote.container_arguments(
            nonce, names, role, "mimirexperts" + nonce + ".slice"
        )
        index = parented.index("--cgroup-parent")
        assert parented[index + 1] == "mimirexperts" + nonce + ".slice"
        assert parented[:index] + parented[index + 2 :] == normal
    assert driver.remote.database_arguments(
        tmp_path, nonce, names, "pg"
    ) == driver.remote.database_arguments(tmp_path, nonce, names, "pg", None)
    assert driver.remote.browser_arguments(
        tmp_path, manifest, names
    ) == driver.remote.browser_arguments(tmp_path, manifest, names, None)
    with pytest.raises(ValueError):
        driver.remote.container_arguments(nonce, names, "web", "system.slice")


def test_aggregate_profile_cli_is_closed_and_preserves_default_mode(
    driver: ModuleType, tmp_path: Path
) -> None:
    argv = [
        "--prepared-output",
        str(tmp_path),
        "--web-memory-mib",
        "384",
        "--output",
        str(tmp_path / "new"),
    ]
    assert driver.arguments(argv).resource_profile == "default"
    assert (
        driver.arguments(
            [*argv, "--resource-profile", "aggregate1024"]
        ).resource_profile
        == "aggregate1024"
    )
    with pytest.raises(SystemExit):
        driver.arguments([*argv, "--resource-profile", "arbitrary-parent"])


def test_benchmark_finish_source_requires_parent_cleanup_before_success_and_private_removal() -> (
    None
):
    tree = ast.parse((_RUNTIME / "benchmark.py").read_text())
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "finish"
    )
    block = next(node for node in function.body if isinstance(node, ast.Try))
    statements = [ast.unparse(node) for node in block.body]
    assert statements[0].startswith("remote.cleanup(")
    assert statements[1].startswith("cleanup_aggregate(")
    assert statements[2] == "result['cleanup'] = 'SUCCESS'"
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "update"
        for node in ast.walk(block.handlers[0])
    )
    removal = next(node for node in function.body if isinstance(node, ast.If))
    assert (
        ast.unparse(removal.test)
        == "result.get('cleanup') == 'SUCCESS' and result.get('export') == 'SUCCESS'"
    )
