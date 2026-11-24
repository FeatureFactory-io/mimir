"""Extract actual category anchors for HTTP acceptance assertions."""

from __future__ import annotations

from dataclasses import dataclass

from tests.support.experts_html import _walk_elements, element_text, find_by_test_id


@dataclass(frozen=True)
class CategoryAnchor:
    """Immutable rendered anchor. Example: Design, ?category=design, page."""

    label: str
    href: str
    test_id: str
    aria_current: str | None


def category_anchors(html: str) -> tuple[CategoryAnchor, ...]:
    """Extract category anchors from real rendered HTML.

    :param html: Response HTML as str. Example: response.content.decode().
    :return: Immutable anchors in DOM order. Example: (CategoryAnchor(
        "Design", "?category=design", "experts-category-design", "page"),).
    :raises TypeError: If html is not str.
    :raises AssertionError: If category navigation is absent or malformed.
    """
    if not isinstance(html, str):
        raise TypeError("Category navigation HTML must be text.")
    navigation = find_by_test_id(html, "experts-category-tabs")
    assert navigation.name == "nav", "Expected a category navigation element."

    anchors: list[CategoryAnchor] = []
    for element in _walk_elements(navigation):
        if element.name != "a":
            continue
        attributes = dict(element.attributes)
        label = element_text(element)
        href = attributes.get("href")
        test_id = attributes.get("data-testid")
        assert label and href and test_id, "Expected a labeled category link and hook."
        anchors.append(
            CategoryAnchor(label, href, test_id, attributes.get("aria-current"))
        )
    assert anchors, "Expected at least one category link."
    return tuple(anchors)
