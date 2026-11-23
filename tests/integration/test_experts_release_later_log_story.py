from __future__ import annotations

import pytest


@pytest.mark.django_db
def test_karma_later_release_log_story_happy(caplog: pytest.LogCaptureFixture) -> None:
    """Assert S30 later-release beats with the real ledger result.

    :param caplog: Real capture. Example: INFO for later-release-02.
    :return: None. Example: previously_released, zero points, no earned message.
    :raises AssertionError: If declared beats, correlation or domain outcome differ.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_karma_later_release_log_story_reject(caplog: pytest.LogCaptureFixture) -> None:
    """Assert wrong-owner release rejection and unchanged persisted state.

    :param caplog: Real capture. Example: INFO-or-higher permission rejection.
    :return: None. Example: safe reason and no award-success beat.
    :raises AssertionError: If rejection story is absent or mutation occurs.
    """
    raise NotImplementedError()
