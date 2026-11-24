"""Real server contracts complementary to guest clipboard certification."""

from __future__ import annotations

import re
from html import unescape
from http import HTTPStatus
from uuid import UUID

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.db.models import Sum
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
from pytest import LogCaptureFixture

from methodology.models import ExpertProfile, KarmaAward
from methodology.services.copy_prompt_service import CopyPromptService
from tests.support.experts_data import CedarDataset
from tests.support.experts_html import find_by_test_id
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

_CEDAR_ACTIVITY_ID = 6203
_CEDAR_PROMPT_ID = f"copy-prompt-text-activity-{_CEDAR_ACTIVITY_ID}"
# Django's semantic HTML parser normalizes the prompt's Markdown whitespace.
_CEDAR_PROMPT_TEXTAREA = re.compile(
    rf'<textarea\b[^>]*\bdata-testid="{_CEDAR_PROMPT_ID}"[^>]*>(.*?)</textarea>',
    re.DOTALL,
)
_MIKE_BASELINE_POINTS = 12_450
_EVENT_ID = UUID("ef208c00-5ee4-4c69-9284-91d6b804d157")
_REQUEST_ID = "cedar-guest-copy-receipt"
_RECEIPT_VIEW = "copy_success_receipt"
_RECEIPT_LOGGERS = ("methodology.karma_views", "methodology.services.karma_service")


def _csrf_guest_client() -> Client:
    """Get a real CSRF cookie without signing in or creating a session.

    :return: Anonymous enforcing client. Example: client after a login form GET.
    :raises AssertionError: If the form fails or establishes an authenticated session.
    """
    client = Client(enforce_csrf_checks=True)
    login_form = client.get(reverse("login"))
    assert login_form.status_code == HTTPStatus.OK
    assert not login_form.wsgi_request.user.is_authenticated
    assert settings.CSRF_COOKIE_NAME in login_form.cookies
    assert settings.SESSION_COOKIE_NAME not in client.cookies
    return client


