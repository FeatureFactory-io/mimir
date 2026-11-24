"""Experts domain bindings using the real Django-client acceptance lifecycle."""

from __future__ import annotations

import logging
from urllib.parse import unquote, urlsplit

from behave import given, then, when
from behave.runner import Context
from django.http import HttpResponse
from django.test.html import Element

from methodology.services.expert_text import format_karma
from methodology.services.experts_service import ExpertsService
from tests.support.experts_data import load_cedar_baseline
from tests.support.experts_html import (
    _walk_elements,
    assert_karma_source_rows,
    element_text,
    find_by_test_id,
)

logger = logging.getLogger(__name__)
_CARD_PREFIX = "experts-card-"
_DEVELOPMENT_TAB = "experts-category-development"
_DEVELOPMENT_PATH = "/experts/?category=development"
_PUBLIC_SCORE_TOTAL = 8200
_PUBLIC_SCORE_SOURCES = (
    ("Released playbooks", 5000),
    ("PIP contributions", 1600),
    ("Consumption", 1200),
    ("Learning", 400),
)
_PUBLIC_SCORE_CATEGORIES = (("Design", 7200), ("Development", 1000))


@given("the CEDAR-RFP-01 baseline dataset")
@given("the isolated CEDAR-RFP-01 baseline is restored")
def cedar_baseline_dataset(context: Context) -> None:
    """Import real baseline rows into the Behave-owned test DB.

    :param context: Transactional AT context. Example: context.test.client.
    :return: None. Example: None.
    :raises ValueError: If isolation or oracle validation fails.
    """
    context.cedar_dataset = load_cedar_baseline()


@when('Elena opens "{path}"')
@when('he opens "{path}"')
@when('Bob opens "{path}"')
def elena_opens_experts(context: Context, path: str) -> None:
    """Request a local production route with the client's existing session.

    :param context: Prepared AT context. Example: context.client.
    :param path: Local absolute path. Example: "/experts/?category=design".
    :return: None. Example: None.
    :raises ValueError: For a nonlocal path.
    """
    local_path = _validated_local_path(path)
    context.response = context.client.get(path)
    logger.info(
        "Experts AT GET | exit | path=%s status=%s",
        local_path,
        context.response.status_code,
    )


@then("the ranked usernames are:")
def ranked_usernames_match_table(context: Context) -> None:
    """Compare actual ordered cards and live totals/subtotals with the table.

    :param context: Response and expected Gherkin table. Example: five rows.
    :return: None. Example: None.
    :raises AssertionError: For any identity, ordering or arithmetic mismatch.
    """
    assert context.table.headings == ["username", "total", "design_subtotal"]
    expected = [
        (row["username"], int(row["total"]), int(row["design_subtotal"]))
        for row in context.table
    ]
    response = context.response
    cards = _leaderboard_cards(response)
    assert [username for username, _ in cards] == [
        username for username, _, _ in expected
    ]
    rendered = [(username, *_card_points(card)) for username, card in cards]
    assert rendered == expected
    for rank, (_, card) in enumerate(cards, start=1):
        rank_display = find_by_test_id(str(card), "expert-card-rank")
        assert element_text(rank_display) == str(rank)
        assert dict(rank_display.attributes)["aria-label"] == f"Rank {rank}"
    assert response.context["selected_category"] == "design"
    assert [
        (person["username"], person["total_points"], person["category_subtotal"])
        for person in response.context["people"]
    ] == expected


@then('sixth eligible Design contributor "{username}" is absent')
@then('Development contributor "{username}" is absent')
@then('zero-Karma contributor "{username}" is absent')
def contributor_is_absent(context: Context, username: str) -> None:
    """Check actual rendered card absence without recomputing ranking.

    :param context: Real response context. Example: Design HTML.
    :param username: Excluded contributor. Example: "tmartin".
    :return: None. Example: None.
    :raises AssertionError: If that contributor card exists.
    """
    assert username not in dict(
        _leaderboard_cards(context.response)
    ), f"{username} has a ranked card."


@when("Elena selects Development")
def elena_selects_development(context: Context) -> None:
    """Follow the rendered Development link through the real Django client.

    :param context: Real Design response/client. Example: context.response.
    :return: None. Example: None.
    :raises AssertionError: If the expected accessible link is missing.
    """
    assert context.response.status_code == 200
    tabs = find_by_test_id(context.response.content, "experts-category-tabs")
    link = find_by_test_id(str(tabs), _DEVELOPMENT_TAB)
    assert link.name == "a" and element_text(link) == "Development"
    href = dict(link.attributes).get("href")
    assert href == _DEVELOPMENT_PATH
    elena_opens_experts(context, href)
    assert context.response.status_code == 200
    current = find_by_test_id(context.response.content, _DEVELOPMENT_TAB)
    assert dict(current.attributes).get("aria-current") == "page"


@then("Mike Chen 12450 precedes Jordan Lee 6100")
def development_order_matches_contract(context: Context) -> None:
    """Check rendered identities, scores and relative card order.

    :param context: Actual Development response. Example: HTTP 200.
    :return: None. Example: None.
    :raises AssertionError: If either score or ordering differs.
    """
    cards = dict(_leaderboard_cards(context.response))
    usernames = tuple(cards)
    for username, name, points in (
        ("mchen", "Mike Chen", 12450),
        ("jlee", "Jordan Lee", 6100),
    ):
        assert username in cards, f"Missing ranked card for {username}"
        assert name in element_text(cards[username])
        assert _card_points(cards[username])[0] == points
    assert usernames.index("mchen") < usernames.index("jlee")


