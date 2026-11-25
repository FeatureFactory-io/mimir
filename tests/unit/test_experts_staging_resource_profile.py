"""Pure/file/local-process controls; no host services or cloud resources are used."""

from __future__ import annotations

import ast
import hashlib
import importlib
import io
import json
import os
import signal
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from types import ModuleType

import pytest

RUNTIME = Path(__file__).resolve().parents[2] / "scripts/experts-staging"
sys.path.insert(0, str(RUNTIME))
import aggregate
import controller
import remote
import resource_runtime
import suite_archive
import suite_contract
import suite_export


@pytest.fixture
def module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(RUNTIME))
    return importlib.import_module("resource_profile")


def test_selected_with_explicit_choice_keeps_default_and_closes_unknown(
    module: ModuleType,
) -> None:
    assert module.selected({}) is False
    assert module.selected({"resource_profile": "default"}) is False
    assert module.selected({"resource_profile": "aggregate960"}) is True
    with pytest.raises(ValueError):
        module.selected({"resource_profile": "caller-floor"})


def test_require_capacity_with_exact_warm_floor_admits_boundary_only(
    module: ModuleType,
) -> None:
    mib = 1024**2
    module.require_capacity(1216 * mib, 1024 * mib, True)
    for memory, disk, cached in [
        (1216 * mib - 1, 1024 * mib, True),
        (1216 * mib, 1024 * mib - 1, True),
        (1600 * mib, 4096 * mib, False),
        (True, 4096 * mib, True),
    ]:
        with pytest.raises(ValueError):
            module.require_capacity(memory, disk, cached)


def test_validate_proof_with_self_asserted_or_hidden_bytes_rejects(
    module: ModuleType,
) -> None:
    with pytest.raises(ValueError):
        module.validate_proof(b'{"measurement":"SUCCESS"}', b"{}", {})


def test_observer_source_with_original_dispatch_failure_preserves_cause() -> None:

    tree = ast.parse((RUNTIME / "resource_observer.py").read_text())
    main = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"
    )
    forbidden = []

    def broken_dispatch() -> None:
        raise RuntimeError("ORIGINAL_SUITE_FAILURE_SENTINEL")

    def broken_measurement(*args: object) -> None:
        raise ValueError("OBSERVATION_FAILURE_SENTINEL")

    manifest = {"resource_profile": "aggregate960"}
    namespace = {
        "json": __import__("json"),
        "Path": lambda path: type(
            "ManifestPath",
            (),
            {"read_text": lambda self: __import__("json").dumps(manifest)},
        )(),
        "selected": lambda m: True,
        "suite_browser": type(
            "ActualCallBoundary", (), {"main": staticmethod(broken_dispatch)}
        ),
        "observe": broken_measurement,
        "forbidden": forbidden,
    }
    exec(  # noqa: S102 - fixed reviewed repository AST, no untrusted code.
        compile(
            ast.Module(body=[main], type_ignores=[]), "<actual-observer-main>", "exec"
        ),
        namespace,
    )
    with pytest.raises(RuntimeError, match="ORIGINAL_SUITE_FAILURE_SENTINEL"):
        namespace["main"]()


@pytest.fixture
def manifest(module: ModuleType) -> dict:
    image = module.IMAGES["web"].split("@")[0]
    digest = module.IMAGES["web"].split("@")[1]
    return {
        "resource_profile": "aggregate960",
        "source_revision": module.SOURCE,
        "control_revision": "b" * 40,
        "runner_revision": "b" * 40,
        "nonce": "c" * 32,
        "build_run_id": "45516980492",
        "account": "411113550285",
        "bucket": "elasticbeanstalk-us-east-1-411113550285",
        "fixture_sha256": "f" * 64,
        "build_receipt": {
            "source_revision": module.SOURCE,
            "run_id": "45516980492",
            "web_image": image,
            "web_digest": digest,
            "platforms": ["linux/amd64"],
        },
        "image_sizes": {role: 1024 for role in module.IMAGES},
        **{role + "_image": value for role, value in module.IMAGES.items()},
    }


