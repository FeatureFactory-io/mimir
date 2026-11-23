"""
MCP User Context Management.

Manages current user context using contextvars for thread-safe operation.
"""

import logging
import contextvars

logger = logging.getLogger(__name__)

# Thread-safe context variable for current user
_current_user = contextvars.ContextVar("current_user", default=None)


def set_current_user(user):
    """
    Set the current user in MCP context.

    :param user: Django User instance
    """
    logger.info(f"MCP context: About to set user to {user.username} (id={user.id})...")
    _current_user.set(user)
    logger.info(
        f"MCP context: ✓ User successfully set to {user.username} (id={user.id})"
    )
    logger.info(
        f"MCP context: User attributes - email={user.email}, is_active={user.is_active}, is_staff={user.is_staff}"
    )


def get_current_user():
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


def clear_current_user():
    """Clear the current user context."""
    _current_user.set(None)
    logger.info("MCP context: User context cleared")


def _log_user_context(user: User) -> None:
    """Log bounded context facts without personal account metadata.

    :param user: Loaded context user. Example: Mike.
    :return: None. Example: user_id, is_active and is_staff logged at INFO.
    :raises ValueError: Missing persisted user identifier.
    """
    raise NotImplementedError()
