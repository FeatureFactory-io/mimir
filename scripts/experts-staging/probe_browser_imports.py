"""CI-only import preflight of the immutable browser image and shipped runtime."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4

import controller
import remote
from suite_contract import suite_cases

_IMAGE = "411113550285.dkr.ecr.us-east-1.amazonaws.com/mimir@sha256:a74104c8fb4ff8a02dd053ee2584868d91dd4273f058b690faf0875684c5e368"
_ENTRIES = {"/runtime/suite_browser.py", "/runtime/resource_observer.py"}
_ENV = {"PYTHONPATH", "PYTHONDONTWRITEBYTECODE", "AWS_EC2_METADATA_DISABLED"}
_LIMIT = 2 * 1024 * 1024
_LABEL = "mimir.ci.browser-import"
_FLAGS = (
    "docker",
    "run",
    "--pull=never",
    "--network",
    "none",
    "--read-only",
    "--cap-drop",
    "ALL",
    "--security-opt",
    "no-new-privileges",
    "--memory",
    "512m",
    "--memory-swap",
    "512m",
    "--cpus",
    "1",
    "--pids-limit",
    "64",
)
_PHASES = {
    "runtime_contract",
    "source_identity",
    "import_resource_observer",
    "import_suite_browser",
    "import_state_guard",
    "environment_guard",
    "complete",
}
_ERRORS = {
    "none",
    "missing_candidate_tests",
    "missing_module",
    "import_error",
    "value_error",
    "assertion_error",
    "file_error",
    "unknown_exception",
}
_PROBE = """import sys,json,importlib,os
from pathlib import Path
sys.path[0] = "/runtime"
phase = "runtime_contract"
try:
    from contract import validate_source_files
    phase = "source_identity"
    source=json.loads(Path("/runtime/source.json").read_text())
    validate_source_files(Path("/app"),source["files"])
    for name in ("resource_observer","suite_browser"):
        phase = "import_" + name
        module=importlib.import_module(name)
        assert Path(module.__file__).resolve()==Path("/runtime")/(name+".py")
    phase = "import_state_guard"
    from django.conf import settings
    assert not settings.configured
    assert "pytest" not in sys.modules
    apps=sys.modules.get("django.apps")
    assert apps is None or not apps.apps.ready
    phase = "environment_guard"
    assert not any(value for key,value in os.environ.items() if key in {"AWS_ACCESS_KEY_ID","AWS_SECRET_ACCESS_KEY","AWS_SESSION_TOKEN","DATABASE_URL","DJANGO_SECRET_KEY"} or key.endswith("_API_KEY") or "PASSWORD" in key)
except Exception as error:
    classification = "unknown_exception"
    if isinstance(error,ModuleNotFoundError):
        classification = "missing_candidate_tests" if error.name in {"tests","tests.support","tests.support.experts_replay_saga"} else "missing_module"
    elif isinstance(error,ImportError): classification = "import_error"
    elif isinstance(error,ValueError): classification = "value_error"
    elif isinstance(error,AssertionError): classification = "assertion_error"
    elif isinstance(error,OSError): classification = "file_error"
    print(json.dumps({"status":"failed","phase":phase,"classification":classification}))
    sys.exit(1)
