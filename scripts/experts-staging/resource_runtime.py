"""Explicit invocation-owned measured profile; no implicit registry or host defaults."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

import aggregate
import resource_profile as profile
from benchmark_metrics import parse_memory

_FIELDS = {
    "id": ".Id",
    "pid": ".State.Pid",
    "running": ".State.Running",
    "parent": ".HostConfig.CgroupParent",
    "memory": ".HostConfig.Memory",
    "swap": ".HostConfig.MemorySwap",
    "owner": 'index .Config.Labels "io.featurefactory.experts.owner"',
    "fixture": 'index .Config.Labels "io.featurefactory.experts.fixture"',
    "readonly": ".HostConfig.ReadonlyRootfs",
    "cap_drop": ".HostConfig.CapDrop",
    "security": ".HostConfig.SecurityOpt",
    "restarts": ".RestartCount",
    "oom_killed": ".State.OOMKilled",
}


@dataclass
class ResourceRun:
    """One explicit owned lifecycle; all actual dependencies and state are visible."""

    root: Path
    manifest: dict[str, Any]
    remote: ModuleType
    owner: aggregate.Owner | None = None
    members: dict[str, bool] = field(default_factory=dict)

    def start(self) -> None:
        """Create only the bounded own parent after actual driver validation.

        :return: None after real hardmax/swap/source/keeper verification.
        :raises Exception: Driver, identity, kernel or creation guard fails.
        """
        raw = self.remote.command(
            [
                "docker",
                "info",
                "--format",
                '{"driver":{{json .CgroupDriver}},"version":{{json .CgroupVersion}}}',
            ]
        )
        aggregate.require_driver(json.loads(raw))
        self.owner = aggregate.plan(
            self.root, self.manifest["nonce"], self.manifest["control_revision"]
        )
        aggregate.start(self.owner)

    def guard(self) -> None:
        """Require actual remaining parent allowance plus unchanged host reserve.

        :return: None after actual owned headroom and fresh host capacity pass.
        :raises ValueError: No positively verified active parent or reserve.
        """
        if self.owner is None:
            raise ValueError("Verified measured parent required before any container.")
        aggregate.guard(self.owner)

    def member(self, role: str, names: dict[str, str]) -> None:
        """Prove actual source/labels/caps and host PID ancestry for each child.

        :param role: Fixed web/db/browser role.
        :param names: Exact invocation names.
        :return: None after actual immutable membership is pinned privately.
        :raises Exception: Any actual parent or role identity differs.
        """
        if self.owner is None:
            raise ValueError("Verified parent required for actual membership.")
        self.remote.assert_resource(
            self.root, "container", names[role], self.manifest["nonce"]
        )
        aggregate.verify_member(
            self.owner, role, container_row(self.remote, self.root, names[role])
        )
        self.members[role] = True

    def retain(self, names: dict[str, str]) -> None:
        """Keep closed per-case actual role/parent evidence before any cleanup.

        :param names: Positively owned resource names.
        :return: None after canonical safe projection is retained.
        :raises Exception: Failed resource proof remains failed after retention.
        """
        parent = None
        roles = {}
        try:
            if self.owner is not None:
                parent = aggregate.observe(self.owner)
        except Exception:  # noqa: BLE001 - unavailable stays explicitly failed.
            parent = None
        for role in profile.CAPS:
            try:
                roles[role] = capture_role(self, names, role)
            except Exception:  # noqa: BLE001 - never export arbitrary error text.
                roles[role] = {"status": "UNAVAILABLE"}
        record = profile.receipt_payload(self.manifest, parent, roles)
        try:
            record["status"] = "VERIFIED"
            profile.validate_measurements(record, True)
        except Exception:
            record["status"] = "FAILED"
            write_receipt(self.root, record)
            raise
        write_receipt(self.root, record)


def create(
    root: Path, manifest: dict[str, Any], remote: ModuleType
) -> ResourceRun | None:
    """Validate fixed transported proof before any profile-owned mutation.

    :param root: Positive private invocation root.
    :param manifest: Authenticated source/image/control identity.
    :param remote: Explicit actual host adapter.
    :return: Fresh explicit state or unchanged defaultNone.
    :raises ValueError: Unknown selector or immutable proof mismatch.
    """
    if not profile.selected(manifest):
        return None
    profile.validate_files(root / "runtime", manifest)
    return ResourceRun(root, manifest, remote)


def container_row(remote: ModuleType, root: Path, name: str) -> dict[str, Any]:
    """Acquire only fixed non-secret real container identity and bounds.

    :param remote: Actual explicit Docker adapter.
    :param root: Owned private configuration.
    :param name: Exact owned resource name.
    :return: Typed curated private identity, never Env or arbitrary Config.
    :raises ValueError: Actual curated fields differ.
    """
    template = (
        "{"
        + ",".join(f'"{key}":{{{{json ({value})}}}}' for key, value in _FIELDS.items())
        + "}"
    )
    row = json.loads(
        remote.docker(root, "container", "inspect", "--format", template, name)
    )
    if not isinstance(row, dict) or set(row) != set(_FIELDS):
        raise ValueError("Exact curated container observation required.")
    return row


def capture_role(run: ResourceRun, names: dict[str, str], role: str) -> dict[str, Any]:
    """Read post-effects actual PG/web counters and before-exit browser counters.

    :param run: Explicit invocation state.
    :param names: Exact positively owned resource names.
    :param role: Fixed role.
    :return: Actual numeric memory/Docker/ancestry projection.
    :raises Exception: Missing data never becomes a passing measurement.
    """
    run.remote.assert_resource(
        run.root, "container", names[role], run.manifest["nonce"]
    )
    row = container_row(run.remote, run.root, names[role])
    memory, member = capture_memory(run, names, role, row)
    return {
        "memory": memory,
        "oom_killed": row["oom_killed"],
        "restarts": row["restarts"],
        "member_verified": member,
    }


def browser_record(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Revalidate exact canonical private observation and this fresh case binding.

    :param root: Owned evidence root.
    :param manifest: Authenticated case/source/nonce.
    :return: Actual before-exit numeric browser observation.
    :raises ValueError: Hidden raw bytes, shape or identity differs.
    """
    path = root / "output/private/resource-browser-memory.json"
    if path.is_symlink() or path.stat().st_nlink != 1 or path.stat().st_size > 8192:
        raise ValueError("Unsafe private browser memory observation.")
    raw = path.read_bytes()
    row = json.loads(raw)
    expected = {key: manifest[key] for key in ("nonce", "source_revision")}
    expected.update(
        case=profile.selected_case(manifest).case,
        suite_phase=profile.selected_case(manifest).phase,
        memory=row.get("memory"),
    )
    if row != expected or profile.canonical(row) != raw:
        raise ValueError("Canonical source/case-bound browser counters required.")
    return row["memory"]


