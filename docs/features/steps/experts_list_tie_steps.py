"""Only S08-owned Django-client acceptance phrases."""

from __future__ import annotations

from http import HTTPStatus

from behave import given, then
from behave.runner import Context

from methodology.models import KarmaAward
from tests.support.experts_html import _walk_elements, element_text, find_by_test_id
from tests.support.experts_tie_data import apply_cedar_tie03

_ALINA_USERNAME = "apark"
_CARD_PREFIX = "experts-card-"
_DESIGN_ORDER = (_ALINA_USERNAME, "sreed", "mrodriguez", "pnair", "dortiz")
_TIED_DISPLAY_TOTAL = "15,400"


@given("the isolated TIE03 variant with Alina Park and Sofia Reed at 15400")
def apply_tie03_variant(context: Context) -> None:
    """Extend the shared baseline in the current acceptance transaction.

    :param context: Real AT context. Example: context.cedar_dataset from S03.
    :return: None. Example: context.cedar_dataset also contains "apark".
    :raises ValueError: If the baseline cannot support the isolated variant.
    :raises AssertionError: If import changes existing awards or sign-in fails.
    """
    baseline_ledger = list(KarmaAward.objects.order_by("pk").values())
    variant = apply_cedar_tie03(context.cedar_dataset)
    variant_ledger = list(KarmaAward.objects.order_by("pk").values())
    alina_id = variant.user_ids[_ALINA_USERNAME]
    assert [row for row in variant_ledger if row["recipient_id"] != alina_id] == (
        baseline_ledger
    ), "TIE03 changed the existing Cedar awards."
    context.cedar_dataset = variant
    context.execute_steps("Given Elena is authenticated")
    context.tie03_ledger = variant_ledger


@then('"{first_username}" precedes "{second_username}"')
def assert_expert_precedes(
    context: Context, first_username: str, second_username: str
) -> None:
    """Assert both cards occur in the actual leaderboard in strict DOM order.

    :param context: Context retaining real response. Example: context.response.
    :param first_username: Earlier contributor. Example: "apark".
    :param second_username: Later contributor. Example: "sreed".
    :return: None. Example: apark card occurs before sreed card.
    :raises AssertionError: If response, card order, tie totals or ledger differ.
    :raises ValueError: If usernames are empty or identical.
    """
    if (
        not first_username.strip()
        or not second_username.strip()
        or first_username == second_username
    ):
        raise ValueError("Two distinct, nonblank expert usernames are required.")

    response = context.response
    assert response.status_code == HTTPStatus.OK, "The Design leaderboard did not load."
    category = find_by_test_id(response.content, "experts-category-design")
    assert ("aria-current", "page") in category.attributes
    leaderboard = find_by_test_id(response.content, "experts-leaderboard")
    usernames = tuple(
        value.removeprefix(_CARD_PREFIX)
        for node in _walk_elements(leaderboard)
        if node.name == "article"
        for name, value in node.attributes
        if name == "data-testid" and value.startswith(_CARD_PREFIX)
    )
    assert usernames == _DESIGN_ORDER, f"Unexpected Design ranking: {usernames!r}."
    assert usernames[:2] == (first_username, second_username)
    for username in (first_username, second_username):
        card = find_by_test_id(str(leaderboard), f"{_CARD_PREFIX}{username}")
        total = find_by_test_id(str(card), "expert-card-karma")
        assert element_text(total) == _TIED_DISPLAY_TOTAL
    assert context.tie03_ledger == list(KarmaAward.objects.order_by("pk").values()), (
        "Opening the Design leaderboard changed its award ledger."
    )