print(json.dumps({"status":"passed","phase":"complete","classification":"none"}))
"""


def runtime_environment(actual: list[str]) -> list[str]:
    """Keep only the real browser's closed explicit noncredential environment.

    :param actual: Actual remote.browser_arguments output, never reconstructed.
    :return: Identical ordered -e fields; no independently supplied PYTHONPATH.
    :raises ValueError: Unknown image/entrypoint/environment or inherited value.
    """
    if len(actual) < 4 or actual[-4:-2] != ["--entrypoint", "python"]:
        raise ValueError("Actual Python browser entrypoint required")
    if actual[-2] != _IMAGE or actual[-1] not in _ENTRIES or "--env-file" in actual:
        raise ValueError("Closed immutable browser import path required")
    result, names = [], set()
    for i, value in enumerate(actual[:-4]):
        if value not in {"-e", "--env"}:
            continue
        field = actual[i + 1]
        key, separator, contents = field.partition("=")
        if not separator or not contents or key not in _ENV or key in names:
            raise ValueError("Only actual explicit noncredential browser env allowed")
        result.extend(["-e", field])
        names.add(key)
    if names != _ENV:
        raise ValueError("Complete actual suite browser environment required")
    return result


def probe_arguments(
    runtime: Path, actual: list[str], identity: str | None = None
) -> list[str]:
    """Compose an isolated import launch with the actual browser environment.

    :param runtime: Exact shipped bundle; :param actual: Real runtime argv.
    :param identity: Fresh UUID hex for one positively owned CI container.
    :return: No-network probe argv; :raises ValueError: Unknown runtime scope.
    """
    environment = runtime_environment(actual)
    identity = identity or uuid4().hex
    if len(identity) != 32 or any(c not in "0123456789abcdef" for c in identity):
        raise ValueError("Fresh closed probe identity required")
    return [
        *_FLAGS,
        "--name",
        "experts-ci-import-" + identity,
        "--label",
        _LABEL + "=" + identity,
        "--mount",
        f"type=bind,src={runtime.resolve()},dst=/runtime,readonly",
        *environment,
        "--entrypoint",
        "python",
        _IMAGE,
        "-c",
        _PROBE,
    ]


def bundle_payloads(
    archive: Path, digest: str, manifest: dict[str, Any]
) -> dict[str, bytes]:
    """Read only the exact bounded controller-produced bundle and member table.

    :param archive: Actual archive; :param digest: Its authenticated SHA256.
    :param manifest: Actual declarations populated by controller.make_bundle.
    :return: Closed regular members; no archive path is directly extracted.
    :raises ValueError: Checksum, member name/type, duplication or size differs.
    """
    if (
        archive.is_symlink()
        or archive.stat().st_nlink != 1
        or archive.stat().st_size > _LIMIT
    ):
        raise ValueError("Bounded unlinked bundle required")
    raw = archive.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Actual runtime bundle checksum differs")
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as package:
        rows = package.getmembers()
        expected = set(controller.bundle_members(manifest))
        if len(rows) != len(expected) or {row.name for row in rows} != expected:
            raise ValueError("Exact shipped member set required")
        if any(not row.isfile() or Path(row.name).name != row.name for row in rows):
            raise ValueError("Only regular flat shipped members allowed")
        if sum(row.size for row in rows) > _LIMIT:
            raise ValueError("Bounded shipped payload required")
        return {row.name: package.extractfile(row).read() for row in rows}


def unpack_bundle(
    archive: Path, digest: str, target: Path, manifest: dict[str, Any]
) -> None:
    """Authenticate exact source/control/run bytes before one private mount exists.

    :param archive: Controller bundle; :param digest: Exact archive SHA256.
    :param target: New directory; :param manifest: Authenticated declarations.
    :return: None after only actual shipped bytes are materialized.
    :raises ValueError: Source/control/run declarations or control bytes differ.
    """
    values = bundle_payloads(archive, digest, manifest)
    controls = json.loads(values["controls.json"])
    source = json.loads(values["source.json"])
    if (
        controls["files"] != manifest["control_files"]
        or source["files"] != manifest["source_files"]
    ):
        raise ValueError("Exact source and committed control maps required")
    if (
        source["source_revision"] != manifest["source_revision"]
        or controls["control_revision"] != manifest["control_revision"]
        or json.loads(values["run.json"]) != manifest
    ):
        raise ValueError("Actual invocation and control identities required")
    if any(
        hashlib.sha256(values[name]).hexdigest() != sha
        for name, sha in controls["files"].items()
    ):
        raise ValueError("Exact committed runtime bytes required")
    target.mkdir(mode=0o700)
    for name, raw in values.items():
        with (target / name).open("xb") as member:
            member.write(raw)


def prepare_bundle(output: Path, manifest: dict[str, Any]) -> tuple[Path, Path, str]:
    """Retain an exclusive probe bundle without overwriting lifecycle evidence.

    :param output: Prepared CI directory; :param manifest: Actual invocation.
    :return: New directory, exact retained bundle and hash.
    :raises ValueError: Source/proof bytes differ from authenticated preparation.
    """
    destination = output / "ci-browser-import-probe"
    destination.mkdir(mode=0o700)
    names = ["source.json"]
    if controller.resource_profile.selected(manifest):
        controller.resource_profile.validate_files(output, manifest)
        names.extend(controller.resource_profile.PROOF_FILES)
    for name in names:
        path = output / name
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
            raise ValueError("Unlinked actual source/proof file required")
        with (destination / name).open("xb") as stream:
            stream.write(path.read_bytes())
    bundle, digest = controller.make_bundle(destination, manifest)
    with (destination / "manifest.json").open("x") as stream:
        json.dump(manifest, stream, sort_keys=True)
    return destination, bundle, digest


def probe_result(result: subprocess.CompletedProcess[bytes]) -> dict[str, str]:
    """Accept only finite child facts; never disclose raw stdout or stderr.

    :param result: Captured private process result.
    :return: Closed phase/classification record; :raises ValueError: Invalid protocol.
    """
    if len(result.stdout) > 8192:
        raise ValueError("Bounded closed import protocol required")
    row = json.loads(result.stdout)
    if not isinstance(row, dict) or set(row) != {"status", "phase", "classification"}:
        raise ValueError("Closed import protocol required")
    if row["phase"] not in _PHASES or row["classification"] not in _ERRORS:
        raise ValueError("Finite import classifications required")
    passing = row == {"status": "passed", "phase": "complete", "classification": "none"}
    failing = (
        row["status"] == "failed"
        and row["phase"] != "complete"
        and row["classification"] != "none"
    )
    if not (
        (passing and result.returncode == 0 and not result.stderr)
        or (failing and result.returncode != 0)
    ):
        raise ValueError("Actual exit status must agree with import protocol")
    return row


def cleanup_probe(identity: str) -> None:
    """Remove only the fresh label-verified CI container, including after timeout.

    :param identity: Fresh UUID used for this exact launch.
    :return: None after actual removal; :raises ValueError: Ownership/removal unknown.
    """
    name = "experts-ci-import-" + identity
    result = subprocess.run(
        ["docker", "container", "inspect", "--format", "{{json .Config.Labels}}", name],
        capture_output=True,
        timeout=15,
        check=False,
    )
    if result.returncode != 0 or len(result.stdout) > 8192:
        raise ValueError("CI probe container ownership unknown")
    labels = json.loads(result.stdout)
    if not isinstance(labels, dict) or labels.get(_LABEL) != identity:
        raise ValueError("CI probe container ownership differs")
    result = subprocess.run(
        ["docker", "rm", "--force", name], capture_output=True, timeout=15, check=False
    )
    if result.returncode != 0:
        raise ValueError("CI probe container cleanup unknown")


def run_probe(runtime: Path, actual: list[str]) -> dict[str, str]:
    """Run the isolated import and bound cleanup to its fresh owned identity.

    :param runtime: Shipped files; :param actual: Actual browser argv.
    :return: Safe actual result or closed timeout/unknown classification.
    """
    identity = uuid4().hex
    command = probe_arguments(runtime, actual, identity)
    try:
        try:
            result = subprocess.run(
                command, capture_output=True, timeout=90, check=False
            )
            return probe_result(result)
        except subprocess.TimeoutExpired:
            return {
                "status": "failed",
                "phase": "container_execution",
                "classification": "timeout",
            }
    finally:
        cleanup_probe(identity)


def import_receipt(
    manifest: dict[str, Any], digest: str, entry: str, facts: dict[str, str]
) -> dict[str, Any]:
    """Bind safe import facts to the retained exact source/control bundle.

    :param manifest: Actual invocation; :param digest: Bundle hash.
    :param entry: Actual script; :param facts: Closed child facts.
    :return: Import-only receipt, never a browser journey or staged acceptance.
    """
    return {
        "status": (
            "CI_BROWSER_IMPORTS_PASS"
            if facts["status"] == "passed"
            else "CI_BROWSER_IMPORTS_FAILED"
        ),
        "scope": "CI_IMPORT_ONLY_NOT_STAGING",
        "browser_image": _IMAGE,
        "runtime_bundle_sha256": digest,
        "source_revision": manifest["source_revision"],
        "control_revision": manifest["control_revision"],
        "entrypoint": entry,
        "import_result": facts,
        "imported_modules": (
            ["resource_observer", "suite_browser"]
            if facts["status"] == "passed"
            else []
        ),
        "full_saga_accepted": False,
    }


def verify(output: Path, images: Path, suite: str) -> dict[str, Any]:
    """Probe only actual shipped imports on disposable Linux CI.

    :param output: Prepared CI data; :param images: Actual image receipt.
    :param suite: Explicit closed selector; :return: Source-bound import receipt.
    :raises ValueError: Default-only core or unknown source/image/import contract.
    """
    manifest = controller.execution_manifest(output, images)
    measured = controller.resource_profile.selected(manifest)
    cases = suite_cases(suite)
    if not measured and suite != "full":
        raise ValueError("Default core remains unchanged")
    case = cases[0] if measured else cases[1]
    manifest.update(suite_phase=case.phase, saga_case=case.case)
    destination, bundle, digest = prepare_bundle(output, manifest)
    with TemporaryDirectory(prefix="experts-ci-import-") as temporary:
        runtime = Path(temporary).resolve() / "runtime"
        unpack_bundle(bundle, digest, runtime, manifest)
        parent = (
            remote.resource_runtime.aggregate.parent_name(manifest["nonce"])
            if measured
            else None
        )
        actual = remote.browser_arguments(
            runtime.parent, manifest, remote.resource_names(manifest["nonce"]), parent
        )
        facts = run_probe(runtime, actual)
    receipt = import_receipt(manifest, digest, actual[-1], facts)
    with (destination / "receipt.json").open("x") as stream:
        json.dump(receipt, stream, sort_keys=True)
    return receipt


def main() -> None:
    """Write only typed probe facts; never print private child output or errors.

    :return: None on actual image import success; nonzero on any unknown failure.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--suite", choices=("core", "full"), required=True)
    args = parser.parse_args()
    passed = False
    try:
        receipt = verify(args.output, args.images, args.suite)
        passed = receipt["status"] == "CI_BROWSER_IMPORTS_PASS"
    except Exception:  # noqa: BLE001 -- Keep private failure text out of CI.
        receipt = {
            "status": "CI_BROWSER_IMPORTS_FAILED",
            "scope": "CI_IMPORT_ONLY_NOT_STAGING",
            "full_saga_accepted": False,
            "import_result": {
                "status": "failed",
                "phase": "preflight_or_cleanup",
                "classification": "unknown_failure",
            },
        }
    try:
        with (args.output / "ci-browser-imports.json").open("x") as stream:
            json.dump(receipt, stream, sort_keys=True)
    except Exception:  # noqa: BLE001 -- Never log output-path failures.
        raise SystemExit(1) from None
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
