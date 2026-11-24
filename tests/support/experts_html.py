"""Semantic real-response HTML helpers shared across Experts acceptance tests."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from http import HTTPStatus

from django.http import HttpResponse
from django.test.html import Element, HTMLParseError, parse_html

_OTHER_EMPTY_MESSAGE = "No experts in Other yet — release a playbook to be the first"
_SOURCE_TABLE_BY_TOTAL_ID = {
    "profile-karma-total": "profile-karma-source-breakdown",
    "expert-karma-total": "karma-source-breakdown",
}
_SOURCE_ROW_COUNT = 4
_SOURCE_ROW_GROUPS = ("thead", "tbody", "tfoot")


def find_by_test_id(html: str | bytes, test_id: str) -> Element:
    """Find exactly one matching element, including a matching parsed root.

    :param html: Actual response HTML. Example: response.content.
    :param test_id: Exact stable selector value. Example: "experts-leaderboard".
    :return: Matching Django Element. Example: the ranked section element.
    :raises AssertionError: If zero or multiple elements match.
    :raises ValueError: For blank selector or malformed input type.
    """
    if not isinstance(test_id, str) or not test_id.strip():
        raise ValueError("A nonblank test ID is required.")
    matches = [
        element
        for element in _walk_elements(_parse_root(html))
        if ("data-testid", test_id) in element.attributes
    ]
    assert (
        len(matches) == 1
    ), f"Expected one data-testid={test_id!r}, found {len(matches)}"
    return matches[0]


def element_text(element: Element) -> str:
    """Collect descendant text in DOM order and normalize whitespace.

    :param element: Parsed element. Example: a contributor card.
    :return: Normalized visible textual content. Example: "Maria Rodriguez 8,200".
    :raises ValueError: For an invalid element.
    """
    return " ".join(" ".join(_text_fragments(element)).split())


def _walk_elements(root: Element) -> Iterator[Element]:
    """Traverse root and descendant Elements in document order.

    :param root: Parsed document or sole top-level element. Example: an article.
    :return: Iterator including root. Example: iterated article then children.
    :raises ValueError: For a non-Element root.
    """
    if not isinstance(root, Element):
        raise ValueError("A Django HTML Element is required.")  # noqa: TRY004
    yield root
    for child in root.children:
        if isinstance(child, Element):
            yield from _walk_elements(child)


def _parse_root(html: str | bytes) -> Element:
    """Decode actual HTML and use Django's existing semantic parser.

    :param html: Actual HTML content. Example: response.content.
    :return: Parsed root. Example: an Element named "section".
    :raises ValueError: For unsupported type or invalid decoding.
    """
    if not isinstance(html, (str, bytes)):
        raise ValueError("HTML must be text or UTF-8 bytes.")  # noqa: TRY004
    try:
        return parse_html(html.decode("utf-8") if isinstance(html, bytes) else html)
    except (UnicodeDecodeError, HTMLParseError) as error:
        raise ValueError("Could not parse the response as HTML.") from error


def _text_fragments(element: Element) -> Iterator[str]:
    """Yield text children recursively without reordering nested content.

    :param element: Parsed element. Example: a score span.
    :return: Ordered string fragments. Example: iterated "8,200".
    :raises ValueError: For a non-Element input.
    """
    if not isinstance(element, Element):
        raise ValueError("A Django HTML Element is required.")  # noqa: TRY004
    for child in element.children:
        if isinstance(child, Element):
            yield from _text_fragments(child)
        else:
            yield child


def assert_no_expert_cards(response: HttpResponse) -> None:
    """Assert a successful leaderboard has no contributor cards.

    :param response: Real Django response. Example: client.get("/experts/?category=other").
    :return: None when HTTP 200 and zero experts-card-* nodes are present.
    :raises AssertionError: If status, leaderboard or card absence differs.
    """
    assert response.status_code == HTTPStatus.OK
    leaderboard = find_by_test_id(response.content, "experts-leaderboard")
    cards = [
        value
        for node in _walk_elements(leaderboard)
        for name, value in node.attributes
        if name == "data-testid" and value.startswith("experts-card-")
    ]
    assert not cards, f"Expected an empty leaderboard, found {cards!r}"


def assert_other_empty_message(response: HttpResponse) -> None:
    """Assert exact Other explanation and current category.

    :param response: Real Django response. Example: client.get("/experts/?category=other").
    :return: None when experts-empty text is exact and Other is current.
    :raises AssertionError: If status, element text or aria-current differs.
    """
    assert response.status_code == HTTPStatus.OK
    empty = find_by_test_id(response.content, "experts-empty")
    assert element_text(empty) == _OTHER_EMPTY_MESSAGE
    category = find_by_test_id(response.content, "experts-category-other")
    assert ("aria-current", "page") in category.attributes


def assert_karma_source_rows(
    html: str, expected: Mapping[str, int], total_test_id: str, expected_total: int
) -> None:
    """Assert four source body rows reconcile with footer and card total.

    :param html: Actual production response HTML. Example: response.content.decode().
    :param expected: Ordered source amounts. Example: {"Released": 5000, "PIP": 1600, "Consumption": 1200, "Learning": 400}.
    :param total_test_id: Own or public score selector. Example: "profile-karma-total".
    :param expected_total: Required integer total. Example: 8200.
    :return: None. Example: all body, footer and card assertions pass.
    :raises AssertionError: For missing, duplicated, unexpected or inconsistent rows.
    :raises ValueError: For a score selector without a registered source table.
    """
    table_id = _SOURCE_TABLE_BY_TOTAL_ID.get(total_test_id)
    if table_id is None:
        raise ValueError(f"No Karma source table is registered for {total_test_id!r}.")
    table = find_by_test_id(html, table_id)
    assert table.name == "table"
    children = [node for node in table.children if isinstance(node, Element)]
    groups = [node for node in children if node.name != "caption"]
    assert tuple(group.name for group in groups) == _SOURCE_ROW_GROUPS
    assert len(expected) == _SOURCE_ROW_COUNT
    assert sum(expected.values()) == expected_total
    displayed_total = f"{expected_total:,}"
    body_rows = [(label, str(points)) for label, points in expected.items()]
    expected_rows = ([("Source", "Karma")], body_rows, [("Total", displayed_total)])
    for group, expected_group in zip(groups, expected_rows, strict=True):
        rows = [row for row in group.children if isinstance(row, Element)]
        assert len(rows) == len(expected_group), f"Wrong number of {group.name} rows"
        for row, expected_cells in zip(rows, expected_group, strict=True):
            cells = [cell for cell in row.children if isinstance(cell, Element)]
            is_header = group.name == "thead"
            assert row.name == "tr"
            assert [cell.name for cell in cells] == ["th", "th" if is_header else "td"]
            assert ("scope", "col" if is_header else "row") in cells[0].attributes
            if is_header:
                assert ("scope", "col") in cells[1].attributes
            assert tuple(element_text(cell) for cell in cells) == expected_cells
    total = find_by_test_id(html, total_test_id)
    assert total not in _walk_elements(
        table
    ), "The score must be separate from the table"
    assert element_text(total) == displayed_total
