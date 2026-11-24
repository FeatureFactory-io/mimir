from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime

import pytest
from _pytest.logging import LogCaptureFixture
from django.apps import apps
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from methodology.models import PipChange
from methodology.models import ProcessImprovementProposal as PIP
from methodology.services.experts_service import ExpertsService
from methodology.services.karma_service import KarmaService
from tests.support.experts_data import (
    CedarDataset,
    create_nonaccepted_pip_case,
    load_cedar_baseline,
)
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

DomainState = tuple[tuple[str, int, str], ...]
_POLICY_LOGGER = "methodology.services.karma_service"
_EXPECTED_SKIP_BEATS = 3
_ADMIN_LOGGER = "methodology.services.pip_admin_service"
_REJECTION_NOTE = "Rejected after checking the published baseline"
_PIP_DECISION_FIELDS = frozenset(
    ("status", "decided_at", "status_changed_at", "updated_at")
)
_CHANGE_DECISION_FIELDS = frozenset(("admin_decision", "admin_note"))
_SESSION_WRITE_FIELDS = frozenset(("session_data", "expire_date"))


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
    dataset = load_cedar_baseline()
    pip = create_nonaccepted_pip_case(dataset, status)
    before = _protected_nonaccepted_state()
    correlation = f"s35_nonaccepted:{status}"
    caplog.clear()
    with capture_experts_logs(caplog, (_POLICY_LOGGER,)):
        outcomes = KarmaService.award_accepted_changes(
            pip=pip, correlation_id=correlation
        )
    assert outcomes == ()
    assert _protected_nonaccepted_state() == before
    _assert_nonaccepted_projection(dataset, pip, status)
    _assert_nonaccepted_log_story(caplog, pip, correlation)
    with pytest.raises(ValueError, match="five nonaccepted states"):
        create_nonaccepted_pip_case(dataset, PIP.STATUS_ACCEPTED)
    assert _protected_nonaccepted_state() == before


@pytest.mark.django_db
def test_finalize_pip_with_rejected_only_preserves_karma_content_and_version(
    client: Client,
    mailoutbox: list[EmailMessage],
    django_capture_on_commit_callbacks: Callable[
        ..., AbstractContextManager[list[Callable[[], None]]]
    ],
) -> None:
    """Prove real staff rejection preserves content/version/awards and sends mail.

    :param client: Real HTTP client. Example: logged-in staff mchen.
    :param mailoutbox: Actual locmem deliveries. Example: one rejection notice.
    :param django_capture_on_commit_callbacks: Callback capture fixture.
        Example: execute=True delivers locmem rejection notification.
    :return: None. Example: rejected PIP, version 2.0 and Maria 8200.
    :raises AssertionError: If persisted decision or permitted effects differ."""
    dataset = load_cedar_baseline()
    pip = create_nonaccepted_pip_case(dataset, PIP.STATUS_REVIEWED)
    reviewer = dataset.users_by_username["mchen"]
    client.force_login(reviewer)
    before = _protected_rejection_state(pip, client)
    started = timezone.now()
    assert not mailoutbox
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = _post_rejected_finalization(client, pip)
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("pip_detail", args=[pip.pk])
    assert len(callbacks) == 1
    assert client.session["_auth_user_id"] == str(reviewer.pk)
    _assert_rejected_finalization(dataset, pip, before, started, client)
    _assert_rejection_mail(mailoutbox, pip)


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
    dataset = load_cedar_baseline()
    pip = create_nonaccepted_pip_case(dataset, PIP.STATUS_REVIEWED)
    client.force_login(dataset.users_by_username["mchen"])
    before = _protected_rejection_state(pip, client)
    started = timezone.now()
    caplog.clear()
    with capture_experts_logs(caplog, (_POLICY_LOGGER, _ADMIN_LOGGER)):
        response = _post_rejected_finalization(client, pip)
    assert response.status_code == 302
    _assert_rejected_finalization(dataset, pip, before, started, client)
    _assert_nonaccepted_log_story(caplog, pip, f"pip_finalize:{pip.pk}")
    forbidden = (pip.title, pip.summary, pip.changes.get().content, _REJECTION_NOTE)
    assert all(value not in caplog.text for value in forbidden)
    assert all(
        email not in caplog.text
        for email in pip.created_by.__class__.objects.values_list("email", flat=True)
        if email
    )


