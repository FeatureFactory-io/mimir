from __future__ import annotations


def test_find_by_test_id_with_matching_root_includes_root() -> None:
    """Find a selector on the sole parsed root rather than skipping it.

    :return: None on the asserted contract. Example: None.
    :raises AssertionError: The described boundary or actual evidence differs.
    """
    raise NotImplementedError()


def test_find_by_test_id_with_duplicate_selectors_rejects() -> None:
    """Reject multiple matches rather than silently selecting one.

    :return: None on the asserted contract. Example: None.
    :raises AssertionError: The described boundary or actual evidence differs.
    """
    raise NotImplementedError()


def test_element_text_with_nested_elements_preserves_document_order() -> None:
    """Preserve descendant text order and normalize whitespace with Django HTML Elements.

    :return: None on the asserted contract. Example: None.
    :raises AssertionError: The described boundary or actual evidence differs.
    """
    raise NotImplementedError()