def write_receipt(root: Path, record: dict[str, Any]) -> None:
    """Retain actual projection with exclusive private-mode public admission pending.

    :param root: Verified invocation root.
    :param record: Closed actual numeric projection.
    :return: None after a single resource receipt exists.
    :raises OSError: The receipt already exists or cannot be retained.
    """
    with (root / "output/resource-receipt.json").open("xb") as stream:
        stream.write(profile.canonical(record))


def cleanup(root: Path, manifest: dict[str, Any], remote: ModuleType) -> None:
    """Remove own parent only after successful exact Docker inventory absence.

    :param root: Retained positive private runtime.
    :param manifest: Authenticated profile/nonce/control identity.
    :param remote: Explicit actual Docker adapter.
    :return: None only after both owned units/kernel group are absent.
    :raises Exception: Any uncertain cleanup retains private owner evidence.
    """
    if not profile.selected(manifest):
        return
    marker = root / "aggregate-owner.json"
    if not marker.exists() and not marker.is_symlink():
        require_unallocated(root, manifest, remote)
        return
    row = aggregate.checked_private(marker)
    owner = aggregate.Owner(
        root, manifest["nonce"], manifest["control_revision"], row["token"], row["boot"]
    )
    aggregate.check_owner(owner)
    names = remote.resource_names(manifest["nonce"])
    aggregate.cleanup(owner, remaining_containers(remote, root, names))


