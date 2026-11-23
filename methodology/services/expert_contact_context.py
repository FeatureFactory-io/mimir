from __future__ import annotations

"""Request-local contact presentation; never part of public expert projections."""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal
from django.http import HttpRequest

ContactState = Literal["available", "authentication_required", "unavailable"]


@dataclass(frozen=True, slots=True)
class ExpertContactContext:
    """Immutable contact presentation with no separate raw email field."""

    username: str
    state: ContactState
    href: str | None
    explanation: str


def build_expert_contact_context(
    request: HttpRequest, expert_usernames: Sequence[str]
) -> Mapping[str, ExpertContactContext]:
    """Build request-local handoffs for already eligible public experts.

    Validate request and usernames; short-circuit guests before email lookup;
    batch-load authenticated targets; validate destinations; return immutable
    mapping and emit the declared body-free log story.

    :param request: Middleware-authenticated request. Example: Elena's list GET.
    :param expert_usernames: Names from public projections. Example: ("mrodriguez",).
    :return: Immutable contact mapping. Example: Maria mapped to an available href.
    :raises TypeError: For invalid request/collection types.
    :raises ValueError: For absent authentication context or invalid usernames.
    """
    raise NotImplementedError()


def _validate_contact_request(request: HttpRequest) -> None:
    """Validate the actual request and middleware-provided identity boundary.

    :param request: Real Django request. Example: a client-produced GET request.
    :return: None. Example: accepted authenticated or anonymous request.
    :raises TypeError: If request is not an HttpRequest.
    :raises ValueError: If authentication middleware context is absent.
    """
    raise NotImplementedError()


def _validated_usernames(expert_usernames: Sequence[str]) -> tuple[str, ...]:
    """Validate and deduplicate public usernames without mutating the input.

    :param expert_usernames: Public names. Example: ("mrodriguez", "mrodriguez").
    :return: Ordered unique tuple. Example: ("mrodriguez",); empty input gives ().
    :raises TypeError: If collection or item types are invalid.
    :raises ValueError: If an item is empty or not a valid model username.
    """
    raise NotImplementedError()


def _load_target_emails(expert_usernames: tuple[str, ...]) -> Mapping[str, str]:
    """Read target mailboxes in one query after authenticated authorization.

    :param expert_usernames: Already eligible names. Example: ("mrodriguez",).
    :return: Target mailbox mapping. Example: Maria's configured account mailbox.
    :raises RuntimeError: No application-level exception is deliberately raised;
        database failures propagate rather than fabricate valid contact data.
    """
    raise NotImplementedError()


def _safe_mailto(email: str | None) -> str | None:
    """Validate a single mailbox and encode a destination without headers.

    :param email: Account mailbox. Example: "maria.rodriguez@example.com".
    :return: Safe href or None. Example: "mailto:maria.rodriguez@example.com".
    :raises TypeError: If supplied a value other than str or None.
    """
    raise NotImplementedError()


def _contact_for_email(username: str, email: str | None) -> ExpertContactContext:
    """Build available/unavailable state for an authenticated target.

    :param username: Valid public username. Example: "mrodriguez".
    :param email: Account mailbox or missing value. Example: None.
    :return: Immutable contact. Example: unavailable with no href.
    :raises TypeError: If internal caller violates the validated input contract.
    """
    raise NotImplementedError()


def _guest_contact(username: str) -> ExpertContactContext:
    """Build the exact guest restriction without loading a target mailbox.

    :param username: Valid public username. Example: "mrodriguez".
    :return: Disabled guest state. Example: authentication_required with no href.
    :raises ValueError: If internal caller supplies an invalid username.
    """
    raise NotImplementedError()
