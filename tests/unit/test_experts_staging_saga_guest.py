"""Fault probes for the literal remote guest lane; no fake browser/server."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import pytest

_SOURCE = Path(__file__).resolve().parents[2] / "scripts/experts-staging/saga_guest.py"


@pytest.fixture(scope="module")
def guest() -> ModuleType:
    """Load the standalone runtime without application or server initialization."""
    spec = importlib.util.spec_from_file_location("cedar_saga_guest", _SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _oracle(guest: ModuleType) -> object:
    """Supply nonsecret public facts and synthetic private disclosure probes."""
    return guest.GuestOracle(
        "a" * 40,
        "b" * 64,
        "Maria maintains Accessibility Audit Playbook.",
        "/playbooks/6101/workflows/7001/",
        ("PRIVATE_VALUE", "private@example.com"),
    )


@pytest.mark.parametrize(
    "origin",
    [
        "https://mimir.featurefactory.io",
        "http://cedar-web:8443",
        "https://cedar-web:8443/",
        "https://cedar-web:8443/?x=1",
        "https://cedar-web:8443#x",
        "https://user@cedar-web:8443",
        "http://localhost:8000",
        "https://cedar-web.evil:8443",
    ],
)
def test_validate_origin_with_nonowned_endpoint_rejects(
    guest: ModuleType, origin: str
) -> None:
    """Reject live, deceptive, insecure or implicitly local endpoints."""
    with pytest.raises(ValueError):
        guest.validate_origin(origin)


def test_validate_origin_with_explicit_companion_and_local_proof_accepts(
    guest: ModuleType,
) -> None:
    """Keep staging and explicitly identified loopback verification separate."""
    assert guest.validate_origin("https://cedar-web:8443") == "https://cedar-web:8443"
    assert (
        guest.validate_origin("http://localhost:51234", local_verification=True)
        == "http://localhost:51234"
    )
    with pytest.raises(ValueError):
        guest.validate_origin("http://192.0.2.1:8000", local_verification=True)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_revision", "a" * 39),
        ("fixture_sha256", "B" * 64),
        ("summary", ""),
        ("workflow_path", "https://other.example/workflows/1/"),
        ("workflow_path", "/playbooks/999/workflows/7001/"),
        ("private_values", ()),
        ("private_values", ("",)),
    ],
)
def test_validate_oracle_with_incomplete_or_deceptive_fact_rejects(
    guest: ModuleType, field: str, value: object
) -> None:
    """Prevent missing expected content or identity from creating a vacuous pass."""
    with pytest.raises(ValueError):
        guest.validate_oracle(replace(_oracle(guest), **{field: value}))


def test_validate_oracle_with_complete_contract_accepts(guest: ModuleType) -> None:
    """Accept the explicit complete public content/reference contract."""
    guest.validate_oracle(_oracle(guest))


@pytest.mark.parametrize(
    "leak",
    [
        "PRIVATE_VALUE",
        "private%40example.com",
        "MAILTO:someone@example.com",
        '<i data-testid="profile-api-token"></i>',
        '<a data-testid="nav-view-profile"></a>',
        '<div id="navbar-user-menu"></div>',
    ],
)
def test_assert_guest_document_with_actual_markup_leak_rejects(
    guest: ModuleType, leak: str
) -> None:
    """Exercise real input strings without substituting any runtime response."""
    with pytest.raises(AssertionError):
        guest.assert_guest_document(
            f"<html><body>{leak}</body></html>", _oracle(guest).private_values
        )


def test_assert_guest_document_with_public_text_accepts(guest: ModuleType) -> None:
    """Require real content and active private probes for a disclosure check."""
    guest.assert_guest_document(
        "<html><body>Maria</body></html>", _oracle(guest).private_values
    )
    with pytest.raises(ValueError):
        guest.assert_guest_document("", _oracle(guest).private_values)
    with pytest.raises(ValueError):
        guest.assert_guest_document("<html>Public</html>", ())


@pytest.mark.parametrize("width", [360, 390, 768, 1024, 1280, 1512, 1920])
def test_assert_column_geometry_with_required_recipe_accepts(
    guest: ModuleType, width: int
) -> None:
    """Check both sides of the exact Bootstrap md breakpoint."""
    read = {"x": 10.0, "y": 20.0, "width": 200.0, "height": 300.0}
    rail = (
        {"x": 10.0, "y": 320.0, "width": 200.0, "height": 50.0}
        if width < 768
        else {"x": 210.0, "y": 20.0, "width": 100.0, "height": 50.0}
    )
    guest.assert_column_geometry(read, rail, width)


@pytest.mark.parametrize(
    ("width", "rail"),
    [
        (360, {"x": 10, "y": 319, "width": 200, "height": 50}),
        (360, {"x": 12, "y": 320, "width": 200, "height": 50}),
        (768, {"x": 208, "y": 20, "width": 100, "height": 50}),
        (768, {"x": 210, "y": 25, "width": 100, "height": 50}),
        (768, {"x": 210, "y": 20, "width": 120, "height": 50}),
    ],
)
def test_assert_column_geometry_with_overlap_or_wrong_recipe_rejects(
    guest: ModuleType, width: int, rail: dict[str, float]
) -> None:
    """Expose overlap, alignment and eight/four proportion faults."""
    with pytest.raises(AssertionError):
        guest.assert_column_geometry(
            {"x": 10, "y": 20, "width": 200, "height": 300}, rail, width
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 0, True])
def test_assert_column_geometry_with_invalid_measurement_rejects(
    guest: ModuleType, value: float
) -> None:
    """Reject nonfinite and nonpositive measured dimensions."""
    with pytest.raises(ValueError):
        guest.assert_column_geometry(
            {"x": 10, "y": 20, "width": value, "height": 300},
            {"x": 210, "y": 20, "width": 100, "height": 50},
            1280,
        )


def test_validate_output_with_real_private_and_linked_directories_checks_owner(
    guest: ModuleType, tmp_path: Path
) -> None:
    """Use actual directory modes and a real symlink for output confinement."""
    target = tmp_path / "private"
    target.mkdir(mode=0o700)
    assert guest.validate_output(target) == target
    linked = tmp_path / "linked"
    linked.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError):
        guest.validate_output(linked)
    target.chmod(0o755)
    with pytest.raises(ValueError):
        guest.validate_output(target)


@pytest.mark.parametrize(("x", "y"), [(210, 20), (10, 320), (-190, 20), (10, -280)])
def test_assert_disjoint_boxes_with_touching_edges_accepts(
    guest: ModuleType, x: float, y: float
) -> None:
    """Treat touching actual rectangles as adjacent rather than overlapping."""
    guest.assert_disjoint_boxes(
        {"x": 10, "y": 20, "width": 200, "height": 300},
        {"x": x, "y": y, "width": 200, "height": 300},
    )


@pytest.mark.parametrize(("x", "y"), [(209, 20), (10, 319), (10, 20), (15, 25)])
def test_assert_disjoint_boxes_with_intersection_rejects(
    guest: ModuleType, x: float, y: float
) -> None:
    """Expose even narrow overlap in independently measured card lanes."""
    with pytest.raises(AssertionError):
        guest.assert_disjoint_boxes(
            {"x": 10, "y": 20, "width": 200, "height": 300},
            {"x": x, "y": y, "width": 200, "height": 300},
        )
