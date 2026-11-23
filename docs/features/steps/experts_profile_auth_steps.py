from __future__ import annotations

"""Unique S13 assertions; shared actor/request bindings belong elsewhere."""
from behave import then
from behave.runner import Context
from tests.support.experts_html import find_by_test_id


@then("he is redirected to the login page")
def assert_own_profile_login_redirect(context: Context) -> None:
    """Check the unfollowed own-profile response's precise login handoff.

    :param context: Real AT context. Example: context.response.status_code == 302.
    :return: None. Example: None after exact Location/next assertions.
    :raises AssertionError: If profile request, redirect or next differs.
    """
    raise NotImplementedError()


@then("no own-profile Karma or account token controls are shown")
def assert_own_profile_controls_absent(context: Context) -> None:
    """Check redirect and login HTML without granting an authenticated session.

    :param context: Real Cedar AT context. Example: context.cedar_dataset.
    :return: None. Example: None after private-control absence assertions.
    :raises AssertionError: If controls, token secrets or an account appear.
    """
    raise NotImplementedError()
