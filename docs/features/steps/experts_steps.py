"""Experts domain bindings using the real Django-client acceptance lifecycle."""

from __future__ import annotations

from behave import given, then, when
from behave.runner import Context


@given("the CEDAR-RFP-01 baseline dataset")
def cedar_baseline_dataset(context: Context) -> None:
    """Import real baseline rows into the Behave-owned test DB.

    :param context: Transactional AT context. Example: context.test.client.
    :return: None. Example: None.
    :raises ValueError: If isolation or oracle validation fails.
    """
    raise NotImplementedError()


@when('Elena opens "{path}"')
def elena_opens_experts(context: Context, path: str) -> None:
    """Request the local production route using the real client.

    :param context: Prepared AT context. Example: context.client.
    :param path: Local absolute path. Example: "/experts/?category=design".
    :return: None. Example: None.
    :raises ValueError: For a nonlocal path.
    """
    raise NotImplementedError()


@then("the ranked usernames are:")
def ranked_usernames_match_table(context: Context) -> None:
    """Compare actual ordered cards and live totals/subtotals with the table.

    :param context: Response and expected Gherkin table. Example: five rows.
    :return: None. Example: None.
    :raises AssertionError: For any identity, ordering or arithmetic mismatch.
    """
    raise NotImplementedError()


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
    raise NotImplementedError()


@when("Elena selects Development")
def elena_selects_development(context: Context) -> None:
    """Follow the rendered Development link through the real Django client.

    :param context: Real Design response/client. Example: context.response.
    :return: None. Example: None.
    :raises AssertionError: If the expected accessible link is missing.
    """
    raise NotImplementedError()


@then("Mike Chen 12450 precedes Jordan Lee 6100")
def development_order_matches_contract(context: Context) -> None:
    """Check rendered identities, scores and relative card order.

    :param context: Actual Development response. Example: HTTP 200.
    :return: None. Example: None.
    :raises AssertionError: If either score or ordering differs.
    """
    raise NotImplementedError()


@then("Maria is absent because her primary playbook category is Design")
def maria_secondary_category_is_excluded(context: Context) -> None:
    """Assert Maria's real primary projection and Development card absence.

    :param context: Imported IDs and actual response. Example: Development HTML.
    :return: None. Example: None.
    :raises AssertionError: If Maria qualifies for the wrong leaderboard.
    """
    raise NotImplementedError()
