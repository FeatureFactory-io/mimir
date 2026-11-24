from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from contextlib import AbstractContextManager

import pytest
from _pytest.logging import LogCaptureFixture
from django.apps import apps
from django.test import Client

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
    django_capture_on_commit_callbacks: Callable[
        ..., AbstractContextManager[list[Callable[[], None]]]
    ],
) -> None:
    """Prove real staff rejection preserves content/version/awards and sends mail.

    :param client: Real HTTP client. Example: logged-in staff mchen.
    :param django_capture_on_commit_callbacks: Callback capture fixture.
        Example: execute=True delivers locmem rejection notification.
    :return: None. Example: rejected PIP, version 2.0 and Maria 8200.
    :raises AssertionError: If persisted decision or permitted effects differ."""
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
