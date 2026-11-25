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
        "KillMode": "process",
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
    path = _keeper_tree(module, owner, tmp_path, monkeypatch)
    marker = owner.root / "private-retained-proof.json"
    module.private_json(marker, {"source": "original"})

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


def _keeper_tree(
    module: ModuleType, owner: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Construct a real-file/metadata model; no host manager or kernel is used."""
    path = tmp_path / "cleanup-tree-model"
    path.mkdir()
    (path / "cgroup.procs").write_text("")
    (path / "cgroup.events").write_text("populated 1\nfrozen 0\n")
    keeper = path / module.unit_name(owner, "keeper")
    keeper.mkdir()
    (keeper / "cgroup.procs").write_text("123\n")
    monkeypatch.setattr(module, "check_owner", lambda own: None)
    monkeypatch.setattr(module, "group_path", lambda own, row: path)
    monkeypatch.setattr(
        module,
        "pid_group",
        lambda pid: "/"
        + module.parent_name(owner.nonce)
        + "/"
        + module.unit_name(owner, "keeper"),
    )

    def metadata(own: object, role: str) -> dict:
        row = _unit_row(module, own, role)
        row["MainPID"] = "123" if role == "keeper" else "0"
        row["ControlGroup"] += (
            "/" + module.unit_name(own, "keeper") if role == "keeper" else ""
        )
        return row

    monkeypatch.setattr(module, "show_unit", metadata)
    return path


@pytest.mark.parametrize("case", ["nested_subgroup", "extra_pid", "parent_pid"])
def test_cleanup_with_unknown_keeper_subgroup_or_pid_refuses_before_any_stop(
    module: ModuleType,
    owner: object,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    path = _keeper_tree(module, owner, tmp_path, monkeypatch)
    keeper = path / module.unit_name(owner, "keeper")
    if case == "nested_subgroup":
        child = keeper / "foreign.scope"
        child.mkdir()
        (child / "cgroup.procs").write_text("456\n")
    elif case == "extra_pid":
        (keeper / "cgroup.procs").write_text("123\n456\n")
    else:
        (path / "cgroup.procs").write_text("456\n")
    calls = []

    def stop_boundary(own: object, role: str) -> None:
        calls.append(role)
        raise RuntimeError("UNIT_STOP_BOUNDARY_NO_COMMAND_EXECUTED")

    monkeypatch.setattr(module, "stop_owned", stop_boundary)
    with pytest.raises(ValueError):
        module.cleanup(owner, [])
    assert calls == []
    assert keeper.exists()


def test_cleanup_with_clean_exact_mainpid_tree_reaches_keeper_stop_boundary(
    module: ModuleType, owner: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _keeper_tree(module, owner, tmp_path, monkeypatch)
    calls = []

    def stop_boundary(own: object, role: str) -> None:
        calls.append(role)
        raise RuntimeError("UNIT_STOP_BOUNDARY_NO_COMMAND_EXECUTED")

    monkeypatch.setattr(module, "stop_owned", stop_boundary)
    with pytest.raises(RuntimeError, match="UNIT_STOP_BOUNDARY"):
        module.cleanup(owner, [])
    assert calls == ["keeper"]


def test_loaded_absence_with_successful_empty_manager_lookup_never_reads_properties(
    module: ModuleType, owner: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def protocol(own: object, argv: list[str]) -> tuple[int, str]:
        calls.append(argv)
        if "ListUnitsByPatterns" in argv:
            return 0, "a(ssssssouso) 0\n"
        return (
            0,
            "Id="
            + module.unit_name(owner, "parent")
            + "\nLoadState=loaded\nTransient=no\n",
        )

    monkeypatch.setattr(module, "invoke", protocol)
    assert module.show_unit(owner, "parent") is None
    assert len(calls) == 1 and "ListUnitsByPatterns" in calls[0]
    assert "/usr/bin/systemctl" not in calls[0]


def test_fresh_start_uses_loaded_only_lookup_before_atomic_creation(
    module: ModuleType, owner: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def protocol(own: object, argv: list[str]) -> tuple[int, str]:
        calls.append(argv)
        if "ListUnitsByPatterns" in argv:
            return 0, "a(ssssssouso) 0\n"
        if "StartTransientUnit" in argv:
            raise RuntimeError("UNIT_CREATE_BOUNDARY_NO_COMMAND_EXECUTED")
        return 0, "LoadState=loaded\nTransient=no\n"

    monkeypatch.setattr(module, "invoke", protocol)
    with pytest.raises(RuntimeError, match="UNIT_CREATE_BOUNDARY"):
        module.start(owner)
    assert all("ListUnitsByPatterns" in argv for argv in calls[:-1])
    assert "StartTransientUnit" in calls[-1]


def _loaded_reply(module: ModuleType, owner: object, role: str) -> str:
    """Model the documented busctl typed array, never a real manager reply."""
    name = module.unit_name(owner, role)
    path = "/org/freedesktop/systemd1/unit/" + name.replace(".", "_2e")
    return f'a(ssssssouso) 1 "{name}" "private description" "loaded" "active" "running" "" "{path}" 0 "" "/"\n'


def test_loaded_unit_with_exact_positive_array_reads_properties_only_after_presence(
    module: ModuleType, owner: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def protocol(own: object, argv: list[str]) -> tuple[int, str]:
        calls.append(argv)
        if "ListUnitsByPatterns" in argv:
            return 0, _loaded_reply(module, owner, "parent")
        return 0, "LoadState=loaded\nId=" + module.unit_name(owner, "parent") + "\n"

    monkeypatch.setattr(module, "invoke", protocol)
    assert module.show_unit(owner, "parent")["LoadState"] == "loaded"
    assert len(calls) == 2 and "ListUnitsByPatterns" in calls[0]
    assert calls[0][-4:] == ["asas", "0", "1", module.unit_name(owner, "parent")]
    assert calls[1][0] == "/usr/bin/systemctl"


@pytest.mark.parametrize(
    "reply",
    [
        "",
        "a(ssssssouso) 0 EXTRA",
        "a(ssssssouso) 2",
        "a(s) 0",
        'a(ssssssouso) 1 "foreign.slice" "d" "loaded" "active" "running" "" "/foreign" 0 "" "/"',
        'a(ssssssouso) 1 "unterminated',
    ],
)
def test_loaded_unit_with_malformed_or_foreign_array_rejects_not_absent(
    module: ModuleType, owner: object, reply: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "invoke", lambda own, argv: (0, reply))
    with pytest.raises(ValueError):
        module.loaded_unit(owner, "parent")


def test_loaded_unit_with_command_error_never_infers_absence(
    module: ModuleType, owner: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "invoke", lambda own, argv: (1, "a(ssssssouso) 0"))
    with pytest.raises(RuntimeError):
        module.loaded_unit(owner, "parent")


def test_await_absent_with_loaded_then_empty_never_reads_unit_properties(
    module: ModuleType, owner: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    replies = iter([_loaded_reply(module, owner, "parent"), "a(ssssssouso) 0"])

    def protocol(own: object, argv: list[str]) -> tuple[int, str]:
        calls.append(argv)
        assert "ListUnitsByPatterns" in argv
        return 0, next(replies)

    monkeypatch.setattr(module, "invoke", protocol)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    module.await_absent(owner, "parent")
    assert len(calls) == 2


@pytest.mark.parametrize("pids", ["123\n123\n", "0\n", "-1\n", "123 456\n", "00123\n"])
def test_cleanup_with_untrustworthy_keeper_pid_file_refuses_every_stop(
    module: ModuleType,
    owner: object,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pids: str,
) -> None:
    path = _keeper_tree(module, owner, tmp_path, monkeypatch)
    (path / module.unit_name(owner, "keeper") / "cgroup.procs").write_text(pids)
    stops = []
    monkeypatch.setattr(module, "stop_owned", lambda own, role: stops.append(role))
    with pytest.raises(ValueError):
        module.cleanup(owner, [])
    assert stops == []


def test_stop_owned_with_late_foreign_keeper_pid_rechecks_before_command(
    module: ModuleType, owner: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _keeper_tree(module, owner, tmp_path, monkeypatch)
    parent = module.show_unit(owner, "parent")
    module.no_foreign_children(owner, parent)
    (path / module.unit_name(owner, "keeper") / "cgroup.procs").write_text("123\n456\n")
    calls = []
    monkeypatch.setattr(module, "invoke", lambda own, argv: calls.append(argv))
    with pytest.raises(ValueError):
        module.stop_owned(owner, "keeper")
    assert calls == []


def test_stop_owned_parent_with_late_unknown_process_retains_all_units(
    module: ModuleType, owner: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _keeper_tree(module, owner, tmp_path, monkeypatch)
    (path / "cgroup.procs").write_text("456\n")
    calls = []
    monkeypatch.setattr(module, "invoke", lambda own, argv: calls.append(argv))
    with pytest.raises(ValueError):
        module.stop_owned(owner, "parent")
    assert calls == []


def test_keeper_properties_with_owned_service_only_select_process_kill_mode(
    module: ModuleType, owner: object
) -> None:
    assert ("KillMode", "s", ["process"]) in module.keeper_properties(owner)
    assert not any(
        name == "KillMode" for name, _, _ in module.unit_properties(owner, "parent")
    )


def test_cleanup_with_wrong_actual_keeper_kill_mode_refuses_stop(
    module: ModuleType, owner: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _keeper_tree(module, owner, tmp_path, monkeypatch)
    original = module.show_unit

    def properties(own: object, role: str) -> dict:
        row = original(own, role)
        if role == "keeper":
            row["KillMode"] = "control-group"
        return row

    monkeypatch.setattr(module, "show_unit", properties)
    stops = []
    monkeypatch.setattr(module, "stop_owned", lambda own, role: stops.append(role))
    with pytest.raises(ValueError):
        module.cleanup(owner, [])
    assert stops == []


def test_stop_owned_with_empty_failed_parent_confirms_absence_without_loading(
    module: ModuleType, owner: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = _unit_row(module, owner, "parent")
    parent.update(ControlGroup="", ActiveState="failed", MainPID="0")
    monkeypatch.setattr(
        module, "show_unit", lambda own, role: parent if role == "parent" else None
    )
    calls = []

    def protocol(own: object, argv: list[str]) -> tuple[int, str]:
        calls.append(argv)
        return 0, "a(ssssssouso) 0" if "ListUnitsByPatterns" in argv else 'o "/job"'

    monkeypatch.setattr(module, "invoke", protocol)
    module.stop_owned(owner, "parent")
    assert len(calls) == 2
    assert "StopUnit" in calls[0] and "ListUnitsByPatterns" in calls[1]


def test_process_ids_with_symlinked_receipt_rejects_foreign_file(
    module: ModuleType, tmp_path: Path
) -> None:
    root = tmp_path / "group"
    root.mkdir()
    private = tmp_path / "foreign-members"
    private.write_text("123\n")
    (root / "cgroup.procs").symlink_to(private)
    with pytest.raises(ValueError, match="Aliased"):
        module.process_ids(root)
    assert private.read_text() == "123\n"


def test_command_failure_with_loaded_lookup_preserves_lookup_not_stop_enum(
    module: ModuleType, owner: object
) -> None:
    module.record_command_failure(
        owner,
        module.loaded_arguments(owner, "parent"),
        1,
        "org.freedesktop.DBus.Error.AccessDenied",
    )
    row = module.checked_private(owner.root / "aggregate-command-failure.json")
    module.validate_failure_record(row)
    assert row["operation"] == "LOOKUP_PARENT"
