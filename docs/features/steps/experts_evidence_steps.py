from __future__ import annotations

"""S19-specific Django-client acceptance bindings."""
from behave import given, then, when
from behave.runner import Context


@given("Elena is on Maria's public expert profile")
def elena_on_maria_public_profile(context: Context) -> None:
    """Authenticate baseline Elena and request Maria's real public detail.

    :param context: Shared Cedar/client context. Example: context.cedar_dataset.
    :return: None. Example: context.response contains HTTP 200.
    :raises AssertionError: If the real public profile is unavailable.
    """
    raise NotImplementedError()


@when('she follows "{title}" version "{version}"')
def follow_public_evidence(context: Context, title: str, version: str) -> None:
    """Match an evidence item and request its extracted local href.

    :param context: Real profile response. Example: Maria's public detail.
    :param title: Exact playbook title. Example: "Accessibility Audit Playbook".
    :param version: Exact displayed version. Example: "1.0".
    :return: None. Example: context.response contains the destination response.
    :raises AssertionError: If evidence is missing, ambiguous or mismatched.
    :raises ValueError: If the href is external or malformed.
    """
    raise NotImplementedError()


@then('the existing playbook detail route "{path}" is shown')
def existing_playbook_route_shown(context: Context, path: str) -> None:
    """Check actual request path, status and existing detail template.

    :param context: Followed real response. Example: playbook 6101 response.
    :param path: Required destination. Example: "/playbooks/6101/".
    :return: None. Example: None after HTTP 200 and template assertions.
    :raises AssertionError: If actual routing differs or redirects to login.
    """
    raise NotImplementedError()


@then('its workflow "{workflow}" includes "{first}" and "{second}"')
def followed_workflow_includes_activities(
    context: Context, workflow: str, first: str, second: str
) -> None:
    """Follow the real workflow anchor and inspect returned activity evidence.

    :param context: Real playbook detail response. Example: playbook 6101.
    :param workflow: Exact workflow. Example: "Lead an Accessibility Review".
    :param first: Required activity. Example: "Trace Keyboard Focus".
    :param second: Required activity. Example: "Review Form Feedback".
    :return: None. Example: None after real workflow HTTP 200/content checks.
    :raises AssertionError: If workflow membership or either activity differs.
    """
    raise NotImplementedError()
