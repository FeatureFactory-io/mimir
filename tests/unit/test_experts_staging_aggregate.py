"""Pure contracts and real-file fixtures; these are not real systemd/kernel proof."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_RUNTIME = Path(__file__).resolve().parents[2] / "scripts/experts-staging"


@pytest.fixture
def module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load the actual standard-library helper without executing host operations."""
    monkeypatch.syspath_prepend(str(_RUNTIME))
    spec = importlib.util.spec_from_file_location(
        "owned_aggregate_contract", _RUNTIME / "aggregate.py"
    )
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, loaded)
    spec.loader.exec_module(loaded)
    return loaded


def test_parent_name_with_fresh_identity_has_no_implicit_ancestor_slices(
    module: ModuleType,
) -> None:
    assert module.parent_name("a" * 32) == "mimirexperts" + "a" * 32 + ".slice"
    assert "-" not in module.parent_name("a" * 32)


@pytest.mark.parametrize("nonce", ["", "a" * 31, "A" * 32, "../system", "system.slice"])
def test_parent_name_with_foreign_or_unsafe_identity_rejects(
    module: ModuleType, nonce: str
) -> None:
    with pytest.raises(ValueError):
        module.parent_name(nonce)


@pytest.mark.parametrize(
    "name,web,browser", [("aggregate1024", 384, 768), ("default", 384, 512)]
)
def test_validate_profile_with_closed_consistent_choice_preserves_default(
    module: ModuleType, name: str, web: int, browser: int
) -> None:
    assert module.validate_profile(name, web, browser) is (name == "aggregate1024")


@pytest.mark.parametrize(
    "name,web,browser",
    [
        ("other", 384, 768),
        ("aggregate1024", 256, 768),
        ("aggregate1024", 384, 512),
        ("aggregate1024", True, 768),
    ],
)
def test_validate_profile_with_unreviewed_or_inconsistent_choice_rejects(
    module: ModuleType, name: str, web: int, browser: int
) -> None:
    with pytest.raises(ValueError):
        module.validate_profile(name, web, browser)


def test_validate_remaining_with_owned_allocations_uses_remaining_not_full_browser(
    module: ModuleType,
) -> None:
    current = 400 * 1024 * 1024
    required = module.LIMIT_BYTES - current + module.RESERVE_BYTES
    module.validate_remaining(required, current, module.LIMIT_BYTES)
    with pytest.raises(ValueError):
        module.validate_remaining(required - 1, current, module.LIMIT_BYTES)


@pytest.mark.parametrize(
    "available,current,maximum",
    [
        (True, 1, 1073741824),
        (2000000000, -1, 1073741824),
        (2000000000, 1073741825, 1073741824),
        (2000000000, 1, 2147483648),
        (2000000000, 0, 1073741824),
    ],
)
def test_validate_remaining_with_unverified_or_invalid_parent_rejects(
    module: ModuleType, available: int, current: int, maximum: int
) -> None:
    with pytest.raises(ValueError):
        module.validate_remaining(available, current, maximum)


def test_read_group_with_actual_files_retains_peak_and_zero_swap(
    module: ModuleType, tmp_path: Path
) -> None:
    values = {
        "memory.current": "4096",
        "memory.peak": "8192",
        "memory.max": "1073741824",
        "memory.swap.current": "0",
        "memory.swap.max": "0",
        "memory.events": "low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\n",
        "cgroup.events": "populated 1\nfrozen 0\n",
    }
    for name, value in values.items():
        (tmp_path / name).write_text(value)
    record = module.read_group(tmp_path)
    assert record["current_bytes"] == 4096 and record["peak_bytes"] == 8192
    assert (
        record["limit_bytes"] == module.LIMIT_BYTES
        and record["swap_current_bytes"] == 0
    )
    (tmp_path / "memory.max").write_text("max")
    with pytest.raises(ValueError):
        module.read_group(tmp_path)


@pytest.fixture
def owner(module: ModuleType, tmp_path: Path) -> object:
    """Use an explicit metadata fixture; this is not a real owned systemd unit."""
    return module.Owner(tmp_path, "a" * 32, "b" * 40, "c" * 32, "d" * 36)


