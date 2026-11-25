"""Owned host-only companion lifecycle; never reads EB configuration or ambient DBs."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import tarfile
import time
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryFile
from types import FrameType
from typing import Any

from contract import (
    LIVE_DISK_RESERVE,
    image_cache_reserve,
    owner_record,
    validate_pull_capacity,
    validate_runtime_manifest,
)

_HARDENING = (
    "--cap-drop",
    "ALL",
    "--security-opt",
    "no-new-privileges",
    "--read-only",
    "--no-healthcheck",
)
_LABEL = "io.featurefactory.experts.owner"
_CLEANUP_ORDER = (
    ("container", ("browser", "web", "db")),
    ("network", ("egress", "internal")),
)
_FIXTURE_LABEL = "io.featurefactory.experts.fixture=CEDAR-RFP-01"

_TLS_OPTIONS = (
    "req",
    "-x509",
    "-newkey",
    "rsa:2048",
    "-sha256",
    "-nodes",
    "-days",
    "1",
    "-subj",
    "/CN=cedar-web",
    "-addext",
    "subjectAltName=DNS:cedar-web,DNS:localhost,IP:127.0.0.1",
)
_LIMITS = {
    "web": (384, "0.75", 128, 64),
    "db": (192, "0.25", 128, 64),
    "browser": (512, "1", 256, 128),
}
_WEB_BINDS = (
    ("runtime", "/runtime", True),
    ("scope", "/experts-scope", False),
    ("mail", "/experts-mail", False),
    ("static", "/experts-static", False),
    ("output", "/output", False),
    ("tls", "/tls", True),
    ("app-data", "/app/data", False),
)
_DB_BINDS = (
    ("pgdata", "/var/lib/postgresql/data", False),
    ("pg-admin-password", "/run/secrets/pg-password", True),
)
# The image clears PGHOST for its setup client, which uses this default socket.
_POSTGRES_SOCKET_DIRECTORY = "/var/run/postgresql"
_POSTGRES_SOCKET_TMPFS = (
    _POSTGRES_SOCKET_DIRECTORY + ":rw,nosuid,size=1m,uid=999,gid=999,mode=3775"
)
_POSTGRES_SERVER = (
    "postgres",
    "-c",
    f"unix_socket_directories={_POSTGRES_SOCKET_DIRECTORY}",
    "-c",
    "shared_buffers=32MB",
    "-c",
    "max_connections=20",
)
_BROWSER_BINDS = (
    ("runtime", "/runtime", True),
    ("output", "/output", False),
    ("app-data", "/app/data", True),
)
_CACHE_FIELDS = ("Id", "RepoDigests", "Os", "Architecture", "Size")
_CACHE_FORMAT = (
    "{" + ",".join(f'"{field}":{{{{json .{field}}}}}' for field in _CACHE_FIELDS) + "}"
)
_FAILURE_PHASES = {
    "capacity": "capacity",
    "reserve_capacity": "capacity",
    "inspect_cached_images": "image_cache",
    "pull_images": "image_pull",
    "bounded_pull": "image_pull",
    "monitor_pull": "image_pull",
    "start_database": "database_start",
    "wait_database": "database_start",
    "create_app_role": "database_role",
    "write_app_runtime": "runtime_setup",
    "start_web": "web_start",
    "wait_web": "web_readiness",
    "run_browser": "browser",
    "require_browser_reserve": "browser_capacity",
}
_PUBLIC_EXCEPTION_CLASSES = {
    "ValueError",
    "RuntimeError",
    "TimeoutError",
    "OSError",
    "FileNotFoundError",
    "PermissionError",
    "JSONDecodeError",
    "CalledProcessError",
    "TimeoutExpired",
}


def inspect_cached_images(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Read only three exact local image identities without registry operations.

    :param root: Invocation-private Docker configuration path.
    :param manifest: Already validated immutable image references.
    :return: Whitelisted actual records; partial/unreadable cache stays untrusted.
    """
    rows = {}
    for role in ("web", "browser", "postgres"):
        try:
            row = json.loads(
                docker(
                    root,
                    "image",
                    "inspect",
                    "--format",
                    _CACHE_FORMAT,
                    manifest[f"{role}_image"],
                    timeout=20,
                )
            )
        except (RuntimeError, json.JSONDecodeError):
            continue
        if isinstance(row, dict) and set(row) == set(_CACHE_FIELDS):
            rows[role] = row
    return rows


