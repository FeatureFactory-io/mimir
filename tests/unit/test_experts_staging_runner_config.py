"""Verify dangerous staging boundaries with real files and pure command contracts."""

from __future__ import annotations

import ast
import importlib.util
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
