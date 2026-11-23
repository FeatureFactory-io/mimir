from __future__ import annotations

"""Extract actual category anchors for HTTP acceptance assertions."""
from dataclasses import dataclass
from html.parser import HTMLParser


@dataclass(frozen=True)
class CategoryAnchor:
    """Immutable rendered anchor. Example: Design, ?category=design, page."""

    label: str
    href: str
    test_id: str
    aria_current: str | None


class _CategoryNavParser(HTMLParser):
    """Read only anchors inside the uniquely identified category navigation."""

    def __init__(self) -> None:
        """Prepare bounded category navigation capture.

        :return: None. Example: initialized parser.
        :raises NotImplementedError: Until BPE implements this skeleton.
        """
        raise NotImplementedError

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Capture category navigation and anchor boundaries.

        :param tag: HTML tag as str. Example: "a".
        :param attrs: HTML attributes. Example: [("href", "?category=design")].
        :return: None. Example: anchor capture started.
        :raises AssertionError: For duplicate category navigation containers.
        :raises NotImplementedError: Until BPE implements this skeleton.
        """
        raise NotImplementedError

    def handle_data(self, data: str) -> None:
        """Capture the visible text of an active category anchor.

        :param data: HTML text as str. Example: "Design".
        :return: None. Example: label fragment captured.
        :raises NotImplementedError: Until BPE implements this skeleton.
        """
        raise NotImplementedError

    def handle_endtag(self, tag: str) -> None:
        """Finish captured anchors and category navigation.

        :param tag: HTML tag as str. Example: "a".
        :return: None. Example: completed Design anchor.
        :raises NotImplementedError: Until BPE implements this skeleton.
        """
        raise NotImplementedError

    def snapshot(self) -> tuple[CategoryAnchor, ...]:
        """Return captured anchors in document order.

        :return: Immutable anchors. Example: (CategoryAnchor("Design",
            "?category=design", "experts-category-design", "page"),).
        :raises AssertionError: If category navigation is missing or malformed.
        :raises NotImplementedError: Until BPE implements this skeleton.
        """
        raise NotImplementedError


def category_anchors(html: str) -> tuple[CategoryAnchor, ...]:
    """Extract category anchors from real rendered HTML.

    :param html: Response HTML as str. Example: response.content.decode().
    :return: Immutable anchor snapshot in DOM order. Example: five anchors.
    :raises TypeError: If html is not str.
    :raises AssertionError: If category navigation is absent or malformed.
    :raises NotImplementedError: Until BPE implements this skeleton.
    """
    raise NotImplementedError