def record_runtime_failure(root: Path, error: Exception) -> None:
    """Retain only safe failure classification, excluding private command output.

    :param root: Positively owned invocation directory.
    :param error: Actual raised exception; its message is never exported.
    :return: None after one exclusive public classification receipt is written.
    :raises ValueError: The evidence destination is linked or unsafe.
    :raises OSError: Existing receipt or filesystem failure prevents safe recording.
    """
    output = root / "output"
    if root.resolve() != root or output.is_symlink():
        raise ValueError("Runtime failure evidence requires an unlinked owned path.")
    output.mkdir(mode=0o700, exist_ok=True)
    frames = [
        {"function": item.name, "line": item.lineno}
        for item in traceback.extract_tb(error.__traceback__)
        if Path(item.filename).name == "remote.py" and item.name in _FAILURE_PHASES
    ]
    kind = type(error).__name__
    record = {
        "status": "FAILED",
        "phase": _FAILURE_PHASES[frames[-1]["function"]] if frames else "owned_runtime",
        "exception_class": kind if kind in _PUBLIC_EXCEPTION_CLASSES else "Exception",
        "source_frames": frames,
        "private_output_exported": False,
    }
    with (output / "runtime-failure.json").open("x") as stream:
        json.dump(record, stream, indent=2)
    print(json.dumps({"stage": "owned_runtime_failure", **record}), flush=True)


def reserve_capacity(
    root: Path, manifest: dict[str, Any], cold_reserve: int
) -> dict[str, Any]:
    """Use actual exact image cache proof while retaining the memory hold.

    :param root: Owned runtime and Docker configuration path.
    :param manifest: Fully validated actual candidate runtime declarations.
    :param cold_reserve: Unchanged original validated cold-image requirement.
    :return: Safe measured capacity, selected reserve and whitelisted cache proof.
    :raises ValueError: Capacity or budget identity is unsafe.
    """
    cache = inspect_cached_images(root, manifest)
    reserve = image_cache_reserve(manifest, cache)
    if reserve not in {cold_reserve, LIVE_DISK_RESERVE}:
        raise ValueError("Actual image budget differs from the checked runtime.")
    return {**capacity(reserve), "required_disk_bytes": reserve, "image_cache": cache}


def command(argv: list[str], *, data: str | None = None, timeout: int = 120) -> str:
    """Run a bounded owned command without exposing its arguments/stderr on failure.

    :param argv: Exact argument vector; never shell-expanded user text.
    :param data: Optional private stdin, e.g. ephemeral SQL or ECR login password.
    :param timeout: Maximum operation seconds.
    :return: Captured stdout; callers publish only allowlisted parsed receipts.
    :raises RuntimeError: Nonzero exit; raw diagnostics remain private on the host.
    """
    result = subprocess.run(
        argv, input=data, capture_output=True, text=True, timeout=timeout, check=False
    )
    if result.returncode:
        raise RuntimeError("Owned command failed; no private command output exported.")
    return result.stdout


def docker(
    root: Path, *arguments: str, data: str | None = None, timeout: int = 120
) -> str:
    """Use only this invocation's private Docker credential directory.

    :param root: Positively owned private host directory.
    :param arguments: Explicit Docker arguments; no inherited env-file use.
    :param data: Optional private standard input.
    :param timeout: Operation deadline.
    :return: Captured command output.
    :raises RuntimeError: Docker rejects the operation.
    """
    return command(
        ["docker", "--config", str(root / "docker-config"), *arguments],
        data=data,
        timeout=timeout,
    )


def verify_root(root: Path, nonce: str) -> None:
    """Require one exclusive private directory under /var/tmp, owned by this UID.

    :param root: Existing launcher-created directory.
    :param nonce: Exact cryptographic ownership identity.
    :return: None when directory identity and marker both agree.
    :raises ValueError: Any path, UID, mode or recorded nonce differs.
    """
    owner_record(nonce)
    if root != Path("/var/tmp") / f"mimir-experts-{nonce}" or root.resolve() != root:
        raise ValueError("Unsafe companion root.")
    metadata = root.stat()
    if metadata.st_uid != os.getuid() or metadata.st_mode & 0o777 != 0o700:
        raise ValueError("Companion root must remain privately owned.")
    marker = root / "controller-owner.json"
    if marker.is_symlink() or json.loads(marker.read_text())["nonce"] != nonce:
        raise ValueError("Companion ownership marker differs.")


def capacity(required_disk: int) -> dict[str, int]:
    """Read fresh host capacity before pulls and before starting the browser.

    :param required_disk: Conservative actual image sizes plus fixed host reserve.
    :return: Actual available bytes; reserve is checked before app creation.
    :raises ValueError: Host has insufficient memory/disk reserve.
    """
    values = dict(
        line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines()
    )
    memory = int(values["MemAvailable"].split()[0]) * 1024
    docker_root = json.loads(
        command(["docker", "info", "--format", "{{json .DockerRootDir}}"])
    )
    disk = shutil.disk_usage(docker_root).free
    validate_pull_capacity(memory, disk, required_disk)
    return {"available_memory_bytes": memory, "available_docker_disk_bytes": disk}


