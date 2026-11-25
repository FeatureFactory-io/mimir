"""Fail-closed Cedar staging contracts exercised without any cloud operations."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[2] / "scripts/experts-staging/contract.py"
_SPEC = importlib.util.spec_from_file_location("experts_staging_contract", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
contract = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = contract
_SPEC.loader.exec_module(contract)
_SHA = "a" * 40
_ACCOUNT = "411113550285"


def test_run_readiness_with_browser_context_blocks_service_workers() -> None:
    """Require the actual public context call to disable routing bypasses.

    :return: None when workers are blocked and TLS validation remains enabled.
    :raises AssertionError: The concrete browser context options are unsafe.
    """
    tree = ast.parse((_PATH.parent / "browser.py").read_text())
    readiness = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_readiness"
    )
    contexts = [
        node
        for node in ast.walk(readiness)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "new_context"
    ]
    assert len(contexts) == 1
    options = {keyword.arg: keyword.value for keyword in contexts[0].keywords}
    assert (
        ast.literal_eval(options.get("service_workers", ast.Constant(None))) == "block"
    )
    assert ast.literal_eval(options["ignore_https_errors"]) is False


def _receipt() -> dict[str, object]:
    """Return a syntactically valid build identity; it never contacts AWS."""
    return {
        "source_revision": _SHA,
        "run_id": "123",
        "web_image": f"{_ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com/mimir",
        "web_digest": "sha256:" + "b" * 64,
        "platforms": ["linux/amd64", "linux/arm64"],
    }


def test_validate_receipt_with_exact_build_returns_immutable_ecr_address() -> None:
    assert contract.validate_receipt(_receipt(), _SHA, "123", _ACCOUNT).endswith(
        "@sha256:" + "b" * 64
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_revision", "c" * 40),
        ("run_id", "456"),
        ("web_image", "docker.io/evil/mimir"),
        ("web_digest", "latest"),
        ("web_digest", "sha256:" + "B" * 64),
        ("platforms", ["linux/arm64"]),
    ],
)
def test_validate_receipt_with_wrong_identity_rejects(
    field: str, value: object
) -> None:
    receipt = _receipt()
    receipt[field] = value
    with pytest.raises(ValueError):
        contract.validate_receipt(receipt, _SHA, "123", _ACCOUNT)


@pytest.mark.parametrize("nonce", ["", "../other", "A" * 32, "f" * 31, "f" * 33])
def test_owner_record_with_invalid_nonce_rejects(nonce: str) -> None:
    with pytest.raises(ValueError):
        contract.owner_record(nonce)


def test_owner_record_with_valid_nonce_has_only_dedicated_nonprivileged_identity() -> (
    None
):
    record = contract.owner_record("a" * 32)
    assert record == {
        "format": "mimir-experts-owned-postgres-v1",
        "fixture": "CEDAR-RFP-01",
        "owner_id": "a" * 32,
        "database": "experts_cedar_" + "a" * 32,
        "role": "experts_cedar_" + "a" * 32,
        "host": "cedar-db",
        "port": "5432",
    }


def _environments() -> list[dict[str, str]]:
    return [
        {
            "ApplicationName": "mimir",
            "EnvironmentName": "mimir-idle",
            "EnvironmentId": "e-live",
            "Status": "Ready",
            "CNAME": "mimir-prod.eba-abc.us-east-1.elasticbeanstalk.com",
        },
        {
            "ApplicationName": "mimir",
            "EnvironmentName": "mimir-prod",
            "EnvironmentId": "e-idle",
            "Status": "Ready",
            "CNAME": "mimir-prod.us-east-1.elasticbeanstalk.com",
        },
    ]


def test_select_idle_with_rotated_names_uses_cname_instead_of_physical_name() -> None:
    assert contract.select_idle(_environments())["EnvironmentId"] == "e-idle"


@pytest.mark.parametrize(
    "mode", ["two_live", "no_live", "wrong_app", "updating", "missing", "foreign_cname"]
)
def test_select_idle_with_ambiguous_or_foreign_topology_rejects(mode: str) -> None:
    rows = _environments()
    if mode == "two_live":
        rows[1]["CNAME"] = "mimir-prod.eba-def.us-east-1.elasticbeanstalk.com"
    if mode == "no_live":
        rows[0]["CNAME"] = "mimir-idle.us-east-1.elasticbeanstalk.com"
    if mode == "wrong_app":
        rows[1]["ApplicationName"] = "other"
    if mode == "updating":
        rows[1]["Status"] = "Updating"
    if mode == "missing":
        rows.pop()
    if mode == "foreign_cname":
        rows[1]["CNAME"] = "attacker.invalid"
    with pytest.raises(ValueError):
        contract.select_idle(rows)


@pytest.mark.parametrize(
    "memory,disk",
    [
        (1399 * 1024 * 1024, 8 * 1024**3),
        (2 * 1024**3, 4 * 1024**3 - 1),
        (-1, 8 * 1024**3),
    ],
)
def test_validate_capacity_with_insufficient_fresh_reserve_rejects(
    memory: int, disk: int
) -> None:
    with pytest.raises(ValueError):
        contract.validate_capacity(memory, disk)


def test_validate_capacity_with_exact_threshold_succeeds() -> None:
    contract.validate_capacity(
        contract.MIN_AVAILABLE_MEMORY, contract.MIN_AVAILABLE_DISK
    )


@pytest.mark.parametrize(
    "path",
    [
        "../outside.py",
        "/app/evil.py",
        "accounts/../../outside.py",
        "infra/.env",
        "accounts/a\\b.py",
    ],
)
def test_validate_source_files_with_unsafe_path_rejects(
    tmp_path: Path, path: str
) -> None:
    with pytest.raises(ValueError):
        contract.validate_source_files(tmp_path, {path: "a" * 64})


def test_validate_source_files_with_real_tree_detects_changed_or_symlinked_source(
    tmp_path: Path,
) -> None:
    files = {
        "mimir/settings/base.py": b"BASE=True\n",
        "methodology/models/karma_award.py": b"MODEL=True\n",
        "tests/support/experts_data.py": b"GUARD=True\n",
        "test-data/experts/cedar-rfp-01.json": b"{}\n",
        "tests/uat/e2e-uat-flow.feature": b"Feature: UAT\n",
        "tests/e2e/test_expert_cards.py": b"VIEWPORTS=()\n",
    }
    hashes = {}
    for name, data in files.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    contract.validate_source_files(tmp_path, hashes)
    changed = tmp_path / "mimir/settings/base.py"
    changed.write_text("different")
    with pytest.raises(ValueError):
        contract.validate_source_files(tmp_path, hashes)
    changed.unlink()
    outside = tmp_path.parent / "foreign-source.py"
    outside.write_bytes(files["mimir/settings/base.py"])
    changed.symlink_to(outside)
    with pytest.raises(ValueError):
        contract.validate_source_files(tmp_path, hashes)
