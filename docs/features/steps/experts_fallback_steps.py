from __future__ import annotations

from behave import then
from behave.runner import Context

from tests.support.experts_fallback_assertions import assert_development_fallback


@then("Development is the current category")
def development_is_current(context: Context) -> None:
    """Delegate this literal phrase to S01's shared category assertion.

    :param context: Real AT response context. Example: context.response from S03's URL step.
    :return: None. Example: successful delegation returns None.
    :raises AssertionError: If S01's current-category contract fails.
    """
    context.execute_steps('Then the "Development" category is current')


@then("no server error or unrelated category data is shown")
def fallback_has_no_unrelated_data(context: Context) -> None:
    """Apply the shared rendered-response assertion to the actual AT response.

    :param context: Cedar-backed Django response context. Example: context.response.
    :return: None. Example: passing assertions return None.
    :raises AssertionError: If the fallback response is erroneous or includes unrelated cards.
    """
    assert_development_fallback(context.response)