def private_file(path: Path, content: str, uid: int | None = None) -> None:
    """Write one exclusive nonsymlink mode0600 file, optionally owned by PostgreSQL.

    :param path: New path below the verified private root.
    :param content: Private or non-secret generated content.
    :param uid: Optional exact container runtime UID, e.g. 999.
    :return: None when the safe file exists.
    :raises OSError: Existing path, wrong permissions or write failure.
    """
    descriptor = os.open(
        path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w") as stream:
        stream.write(content)
    if uid is not None:
        os.chown(path, uid, uid)


def resource_names(nonce: str) -> dict[str, str]:
    """Create deterministic names from an already validated random ownership ID.

    :param nonce: Validated 32-hex identity.
    :return: Exact container/network names, never a wildcard filter.
    :raises ValueError: Invalid identity.
    """
    owner_record(nonce)
    prefix = f"mimir-experts-{nonce}"
    return {
        kind: f"{prefix}-{kind}"
        for kind in ("db", "web", "browser", "internal", "egress")
    }


def labels(nonce: str) -> list[str]:
    """Return the two exact Docker resource ownership labels.

    :param nonce: Validated invocation owner.
    :return: Docker CLI label arguments.
    """
    owner_record(nonce)
    return ["--label", f"{_LABEL}={nonce}", "--label", _FIXTURE_LABEL]


def assert_resource(root: Path, kind: str, name: str, nonce: str) -> None:
    """Check exact labels before any existing resource is inspected or removed.

    :param root: Owned credential directory.
    :param kind: Docker inspect resource type, e.g. container or network.
    :param name: Exact previously allocated resource name.
    :param nonce: Expected owner identity.
    :return: None only for the invocation's own resource.
    :raises ValueError: A colliding or altered resource is foreign.
    """
    inspected = json.loads(docker(root, kind, "inspect", name, timeout=20))[0]
    actual = (
        inspected.get("Labels")
        if kind == "network"
        else inspected["Config"].get("Labels")
    )
    if (
        not actual
        or actual.get(_LABEL) != nonce
        or actual.get("io.featurefactory.experts.fixture") != "CEDAR-RFP-01"
    ):
        raise ValueError("Refusing a foreign Docker resource.")


def create_directories(root: Path) -> None:
    """Allocate all bind mounts inside this invocation's private parent.

    :param root: Verified owner directory.
    :return: None; no anonymous/named Docker volumes are needed.
    :raises OSError: Any path already exists or cannot be privately created.
    """
    for name in (
        "docker-config",
        "scope",
        "mail",
        "static",
        "app-data",
        "pgdata",
        "tls",
        "output",
    ):
        (root / name).mkdir(mode=0o700)
    os.chown(root / "pgdata", 999, 999)


def generate_tls(root: Path) -> str:
    """Create an owned short-lived certificate and return its public-key pin.

    :param root: Private directory; key material is never exported.
    :return: Base64 SHA-256 SPKI digest for exact-key browser trust.
    :raises RuntimeError: OpenSSL cannot create or parse the certificate.
    """
    command(
        [
            "openssl",
            *_TLS_OPTIONS,
            "-keyout",
            str(root / "tls/server.key"),
            "-out",
            str(root / "tls/server.crt"),
        ]
    )
    (root / "tls/server.key").chmod(0o600)
    public = command(
        ["openssl", "x509", "-in", str(root / "tls/server.crt"), "-pubkey", "-noout"]
    )
    der = subprocess.run(
        ["openssl", "pkey", "-pubin", "-outform", "DER"],
        input=public.encode(),
        capture_output=True,
        check=True,
    ).stdout
    return base64.b64encode(hashlib.sha256(der).digest()).decode()


def pull_images(root: Path, manifest: dict[str, Any]) -> str:
    """Pull only exact ECR digests and resolve PostgreSQL16 to its actual digest.

    :param root: Invocation-owned Docker credentials.
    :param manifest: Validated source/build/browser identities from CI.
    :return: Immutable PostgreSQL16 repository digest.
    :raises RuntimeError: Authentication, pull or digest resolution fails.
    """
    registry = manifest["web_image"].split("/")[0]
    password = command(["aws", "ecr", "get-login-password", "--region", "us-east-1"])
    docker(
        root, "login", "--username", "AWS", "--password-stdin", registry, data=password
    )
    for image in (
        manifest["web_image"],
        manifest["browser_image"],
        manifest["postgres_image"],
    ):
        bounded_pull(root, image)
    return manifest["postgres_image"]


def bounded_pull(root: Path, image: str) -> None:
    """Keep a live oneGiB Docker-storage floor while pulling an owned exact image.

    :param root: Private Docker credentials; no ambient configuration is loaded.
    :param image: Previously validated immutable candidate/PG/browser image.
    :return: None after the actual pull completes above the fixed host reserve.
    :raises RuntimeError: Pull fails or threatens the existing host's free-space floor.
    """
    storage = json.loads(
        command(["docker", "info", "--format", "{{json .DockerRootDir}}"])
    )
    argv = ["docker", "--config", str(root / "docker-config"), "pull", image]
    with TemporaryFile() as output:
        process = subprocess.Popen(argv, stdout=output, stderr=output)
        try:
            monitor_pull(process, Path(storage))
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=20)
    if process.returncode:
        raise RuntimeError("Owned image pull failed; no private output exported.")


