from __future__ import annotations

from django.test import Client


def test_stored_summary_with_three_surface_reads_preserves_identical_full_text(
    client: Client, db: None
) -> None:
    """Certify one persisted paragraph across all three real HTML responses.

    :param client: Real Django client. Example: Client().
    :param db: Isolated pytest database access. Example: None.
    :return: None when every full DOM paragraph equals stored Maria prose.
    :raises AssertionError: If a response differs, omits its ending or truncates text.
    """
    raise NotImplementedError()


def test_stored_summary_with_repeated_reads_preserves_refresh_state(
    client: Client, db: None
) -> None:
    """Certify repeated serving preserves stored prose and refresh state.

    :param client: Real Django client. Example: Client().
    :param db: Isolated pytest database access. Example: None.
    :return: None when text, metadata and interaction count remain unchanged.
    :raises AssertionError: If reads mutate summary state or rendered text.
    """
    raise NotImplementedError()
