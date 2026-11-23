"""Semantic real-response HTML helpers shared across Experts acceptance tests."""

from __future__ import annotations

from django.http import HttpResponse

from collections.abc import Iterator
from django.test.html import Element, parse_html


def find_by_test_id(html: str | bytes, test_id: str) -> Element:
    """Find exactly one matching element, including a matching parsed root.

    :param html: Actual response HTML. Example: response.content.
    :param test_id: Exact stable selector value. Example: "experts-leaderboard".
    :return: Matching Django Element. Example: the ranked section element.
    :raises AssertionError: If zero or multiple elements match.
    :raises ValueError: For blank selector or malformed input type.
    """
    raise NotImplementedError()


def element_text(element: Element) -> str:
    """Collect descendant text in DOM order and normalize whitespace.

    :param element: Parsed element. Example: a contributor card.
    :return: Normalized visible textual content. Example: "Maria Rodriguez 8,200".
    :raises ValueError: For an invalid element.
    """
    raise NotImplementedError()


def _walk_elements(root: Element) -> Iterator[Element]:
    """Traverse root and descendant Elements in document order.

    :param root: Parsed document or sole top-level element. Example: an article.
    :return: Iterator including root. Example: iterated article then children.
    :raises ValueError: For a non-Element root.
    """
    raise NotImplementedError()


def _parse_root(html: str | bytes) -> Element:
    """Decode actual HTML and use Django's existing semantic parser.

    :param html: Actual HTML content. Example: response.content.
    :return: Parsed root. Example: an Element named "section".
    :raises ValueError: For unsupported type or invalid decoding.
    """
    raise NotImplementedError()


def _text_fragments(element: Element) -> Iterator[str]:
    """Yield text children recursively without reordering nested content.

    :param element: Parsed element. Example: a score span.
    :return: Ordered string fragments. Example: iterated "8,200".
    :raises ValueError: For a non-Element input.
    """
    raise NotImplementedError()


def assert_no_expert_cards(response: HttpResponse) -> None:
    """Assert a successful leaderboard has no contributor cards.

    :param response: Real Django response. Example: client.get("/experts/?category=other").
    :return: None when HTTP 200 and zero experts-card-* nodes are present.
    :raises AssertionError: If status, leaderboard or card absence differs.
    """
    raise NotImplementedError()


def assert_other_empty_message(response: HttpResponse) -> None:
    """Assert exact Other explanation and current category.

    :param response: Real Django response. Example: client.get("/experts/?category=other").
    :return: None when experts-empty text is exact and Other is current.
    :raises AssertionError: If status, element text or aria-current differs.
    """
    raise NotImplementedError()
