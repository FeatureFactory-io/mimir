from __future__ import annotations

from behave import then, when
from behave.runner import Context


@when('anonymous Bob opens "{path}"')
def anonymous_bob_opens(context: Context, path: str) -> None:
    """Log out and request the exact production path.

    :param context: Real AT context, e.g. context.client and cedar_dataset.
    :param path: Local absolute path, e.g. "/experts/mrodriguez/".
    :return: None; context.response contains actual HTTP result.
    :raises ValueError: If path is external or malformed.
    """
    raise NotImplementedError()


@then('the response omits "{value}"')
@then('it omits "{value}"')
def response_omits(context: Context, value: str) -> None:
    """Assert exact sentinel exclusion from full response markup.

    :param context: Real AT context, e.g. response status 200.
    :param value: Forbidden sentinel, e.g. "Cedar Bid Pricing".
    :return: None; stored fixture exists and sentinel is absent.
    :raises AssertionError: If fixture evidence is missing or value appears.
    """
    raise NotImplementedError()


@then('no "{test_id}" exists')
def response_has_no_test_id(context: Context, test_id: str) -> None:
    """Use S03 shared HTML parser to check an absent control.

    :param context: Real AT context, e.g. guest detail response.
    :param test_id: Forbidden hook, e.g. "profile-token-field".
    :return: None; matching element count is zero.
    :raises AssertionError: If the forbidden control exists.
    """
    raise NotImplementedError()