def _protected_nonaccepted_state() -> DomainState:
    """Snapshot every real row, including implicit relationships and original awards.

    :return: Model/count/SHA256 tuples, without private values. Example: immutable ledger digest.
    :raises DatabaseError: If the actual database cannot be read.
    """
    snapshots: list[tuple[str, int, str]] = []
    for model in sorted(
        apps.get_models(include_auto_created=True),
        key=lambda model: model._meta.label_lower,
    ):
        rows = list(model.objects.order_by("pk").values())
        payload = json.dumps(rows, sort_keys=True, default=str).encode()
        snapshots.append(
            (model._meta.label_lower, len(rows), hashlib.sha256(payload).hexdigest())
        )
    return tuple(snapshots)


def _assert_nonaccepted_projection(
    dataset: CedarDataset, pip: PIP, status: str
) -> None:
    """Prove independently stated totals and the exact persisted eligibility boundary.

    :param dataset: Real Cedar rows. Example: Maria account and Hana6106.
    :param pip: Built persisted proposal. Example: reviewed ADD Activity.
    :param status: Contracted state. Example: "processing_galdr".
    :return: None. Example:8200/7200/1000 remain unchanged.
    :raises AssertionError: If scores or fixture status/timestamps/choices differ.
    """
    projection = ExpertsService().project_user(
        dataset.users_by_username["mrodriguez"].pk
    )
    assert projection.total_points == 8200
    assert projection.primary_category == "design"
    assert dict(projection.category_points) == {"design": 7200, "development": 1000}
    pip.refresh_from_db()
    assert pip.status == status and pip.playbook.version == 2
    assert (pip.decided_at is not None) == (status == PIP.STATUS_REJECTED)
    assert (pip.submitted_at is not None) == (status != PIP.STATUS_DRAFT)
    assert (pip.reviewed_at is not None) == (
        status in (PIP.STATUS_REVIEWED, PIP.STATUS_REJECTED)
    )
    if status == PIP.STATUS_REVIEWED:
        change = pip.changes.get()
        assert change.galdr_recommendation == PipChange.GALDR_ACCEPT
        assert change.admin_decision == PipChange.ADMIN_ACCEPT
    if status == PIP.STATUS_REJECTED:
        assert all(
            change.admin_decision == PipChange.ADMIN_REJECT
            for change in pip.changes.all()
        )


def _assert_nonaccepted_log_story(
    caplog: LogCaptureFixture, pip: PIP, correlation: str
) -> None:
    """Check safe literal beats from the actual S32 eligibility branch.

    :param caplog: Actual policy log capture. Example: entry, branch and exit records.
    :param pip: Real ineligible proposal. Example: rejected PIP42.
    :param correlation: Expected safe identifier. Example: "s35_nonaccepted:rejected".
    :return: None. Example: no award-success beat or private prose appears.
    :raises AssertionError: If correlation, zero outcomes or privacy differ.
    """
    trace = (f"pip_id={pip.pk}", f"correlation_id={correlation}")
    assert_log_story(
        caplog,
        where="KarmaService.award_accepted_changes",
        beats={
            "entry": ("| entry |", *trace),
            "branch": ("| branch |", "reason=decision_ineligible", *trace),
            "exit": ("| exit |", "created_count=0", "existing_count=0", *trace),
        },
    )
    messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == _POLICY_LOGGER
    ]
    assert len(messages) == _EXPECTED_SKIP_BEATS
    private = (
        pip.title,
        pip.summary,
        *(change.content for change in pip.changes.all()),
        *pip.created_by.__class__.objects.values_list("email", flat=True),
    )
    assert all(
        not value or all(value not in message for message in messages)
        for value in private
    )
    assert not any(
        "persist_awards" in message or "| error |" in message for message in messages
    )


