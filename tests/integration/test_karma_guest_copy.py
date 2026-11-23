from __future__ import annotations

"""Real server contracts complementary to guest clipboard certification."""
import pytest
from django.test import Client
from pytest import LogCaptureFixture


@pytest.mark.django_db
def test_guest_activity_with_initial_get_renders_full_prompt_without_awards(
    client: Client,
) -> None:
    """Certify initial anonymous HTML without claiming clipboard execution.

    :param client: Anonymous Django client. Example: unauthenticated activity6203 GET.
    :return: None after full prompt, permissions and unchanged DB checks.
    :raises AssertionError: If HTML differs, Mike !=12450 or any account/award changes.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_guest_copy_receipt_with_anonymous_post_rejects_without_awards(
    client: Client,
) -> None:
    """Reject a valid-shaped anonymous receipt through S36's real boundary.

    :param client: Anonymous Django client. Example: POST activity6203 plus action UUID.
    :return: None after non-redirect rejection and unchanged DB checks.
    :raises AssertionError: If anonymous reporting succeeds or creates domain state.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_guest_copy_receipt_log_story_reject(
    client: Client, caplog: LogCaptureFixture
) -> None:
    """Certify S36's safe unauthenticated rejection beat with real HTTP.

    :param client: Anonymous Django client. Example: valid-shaped forged receipt.
    :param caplog: INFO log capture. Example: request ID and unauthenticated branch.
    :return: None after assert_log_story and sensitive-content exclusion checks.
    :raises AssertionError: If rejection is unobservable or contains sensitive data.
    """
    raise NotImplementedError()
