from __future__ import annotations

from behave import then
from behave.runner import Context


@then("Reach out is disabled and has no mailto destination")
def guest_detail_reach_out_is_restricted(context: Context) -> None:
    """Check native disabled guest contact in the actual initial response.

    :param context: Real AT response and Cedar dataset. Example: S16 context.
    :return: None. Example: None after shared guest markup assertion.
    :raises AssertionError: If contact is enabled or any contact email leaks.
    """
    raise NotImplementedError()


@then('its focusable wrapper explains "{explanation}"')
def guest_contact_wrapper_explains(context: Context, explanation: str) -> None:
    """Check wrapper focusability and explanation association in initial HTML.

    :param context: Real AT response. Example: S16 public detail response.
    :param explanation: Exact required description. Example: GUEST_CONTACT_EXPLANATION.
    :return: None. Example: None after matching text and aria-describedby.
    :raises AssertionError: If explanation, target ID or focusable markup differs.
    """
    raise NotImplementedError()


@then("public contribution and released-playbook evidence remain readable")
def guest_detail_public_evidence_is_readable(context: Context) -> None:
    """Check public prose and real anonymous evidence HTTP access.

    :param context: AT client, response and cedar_dataset. Example: S16 context.
    :return: None. Example: None after shared server evidence assertion.
    :raises AssertionError: If full prose or public released evidence is unavailable.
    """
    raise NotImplementedError()
