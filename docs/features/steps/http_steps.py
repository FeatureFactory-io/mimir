"""Reusable Django-client AT primitives; no browser imports or domain mocks."""

import logging

from behave import given, then, when

logger = logging.getLogger(__name__)


@given("an anonymous AT visitor")
def anonymous_visitor(context) -> None:
    """Start the request without authenticated cookies.

    :param context: Prepared transactional Django-client context.
    :return: None.
    """
    context.client.logout()


@when('the AT visitor requests "{path}"')
def request_path(context, path: str) -> None:
    """Request a local application path with the real Django client.

    :param context: Prepared AT context.
    :param path: Absolute local URL path, not an external URL.
    :return: None.
    :raises ValueError: For external or malformed paths.
    """
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("AT requests require a local absolute path")
    context.response = context.client.get(path)
    logger.info(
        "AT request_path | exit | path=%s status=%s", path, context.response.status_code
    )


@then("the AT response status is {status:d}")
def response_status(context, status: int) -> None:
    """Check the actual response status, without simulating a page.

    :param context: Context containing the real HTTP response.
    :param status: Required HTTP response status.
    :return: None.
    :raises AssertionError: When the actual status differs.
    """
    assert context.response.status_code == status
