"""Real owner-profile regression for the shared live numeric fallback."""

from __future__ import annotations

import hashlib
from http import HTTPStatus

import pytest
from django.apps import apps
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.core import mail
from django.db import connection
from django.http import HttpResponse
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token

from methodology.models import EventChannel, ExpertProfile, KarmaAward, Playbook
from tests.support.experts_data import CedarDataset
from tests.support.experts_html import element_text, find_by_test_id
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

pytestmark = pytest.mark.django_db
_MIKE = "mchen"
_FALLBACK = "2 released playbooks · 47 copies"
_REQUEST_ID = "s10-numeric-fallback-repair"
_READ_ONLY_SQL = {"SELECT", "BEGIN", "COMMIT", "SAVEPOINT", "RELEASE"}
_CONTEXT_LOG = "accounts.views._profile_contribution_context"


@pytest.mark.parametrize("summary", ["", " \n\t "])
def test_profile_numeric_fallback_with_missing_prose_reads_live_counts(
    client: Client, cedar_dataset: CedarDataset, summary: str
) -> None:
    """Render exact live fallback for empty and whitespace-only stored text.

    :param client: Real request client. Example: Client().
    :param cedar_dataset: Owned Cedar database. Example: Mike with two releases.
    :param summary: Supported empty text variant. Example: empty string.
    :return: None. Example: exact2/47 without summary controls or side effects.
    :raises AssertionError: If numeric text is absent, stale or read-side mutating.
    """
    mike = cedar_dataset.users_by_username[_MIKE]
    ExpertProfile.objects.filter(user=mike).update(contribution_summary=summary)
    _authenticate_owner(client, mike)
    response = _read_profile_unchanged(client)
    _assert_numeric_only(response, _FALLBACK)
    assert ExpertProfile.objects.get(user=mike).contribution_summary == summary