def _protected_rejection_state(pip: PIP, client: Client) -> DomainState:
    """Hash every real row while permitting only the current review and session writes.

    :param pip: Proposal whose real decision may change. Example: reviewed PIP42.
    :param client: Real staff session. Example: Mike authenticated before snapshot.
    :return: Immutable full-model/M2M digests. Example: identical ledger and content hashes.
    :raises DatabaseError: If the actual database cannot be read.
    """
    snapshots: list[tuple[str, int, str]] = []
    session_key = client.session.session_key
    assert session_key, "Expected an existing authenticated staff session"
    for model in sorted(
        apps.get_models(include_auto_created=True),
        key=lambda item: item._meta.label_lower,
    ):
        label = model._meta.label_lower
        rows = list(model.objects.order_by("pk").values())
        for row in rows:
            allowed = frozenset()
            if label == PIP._meta.label_lower and row["id"] == pip.pk:
                allowed = _PIP_DECISION_FIELDS
            elif label == PipChange._meta.label_lower and row["pip_id"] == pip.pk:
                allowed = _CHANGE_DECISION_FIELDS
            elif label == "sessions.session" and row["session_key"] == session_key:
                allowed = _SESSION_WRITE_FIELDS
            for field in allowed:
                row.pop(field)
        payload = json.dumps(rows, sort_keys=True, default=str).encode()
        snapshots.append((label, len(rows), hashlib.sha256(payload).hexdigest()))
    return tuple(snapshots)


def _post_rejected_finalization(client: Client, pip: PIP) -> HttpResponse:
    """Override a saved ACCEPT with the existing staff finalization HTTP action.

    :param client: Authenticated real Mike client. Example: session user mchen.
    :param pip: Actual reviewed fixture. Example: one ADD Activity with saved ACCEPT.
    :return: Actual HTTP response. Example:302 to the decided proposal.
    :raises AssertionError: If the fixture lacks its real prior saved choice.
    """
    changes = tuple(pip.changes.order_by("pk"))
    assert len(changes) == 1
    assert all(change.admin_decision == PipChange.ADMIN_ACCEPT for change in changes)
    fields = {"action": "finalize"}
    for change in changes:
        fields[f"decision_{change.pk}"] = PipChange.ADMIN_REJECT
        fields[f"note_{change.pk}"] = _REJECTION_NOTE
    return client.post(reverse("pip_admin_review", args=[pip.pk]), fields)


def _assert_rejected_finalization(
    dataset: CedarDataset,
    pip: PIP,
    before: DomainState,
    started: datetime,
    client: Client,
) -> None:
    """Verify permitted decisions/timestamps while protecting all content and awards.

    :param dataset: Actual Cedar baseline. Example: Maria8200 and Hana6106v2.0.
    :param pip: Really finalized proposal. Example: rejected PIP42.
    :param before: Pre-request normalized row digests. Example: every unchanged ledger field.
    :param started: Actual request lower time bound. Example: aware UTC instant.
    :param client: Actual staff session. Example: mchen identity survives finalization.
    :return: None. Example: rejected and notified without content/version/Karma changes.
    :raises AssertionError: If persisted decisions, timestamps or protected rows differ.
    """
    assert _protected_rejection_state(pip, client) == before
    assert client.session["_auth_user_id"] == str(dataset.users_by_username["mchen"].pk)
    _assert_nonaccepted_projection(dataset, pip, PIP.STATUS_REJECTED)
    assert pip.playbook_id == 6106 and not pip.playbook_versions.exists()
    assert timezone.is_aware(pip.decided_at)
    assert (
        started
        <= pip.decided_at
        <= pip.status_changed_at
        <= pip.updated_at
        <= timezone.now()
    )
    for change in pip.changes.all():
        assert change.admin_decision == PipChange.ADMIN_REJECT
        assert change.admin_note == _REJECTION_NOTE
        assert change.updated_at <= started
        assert not change.parent_workflow.activities.filter(name=change.name).exists()


def _assert_rejection_mail(mailoutbox: list[EmailMessage], pip: PIP) -> None:
    """Inspect one actual post-commit locmem notification rather than an external send.

    :param mailoutbox: Actual test mail deliveries. Example: one EmailMessage.
    :param pip: Rejected persisted proposal. Example: PIP42 authored by Maria.
    :return: None. Example: correct recipient, rejection and unchanged version wording.
    :raises AssertionError: If mail count, recipient or actual decision content differs.
    """
    assert len(mailoutbox) == 1
    message = mailoutbox[0]
    assert message.to == [pip.created_by.email]
    assert message.subject == f'Your PIP "{pip.title}" — Rejected ✗'
    assert "Overall: Rejected." in message.body
    assert "Decision: REJECT" in message.body
    assert f"/pips/{pip.pk}/" in message.body
    assert _REJECTION_NOTE in message.body
    assert "is now v" not in message.body
