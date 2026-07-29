"""Highlight search query matches in result display text."""

import re

from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe


def highlight_search_term(text: str, query: str) -> SafeString:
    """Wrap case-insensitive query matches in ``<mark class="mm-search-highlight">``.

    :param text: Plain text to display (escaped before highlighting).
    :param query: User search query; empty query returns escaped text only.
    :return: Safe HTML string with highlighted spans.
    """
    if text is None:
        return mark_safe("")
    escaped = escape(str(text))
    needle = (query or "").strip()
    if not needle:
        return mark_safe(escaped)
    pattern = re.compile(re.escape(needle), re.IGNORECASE)
    highlighted = pattern.sub(
        r'<mark class="mm-search-highlight">\g<0></mark>',
        escaped,
    )
    return mark_safe(highlighted)
