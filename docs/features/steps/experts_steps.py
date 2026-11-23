"""Experts domain bindings using the real Django-client acceptance lifecycle."""

from __future__ import annotations

from behave import then

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


@then(
    "score sources are Released playbooks 5000, PIP contributions 1600, Consumption 1200 and Learning 400"
)
def public_score_sources(context: Context) -> None:
    """Check the four exact source labels and values in the real response.

    :param context: Actual AT response context. Example: context.response.
    :return: None. Example: None after shared source helper succeeds.
    :raises AssertionError: If any source label/value is missing or duplicated.
    """
    raise NotImplementedError()


@then("the source rows sum to the displayed total 8200")
def public_score_source_sum(context: Context) -> None:
    """Reconcile source tbody values with expert-karma-total.

    :param context: Actual AT response context. Example: context.response.
    :return: None. Example: None for sum=8200 and formatted total 8,200.
    :raises AssertionError: If source sum and displayed total disagree.
    """
    raise NotImplementedError()


@then(
    "category subtotals Design 7200 and Development 1000 are not mislabeled as source rows"
)
def public_score_category_separation(context: Context) -> None:
    """Check category values reside only in the independent category section.

    :param context: Actual AT response context. Example: context.response.
    :return: None. Example: None for the two correctly classified categories.
    :raises AssertionError: If category/source sections overlap or values differ.
    """
    raise NotImplementedError()