def monitor_pull(process: subprocess.Popen[bytes], storage: Path) -> None:
    """Stop this pull before free space can consume the existing-host reserve.

    :param process: Only the invocation's actual Docker-pull CLI process.
    :param storage: Actual Docker-root filesystem path.
    :return: None once that pull finishes.
    :raises RuntimeError: The live reserve or pull deadline is reached.
    """
    deadline = time.monotonic() + 900
    while process.poll() is None:
        if shutil.disk_usage(storage).free < 1024**3 or time.monotonic() >= deadline:
            process.kill()
            raise RuntimeError(
                "Owned image pull stopped at the live disk/time reserve."
            )
        time.sleep(0.25)


def create_networks(root: Path, nonce: str, names: dict[str, str]) -> None:
    """Create only labeled private app/DB and separate browser-egress bridges.

    :param root: Owned runtime directory.
    :param nonce: Invocation identity.
    :param names: Exact allocated resource names.
    :return: None; app/DB receive no external network.
    :raises RuntimeError: A collision or Docker networking failure occurs.
    """
    docker(root, "network", "create", "--internal", *labels(nonce), names["internal"])
    docker(root, "network", "create", *labels(nonce), names["egress"])


def start_database(
    root: Path, nonce: str, names: dict[str, str], image: str, parent: str | None = None
) -> str:
    """Start only the fresh owned PostgreSQL container and dedicated app role.

    :param root: Private bind mounts and generated credentials.
    :param nonce: Exact owner identity.
    :param names: Exact allocated resource names.
    :param image: Immutable PostgreSQL16 repository digest.
    :param parent: Explicit owned cgroup slice or unchanged defaultNone.
    :return: Dedicated app-role password, never logged/exported.
    :raises RuntimeError: Real database startup or role creation fails.
    """
    private_file(root / "pg-admin-password", os.urandom(32).hex(), 999)
    docker(root, *database_arguments(root, nonce, names, image, parent))
    wait_database(root, names["db"])
    return create_app_role(root, nonce, names["db"])


def container_arguments(
    nonce: str, names: dict[str, str], kind: str, parent: str | None = None
) -> list[str]:
    """Compose common least-privilege and resource bounds for one owned container.

    :param nonce: Validated owner identity.
    :param names: Exact allocated resource names.
    :param kind: Fixed role: web, db or browser.
    :param parent: Optional exact owned slice, never an ambient/default parent.
    :return: Explicit Docker arguments; no shell expansion or inherited environment.
    """
    operation = ["create"] if kind == "browser" else ["run", "-d"]
    return [
        *operation,
        "--name",
        names[kind],
        *labels(nonce),
        "--network",
        names["internal"],
        *owned_parent_arguments(nonce, parent),
        *role_arguments(kind),
    ]


def mounts(root: Path, bindings: tuple[tuple[str, str, bool], ...]) -> list[str]:
    """Mount only the declared invocation-local files/directories.

    :param root: Verified private parent directory.
    :param bindings: Fixed source leaf, container target and read-only flag triples.
    :return: Explicit Docker bind-mount arguments.
    """
    return [
        item
        for source, target, readonly in bindings
        for item in (
            "--mount",
            f"type=bind,src={root / source},dst={target}"
            + (",readonly" if readonly else ""),
        )
    ]


def database_arguments(
    root: Path, nonce: str, names: dict[str, str], image: str, parent: str | None = None
) -> list[str]:
    """Build the internal-only nonroot PostgreSQL container command.

    :param root: Owned PG files and secret file.
    :param nonce: Owner identity.
    :param names: Exact allocated resources.
    :param image: Immutable PG16 digest.
    :param parent: Explicit owned cgroup slice or unchanged defaultNone.
    :return: Docker argument vector with no shared DB URL.
    """
    return [
        *container_arguments(nonce, names, "db", parent),
        "--network-alias",
        "cedar-db",
        "--user",
        "999:999",
        "--tmpfs",
        _POSTGRES_SOCKET_TMPFS,
        *mounts(root, _DB_BINDS),
        "-e",
        "POSTGRES_PASSWORD_FILE=/run/secrets/pg-password",
        image,
        *_POSTGRES_SERVER,
    ]


def wait_database(root: Path, name: str) -> None:
    """Wait for the actual owned PostgreSQL server with a sixty-second bound.

    :param root: Owned Docker credential directory.
    :param name: Exact database-container name.
    :return: None after real pg_isready succeeds.
    :raises RuntimeError: The actual server never becomes ready.
    """
    for _ in range(60):
        try:
            docker(
                root, "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "postgres"
            )
            return
        except RuntimeError:
            time.sleep(1)
    raise RuntimeError("Owned PostgreSQL startup timed out.")


