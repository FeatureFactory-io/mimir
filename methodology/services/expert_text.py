"""Shared pure presentation primitives; no ORM, profile query or contact data."""

from __future__ import annotations


def format_karma(points: int) -> str:
    """Format nonnegative integral Karma using thousands separators.

    :param points: Live numeric total. Example: 8200.
    :return: Readable numeric text. Example: "8,200".
    :raises ValueError: For boolean, noninteger or negative values.
    """
    raise NotImplementedError()


def category_label(category_slug: str) -> str:
    """Resolve an internal category slug using existing Playbook choices.

    :param category_slug: Recognized canonical slug. Example: "design".
    :return: Existing user-facing category label. Example: "Design".
    :raises ValueError: For an unsupported or malformed slug.
    """
    raise NotImplementedError()


def display_initials(display_name: str) -> str:
    """Return uppercase initials from at most the first two name components.

    :param display_name: Nonblank public display name. Example: "Maria Rodriguez".
    :return: At most two initials. Example: "MR".
    :raises ValueError: For a nonstring or blank name.
    """
    raise NotImplementedError()


def format_numeric_fallback(
    released_public_playbook_count: int, successful_gui_copy_count: int
) -> str:
    """Format current public-book and eligible GUI author-copy counts.

    :param released_public_playbook_count: Current public releases. Example: 2.
    :param successful_gui_copy_count: GUI author-consumption events. Example: 47.
    :return: Singular-aware fallback. Example: "2 released playbooks · 47 copies".
    :raises ValueError: For boolean, noninteger or negative counts.
    """
    raise NotImplementedError()
