"""Unique S05 Django-client steps; shared assertions retain their owners."""

from __future__ import annotations

from http import HTTPStatus

from behave import given, when
from behave.runner import Context

from tests.support.expert_profile_handoff import extract_maria_profile_href

_DESIGN_PATH = "/experts/?category=design"
_ELENA_USERNAME = "esvensson"


@given("Elena is on the Design leaderboard")
def elena_on_design_leaderboard(context: Context) -> None:
    """Establish Elena's real authenticated Design response.

    :param context: AT context. Example: context.cedar_dataset from S03.
    :return: None. Example: current response is the Design leaderboard.
    :raises AssertionError: Cedar Elena is missing or Design does not load.
    """
    context.execute_steps(
        f'Given Elena is authenticated\nWhen Elena opens "{_DESIGN_PATH}"'
    )
    response = context.response
    assert response.status_code == HTTPStatus.OK, "The Design leaderboard did not load."
    assert response.context["selected_category"] == "design", "Design must be selected."
    assert (
        response.wsgi_request.user
        == context.cedar_dataset.users_by_username[_ELENA_USERNAME]
    ), "The Design leaderboard must be served to Elena."


@when("she follows Maria's View profile link")
def follow_maria_profile_link(context: Context) -> None:
    """Request Maria's actual rendered anchor destination.

    :param context: AT context. Example: real Design response and Django client.
    :return: None. Example: context.response holds Maria's production detail.
    :raises AssertionError: If the link, response or session differs from the contract.
    :raises ValueError: If the Design response HTML cannot be parsed.
    """
    listing = context.response
    href = extract_maria_profile_href(listing.content)
    context.execute_steps(f'When Elena opens "{href}"')
    detail = context.response
    assert detail.status_code == HTTPStatus.OK, "Maria's profile did not load."
    assert detail.wsgi_request.user == listing.wsgi_request.user, (
        "Maria's profile must be served in Elena's session."
    )
