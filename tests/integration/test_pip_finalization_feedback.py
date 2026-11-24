"""Keep staff finalization feedback consistent with the real applied decision."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from decimal import Decimal
from http import HTTPStatus
from typing import Any

import pytest
from django.contrib import messages
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from methodology.models import (
    Activity,
    EventChannel,
    KarmaAward,
    PipChange,
    PlaybookVersion,
)
from methodology.models import ProcessImprovementProposal as PIP
from methodology.services.experts_service import ExpertsService
from methodology.services.pip_service import PIPService
from tests.support.experts_data import (
    CedarDataset,
    create_nonaccepted_pip_case,
    load_cedar_baseline,
)

CaptureCallbacks = Callable[..., AbstractContextManager[list[Callable[[], None]]]]
Rows = tuple[dict[str, Any], ...]
_MARIA_BASELINE_POINTS = 8200
_MAJOR_ADD_POINTS = 500
_BASELINE_VERSION = Decimal("2.0")
_PUBLISHED_VERSION = Decimal("3.0")


@dataclass(frozen=True)
class FeedbackState:
    """Independent full-row snapshots before the actual staff request."""

    ledger: Rows
    activities: Rows
    history: Rows


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("decisions", "expected_status", "expected_message"),
    [
        pytest.param(
            (PipChange.ADMIN_REJECT,),
            PIP.STATUS_REJECTED,
            "PIP rejected — no changes applied.",
            id="rejected",
        ),
        pytest.param(
            (PipChange.ADMIN_ACCEPT,),
            PIP.STATUS_ACCEPTED,
            "PIP accepted — changes applied.",
            id="accepted",
        ),
        pytest.param(
            (PipChange.ADMIN_ACCEPT, PipChange.ADMIN_REJECT),
            PIP.STATUS_ACCEPTED_PARTIAL,
            "PIP partially accepted — changes applied.",
            id="partial",
        ),
    ],
)
def test_finalization_with_real_decisions_reports_actual_applied_outcome(
    decisions: tuple[str, ...],
    expected_status: str,
    expected_message: str,
    mailoutbox: list[EmailMessage],
    django_capture_on_commit_callbacks: CaptureCallbacks,
) -> None:
    """Display the persisted result while preserving real application and notification.

    :param decisions: Actual staff choices. Example: ("ACCEPT", "REJECT").
    :param expected_status: Independently expected terminal state. Example: "rejected".
    :param expected_message: Exact visible feedback. Example: no changes applied.
    :param mailoutbox: Actual locmem deliveries. Example: one decision notice.
    :param django_capture_on_commit_callbacks: Execute actual notification callback.
    :return: None. Example: rejected feedback agrees with unchanged v2.0 and awards.
    :raises AssertionError: If visible feedback, persisted effects or notification differ.
    """
    dataset = load_cedar_baseline()
    pip = _prepare_feedback_case(dataset, decisions)
    client = Client(enforce_csrf_checks=True)
    client.force_login(dataset.users_by_username["mchen"])
    before = _feedback_snapshot(pip)
    assert not mailoutbox
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = _post_feedback_finalization(client, pip, decisions)
    assert response.status_code == HTTPStatus.FOUND and len(callbacks) == 1
    actual_messages = tuple(messages.get_messages(response.wsgi_request))
    assert [(message.level, str(message)) for message in actual_messages] == [
        (messages.SUCCESS, expected_message)
    ]
    landing = client.get(response.headers["Location"])
    assert landing.status_code == HTTPStatus.OK
    assert expected_message in landing.content.decode()
    _assert_feedback_outcome(pip, decisions, before)
    assert pip.status == expected_status and pip.decided_at is not None
    assert len(mailoutbox) == 1 and mailoutbox[0].to == [pip.created_by.email]
    assert pip.title in mailoutbox[0].subject
    assert expected_status.split("_")[0].lower() in mailoutbox[0].body.lower()


def _prepare_feedback_case(dataset: CedarDataset, decisions: tuple[str, ...]) -> PIP:
    """Build real draft ADDs, then establish the explicit reviewed boundary fixture.

    :param dataset: Independent real Cedar rows. Example: Maria and Hana6106v2.0.
    :param decisions: One or two valid choices. Example: ("ACCEPT", "REJECT").
    :return: Real reviewed proposal with unapplied activities. Example: two ADD rows.
    :raises AssertionError: If requested choices exceed this bounded three-case matrix.
    :raises ValidationError: If the normal draft/change builder rejects fixture inputs.
    """
    assert len(decisions) in (1, 2)
    assert set(decisions) <= {PipChange.ADMIN_ACCEPT, PipChange.ADMIN_REJECT}
    pip = create_nonaccepted_pip_case(dataset, PIP.STATUS_DRAFT)
    first = pip.changes.get()
    if len(decisions) == 2:
        PIPService.add_change(
            actor=dataset.users_by_username["mrodriguez"],
            pip=pip,
            change_type=PipChange.CHANGE_ADD,
            entity_type=PipChange.ENTITY_ACTIVITY,
            name="Review feedback recovery",
            content="Retain valid form input after rejection.",
            parent_workflow_id=first.parent_workflow_id,
        )
    pip.status = PIP.STATUS_REVIEWED
    pip.submitted_at = pip.reviewed_at = timezone.now()
    pip.save(update_fields=["status", "submitted_at", "reviewed_at", "updated_at"])
    pip.changes.update(galdr_recommendation=PipChange.GALDR_ACCEPT)
    return pip


def _post_feedback_finalization(
    client: Client, pip: PIP, decisions: tuple[str, ...]
) -> HttpResponse:
    """Use the actual staff page token and normal finalization HTTP endpoint.

    :param client: Real strict-CSRF staff session. Example: authenticated Mike.
    :param pip: Reviewed proposal. Example: a normal builder-created ADD.
    :param decisions: Choices matching ordered changes. Example: ("REJECT",).
    :return: Actual response. Example:302 to the decided proposal.
    :raises AssertionError: If review rendering or the expected form token is absent.
    """
    path = reverse("pip_admin_review", args=[pip.pk])
    review = client.get(path)
    assert review.status_code == HTTPStatus.OK
    fields = {
        "action": "finalize",
        "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
    }
    changes = tuple(pip.changes.order_by("pk"))
    for change, decision in zip(changes, decisions, strict=True):
        fields[f"decision_{change.pk}"] = decision
        fields[f"note_{change.pk}"] = "Checked against the published baseline"
    return client.post(path, fields)


def _feedback_snapshot(pip: PIP) -> FeedbackState:
    """Read full real award rows and all target activity/version fields.

    :param pip: Actual target owner. Example: a proposal against Hana6106.
    :return: Complete deterministic snapshots. Example:2129 original award rows.
    :raises DatabaseError: If the owned database cannot be read.
    """
    return FeedbackState(
        ledger=tuple(KarmaAward.objects.order_by("pk").values()),
        activities=tuple(
            Activity.objects.filter(workflow__playbook_id=pip.playbook_id)
            .order_by("pk")
            .values()
        ),
        history=tuple(
            PlaybookVersion.objects.filter(playbook_id=pip.playbook_id)
            .order_by("pk")
            .values()
        ),
    )


def _assert_feedback_outcome(
    pip: PIP, decisions: tuple[str, ...], before: FeedbackState
) -> None:
    """Compare displayed feedback with the exact applied or rejected database result.

    :param pip: Really finalized proposal. Example: partially accepted PIP42.
    :param decisions: Actual posted staff choices. Example: one ACCEPT, one REJECT.
    :param before: Independent full-row snapshots. Example: original ledger/content/history.
    :return: None. Example: only the accepted ADD exists and earns500.
    :raises AssertionError: If rejected content appears or protected history/awards change.
    """
    pip.refresh_from_db()
    pip.playbook.refresh_from_db()
    changes = tuple(pip.changes.order_by("pk"))
    assert tuple(change.admin_decision for change in changes) == decisions
    accepted = tuple(
        change
        for change, choice in zip(changes, decisions, strict=True)
        if choice == PipChange.ADMIN_ACCEPT
    )
    after = _feedback_snapshot(pip)
    _assert_existing_feedback_rows(before, after)
    _assert_feedback_awards(pip, accepted, before, after)
    existing_ids = {row["id"] for row in before.activities}
    added = tuple(
        (row["name"], row["guidance"])
        for row in after.activities
        if row["id"] not in existing_ids
    )
    assert added == tuple((change.name, change.content) for change in accepted)
    assert pip.playbook.version == (
        _PUBLISHED_VERSION if accepted else _BASELINE_VERSION
    )
    assert len(after.history) == len(before.history) + bool(accepted)
    projection = ExpertsService().project_user(pip.created_by_id)
    assert (
        projection.total_points
        == _MARIA_BASELINE_POINTS + len(accepted) * _MAJOR_ADD_POINTS
    )


def _assert_existing_feedback_rows(before: FeedbackState, after: FeedbackState) -> None:
    """Require every original award, activity and version row to remain byte-value equal.

    :param before: Original independent rows. Example:2129 awards and existing activities.
    :param after: Really persisted post-request rows. Example:2130 awards after one ADD.
    :return: None. Example: original identities, amounts, categories and times preserved.
    :raises AssertionError: If finalization deletes or changes any original protected row.
    """
    for original, current in (
        (before.ledger, after.ledger),
        (before.activities, after.activities),
        (before.history, after.history),
    ):
        ids = {row["id"] for row in original}
        assert tuple(row for row in current if row["id"] in ids) == original


def _assert_feedback_awards(
    pip: PIP,
    accepted: tuple[PipChange, ...],
    before: FeedbackState,
    after: FeedbackState,
) -> None:
    """Require only the exact eligible accepted ADD award, never a rejection award.

    :param pip: Actual finalized proposal. Example: rejected or partially accepted.
    :param accepted: Real persisted ACCEPT changes. Example: one ADD Activity.
    :param before: Original complete ledger. Example:2129 historical rows.
    :param after: Actual complete ledger. Example: one newly accepted-change row.
    :return: None. Example:500 to Maria only, with original event-time metadata.
    :raises AssertionError: If an extra, misattributed or synthetic award appears.
    """
    original_ids = {row["id"] for row in before.ledger}
    new_rows = tuple(row for row in after.ledger if row["id"] not in original_ids)
    assert len(new_rows) == len(accepted)
    for row, change in zip(new_rows, accepted, strict=True):
        expected = {
            "recipient_id": pip.created_by_id,
            "points": _MAJOR_ADD_POINTS,
            "source_kind": KarmaAward.SourceKind.MAJOR,
            "category": "design",
            "event_channel": EventChannel.ACCEPTED_CHANGE,
            "event_identity": f"accepted_change:{change.pk}",
            "playbook_id_snapshot": pip.playbook_id,
            "change_id_snapshot": change.pk,
            "occurred_at": pip.decided_at,
        }
        assert {field: row[field] for field in expected} == expected
