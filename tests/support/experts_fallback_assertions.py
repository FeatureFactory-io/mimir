from __future__ import annotations

from django.http import HttpResponse


def assert_development_fallback(response: HttpResponse) -> None:
    """Assert the real rendered fallback result without reparsing query input.

    :param response: Actual production response. Example: client.get("/experts/?category=unrecognized").
    :return: None. Example: successful assertions return None.
    :raises AssertionError: If status, current category, cards, totals or error state differ.
    """
    raise NotImplementedError()