def create_app_role(root: Path, nonce: str, name: str) -> str:
    """Create one exact nonprivileged role/database/comment in the fresh server.

    :param root: Owned Docker credential directory.
    :param nonce: Validated 32-hex identity, safe for generated SQL identifiers.
    :param name: Exact fresh PostgreSQL container.
    :return: Newly generated app password sent only through private SQL stdin.
    :raises RuntimeError: Any real SQL precondition fails.
    """
    record, password = owner_record(nonce), os.urandom(32).hex()
    sql = f"CREATE ROLE {record['role']} LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOREPLICATION;\nCREATE DATABASE {record['database']} OWNER {record['role']};\nCOMMENT ON DATABASE {record['database']} IS '{record['format']}:{nonce}';\n"
    docker(
        root,
        "exec",
        "-i",
        name,
        "psql",
        "-h",
        _POSTGRES_SOCKET_DIRECTORY,
        "-U",
        "postgres",
        "-d",
        "postgres",
        "-v",
        "ON_ERROR_STOP=1",
        data=sql,
    )
    return password


def write_app_runtime(root: Path, manifest: dict[str, Any], password: str) -> None:
    """Create only fresh app credentials and the exact ownership marker.

    :param root: Private runtime directory.
    :param manifest: Trusted public source/build identities.
    :param password: Dedicated nonprivileged application-role password.
    :return: None; no ambient or provider credential is read.
    """
    record = owner_record(manifest["nonce"])
    private_file(root / "scope/owner.json", json.dumps(record))
    values = {
        "DJANGO_SETTINGS_MODULE": "experts_staging_settings",
        "MIMIR_ENV": "experts_staging",
        "PYTHONPATH": "/runtime:/app",
        "DJANGO_SECRET_KEY": os.urandom(48).hex(),
        "DATABASE_URL": f"postgresql://{record['role']}:{password}@cedar-db:5432/{record['database']}",
        "AWS_EC2_METADATA_DISABLED": "true",
        "MIMIR_GIT_REVISION": manifest["source_revision"],
        "COOKIE_SECURE": "true",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    private_file(
        root / "app.env", "".join(f"{key}={value}\n" for key, value in values.items())
    )
    pin = generate_tls(root)
    private_file(
        root / "runtime/browser-identity.json",
        json.dumps({"certificate_spki_sha256_base64": pin}),
    )


def web_mounts(root: Path) -> list[str]:
    """Return only the declared owned application mounts.

    :param root: Verified invocation directory.
    :return: Safe Docker mount arguments; no ambient volume or environment file.
    """
    return mounts(root, _WEB_BINDS)


def start_web(
    root: Path,
    manifest: dict[str, Any],
    names: dict[str, str],
    parent: str | None = None,
) -> None:
    """Launch the bounded app with an explicit verify/guard/init/TLS entrypoint.

    :param root: Private runtime directory.
    :param manifest: Immutable source/image identity.
    :param names: Exact allocated resources.
    :param parent: Explicit owned cgroup slice or unchanged defaultNone.
    :return: None after Docker starts the owned app.
    :raises RuntimeError: Container creation fails.
    """
    argv = [
        *container_arguments(manifest["nonce"], names, "web", parent),
        "--network-alias",
        "cedar-web",
        "--publish",
        "127.0.0.1::8443",
        "--env-file",
        str(root / "app.env"),
        *web_mounts(root),
        "--entrypoint",
        "python",
        manifest["web_image"],
        "/runtime/web_entry.py",
    ]
    docker(root, *argv)


def wait_web(root: Path, manifest: dict[str, Any], names: dict[str, str]) -> None:
    """Require actual healthy HTTPS and verified candidate revision.

    :param root: Owned artifact/credential directory.
    :param manifest: Verified candidate source identity.
    :param names: Exact container identities.
    :return: None when the real owned server is ready.
    :raises RuntimeError: Bounded readiness expires.
    """
    for _ in range(90):
        try:
            result = read_health(root, names["web"])
            if (
                result.get("status") == "healthy"
                and result.get("environment") == "experts_staging"
                and result.get("revision") == manifest["source_revision"]
            ):
                (root / "output/health.json").write_text(
                    json.dumps(
                        {
                            key: result[key]
                            for key in ("status", "checks", "environment", "revision")
                        },
                        indent=2,
                    )
                )
                return
        except (RuntimeError, json.JSONDecodeError):
            pass
        time.sleep(2)
    raise RuntimeError("Owned candidate HTTPS health did not become ready.")


def read_health(root: Path, name: str) -> dict[str, Any]:
    """Read HTTPS health using only the exact owned self-signed certificate.

    :param root: Owned runtime directory.
    :param name: Exact web container name.
    :return: Actual JSON health response; no fabricated success.
    :raises RuntimeError: Real certificate/HTTP/server checks fail.
    """
    probe = "import urllib.request,ssl; c=ssl.create_default_context(cafile='/tls/server.crt'); r=urllib.request.urlopen('https://localhost:8443/health/',context=c,timeout=3); print(r.read().decode())"
    return json.loads(docker(root, "exec", name, "python", "-c", probe, timeout=10))


def run_browser(root: Path, manifest: dict[str, Any], names: dict[str, str]) -> None:
    """Run separately bounded real Chromium, then recheck actual DB ownership/state.

    :param root: Owned runtime/output directories.
    :param manifest: Immutable browser image contract.
    :param names: Exact allocated Docker resources.
    :return: None after actual clipboard/readiness and domain readback pass.
    :raises RuntimeError: Browser or real database readback fails.
    """
    require_browser_reserve()
    docker(root, *browser_arguments(root, manifest, names))
    docker(root, "network", "connect", names["egress"], names["browser"])
    docker(root, "start", names["browser"])
    write_isolation_receipt(root, manifest, names)
    if docker(root, "wait", names["browser"], timeout=600).strip() != "0":
        raise RuntimeError("Actual on-idle browser readiness failed.")
    docker(
        root,
        "exec",
        names["web"],
        "python",
        "manage.py",
        "shell",
        "--no-imports",
        "-c",
        "from bootstrap import verify_after; verify_after()",
    )


def require_browser_reserve() -> None:
    """Check live remaining memory before adding the512MiB browser container.

    :return: None with at least768MiB still available.
    :raises ValueError: Current host reserve is insufficient.
    """
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
    if available < 768 * 1024 * 1024:
        raise ValueError("Insufficient fresh memory for browser plus host reserve.")


def browser_arguments(
    root: Path,
    manifest: dict[str, Any],
    names: dict[str, str],
    parent: str | None = None,
) -> list[str]:
    """Build the actual browser command without app/database/provider credentials.

    :param root: Owned source/output mounts.
    :param manifest: Immutable browser digest and owner identity.
    :param names: Exact allocated resources.
    :param parent: Explicit owned cgroup slice or unchanged defaultNone.
    :return: Docker create arguments; code mounts are read-only.
    """
    return [
        *container_arguments(manifest["nonce"], names, "browser", parent),
        "--shm-size",
        "128m",
        *mounts(root, _BROWSER_BINDS),
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        "-e",
        "AWS_EC2_METADATA_DISABLED=true",
        "--entrypoint",
        "python",
        manifest["browser_image"],
        "/runtime/browser.py",
    ]


def write_isolation_receipt(
    root: Path, manifest: dict[str, Any], names: dict[str, str]
) -> None:
    """Save actual container bounds/networks while excluding every Config.Env value.

    :param root: Private output directory.
    :param manifest: Expected source/owner identities.
    :param names: Exact created resources.
    :return: None after actual runtime observations pass.
    :raises AssertionError: Actual isolation differs from the approved plan.
    """
    rows = [
        isolation_row(root, manifest, names, kind) for kind in ("web", "db", "browser")
    ]
    (root / "output/runtime-isolation.json").write_text(json.dumps(rows, indent=2))


def isolation_row(
    root: Path, manifest: dict[str, Any], names: dict[str, str], kind: str
) -> dict[str, Any]:
    """Verify one real labeled container and expose only safe runtime metadata.

    :param root: Owned Docker credential directory.
    :param manifest: Exact owner/image identities.
    :param names: Exact allocated resources.
    :param kind: Web, db or browser role.
    :return: Whitelisted actual resource observations.
    :raises AssertionError: Actual network/bounds/read-only state differs.
    """
    assert_resource(root, "container", names[kind], manifest["nonce"])
    item = json.loads(docker(root, "container", "inspect", names[kind]))[0]
    networks = set(item["NetworkSettings"]["Networks"])
    assert networks == (
        {names["internal"], names["egress"]}
        if kind == "browser"
        else {names["internal"]}
    )
    limits = item["HostConfig"]
    assert (
        limits["Memory"] == _LIMITS[kind][0] * 1024 * 1024 and limits["ReadonlyRootfs"]
    )
    return {
        "role": kind,
        "image": item["Config"]["Image"],
        "networks": sorted(networks),
        "memory_bytes": limits["Memory"],
        "nano_cpus": limits["NanoCpus"],
        "ports": item["NetworkSettings"].get("Ports"),
    }


def archive_evidence(root: Path, manifest: dict[str, Any]) -> None:
    """Export only checked bounded artifacts under the exact owned S3 key.

    :param root: Verified private owner directory.
    :param manifest: Public source/build/transport identities.
    :return: None after a bounded SSE-encrypted object and safe receipt exist.
    :raises ValueError: Unsafe evidence or ownership metadata is found.
    """
    output = root / "output"
    identity = {
        key: manifest[key]
        for key in (
            "source_revision",
            "build_run_id",
            "web_image",
            "browser_image",
            "nonce",
            "fixture_sha256",
        )
    }
    (output / "source-identity.json").write_text(json.dumps(identity, indent=2))
    archive = package_evidence(root, evidence_files(output))
    upload_evidence(archive, manifest)


def upload_evidence(archive: Path, manifest: dict[str, Any]) -> None:
    """Upload only the exact artifact object, using the existing host role.

    :param archive: Checked actual source evidence package.
    :param manifest: Validated existing-bucket and owner identity.
    :return: None after a safe content-hash receipt is emitted.
    :raises RuntimeError: The actual existing-role S3 transfer fails.
    """
    key = f"experts-uat/{manifest['nonce']}/evidence.tar.gz"
    command(
        [
            "aws",
            "s3",
            "cp",
            str(archive),
            f"s3://{manifest['bucket']}/{key}",
            "--sse",
            "AES256",
            "--only-show-errors",
        ],
        timeout=120,
    )
    print(
        json.dumps(
            {
                "evidence_key": key,
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "bytes": archive.stat().st_size,
            }
        )
    )


def evidence_files(output: Path) -> list[Path]:
    """Reject links, unexpected members and oversized public artifact exports.

    :param output: Only the invocation's public evidence directory.
    :return: Actual regular allowlisted artifacts; runtime secrets are excluded.
    :raises ValueError: A link, undeclared artifact or size bound is unsafe.
    """
    entries = list(output.rglob("*"))
    if any(item.is_symlink() for item in entries):
        raise ValueError("Evidence exports cannot contain symbolic links.")
    files = [item for item in entries if item.is_file()]
    for item in files:
        if (
            item.resolve() != item
            or item.stat().st_nlink != 1
            or not allowed_evidence_name(item.relative_to(output))
        ):
            raise ValueError("Unsafe evidence export member.")
    if sum(item.stat().st_size for item in files) > 128 * 1024 * 1024:
        raise ValueError("Owned browser evidence exceeds the fixed export bound.")
    return files


def allowed_evidence_name(path: Path) -> bool:
    """Allow only declared original acquisition and non-secret receipt filenames.
    :param path: Relative artifact path inside the public output directory.
    :return: Whether the concrete artifact is an expected safe output.
    """
    fixed = {
        "health.json",
        "public-copy.json",
        "seed-receipt.json",
        "post-browser-state.json",
        "source-identity.json",
        "image-source-verification.json",
        "source-manifest.json",
        "browser-readiness.json",
        "browser-failure.json",
        "runtime-isolation.json",
        "capacity.json",
        "runtime-failure.json",
        "browser-trace.zip",
        "screenshots/guest-native-clipboard.png",
    }
    name = path.as_posix()
    return bool(
        name in fixed
        or re.fullmatch(
            r"(?:screenshots/)?guest-(?:list|profile)-[0-9]{3,4}-[0-9]{3,4}-attempt-[12]\.(?:json|png)",
            name,
        )
        or re.fullmatch(r"video/(?:page@)?[a-f0-9]{32}\.webm", name)
    )


def package_evidence(root: Path, files: list[Path]) -> Path:
    """Package original acquired bytes without adding runtime credentials or keys.

    :param root: Verified owner directory.
    :param files: Previously checked exact artifact paths.
    :return: Actual portable gzip tarball path.
    :raises OSError: The owned package cannot be created.
    """
    archive = root / "evidence.tar.gz"
    with tarfile.open(archive, "w:gz") as package:
        for item in files:
            package.add(
                item, arcname=str(item.relative_to(root / "output")), recursive=False
            )
    return archive


def cleanup(root: Path, nonce: str, names: dict[str, str]) -> None:
    """Remove only exact labeled companions, preserving all ambient resources.

    :param root: Verified private root.
    :param nonce: Exact owner identity.
    :param names: Exact allocated resources, never wildcard-selected targets.
    :return: None after actual owned containers/networks are gone.
    :raises ValueError: Any colliding name has foreign labels.
    :raises RuntimeError: Docker inventory/removal fails; absence is not assumed.
    """
    verify_root(root, nonce)
    for kind, keys in _CLEANUP_ORDER:
        listing = [kind, "ls"] + (["--all"] if kind == "container" else [])
        found = docker(
            root,
            *listing,
            "--format",
            "{{.Names}}" if kind == "container" else "{{.Name}}",
            timeout=20,
        ).splitlines()
        for key in keys:
            if names[key] in found:
                assert_resource(root, kind, names[key], nonce)
                arguments = (
                    [kind, "rm"]
                    + (["--force"] if kind == "container" else [])
                    + [names[key]]
                )
                docker(root, *arguments, timeout=20)


@contextmanager
def runtime_deadline() -> Iterator[None]:
    """Leave cleanup reserve before SSM's hard execution deadline.

    Python signal reference: https://docs.python.org/3/library/signal.html#signal.alarm
    :return: Controlled execution window with ordinary finally cleanup on expiry.
    :raises TimeoutError: The owned workload exceeds twelve minutes or is stopped.
    """
    previous_alarm = signal.signal(signal.SIGALRM, deadline_exceeded)
    previous_term = signal.signal(signal.SIGTERM, deadline_exceeded)
    signal.alarm(720)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_alarm)
        signal.signal(signal.SIGTERM, previous_term)


