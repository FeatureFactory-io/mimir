"""Verify dangerous staging boundaries with real files and pure command contracts."""

from __future__ import annotations

import ast
import importlib.util
import json
import signal
import subprocess
import sys
import tarfile
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import uuid4

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME = _ROOT / "scripts/experts-staging"
_ACCOUNT = "411113550285"
_REVISION = "a" * 40
_PUBLIC_RECEIPTS = (
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
)


def _load(name: str) -> ModuleType:
    """Load one actual control module without running its CLI entrypoint."""
    spec = importlib.util.spec_from_file_location(
        "cedar_runner_" + name, _RUNTIME / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch) -> dict[str, ModuleType]:
    """Scope module import wiring to this test; no AWS/Docker dependency is replaced."""
    monkeypatch.syspath_prepend(str(_RUNTIME))
    contract = _load("contract")
    monkeypatch.setitem(sys.modules, "contract", contract)
    return {
        "contract": contract,
        "controller": _load("controller"),
        "remote": _load("remote"),
    }


def _runtime_manifest() -> dict[str, Any]:
    """Build one safe public contract with no actual credential or cloud action."""
    image = f"{_ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com/mimir"
    receipt = {
        "source_revision": _REVISION,
        "run_id": "123",
        "web_image": image,
        "web_digest": "sha256:" + "b" * 64,
        "platforms": ["linux/amd64", "linux/arm64"],
    }
    return {
        "nonce": "c" * 32,
        "account": _ACCOUNT,
        "source_revision": _REVISION,
        "build_run_id": "123",
        "build_receipt": receipt,
        "web_image": image + "@" + receipt["web_digest"],
        "browser_image": image + "@sha256:" + "d" * 64,
        "postgres_image": "postgres@sha256:" + "e" * 64,
        "bucket": f"elasticbeanstalk-us-east-1-{_ACCOUNT}",
        "fixture_sha256": "f" * 64,
        "image_sizes": {
            "web": 2 * 1024**3,
            "browser": 3 * 1024**3,
            "postgres": 512 * 1024**2,
        },
    }


def test_runtime_manifest_with_actual_sizes_requires_conservative_pull_reserve(
    modules: dict[str, ModuleType],
) -> None:
    result = modules["contract"].validate_runtime_manifest(_runtime_manifest())
    assert result == 6 * 1024**3 + 512 * 1024**2


@pytest.mark.parametrize(
    "field,value",
    [
        ("bucket", "mimir-db-backups-411113550285"),
        ("browser_image", "evil.invalid/mimir:latest"),
        ("web_image", "evil.invalid/mimir@sha256:" + "b" * 64),
        ("postgres_image", "postgres:16"),
        ("nonce", "../foreign"),
        ("fixture_sha256", "bad"),
        ("image_sizes", {"web": 1}),
        ("image_sizes", {"web": True, "browser": 10, "postgres": 10}),
    ],
)
def test_runtime_manifest_with_foreign_transport_or_images_rejects(
    modules: dict[str, ModuleType], field: str, value: object
) -> None:
    manifest = _runtime_manifest()
    manifest[field] = value
    with pytest.raises(ValueError):
        modules["contract"].validate_runtime_manifest(manifest)


