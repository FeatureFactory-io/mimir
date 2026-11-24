"""EXPERTS-PROFILE-04 real-client authorization certification."""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from http import HTTPStatus
from urllib.parse import parse_qs, urlsplit

import pytest
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.db import connection
from django.db.models import Q
from django.http import HttpResponse
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.authtoken.models import Token

from methodology.models import ExpertProfile
from tests.support.experts_data import CedarDataset
from tests.support.experts_html import _parse_root, _walk_elements, find_by_test_id
from tests.support.experts_logs import capture_experts_logs

_OWN_PROFILE_PATH = "/auth/user/profile/"
_PROFILE_TEMPLATE = "accounts/profile.html"
_LOGIN_FORM_ID = "login-form"
_PROFILE_LOGGER = "accounts.views"
_PROFILE_LOG_PREFIXES = (
    "[PROFILE] Page GET",
    "[PROFILE] Render",
    "accounts.views._profile_contribution_context",
    "accounts.views._validate_profile_contribution_request",
)
_PRIVATE_TEST_IDS = frozenset(
    {
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
    }
)
_READ_ONLY_SQL = {"SELECT", "SAVEPOINT", "RELEASE", "ROLLBACK"}


@dataclass(frozen=True, repr=False)
class _PrivateProfile:
    """Existing private profile material and pre-request account state."""

    maria_key: str
    summary: str
    accounts: tuple[tuple[tuple[object, ...], ...], ...]


@pytest.mark.django_db
def test_own_profile_with_anonymous_request_redirects_without_private_render(
    client: Client,
    caplog: pytest.LogCaptureFixture,
    private_profile: _PrivateProfile,
    mailoutbox: list[EmailMessage],
) -> None:
    """Prove authorization precedes private rendering and token access.

    :param client: Anonymous real Django client. Example: Client().
    :param caplog: Pytest log capture. Example: INFO capture for accounts.views.
    :param private_profile: Prepared Cedar profile state. Example: pre-request token rows.
    :param mailoutbox: Test mail outbox. Example: [] after a guest request.
    :return: None. Example: after all privacy and no-write assertions pass.
    :raises AssertionError: For a wrong redirect, disclosure or request side effect.
    """
    with (
        capture_experts_logs(caplog, (_PROFILE_LOGGER,)),
        CaptureQueriesContext(connection) as queries,
    ):
        response = client.get(_OWN_PROFILE_PATH)

    assert response.status_code == HTTPStatus.FOUND
    _assert_login_location(response.headers["Location"])
    assert _LOGIN_FORM_ID not in _assert_private_profile_absent(
        response, private_profile
    )
    assert not any(
        record.name == _PROFILE_LOGGER
        and record.getMessage().startswith(_PROFILE_LOG_PREFIXES)
        for record in caplog.records
    ), "An anonymous request entered private profile code"
    _assert_read_only(queries, private_profile, mailoutbox)


@pytest.mark.django_db
def test_own_profile_with_followed_anonymous_redirect_shows_login_only(
    client: Client, private_profile: _PrivateProfile, mailoutbox: list[EmailMessage]
) -> None:
    """Prove the redirect destination presents only anonymous login controls.

    :param client: Fresh anonymous real Django client. Example: Client().
    :param private_profile: Prepared Cedar profile state. Example: pre-request token rows.
    :param mailoutbox: Test mail outbox. Example: [] after a guest request.
    :return: None. Example: after one redirect and an anonymous login form.
    :raises AssertionError: For extra redirects, private content or session auth.
    """
    with CaptureQueriesContext(connection) as queries:
        response = client.get(_OWN_PROFILE_PATH, follow=True)

    assert len(response.redirect_chain) == 1
    location, status = response.redirect_chain[0]
    assert status == HTTPStatus.FOUND
    _assert_login_location(location)
    assert response.status_code == HTTPStatus.OK
    assert response.wsgi_request.path == reverse("login")
    _assert_private_profile_absent(response, private_profile)
    assert find_by_test_id(response.content, _LOGIN_FORM_ID).name == "form"
    assert not response.wsgi_request.user.is_authenticated
    assert SESSION_KEY not in response.wsgi_request.session
    _assert_read_only(queries, private_profile, mailoutbox)