def _measurements(module: ModuleType) -> tuple[dict, dict]:
    """Explicit unit counter model; never actual kernel measurement evidence."""
    events = {"low": 0, "high": 0, "max": 0, "oom": 0, "oom_kill": 0}
    parent = {
        "current_bytes": 4096,
        "peak_bytes": 8192,
        "limit_bytes": 960 * module.MIB,
        "swap_current_bytes": 0,
        "swap_limit_bytes": 0,
        "events": dict(events),
        "populated": True,
        "keeper_verified": True,
    }
    roles = {}
    for role, cap in module.CAPS.items():
        memory = {
            "role": role,
            "peak_bytes": 4096,
            "limit_bytes": cap * module.MIB,
            "events": dict(events),
        }
        if role == "browser":
            memory["driver_passed"] = True
        roles[role] = {
            "memory": memory,
            "oom_killed": False,
            "restarts": 0,
            "member_verified": True,
        }
    return parent, roles


def test_checked_receipt_with_complete_typed_unit_model_roundtrips(
    module: ModuleType, manifest: dict
) -> None:
    parent, roles = _measurements(module)
    record = module.receipt_payload(manifest, parent, roles)
    record["status"] = "VERIFIED"
    assert module.checked_receipt(module.canonical(record), manifest) == record


@pytest.mark.parametrize(
    "field", ["nonce", "case", "control_revision", "images", "roles"]
)
def test_checked_receipt_with_redirected_identity_or_missing_role_rejects(
    module: ModuleType, manifest: dict, field: str
) -> None:
    parent, roles = _measurements(module)
    record = module.receipt_payload(manifest, parent, roles)
    record["status"] = "VERIFIED"
    record[field] = (
        {"private": "PRIVATE_SENTINEL"} if field in {"images", "roles"} else "foreign"
    )
    with pytest.raises(ValueError):
        module.checked_receipt(module.canonical(record), manifest)


@pytest.mark.parametrize("mutation", ["duplicate", "extra", "escaped", "whitespace"])
def test_resource_admission_with_hidden_raw_bytes_never_exports_raw_record(
    module: ModuleType, manifest: dict, mutation: str, monkeypatch: pytest.MonkeyPatch
) -> None:

    parent, roles = _measurements(module)
    record = module.receipt_payload(manifest, parent, roles)
    record["status"] = "VERIFIED"
    raw = module.canonical(record)
    if mutation == "duplicate":
        raw = raw.replace(b'"nonce":', b'"nonce":"PRIVATE_SENTINEL","nonce":')
    elif mutation == "extra":
        raw = raw.replace(b"{", b'{"private":"PRIVATE_SENTINEL",', 1)
    elif mutation == "escaped":
        raw = raw.replace(b"VERIFIED", b"VERIF\\u0049ED")
    else:
        raw = b" " + raw
    with pytest.raises(ValueError):
        module.checked_receipt(raw, manifest)
    result = suite_export._admit_receipt(
        "resource-receipt.json", __import__("json").loads(raw), raw, manifest
    )
    assert result["status"] == "FAILED" and result["receipt_content_rejected"] is True
    assert b"PRIVATE_SENTINEL" not in __import__("json").dumps(result).encode()


def test_failed_measurement_with_actual_numeric_oom_retains_failure_not_acceptance(
    module: ModuleType, manifest: dict
) -> None:
    parent, roles = _measurements(module)
    roles["browser"]["memory"]["events"]["oom_kill"] = 1
    roles["browser"]["oom_killed"] = True
    parent["events"]["oom_kill"] = 1
    record = module.receipt_payload(manifest, parent, roles)
    safe = module.checked_receipt(module.canonical(record), manifest, False)
    assert safe["roles"]["browser"]["oom_killed"] is True
    assert safe["parent"]["events"]["oom_kill"] == 1
    with pytest.raises(ValueError):
        module.checked_receipt(module.canonical(record), manifest, True)


