"""Keep reduced staging capacity bound to the reviewed immutable CI measurement."""

import hashlib
import importlib.util
import io
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[2]


def _module():
    """Load the standalone proof validator without importing Django.

    :return: Newly loaded control-plane module.
    :raises ImportError: The module is unavailable.
    """
    path = _ROOT / "scripts/experts-staging/download_resource_proof.py"
    spec = importlib.util.spec_from_file_location("download_resource_proof", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fixture(monkeypatch):
    """Create a harmless ZIP with independently bound member and archive hashes.

    :param monkeypatch: Pytest replacement scope for synthetic fixture digests.
    :return: Validator module and synthetic artifact bytes.
    """
    module = _module()
    members = {
        "benchmark-result.json": b'{"measurement":"fixture"}\n',
        "benchmark-source.json": b'{"source":"fixture"}\n',
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
        archive.writestr("screenshots/private-not-requested.png", b"excluded")
    payload = buffer.getvalue()
    monkeypatch.setattr(module, "ARCHIVE_SHA256", hashlib.sha256(payload).hexdigest())
    monkeypatch.setattr(
        module,
        "PROOF_MEMBERS",
        {
            name: (len(value), hashlib.sha256(value).hexdigest())
            for name, value in members.items()
        },
    )
    return module, payload


def test_extract_proof_with_verified_artifact_writes_only_two_bound_files(
    tmp_path,
    monkeypatch,
):
    module, payload = _fixture(monkeypatch)
    archive = tmp_path / "original.zip"
    archive.write_bytes(payload)
    output = tmp_path / "proof"
    module.extract_proof(archive, output)
    assert {p.name for p in output.iterdir()} == set(module.PROOF_MEMBERS)
    assert output.stat().st_mode & 0o777 == 0o700
    for name, (_, digest) in module.PROOF_MEMBERS.items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("condition", ["changed", "symlink", "hardlink", "oversize"])
def test_extract_proof_with_untrusted_archive_fails_before_output(
    tmp_path,
    monkeypatch,
    condition,
):
    module, payload = _fixture(monkeypatch)
    archive = tmp_path / "original.zip"
    archive.write_bytes(payload)
    if condition == "changed":
        archive.write_bytes(payload + b"altered")
    elif condition == "symlink":
        target = tmp_path / "target.zip"
        archive.rename(target)
        archive.symlink_to(target)
    elif condition == "hardlink":
        (tmp_path / "alias.zip").hardlink_to(archive)
    else:
        monkeypatch.setattr(module, "MAX_ARCHIVE_BYTES", len(payload) - 1)
    with pytest.raises((ValueError, OSError)):
        module.extract_proof(archive, tmp_path / "proof")
    assert not (tmp_path / "proof").exists()


def test_extract_proof_with_invalid_member_digest_fails_before_output(
    tmp_path, monkeypatch
):
    module, payload = _fixture(monkeypatch)
    archive = tmp_path / "original.zip"
    archive.write_bytes(payload)
    monkeypatch.setattr(
        module,
        "PROOF_MEMBERS",
        {
            **module.PROOF_MEMBERS,
            "benchmark-result.json": (len(b"{}"), "0" * 64),
        },
    )
    with pytest.raises(ValueError):
        module.extract_proof(archive, tmp_path / "proof")
    assert not (tmp_path / "proof").exists()


def test_extract_proof_with_existing_output_preserves_original_bytes(
    tmp_path, monkeypatch
):
    module, payload = _fixture(monkeypatch)
    archive = tmp_path / "original.zip"
    archive.write_bytes(payload)
    output = tmp_path / "proof"
    output.mkdir()
    original = output / "benchmark-result.json"
    original.write_bytes(b"preserve")
    with pytest.raises(FileExistsError):
        module.extract_proof(archive, output)
    assert original.read_bytes() == b"preserve"


def test_resource_dispatch_with_reduced_budget_requires_exact_closed_proof_chain():
    workflow = yaml.load(
        (_ROOT / ".github/workflows/build-and-deploy.yml").read_text(),
        Loader=yaml.BaseLoader,
    )
    option = workflow["on"]["workflow_dispatch"]["inputs"]["experts_resource_profile"]
    assert option["default"] == "default"
    assert option["options"] == ["default", "aggregate1024"]
    job = workflow["jobs"]["experts-staging"]
    assert job["env"]["RESOURCE_PROFILE"] == "${{ inputs.experts_resource_profile }}"
    assert (
        'case "$RESOURCE_PROFILE" in default|aggregate1024)' in job["steps"][0]["run"]
    )
    proof = next(
        step
        for step in job["steps"]
        if step.get("name") == "Verify immutable measured resource proof"
    )
    assert proof["if"] == "inputs.experts_resource_profile == 'aggregate1024'"
    assert (
        "repos/FeatureFactory-io/mimir/actions/artifacts/14991594192/zip"
        in proof["run"]
    )
    assert "download_resource_proof.py" in proof["run"]
    assert "${{" not in proof["run"]
    prepare = next(
        step["run"] for step in job["steps"] if step.get("id") == "experts-source"
    )
    assert '--resource-profile "$RESOURCE_PROFILE"' in prepare
    assert 'if [[ "$RESOURCE_PROFILE" = aggregate1024 ]]' in prepare
    assert (
        "--resource-proof-result measured-resource-proof/benchmark-result.json"
        in prepare
    )
    assert (
        "--resource-proof-source measured-resource-proof/benchmark-source.json"
        in prepare
    )
    assert '"${RESOURCE_PROOF_ARGS[@]}"' in prepare
