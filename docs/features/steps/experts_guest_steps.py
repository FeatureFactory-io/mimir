from __future__ import annotations

"""S07-owned AT bindings; common baseline and open-URL belong to S03."""
from behave import given, then
from behave.runner import Context


@given("Bob is an anonymous visitor")
def bob_is_anonymous(context: Context) -> None:
    """Reuse the working anonymous AT primitive without creating Bob.

    :param context: Real AT Context. Example: context.client is available.
    :return: None. Example: authenticated cookies are removed.
    :raises RuntimeError: The Django-client harness was not initialized.
    """
    raise NotImplementedError()


@then("the same five Design contributors are visible")
def same_design_contributors(context: Context) -> None:
    """Apply the shared fixed-ranking assertion to the real response.

    :param context: AT Context. Example: context.response.status_code == 200.
    :return: None. Example: all five Cedar cards are correctly ordered.
    :raises AssertionError: Response status or public ranking differs.
    """
    raise NotImplementedError()


@then("a guest banner offers Sign In and Register")
def guest_banner_offers_authentication(context: Context) -> None:
    """Apply the shared banner assertion to real rendered HTML.

    :param context: AT Context. Example: context.response contains the list.
    :return: None. Example: two correctly named auth anchors are present.
    :raises AssertionError: Banner or destination fails the contract.
    """
    raise NotImplementedError()


@then("no own-profile Karma card or API token is present")
def private_account_controls_are_absent(context: Context) -> None:
    """Apply the shared public-page account-boundary assertion.

    :param context: AT Context. Example: anonymous Design response.
    :return: None. Example: no own-profile or token control appears.
    :raises AssertionError: Private account material appears in HTML.
    """
    raise NotImplementedError()
