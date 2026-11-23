"""Pure category resolver tests; S47 appends dedicated tie contracts."""

from __future__ import annotations

from methodology.services.experts_service import resolve_primary_category


def test_resolve_primary_category_with_highest_points_selects_design() -> None:
    """Prove category selection uses awarded points.

    :return: None. Example: None.
    :raises AssertionError: If 7200 Design loses to 1000 Development.
    """
    raise NotImplementedError()


def test_resolve_primary_category_with_zero_points_returns_none() -> None:
    """Prove an account without positive contribution has no category.

    :return: None. Example: None.
    :raises AssertionError: If zero totals acquire a primary category.
    """
    raise NotImplementedError()


def test_resolve_primary_category_with_invalid_values_rejects() -> None:
    """Prove invalid categories, booleans and negative values fail clearly.

    :return: None. Example: None.
    :raises AssertionError: If invalid inputs are accepted.
    """
    raise NotImplementedError()
