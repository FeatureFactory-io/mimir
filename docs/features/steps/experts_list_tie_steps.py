from __future__ import annotations

"""Only S08-owned Django-client acceptance phrases."""
from behave import given, then
from behave.runner import Context


@given("the isolated TIE03 variant with Alina Park and Sofia Reed at 15400")
def apply_tie03_variant(context: Context) -> None:
    """Extend the shared baseline in the current acceptance transaction.

    :param context: Real AT context. Example: context.cedar_dataset from S03.
    :return: None. Example: context.cedar_dataset also contains "apark".
    :raises ValueError: If the baseline cannot support the isolated variant.
    :raises NotImplementedError: Until the fixture binding is implemented.
    """
    raise NotImplementedError()


@then('"{first_username}" precedes "{second_username}"')
def assert_expert_precedes(
    context: Context, first_username: str, second_username: str
) -> None:
    """Assert both cards occur in the actual leaderboard in strict DOM order.

    :param context: Context retaining real response. Example: context.response.
    :param first_username: Earlier contributor. Example: "apark".
    :param second_username: Later contributor. Example: "sreed".
    :return: None. Example: apark card occurs before sreed card.
    :raises AssertionError: If status, either card or their strict order is wrong.
    :raises ValueError: If usernames are empty or identical.
    :raises NotImplementedError: Until parsed-HTML acceptance is implemented.
    """
    raise NotImplementedError()
