"""S13 browser certification using the existing isolated fixture lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from http import HTTPMethod, HTTPStatus
from sqlite3 import Connection
from urllib.parse import parse_qs, urlsplit

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.db import connection
from django.db.models import Q
from django.urls import reverse
from playwright.sync_api import Page, Request, Response, expect
from rest_framework.authtoken.models import Token

from methodology.models import AgentInteraction, ExpertProfile, KarmaAward
from tests.support.experts_data import CedarDataset

_OWN_PROFILE_PATH = "/auth/user/profile/"
_PRIVATE_PROFILE_IDS = (
    "profile-page",
    "profile-edit-btn",
    "profile-karma-card",
    "profile-karma-total",
    "profile-contribution-summary",
    "profile-token-field",
    "profile-token-toggle",
    "profile-token-copy",
    "profile-token-regenerate-form",
    "profile-token-regenerate-password",
    "profile-token-regenerate-submit",
)
_SAFE_REQUEST_METHODS = frozenset((HTTPMethod.GET, HTTPMethod.HEAD, HTTPMethod.OPTIONS))


@dataclass(frozen=True, repr=False)
class _PrivateProfile:
    """Persisted private values used for disclosure checks without exposing them."""

    token: str
    summary: str


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_own_profile_with_anonymous_browser_navigation_shows_login_only(
    page: Page,
    live_server_url: str,
    cedar_dataset: CedarDataset,
    mailoutbox: list[EmailMessage],
) -> None:
    """Prove a fresh anonymous browser cannot display own-profile controls.

    :param page: Existing function-scoped page. Example: fresh Chromium page.
    :param live_server_url: Real test server origin. Example: http://localhost:8001.
    :param cedar_dataset: Real Cedar baseline. Example: contains Maria's account.
    :param mailoutbox: Test-local email outbox. Example: empty after guest navigation.
    :return: None. Example: after an anonymous sign-in handoff with no writes.
    :raises AssertionError: For incorrect redirect, private content or a side effect.
    """
    private_profile = _prepare_private_profile(cedar_dataset)
    rows_before = _snapshot_rows()
    sqlite_connection = connection.connection
    assert isinstance(sqlite_connection, Connection) and connection.is_in_memory_db()
    writes_before = sqlite_connection.total_changes
    assert page.url == "about:blank" and not page.context.cookies()

    responses = _follow_guest_profile_request(page, live_server_url)
    _assert_login_handoff(page, live_server_url, responses)
    _assert_private_profile_absent(page, responses, private_profile)

    assert sqlite_connection.total_changes == writes_before, (
        "Guest navigation wrote to SQLite"
    )
    if _snapshot_rows() != rows_before:
        raise AssertionError("Guest navigation changed persisted Cedar state")
    assert len(mailoutbox) == 0, "Guest navigation sent mail"


def _prepare_private_profile(cedar: CedarDataset) -> _PrivateProfile:
    """Establish a real private token and summary before the navigation.

    :param cedar: Previously loaded baseline. Example: Maria has a stored summary.
    :return: Private values for a meaningful absence check. Example: Maria's API key.
    :raises AssertionError: If Bob has an account or the private values are missing.
    """
    assert not User.objects.filter(
        Q(username__iexact="bob")
        | Q(first_name__iexact="Bob", last_name__iexact="Carter")
    ).exists()
    maria = cedar.users_by_username["mrodriguez"]
    token, _ = Token.objects.get_or_create(user=maria)
    summary = ExpertProfile.objects.get(user=maria).contribution_summary
    if not token.key or not summary:
        raise AssertionError("The Cedar account is missing private test values")
    return _PrivateProfile(token.key, summary)


def _snapshot_rows() -> tuple[tuple[tuple[object, ...], ...], ...]:
    """Capture account, token, Karma, profile and model interaction state.

    :return: Complete rows ordered by primary key. Example: before the guest request.
    """
    return tuple(
        tuple(model.objects.order_by("pk").values_list())
        for model in (User, Token, KarmaAward, ExpertProfile, AgentInteraction)
    )


def _follow_guest_profile_request(page: Page, origin: str) -> tuple[Response, Response]:
    """Navigate the existing page directly to the own-profile URL.

    :param page: Fresh browser fixture. Example: no cookies or open document.
    :param origin: Test server origin. Example: http://localhost:8001.
    :return: Both actual document responses. Example: the redirect and login page.
    :raises AssertionError: If navigation issues unexpected requests or misses a document.
    """
    requests: list[Request] = []

    def observe_request(request: Request) -> None:
        """Keep the request object for the post-navigation assertions.

        :param request: Browser event. Example: GET for the login page.
        :return: None.
        """
        requests.append(request)

    page.on("request", observe_request)
    try:
        page.goto(f"{origin}{_OWN_PROFILE_PATH}")
    finally:
        page.remove_listener("request", observe_request)
    assert all(request.method in _SAFE_REQUEST_METHODS for request in requests)
    documents = [
        request
        for request in requests
        if request.is_navigation_request() and request.frame == page.main_frame
    ]
    assert len(documents) == 2, "Expected one profile request and one login request"
    original, destination = documents
    assert original.method == destination.method == HTTPMethod.GET
    assert original.redirected_from is None and destination.redirected_from == original
    redirect, login = original.response(), destination.response()
    assert redirect is not None and login is not None
    return redirect, login


def _assert_login_handoff(
    page: Page, origin: str, responses: tuple[Response, Response]
) -> None:
    """Check the local redirect, one preserved next value and visible login form.

    :param page: Final browser page. Example: the login form is visible.
    :param origin: Test server origin. Example: http://localhost:8001.
    :param responses: Actual redirect and destination. Example: HTTP 302 then 200.
    :return: None. Example: after confirming the final page and anonymous cookie state.
    :raises AssertionError: If the destination, redirect chain or session is wrong.
    """
    redirect, login = responses
    assert redirect.url == f"{origin}{_OWN_PROFILE_PATH}"
    assert redirect.status == HTTPStatus.FOUND and login.status == HTTPStatus.OK
    assert login.url == page.url
    location = urlsplit(redirect.header_value("location") or "")
    target = urlsplit(page.url)
    local = urlsplit(origin)
    assert not (location.scheme or location.netloc or location.fragment)
    assert (target.scheme, target.netloc) == (local.scheme, local.netloc)
    assert not target.fragment
    assert location.path == target.path == reverse("login")
    expected_query = {"next": [_OWN_PROFILE_PATH]}
    assert parse_qs(location.query, keep_blank_values=True) == expected_query
    assert parse_qs(target.query, keep_blank_values=True) == expected_query
    expect(page.get_by_test_id("login-form").and_(page.locator("form"))).to_be_visible()
    if any(
        cookie["name"] == settings.SESSION_COOKIE_NAME
        for cookie in page.context.cookies()
    ):
        raise AssertionError("Guest navigation issued a session cookie")


def _assert_private_profile_absent(
    page: Page, responses: tuple[Response, Response], private_profile: _PrivateProfile
) -> None:
    """Reject private HTML, hidden controls or token leakage through headers.

    :param page: Full destination document. Example: the anonymous login page.
    :param responses: Actual redirect and destination. Example: HTTP 302 then 200.
    :param private_profile: Real pre-existing private values. Example: Maria's token.
    :return: None. Example: after finding no own-profile content.
    :raises AssertionError: If any private content appears, including hidden elements.
    """
    for test_id in _PRIVATE_PROFILE_IDS:
        assert (
            page.get_by_test_id(test_id).or_(page.locator(f"#{test_id}")).count() == 0
        )
    content = unescape(page.content())
    if private_profile.summary in content:
        raise AssertionError("Guest navigation exposed the stored contribution summary")
    header_values = tuple(
        value for response in responses for value in response.all_headers().values()
    )
    if any(private_profile.token in value for value in (content, *header_values)):
        raise AssertionError("Guest navigation exposed a private API token")