def _post_guest_receipt(client: Client) -> HttpResponse:
    """Post a CSRF-valid, well-formed activity report as a guest.

    :param client: Anonymous enforcing client with its real CSRF cookie.
    :return: Receipt route response. Example: safe JSON with status 401.
    :raises KeyError: If the CSRF cookie is missing.
    """
    return client.post(
        reverse("karma_copy_receipt"),
        data={
            "entity_type": "activity",
            "entity_id": _CEDAR_ACTIVITY_ID,
            "event_identity": str(_EVENT_ID),
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value,
        HTTP_X_REQUEST_ID=_REQUEST_ID,
    )


def _guest_state_snapshot() -> dict[str, list[dict[str, object]]]:
    """Read complete, ordered account, profile, award, and session rows.

    :return: Table-to-rows mapping. Example: a Session table with no rows.
    """
    return {
        model.__name__: list(model.objects.order_by("pk").values())
        for model in (User, ExpertProfile, KarmaAward, Session)
    }


@pytest.mark.django_db
def test_guest_activity_with_initial_get_renders_full_prompt_without_awards(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Certify the server-rendered anonymous activity detail.

    :param client: Anonymous Django client. Example: unauthenticated activity6203 GET.
    :param cedar_dataset: Real Cedar fixture. Example: Mike's public released activity.
    :return: None after verifying the full prompt, read-only controls and unchanged rows.
    :raises AssertionError: If access, prompt controls, account or Karma state differs.
    """
    activity = cedar_dataset.activities_by_pk[_CEDAR_ACTIVITY_ID]
    mike = cedar_dataset.users_by_username["mchen"]
    playbook = activity.workflow.playbook
    assert playbook.author_id == mike.pk
    assert (playbook.visibility, playbook.status) == ("public", "released")
    assert not User.objects.filter(username__iexact="bob").exists()
    points = mike.karma_awards.aggregate(points=Sum("points"))
    assert points["points"] == _MIKE_BASELINE_POINTS
    before = _guest_state_snapshot()
    route = (playbook.pk, activity.workflow_id, activity.pk)
    response = client.get(reverse("activity_detail", args=route))
    assert response.status_code == HTTPStatus.OK
    assert not response.wsgi_request.user.is_authenticated
    assert settings.SESSION_COOKIE_NAME not in client.cookies
    html = response.content.decode(response.charset)
    button = find_by_test_id(html, "copy-prompt-btn")
    button_attrs = dict(button.attributes)
    assert button.name == "button" and "data-copy-prompt-trigger" in button_attrs
    assert "disabled" not in button_attrs
    assert button_attrs.get("aria-disabled") != "true"
    find_by_test_id(html, "guest-auth-banner")
    assert 'data-testid="edit-btn"' not in html
    prompt = find_by_test_id(html, _CEDAR_PROMPT_ID)
    assert "visually-hidden" in dict(prompt.attributes).get("class", "").split()
    source = _CEDAR_PROMPT_TEXTAREA.search(html)
    assert source is not None, "Expected the hidden activity prompt textarea."
    if unescape(source[1]) != CopyPromptService.build_activity_prompt(activity):
        pytest.fail("The activity textarea does not contain the complete prompt.")
    if _guest_state_snapshot() != before:
        pytest.fail("Guest GET changed account, profile, award or session rows.")


@pytest.mark.django_db
def test_guest_copy_receipt_with_anonymous_post_rejects_without_awards(
    cedar_dataset: CedarDataset,
) -> None:
    """Reject a valid-shaped anonymous receipt through S36's real boundary.

    :param cedar_dataset: Real Cedar records. Example: Mike's activity 6203.
    :return: None after non-redirect rejection and unchanged DB checks.
    :raises AssertionError: If anonymous reporting succeeds or creates domain state.
    """
    mike = cedar_dataset.users_by_username["mchen"]
    assert mike.karma_awards.aggregate(points=Sum("points"))["points"] == (
        _MIKE_BASELINE_POINTS
    )
    assert not User.objects.filter(username__iexact="bob").exists()
    before = _guest_state_snapshot()
    client = _csrf_guest_client()

    response = _post_guest_receipt(client)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["Content-Type"] == "application/json"
    assert response.json() == {"status": "rejected", "reason": "unauthenticated"}
    assert "Location" not in response.headers
    assert not response.wsgi_request.user.is_authenticated
    assert settings.SESSION_COOKIE_NAME not in response.wsgi_request.COOKIES
    assert settings.SESSION_COOKIE_NAME not in client.cookies
    assert mike.karma_awards.aggregate(points=Sum("points"))["points"] == (
        _MIKE_BASELINE_POINTS
    )
    if _guest_state_snapshot() != before:
        pytest.fail("Guest receipt changed account, profile, award or session rows.")


@pytest.mark.django_db
def test_guest_copy_receipt_log_story_reject(
    cedar_dataset: CedarDataset, caplog: LogCaptureFixture
) -> None:
    """Certify S36's safe unauthenticated rejection beat with real HTTP.

    :param cedar_dataset: Real Cedar records. Example: Mike's activity 6203.
    :param caplog: INFO log capture. Example: request ID and unauthenticated branch.
    :return: None after assert_log_story and sensitive-content exclusion checks.
    :raises AssertionError: If rejection is unobservable or contains sensitive data.
    """
    assert _CEDAR_ACTIVITY_ID in cedar_dataset.activities_by_pk
    client = _csrf_guest_client()
    trace = f"request_id={_REQUEST_ID}"
    with capture_experts_logs(caplog, _RECEIPT_LOGGERS):
        response = _post_guest_receipt(client)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["X-Request-ID"] == _REQUEST_ID
    assert_log_story(
        caplog,
        where=_RECEIPT_VIEW,
        beats={"branch": ("| branch |", trace, "reason=unauthenticated", "awards=0")},
    )
    # The safe allowlist excludes prompt text, account data and request credentials.
    messages = [
        record.getMessage()
        for record in caplog.records
        if record.name in _RECEIPT_LOGGERS
    ]
    if messages != [
        f"{_RECEIPT_VIEW} | branch | {trace} reason=unauthenticated awards=0"
    ]:
        pytest.fail("Guest receipt logs contained fields beyond the rejection story.")