def test_downloaded_resource_with_changed_case_or_counter_fails_independent_readback(
    module: ModuleType, manifest: dict
) -> None:

    parent, roles = _measurements(module)
    payload = module.receipt_payload(manifest, parent, roles)
    payload["status"] = "VERIFIED"
    derivative = {
        **payload,
        "derivative": True,
        "original_sha256": hashlib.sha256(module.canonical(payload)).hexdigest(),
    }
    suite_archive.verify_resource_record(
        {"resource-receipt.json": derivative}, manifest, True
    )
    derivative["parent"]["events"]["max"] = 1
    with pytest.raises(ValueError):
        suite_archive.verify_resource_record(
            {"resource-receipt.json": derivative}, manifest, True
        )


def test_parent_arguments_with_foreign_parent_never_retargets_ambient_group(
    module: ModuleType,
) -> None:

    assert resource_runtime.parent_arguments("a" * 32, None) == []
    with pytest.raises(ValueError):
        resource_runtime.parent_arguments("a" * 32, "system.slice")


def test_generic_observer_source_dispatches_actual_suite_main_and_samples_before_exit() -> (
    None
):
    text = (RUNTIME / "resource_observer.py").read_text()
    assert "suite_browser.main()" in text and "browser.main()" not in text.replace(
        "suite_browser.main()", ""
    )
    assert "finally:" in text and "read_memory(" in text


def test_cleanup_with_missing_marker_and_loaded_unit_refuses_success(
    module: ModuleType, manifest: dict, tmp_path: Path
) -> None:

    calls = []

    class ReadOnlyManager:
        @staticmethod
        def command(argv: list[str]) -> str:
            calls.append(argv)
            raise RuntimeError("READ_ONLY_MANAGER_BOUNDARY_LOADED_UNIT")

    with pytest.raises((RuntimeError, ValueError)):
        resource_runtime.cleanup(tmp_path, manifest, ReadOnlyManager)
    assert calls


def test_stopped_browser_with_missing_initial_member_record_cannot_recreate_proof(
    module: ModuleType, manifest: dict, tmp_path: Path
) -> None:

    owner = aggregate.Owner(
        tmp_path, manifest["nonce"], manifest["control_revision"], "d" * 32, "e" * 36
    )
    run = resource_runtime.ResourceRun(
        tmp_path, manifest, None, owner, {"browser": True}
    )
    row = {
        "id": "a" * 64,
        "parent": aggregate.parent_name(owner.nonce),
        "memory": 768 * module.MIB,
        "swap": 768 * module.MIB,
    }
    with pytest.raises((FileNotFoundError, ValueError)):
        resource_runtime.verify_stopped_browser(run, row)
    assert not (tmp_path / "aggregate-member-browser.json").exists()


@pytest.fixture
def model_proof(
    module: ModuleType, manifest: dict, monkeypatch: pytest.MonkeyPatch
) -> tuple[bytes, bytes]:
    """Hash-bound unit model, explicitly not the immutable actual CI proof."""

    parent, roles = _measurements(module)
    result = {
        "measurement": "SUCCESS",
        "cleanup": "SUCCESS",
        "export": "SUCCESS",
        "private_root_removed": True,
        "resource_profile": "aggregate960",
        "aggregate_members": {role: True for role in module.CAPS},
        "aggregate": parent,
        "envelope_mib": module.CAPS,
        "host_reserve_mib": 256,
        "observations": {
            "roles": {
                role: {
                    "memory": row["memory"],
                    "docker": {"oom_killed": False, "restarts": 0},
                }
                for role, row in roles.items()
            }
        },
    }
    source = {
        "source_revision": module.SOURCE,
        "runner_revision": module.RUNNER,
        "images": module.IMAGES,
    }
    raw = (module.canonical(result), module.canonical(source))
    monkeypatch.setattr(
        module,
        "PROOF_FILES",
        {
            name: hashlib.sha256(data).hexdigest()
            for name, data in zip(module.PROOF_FILES, raw)
        },
    )
    return raw