def deadline_exceeded(signum: int, frame: FrameType | None) -> None:
    """Raise into the normal owned-resource cleanup boundary.

    :param signum: Actual SIGALRM or SIGTERM signal.
    :param frame: Interrupted Python frame, never logged.
    :return: Does not return.
    :raises TimeoutError: Always, preserving the ordinary cleanup path.
    """
    raise TimeoutError("Owned companion workload deadline reached.")


def provision(
    root: Path, manifest: dict[str, Any], names: dict[str, str], required_disk: int
) -> None:
    """Create only the owned bounded app/database/browser lifecycle.

    :param root: Verified private host root.
    :param manifest: Validated public runtime identity.
    :param names: Exact allocated resources.
    :param required_disk: Conservative actual image-size reserve.
    :return: None after genuine core readiness and real state readback.
    """
    measured = reserve_capacity(root, manifest, required_disk)
    create_directories(root)
    (root / "output/capacity.json").write_text(json.dumps(measured, indent=2))
    image = pull_images(root, manifest)
    create_networks(root, manifest["nonce"], names)
    password = start_database(root, manifest["nonce"], names, image)
    write_app_runtime(root, manifest, password)
    start_web(root, manifest, names)
    wait_web(root, manifest, names)
    run_browser(root, manifest, names)


