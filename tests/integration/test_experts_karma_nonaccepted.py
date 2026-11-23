from __future__ import annotations

import pytest
from _pytest.logging import LogCaptureFixture
from django.test import Client
from methodology.models import ProcessImprovementProposal as PIP


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [
        PIP.STATUS_DRAFT,
        PIP.STATUS_SUBMITTED,
        PIP.STATUS_PROCESSING_GALDR,
        PIP.STATUS_REVIEWED,
        PIP.STATUS_REJECTED,
    ],
)
def test_nonaccepted_pip_log_story_reject(
    status: str, caplog: LogCaptureFixture
) -> None:
    """Prove status eligibility, unchanged awards and safe skip narration.

    :param status: Independent persisted boundary. Example: "reviewed".
    :param caplog: Real INFO capture. Example: eligibility branch records.
    :return: None. Example: empty outcomes and Maria remains at 8200.
    :raises AssertionError: If eligibility, ledger, projection or logs differ.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_finalize_pip_with_rejected_only_preserves_karma_content_and_version(
    client: Client, django_capture_on_commit_callbacks
) -> None:
    """Prove real staff rejection preserves content/version/awards and sends mail.

    :param client: Real HTTP client. Example: logged-in staff mchen.
    :param django_capture_on_commit_callbacks: Callback capture fixture.
        Example: execute=True delivers locmem rejection notification.
    :return: None. Example: rejected PIP, version 2.0 and Maria 8200.
    :raises AssertionError: If persisted decision or permitted effects differ.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_rejected_finalization_log_story_reject(
    client: Client, caplog: LogCaptureFixture
) -> None:
    """Assert S32 zero-award narration through actual all-reject finalization.

    :param client: Real staff HTTP client. Example: mchen session.
    :param caplog: Real INFO capture. Example: zero-outcome eligibility beats.
    :return: None. Example: every declared log row is present and safe.
    :raises AssertionError: If skip narration or ledger invariants differ.
    """
    raise NotImplementedError()
