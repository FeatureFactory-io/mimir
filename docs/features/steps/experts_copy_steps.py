from __future__ import annotations

"Django-client copy receipt AT; actual clipboard proof is Playwright-owned."
from behave import given, then, when
from behave.runner import Context


@when("she successfully copies Mike's public released activity 6203")
def reports_successful_activity_copy(context: Context) -> None:
    """Exercise rendered prompt and real successful-action receipt boundary.

    :param context: Real Django-client AT context. Example: Maria session.
    :return: None with actual GET and receipt responses.
    :raises AssertionError: If authorized prompt or receipt is unavailable.
    """
    raise NotImplementedError()


@then("the clipboard receives the actual activity prompt")
def actual_activity_prompt_is_the_copy_payload(context: Context) -> None:
    """Check actual server-built copy payload; browser gate proves the clipboard.

    :param context: AT context containing the real rendered prompt. Example: activity 6203.
    :return: None after expected prompt equality; no browser certification is implied.
    :raises AssertionError: If rendered payload differs from CopyPromptService output.
    """
    raise NotImplementedError()


@then("Maria's total becomes 8205 and Mike's becomes 12455")
def copy_pair_totals_match_cedar(context: Context) -> None:
    """Check real ledger projections against EV01.

    :param context: AT context with real Cedar actors. Example: Maria and Mike.
    :return: None after both numeric total assertions.
    :raises AssertionError: If either projected total differs.
    """
    raise NotImplementedError()


@then("both awards belong to Development")
def copy_pair_category_is_development(context: Context) -> None:
    """Check the two new immutable category snapshots.

    :param context: AT context carrying the receipt identity. Example: EV01 action UUID.
    :return: None after exact two-recipient Development assertions.
    :raises AssertionError: If award attribution differs.
    """
    raise NotImplementedError()
