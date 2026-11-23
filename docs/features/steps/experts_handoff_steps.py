from __future__ import annotations

"""Unique S05 Django-client steps; shared assertions retain their owners."""
from behave import given, when
from behave.runner import Context


@given("Elena is on the Design leaderboard")
def elena_on_design_leaderboard(context: Context) -> None:
    """Establish Elena's real authenticated Design response.

    :param context: AT context. Example: context.cedar_dataset from S03.
    :return: None. Example: current response is the Design leaderboard.
    :raises AssertionError: Cedar Elena is missing or Design does not load.
    :raises NotImplementedError: Until the approved AT slice is implemented.
    """
    raise NotImplementedError()


@when("she follows Maria's View profile link")
def follow_maria_profile_link(context: Context) -> None:
    """Request Maria's actual rendered anchor destination.

    :param context: AT context. Example: real Design response and Django client.
    :return: None. Example: context.response holds Maria's production detail.
    :raises AssertionError: Link missing/ambiguous, href invalid, or GET fails.
    :raises NotImplementedError: Until the approved AT slice is implemented.
    """
    raise NotImplementedError()