@pytest.mark.parametrize(
    "url,method,allowed",
    [
        ("https://cedar-web:8443/experts/", "GET", True),
        ("https://cedar-web:8443/karma/copy-receipts/", "POST", False),
        ("https://fonts.googleapis.com/css2?family=Montserrat", "GET", True),
        ("https://fonts.gstatic.com/example.woff2", "GET", True),
        ("https://ka-p.fontawesome.com/font.woff2", "GET", True),
        ("https://kit.fontawesome.com/600fa45ed9.js", "GET", True),
        ("https://cdn.jsdelivr.net/npm/bootstrap/style.css", "GET", True),
        ("https://unpkg.com/htmx.org@2.0.4", "GET", True),
        ("https://fonts.googleapis.com/collect", "POST", False),
        ("http://169.254.169.254/latest/meta-data/", "GET", False),
        ("https://api.anthropic.com/v1/messages", "POST", False),
        ("https://fonts.googleapis.com.attacker.invalid/font", "GET", False),
        ("https://user:secret@fonts.gstatic.com/font", "GET", False),
        ("https://fonts.gstatic.com:444/font", "GET", False),
        ("https://fonts.gstatic.com:bad/font", "GET", False),
    ],
)
def test_browser_request_allowlist_preserves_real_assets_and_blocks_other_egress(
    modules: dict[str, ModuleType], url: str, method: str, allowed: bool
) -> None:
    assert modules["contract"].allow_browser_request(url, method) is allowed


def test_workflow_with_normal_defaults_has_no_implicit_companion_dispatch() -> None:
    workflow = yaml.safe_load(
        (_ROOT / ".github/workflows/build-and-deploy.yml").read_text()
    )
    trigger = workflow.get("on", workflow.get(True))
    inputs = trigger["workflow_dispatch"]["inputs"]
    assert inputs["experts_staging_only"]["default"] is False
    assert inputs["deploy_to_idle"]["default"] is True
    assert inputs["preflight_only"]["default"] is False
    jobs = workflow["jobs"]
    for name in (
        "test",
        "build-and-push",
        "deploy-idle",
        "wake_idle",
        "staging-preflight",
    ):
        assert "!inputs.experts_staging_only" in jobs[name]["if"]
    assert (
        jobs["experts-staging"]["if"]
        == "github.event_name == 'workflow_dispatch' && inputs.experts_staging_only"
    )
    assert jobs["experts-staging"]["concurrency"] == {
        "group": "mimir-idle-power",
        "cancel-in-progress": False,
    }


def test_workflow_with_untrusted_selectors_uses_environment_and_guards_before_aws() -> (
    None
):
    data = yaml.safe_load(
        (_ROOT / ".github/workflows/build-and-deploy.yml").read_text()
    )
    steps = data["jobs"]["experts-staging"]["steps"]
    first = steps[0]["run"]
    assert (
        'test "$NORMAL_DEPLOY" = false' in first
        and 'test "$WAKE_IDLE" = false' in first
    )
    assert '[[ "$CANDIDATE_SHA" =~ ^[a-f0-9]{40}$ ]]' in first
    assert all("${{ inputs." not in step.get("run", "") for step in steps)
    prepared = next(
        i for i, step in enumerate(steps) if step.get("id") == "experts-source"
    )
    connection = next(
        i
        for i, step in enumerate(steps)
        if step.get("uses", "").startswith("aws-actions/configure-aws-credentials")
    )
    assert prepared < connection


def test_launcher_with_real_package_has_no_credentials_urls_or_unsafe_extraction(
    modules: dict[str, ModuleType], tmp_path: Path
) -> None:
    manifest = _runtime_manifest()
    (tmp_path / "source.json").write_text('{"files":{}}')
    for name in ("app.env", "server.key", "host-secret.json"):
        (tmp_path / name).write_text("DO_NOT_EXPORT_PRIVATE_SENTINEL")
    bundle, digest = modules["controller"].make_bundle(tmp_path, manifest)
    with tarfile.open(bundle) as package:
        assert set(package.getnames()) == {
            *modules["controller"]._RUNTIME_FILES,
            "source.json",
            "run.json",
            "controls.json",
        }
        assert all(
            b"DO_NOT_EXPORT_PRIVATE_SENTINEL" not in package.extractfile(item).read()
            for item in package.getmembers()
        )
    launcher = modules["controller"].launcher(manifest, digest)
    assert (
        "https://" not in launcher
        and "StartSession" not in launcher
        and "get-config" not in launcher
    )
    subprocess.run(["bash", "-n"], input=launcher, text=True, check=True)
    ast.parse("\n".join(launcher.splitlines()[1:-1]))


