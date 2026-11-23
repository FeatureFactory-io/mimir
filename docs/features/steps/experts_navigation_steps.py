from __future__ import annotations

from behave import given, then, when
from behave.runner import Context


@given("Elena is authenticated")
def elena_is_authenticated(context: Context) -> None:
    """Authenticate the real baseline Elena account.

    :param context: AT context with CedarDataset. Example: context.cedar_dataset.
    :return: None. Example: None.
    :raises AssertionError: If baseline Elena is missing.
    """
    raise NotImplementedError()


@when("she follows the Experts navigation link")
def follows_experts_navigation_link(context: Context) -> None:
    """Follow the actual rendered shell destination with the Django client.

    :param context: Authenticated AT context. Example: Elena's client.
    :return: None. Example: None.
    :raises AssertionError: If the unique local nav-experts link is missing.
    """
    raise NotImplementedError()


def _experts_navigation_href(html: str) -> str:
    """Extract and validate the single Experts sidebar destination.

    :param html: Rendered existing page. Example: HTML containing nav-experts.
    :return: Local destination. Example: "/experts/".
    :raises AssertionError: If missing, duplicated or external.
    """
    raise NotImplementedError()


@then('the URL is "{path}"')
def url_is(context: Context, path: str) -> None:
    """Compare the actual final response request path and query.

    :param context: AT context with real response. Example: Experts response.
    :param path: Expected local URL. Example: "/experts/?category=design".
    :return: None. Example: None.
    :raises AssertionError: If the actual URL differs.
    """
    raise NotImplementedError()


@then('the page title is "{title}"')
def page_title_is(context: Context, title: str) -> None:
    """Check the document title and visible page heading.

    :param context: AT context with real response. Example: Experts response.
    :param title: Required title. Example: "Experts".
    :return: None. Example: None.
    :raises AssertionError: If document title or page heading differs.
    """
    raise NotImplementedError()


@then('the subtitle is "{subtitle}"')
def subtitle_is(context: Context, subtitle: str) -> None:
    """Check the rendered page subtitle exactly.

    :param context: AT context with real response. Example: Experts response.
    :param subtitle: Required text. Example: "Top contributors by playbook category".
    :return: None. Example: None.
    :raises AssertionError: If the subtitle differs.
    """
    raise NotImplementedError()


@then('the "{category}" category is current')
def category_is_current(context: Context, category: str) -> None:
    """Check the selected category's semantic current-page state.

    :param context: AT context with real response. Example: Experts response.
    :param category: Visible category label. Example: "Development".
    :return: None. Example: None.
    :raises AssertionError: If the category lacks aria-current="page".
    """
    raise NotImplementedError()