def main() -> None:
    """Execute one explicit companion with actual export and exact cleanup.

    :return: None after real core readiness and verified cleanup.
    :raises Exception: Any runtime guard/transport/browser failure keeps UAT pending.
    """
    root = Path(__file__).resolve().parent.parent
    manifest = json.loads((root / "runtime/run.json").read_text())
    required_disk = validate_runtime_manifest(manifest)
    nonce = manifest["nonce"]
    verify_root(root, nonce)
    names = resource_names(nonce)
    with runtime_deadline():
        try:
            announce_start(manifest)
            provision(root, manifest, names, required_disk)
        except Exception as error:
            record_runtime_failure(root, error)
            raise
        finally:
            finish_owned_run(root, manifest, names)


def announce_start(manifest: dict[str, Any]) -> None:
    """Emit only the original safe source/owner start declaration.

    :param manifest: Previously validated public runtime identity.
    :return: None after the actual start decision is observable.
    """
    print(
        json.dumps(
            {
                "stage": "owned_companion_start",
                "source_revision": manifest["source_revision"],
                "nonce": manifest["nonce"],
            }
        ),
        flush=True,
    )


def finish_owned_run(
    root: Path, manifest: dict[str, Any], names: dict[str, str]
) -> None:
    """Export real partial/success artifacts and always remove exact owned resources.

    :param root: Verified private invocation root.
    :param manifest: Exact source/owner/transport identities.
    :param names: Exact allocated resources.
    :return: None after actual artifact transfer and verified cleanup.
    :raises Exception: Export/cleanup failure remains an actual failed run.
    """
    try:
        if (root / "output").is_dir():
            archive_evidence(root, manifest)
    finally:
        cleanup(root, manifest["nonce"], names)
        verify_root(root, manifest["nonce"])
        shutil.rmtree(root)


def owned_parent_arguments(nonce: str, parent: str | None) -> list[str]:
    """Admit only this invocation's explicit slice; default vectors stay identical.

    :param nonce: Positive32hex owner identity.
    :param parent: Optional fixed derived unit name.
    :return: Empty default or exact cgroup-parent option.
    :raises ValueError: Foreign or malformed parent.
    """
    owner_record(nonce)
    if parent is None:
        return []
    if parent != f"mimirexperts{nonce}.slice":
        raise ValueError("Refusing a foreign cgroup parent.")
    return ["--cgroup-parent", parent]


def role_arguments(kind: str) -> list[str]:
    """Keep every original per-role resource and hardening option unchanged.

    :param kind: Existing web/db/browser role.
    :return: Original bounded argument vector in its original order.
    :raises KeyError: Unknown role.
    """
    memory, cpu, pids, temporary = _LIMITS[kind]
    return [
        "--memory",
        f"{memory}m",
        "--memory-swap",
        f"{memory}m",
        "--cpus",
        cpu,
        "--pids-limit",
        str(pids),
        *_HARDENING,
        "--tmpfs",
        f"/tmp:rw,nosuid,size={temporary}m",
    ]


if __name__ == "__main__":
    main()
