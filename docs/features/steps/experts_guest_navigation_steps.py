from __future__ import annotations

"""S49-only bindings; common Cedar/Bob phrases retain their existing owners."""
from behave import then, when
from behave.runner import Context


@when("he follows Experts from the app sidebar")
def guest_follows_experts_from_sidebar(context: Context) -> None:
    """Follow the rendered public shell href using the real Django client.

    :param context: Prepared AT Context. Example: context.client is anonymous.
    :return: None. Example: context.response contains GET /experts/ response.
    :raises AssertionError: Public shell or unique local Experts link is wrong.
    """
    raise NotImplementedError()


@then('he reaches "{path}" without a login redirect')
def guest_reaches_public_path(context: Context, path: str) -> None:
    """Assert the real response reaches the declared public destination.

    :param context: AT Context. Example: response from rendered sidebar href.
    :param path: Expected local path str. Example: "/experts/".
    :return: None. Example: HTTP 200 at /experts/ with no Location header.
    :raises ValueError: Expected path is not an absolute local path.
    :raises AssertionError: Response redirects, authenticates or lands elsewhere.
    """
    raise NotImplementedError()


@then("the guest banner explains sign-in and registration")
def guest_banner_explains_authentication(context: Context) -> None:
    """Apply the shared banner assertion to the real public response.

    :param context: AT Context. Example: context.response contains Experts HTML.
    :return: None. Example: one explanatory banner with valid auth actions.
    :raises AssertionError: Explanation or Sign In/Register action is missing.
    """
    raise NotImplementedError()
