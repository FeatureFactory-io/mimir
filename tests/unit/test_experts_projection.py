"""Pure category resolver tests; S47 appends dedicated tie contracts."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from methodology.services.experts_service import resolve_primary_category


def test_resolve_primary_category_with_highest_points_selects_design() -> None:
    """Verify awarded points control the primary category before release counts."""
    assert (
        resolve_primary_category(
            {"design": 7200, "development": 1000}, {"development": 5}
        )
        == "design"
    )


@pytest.mark.parametrize("points", [{}, {"design": 0, "development": 0}])
def test_resolve_primary_category_with_zero_points_returns_none(
    points: Mapping[str, int],
) -> None:
    """A release alone does not imply a primary category."""
    assert resolve_primary_category(points, {"design": 1}) is None


@pytest.mark.parametrize(
    ("points", "counts"),
    [
        ({"invalid": 1}, {}),
        ({"design": True}, {}),
        ({"design": -1}, {}),
        ({"design": 1.0}, {}),
        ({"design": 1}, {"other": -1}),
        ({"design": 1}, {"design": False}),
        ({}, {"invalid": 1}),
    ],
)
def test_resolve_primary_category_with_invalid_values_rejects(
    points: Mapping[str, int], counts: Mapping[str, int]
) -> None:
    """Validate all keys and counts even where they would not affect the winner."""
    with pytest.raises(ValueError):
        resolve_primary_category(points, counts)


def test_resolve_primary_category_with_equal_points_applies_both_tiebreaks() -> None:
    """Prefer release counts, then existing alphabetical display labels."""
    points = {"research": 100, "development": 100, "design": 100}
    assert resolve_primary_category(points, {"research": 1}) == "research"
    assert resolve_primary_category(points, {"development": 1, "design": 1}) == "design"