def test_evidence_export_with_real_regular_files_preserves_bytes(
    modules: dict[str, ModuleType], tmp_path: Path
) -> None:
    """Round-trip every emitted fixed public receipt through a real gzip archive.

    :param modules: Actual control modules, without cloud or HTTP substitutions.
    :param tmp_path: Owned real filesystem directory; no ambient data is touched.
    :return: None when archived bytes equal the unchanged originals.
    :raises AssertionError: A receipt is missing, changed or unexpectedly added.
    """
    output = tmp_path / "output"
    output.mkdir()
    original = {
        name: ('{"receipt":"' + name + '"}\n').encode() for name in _PUBLIC_RECEIPTS
    }
    for name, payload in original.items():
        (output / name).write_bytes(payload)
    files = modules["remote"].evidence_files(output)
    archive = modules["remote"].package_evidence(tmp_path, files)
    with tarfile.open(archive) as package:
        assert set(package.getnames()) == set(original)
        for name, payload in original.items():
            assert package.extractfile(name).read() == payload
            assert (output / name).read_bytes() == payload


@pytest.mark.parametrize(
    "name",
    [
        "health.json.env",
        "health.json.bak",
        "private/health.json",
        "health-secret.json",
        "../health.json",
        "/health.json",
        "unknown.json",
    ],
)
def test_allowed_evidence_name_with_health_variants_rejects(
    modules: dict[str, ModuleType], name: str
) -> None:
    """Permit only the exact public health receipt, never a broader name pattern.

    :param modules: Actual imported control modules; no cloud operations occur.
    :param name: Undeclared, private or unsafe relative artifact spelling.
    :return: None when the concrete artifact name is rejected.
    :raises AssertionError: The health allowlist becomes broader than intended.
    """
    assert modules["remote"].allowed_evidence_name(Path(name)) is False


@pytest.mark.parametrize(
    "mode", ["symlink", "hardlink", "secret_suffix", "unknown", "private_health"]
)
def test_evidence_export_with_real_foreign_links_or_credentials_rejects(
    modules: dict[str, ModuleType], tmp_path: Path, mode: str
) -> None:
    output = tmp_path / "output"
    output.mkdir()
    outside = tmp_path / "private.json"
    outside.write_text("PRIVATE_SENTINEL")
    if mode == "symlink":
        (output / "health.json").symlink_to(outside)
    if mode == "hardlink":
        (output / "health.json").hardlink_to(outside)
    if mode == "secret_suffix":
        (output / "app.env").write_text("PRIVATE_SENTINEL")
    if mode == "unknown":
        (output / "unknown.json").write_text("PRIVATE_SENTINEL")
    if mode == "private_health":
        (output / "private").mkdir()
        (output / "private/health.json").write_text("PRIVATE_SENTINEL")
    with pytest.raises(ValueError):
        modules["remote"].evidence_files(output)


def test_container_contract_with_actual_generated_vectors_has_no_ambient_runtime(
    modules: dict[str, ModuleType], tmp_path: Path
) -> None:
    remote = modules["remote"]
    manifest = _runtime_manifest()
    names = remote.resource_names(manifest["nonce"])
    database = remote.database_arguments(
        tmp_path, manifest["nonce"], names, manifest["postgres_image"]
    )
    browser = remote.browser_arguments(tmp_path, manifest, names)
    assert "cedar-db" in database and "--publish" not in database
    assert "--env-file" not in browser and "DATABASE_URL" not in " ".join(browser)
    assert "ANTHROPIC_API_KEY" not in " ".join(
        browser
    ) and "AWS_ACCESS_KEY_ID" not in " ".join(browser)
    assert "--entrypoint" in browser and browser[-2:] == [
        manifest["browser_image"],
        "/runtime/browser.py",
    ]
    for argv in (database, browser):
        assert "--cap-drop" in argv and "ALL" in argv and "--read-only" in argv
        assert "--memory-swap" in argv and "--cpus" in argv
        assert "--no-healthcheck" in argv
        assert "--privileged" not in argv and "--network=host" not in argv


