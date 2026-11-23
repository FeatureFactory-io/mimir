from __future__ import annotations

from behave import then
from behave.runner import Context
from tests.support.experts_html import (
    assert_no_expert_cards,
    assert_other_empty_message,
)


@then("no contributor cards are present")
def no_contributor_cards(context: Context) -> None:
    """Check the actual retained response for absent contributor cards.

    :param context: Prepared AT context. Example: context.response from production GET.
    :return: None after successful HTTP and zero-card assertions.
    :raises AssertionError: If the response or leaderboard violates the contract.
    """
    raise NotImplementedError()


@then('she sees "No experts in Other yet — release a playbook to be the first"')
def other_empty_message(context: Context) -> None:
    """Check the exact Other explanation without a generic text binding.

    :param context: Prepared AT context. Example: context.response from Other GET.
    :return: None after exact message and Other-current assertions.
    :raises AssertionError: If actual rendered text or selected category differs.
    """
    raise NotImplementedError()
