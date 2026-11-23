from __future__ import annotations

"""S14-owned contact phrases; baseline/authentication bindings are reused."""
from behave import then, when
from behave.runner import Context


@when("she inspects Maria's Reach out action on list and public detail")
def inspect_maria_contact_actions(context: Context) -> None:
    """Read real production HTML for both contact surfaces.

    :param context: Existing AT context. Example: context.cedar_dataset and client.
    :return: None. Example: two real responses retained for later assertions.
    :raises AssertionError: For unsuccessful requests or missing Maria actions.
    """
    raise NotImplementedError()


@then('both destinations are "{destination}"')
def assert_both_contact_destinations(context: Context, destination: str) -> None:
    """Compare both rendered Maria destinations with the exact contract value.

    :param context: Existing AT context. Example: retained list/detail responses.
    :param destination: Expected href. Example: "mailto:maria.rodriguez@example.com".
    :return: None. Example: both action destinations match.
    :raises AssertionError: For an absent, disabled or mismatched action.
    """
    raise NotImplementedError()


@then("the action does not imply that availability is confirmed")
def assert_contact_does_not_confirm_availability(context: Context) -> None:
    """Check action labels/descriptions preserve the discussion-only handoff.

    :param context: Existing AT context. Example: both retained contact controls.
    :return: None. Example: discussion wording and no availability promise.
    :raises AssertionError: For availability or suitability confirmation language.
    """
    raise NotImplementedError()