@then("Maria is absent because her primary playbook category is Design")
def maria_secondary_category_is_excluded(context: Context) -> None:
    """Assert Maria's real primary projection and Development card absence.

    :param context: Imported IDs and actual response. Example: Development HTML.
    :return: None. Example: None.
    :raises AssertionError: If Maria qualifies for the wrong leaderboard.
    """
    assert context.response.context["selected_category"] == "development"
    maria_id = context.cedar_dataset.user_ids["mrodriguez"]
    maria = ExpertsService().project_user(maria_id)
    assert maria.primary_category == "design"
    assert dict(maria.category_points).get("development", 0) > 0
    contributor_is_absent(context, maria.username)


def _validated_local_path(path: str) -> str:
    """Return the request path for logging after checking it is safe and local."""
    if (
        not isinstance(path, str)
        or not path.startswith("/")
        or "#" in path
        or "\\" in path
        or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in path)
    ):
        raise ValueError("Experts AT requests require a local absolute URL path.")
    parts = urlsplit(path)
    decoded_path = unquote(parts.path)
    if (
        parts.scheme
        or parts.netloc
        or path.startswith("//")
        or decoded_path.startswith("//")
        or "\\" in decoded_path
        or any(ord(char) < 32 or ord(char) == 127 for char in decoded_path)
    ):
        raise ValueError("Experts AT requests require a local absolute URL path.")
    return parts.path


def _leaderboard_cards(response: HttpResponse) -> tuple[tuple[str, Element], ...]:
    """Read each rendered card's username in actual leaderboard order."""
    assert response.status_code == 200
    leaderboard = find_by_test_id(response.content, "experts-leaderboard")
    cards = []
    for child in leaderboard.children:
        if not isinstance(child, Element) or child.name != "article":
            continue
        test_id = dict(child.attributes).get("data-testid", "")
        assert test_id.startswith(_CARD_PREFIX) and test_id != _CARD_PREFIX
        cards.append((test_id.removeprefix(_CARD_PREFIX), child))
    assert len({username for username, _ in cards}) == len(
        cards
    ), "Duplicate ranked card."
    return tuple(cards)


def _card_points(card: Element) -> tuple[int, int]:
    """Read raw total and subtotal and check the displayed Karma value."""
    attributes = dict(card.attributes)
    total = int(attributes["data-total-points"])
    subtotal = int(attributes["data-category-points"])
    karma = find_by_test_id(str(card), "expert-card-karma")
    assert element_text(karma) == f"{total:,}"
    return total, subtotal


@then(
    "score sources are Released playbooks 5000, PIP contributions 1600, Consumption 1200 and Learning 400"
)
def public_score_sources(context: Context) -> None:
    """Check the four exact source labels and values in the real response.

    :param context: Actual AT response context. Example: context.response.
    :return: None. Example: None after shared source helper succeeds.
    :raises AssertionError: If any source label/value is missing or duplicated.
    """
    response = context.response
    assert response.status_code == 200
    assert response.context["person"]["username"] == "mrodriguez"
    assert_karma_source_rows(
        response.content.decode(response.charset),
        dict(_PUBLIC_SCORE_SOURCES),
        "expert-karma-total",
        _PUBLIC_SCORE_TOTAL,
    )
    assert response.context["person"]["source_rows"] == tuple(
        {"label": label, "points": format_karma(points)}
        for label, points in _PUBLIC_SCORE_SOURCES
    )


@then("the source rows sum to the displayed total 8200")
def public_score_source_sum(context: Context) -> None:
    """Reconcile source tbody values with expert-karma-total.

    :param context: Actual AT response context. Example: context.response.
    :return: None. Example: None for sum=8200 and formatted total 8,200.
    :raises AssertionError: If source sum and displayed total disagree.
    """
    person = context.response.context["person"]
    assert sum(points for _, points in _PUBLIC_SCORE_SOURCES) == _PUBLIC_SCORE_TOTAL
    assert person["total_karma"] == _PUBLIC_SCORE_TOTAL
    assert person["formatted_karma"] == format_karma(_PUBLIC_SCORE_TOTAL) == "8,200"
    assert_karma_source_rows(
        context.response.content.decode(context.response.charset),
        dict(_PUBLIC_SCORE_SOURCES),
        "expert-karma-total",
        person["total_karma"],
    )


@then(
    "category subtotals Design 7200 and Development 1000 are not mislabeled as source rows"
)
def public_score_category_separation(context: Context) -> None:
    """Check category values reside only in the independent category section.

    :param context: Actual AT response context. Example: context.response.
    :return: None. Example: None for the two correctly classified categories.
    :raises AssertionError: If category/source sections overlap or values differ.
    """
    response = context.response
    section = find_by_test_id(response.content, "karma-category-breakdown")
    assert section.name == "dl"
    actual = [(node.name, element_text(node)) for node in _walk_elements(section)]
    assert actual[1:] == [
        item
        for label, points in _PUBLIC_SCORE_CATEGORIES
        for item in (("dt", label), ("dd", format_karma(points)))
    ]
    table = find_by_test_id(response.content, "karma-source-breakdown")
    body = next(
        node
        for node in table.children
        if isinstance(node, Element) and node.name == "tbody"
    )
    assert all(label not in element_text(body) for label, _ in _PUBLIC_SCORE_CATEGORIES)
    assert sum(points for _, points in _PUBLIC_SCORE_CATEGORIES) == _PUBLIC_SCORE_TOTAL
    assert response.context["person"]["category_rows"] == tuple(
        {"label": label, "points": format_karma(points)}
        for label, points in _PUBLIC_SCORE_CATEGORIES
    )
