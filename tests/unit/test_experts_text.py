from __future__ import annotations

import pytest

from methodology.services.expert_text import (
    category_label,
    display_initials,
    format_karma,
    format_numeric_fallback,
)


@pytest.mark.parametrize(
    ("books", "copies", "expected"),
    [
        (0, 0, "0 released playbooks · 0 copies"),
        (1, 1, "1 released playbook · 1 copy"),
        (2, 47, "2 released playbooks · 47 copies"),
    ],
)
def test_format_numeric_fallback_with_zero_singular_and_plural_counts_matches_copy(
    books: int, copies: int, expected: str
) -> None:
    """Check the approved fallback text at each pluralization boundary."""
    assert format_numeric_fallback(books, copies) == expected


@pytest.mark.parametrize("value", [True, -1, 1.5, "1"])
def test_expert_text_with_invalid_values_rejects(value: object) -> None:
    """Reject invalid numbers in the score and in both independent counts."""
    with pytest.raises(ValueError):
        format_karma(value)
    with pytest.raises(ValueError):
        format_numeric_fallback(value, 1)
    with pytest.raises(ValueError):
        format_numeric_fallback(1, value)


@pytest.mark.parametrize("value", ["", " ", None, [], "unknown"])
def test_category_label_with_unsupported_value_raises_value_error(
    value: object,
) -> None:
    """Reject any input outside the canonical Playbook category slugs."""
    with pytest.raises(ValueError):
        category_label(value)


@pytest.mark.parametrize("value", ["", " \n ", None])
def test_display_initials_with_invalid_name_rejects(value: object) -> None:
    """Require nonblank public display names."""
    with pytest.raises(ValueError):
        display_initials(value)


def test_display_initials_with_real_cedar_names_returns_expected_letters() -> None:
    """Derive stable initials from fictional contributor names."""
    assert display_initials("Maria Rodriguez") == "MR"
    assert display_initials("  Sofia\tReed ") == "SR"
    assert display_initials("  Sam ") == "S"
    assert display_initials("Priya Nair Singh") == "PN"


def test_format_karma_and_category_label_with_cedar_values_matches_ui() -> None:
    """Use readable scores and existing category labels."""
    assert format_karma(8200) == "8,200"
    assert format_karma(0) == "0"
    assert category_label("design") == "Design"
