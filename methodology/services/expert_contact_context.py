"""Request-local contact presentation; never part of public expert projections."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal
from urllib.parse import quote, unquote

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.base import SessionBase
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpRequest

from methodology.services.experts_service import _CORRELATION_ID

logger = logging.getLogger(__name__)
_LOG = "build_expert_contact_context"
_VALIDATION_LOG = f"{_LOG} | validation | reason=invalid_input field=%s %s"
_ENTRY_LOG = f"{_LOG} | entry | actor_id=%s target_count=%s %s"
_GUEST_LOG = f"{_LOG} | branch | reason=authentication_required email_lookup=false %s"
_UNAVAILABLE_LOG = (
    f"{_LOG} | branch | reason=contact_unavailable unavailable_count=%s %s"
)
_EXIT_LOG = f"{_LOG} | exit | available_count=%s disabled_count=%s %s"
_SIGN_IN_EXPLANATION = "You need to be logged in to reach out to the expert"
_UNAVAILABLE_EXPLANATION = "Contact information is unavailable"

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
    tag = _validate_contact_request(request)
    try:
        usernames = _validated_usernames(expert_usernames)
    except TypeError, ValueError:
        logger.warning(_VALIDATION_LOG, "expert_usernames", tag)
        raise
    authenticated = request.user.is_authenticated
    actor_id = request.user.pk if authenticated else "anonymous"
    logger.info(_ENTRY_LOG, actor_id, len(usernames), tag)
    contacts: dict[str, ExpertContactContext] = {}
    if not authenticated:
        logger.info(_GUEST_LOG, tag)
        contacts = {username: _guest_contact(username) for username in usernames}
    elif usernames:
        emails = _load_target_emails(usernames, tag=tag)
        contacts = {
            username: _contact_for_email(username, emails.get(username))
            for username in usernames
        }
    available_count = sum(contact.state == "available" for contact in contacts.values())
    disabled_count = len(contacts) - available_count
    if authenticated and disabled_count:
        logger.info(_UNAVAILABLE_LOG, disabled_count, tag)
    logger.info(_EXIT_LOG, available_count, disabled_count, tag)
    return MappingProxyType(contacts)


def _validate_contact_request(request: HttpRequest) -> str:
    """Validate the actual request and middleware-provided identity boundary.

    :param request: Real Django request. Example: a client-produced GET request.
    :return: Safe log context. Example: "correlation_id=cedar-s14".
    :raises TypeError: If request is not an HttpRequest.
    :raises ValueError: If authentication middleware context is absent.
    """
    if not isinstance(request, HttpRequest):
        logger.warning(_VALIDATION_LOG, "request", "correlation_id=none")
        raise TypeError("Contact context requires a Django HttpRequest.")
    correlation = getattr(request, "request_id", None)
    if not isinstance(correlation, str) or not _CORRELATION_ID.fullmatch(correlation):
        correlation = "none"
    tag = f"correlation_id={correlation}"
    user = getattr(request, "user", None)
    has_session = isinstance(getattr(request, "session", None), SessionBase)
    valid_user = isinstance(user, AnonymousUser) or (
        isinstance(user, get_user_model()) and user.pk is not None and user.is_active
    )
    if not has_session or not valid_user:
        logger.warning(_VALIDATION_LOG, "request", tag)
        raise ValueError("Contact context requires middleware authentication context.")
    return tag


def _validated_usernames(expert_usernames: Sequence[str]) -> tuple[str, ...]:
    """Validate and deduplicate public usernames without mutating the input.

    :param expert_usernames: Public names. Example: ("mrodriguez", "mrodriguez").
    :return: Ordered unique tuple. Example: ("mrodriguez",); empty input gives ().
    :raises TypeError: If collection or item types are invalid.
    :raises ValueError: If an item is empty or not a valid model username.
    """
    if not isinstance(expert_usernames, Sequence) or isinstance(
        expert_usernames, (str, bytes, bytearray, memoryview)
    ):
        raise TypeError("Expert usernames must be a sequence of strings.")
    username_field = get_user_model()._meta.get_field("username")
    for username in expert_usernames:
        if not isinstance(username, str):
            raise TypeError("Each expert username must be a string.")
        try:
            username_field.clean(username, None)
        except ValidationError:
            raise ValueError(
                "Each expert username must be a valid account name."
            ) from None
    return tuple(dict.fromkeys(expert_usernames))


def _load_target_emails(
    expert_usernames: tuple[str, ...], *, tag: str
) -> Mapping[str, str]:
    """Read target mailboxes in one query after authenticated authorization.

    :param expert_usernames: Already eligible names. Example: ("mrodriguez",).
    :param tag: Safe log context. Example: "correlation_id=cedar-s14".
    :return: Target mailbox mapping. Example: Maria's configured account mailbox.
    :raises DatabaseError: If the target mailbox query fails.
    """
    logger.info(
        "%s | processing | email_lookup=true target_count=%s %s",
        _LOG,
        len(expert_usernames),
        tag,
    )
    return dict(
        get_user_model()
        .objects.filter(username__in=expert_usernames)
        .values_list("username", "email")
    )


def _safe_mailto(email: str | None) -> str | None:
    """Validate a single mailbox and encode a destination without headers.

    :param email: Account mailbox. Example: "maria.rodriguez@example.com".
    :return: Safe href or None. Example: "mailto:maria.rodriguez@example.com".
    :raises TypeError: If supplied a value other than str or None.
    """
    if email is None:
        return None
    if not isinstance(email, str):
        raise TypeError("A target mailbox must be a string or None.")
    if not email.isprintable() or not unquote(email).isprintable():
        return None
    try:
        validate_email(email)
    except ValidationError:
        return None
    mailbox, domain = email.rsplit("@", 1)
    return f"mailto:{quote(mailbox, safe='')}@{quote(domain, safe='')}"


def _contact_for_email(username: str, email: str | None) -> ExpertContactContext:
    """Build available/unavailable state for an authenticated target.

    :param username: Valid public username. Example: "mrodriguez".
    :param email: Account mailbox or missing value. Example: None.
    :return: Immutable contact. Example: unavailable with no href.
    :raises TypeError: If internal caller violates the validated input contract.
    """
    href = _safe_mailto(email)
    if href is None:
        return ExpertContactContext(
            username, "unavailable", None, _UNAVAILABLE_EXPLANATION
        )
    return ExpertContactContext(username, "available", href, "")


def _guest_contact(username: str) -> ExpertContactContext:
    """Build the exact guest restriction without loading a target mailbox.

    :param username: Valid public username. Example: "mrodriguez".
    :return: Disabled guest state. Example: authentication_required with no href.
    """
    return ExpertContactContext(
        username, "authentication_required", None, _SIGN_IN_EXPLANATION
    )
