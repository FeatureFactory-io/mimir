"""CI-only positively owned systemd-v2 parent; no global or application settings."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmark_metrics import parse_events

LIMIT_BYTES = 960 * 1024 * 1024
RESERVE_BYTES = 256 * 1024 * 1024
ROLE_MEMORY_MIB = {"web": 384, "db": 192, "browser": 768}
_FIELDS = (
    "Id",
    "Description",
    "LoadState",
    "ActiveState",
    "Transient",
    "ControlGroup",
    "MainPID",
    "MemoryMax",
    "MemorySwapMax",
    "KillMode",
)
_ROOT = Path("/sys/fs/cgroup")
_FORMAT = "mimir-experts-owned-aggregate-v1"
_OPERATIONS = {
    action + "_" + role
    for action in ("START", "STOP", "LOOKUP")
    for role in ("PARENT", "KEEPER")
}


@dataclass(frozen=True)
class Owner:
    """Immutable private identity; its token and descriptions are never exported."""

    root: Path
    nonce: str
    source: str
    token: str
    boot: str


def parent_name(nonce: str) -> str:
    """Derive one root slice without implicit hyphen-separated ancestors.

    :param nonce: Fresh32hex positive owner identity.
    :return: Exact transient slice name.
    :raises ValueError: Unsafe owner identity.
    """
    if not isinstance(nonce, str) or not re.fullmatch(r"[a-f0-9]{32}", nonce):
        raise ValueError("Invalid aggregate owner identity.")
    return f"mimirexperts{nonce}.slice"


def unit_name(owner: Owner, role: str) -> str:
    """Derive only the two exact temporary owned unit names.

    :param owner: Immutable invocation identity.
    :param role: Parent or keeper.
    :return: Closed derived unit name.
    :raises ValueError: Unknown unit role.
    """
    parent_name(owner.nonce)
    if role == "parent":
        return parent_name(owner.nonce)
    if role != "keeper":
        raise ValueError("Unknown aggregate unit role.")
    return f"mimirexperts{owner.nonce}keeper.service"


def validate_profile(name: str, web: int, browser: int) -> bool:
    """Admit only default or the fixed CI aggregate preset.

    :param name: Closed resource profile.
    :param web: Explicit web memory cap.
    :param browser: Explicit browser memory cap.
    :return: Whether aggregate960 is selected.
    :raises ValueError: Unknown profile or contradictory caps.
    """
    if type(name) is not str or name not in {"default", "aggregate960"}:
        raise ValueError("Unknown resource profile.")
    if name == "aggregate960" and (
        type(web) is not int or type(browser) is not int or web != 384 or browser != 768
    ):
        raise ValueError("Aggregate profile requires web384 PG192 browser768.")
    return name == "aggregate960"


def validate_remaining(available: int, current: int, maximum: int) -> None:
    """Require fresh capacity for actual remaining parent budget plus reserve.

    :param available: Actual fresh MemAvailable bytes.
    :param current: Actual owned parent memory.current.
    :param maximum: Actual parent memory.max.
    :return: None after hard-budget arithmetic succeeds.
    :raises ValueError: Invalid counters, limit or insufficient reserve.
    """
    if any(type(value) is not int for value in (available, current, maximum)):
        raise ValueError("Typed aggregate capacity is required.")
    if maximum != LIMIT_BYTES or not 0 < current <= maximum:
        raise ValueError("Aggregate parent budget is unverified.")
    if available < maximum - current + RESERVE_BYTES:
        raise ValueError("Aggregate remaining budget exceeds fresh reserve.")


def counter(text: str) -> int:
    """Accept only finite bounded unsigned kernel numbers.

    :param text: Actual counter text.
    :return: Nonnegative integer.
    :raises ValueError: Unlimited, malformed or oversized value.
    """
    value = text.strip()
    if not re.fullmatch(r"[0-9]{1,20}", value):
        raise ValueError("Invalid aggregate kernel counter.")
    return int(value)


def read_group(path: Path) -> dict[str, Any]:
    """Read actual cgroup counters; unit fixtures are not kernel proof.

    :param path: Positively verified cgroup or explicit unit fixture.
    :return: Strict numeric concurrent observations.
    :raises ValueError: Counter, cap, swap or event mismatch.
    :raises OSError: Required counters are unavailable.
    """
    names = {
        "current_bytes": "memory.current",
        "peak_bytes": "memory.peak",
        "limit_bytes": "memory.max",
        "swap_current_bytes": "memory.swap.current",
        "swap_limit_bytes": "memory.swap.max",
    }
    row = {key: counter((path / name).read_text()) for key, name in names.items()}
    if (
        row["limit_bytes"] != LIMIT_BYTES
        or not 0 <= row["current_bytes"] <= row["peak_bytes"]
    ):
        raise ValueError("Aggregate kernel limit or peak differs.")
    if row["swap_current_bytes"] != 0 or row["swap_limit_bytes"] != 0:
        raise ValueError("Aggregate swap must remain disabled.")
    row["events"] = parse_events((path / "memory.events").read_text().splitlines())
    row["populated"] = populated(path)
    return row


def populated(path: Path) -> bool:
    """Read task-population state without exporting unknown kernel fields.

    :param path: Actual cgroup directory.
    :return: Whether this cgroup or its descendants contain processes.
    :raises ValueError: Missing, duplicated or unknown population fields.
    """
    rows = [line.split() for line in (path / "cgroup.events").read_text().splitlines()]
    values = {}
    for parts in rows:
        if (
            len(parts) != 2
            or parts[0] not in {"populated", "frozen"}
            or parts[0] in values
            or parts[1] not in {"0", "1"}
        ):
            raise ValueError("Invalid aggregate population counters.")
        values[parts[0]] = parts[1]
    if "populated" not in values:
        raise ValueError("Missing aggregate population counter.")
    return values["populated"] == "1"


def require_headroom(row: dict[str, Any]) -> None:
    """Keep every aggregate max/OOM event a failed experiment.

    :param row: Strict actual parent observation.
    :return: None for positive headroom and zero exhaustion events.
    :raises ValueError: The owned budget was exhausted.
    """
    if row["peak_bytes"] >= LIMIT_BYTES or any(
        row["events"].get(key, 0)
        for key in ("max", "oom", "oom_kill", "oom_group_kill")
    ):
        raise ValueError("Aggregate memory envelope was exhausted.")


def private_json(path: Path, value: dict[str, Any]) -> None:
    """Create an exclusive private ownership or identity receipt.

    :param path: New file within the verified private root.
    :param value: Private fixed-schema record.
    :return: None after mode0600 write.
    :raises OSError: Existing/linked file or write failure.
    """
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w") as stream:
        json.dump(value, stream, sort_keys=True)


def verify_root(root: Path, nonce: str) -> None:
    """Borrow the exact root/owner guards without importing the remote runner.

    :param root: Existing invocation root.
    :param nonce: Expected owner identity.
    :return: None after actual private filesystem ownership agrees.
    :raises ValueError: Root, UID, mode or controller marker differs.
    """
    parent_name(nonce)
    if root != Path("/var/tmp") / f"mimir-experts-{nonce}" or root.resolve() != root:
        raise ValueError("Unsafe aggregate private root.")
    metadata = root.stat()
    if metadata.st_uid != os.getuid() or metadata.st_mode & 0o777 != 0o700:
        raise ValueError("Aggregate root must remain private.")
    marker = checked_private(root / "controller-owner.json")
    if marker.get("nonce") != nonce:
        raise ValueError("Aggregate controller owner differs.")


def checked_private(path: Path) -> dict[str, Any]:
    """Read only a bounded actual private marker.

    :param path: Exact marker destination.
    :return: Parsed private object, never exported.
    :raises ValueError: Aliases, ownership, mode, size or shape differs.
    """
    if path.resolve() != path or not path.is_file():
        raise ValueError("Invalid aggregate private marker.")
    metadata = path.stat()
    if (
        metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
        or metadata.st_mode & 0o777 != 0o600
        or metadata.st_size > 16384
    ):
        raise ValueError("Unsafe aggregate private marker bounds.")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("Invalid aggregate private marker shape.")  # noqa: TRY004
    return value


def owner_record(owner: Owner) -> dict[str, str]:
    """Build the exact private source/boot/UUID ownership declaration.

    :param owner: Immutable validated invocation identity.
    :return: Closed private ownership fields.
    """
    return {
        "format": _FORMAT,
        "nonce": owner.nonce,
        "source": owner.source,
        "token": owner.token,
        "boot": owner.boot,
        "parent": unit_name(owner, "parent"),
        "keeper": unit_name(owner, "keeper"),
    }


def plan(root: Path, nonce: str, source: str) -> Owner:
    """Record a fresh owner before any transient unit operation.

    :param root: Verified existing private invocation root.
    :param nonce: Fresh controller UUID.
    :param source: Exact reviewed control Git SHA.
    :return: Immutable positively owned plan.
    :raises ValueError: Root or source identity differs.
    """
    verify_root(root, nonce)
    if not isinstance(source, str) or not re.fullmatch(r"[a-f0-9]{40}", source):
        raise ValueError("Exact aggregate control source is required.")
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    owner = Owner(root, nonce, source, os.urandom(16).hex(), boot)
    private_json(root / "aggregate-owner.json", owner_record(owner))
    check_owner(owner)
    return owner


def check_owner(owner: Owner) -> None:
    """Recheck immutable private owner identity before every host unit operation.

    :param owner: Source/nonce/token-bound invocation.
    :return: None after private marker and boot continuity agree.
    :raises ValueError: A stale or foreign owner is detected.
    """
    verify_root(owner.root, owner.nonce)
    if (
        not re.fullmatch(r"[a-f0-9]{40}", owner.source)
        or not re.fullmatch(r"[a-f0-9]{32}", owner.token)
        or not re.fullmatch(r"[a-f0-9-]{36}", owner.boot)
    ):
        raise ValueError("Invalid aggregate private source identity.")
    if checked_private(owner.root / "aggregate-owner.json") != owner_record(owner):
        raise ValueError("Aggregate owner marker changed.")
    if Path("/proc/sys/kernel/random/boot_id").read_text().strip() != owner.boot:
        raise ValueError("Aggregate owner belongs to another boot.")


def description(owner: Owner, role: str) -> str:
    """Build the private unit marker, never a public diagnostic string.

    :param owner: Immutable private identity.
    :param role: Exact owned unit role.
    :return: Exact private source/UUID/token description.
    """
    unit_name(owner, role)
    return f"mimir-experts:{owner.nonce}:{owner.source}:{owner.token}:{role}"


def unit_properties(owner: Owner, role: str) -> list[tuple[str, str, list[str]]]:
    """Build only properties on the temporary owned units, never global settings.

    :param owner: Source-bound private identity.
    :param role: Parent or keeper.
    :return: Typed systemd property tuples.
    """
    common = [
        ("Description", "s", [description(owner, role)]),
        ("MemoryAccounting", "b", ["true"]),
        ("CollectMode", "s", ["inactive-or-failed"]),
    ]
    if role == "parent":
        return [
            *common,
            ("MemoryMax", "t", [str(LIMIT_BYTES)]),
            ("MemorySwapMax", "t", ["0"]),
            ("StopWhenUnneeded", "b", ["false"]),
        ]
    unit_name(owner, role)
    return [*common, *keeper_properties(owner)]


def start_arguments(owner: Owner, role: str) -> list[str]:
    """Build atomic fail-if-existing transient-unit creation without shell text.

    :param owner: Positively owned private identity.
    :param role: Exact parent/keeper role.
    :return: Fixed busctl argument vector.
    """
    properties = unit_properties(owner, role)
    values = [
        item
        for name, signature, arguments in properties
        for item in (name, signature, *arguments)
    ]
    return [
        "/usr/bin/busctl",
        "--system",
        "--timeout=15",
        "call",
        "org.freedesktop.systemd1",
        "/org/freedesktop/systemd1",
        "org.freedesktop.systemd1.Manager",
        "StartTransientUnit",
        "ssa(sv)a(sa(sv))",
        unit_name(owner, role),
        "fail",
        str(len(properties)),
        *values,
        "0",
    ]


def invoke(owner: Owner, argv: list[str]) -> tuple[int, str]:
    """Execute only fixed owned unit commands; unknown output stays private.

    :param owner: Private invocation identity.
    :param argv: Validated fixed command vector.
    :return: Actual exit code and bounded stdout for internal validation.
    :raises RuntimeError: Excessive command output or process timeout.
    """
    check_owner(owner)
    result = subprocess.run(
        argv, capture_output=True, text=True, timeout=20, check=False
    )
    if result.returncode:
        private_failure(owner, result.stderr)
        if argv[0] == "/usr/bin/busctl":
            record_command_failure(owner, argv, result.returncode, result.stderr)
    if len(result.stdout) > 32768:
        raise RuntimeError("Aggregate command output exceeded its bound.")
    return result.returncode, result.stdout


def private_failure(owner: Owner, stderr: str) -> None:
    """Retain a bounded private diagnostic without exporting stderr or paths.

    :param owner: Verified private root.
    :param stderr: Actual failed command diagnostics.
    :return: None after at most32KiB of private acquisition is retained.
    """
    path = owner.root / "aggregate-private.log"
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "wb") as stream:
        metadata = os.fstat(stream.fileno())
        if (
            metadata.st_nlink != 1
            or metadata.st_uid != os.getuid()
            or metadata.st_mode & 0o777 != 0o600
        ):
            raise ValueError("Unsafe aggregate private diagnostic file.")
        stream.write(stderr.encode()[: max(0, 32768 - metadata.st_size)])


def loaded_unit(owner: Owner, role: str) -> bool:
    """Query loaded units without loading absent slice names.

    :param owner: Source-bound private identity.
    :param role: Exact parent or keeper.
    :return: Positive loaded presence or successful empty lookup.
    :raises RuntimeError: Manager lookup failed.
    :raises ValueError: Typed exact-name reply is invalid.
    """
    name = unit_name(owner, role)
    code, text = invoke(owner, loaded_arguments(owner, role))
    if code:
        raise RuntimeError("Owned aggregate loaded-unit lookup failed.")
    return parse_loaded(text, name)


def loaded_arguments(owner: Owner, role: str) -> list[str]:
    """Build a manager enumeration that cannot autoload missing units.

    :param owner: Source-bound private identity.
    :param role: Exact derived unit role.
    :return: Fixed exact literal pattern, empty state filter and typed ABI.
    """
    return [
        "/usr/bin/busctl",
        "--system",
        "--timeout=15",
        "call",
        "org.freedesktop.systemd1",
        "/org/freedesktop/systemd1",
        "org.freedesktop.systemd1.Manager",
        "ListUnitsByPatterns",
        "asas",
        "0",
        "1",
        unit_name(owner, role),
    ]


def parse_loaded(text: str, name: str) -> bool:
    """Validate the successful manager array before admitting presence/absence.

    :param text: Bounded private busctl reply.
    :param name: Exact literal requested unit, never a wildcard.
    :return: Whether the sole exact unit is already loaded.
    :raises ValueError: Signature, count, identity or object path differs.
    """
    tokens = shlex.split(text)
    if tokens == ["a(ssssssouso)", "0"]:
        return False
    expected = "/org/freedesktop/systemd1/unit/" + name.replace(".", "_2e")
    if (
        len(tokens) != 12
        or tokens[:2] != ["a(ssssssouso)", "1"]
        or tokens[2] != name
        or tokens[8] != expected
        or not re.fullmatch(r"[0-9]+", tokens[9])
        or not tokens[11].startswith("/")
    ):
        raise ValueError("Invalid aggregate loaded-unit acquisition.")
    return True


def show_unit(owner: Owner, role: str) -> dict[str, str] | None:
    """Inspect only whitelisted properties of the exact derived unit.

    :param owner: Positive private identity.
    :param role: Parent or keeper.
    :return: Actual private unit metadata, or positively observed absence.
    :raises RuntimeError: The actual manager cannot be read.
    :raises ValueError: Unexpected or duplicate property output.
    """
    if not loaded_unit(owner, role):
        return None
    code, text = invoke(
        owner,
        [
            "/usr/bin/systemctl",
            "show",
            "--no-pager",
            "--property=" + ",".join(_FIELDS),
            unit_name(owner, role),
        ],
    )
    return parse_properties(code, text)


def parse_properties(code: int, text: str) -> dict[str, str]:
    """Validate the positive-loaded unit property read without absence inference.

    :param code: Actual property acquisition status.
    :param text: Bounded private properties.
    :return: Whitelisted unique loaded-unit properties.
    :raises ValueError: Duplicate or unknown property appears.
    :raises RuntimeError: Unit disappeared or acquisition failed.
    """
    values = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if not separator or key not in _FIELDS or key in values:
            raise ValueError("Invalid aggregate unit property acquisition.")
        values[key] = value
    if code or values.get("LoadState") != "loaded":
        raise RuntimeError("Owned aggregate unit read failed.")
    return values


def require_unit_identity(owner: Owner, role: str, row: dict[str, str]) -> None:
    """Reject foreign units before inspecting membership or stopping anything.

    :param owner: Private source/token identity.
    :param role: Exact expected unit role.
    :param row: Actual whitelisted manager properties.
    :return: None only for this invocation's actual transient unit.
    :raises ValueError: Name, description or transient ownership differs.
    """
    if (
        row.get("Id") != unit_name(owner, role)
        or row.get("Description") != description(owner, role)
        or row.get("Transient") != "yes"
    ):
        raise ValueError("Refusing a foreign aggregate unit.")


def wait_active(owner: Owner, role: str) -> dict[str, str]:
    """Wait within a fixed bound for the exact created unit to become active.

    :param owner: Positive private source identity.
    :param role: Parent or keeper.
    :return: Actual active unit metadata.
    :raises RuntimeError: The owned unit failed or did not become active.
    """
    for _ in range(50):
        row = show_unit(owner, role)
        if row is not None:
            require_unit_identity(owner, role, row)
            if row.get("ActiveState") == "active" and (
                role == "parent" or counter(row.get("MainPID", "0")) > 0
            ):
                return row
            if row.get("ActiveState") == "failed":
                break
        time.sleep(0.1)
    raise RuntimeError("Owned aggregate unit did not become active.")


def group_path(owner: Owner, row: dict[str, str]) -> Path:
    """Bind the actual root slice to one real unaliased cgroup directory.

    :param owner: Immutable source/UUID identity.
    :param row: Actual parent unit metadata.
    :return: Exact actual kernel directory.
    :raises ValueError: The actual manager/kernel path differs.
    """
    expected = "/" + parent_name(owner.nonce)
    if row.get("ControlGroup") != expected:
        raise ValueError("Aggregate parent kernel path differs.")
    path = _ROOT / parent_name(owner.nonce)
    if path.resolve() != path or not path.is_dir():
        raise ValueError("Aggregate kernel directory is missing or aliased.")
    return path


def pid_group(pid: int) -> str:
    """Read the real host unified cgroup of one observed running process.

    :param pid: Actual positive manager/Docker PID.
    :return: Actual unified cgroup path for private validation only.
    :raises ValueError: PID or unified hierarchy is invalid.
    """
    if type(pid) is not int or pid <= 0:
        raise ValueError("Positive aggregate process identity required.")
    lines = Path(f"/proc/{pid}/cgroup").read_text().splitlines()
    if len(lines) != 1 or not lines[0].startswith("0::/"):
        raise ValueError("Aggregate requires the actual unified cgroup hierarchy.")
    return lines[0][3:]


def verify_keeper(owner: Owner, row: dict[str, str]) -> None:
    """Verify the tiny keeper is really charged under this exact parent.

    :param owner: Positive private identity.
    :param row: Actual active keeper metadata.
    :return: None after actual PID ancestry matches.
    :raises ValueError: Keeper identity or hierarchy differs.
    """
    require_unit_identity(owner, "keeper", row)
    expected = "/" + parent_name(owner.nonce) + "/" + unit_name(owner, "keeper")
    if (
        row.get("ControlGroup") != expected
        or row.get("KillMode") != "process"
        or pid_group(counter(row.get("MainPID", "0"))) != expected
    ):
        raise ValueError("Aggregate keeper is outside its owned parent.")


def start(owner: Owner) -> None:
    """Create only the owned slice and keeper; verify cap before any container.

    :param owner: Exclusive private owner declaration.
    :return: None after actual active ownership, hard cap and swap proof.
    :raises Exception: Actual unit creation or kernel proof fails.
    """
    for role in ("parent", "keeper"):
        if loaded_unit(owner, role):
            raise ValueError("Aggregate unit name already exists.")
    code, _ = invoke(owner, start_arguments(owner, "parent"))
    if code:
        raise RuntimeError("Owned aggregate parent creation failed.")
    parent = wait_active(owner, "parent")
    path = group_path(owner, parent)
    read_group(path)
    metadata = path.stat()
    private_json(
        owner.root / "aggregate-kernel.json",
        {"inode": metadata.st_ino, "device": metadata.st_dev},
    )
    code, _ = invoke(owner, start_arguments(owner, "keeper"))
    if code:
        raise RuntimeError("Owned aggregate keeper creation failed.")
    verify_keeper(owner, wait_active(owner, "keeper"))
    live(owner)


def live(owner: Owner) -> dict[str, Any]:
    """Require actual positive parent accounting and verified live keeper.

    :param owner: Private source and kernel identity.
    :return: Actual current/peak/limit/event observations.
    :raises Exception: Kernel continuity or live ownership is unproved.
    """
    row = observe(owner)
    if not row["keeper_verified"] or row["current_bytes"] <= 0 or not row["populated"]:
        raise ValueError("Aggregate live ownership accounting is absent.")
    return row


def observe(owner: Owner) -> dict[str, Any]:
    """Retain real parent failure counters even if its own keeper was OOM-killed.

    :param owner: Private source/UUID and pinned kernel identity.
    :return: Only typed actual counters and a fixed keeper-verification boolean.
    :raises Exception: Parent or kernel identity itself cannot be established.
    """
    check_owner(owner)
    parent = show_unit(owner, "parent")
    if parent is None:
        raise ValueError("Aggregate parent is missing.")
    require_unit_identity(owner, "parent", parent)
    path = group_path(owner, parent)
    metadata = path.stat()
    if checked_private(owner.root / "aggregate-kernel.json") != {
        "inode": metadata.st_ino,
        "device": metadata.st_dev,
    }:
        raise ValueError("Aggregate kernel identity changed.")
    row = read_group(path)
    row["keeper_verified"] = keeper_verified(owner)
    return row


def keeper_verified(owner: Owner) -> bool:
    """Classify actual keeper loss without exporting unknown unit metadata.

    :param owner: Private owner declaration.
    :return: Whether the actual keeper identity, active PID and ancestry match.
    """
    try:
        row = show_unit(owner, "keeper")
        if row is None or row.get("ActiveState") != "active":
            return False
        verify_keeper(owner, row)
        return True
    except (ValueError, OSError, RuntimeError):
        return False


def guard(owner: Owner) -> dict[str, Any]:
    """Use real remaining parent budget without counting allocated children twice.

    :param owner: Positively owned active aggregate.
    :return: Actual parent and host reserve observation.
    :raises Exception: Identity, headroom or remaining host reserve fails.
    """
    row = live(owner)
    require_headroom(row)
    available = (
        int(
            next(
                line.split()[1]
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            )
        )
        * 1024
    )
    validate_remaining(available, row["current_bytes"], row["limit_bytes"])
    return {
        **row,
        "available_host_bytes": available,
        "required_host_bytes": row["limit_bytes"]
        - row["current_bytes"]
        + RESERVE_BYTES,
    }


def verify_member(owner: Owner, role: str, row: dict[str, Any]) -> None:
    """Prove actual Docker/PID membership before accepting container work.

    :param owner: Positively owned aggregate.
    :param role: Fixed db/web/browser role.
    :param row: Actual narrow Docker observation.
    :return: None after actual parent and enforced limit proof.
    :raises ValueError: Owner, PID ancestry, limits or hardening differs.
    """
    live(owner)
    identity, expected = validate_member_row(owner, role, row)
    if pid_group(row.get("pid")) != expected:
        raise ValueError("Aggregate child actual PID ancestry differs.")
    record_member(owner, role, {"id": identity, "path": expected})


def stop_arguments(owner: Owner, role: str) -> list[str]:
    """Stop only the exact positively owned temporary unit.

    :param owner: Private positive identity.
    :param role: Parent or keeper.
    :return: Fixed named StopUnit call; no broad reset/revert/prune.
    """
    return [
        "/usr/bin/busctl",
        "--system",
        "--timeout=15",
        "call",
        "org.freedesktop.systemd1",
        "/org/freedesktop/systemd1",
        "org.freedesktop.systemd1.Manager",
        "StopUnit",
        "ss",
        unit_name(owner, role),
        "fail",
    ]


def await_absent(owner: Owner, role: str) -> None:
    """Positively confirm that the owned transient unit was removed.

    :param owner: Private verified identity.
    :param role: Exact parent or keeper.
    :return: None only after actual manager absence.
    :raises RuntimeError: Unit removal was not proved within the bound.
    """
    for _ in range(50):
        if not loaded_unit(owner, role):
            return
        time.sleep(0.1)
    raise RuntimeError("Aggregate unit absence was not confirmed.")


def cleanup(owner: Owner, remaining_containers: list[str]) -> None:
    """Remove only owned units after Docker absence and no foreign descendants.

    :param owner: Retained private ownership evidence.
    :param remaining_containers: Actual successful Docker inventory's own matches.
    :return: None only after keeper, slice and kernel parent are absent.
    :raises Exception: Any container remains, foreign child exists or cleanup fails.
    """
    check_owner(owner)
    if remaining_containers:
        raise ValueError("Aggregate parent cannot stop before Docker cleanup.")
    parent = show_unit(owner, "parent")
    if parent is not None:
        require_unit_identity(owner, "parent", parent)
        if empty_failed_parent(owner, parent):
            stop_owned(owner, "parent")
            return
        no_foreign_children(owner, parent)
    stop_owned(owner, "keeper")
    if parent is not None:
        path = group_path(owner, parent)
        if populated(path) or any(item.is_dir() for item in path.iterdir()):
            raise ValueError("Aggregate parent still contains descendant resources.")
    stop_owned(owner, "parent")
    if (_ROOT / parent_name(owner.nonce)).exists():
        raise ValueError("Aggregate kernel parent was not removed.")


def no_foreign_children(owner: Owner, parent: dict[str, str]) -> None:
    """Refuse broad slice stop if any unexpected descendant cgroup exists.

    :param owner: Private source-bound identity.
    :param parent: Actual positively owned unit metadata.
    :return: None when only the exact keeper remains before its removal.
    :raises ValueError: Foreign or lingering Docker descendants remain.
    """
    path = group_path(owner, parent)
    directories = [
        item for item in path.iterdir() if item.is_dir() or item.is_symlink()
    ]
    if any(item.name != unit_name(owner, "keeper") for item in directories):
        raise ValueError("Refusing aggregate cleanup with unknown descendants.")
    if process_ids(path):
        raise ValueError("Refusing aggregate cleanup with unknown parent processes.")
    for directory in directories:
        require_keeper_tree(owner, directory)


def process_ids(path: Path) -> tuple[int, ...]:
    """Read a real unaliased group's strictly positive unique process IDs.

    :param path: Positively bounded cgroup directory.
    :return: Actual current members, without accepting duplicates.
    :raises ValueError: Aliased directory, malformed PID or duplicates.
    """
    if path.is_symlink() or path.resolve() != path:
        raise ValueError("Aliased aggregate cgroup directory.")
    member_file = path / "cgroup.procs"
    if member_file.is_symlink():
        raise ValueError("Aliased aggregate process file.")
    with member_file.open() as stream:
        text = stream.read(32769)
    if len(text) > 32768:
        raise ValueError("Aggregate process acquisition exceeded its bound.")
    lines = text.splitlines()
    if any(not re.fullmatch(r"[1-9][0-9]{0,9}", line) for line in lines):
        raise ValueError("Invalid aggregate process acquisition.")
    identifiers = tuple(int(line) for line in lines)
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate aggregate process acquisition.")
    return identifiers


def require_keeper_tree(owner: Owner, path: Path) -> None:
    """Reject every keeper descendant and any PID except its fresh MainPID.

    :param owner: Positive private identity.
    :param path: Exact direct keeper cgroup.
    :return: None only for empty stopped or singly owned live keeper.
    :raises ValueError: Nested subgroup, alias or foreign process exists.
    """
    if any(item.is_dir() or item.is_symlink() for item in path.iterdir()):
        raise ValueError("Refusing aggregate cleanup with unknown keeper descendants.")
    identifiers = process_ids(path)
    row = show_unit(owner, "keeper")
    if row is None:
        if identifiers:
            raise ValueError("Unowned aggregate keeper processes remain.")
        return
    require_unit_identity(owner, "keeper", row)
    pid = counter(row.get("MainPID", "0"))
    expected = "/" + parent_name(owner.nonce) + "/" + unit_name(owner, "keeper")
    if (
        pid == 0
        and row.get("ActiveState") in {"inactive", "failed"}
        and not identifiers
        and row.get("ControlGroup") in {"", expected}
        and row.get("KillMode") == "process"
    ):
        return
    verify_keeper(owner, row)
    if identifiers != (pid,):
        raise ValueError("Refusing aggregate cleanup with unknown keeper processes.")


def require_stop_tree(owner: Owner, role: str, row: dict[str, str]) -> None:
    """Repeat the actual tree proof immediately before a unit stop request.

    :param owner: Positive private identity.
    :param role: Exact stop role.
    :param row: Fresh manager properties.
    :return: None only after the relevant process boundary is proved.
    :raises ValueError: Any foreign actor or remaining child is observed.
    """
    if role == "keeper":
        parent = show_unit(owner, "parent")
        if parent is None:
            raise ValueError("Keeper cannot stop without its owned parent.")
        require_unit_identity(owner, "parent", parent)
        no_foreign_children(owner, parent)
        path = group_path(owner, parent) / unit_name(owner, "keeper")
        if path.exists():
            require_keeper_tree(owner, path)
        elif row.get("MainPID") != "0" or row.get("ActiveState") not in {
            "inactive",
            "failed",
        }:
            raise ValueError("Aggregate keeper process group is missing.")
    elif not empty_failed_parent(owner, row):
        path = group_path(owner, row)
        no_foreign_children(owner, row)
        if populated(path) or any(item.is_dir() for item in path.iterdir()):
            raise ValueError("Aggregate parent is not empty before stop.")


def stop_owned(owner: Owner, role: str) -> None:
    """Stop a unit only after its actual private ownership marker matches.

    :param owner: Positive private source identity.
    :param role: Exact derived unit role.
    :return: None after proven absence, including never-created units.
    :raises Exception: Foreign identity or failed stop/absence proof.
    """
    row = show_unit(owner, role)
    if row is None:
        return
    require_unit_identity(owner, role, row)
    require_stop_tree(owner, role, row)
    code, _ = invoke(owner, stop_arguments(owner, role))
    if code:
        raise RuntimeError("Owned aggregate unit stop failed.")
    await_absent(owner, role)


def require_driver(row: dict[str, Any]) -> None:
    """Require actual systemd/v2 rather than inferring host support from a flag.

    :param row: Actual narrowly inspected Docker driver/version fields.
    :return: None for the one supported runtime.
    :raises ValueError: Wrong, partial or extended runtime identity.
    """
    if row != {"driver": "systemd", "version": "2"}:
        raise ValueError("Aggregate requires actual systemd cgroup v2.")


def record_member(owner: Owner, role: str, record: dict[str, str]) -> None:
    """Keep the first exact positive member proof immutable across rechecks.

    :param owner: Private source identity.
    :param role: Known fixed container role.
    :param record: Exact positively verified container/cgroup identity.
    :return: None after original or identical evidence exists.
    :raises ValueError: An existing role identity differs.
    """
    path = owner.root / f"aggregate-member-{role}.json"
    if path.exists() or path.is_symlink():
        if checked_private(path) != record:
            raise ValueError("Aggregate member identity changed.")
        return
    private_json(path, record)


def keeper_properties(owner: Owner) -> list[tuple[str, str, list[str]]]:
    """Build the tiny bounded-life keeper inside the already capped parent.

    :param owner: Positive private identity.
    :return: Only this transient keeper's resource/security properties.
    """

    return [
        ("Slice", "s", [parent_name(owner.nonce)]),
        ("Type", "s", ["simple"]),
        ("KillMode", "s", ["process"]),
        ("User", "s", ["nobody"]),
        ("NoNewPrivileges", "b", ["true"]),
        ("CapabilityBoundingSet", "t", ["0"]),
        ("RuntimeMaxUSec", "t", ["1200000000"]),
        (
            "ExecStart",
            "a(sasb)",
            ["1", "/usr/bin/sleep", "2", "/usr/bin/sleep", "1200", "false"],
        ),
    ]


def validate_member_row(
    owner: Owner, role: str, row: dict[str, Any]
) -> tuple[str, str]:
    """Validate only actual curated child identity and enforced bounds.

    :param owner: Private invocation identity.
    :param role: Fixed container role.
    :param row: Narrow actual Docker fields.
    :return: Exact container ID and expected actual host cgroup path.
    :raises ValueError: Any ownership, cap, swap or privilege field differs.
    """
    if (
        role not in ROLE_MEMORY_MIB
        or row.get("owner") != owner.nonce
        or row.get("fixture") != "CEDAR-RFP-01"
        or row.get("parent") != parent_name(owner.nonce)
    ):
        raise ValueError("Aggregate child ownership or parent differs.")
    identity = row.get("id")
    if not isinstance(identity, str) or not re.fullmatch(r"[a-f0-9]{64}", identity):
        raise ValueError("Invalid aggregate container identity.")
    if not child_bounds(role, row):
        raise ValueError("Aggregate child enforced limit or hardening differs.")
    return identity, "/" + parent_name(owner.nonce) + f"/docker-{identity}.scope"


def empty_failed_parent(owner: Owner, parent: dict[str, str]) -> bool:
    """Allow exact empty owned unit cleanup after creation failed before capping.

    :param owner: Positive private owner.
    :param parent: Actual positively verified unit metadata.
    :return: Whether there is no kernel group and no keeper to remove first.
    :raises ValueError: Contradictory keeper presence makes cleanup unsafe.
    """
    if parent.get("ControlGroup") != "" or (_ROOT / parent_name(owner.nonce)).exists():
        return False
    if show_unit(owner, "keeper") is not None:
        raise ValueError("Unverified aggregate keeper exists.")
    return True


def child_bounds(role: str, row: dict[str, Any]) -> bool:
    """Compare actual typed Docker bounds/hardening with the fixed child preset.

    :param role: Validated fixed role.
    :param row: Actual curated Docker observation.
    :return: Whether every exact enforced bound and privilege guard matches.
    """
    cap = ROLE_MEMORY_MIB[role] * 1024 * 1024
    numeric = (
        type(row.get("memory")) is int
        and row["memory"] == cap
        and type(row.get("swap")) is int
        and row["swap"] == cap
    )
    security = row.get("security")
    return (
        numeric
        and row.get("running") is True
        and row.get("readonly") is True
        and row.get("cap_drop") == ["ALL"]
        and isinstance(security, list)
        and "no-new-privileges" in security
        and type(row.get("restarts")) is int
        and row["restarts"] == 0
    )


def command_action(argv: list[str]) -> str:
    """Classify only the fixed manager operations used by this runtime.

    :param argv: Reviewed fixed manager command vector.
    :return: Closed action enum for the private failure projection.
    :raises ValueError: Unexpected operation is never mislabeled as cleanup.
    """
    actions = {
        "StartTransientUnit": "START",
        "StopUnit": "STOP",
        "ListUnitsByPatterns": "LOOKUP",
    }
    if len(argv) <= 7 or argv[7] not in actions:
        raise ValueError("Unknown aggregate manager operation.")
    return actions[argv[7]]


def record_command_failure(
    owner: Owner, argv: list[str], code: int, stderr: str
) -> None:
    """Retain original command failure with closed enums, never raw private text.

    :param owner: Positive private identity.
    :param argv: Fixed owned busctl command.
    :param code: Actual process exit status.
    :param stderr: Private text inspected only for known ABI error identifiers.
    :return: None after first safe failure receipt is retained privately.
    """
    path = owner.root / "aggregate-command-failure.json"
    if path.exists() or path.is_symlink():
        return
    action = command_action(argv)
    role = "PARENT" if unit_name(owner, "parent") in argv else "KEEPER"
    known = (
        "InvalidArgs",
        "AccessDenied",
        "NotSupported",
        "UnitExists",
        "NoSuchUnit",
        "PropertyReadOnly",
    )
    error = next((name for name in known if "." + name in stderr), "UNCLASSIFIED")
    private_json(
        path,
        {"operation": action + "_" + role, "return_code": code, "manager_error": error},
    )


def failure_receipt(owner: Owner) -> dict[str, Any]:
    """Expose only independently validated original operation/code/error enums.

    :param owner: Private source-bound owner.
    :return: Safe closed failure acquisition, never log strings or token.
    :raises ValueError: Private receipt shape/types or enums were altered.
    """
    path = owner.root / "aggregate-command-failure.json"
    if not path.exists() and not path.is_symlink():
        return {"operation": "KERNEL_OR_OWNER_GUARD", "manager_error": "UNCLASSIFIED"}
    row = checked_private(path)
    validate_failure_record(row)
    return row


def validate_failure_record(row: dict[str, Any]) -> None:
    """Reject arbitrary text/types before publishing the fixed command result.

    :param row: Actual private first-failure record.
    :return: None only for the closed safe projection.
    :raises ValueError: Schema, code or closed enums differ.
    """
    errors = {
        "InvalidArgs",
        "AccessDenied",
        "NotSupported",
        "UnitExists",
        "NoSuchUnit",
        "PropertyReadOnly",
        "UNCLASSIFIED",
    }
    if (
        set(row) != {"operation", "return_code", "manager_error"}
        or not isinstance(row["operation"], str)
        or row["operation"] not in _OPERATIONS
        or type(row["return_code"]) is not int
        or not -255 <= row["return_code"] <= 255
        or not isinstance(row["manager_error"], str)
        or row["manager_error"] not in errors
    ):
        raise ValueError("Invalid aggregate failure projection.")
