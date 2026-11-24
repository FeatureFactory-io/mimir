"""
MCP User Context Management.

Manages current user context using contextvars for thread-safe operation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import User

import logging
import contextvars

logger = logging.getLogger(__name__)

# Thread-safe context variable for current user
_current_user = contextvars.ContextVar("current_user", default=None)


def set_current_user(user: User) -> None:
    """Set the saved user for the current MCP execution context.

    :param user: Loaded Django user. Example: authenticated MCP account.
    :return: None. Example: get_current_user() returns the account.
    :raises ValueError: The user has no persisted identifier.
    """
    _log_user_context(user)
    _current_user.set(user)


def get_current_user() -> User:
    """
    Get the current user from MCP context.

    :returns: Django User instance
    :raises ValueError: If no user context is set
    """
    user = _current_user.get(None)
    if user is None:
        logger.error("MCP context: No user context available")
        raise ValueError("No user context available. Call set_current_user() first.")
    return user


def clear_current_user() -> None:
    """Clear the current user context."""
    _current_user.set(None)
    logger.info("MCP context: User context cleared")


def _log_user_context(user: User) -> None:
    """Log bounded context facts without personal account metadata.

    :param user: Loaded context user. Example: Mike.
    :return: None. Example: user_id, is_active and is_staff logged at INFO.
    :raises ValueError: Missing persisted user identifier.
    """
    user_id = getattr(user, "pk", None)
    if type(user_id) is not int or user_id <= 0:
        raise ValueError("MCP context requires a saved user identifier.")
    logger.info(
        "MCP context: user_id=%s is_active=%s is_staff=%s",
        user_id,
        user.is_active,
        user.is_staff,
    )
