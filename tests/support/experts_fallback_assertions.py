"""Rendered contract shared by the category fallback certifications."""

from __future__ import annotations

from http import HTTPStatus

from django.http import HttpResponse

from tests.support.experts_category_html import category_anchors
from tests.support.experts_html import _walk_elements, element_text, find_by_test_id

_EXPECTED_CATEGORIES = (
    ("Product", None),
    ("Development", "page"),
    ("Research", None),
    ("Design", None),
    ("Other", None),
)
_EXPECTED_RANKING = (
    ("experts-card-mchen", "Mike Chen", "12,450", "Development"),
    ("experts-card-jlee", "Jordan Lee", "6,100", "Development"),
)


def assert_development_fallback(response: HttpResponse) -> None:
    """Assert the real rendered fallback result without reparsing query input.

    :param response: Actual production response. Example: client.get("/experts/?category=unrecognized").
    :return: None. Example: successful assertions return None.
    :raises AssertionError: If status, current category, cards, totals or error state differ.
    """
    assert response.status_code == HTTPStatus.OK
    html = response.content.decode(response.charset)
    anchors = category_anchors(html)
    assert tuple((anchor.label, anchor.aria_current) for anchor in anchors) == (
        _EXPECTED_CATEGORIES
    )

    leaderboard = find_by_test_id(html, "experts-leaderboard")
    ranking = []
    for card in _walk_elements(leaderboard):
        if card.name != "article":
            continue
        card_html = str(card)
        ranking.append(
            (
                dict(card.attributes).get("data-testid"),
                element_text(find_by_test_id(card_html, "expert-card-name")),
                element_text(find_by_test_id(card_html, "expert-card-karma")),
                element_text(find_by_test_id(card_html, "expert-card-category")),
            )
        )
    assert tuple(ranking) == _EXPECTED_RANKING
