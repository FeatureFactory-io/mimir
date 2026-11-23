from __future__ import annotations

import pytest


@pytest.mark.django_db(transaction=True)
def test_s28_copy_receipt_with_stored_summary_updates_only_live_numbers() -> None:
    """Prove the real receipt adds exactly the eligible pair, preserving prose.
    :return: None. Example: Maria 8205, Mike 12455, identical summary state.
    :raises AssertionError: For wrong attribution, extra rows or changed metadata.
    """
    raise NotImplementedError()


@pytest.mark.django_db(transaction=True)
def test_s28_display_with_completed_copy_reads_live_totals_and_stored_prose() -> None:
    """Prove real surfaces read updated projections without changing prose.
    :return: None. Example: own/list/detail show 8,205 and Design.
    :raises AssertionError: For stale display, changed text or GET side effects.
    """
    raise NotImplementedError()


@pytest.mark.django_db(transaction=True)
def test_s28_copy_log_story_happy(caplog: pytest.LogCaptureFixture) -> None:
    """Assert E's existing receipt/projection beats after clearing baseline logs.
    :param caplog: INFO capture. Example: receipt and profile records.
    :return: None. Example: complete copy story and no generation entry.
    :raises AssertionError: For missing beats, extra generation or leaked bodies.
    """
    raise NotImplementedError()
