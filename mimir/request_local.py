"""Thread-local request context and its safe correlation identifier."""

from __future__ import annotations

import re
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpRequest

CORRELATION_ID_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}"
CREDENTIAL_PATTERN = re.compile(
    r"(?:api[-_]?(?:key|token)|access[-_]?token|auth[-_]?token|client[-_]?secret|password):.+|"
    r"(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_-]{12,}|"
    r"github_pat_[A-Za-z0-9_-]{12,}|xox[baprs]-[A-Za-z0-9_-]{12,}|"
    r"(?:AKIA|ASIA)[A-Z0-9]{16}|eyJ[\w-]+\.[\w-]+\.[\w-]+|[a-f0-9]{40})",
    re.IGNORECASE,
)

_thread_locals = threading.local()


def normalize_request_id(value: object) -> str | None:
    """Accept only bounded identifiers without a recognized credential.

    :param value: Untrusted request metadata. Example: "cedar-submit-01".
    :return: The unchanged safe ID or None for absent or unsafe input.
        Example: None for "user@example.invalid".
    """
    if (
        isinstance(value, str)
        and re.fullmatch(CORRELATION_ID_PATTERN, value)
        and not CREDENTIAL_PATTERN.search(value)
    ):
        return value
    return None


def set_current_request(request: HttpRequest) -> None:
    """Store the request for logs emitted on this thread.

    :param request: Active Django request. Example: a PIP submission POST.
    :return: None.
    """
    _thread_locals.request = request


def get_current_request() -> HttpRequest | None:
    """Retrieve the current request from thread-local storage.

    :return: Django request or None. Example: None from a background worker.
    """
    return getattr(_thread_locals, "request", None)


def clear_current_request() -> None:
    """Clear the current request from thread-local storage.

    :return: None. Example: clearing again after a finished request is safe.
    """
    if hasattr(_thread_locals, "request"):
        del _thread_locals.request