def test_start_arguments_with_own_units_fail_on_collision_and_cap_the_slice(
    module: ModuleType, owner: object
) -> None:
    parent = module.unit_properties(owner, "parent")
    values = {name: (signature, args) for name, signature, args in parent}
    assert len(values) == len(parent)
    assert values["MemoryMax"] == ("t", [str(module.LIMIT_BYTES)])
    assert values["MemorySwapMax"] == ("t", ["0"])
    for role in ("parent", "keeper"):
        argv = module.start_arguments(owner, role)
        assert argv[9] == module.unit_name(owner, role) and argv[10] == "fail"
        assert (
            argv[11] == str(len(module.unit_properties(owner, role)))
            and argv[-1] == "0"
        )
        assert (
            "replace" not in argv
            and "system.slice" not in argv
            and "/bin/sh" not in argv
        )
    keeper = {
        name: (signature, args)
        for name, signature, args in module.unit_properties(owner, "keeper")
    }
    assert keeper["Description"][1] == [module.description(owner, "keeper")]
    assert keeper["Slice"] == ("s", [module.parent_name(owner.nonce)])
    assert keeper["ExecStart"] == (
        "a(sasb)",
        ["1", "/usr/bin/sleep", "2", "/usr/bin/sleep", "1200", "false"],
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("Id", "system.slice"),
        ("Description", "FOREIGN_PRIVATE_SENTINEL"),
        ("Transient", "no"),
    ],
)
def test_unit_identity_with_foreign_metadata_rejects_before_stop(
    module: ModuleType, owner: object, field: str, value: str
) -> None:
    row = {
        "Id": module.unit_name(owner, "parent"),
        "Description": module.description(owner, "parent"),
        "Transient": "yes",
    }
    module.require_unit_identity(owner, "parent", row)
    row[field] = value
    with pytest.raises(ValueError):
        module.require_unit_identity(owner, "parent", row)


@pytest.mark.parametrize(
    "row",
    [
        {"driver": "cgroupfs", "version": "2"},
        {"driver": "systemd", "version": "1"},
        {"driver": "systemd", "version": 2},
        {"driver": "systemd", "version": "2", "extra": "PRIVATE"},
    ],
)
def test_driver_with_unsupported_or_untyped_identity_rejects(
    module: ModuleType, row: dict
) -> None:
    with pytest.raises(ValueError):
        module.require_driver(row)
    module.require_driver({"driver": "systemd", "version": "2"})


def _member(module: ModuleType, owner: object, role: str) -> dict:
    """Representative curated metadata for pure validation, not Docker evidence."""
    memory = module.ROLE_MEMORY_MIB[role] * 1024 * 1024
    return {
        "owner": owner.nonce,
        "fixture": "CEDAR-RFP-01",
        "parent": module.parent_name(owner.nonce),
        "id": "e" * 64,
        "memory": memory,
        "swap": memory,
        "running": True,
        "readonly": True,
        "cap_drop": ["ALL"],
        "security": ["no-new-privileges"],
        "restarts": 0,
        "pid": 123,
    }


@pytest.mark.parametrize("role", ["db", "web", "browser"])
def test_member_row_with_fixed_caps_derives_exact_expected_actual_scope(
    module: ModuleType, owner: object, role: str
) -> None:
    identity, path = module.validate_member_row(
        owner, role, _member(module, owner, role)
    )
    assert identity == "e" * 64
    assert (
        path == "/" + module.parent_name(owner.nonce) + "/docker-" + identity + ".scope"
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("owner", "f" * 32),
        ("fixture", "FOREIGN"),
        ("parent", "system.slice"),
        ("id", "short"),
        ("memory", 512),
        ("swap", -1),
        ("running", False),
        ("readonly", False),
        ("cap_drop", []),
        ("security", None),
        ("restarts", 1),
    ],
)
def test_member_row_with_wrong_owner_parent_cap_or_hardening_rejects(
    module: ModuleType, owner: object, field: str, value: object
) -> None:
    row = _member(module, owner, "browser")
    row[field] = value
    with pytest.raises(ValueError):
        module.validate_member_row(owner, "browser", row)


def test_private_marker_with_real_hardlink_or_world_access_rejects(
    module: ModuleType, tmp_path: Path
) -> None:
    path = tmp_path / "owner.json"
    module.private_json(path, {"fixed": "private"})
    assert module.checked_private(path) == {"fixed": "private"}
    path.chmod(0o644)
    with pytest.raises(ValueError):
        module.checked_private(path)
    path.chmod(0o600)
    alias = tmp_path / "alias.json"
    alias.hardlink_to(path)
    with pytest.raises(ValueError):
        module.checked_private(path)


def test_exhaustion_with_real_file_fixture_keeps_actual_counters_but_fails(
    module: ModuleType, tmp_path: Path
) -> None:
    values = {
        "memory.current": "100",
        "memory.peak": str(module.LIMIT_BYTES),
        "memory.max": str(module.LIMIT_BYTES),
        "memory.swap.current": "0",
        "memory.swap.max": "0",
        "memory.events": "low 0\nhigh 0\nmax 2\noom 1\noom_kill 1\n",
        "cgroup.events": "populated 1\nfrozen 0\n",
    }
    for name, value in values.items():
        (tmp_path / name).write_text(value)
    row = module.read_group(tmp_path)
    assert row["events"]["oom_kill"] == 1 and row["peak_bytes"] == module.LIMIT_BYTES
    with pytest.raises(ValueError):
        module.require_headroom(row)


