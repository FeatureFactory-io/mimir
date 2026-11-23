"""Shared pure presentation primitives; no ORM, profile query or contact data."""

from __future__ import annotations

from methodology.models.playbook import Playbook

CATEGORY_LABELS = dict(Playbook.CATEGORY_CHOICES)


def format_karma(points: int) -> str:
    """Format nonnegative integral Karma using thousands separators.

    :param points: Live numeric total. Example: 8200.
    :return: Readable numeric text. Example: "8,200".
    :raises ValueError: For boolean, noninteger or negative values.
    """
    if type(points) is not int or points < 0:
        raise ValueError("Karma points must be a nonnegative integer.")
    return f"{points:,}"


def category_label(category_slug: str) -> str:
    """Resolve an internal category slug using existing Playbook choices.

    :param category_slug: Recognized canonical slug. Example: "design".
    :return: Existing user-facing category label. Example: "Design".
    :raises ValueError: For an unsupported or malformed slug.
    """
    if not isinstance(category_slug, str) or category_slug not in CATEGORY_LABELS:
        raise ValueError("Unrecognized playbook category.")
    return CATEGORY_LABELS[category_slug]


def display_initials(display_name: str) -> str:
    """Return uppercase initials from at most the first two name components.

    :param display_name: Nonblank public display name. Example: "Maria Rodriguez".
    :return: At most two initials. Example: "MR".
    :raises ValueError: For a nonstring or blank name.
    """
    if not isinstance(display_name, str) or not display_name.strip():
        raise ValueError("Display name must be nonblank text.")
    return "".join(component[0].upper() for component in display_name.split()[:2])


def format_numeric_fallback(
    released_public_playbook_count: int, successful_gui_copy_count: int
) -> str:
    """Format current public-book and eligible GUI author-copy counts.

    :param released_public_playbook_count: Current public releases. Example: 2.
    :param successful_gui_copy_count: GUI author-consumption events. Example: 47.
    :return: Singular-aware fallback. Example: "2 released playbooks · 47 copies".
    :raises ValueError: For boolean, noninteger or negative counts.
    """
    books = format_karma(released_public_playbook_count)
    copies = format_karma(successful_gui_copy_count)
    book_label = "playbook" if released_public_playbook_count == 1 else "playbooks"
    copy_label = "copy" if successful_gui_copy_count == 1 else "copies"
    return f"{books} released {book_label} · {copies} {copy_label}"