@pytest.mark.parametrize(
    "field", ["nonce", "build_receipt", "source_revision", "image_sizes"]
)
def test_runtime_manifest_with_missing_required_field_rejects_before_execution(
    modules: dict[str, ModuleType], field: str
) -> None:
    """Missing runtime proof cannot silently fall back to ambient state."""
    manifest = _runtime_manifest()
    del manifest[field]
    with pytest.raises(ValueError):
        modules["contract"].validate_runtime_manifest(manifest)


def test_independent_cleanup_with_absent_owned_root_is_a_real_safe_noop(
    modules: dict[str, ModuleType],
) -> None:
    """Execute the actual cleanup launcher only for a positively absent random root."""
    manifest = _runtime_manifest()
    manifest["nonce"] = uuid4().hex
    assert not (Path("/var/tmp") / f"mimir-experts-{manifest['nonce']}").exists()
    program = modules["controller"].cleanup_launcher(manifest)
    inner = "\n".join(program.splitlines()[1:-1])
    subprocess.run([sys.executable, "-c", inner], check=True, capture_output=True)
    assert "prune" not in program and "--all" not in program


@pytest.mark.parametrize("raise_inside", [False, True])
def test_real_deadline_context_restores_original_signal_handlers(
    modules: dict[str, ModuleType], raise_inside: bool
) -> None:
    """Actual normal and exceptional context exits restore the previous handlers."""
    previous = (signal.getsignal(signal.SIGALRM), signal.getsignal(signal.SIGTERM))
    try:
        with modules["remote"].runtime_deadline():
            if raise_inside:
                raise RuntimeError("declared test-only body failure")
    except RuntimeError:
        assert raise_inside
    assert previous == (
        signal.getsignal(signal.SIGALRM),
        signal.getsignal(signal.SIGTERM),
    )
    assert signal.alarm(0) == 0


def test_explicit_deadline_signal_raises_into_cleanup_boundary(
    modules: dict[str, ModuleType],
) -> None:
    """The real handler raises instead of bypassing ordinary finally cleanup."""
    with pytest.raises(TimeoutError):
        modules["remote"].deadline_exceeded(signal.SIGALRM, None)


def test_https_web_entry_with_four_threads_preserves_one_process_and_tls() -> None:
    """Bound HTTPS connection concurrency without adding another app process.

    :return: None when the measured local repair retains one worker and TLS.
    :raises AssertionError: Worker count, thread count, TLS or deadline changes.
    """
    tree = ast.parse((_RUNTIME / "web_entry.py").read_text())
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "_GUNICORN"
            for target in node.targets
        )
    )
    argv = ast.literal_eval(assignment.value)
    assert argv[:2] == ["gunicorn", "mimir.wsgi:application"]
    assert argv[argv.index("--workers") + 1] == "1"
    assert argv[argv.index("--threads") + 1] == "4"
    assert argv[argv.index("--certfile") + 1] == "/tls/server.crt"
    assert argv[argv.index("--keyfile") + 1] == "/tls/server.key"
    assert argv[argv.index("--timeout") + 1] == "90"