def parent(run: ResourceRun | None) -> str | None:
    """Return only the positively started explicit parent, preserving defaultNone.

    :param run: Explicit measured state or unchanged default.
    :return: Derived verified parent name.
    :raises ValueError: Aggregate state has not been verified yet.
    """
    if run is None:
        return None
    if run.owner is None:
        raise ValueError("Actual verified parent required.")
    return aggregate.parent_name(run.owner.nonce)


def parent_arguments(nonce: str, name: str | None) -> list[str]:
    """Prevent redirecting companion resources into an ambient cgroup.

    :param nonce: Exact positive owner identity.
    :param name: Optional exact derived parent.
    :return: Fixed Docker parent arguments, empty for unchanged defaults.
    :raises ValueError: Parent does not belong to this invocation.
    """
    if name is None:
        return []
    if name != aggregate.parent_name(nonce):
        raise ValueError("Foreign aggregate parent rejected.")
    return ["--cgroup-parent", name, "--pull=never"]


def capacity(run: ResourceRun, cache: dict[str, Any]) -> dict[str, Any]:
    """Require measured fixed warm-image profile and fresh1280MiB/1GiB budget.

    :param run: Explicit proof-validated invocation.
    :param cache: Actual exact image metadata from this fresh idle host.
    :return: Fresh safe capacity with whitelisted positive cache observations.
    :raises ValueError: Incomplete cache or fresh fixed reserve is unsafe.
    """
    import_guard = run.remote.image_cache_reserve(run.manifest, cache) == 1024**3
    values = dict(
        line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines()
    )
    memory = int(values["MemAvailable"].split()[0]) * 1024
    docker_root = json.loads(
        run.remote.command(["docker", "info", "--format", "{{json .DockerRootDir}}"])
    )
    disk = run.remote.shutil.disk_usage(docker_root).free
    try:
        profile.require_capacity(memory, disk, import_guard)
    except ValueError:
        retain_capacity_failure(run, memory, disk, import_guard)
        raise
    return {
        "available_memory_bytes": memory,
        "available_docker_disk_bytes": disk,
        "required_memory_bytes": 1280 * profile.MIB,
        "required_disk_bytes": 1024**3,
        "image_cache_verified": import_guard,
        "image_cache": cache,
    }


def verify_stopped_browser(run: ResourceRun, row: dict[str, Any]) -> None:
    """Pin the completed actual browser to its previously proved child identity.

    :param run: Positive invocation with initial actual ancestry proof.
    :param row: Actual curated post-exit Docker state.
    :return: None only for identical container, parent and immutable member record.
    :raises ValueError: Parent/identity/caps drifted after the live proof.
    """
    if run.owner is None or row["parent"] != aggregate.parent_name(run.owner.nonce):
        raise ValueError("Completed browser parent differs.")
    expected = {
        "id": row["id"],
        "path": "/" + row["parent"] + "/docker-" + row["id"] + ".scope",
    }
    original = aggregate.checked_private(run.root / "aggregate-member-browser.json")
    if original != expected:
        raise ValueError("Completed browser lacks its original actual ancestry proof.")
    if row["memory"] != 768 * profile.MIB or row["swap"] != 768 * profile.MIB:
        raise ValueError("Completed browser enforced caps differ.")


def role_memory(run: ResourceRun, name: str, role: str) -> dict[str, Any]:
    """Read actual running role counters after case database/mail effects.

    :param run: Explicit positive invocation.
    :param name: Exact owned container.
    :param role: Fixed web or database role.
    :return: Strict actual cgroup counters.
    :raises Exception: Role is stopped or counters differ from enforced cap.
    """
    text = run.remote.docker(
        run.root,
        "exec",
        name,
        "cat",
        "/sys/fs/cgroup/memory.peak",
        "/sys/fs/cgroup/memory.max",
        "/sys/fs/cgroup/memory.events",
    )
    return parse_memory(text, role, profile.CAPS[role] * profile.MIB)


