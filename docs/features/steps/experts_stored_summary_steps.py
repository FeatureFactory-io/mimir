from __future__ import annotations

from behave import given, then
from behave.runner import Context


@given("Maria's contribution summary has refreshed")
def maria_has_stored_refreshed_summary(context: Context) -> None:
    """Select Maria's successful stored Cedar summary without generating prose.

    :param context: Shared Cedar AT context. Example: context.cedar_dataset.
    :return: None; context stores the persisted paragraph as comparison source.
    :raises AssertionError: If stored text is absent or differs from the Cedar oracle.
    """
    raise NotImplementedError()


@then("her own profile and public expert detail show that stored text")
def own_and_public_show_stored_summary(context: Context) -> None:
    """Check real authenticated-own and public-detail initial HTML.

    :param context: Real transactional AT context. Example: context.client.
    :return: None when both full prose nodes match the persisted paragraph.
    :raises AssertionError: If status, text or final sentence differs.
    """
    raise NotImplementedError()


@then("her leaderboard hint is a visually truncated excerpt of it")
def leaderboard_uses_stored_summary(context: Context) -> None:
    """Check full source DOM and clamp wiring; browser gate proves geometry.

    :param context: Shared real AT context. Example: context.cedar_dataset.
    :return: None when Maria's actual Design-card hint retains the full source.
    :raises AssertionError: If server truncation or missing clamp wiring is found.
    """
    raise NotImplementedError()


@then("the public detail retains the complete paragraph")
def public_detail_retains_complete_summary(context: Context) -> None:
    """Check the saved real public response retains all nine fixture sentences.

    :param context: AT context with public response. Example: context.client.
    :return: None when the public paragraph exactly matches stored text.
    :raises AssertionError: If any stored sentence or its ending is absent.
    """
    raise NotImplementedError()