def test_database_arguments_with_readonly_root_support_entrypoint_socket(
    modules: dict[str, ModuleType], tmp_path: Path
) -> None:
    """Keep the real image's initialization client and server on one socket.

    :param modules: Actual pure staging-control imports.
    :param tmp_path: Owned command-contract path; no Docker calls occur.
    :return: None when only the bounded nonroot socket mount is writable.
    :raises AssertionError: The entrypoint cannot reach its temporary server.
    """
    remote, manifest = modules["remote"], _runtime_manifest()
    argv = remote.database_arguments(
        tmp_path,
        manifest["nonce"],
        remote.resource_names(manifest["nonce"]),
        manifest["postgres_image"],
    )
    assert "unix_socket_directories=/var/run/postgresql" in argv
    assert "/var/run/postgresql:rw,nosuid,size=1m,uid=999,gid=999,mode=3775" in argv
    assert "unix_socket_directories=/tmp" not in argv and "--read-only" in argv
    assert argv[argv.index("--user") + 1] == "999:999"
    assert argv[argv.index("--memory") + 1] == "192m"
    assert argv[argv.index("--cpus") + 1] == "0.25"
    assert "--publish" not in argv and "--privileged" not in argv


def _cache_metadata(manifest: dict[str, Any]) -> dict[str, Any]:
    """Construct pure input records matching the public Docker metadata schema.

    :param manifest: Valid test contract; no image or cloud operation is invoked.
    :return: Complete matching three-role Linux/amd64 metadata.
    """
    return {
        role: {
            "Id": "sha256:" + "a" * 64,
            "Os": "linux",
            "Architecture": "amd64",
            "Size": size,
            "RepoDigests": [manifest[f"{role}_image"]],
        }
        for role, size in manifest["image_sizes"].items()
    }


def test_image_cache_reserve_with_three_exact_records_excludes_resident_bytes(
    modules: dict[str, ModuleType],
) -> None:
    """Recognize only a complete exact cache; keep the declared live disk floor.

    :param modules: Actual pure staging contract functions.
    :return: None once all three matching immutable records permit the live floor.
    :raises AssertionError: Cache identity or reserve computation differs.
    """
    manifest = _runtime_manifest()
    cache = _cache_metadata(manifest)
    assert modules["contract"].image_cache_reserve(manifest, cache) == 1024**3


@pytest.mark.parametrize(
    "field,value",
    [
        ("Os", "windows"),
        ("Architecture", "arm64"),
        ("Size", True),
        ("Size", 0),
        ("Size", -1),
        ("Size", 20 * 1024**3),
        ("Size", 20 * 1024**3 + 1),
        ("Id", "latest"),
        ("Id", "sha256:" + "A" * 64),
        ("RepoDigests", ["mimir:latest"]),
        ("RepoDigests", "not-a-list"),
        ("RepoDigests", []),
    ],
)
def test_image_cache_reserve_with_wrong_metadata_keeps_cold_budget(
    modules: dict[str, ModuleType], field: str, value: Any
) -> None:
    """Never lower storage reserve for mismatched local metadata.

    :param modules: Actual contract module.
    :param field: One public Docker metadata field to corrupt.
    :param value: Explicit adverse value; no Docker dependency is mocked.
    :return: None after the unchanged conservative cold budget is required.
    :raises AssertionError: An incomplete identity permits the cached budget.
    """
    manifest = _runtime_manifest()
    cache = _cache_metadata(manifest)
    cache["web"][field] = value
    assert modules["contract"].image_cache_reserve(manifest, cache) == (
        modules["contract"].validate_runtime_manifest(manifest)
    )


@pytest.mark.parametrize("mode", ["missing", "extra", "empty", "invalid_row"])
def test_image_cache_reserve_with_incomplete_roles_keeps_cold_budget(
    modules: dict[str, ModuleType], mode: str
) -> None:
    """Require all and only the three role observations before using cache proof.

    :param modules: Actual pure contract module.
    :param mode: Missing, extra, empty or malformed role observation.
    :return: None after the cold budget remains required.
    :raises AssertionError: Partial proof changes the resource requirement.
    """
    manifest, cache = _runtime_manifest(), _cache_metadata(_runtime_manifest())
    if mode == "missing":
        del cache["postgres"]
    if mode == "extra":
        cache["foreign"] = cache["web"]
    if mode == "empty":
        cache = {}
    if mode == "invalid_row":
        cache["browser"] = None
    assert modules["contract"].image_cache_reserve(manifest, cache) == (
        modules["contract"].validate_runtime_manifest(manifest)
    )