def remaining_containers(
    remote: ModuleType, root: Path, names: dict[str, str]
) -> list[str]:
    """Positively inventory all containers before exact parent cleanup.

    :param remote: Explicit actual Docker adapter.
    :param root: Owned configuration.
    :param names: Exact invocation resource names.
    :return: Own role names that still exist; inventory failure is never absence.
    :raises Exception: Actual Docker inventory fails.
    """
    existing = remote.docker(
        root, "container", "ls", "--all", "--format", "{{.Names}}", timeout=20
    ).splitlines()
    return [
        name
        for role, name in names.items()
        if role in profile.CAPS and name in existing
    ]


def require_unallocated(
    root: Path, manifest: dict[str, Any], remote: ModuleType
) -> None:
    """Require positive absence when creation never left an ownership marker.

    :param root: Retained private invocation root.
    :param manifest: Authenticated exact nonce/control identity.
    :param remote: Explicit read-only command adapter.
    :return: None only after both loaded-only unit lookups and kernel absence.
    :raises Exception: Missing evidence never authorizes stopping or disposal.
    """
    names_only = aggregate.Owner(
        root, manifest["nonce"], manifest["control_revision"], "0" * 32, "0" * 36
    )
    for role in ("parent", "keeper"):
        text = remote.command(aggregate.loaded_arguments(names_only, role))
        if aggregate.parse_loaded(text, aggregate.unit_name(names_only, role)):
            raise ValueError("Missing aggregate owner marker with a loaded unit.")
    kernel = Path("/sys/fs/cgroup") / aggregate.parent_name(manifest["nonce"])
    if kernel.exists() or kernel.is_symlink():
        raise ValueError(
            "Missing aggregate owner marker with a remaining kernel group."
        )


def start(run: ResourceRun | None) -> None:
    """Start the explicit measured parent, preserving unchanged default behavior.

    :param run: Proof-validated measured state or defaultNone.
    :return: None after positive actual parent and live reserve checks.
    :raises Exception: Parent creation or actual guard fails.
    """
    if run is not None:
        run.start()
        run.guard()


def capture_memory(
    run: ResourceRun, names: dict[str, str], role: str, row: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    """Preserve known Docker state if actual counters cannot be obtained.

    :param run: Explicit positive invocation state.
    :param names: Exact owned container names.
    :param role: Fixed actual role.
    :param row: Already acquired curated Docker identity.
    :return: Actual memory or explicit unavailable slot, with actual membership flag.
    :raises Exception: Curated Docker acquisition errors remain outside this helper.
    """
    member = False
    try:
        if role == "browser":
            verify_stopped_browser(run, row)
            member = True
            return browser_record(run.root, run.manifest), member
        run.member(role, names)
        member = True
        return role_memory(run, names[role], role), member
    except Exception:  # noqa: BLE001 - fixed unavailable observation, no raw errors.
        return {"status": "UNAVAILABLE"}, member


def retain_capacity_failure(
    run: ResourceRun, memory: int, disk: int, cached: bool
) -> None:
    """Record actual numeric observations before rejecting an unsafe initial guard.

    :param run: Positively owned invocation; no container has been created.
    :param memory: Actual fresh available memory bytes.
    :param disk: Actual fresh Docker-storage bytes.
    :param cached: Actual complete fixed image-cache validation result.
    :return: None after one private-mode, closed numeric receipt is retained.
    :raises ValueError: Invalid types/ownership cannot create a public observation.
    """
    row = profile.capacity_observation(memory, disk, cached)
    output = owned_capacity_output(run.root)
    descriptor = os.open(
        output / "capacity.json",
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(profile.canonical(row))


def owned_capacity_output(root: Path) -> Path:
    """Create only the positive invocation's unaliased private-mode output directory.

    :param root: Already verified own runtime root.
    :return: Actual own output directory for finite diagnostic fields only.
    :raises ValueError: Any alias, foreign UID or permission drift is unsafe.
    """
    output = root / "output"
    output.mkdir(mode=0o700, exist_ok=True)
    if (
        output.is_symlink()
        or output.resolve() != output
        or output.stat().st_uid != os.getuid()
        or output.stat().st_mode & 0o777 != 0o700
    ):
        raise ValueError("Positively owned capacity output required.")
    return output
