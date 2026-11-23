from __future__ import annotations

import pytest

from tests.support.experts_html import element_text, find_by_test_id


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