@pytest.mark.parametrize("value", [True, None, -1, 0, 1024**3 - 1, 1024**3 + 1])
def test_validate_pull_capacity_with_uncomputed_budget_rejects(
    modules: dict[str, ModuleType], value: Any
) -> None:
    """Reject arbitrary budget values instead of admitting an unproven floor.

    :param modules: Actual contract module.
    :param value: Invalid or noncanonical reserve candidate.
    :return: None after rejection.
    :raises AssertionError: An arbitrary input lowers the guard.
    """
    with pytest.raises(ValueError):
        modules["contract"].validate_pull_capacity(2 * 1024**3, 8 * 1024**3, value)


def test_validate_pull_capacity_with_cached_disk_still_rejects_low_memory(
    modules: dict[str, ModuleType],
) -> None:
    """Retain the measured memory hold even with exact cached image proof.

    :param modules: Actual contract module.
    :return: None after the real post-pull memory observation remains blocked.
    :raises AssertionError: Disk accounting silently lowers the memory threshold.
    """
    with pytest.raises(ValueError):
        modules["contract"].validate_pull_capacity(
            1_357_348_864, 3_306_106_880, 1024**3
        )
    modules["contract"].validate_pull_capacity(
        modules["contract"].MIN_AVAILABLE_MEMORY, 1024**3, 1024**3
    )


