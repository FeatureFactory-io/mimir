from __future__ import annotations

"""Test-only extraction of Maria's rendered View profile destination."""
from html.parser import HTMLParser


class MariaProfileLinkParser(HTMLParser):
    """Collect anchors carrying Maria's stable View profile test id."""

    hrefs: list[str | None]

    def __init__(self) -> None:
        """Initialize an independent parser.

        :return: None. Example: parser.hrefs is initially empty.
        :raises NotImplementedError: Until the approved slice is implemented.
        """
        raise NotImplementedError()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect only Maria's matching anchor href.

        :param tag: HTML tag. Example: "a".
        :param attrs: Parsed attributes. Example: [("href", "/experts/mrodriguez/")].
        :return: None. Example: one matching href retained.
        :raises NotImplementedError: Until the approved slice is implemented.
        """
        raise NotImplementedError()


def extract_maria_profile_href(html: str) -> str:
    """Require exactly one Maria anchor with the production local destination.

    :param html: Real rendered response HTML. Example: Design leaderboard HTML.
    :return: Destination str. Example: "/experts/mrodriguez/".
    :raises AssertionError: Missing/duplicate anchor, missing or incorrect href.
    :raises NotImplementedError: Until the approved slice is implemented.
    """
    raise NotImplementedError()