def test_make_bundle_with_actual_committed_controls_matches_launcher_exact_members(
    module: ModuleType, manifest: dict, model_proof: tuple[bytes, bytes], tmp_path: Path
) -> None:

    (tmp_path / "source.json").write_text('{"files":{}}')
    for name, raw in zip(module.PROOF_FILES, model_proof):
        (tmp_path / name).write_bytes(raw)
    bundle, digest = controller.make_bundle(tmp_path, manifest)
    script = controller.launcher(manifest, digest).split("\n", 1)[1].rsplit("\n", 1)[0]
    tree = ast.parse(script)
    assignment = next(
        n
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "record" for t in n.targets)
    )
    declaration = json.loads(ast.literal_eval(assignment.value.args[0]))
    with tarfile.open(bundle) as archive:
        assert set(archive.getnames()) == set(declaration["members"])
    assert set(module.PROOF_FILES) <= set(declaration["members"])


def test_container_arguments_with_aggregate_forbid_implicit_pulls_keep_default_cap(
    module: ModuleType, manifest: dict
) -> None:

    nonce = manifest["nonce"]
    names = remote.resource_names(nonce)
    normal = remote.container_arguments(nonce, names, "browser")
    measured = remote.container_arguments(
        nonce, names, "browser", aggregate.parent_name(nonce)
    )
    assert "--pull=never" in measured and "--pull=never" not in normal
    assert normal[normal.index("--memory") + 1] == "512m"
    assert measured[measured.index("--memory") + 1] == "768m"
    assert remote._LIMITS["web"][0] == 384 and remote._LIMITS["db"][0] == 192


def test_receipt_with_each_of_eleven_fresh_cases_has_distinct_case_nonce_binding(
    module: ModuleType, manifest: dict
) -> None:

    for index, case in enumerate(suite_contract.suite_cases("full")):
        actual = {
            **manifest,
            "suite_phase": case.phase,
            "saga_case": case.case,
            "nonce": f"{index:032x}",
        }
        parent, roles = _measurements(module)
        record = module.receipt_payload(actual, parent, roles)
        record["status"] = "VERIFIED"
        assert (
            module.checked_receipt(module.canonical(record), actual)["case"]
            == case.case
        )
        with pytest.raises(ValueError):
            module.checked_receipt(
                module.canonical(record), {**actual, "nonce": "f" * 32}
            )


def test_downloaded_resource_bytes_with_overwritten_private_duplicate_rejects(
    module: ModuleType, tmp_path: Path
) -> None:

    raw = b'{"private":"PRIVATE_SENTINEL","private":false}\n'
    target = tmp_path / "duplicate-resource.tar.gz"
    with tarfile.open(target, "w:gz") as archive:
        item = tarfile.TarInfo("resource-receipt.json")
        item.size = len(raw)
        archive.addfile(item, io.BytesIO(raw))
    with tarfile.open(target) as archive, pytest.raises(ValueError):
        suite_archive._received_resource_bytes(archive, archive.getmembers())


def test_cleanup_with_positive_loaded_unit_and_missing_marker_refuses_all_mutation(
    module: ModuleType, manifest: dict, tmp_path: Path
) -> None:

    calls = []
    name = aggregate.parent_name(manifest["nonce"])
    path = "/org/freedesktop/systemd1/unit/" + name.replace(".", "_2e")

    class Adapter:
        @staticmethod
        def command(argv: list[str]) -> str:
            calls.append(argv)
            return f'a(ssssssouso) 1 "{name}" "owned" "loaded" "active" "active" "" "{path}" 0 "" "/"'

    with pytest.raises(ValueError):
        resource_runtime.cleanup(tmp_path, manifest, Adapter)
    assert len(calls) == 1 and "ListUnitsByPatterns" in calls[0]
    assert not (tmp_path / "aggregate-owner.json").exists()


