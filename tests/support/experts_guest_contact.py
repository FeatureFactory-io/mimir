from __future__ import annotations

from django.http import HttpResponse

GUEST_CONTACT_EXPLANATION = "You need to be logged in to reach out to the expert"


def assert_guest_contact_markup(
    response: HttpResponse,
    container_test_id: str | None,
    forbidden_emails: tuple[str, ...],
) -> None:
    """Assert initial guest contact HTML using the shared experts_html helpers.

    :param response: Actual guest response. Example: Design list HTTP 200.
    :param container_test_id: Scope or document root. Example: "experts-card-mrodriguez"; None for detail.
    :param forbidden_emails: Fixture contact values forbidden in the whole HTML. Example: ("maria.rodriguez@example.com",).
    :return: None when disabled button, focusable wrapper, exact associated description, tooltip declaration and privacy checks pass.
    :raises AssertionError: For missing/ambiguous controls, invalid description, enabled contact or leaked email/mailto.
    """
    raise NotImplementedError()


def assert_guest_profile_link(response: HttpResponse, username: str) -> None:
    """Assert the contributor's profile action remains available on the list.

    :param response: Actual guest list response. Example: Design list HTTP 200.
    :param username: Contributor username. Example: "mrodriguez".
    :return: None when the scoped named link is enabled and targets /experts/mrodriguez/.
    :raises AssertionError: For a missing, disabled, incorrect or authentication-redirect destination.
    """
    raise NotImplementedError()
