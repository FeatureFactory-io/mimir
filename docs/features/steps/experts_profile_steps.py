"""Acceptance bindings for expert profiles and shared display phrases."""

from __future__ import annotations

import logging

from behave import given, then, when
from behave.runner import Context
from django.urls import reverse

from tests.support.experts_data import CEDAR_PASSWORD
from tests.support.experts_html import element_text, find_by_test_id

logger = logging.getLogger(__name__)
_MARIA_USERNAME = "mrodriguez"


@given("Maria is authenticated")
def maria_is_authenticated(context: Context) -> None:
    """Authenticate the real Cedar Maria account with the existing test client.

    :param context: Behave context; example: contains cedar_dataset from S03.
    :return: None; example: client owns Maria's authenticated session.
    :raises AssertionError: If Maria is missing or authentication fails.
    """
    maria = context.cedar_dataset.users_by_username.get(_MARIA_USERNAME)
    assert maria is not None, "The Cedar baseline must contain Maria."
    logger.info("Experts profile AT | sign-in entry | user_id=%s", maria.pk)
    assert context.client.login(
        username=maria.username, password=CEDAR_PASSWORD
    ), "Maria's Cedar account could not sign in."
    logger.info("Experts profile AT | sign-in exit | user_id=%s", maria.pk)


@when('she opens "{path}"')
@when("she opens her own profile")
def maria_opens_profile_path(
    context: Context, path: str = "/auth/user/profile/"
) -> None:
    """Request the existing own-profile route and retain the real response.

    :param context: Prepared authenticated context; example: Cedar Maria.
    :param path: Absolute local path; example: "/auth/user/profile/".
    :return: None; example: context.response holds the actual GET response.
    :raises ValueError: If path differs from the account profile route.
    :raises AssertionError: If the response fails or loses Maria's session.
    """
    if path != reverse("profile"):
        raise ValueError("The own-profile step requires the existing profile route.")
    response = context.client.get(path)
    logger.info(
        "Experts profile AT | GET exit | path=%s status=%s", path, response.status_code
    )
    assert response.status_code == 200, "The existing profile route did not load."
    maria = context.cedar_dataset.users_by_username[_MARIA_USERNAME]
    assert response.wsgi_request.user == maria, "The profile lost Maria's session."
    context.response = response


@then('"{test_id}" is present')
def profile_element_is_present(context: Context, test_id: str) -> None:
    """Assert the named stable hook exists in the real rendered response.

    :param context: Context with actual response; example: profile HTTP 200.
    :param test_id: Allowed profile hook; example: "profile-karma-card".
    :return: None; example: Django response assertion passes.
    :raises AssertionError: If the response or hook is absent.
    """
    assert context.response.status_code == 200
    find_by_test_id(context.response.content, test_id)


@then('"{test_id}" reads "{value}"')
def profile_element_reads(context: Context, test_id: str, value: str) -> None:
    """Assert an expert profile value in both the rendered HTML and its context.

    :param context: Real Django-client response; example: Maria's public detail.
    :param test_id: Stable display hook; example: "expert-karma-total".
    :param value: Required display text; example: "8,200".
    :return: None when the displayed value and projection match.
    :raises NotImplementedError: For a pending profile hook.
    :raises AssertionError: If the profile response or value differs.
    """
    if test_id == "expert-karma-total":
        route, context_key = "expert_detail", "person"
    elif test_id == "profile-karma-total":
        route, context_key = "profile", "contributions"
    else:
        raise NotImplementedError()
    response = context.response
    assert response.status_code == 200
    assert response.resolver_match.url_name == route
    projection = response.context[context_key]
    assert projection["formatted_karma"] == value
    assert f"{projection['total_karma']:,}" == value
    assert element_text(find_by_test_id(response.content, test_id)) == value


@then('the primary playbook category is "{category}"')
def profile_primary_category_is(context: Context, category: str) -> None:
    """Assert the expert's projected category and rendered category badge.

    :param context: Actual profile response; example: Maria's public detail.
    :param category: Required category; example: "Design".
    :return: None when the badge and projection match.
    :raises NotImplementedError: For unrecognized profile routes.
    :raises AssertionError: If the profile response or category differs.
    """
    response = context.response
    route = response.resolver_match.url_name
    if route == "expert_detail":
        context_key, test_id = "person", "expert-primary-category"
    elif route == "profile":
        context_key, test_id = "contributions", "profile-primary-category"
    else:
        raise NotImplementedError()
    assert response.status_code == 200
    assert response.context[context_key]["primary_category"] == category
    badge = find_by_test_id(response.content, test_id)
    assert element_text(badge) == category


@then("existing account/profile controls remain available")
def existing_profile_controls_remain(context: Context) -> None:
    """Verify retained account links, token controls and existing sections.

    :param context: Real authenticated response; example: Maria profile.
    :return: None; example: all existing controls and destinations remain.
    :raises AssertionError: If any account function was replaced or removed.
    """
    html = context.response.content
    edit = find_by_test_id(html, "profile-edit-btn")
    assert edit.name == "a" and ("href", reverse("profile_edit")) in edit.attributes
    field = find_by_test_id(html, "profile-token-field")
    assert field.name == "input" and ("type", "password") in field.attributes
    assert find_by_test_id(html, "profile-token-toggle").name == "button"
    assert find_by_test_id(html, "profile-token-copy").name == "button"
    form = find_by_test_id(html, "profile-token-regenerate-form")
    assert form.name == "form" and ("method", "post") in form.attributes
    assert ("action", reverse("profile_regenerate_token")) in form.attributes
    password = find_by_test_id(str(form), "profile-token-regenerate-password")
    assert ("name", "current_password") in password.attributes
    assert ("type", "password") in password.attributes
    assert "required" in dict(password.attributes)
    submit = find_by_test_id(str(form), "profile-token-regenerate-submit")
    assert submit.name == "button" and ("type", "submit") in submit.attributes
    for test_id in (
        "profile-pips-table",
        "profile-playbooks-table",
        "profile-teams-section",
    ):
        find_by_test_id(html, test_id)


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
