from __future__ import annotations

import pytest

from tests.support.experts_html import (
    assert_karma_source_rows,
    element_text,
    find_by_test_id,
)

_PUBLIC_SOURCE_TABLE = """
<span data-testid="expert-karma-total">8,200</span>
<table data-testid="karma-source-breakdown">
  <thead><tr><th scope="col">Source</th><th scope="col">Karma</th></tr></thead>
  <tbody>
    <tr><th scope="row">Released playbooks</th><td>{released}</td></tr>
    <tr><th scope="row">PIP contributions</th><td>1,600</td></tr>
    <tr><th scope="row">Consumption</th><td>1,200</td></tr>
    <tr><th scope="row">Learning</th><td>400</td></tr>
  </tbody>
  <tfoot><tr><th scope="row">Total</th><td>8,200</td></tr></tfoot>
</table>
"""
_PUBLIC_SOURCES = {
    "Released playbooks": 5000,
    "PIP contributions": 1600,
    "Consumption": 1200,
    "Learning": 400,
}


def test_find_by_test_id_with_matching_root_includes_root() -> None:
    """Find a selector on the sole parsed root."""
    root = find_by_test_id(
        b'<article data-testid="cedar-card">Card</article>', "cedar-card"
    )
    assert root.name == "article"
    assert ("data-testid", "cedar-card") in root.attributes


def test_find_by_test_id_with_duplicate_selectors_rejects() -> None:
    """Reject matching descendants even when the root already matches."""
    with pytest.raises(AssertionError, match="card"):
        find_by_test_id(
            '<article data-testid="card"><p data-testid="card">Two</p></article>',
            "card",
        )


def test_element_text_with_nested_elements_preserves_document_order() -> None:
    """Normalize whitespace and retain descendant text order."""
    element = find_by_test_id(
        '<p data-testid="card"> Maria <strong>Rodriguez</strong>\n '
        "<span><b>8,200</b></span> &amp; evidence </p>",
        "card",
    )
    assert element_text(element) == "Maria Rodriguez 8,200 & evidence"


def test_find_by_test_id_with_no_matching_element_rejects() -> None:
    """Fail clearly for HTML without the requested exact selector."""
    with pytest.raises(AssertionError, match="missing"):
        find_by_test_id("<p>Real text</p>", "missing")


@pytest.mark.parametrize(
    ("html", "test_id"), [(b"\xff", "card"), ("<p></p>", " "), (3, "card")]
)
def test_find_by_test_id_with_invalid_input_raises_value_error(
    html: object, test_id: str
) -> None:
    """Reject invalid UTF-8, malformed argument types and blank selectors."""
    with pytest.raises(ValueError):
        find_by_test_id(html, test_id)


def test_element_text_with_non_element_raises_value_error() -> None:
    """Require a parsed Django Element."""
    with pytest.raises(ValueError):
        element_text("plain text")


@pytest.mark.parametrize("released", ["5000", "50,00"])
def test_assert_karma_source_rows_with_wrong_public_grouping_rejects(
    released: str,
) -> None:
    """Reject public source amounts that use the wrong digit grouping.

    :param released: Rendered released points. Example: "50,00".
    :return: None when the helper rejects the format.
    :raises AssertionError: If a public amount bypasses exact formatting.
    """
    with pytest.raises(AssertionError, match="Released playbooks"):
        assert_karma_source_rows(
            _PUBLIC_SOURCE_TABLE.format(released=released),
            _PUBLIC_SOURCES,
            "expert-karma-total",
            8200,
        )


@pytest.mark.parametrize("points", [True, -1])
def test_assert_karma_source_rows_with_invalid_points_rejects(points: int) -> None:
    """Require semantic nonnegative integers for the expected amounts.

    :param points: Invalid expected contribution. Example: True.
    :return: None when the helper rejects the expected amount.
    :raises AssertionError: If the invalid expectation bypasses validation.
    """
    expected = _PUBLIC_SOURCES | {"Learning": points}
    with pytest.raises(AssertionError, match="nonnegative integers"):
        assert_karma_source_rows(
            _PUBLIC_SOURCE_TABLE.format(released="5,000"),
            expected,
            "expert-karma-total",
            sum(expected.values()),
        )