@pytest.fixture
def private_profile(cedar_dataset: CedarDataset) -> _PrivateProfile:
    """Prepare Maria's real token while Bob remains an anonymous visitor.

    :param cedar_dataset: Real Cedar baseline. Example: includes account mrodriguez.
    :return: Pre-request user and token rows. Example: rows including Maria's token.
    :raises AssertionError: If an account exists for Bob or Maria has no token key.
    """
    assert not User.objects.filter(
        Q(username__iexact="bob")
        | Q(first_name__iexact="Bob", last_name__iexact="Carter")
    ).exists()
    maria = cedar_dataset.users_by_username["mrodriguez"]
    token, _ = Token.objects.get_or_create(user=maria)
    if not token.key:
        raise AssertionError("Maria's test token is missing a key")
    summary = ExpertProfile.objects.get(user=maria).contribution_summary
    assert bool(summary), "Cedar must provide a stored profile summary"
    return _PrivateProfile(token.key, summary, _snapshot_accounts())


def _snapshot_accounts() -> tuple[tuple[tuple[object, ...], ...], ...]:
    """Capture complete account and token rows without rendering them.

    :return: Ordered row snapshots. Example: snapshots before the guest GET.
    """
    return tuple(
        tuple(model.objects.order_by("pk").values_list()) for model in (User, Token)
    )


def _assert_login_location(location: str) -> None:
    """Check the precise local sign-in destination and single next value.

    :param location: Actual redirect URL. Example: /auth/user/login/?next=/auth/user/profile/.
    :return: None. Example: when the path and next match.
    :raises AssertionError: If the redirect target differs.
    """
    target = urlsplit(location)
    if (
        target.scheme
        or target.netloc
        or target.fragment
        or target.path != reverse("login")
        or parse_qs(target.query, keep_blank_values=True)
        != {"next": [_OWN_PROFILE_PATH]}
    ):
        raise AssertionError("The redirect did not preserve the exact login target")


def _assert_private_profile_absent(
    response: HttpResponse, state: _PrivateProfile
) -> set[str]:
    """Reject private rendering, account controls and Maria's actual token.

    :param response: Real HTTP response. Example: the unfollowed 302.
    :param state: Test account snapshot. Example: Maria's persisted key.
    :return: Rendered IDs. Example: an empty set for an empty redirect body.
    :raises AssertionError: If private content appears anywhere in the response.
    """
    body = unescape(response.content.decode(response.charset))
    if any(
        state.maria_key in value
        for value in (body, response.cookies.output(), *response.headers.values())
    ):
        raise AssertionError("The guest response exposed a private API token")
    if state.summary in body:
        raise AssertionError("The guest response rendered the stored profile summary")
    assert all(template.name != _PROFILE_TEMPLATE for template in response.templates)
    if not response.content.strip():
        return set()
    hooks = {
        value
        for node in _walk_elements(_parse_root(response.content))
        for name, value in node.attributes
        if name in {"id", "data-testid"}
    }
    assert hooks.isdisjoint(_PRIVATE_TEST_IDS), (
        "The guest response has private controls"
    )
    return hooks


def _assert_read_only(
    queries: CaptureQueriesContext,
    state: _PrivateProfile,
    mailoutbox: list[EmailMessage],
) -> None:
    """Reject model writes, account/token changes and outgoing mail.

    :param queries: SQL from the real guest request. Example: no SQL on a redirect.
    :param state: ORM state before the request. Example: prepared test accounts.
    :param mailoutbox: Test outbox. Example: [] after the request.
    :return: None. Example: no writes or mail were observed.
    :raises AssertionError: If the request mutates persisted state or sends mail.
    """
    for entry in queries.captured_queries:
        if entry["sql"].split(maxsplit=1)[0].upper() not in _READ_ONLY_SQL:
            raise AssertionError("The guest request issued a mutating SQL statement")
    if _snapshot_accounts() != state.accounts:
        raise AssertionError("The guest request changed account or token rows")
    assert len(mailoutbox) == 0, "The guest request sent mail"
