"""Acceptance bindings for expert profiles and shared display phrases."""

from __future__ import annotations

from behave import given, then, when
from behave.runner import Context

from tests.support.experts_html import element_text, find_by_test_id


@given("Maria is authenticated")
def maria_is_authenticated(context: Context) -> None:
    """Authenticate the real Cedar Maria account with the existing test client.

    :param context: Behave context; example: contains cedar_dataset from S03.
    :return: None; example: client owns Maria's authenticated session.
    :raises AssertionError: If Maria is missing or authentication fails.
    """
    raise NotImplementedError()


@when('she opens "{path}"')
@when("she opens her own profile")
def maria_opens_profile_path(
    context: Context, path: str = "/auth/user/profile/"
) -> None:
    """Request a local route and retain the real response.

    :param context: Prepared authenticated context; example: Cedar Maria.
    :param path: Absolute local path; example: "/auth/user/profile/".
    :return: None; example: context.response holds the actual GET response.
    :raises ValueError: If path is external or malformed; example: "//host".
    """
    raise NotImplementedError()


@then('"{test_id}" is present')
def profile_element_is_present(context: Context, test_id: str) -> None:
    """Assert the named stable hook exists in the real rendered response.

    :param context: Context with actual response; example: profile HTTP 200.
    :param test_id: Allowed profile hook; example: "profile-karma-card".
    :return: None; example: Django response assertion passes.
    :raises AssertionError: If the response or hook is absent.
    """
    raise NotImplementedError()


@then('"{test_id}" reads "{value}"')
def profile_element_reads(context: Context, test_id: str, value: str) -> None:
    """Assert an expert profile value in both the rendered HTML and its context.

    :param context: Real Django-client response; example: Maria's public detail.
    :param test_id: Stable display hook; example: "expert-karma-total".
    :param value: Required display text; example: "8,200".
    :return: None when the displayed value and projection match.
    :raises NotImplementedError: For a pending profile hook.
    :raises AssertionError: If the public response or value differs.
    """
    if test_id != "expert-karma-total":
        raise NotImplementedError()
    response = context.response
    assert response.status_code == 200
    assert response.resolver_match.url_name == "expert_detail"
    person = response.context["person"]
    assert person["formatted_karma"] == value
    assert f"{person['total_karma']:,}" == value
    assert element_text(find_by_test_id(response.content, test_id)) == value


@then('the primary playbook category is "{category}"')
def profile_primary_category_is(context: Context, category: str) -> None:
    """Assert the expert's projected category and rendered category badge.

    :param context: Actual profile response; example: Maria's public detail.
    :param category: Required category; example: "Design".
    :return: None when the public badge and projection match.
    :raises NotImplementedError: For the pending own-profile route.
    :raises AssertionError: If the public response or category differs.
    """
    response = context.response
    if response.resolver_match.url_name != "expert_detail":
        raise NotImplementedError()
    assert response.status_code == 200
    assert response.context["person"]["primary_category"] == category
    badge = find_by_test_id(response.content, "expert-primary-category")
    assert element_text(badge) == category


@then("existing account/profile controls remain available")
def existing_profile_controls_remain(context: Context) -> None:
    """Verify retained account links, token controls and existing sections.

    :param context: Real authenticated response; example: Maria profile.
    :return: None; example: all existing controls and destinations remain.
    :raises AssertionError: If any account function was replaced or removed.
    """
    raise NotImplementedError()


@then("the source rows show {released:d}, {pip:d}, {consumption:d} and {learning:d}")
def source_rows_show(
    context: Context, released: int, pip: int, consumption: int, learning: int
) -> None:
    """Check the real response's four rows against expected and persisted awards.

    :param context: Real HTTP/Cedar context. Example: context.cedar_dataset.
    :param released: Release subtotal. Example: 5000.
    :param pip: Combined major/minor subtotal across categories. Example: 1600.
    :param consumption: Author-consumption subtotal. Example: 1200.
    :param learning: Learner subtotal. Example: 400.
    :return: None. Example: four exact source rows match ORM and HTML.
    :raises AssertionError: If HTTP, ledger or rendered source rows differ.
    """
    raise NotImplementedError()


@then("their sum equals the displayed total {total:d}")
def source_sum_matches_total(context: Context, total: int) -> None:
    """Reconcile source body, footer, card and persisted total.

    :param context: Context retaining actual profile HTTP. Example: context.response.
    :param total: Required total. Example: 8200.
    :return: None. Example: every independently read total equals 8200.
    :raises AssertionError: If any total or source arithmetic differs.
    """
    raise NotImplementedError()
