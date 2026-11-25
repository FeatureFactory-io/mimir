"""Pure measured-proof and real-file admission controls; no host/cloud operations."""

from __future__ import annotations

import ast
import hashlib
import importlib
import io
import json
import sys
import tarfile
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
    assert module.selected({"resource_profile": "aggregate1024"}) is True
    with pytest.raises(ValueError):
        module.selected({"resource_profile": "caller-floor"})


def test_require_capacity_with_exact_warm_floor_admits_boundary_only(
    module: ModuleType,
) -> None:
    mib = 1024**2
    module.require_capacity(1280 * mib, 1024 * mib, True)
    for memory, disk, cached in [
        (1280 * mib - 1, 1024 * mib, True),
        (1280 * mib, 1024 * mib - 1, True),
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

    manifest = {"resource_profile": "aggregate1024"}
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
        "resource_profile": "aggregate1024",
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
        "limit_bytes": 1024 * module.MIB,
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
        "resource_profile": "aggregate1024",
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
