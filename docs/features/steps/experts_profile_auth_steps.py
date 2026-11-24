"""Unique S13 assertions; shared actor/request bindings belong elsewhere."""

from __future__ import annotations

from html import unescape
from http import HTTPStatus
from urllib.parse import parse_qs, urlsplit

from behave import then
from behave.runner import Context
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import User
from django.core import mail
from django.db import connection
from django.http import HttpResponse
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.authtoken.models import Token

from methodology.models import ExpertProfile
from tests.support.experts_data import CedarDataset
from tests.support.experts_html import _parse_root, _walk_elements, find_by_test_id

_OWN_PROFILE_PATH = "/auth/user/profile/"
_PROFILE_TEMPLATE = "accounts/profile.html"
_LOGIN_TEMPLATE = "accounts/login.html"
_LOGIN_FORM_ID = "login-form"
_PRIVATE_HOOK_PREFIXES = ("profile-", "nav-view-profile")
_READ_ONLY_SQL = frozenset({"SELECT", "SAVEPOINT", "RELEASE", "ROLLBACK"})


@then("he is redirected to the login page")
def assert_own_profile_login_redirect(context: Context) -> None:
    """Check the unfollowed own-profile response's precise login handoff.

    :param context: Real AT context. Example: context.response.status_code == 302.
    :return: None. Example: None after exact Location/next assertions.
    :raises AssertionError: If profile request, redirect or next differs.
    """
    _own_profile_login_location(context.response)


@then("no own-profile Karma or account token controls are shown")
def assert_own_profile_controls_absent(context: Context) -> None:
    """Check redirect and login HTML without granting an authenticated session.

    :param context: Real Cedar AT context. Example: context.cedar_dataset.
    :return: None. Example: None after private-control absence assertions.
    :raises AssertionError: If controls, token secrets or an account appear.
    """
    original: HttpResponse = context.response
    visitor: Client = context.client
    location = _own_profile_login_location(original)
    private_values = _cedar_private_profile_values(context.cedar_dataset)
    before = _snapshot_account_rows()
    assert _LOGIN_FORM_ID not in _assert_private_profile_absent(
        original, private_values
    )

    # Measure the same anonymous profile GET under SQL capture because the shared
    # path binding has already issued the original request before this assertion.
    with CaptureQueriesContext(connection) as queries:
        replay = Client().get(_OWN_PROFILE_PATH, follow=False)
        login = visitor.get(location, follow=False)

    assert _own_profile_login_location(replay) == location
    assert _LOGIN_FORM_ID not in _assert_private_profile_absent(replay, private_values)
    _assert_anonymous_login_form(login, private_values)
    _assert_read_only(queries)
    if _snapshot_account_rows() != before:
        raise AssertionError("Guest requests changed account or token rows")


def _own_profile_login_location(response: HttpResponse) -> str:
    """Assert the exact local login handoff from an anonymous profile GET.

    :param response: Original Django-client response. Example: unfollowed HTTP 302.
    :return: Checked Location. Example: /auth/user/login/?next=/auth/user/profile/.
    :raises AssertionError: If request, redirect target or anonymity differs.
    """
    request = response.wsgi_request
    assert request.method == "GET" and request.get_full_path() == _OWN_PROFILE_PATH
    assert not request.user.is_authenticated and SESSION_KEY not in request.session
    assert response.status_code == HTTPStatus.FOUND
    location = response.headers.get("Location", "")
    login_path = reverse("login")
    assert location.startswith(f"{login_path}?")
    target = urlsplit(location)
    assert not (target.scheme or target.netloc or target.fragment)
    assert target.path == login_path
    assert parse_qs(target.query, keep_blank_values=True) == {
        "next": [_OWN_PROFILE_PATH]
    }
    return location


def _cedar_private_profile_values(dataset: CedarDataset) -> tuple[str, ...]:
    """Use actual persisted keys and contribution prose as disclosure probes.

    :param dataset: Real Cedar background. Example: seeded Maria account and token.
    :return: Private strings to check without logging them. Example: one key and summary.
    :raises AssertionError: If the original request created an account or token.
    """
    expected_users = set(dataset.user_ids.values())
    assert set(User.objects.values_list("pk", flat=True)) == expected_users, (
        "Guest request changed the Cedar account set"
    )
    maria = dataset.users_by_username["mrodriguez"]
    token_rows = dict(Token.objects.values_list("user_id", "key"))
    assert set(token_rows) == {maria.pk}, "Expected only Maria's seeded API token"
    summary = ExpertProfile.objects.get(user=maria).contribution_summary
    assert token_rows[maria.pk] and summary, "Missing Cedar privacy probes"
    return (*token_rows.values(), summary)


def _snapshot_account_rows() -> tuple[tuple[tuple[object, ...], ...], ...]:
    """Capture full account and token rows without displaying their values.

    :return: Ordered snapshots. Example: account and token rows before following.
    """
    return tuple(
        tuple(model.objects.order_by("pk").values_list()) for model in (User, Token)
    )


def _assert_private_profile_absent(
    response: HttpResponse, private_values: tuple[str, ...]
) -> set[str]:
    """Reject private templates, own-profile hooks and actual stored values.

    :param response: Real guest response. Example: the unfollowed redirect.
    :param private_values: Fixture probes. Example: an existing token and summary.
    :return: Actual element IDs. Example: an empty set for an empty redirect.
    :raises AssertionError: If a private control, token or summary is present.
    """
    assert _PROFILE_TEMPLATE not in {template.name for template in response.templates}
    surface = (
        response.content.decode(response.charset),
        *response.headers.values(),
        response.cookies.output(),
    )
    if any(
        private in unescape(value) for value in surface for private in private_values
    ):
        raise AssertionError("The guest response exposed private profile data")
    if not response.content.strip():
        return set()
    hooks = {
        value
        for node in _walk_elements(_parse_root(response.content))
        for name, value in node.attributes
        if name in {"id", "data-testid"}
    }
    assert not any(hook.startswith(_PRIVATE_HOOK_PREFIXES) for hook in hooks), (
        "The guest response rendered an own-profile control"
    )
    return hooks


def _assert_anonymous_login_form(
    response: HttpResponse, private_values: tuple[str, ...]
) -> None:
    """Require a successful login form after exactly one actual handoff.

    :param response: Unfollowed GET of the original Location. Example: HTTP 200.
    :param private_values: Fixture probes. Example: a stored API token and summary.
    :return: None. Example: the login form exists and the visitor is anonymous.
    :raises AssertionError: If login delivery, privacy or anonymity differs.
    """
    request = response.wsgi_request
    assert response.status_code == HTTPStatus.OK
    assert request.method == "GET" and request.path == reverse("login")
    assert dict(request.GET) == {"next": [_OWN_PROFILE_PATH]}
    assert not request.user.is_authenticated and SESSION_KEY not in request.session
    assert _LOGIN_TEMPLATE in {template.name for template in response.templates}
    _assert_private_profile_absent(response, private_values)
    assert find_by_test_id(response.content, _LOGIN_FORM_ID).name == "form"


def _assert_read_only(queries: CaptureQueriesContext) -> None:
    """Check request SQL and mail without showing statement or message contents.

    :param queries: SQL captured from the real requests. Example: read-only SELECTs.
    :return: None. Example: no ledger/model writes or mail during rejection.
    :raises AssertionError: If either request issues a write or sends mail.
    """
    for query in queries.captured_queries:
        if query["sql"].split(maxsplit=1)[0].upper() not in _READ_ONLY_SQL:
            raise AssertionError("Guest requests issued a mutating SQL statement")
    if mail.outbox:
        raise AssertionError("Guest requests sent mail")
