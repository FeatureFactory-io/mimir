from __future__ import annotations

"""EXPERTS-PROFILE-04 real-client authorization certification."""
import pytest
from django.test import Client
from _pytest.logging import LogCaptureFixture
from tests.support.experts_data import load_cedar_baseline
from tests.support.experts_html import find_by_test_id


@pytest.mark.django_db
def test_own_profile_with_anonymous_request_redirects_without_private_render(
    client: Client, caplog: LogCaptureFixture
) -> None:
    """Prove authorization precedes private rendering and token access.

    :param client: Anonymous real Django client. Example: Client().
    :param caplog: Pytest log capture. Example: INFO capture for accounts.views.
    :return: None. Example: None after assertions pass.
    :raises AssertionError: For a wrong redirect, disclosure or token mutation.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_own_profile_with_followed_anonymous_redirect_shows_login_only(
    client: Client,
) -> None:
    """Prove the redirect destination presents only anonymous login controls.

    :param client: Anonymous real Django client. Example: Client().
    :return: None. Example: None after assertions pass.
    :raises AssertionError: For extra redirects, private content or session auth.
    """
    raise NotImplementedError()