def test_profile_numeric_fallback_with_row_changes_refreshes_next_get(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Refresh from changed public release and eligible GUI author award rows.

    :param client: Real request client. Example: Mike's account session.
    :param cedar_dataset: Owned Cedar rows. Example: baseline2/47.
    :return: None. Example: changed1/48 with empty prose/history unchanged.
    :raises AssertionError: If live reads use cached counts or regenerate prose.
    """
    mike = cedar_dataset.users_by_username[_MIKE]
    _authenticate_owner(client, mike)
    _assert_numeric_only(_read_profile_unchanged(client), _FALLBACK)
    book = Playbook.objects.filter(
        author=mike, status="released", visibility="public"
    ).first()
    assert book is not None
    Playbook.objects.filter(pk=book.pk).update(visibility="private")
    KarmaAward.objects.create(
        recipient=mike,
        event_identity="s10-repair:additional-gui-author-copy",
        source_kind=KarmaAward.SourceKind.CONSUMPTION,
        event_channel=EventChannel.GUI_COPY,
        points=5,
        category="development",
        occurred_at=timezone.now(),
    )
    _assert_numeric_only(
        _read_profile_unchanged(client), "1 released playbook · 48 copies"
    )
    assert ExpertProfile.objects.get(user=mike).contribution_summary == ""


def test_profile_numeric_fallback_with_stored_prose_preserves_existing_contract(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Preserve Maria's exact existing summary context and disclosure markup.

    :param client: Real request client. Example: Maria's signed-in session.
    :param cedar_dataset: Real owned baseline. Example: nine-sentence Maria.
    :return: None. Example: complete stored text and unchanged account controls.
    :raises AssertionError: If fallback replaces or changes stored prose/controls.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    summary = ExpertProfile.objects.get(user=maria).contribution_summary
    assert summary and summary.endswith(
        "availability and project fit still require a conversation."
    )
    _authenticate_owner(client, maria)
    response = _read_profile_unchanged(client)
    contributions = response.context["contributions"]
    assert contributions["summary"] == summary
    assert "numeric_fallback" not in contributions
    assert element_text(
        find_by_test_id(response.content, "profile-contribution-summary")
    ) == " ".join(summary.split())
    toggle = find_by_test_id(response.content, "profile-summary-toggle")
    assert ("aria-controls", "own-contribution-summary") in toggle.attributes
    assert element_text(toggle) == "Show more"
    for hook in ("profile-token-field", "profile-edit-btn", "profile-playbooks-table"):
        find_by_test_id(response.content, hook)
    assert b'data-testid="profile-numeric-fallback"' not in response.content


def test_profile_numeric_fallback_with_absent_profile_does_not_create_one(
    client: Client,
) -> None:
    """Keep an unscored account usable without creating summary state.

    :param client: Real request client. Example: new account without ExpertProfile.
    :return: None. Example: zero releases/copies and no new profile or generation.
    :raises AssertionError: If GET creates a profile or omits neutral live counts.
    """
    owner = User.objects.create_user(username="s10-fallback-without-profile")
    assert not ExpertProfile.objects.filter(user=owner).exists()
    _authenticate_owner(client, owner)
    response = _read_profile_unchanged(client)
    _assert_numeric_only(response, "0 released playbooks · 0 copies")
    assert not ExpertProfile.objects.filter(user=owner).exists()


def test_profile_numeric_fallback_log_story_happy(
    client: Client,
    cedar_dataset: CedarDataset,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Prove the missing-prose branch stays owner-bound and safely correlated.

    :param client: Real request client. Example: Mike querying another username.
    :param cedar_dataset: Owned Cedar rows. Example: Mike and Maria.
    :param caplog: Real log capture. Example: INFO profile context beats.
    :return: None. Example: entry/missing/exit without secret or prose logging.
    :raises AssertionError: If the subject changes or a declared log beat is absent.
    """
    mike = cedar_dataset.users_by_username[_MIKE]
    _authenticate_owner(client, mike)
    with capture_experts_logs(caplog, ("accounts.views",)):
        response = _read_profile_unchanged(client, "?username=mrodriguez")
    _assert_numeric_only(response, _FALLBACK)
    assert response.context["username"] == _MIKE
    _assert_missing_branch(caplog, mike.pk)
    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert "@" not in messages
    assert Token.objects.get(user=mike).key not in messages
    for profile in ExpertProfile.objects.exclude(contribution_summary=""):
        assert profile.contribution_summary not in messages


def _authenticate_owner(client: Client, owner: User) -> None:
    """Establish existing account state before the read observation window.

    :param client: Real Django client. Example: Client().
    :param owner: Persisted request owner. Example: Cedar Mike.
    :return: None. Example: owner session and stable API token already exist.
    :raises AssertionError: If owner is unsaved.
    """
    assert owner.pk and not owner._state.adding
    Token.objects.get_or_create(user=owner)
    client.force_login(owner)


def _state_fingerprint() -> str:
    """Hash all domain/M2M rows, session identity and captured mail privately.

    :return: Private-safe full-state digest. Example: equal hashes before/after GET.
    :raises RuntimeError: If the owned test database cannot be queried.
    """
    models = sorted(
        apps.get_models(include_auto_created=True), key=lambda model: model._meta.label
    )
    rows = [
        tuple(model.objects.order_by("pk").values_list())
        for model in models
        if model is not Session
    ]
    rows.append(
        tuple(
            (session.pk, session.get_decoded())
            for session in Session.objects.order_by("pk")
        )
    )
    rows.append(tuple(message.__dict__ for message in getattr(mail, "outbox", ())))
    return hashlib.sha256(repr(rows).encode()).hexdigest()


def _read_profile_unchanged(client: Client, query: str = "") -> HttpResponse:
    """Require owner GET to preserve all state and queue no post-commit work.

    :param client: Prepared real owner client. Example: Mike-authenticated Client().
    :param query: Optional subject-tampering query. Example: ?username=mrodriguez.
    :return: Successful real profile response. Example: HTTP200 own account.
    :raises AssertionError: If GET mutates domain/mail/session identity or queues work.
    """
    before = _state_fingerprint()
    with (
        TestCase.captureOnCommitCallbacks() as callbacks,
        CaptureQueriesContext(connection) as queries,
    ):
        response = client.get(
            reverse("profile") + query, headers={"X-Request-ID": _REQUEST_ID}
        )
    assert response.status_code == HTTPStatus.OK
    assert _state_fingerprint() == before
    assert not callbacks
    for query_record in queries:
        sql = query_record["sql"].lstrip().upper()
        assert sql.split(maxsplit=1)[0] in _READ_ONLY_SQL or sql.startswith(
            'UPDATE "DJANGO_SESSION" SET '
        )
    return response


def _assert_numeric_only(response: HttpResponse, expected: str) -> None:
    """Require exact distinct numeric paragraph and no fabricated summary control.

    :param response: Actual owner HTML/context. Example: Mike's HTTP200 profile.
    :param expected: Independent exact count sentence. Example: baseline2/47.
    :return: None. Example: a semantic numeric paragraph without expansion.
    :raises AssertionError: If fallback, empty storage projection or controls differ.
    """
    fallback = find_by_test_id(response.content, "profile-numeric-fallback")
    assert fallback.name == "p" and element_text(fallback) == expected
    assert response.context["contributions"]["numeric_fallback"] == expected
    assert response.context["contributions"]["summary"] == ""
    for hook in ("profile-contribution-summary", "profile-summary-toggle"):
        assert f'data-testid="{hook}"'.encode() not in response.content


def _assert_missing_branch(caplog: pytest.LogCaptureFixture, owner_id: int) -> None:
    """Match existing safe owner profile entry, missing branch and exit logs.

    :param caplog: Captured real INFO records. Example: accounts.views events.
    :param owner_id: Persisted authenticated subject. Example: Mike's primary key.
    :return: None. Example: one request's complete declared existing story.
    :raises AssertionError: If correlation, owner or missing-prose branch is absent.
    """
    correlation = f"request_id={_REQUEST_ID}"
    assert_log_story(
        caplog,
        where=_CONTEXT_LOG,
        beats={
            "entry": ("beat=entry", f"actor_user_id={owner_id}", correlation),
            "missing": (
                "beat=branch",
                "summary_state=missing",
                f"subject_user_id={owner_id}",
                correlation,
            ),
            "exit": ("beat=exit", "total_points=12450", "source_count=4", correlation),
        },
    )