def test_cleanup_source_with_live_containers_or_foreign_children_has_no_parent_stop_bypass() -> (
    None
):
    tree = ast.parse((_RUNTIME / "aggregate.py").read_text())
    methods = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    cleanup = methods["cleanup"]
    guards = [node for node in cleanup.body if isinstance(node, ast.If)]
    assert ast.unparse(guards[0].test) == "remaining_containers"
    assert isinstance(guards[0].body[0], ast.Raise)
    calls = [
        ast.unparse(node.func)
        for node in ast.walk(methods["stop_owned"])
        if isinstance(node, ast.Call)
    ]
    assert calls.index("require_unit_identity") < calls.index("invoke")
    assert "await_absent" in calls


def _unit_row(module: ModuleType, owner: object, role: str) -> dict:
    """Closed manager state fixture, not actual host-unit evidence."""
    return {
        "Id": module.unit_name(owner, role),
        "Description": module.description(owner, role),
        "Transient": "yes",
        "ControlGroup": "/" + module.parent_name(owner.nonce),
        "ActiveState": "active",
    }


def test_cleanup_with_container_still_present_refuses_every_unit_operation(
    module: ModuleType, owner: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    monkeypatch.setattr(module, "check_owner", lambda own: None)
    monkeypatch.setattr(module, "show_unit", lambda own, role: calls.append(role))
    with pytest.raises(ValueError, match="before Docker cleanup"):
        module.cleanup(owner, ["owned-container-still-present"])
    assert calls == []


def test_cleanup_with_foreign_unit_metadata_never_stops_any_unit(
    module: ModuleType, owner: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    row = _unit_row(module, owner, "parent")
    row["Description"] = "FOREIGN_PRIVATE_UNIT"
    monkeypatch.setattr(module, "check_owner", lambda own: None)
    monkeypatch.setattr(module, "show_unit", lambda own, role: row)
    monkeypatch.setattr(module, "stop_owned", lambda own, role: calls.append(role))
    with pytest.raises(ValueError, match="foreign"):
        module.cleanup(owner, [])
    assert calls == []


def test_cleanup_with_unknown_real_directory_refuses_broad_parent_stop(
    module: ModuleType, owner: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    path = tmp_path / "simulated-kernel-parent"
    path.mkdir()
    (path / "foreign-service").mkdir()
    monkeypatch.setattr(module, "check_owner", lambda own: None)
    monkeypatch.setattr(
        module, "show_unit", lambda own, role: _unit_row(module, own, role)
    )
    monkeypatch.setattr(module, "group_path", lambda own, row: path)
    monkeypatch.setattr(module, "stop_owned", lambda own, role: calls.append(role))
    with pytest.raises(ValueError, match="unknown descendants"):
        module.cleanup(owner, [])
    assert calls == [] and (path / "foreign-service").exists()


def test_cleanup_with_keeper_stop_failure_keeps_parent_and_private_proof(
    module: ModuleType, owner: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    path = tmp_path / "simulated-kernel-parent"
    path.mkdir()
    (path / module.unit_name(owner, "keeper")).mkdir()
    marker = owner.root / "private-retained-proof.json"
    module.private_json(marker, {"source": "original"})
    monkeypatch.setattr(module, "check_owner", lambda own: None)
    monkeypatch.setattr(
        module, "show_unit", lambda own, role: _unit_row(module, own, role)
    )
    monkeypatch.setattr(module, "group_path", lambda own, row: path)

    def rejected_stop(own: object, argv: list[str]) -> tuple[int, str]:
        calls.append(argv[9])
        return 1, ""

    monkeypatch.setattr(module, "invoke", rejected_stop)
    with pytest.raises(RuntimeError, match="unit stop failed"):
        module.cleanup(owner, [])
    assert calls == [module.unit_name(owner, "keeper")]
    assert marker.exists() and path.exists()


def test_failure_projection_with_private_extra_fields_rejects(
    module: ModuleType,
) -> None:
    allowed = {
        "operation": "START_PARENT",
        "return_code": 1,
        "manager_error": "InvalidArgs",
    }
    module.validate_failure_record(allowed)
    with pytest.raises(ValueError):
        module.validate_failure_record({**allowed, "private": "PRIVATE_SENTINEL"})
    with pytest.raises(ValueError):
        module.validate_failure_record({**allowed, "operation": ["PRIVATE_SENTINEL"]})