def test_runtime_failure_receipt_with_private_error_exports_only_classification(
    modules: dict[str, ModuleType], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Retain useful safe failure metadata with original private text excluded.

    :param modules: Real host control implementation.
    :param tmp_path: Real owned filesystem destination.
    :param capsys: Actual emitted safe decision output.
    :return: None after byte-level receipt and stdout privacy assertions pass.
    :raises AssertionError: Exception text leaks or export protection changes.
    """
    try:
        raise RuntimeError("PRIVATE_PASSWORD_AND_PROPOSAL_SENTINEL")
    except RuntimeError as error:
        modules["remote"].record_runtime_failure(tmp_path, error)
    target = tmp_path / "output/runtime-failure.json"
    record = json.loads(target.read_text())
    assert record["status"] == "FAILED" and record["exception_class"] == "RuntimeError"
    assert "PRIVATE_PASSWORD" not in target.read_text() + capsys.readouterr().out
    assert modules["remote"].evidence_files(tmp_path / "output") == [target]
    with pytest.raises(FileExistsError):
        modules["remote"].record_runtime_failure(tmp_path, RuntimeError("PRIVATE"))


def test_runtime_failure_receipt_with_linked_destination_rejects(
    modules: dict[str, ModuleType], tmp_path: Path
) -> None:
    """Do not follow a linked artifact directory while handling a failure.

    :param modules: Actual host control module.
    :param tmp_path: Real owned test directory.
    :return: None when the original outside bytes remain untouched.
    :raises AssertionError: Error recording writes through a link.
    """
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "output").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        modules["remote"].record_runtime_failure(tmp_path, RuntimeError("PRIVATE"))
    assert not list(outside.iterdir())


@pytest.mark.parametrize(
    "name",
    [
        "runtime-failure.json.env",
        "private/runtime-failure.json",
        "runtime-failure-secret.json",
    ],
)
def test_allowed_evidence_name_with_private_failure_variant_rejects(
    modules: dict[str, ModuleType], name: str
) -> None:
    """Admit only the fixed sanitized failure receipt, never private variants.

    :param modules: Real host control import.
    :param name: Unsafe failure-artifact spelling.
    :return: None after rejection.
    :raises AssertionError: The new artifact admission broadens unexpectedly.
    """
    assert modules["remote"].allowed_evidence_name(Path(name)) is False


def _docker_arguments_from_source(method_name: str) -> list[ast.expr]:
    """Read a concrete Docker call without replacing its runtime implementation.

    :param method_name: Actual host method; e.g. create_app_role.
    :return: The single Docker invocation's concrete argument expressions.
    :raises AssertionError: The source no longer has one such invocation.
    """
    tree = ast.parse((_RUNTIME / "remote.py").read_text())
    method = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == method_name
    )
    calls = [
        n
        for n in ast.walk(method)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "docker"
    ]
    assert len(calls) == 1
    return calls[0].args


def test_create_app_role_with_explicit_socket_matches_bootstrap_directory(
    modules: dict[str, ModuleType],
) -> None:
    """Keep the actual post-start SQL client on the verified writable socket.

    :param modules: Actual host control module and its source constants.
    :return: None after the concrete SQL invocation matches the default socket.
    :raises AssertionError: Role creation would connect to a different directory.
    """
    args = _docker_arguments_from_source("create_app_role")
    host_index = (
        next(
            i
            for i, value in enumerate(args)
            if isinstance(value, ast.Constant) and value.value == "-h"
        )
        + 1
    )
    target = args[host_index]
    actual = (
        getattr(modules["remote"], target.id)
        if isinstance(target, ast.Name)
        else ast.literal_eval(target)
    )
    assert actual == "/var/run/postgresql"


def test_image_cache_reserve_with_observed_idle_sizes_uses_digest_identity(
    modules: dict[str, ModuleType],
) -> None:
    """Accept measured exact images despite engine-dependent size accounting.

    :param modules: Actual contract implementation, without any cloud call.
    :return: None when the real copied records prove all three resident images.
    :raises AssertionError: CI storage-size representation is used as identity.
    """
    manifest, observed = _runtime_manifest(), json.loads(_OBSERVED_IDLE_CACHE_JSON)
    for role, row in observed.items():
        manifest[f"{role}_image"] = row["RepoDigests"][0]
    manifest["build_receipt"]["web_digest"] = manifest["web_image"].split("@")[1]
    manifest["image_sizes"] = {
        "web": 286_723_520,
        "browser": 750_259_047,
        "postgres": 166_208_812,
    }
    assert all(
        observed[role]["Size"] != size for role, size in manifest["image_sizes"].items()
    )
    assert modules["contract"].image_cache_reserve(manifest, observed) == 1024**3


# Actual read-only CI45526140670 metadata, source receipt SHA256
# 13ba76346cb63685e40b67b32c092f163d27fdb8c061227fa6e152dfb6c0e1d8.
_OBSERVED_IDLE_CACHE_JSON = '{"web":{"Id":"sha256:5d250803bac2ea5a1c545246d82b5a5eded74eec52451bf7eacef5738839ed61","RepoDigests":["411113550285.dkr.ecr.us-east-1.amazonaws.com/mimir@sha256:e7f6e2170fd6250a9b6c3f635ceb2b90d0dfbe81ed337c10180c0a903ca5e1ba"],"Os":"linux","Architecture":"amd64","Size":827361988},"browser":{"Id":"sha256:06420e0e4d82040e23ef50eec215ca9be5e1b66683ffc5df426268996ed013e4","RepoDigests":["411113550285.dkr.ecr.us-east-1.amazonaws.com/mimir@sha256:a74104c8fb4ff8a02dd053ee2584868d91dd4273f058b690faf0875684c5e368"],"Os":"linux","Architecture":"amd64","Size":1904824872},"postgres":{"Id":"sha256:a026aff735540e5492c2ac4a782edd7dffa9b3b816dbda710d63b7a84f2c9b82","RepoDigests":["postgres@sha256:07abc3f43c9395b0bdbbab36bc25ddb0e8d83cd4fcafb5fb7d6abe14ff156dd8"],"Os":"linux","Architecture":"amd64","Size":468060783}}'