def test_capture_role_with_missing_observer_preserves_known_docker_oom_and_restarts(
    module: ModuleType, manifest: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real missing-file control with modeled curated Docker acquisition, no host ops."""
    row = {"oom_killed": True, "restarts": 2}

    class Adapter:
        @staticmethod
        def assert_resource(*args: object) -> None:
            return None

    run = resource_runtime.ResourceRun(tmp_path, manifest, Adapter)
    monkeypatch.setattr(resource_runtime, "container_row", lambda *args: row)
    monkeypatch.setattr(resource_runtime, "verify_stopped_browser", lambda *args: None)
    result = resource_runtime.capture_role(run, {"browser": "owned-browser"}, "browser")
    assert result == {
        "memory": {"status": "UNAVAILABLE"},
        "oom_killed": True,
        "restarts": 2,
        "member_verified": True,
    }
    parent, roles = _measurements(module)
    roles["browser"] = result
    payload = module.receipt_payload(manifest, parent, roles)
    raw = module.canonical(payload)
    assert module.checked_receipt(raw, manifest, False)["roles"]["browser"] == result
    derivative = suite_export._special_receipt(
        "resource-receipt.json", payload, raw, manifest
    )
    assert derivative["roles"]["browser"]["oom_killed"] is True
    assert derivative["roles"]["browser"]["restarts"] == 2
    suite_archive.verify_resource_record(
        {"resource-receipt.json": derivative}, manifest, False
    )
    with pytest.raises(ValueError):
        suite_archive.verify_resource_record(
            {"resource-receipt.json": derivative}, manifest, True
        )
    with pytest.raises(ValueError):
        module.checked_receipt(raw, manifest, True)


def test_verified_receipt_with_unavailable_memory_never_passes_partial_transport_mode(
    module: ModuleType, manifest: dict
) -> None:
    parent, roles = _measurements(module)
    roles["browser"]["memory"] = {"status": "UNAVAILABLE"}
    record = module.receipt_payload(manifest, parent, roles)
    record["status"] = "VERIFIED"
    with pytest.raises(ValueError):
        module.checked_receipt(module.canonical(record), manifest, False)


def test_archive_evidence_with_early_runtime_failure_exports_both_exact_declarations(
    manifest: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Actual producer/export/tar/readback with real files; no upload or runtime."""
    output = tmp_path / "output"
    output.mkdir()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    actual = {
        **manifest,
        "resource_profile": "default",
        "source_files": {"unit-model.py": "a" * 64},
        "control_files": {"remote.py": "b" * 64},
    }
    source = {
        "source_revision": actual["source_revision"],
        "files": actual["source_files"],
    }
    controls = {
        "control_revision": actual["control_revision"],
        "files": actual["control_files"],
    }
    (runtime / "source.json").write_bytes(json.dumps(source).encode())
    (runtime / "controls.json").write_bytes(json.dumps(controls).encode())
    (output / "runtime-failure.json").write_text(
        json.dumps(
            {
                "status": "FAILED",
                "exception_class": "ValueError",
                "private_output_exported": False,
            }
        )
    )
    monkeypatch.setattr(suite_export, "__file__", str(runtime / "suite_export.py"))
    uploaded = []
    monkeypatch.setattr(
        remote, "upload_evidence", lambda path, record: uploaded.append(path)
    )
    remote.archive_evidence(tmp_path, actual)
    assert len(uploaded) == 1
    suite_archive.verify_case_archive(uploaded[0], actual, require_pass=False)
    with tarfile.open(uploaded[0]) as archive:
        assert {"source-manifest.json", "control-identity.json"} <= set(
            archive.getnames()
        )
        observed = json.loads(archive.extractfile("source-manifest.json").read())
        assert observed["declaration"] == source
    with pytest.raises(ValueError):
        suite_archive.verify_case_archive(uploaded[0], actual, require_pass=True)


def test_capacity_with_real_low_memory_fixture_retains_numeric_observation_before_reject(
    module: ModuleType, manifest: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real fixture-file OS boundary model; no actual host or Docker query."""
    memory = tmp_path / "model-meminfo"
    memory.write_text(f"MemAvailable: {1216 * 1024 - 1} kB\n")
    real_path = Path
    monkeypatch.setattr(
        resource_runtime,
        "Path",
        lambda value: memory if value == "/proc/meminfo" else real_path(value),
    )

    class Adapter:
        image_cache_reserve = staticmethod(lambda record, cache: 1024**3)
        command = staticmethod(lambda argv: json.dumps("/owned-engine-model"))

        class shutil:
            @staticmethod
            def disk_usage(value: str) -> object:
                return type("DiskFixture", (), {"free": 2 * 1024**3})()

    run = resource_runtime.ResourceRun(tmp_path, manifest, Adapter)
    with pytest.raises(ValueError):
        resource_runtime.capacity(run, {})
    row = json.loads((tmp_path / "output/capacity.json").read_text())
    assert row["available_memory_bytes"] == 1216 * module.MIB - 1024
    assert row["required_memory_bytes"] == 1216 * module.MIB
    assert row["image_cache_verified"] is True
    assert not (tmp_path / "aggregate-owner.json").exists()


def test_runtime_failure_with_actual_capacity_guard_preserves_only_finite_phase(
    module: ModuleType, tmp_path: Path
) -> None:
    try:
        module.require_capacity(1, 1024**3, True)
    except ValueError as error:
        remote.record_runtime_failure(tmp_path, error)
    raw = (tmp_path / "output/runtime-failure.json").read_bytes()
    row = json.loads(raw)
    exported = suite_export._special_receipt("runtime-failure.json", row, raw, {})
    assert exported["phase"] == "capacity"
    assert exported["source_frames"] and all(
        type(frame["line"]) is int for frame in exported["source_frames"]
    )
    assert all(
        set(frame) == {"function", "line"} for frame in exported["source_frames"]
    )
    assert b"PRIVATE_SENTINEL" not in module.canonical(exported)


@pytest.mark.parametrize("change", ["phase", "function", "line_bool", "line_bound"])
def test_runtime_failure_with_unknown_diagnostic_data_rejects_private_projection(
    tmp_path: Path, change: str
) -> None:
    record = {
        "status": "FAILED",
        "exception_class": "ValueError",
        "private_output_exported": False,
        "phase": "capacity",
        "source_frames": [{"function": "capacity", "line": 1}],
    }
    if change == "phase":
        record["phase"] = "PRIVATE_SENTINEL"
    elif change == "function":
        record["source_frames"][0]["function"] = "PRIVATE_SENTINEL"
    elif change == "line_bool":
        record["source_frames"][0]["line"] = True
    else:
        record["source_frames"][0]["line"] = 4097
    raw = json.dumps(record).encode()
    safe = suite_export._admit_receipt("runtime-failure.json", record, raw, {})
    assert safe["status"] == "FAILED" and safe["receipt_content_rejected"] is True
    assert b"PRIVATE_SENTINEL" not in json.dumps(safe).encode()


def test_source_declaration_with_conflicting_existing_original_refuses_overwrite(
    tmp_path: Path,
) -> None:
    (tmp_path / "runtime").mkdir()
    (tmp_path / "output").mkdir()
    original = b'{"PRIVATE_SENTINEL":"original evidence"}'
    (tmp_path / "runtime/source.json").write_bytes(b'{"files":{}}')
    target = tmp_path / "output/source-manifest.json"
    target.write_bytes(original)
    with pytest.raises(ValueError):
        remote.retain_source_declaration(tmp_path)
    assert target.read_bytes() == original


def test_capacity_failure_with_linked_output_never_writes_foreign_directory(
    manifest: dict, tmp_path: Path
) -> None:
    own = tmp_path / "own"
    own.mkdir()
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (own / "output").symlink_to(foreign, target_is_directory=True)
    run = resource_runtime.ResourceRun(own, manifest, None)
    with pytest.raises(ValueError):
        resource_runtime.retain_capacity_failure(run, 1, 1024**3, True)
    assert not list(foreign.iterdir())


def _launcher_ast(manifest: dict) -> ast.Module:
    """Read actual generated code without executing any transport/host command."""
    program = (
        controller.launcher(manifest, "a" * 64).split("\n", 1)[1].rsplit("\n", 1)[0]
    )
    return ast.parse(program)


def test_aggregate_launcher_with_verified_profile_replaces_waiting_python_process(
    manifest: dict,
) -> None:
    tree = _launcher_ast(manifest)
    final = tree.body[-1]
    assert isinstance(final, ast.Expr) and isinstance(final.value, ast.Call)
    assert ast.unparse(final.value.func) == "os.execv"
    assert ast.unparse(final.value.args[0]) == "sys.executable"
    assert (
        ast.unparse(final.value.args[1])
        == "[sys.executable, str(runtime / 'remote.py')]"
    )


def test_default_launcher_with_old_profile_keeps_original_subprocess_vector(
    manifest: dict,
) -> None:
    tree = _launcher_ast({**manifest, "resource_profile": "default"})
    final = tree.body[-1]
    assert ast.unparse(final.value.func) == "subprocess.run"
    assert ast.unparse(final.value.args[0]) == "['python3', str(runtime / 'remote.py')]"
    assert [(kw.arg, ast.literal_eval(kw.value)) for kw in final.value.keywords] == [
        ("check", True)
    ]


# A local real exec took 7.58s; these fixtures prove identity and signal invariants,
# not startup speed. Production supervision deadlines remain unchanged.
_LOCAL_EXEC_WAIT_SECONDS = 15

_LOCAL_EXEC_IDENTITY = """import hashlib,json,os,signal,sys,time
from pathlib import Path
root=Path(__file__).resolve().parent
def snapshot(name):
    owner=root/'controller-owner.json'
    info=owner.stat()
    row={'pid':os.getpid(),'ppid':os.getppid(),'uid':os.getuid(),'gid':os.getgid(),
         'groups':sorted(os.getgroups()),'cwd':os.getcwd(),'executable':sys.executable,
         'sentinel':os.environ.get('EXPERTS_LOCAL_EXEC_VALUE'),
         'owner_sha256':hashlib.sha256(owner.read_bytes()).hexdigest(),
         'owner_inode':info.st_ino,'owner_uid':info.st_uid,'owner_gid':info.st_gid,
         'owner_mode':info.st_mode&0o777}
    (root/name).write_text(json.dumps(row))
"""
_LOCAL_EXEC_TARGET = """
mode=os.environ['EXPERTS_LOCAL_EXEC_MODE']
if mode=='signal':
    signal.signal(signal.SIGTERM,lambda number,frame:sys.exit(74))
snapshot('after.json')
if mode=='signal':
    time.sleep(10)
else:
    sys.exit(int(mode))
"""


def _write_exec_fixture(manifest: dict, tmp_path: Path) -> tuple[Path, Path]:
    """Execute only the reviewed final two launcher nodes in an owned local fixture."""
    tree = _launcher_ast(manifest)
    nodes = tree.body[-2:]
    assert isinstance(nodes[0], ast.Import) and [n.name for n in nodes[0].names] == [
        "sys"
    ]
    assert (
        isinstance(nodes[1], ast.Expr)
        and ast.unparse(nodes[1].value.func) == "os.execv"
    )
    terminal = ast.unparse(ast.Module(body=nodes, type_ignores=[]))
    own = tmp_path / "local-exec-only"
    own.mkdir(mode=0o700)
    owner = own / "controller-owner.json"
    owner.write_text("LOCAL_TEST_OWNER_ONLY")
    owner.chmod(0o600)
    wrapper = own / "launcher.py"
    wrapper.write_text(
        _LOCAL_EXEC_IDENTITY
        + "\nruntime=root\nsnapshot('before.json')\n"
        + terminal
        + "\n"
    )
    (own / "remote.py").write_text(_LOCAL_EXEC_IDENTITY + _LOCAL_EXEC_TARGET)
    cwd = own / "retained-working-directory"
    cwd.mkdir(mode=0o700)
    return wrapper, cwd


def _assert_exec_identity(before: dict, after: dict, pid: int) -> None:
    """Compare actual local kernel/process state, not an asserted PID model."""
    assert before["pid"] == after["pid"] == pid
    assert before["uid"] == after["uid"] == os.getuid()
    assert before["gid"] == after["gid"] == os.getgid()
    for key in (
        "ppid",
        "groups",
        "cwd",
        "executable",
        "sentinel",
        "owner_sha256",
        "owner_inode",
        "owner_uid",
        "owner_gid",
        "owner_mode",
    ):
        assert before[key] == after[key], key
    assert (
        after["sentinel"] == "fixed-public-local-probe" and after["owner_mode"] == 0o600
    )


@pytest.mark.parametrize("exit_code", [0, 23])
def test_aggregate_exec_with_real_local_process_retains_pid_identity_and_exit_status(
    manifest: dict, tmp_path: Path, exit_code: int
) -> None:
    wrapper, cwd = _write_exec_fixture(manifest, tmp_path)
    env = {
        **os.environ,
        "EXPERTS_LOCAL_EXEC_VALUE": "fixed-public-local-probe",
        "EXPERTS_LOCAL_EXEC_MODE": str(exit_code),
    }
    process = subprocess.Popen(
        [sys.executable, str(wrapper)],
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = process.communicate(timeout=_LOCAL_EXEC_WAIT_SECONDS)
    assert process.returncode == exit_code and stdout == stderr == b""
    before = json.loads((wrapper.parent / "before.json").read_text())
    after = json.loads((wrapper.parent / "after.json").read_text())
    _assert_exec_identity(before, after, process.pid)
    assert after["cwd"] == str(cwd)


def _ready_exec_snapshot(path: Path) -> dict:
    """Read a completed real snapshot before delivering the bounded test signal."""
    deadline = time.monotonic() + _LOCAL_EXEC_WAIT_SECONDS
    while time.monotonic() < deadline:
        try:
            return json.loads(path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(0.01)
    raise AssertionError("Actual local exec target did not become ready.")


def test_aggregate_exec_with_real_local_sigterm_reaches_same_supervised_pid(
    manifest: dict, tmp_path: Path
) -> None:
    wrapper, cwd = _write_exec_fixture(manifest, tmp_path)
    env = {
        **os.environ,
        "EXPERTS_LOCAL_EXEC_VALUE": "fixed-public-local-probe",
        "EXPERTS_LOCAL_EXEC_MODE": "signal",
    }
    process = subprocess.Popen(
        [sys.executable, str(wrapper)],
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        after = _ready_exec_snapshot(wrapper.parent / "after.json")
        process.send_signal(signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=_LOCAL_EXEC_WAIT_SECONDS)
        assert process.returncode == 74 and stdout == stderr == b""
        before = json.loads((wrapper.parent / "before.json").read_text())
        _assert_exec_identity(before, after, process.pid)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=_LOCAL_EXEC_WAIT_SECONDS)


@pytest.mark.parametrize("choice", [None, True, "aggregate512", {"floor": 1}])
def test_launcher_template_with_unknown_resource_selector_rejects(
    choice: object,
) -> None:
    with pytest.raises(ValueError):
        controller.launcher_template({"resource_profile": choice})


def test_launcher_template_with_changed_terminal_boundary_refuses_broad_replacement(
    manifest: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        controller,
        "_LAUNCHER",
        controller._LAUNCHER + "\n" + controller._REMOTE_DISPATCH,
    )
    with pytest.raises(ValueError):
        controller.launcher_template(manifest)


def test_selected_with_retired_1024_profile_refuses_compatibility_alias(
    module: ModuleType,
) -> None:
    with pytest.raises(ValueError):
        module.selected({"resource_profile": "aggregate1024"})


def test_checked_parent_with_old_1024_cap_refuses_new_960_measurement(
    module: ModuleType,
) -> None:
    parent, _ = _measurements(module)
    parent["limit_bytes"] = 1024 * module.MIB
    with pytest.raises(ValueError):
        module.checked_parent(parent, False)
