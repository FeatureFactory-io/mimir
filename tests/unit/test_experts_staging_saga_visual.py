"""Pure fail-closed visual contracts with checked real source and fixture inputs."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "scripts/experts-staging"))
import saga_visual_contract as contract


def test_validate_output_with_private_owned_directory_accepts(tmp_path: Path) -> None:
    """Original acquisitions use an explicit owned private root."""
    tmp_path.chmod(0o700)
    assert contract.validate_output(tmp_path) == tmp_path


@pytest.mark.parametrize("variant", ["public", "linked", "absent", "relative"])
def test_validate_output_with_unsafe_directory_rejects(
    tmp_path: Path, variant: str
) -> None:
    """Public, redirected, missing or relative roots cannot acquire evidence."""
    tmp_path.chmod(0o700)
    if variant == "public":
        tmp_path.chmod(0o755)
        path = tmp_path
    elif variant == "linked":
        path = tmp_path / "linked"
        path.symlink_to(tmp_path, target_is_directory=True)
    elif variant == "relative":
        path = Path("relative")
    else:
        path = tmp_path / "absent"
    with pytest.raises(ValueError):
        contract.validate_output(path)


@pytest.mark.parametrize("case", [None, "", "normal", "guest", 1, "../missing_summary"])
def test_validate_case_with_other_lane_rejects(case: object) -> None:
    """Normal and guest modules cannot stand in for these two explicit variants."""
    with pytest.raises(ValueError):
        contract.validate_case(case)


def test_browser_import_with_clean_process_never_imports_django() -> None:
    """Credential-free browser graph never executes the ORM-coupled source test."""
    code = (
        "import sys; sys.path.insert(0, "
        + repr(str(_REPO / "scripts/experts-staging"))
        + "); import saga_visual_browser; assert not any(name == 'django' or name.startswith('django.') for name in sys.modules)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


def test_expected_contributors_with_reordered_fixture_rejects() -> None:
    """Exact source constants cannot mask an altered independent fixture order."""
    values = contract.source_constants(_REPO / "tests/e2e/test_expert_cards.py")
    document = json.loads((_REPO / "test-data/experts/cedar-rfp-01.json").read_text())
    document["expected_design_order"].reverse()
    with pytest.raises(ValueError):
        contract.expected_contributors(document, "long_identity_and_prose", values)


def test_source_constants_with_exact_candidate_reads_checked_literals() -> None:
    """Actual candidate source yields all seven sizes without executing imports."""
    values = contract.source_constants(_REPO / "tests/e2e/test_expert_cards.py")
    assert len(values["VIEWPORTS"]) == 7
    assert values["_LONG_FIRST"] == "MaríaFernandaAlejandraCatalinaValentina"
    assert (
        values["source_sha256"]
        == "896285a8b9281e28cda5f66515c7e09a5c3bbcab96caa0d3f5e712046abac379"
    )


def test_source_constants_with_changed_bytes_rejects(tmp_path: Path) -> None:
    """Even a harmless source drift cannot masquerade as the exact candidate."""
    path = tmp_path / "test.py"
    path.write_bytes((_REPO / "tests/e2e/test_expert_cards.py").read_bytes() + b"\n")
    with pytest.raises(ValueError):
        contract.source_constants(path)


@pytest.mark.parametrize("case", contract.CASES)
def test_expected_contributors_with_actual_fixture_has_exact_variant(case: str) -> None:
    """Long Maria replaces identity/prose and missing uses real Mike Development."""
    values = contract.source_constants(_REPO / "tests/e2e/test_expert_cards.py")
    document = json.loads((_REPO / "test-data/experts/cedar-rfp-01.json").read_text())
    category, rows = contract.expected_contributors(document, case, values)
    if case == "missing_summary":
        assert category == "Development" and rows[0]["username"] == "mchen"
        assert (rows[0]["total"], rows[0]["hint"]) == (
            "12,450",
            "2 released playbooks · 47 copies",
        )
    else:
        assert category == "Design" and rows[1]["username"] == "mrodriguez"
        assert rows[1]["name"] == values["_LONG_FIRST"] + " " + values["_LONG_LAST"]
        assert rows[1]["hint"] == values["_LONG_SUMMARY"]


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_allow_visual_request_with_unrelated_write_rejects(method: str) -> None:
    """No proposal, award or token mutation endpoint gains a visual exception."""
    assert not contract.allow_visual_request(
        "https://cedar-web:8443/karma/copy-receipts/", method
    )


def test_allow_visual_request_with_exact_login_and_read_allows() -> None:
    """Only ordinary login POST and actual permitted asset/document reads pass."""
    assert contract.allow_visual_request(
        "https://cedar-web:8443/auth/user/login/", "POST"
    )
    assert contract.allow_visual_request(
        "https://cedar-web:8443/experts/?category=design", "GET"
    )
    assert not contract.allow_visual_request(
        "https://cedar-web:8443/auth/user/login/?next=x", "POST"
    )
    assert not contract.allow_visual_request(
        "https://example.com/auth/user/login/", "POST"
    )


def test_assert_preparation_rows_with_missing_requires_exact_no_change() -> None:
    """No mutation at all is allowed in the missing-summary fixture lane."""
    original = {"auth.user": {}, "methodology.expertprofile": {}, "other": {}}
    contract.assert_preparation_rows(
        original, copy.deepcopy(original), "missing_summary", {}
    )
    with pytest.raises(AssertionError):
        contract.assert_preparation_rows(
            original, {**original, "extra": {}}, "missing_summary", {}
        )
