from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from http import HTTPStatus
from typing import Any

import pytest
from _pytest.logging import LogCaptureFixture
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.models import User
from django.core import mail
from django.db import connection, transaction
from django.db.models import Sum
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from methodology.models import (
    Activity,
    EventChannel,
    ExpertProfile,
    KarmaAward,
    PipChange,
    Playbook,
    PlaybookVersion,
    ProcessImprovementProposal,
    VersionSource,
)
from methodology.services.experts_service import ExpertsService
from methodology.services.pip_admin_service import PIPAdminService
from tests.support.experts_data import (
    CedarDataset,
    create_reviewed_partial_pip,
    load_cedar_baseline,
)
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

DomainState = tuple[tuple[str, int, str], ...]
_PARTIAL_LOGGERS = (
    "methodology.services.karma_service",
    "methodology.services.pip_admin_service",
    "methodology.services.pip_notification_service",
)
_PIP_DECISION_FIELDS = frozenset(
    {"status", "decided_at", "status_changed_at", "updated_at"}
)
_PARTIAL_NOTE = "Accepted ADD only; preserve the existing recovery step"
_MAJOR_POINTS = 500
_ROLLBACK_SIGNAL = "S34 deliberate outer rollback"


@dataclass(frozen=True)
class PartialState:
    """Immutable protection digest and actual identities before partial finalization."""

    protected: DomainState
    ledger_ids: tuple[int, ...]
    activity_ids: tuple[int, ...]
    history_ids: tuple[int, ...]
    totals: tuple[tuple[int, int], ...]


pytestmark = pytest.mark.django_db(transaction=True)


def test_partial_fixture_with_reviewed_state_preserves_baseline() -> None:
    """Verify draft builders and explicit reviewed state preserve baseline facts.

    :return: None. Example: two undecided changes, Maria8200, Hana2.0, no mail.
    :raises AssertionError: If real content, history, awards or permissions differ.
    """
    dataset = load_cedar_baseline()
    before = _preparation_state()
    pip = create_reviewed_partial_pip(dataset)
    _assert_partial_fixture(dataset, pip)
    assert _preparation_state() == before
    assert not getattr(mail, "outbox", [])


def test_finalize_partial_with_accepted_add_awards_only_500(client: Client) -> None:
    """Use actual strict-CSRF staff HTTP and prove accepted-only global effects.

    :param client: Real Django client. Example: existing Mike staff session.
    :return: None. Example: Maria8700, one ADD, one major receipt and truthful feedback.
    :raises AssertionError: If response, protected state, content or exact awards differ.
    """
    dataset = load_cedar_baseline()
    pip = create_reviewed_partial_pip(dataset)
    _prepare_partial_client(client, dataset, pip)
    before = _partial_before(pip, client)
    started = timezone.now()
    response = _post_partial_decisions(client, pip)
    assert response.status_code == HTTPStatus.FOUND
    assert response.headers["Location"] == reverse("pip_detail", args=[pip.pk])
    assert [
        (m.level, str(m)) for m in messages.get_messages(response.wsgi_request)
    ] == [(messages.SUCCESS, "PIP partially accepted — changes applied.")]
    _assert_partial_outcome(dataset, pip, before, started, client)
    _assert_partial_mail(pip)


def test_finalize_partial_with_outer_commit_sends_one_normal_notification() -> None:
    """Verify real outer commit releases exactly one truthful partial email.

    :return: None. Example: no mail inside atomic; one normal email after exit.
    :raises AssertionError: Delivery timing, recipient, decisions or version differ.
    """
    dataset, pip, before = _partial_setup()
    started = timezone.now()
    with transaction.atomic():
        PIPAdminService.finalize_pip(pip, dataset.users_by_username["mchen"])
        _assert_partial_outcome(dataset, pip, before, started)
        _assert_partial_notification_pending()
    assert not connection.in_atomic_block and not connection.run_on_commit
    _assert_partial_outcome(dataset, pip, before, started)
    _assert_partial_transaction_mail(pip)


def test_finalize_partial_with_outer_rollback_preserves_baseline_and_sends_no_mail() -> (
    None
):
    """Verify rollback removes all finalization effects and suppresses mail.

    :return: None. Example: reviewed fixture, Maria8200, target2.0, empty outbox.
    :raises AssertionError: Any rolled-back effect or notification survives.
    """
    dataset, pip, before = _partial_setup()
    original = _partial_transaction_state()
    started = timezone.now()
    with pytest.raises(RuntimeError, match=_ROLLBACK_SIGNAL), transaction.atomic():
        PIPAdminService.finalize_pip(pip, dataset.users_by_username["mchen"])
        _assert_partial_outcome(dataset, pip, before, started)
        _assert_partial_notification_pending()
        raise RuntimeError(_ROLLBACK_SIGNAL)
    _assert_partial_transaction_rolled_back(pip, before, original)


def test_partial_decision_log_story_happy(caplog: LogCaptureFixture) -> None:
    """Certify actual classification, atomic finalization and postcommit mail beats.

    :param caplog: Actual INFO capture. Example:500 classification and partial email.
    :return: None. Example: all five declared owners emit correct actual identifiers.
    :raises AssertionError: If correlated beats, protected facts or notification differ.
    """
    dataset = load_cedar_baseline()
    pip = create_reviewed_partial_pip(dataset)
    before = _partial_before(pip)
    started = timezone.now()
    caplog.clear()
    with capture_experts_logs(caplog, _PARTIAL_LOGGERS):
        PIPAdminService.finalize_pip(
            pip, dataset.users_by_username["mchen"], decisions=_partial_choices(pip)
        )
    _assert_partial_outcome(dataset, pip, before, started)
    _assert_partial_log_story(caplog, pip, dataset)
    _assert_partial_mail(pip)


def test_partial_decision_log_story_reject(caplog: LogCaptureFixture) -> None:
    """Keep the real rejected ALTER in the decision while omitting its content/award.

    :param caplog: Actual policy capture. Example: accepted1/rejected1 finalizer record.
    :return: None. Example: rejected target stays original, no minor100 classification.
    :raises AssertionError: If rejection leaks into application, awards or policy logs.
    """
    dataset = load_cedar_baseline()
    pip = create_reviewed_partial_pip(dataset)
    before = _partial_before(pip)
    started = timezone.now()
    caplog.clear()
    with capture_experts_logs(caplog, _PARTIAL_LOGGERS):
        PIPAdminService.finalize_pip(
            pip, dataset.users_by_username["mchen"], decisions=_partial_choices(pip)
        )
    _assert_partial_outcome(dataset, pip, before, started)
    _assert_partial_log_story(caplog, pip, dataset)
    rejected = pip.changes.get(change_type=PipChange.CHANGE_ALTER)
    assert rejected.admin_decision == PipChange.ADMIN_REJECT
    assert not KarmaAward.objects.filter(change_id_snapshot=rejected.pk).exists()


def _preparation_state() -> DomainState:
    """Hash every event-derived model before and after the two-change preparation.

    :return: Ordered complete-row hashes. Example: original awards/history/content/profiles/users.
    :raises DatabaseError: If the actual owned test database cannot be read.
    """
    snapshots = []
    for model in (KarmaAward, PlaybookVersion, Activity, Playbook, ExpertProfile, User):
        rows = list(model.objects.order_by("pk").values())
        payload = json.dumps(rows, sort_keys=True, default=str).encode()
        snapshots.append(
            (model._meta.label_lower, len(rows), hashlib.sha256(payload).hexdigest())
        )
    return tuple(snapshots)


def _assert_partial_fixture(
    dataset: CedarDataset, pip: ProcessImprovementProposal
) -> None:
    """Assert real draft-origin two-change structure and the independent baseline.

    :param dataset: Actual restored Cedar rows. Example: Hana6106 and Maria8200.
    :param pip: Explicitly reviewed fixture. Example: ADD/ALTER, both admin choices unset.
    :return: None. Example: reviewed timestamps but no applied content/history/awards.
    :raises AssertionError: If structure, actor permissions or baseline facts differ.
    """
    pip.refresh_from_db()
    book = pip.playbook
    assert pip.created_by_id == dataset.users_by_username["mrodriguez"].pk
    assert not pip.created_by.is_staff and dataset.users_by_username["mchen"].is_staff
    assert book.pk == dataset.playbooks_by_pk[6106].pk
    assert book.author_id == dataset.users_by_username["hkim"].pk
    assert (book.status, book.category, book.version) == (
        "released",
        "design",
        Decimal("2.0"),
    )
    _assert_partial_fixture_changes(pip)
    projection = ExpertsService().project_user(pip.created_by_id)
    assert projection.total_points == 8200
    assert dict(projection.category_points) == {"design": 7200, "development": 1000}


def _prepare_partial_client(
    client: Client, dataset: CedarDataset, pip: ProcessImprovementProposal
) -> None:
    """Open the actual staff review and enable the client's native strict CSRF checks.

    :param client: Actual Django client. Example: real per-test Client instance.
    :param dataset: Existing Cedar actors. Example: Mike is staff, Maria is not.
    :param pip: Reviewed proposal. Example: two unapplied Activity changes.
    :return: None. Example: rendered200 and a real csrf cookie, authenticated Mike.
    :raises AssertionError: If original permission or form/token acquisition differs.
    """
    client.handler.enforce_csrf_checks = True
    client.force_login(dataset.users_by_username["mchen"])
    response = client.get(reverse("pip_admin_review", args=[pip.pk]))
    assert response.status_code == HTTPStatus.OK
    assert client.cookies["csrftoken"].value
    assert client.session["_auth_user_id"] == str(dataset.users_by_username["mchen"].pk)


def _partial_choices(pip: ProcessImprovementProposal) -> dict[int, tuple[str, str]]:
    """Derive explicit ADD-accept/ALTER-reject choices from the real two stored rows.

    :param pip: Actual reviewed proposal. Example: ADD Activity plus ALTER Activity.
    :return: Real change-ID choices. Example: {42: ("ACCEPT", note), 43: ("REJECT", note)}.
    :raises AssertionError: If the fixture contains any unexpected operation or count.
    """
    changes = tuple(pip.changes.order_by("order", "pk"))
    assert tuple(change.change_type for change in changes) == (
        PipChange.CHANGE_ADD,
        PipChange.CHANGE_ALTER,
    )
    return {
        changes[0].pk: (PipChange.ADMIN_ACCEPT, _PARTIAL_NOTE),
        changes[1].pk: (PipChange.ADMIN_REJECT, _PARTIAL_NOTE),
    }


def _post_partial_decisions(
    client: Client, pip: ProcessImprovementProposal
) -> HttpResponse:
    """POST real form decisions and the genuine previously acquired CSRF token.

    :param client: Real authenticated strict-CSRF client. Example: Mike session.
    :param pip: Reviewed proposal. Example: exact ADD/ALTER partial decision.
    :return: Actual response. Example:302 redirect to the decided proposal.
    :raises AssertionError: If a real staff token was not acquired first.
    """
    assert client.handler.enforce_csrf_checks and client.cookies["csrftoken"].value
    fields = {
        "action": "finalize",
        "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
    }
    for change_id, (decision, note) in _partial_choices(pip).items():
        fields[f"decision_{change_id}"] = decision
        fields[f"note_{change_id}"] = note
    return client.post(reverse("pip_admin_review", args=[pip.pk]), fields)


def _partial_before(
    pip: ProcessImprovementProposal, client: Client | None = None
) -> PartialState:
    """Capture all protected database fields and original global identities.

    :param pip: Current fixture. Example: reviewed PIP42 targeting Hana6106.
    :param client: Real prepared HTTP session, or service lane. Example: Mike Client.
    :return: Immutable digest/ID baseline. Example:2129 existing complete award rows.
    :raises DatabaseError: If the owned real database cannot be read.
    """
    return PartialState(
        protected=_protected_partial_state(pip, client, {}),
        ledger_ids=tuple(
            KarmaAward.objects.order_by("pk").values_list("pk", flat=True)
        ),
        activity_ids=tuple(
            Activity.objects.order_by("pk").values_list("pk", flat=True)
        ),
        history_ids=tuple(
            PlaybookVersion.objects.order_by("pk").values_list("pk", flat=True)
        ),
        totals=_partial_totals(),
    )


def _protected_partial_state(
    pip: ProcessImprovementProposal,
    client: Client | None,
    omitted: dict[str, tuple[int, ...]],
) -> DomainState:
    """Hash every real model/M2M row, permitting only exact current decision writes.

    :param pip: Current decided proposal. Example: PIP42.
    :param client: Actual staff session or absent service lane. Example: Mike Client.
    :param omitted: Exact verified newly created row IDs. Example: one award/activity/version.
    :return: Full normalized database fingerprint. Example: every original field unchanged.
    :raises DatabaseError: If actual persisted rows cannot be read.
    """
    snapshots = []
    for model in sorted(
        apps.get_models(include_auto_created=True),
        key=lambda item: item._meta.label_lower,
    ):
        label = model._meta.label_lower
        rows = list(
            model.objects.exclude(pk__in=omitted.get(label, ())).order_by("pk").values()
        )
        for row in rows:
            for field in _partial_allowed_fields(label, row, pip, client):
                row.pop(field)
        payload = json.dumps(rows, sort_keys=True, default=str).encode()
        snapshots.append((label, len(rows), hashlib.sha256(payload).hexdigest()))
    return tuple(snapshots)


def _partial_allowed_fields(
    label: str,
    row: dict[str, Any],
    pip: ProcessImprovementProposal,
    client: Client | None,
) -> frozenset[str]:
    """Name only the current finalizer's permitted mutable database fields.

    :param label: Actual Django model label. Example: methodology.playbook.
    :param row: Actual persisted values. Example: target playbook6106.
    :param pip: Current fixture. Example: PIP42, not historical Cedar proposals.
    :param client: Prepared session or absent. Example: authenticated staff session.
    :return: Exact ignored decision fields. Example: current target version/updated_at only.
    :raises AssertionError: If session identity required by HTTP is absent.
    """
    if label == ProcessImprovementProposal._meta.label_lower and row["id"] == pip.pk:
        return _PIP_DECISION_FIELDS
    if label == PipChange._meta.label_lower and row["pip_id"] == pip.pk:
        return frozenset({"admin_decision", "admin_note"})
    if label == Playbook._meta.label_lower and row["id"] == pip.playbook_id:
        return frozenset({"version", "updated_at"})
    if label == "sessions.session" and client is not None:
        assert client.session.session_key
        if row["session_key"] == client.session.session_key:
            return frozenset({"session_data", "expire_date"})
    return frozenset()


def _assert_partial_outcome(
    dataset: CedarDataset,
    pip: ProcessImprovementProposal,
    before: PartialState,
    started: datetime,
    client: Client | None = None,
) -> None:
    """Certify exact publication, accepted-only award and all protected original rows.

    :param dataset: Real restored Cedar actors. Example: Maria, Hana and Mike.
    :param pip: Really finalized proposal. Example: accepted_partial.
    :param before: Independent pre-request fingerprints. Example:2129 original awards.
    :param started: Actual aware lower bound. Example: instant before finalize.
    :param client: Actual staff client if HTTP lane. Example: Mike session.
    :return: None. Example:8700/7700/1000, exactly one ADD/major receipt/500 award.
    :raises AssertionError: If any payload, original row, timestamp or category differs.
    """
    pip.refresh_from_db()
    pip.playbook.refresh_from_db()
    accepted = pip.changes.get(change_type=PipChange.CHANGE_ADD)
    award = KarmaAward.objects.exclude(pk__in=before.ledger_ids).get()
    activity = Activity.objects.exclude(pk__in=before.activity_ids).get()
    receipt = PlaybookVersion.objects.exclude(pk__in=before.history_ids).get()
    omitted = {
        KarmaAward._meta.label_lower: (award.pk,),
        Activity._meta.label_lower: (activity.pk,),
        PlaybookVersion._meta.label_lower: (receipt.pk,),
    }
    assert _protected_partial_state(pip, client, omitted) == before.protected
    _assert_partial_content(pip, accepted, activity)
    _assert_partial_publication(pip, accepted, receipt)
    _assert_partial_award(pip, accepted, award)
    _assert_partial_scores(dataset, pip, before)
    assert pip.status == pip.STATUS_ACCEPTED_PARTIAL
    assert (
        started
        <= pip.decided_at
        <= pip.status_changed_at
        <= pip.updated_at
        <= timezone.now()
    )
    assert timezone.is_aware(pip.decided_at)
    assert receipt.created_by_id == dataset.users_by_username["mchen"].pk
    assert started <= receipt.created_at <= timezone.now()
    assert started <= pip.playbook.updated_at <= timezone.now()
    if client is not None:
        assert client.session["_auth_user_id"] == str(receipt.created_by_id)


def _assert_partial_publication(
    pip: ProcessImprovementProposal, accepted: PipChange, receipt: PlaybookVersion
) -> None:
    """Verify the existing version owner's single real major publication receipt.

    :param pip: Actually decided partial proposal. Example: Hana2.0 to3.0.
    :param accepted: Persisted accepted ADD. Example: one Activity change.
    :param receipt: Actual new receipt. Example: source=pip/is_major=True.
    :return: None. Example: accepted ID only and full before/after/category metadata.
    :raises AssertionError: If receipt source, content summary or exact snapshot differs.
    """
    assert receipt.playbook_id == pip.playbook_id and receipt.pip_id == pip.pk
    assert receipt.version_number == pip.playbook.version == Decimal("3.0")
    assert receipt.source == VersionSource.PIP_SOURCE and receipt.is_major
    assert receipt.created_by.is_staff
    assert receipt.snapshot_data == {
        "pip_id": pip.pk,
        "playbook_name": pip.playbook.name,
        "version_before": "2.0",
        "version_after": "3.0",
        "accepted_change_ids": [accepted.pk],
        "category": "design",
    }
    assert receipt.change_summary == f"ADD {accepted.name}"
    rejected = pip.changes.get(change_type=PipChange.CHANGE_ALTER)
    assert (
        rejected.name not in receipt.change_summary
        and rejected.content not in receipt.change_summary
    )
    assert pip.playbook_versions.count() == 1


def _assert_partial_award(
    pip: ProcessImprovementProposal, accepted: PipChange, award: KarmaAward
) -> None:
    """Compare every domain field of the sole new award to an independent oracle.

    :param pip: Actually finalized partial proposal. Example: creator Maria.
    :param accepted: Only eligible persisted change. Example: accepted ADD Activity.
    :param award: Sole new global ledger row. Example: major500 at actual decided_at.
    :return: None. Example: original accepted_change identity and exact nullable entity pair.
    :raises AssertionError: If any attribution, channel, identity, point or time differs.
    """
    actual = KarmaAward.objects.values().get(pk=award.pk)
    expected = {
        "id": award.pk,
        "recipient_id": pip.created_by_id,
        "event_identity": f"accepted_change:{accepted.pk}",
        "event_channel": EventChannel.ACCEPTED_CHANGE,
        "source_kind": KarmaAward.SourceKind.MAJOR,
        "points": _MAJOR_POINTS,
        "category": "design",
        "playbook_id_snapshot": pip.playbook_id,
        "change_id_snapshot": accepted.pk,
        "entity_type_snapshot": None,
        "entity_id_snapshot": None,
        "occurred_at": pip.decided_at,
    }
    assert actual == expected


def _assert_partial_mail(pip: ProcessImprovementProposal) -> None:
    """Inspect the one actual postcommit locmem partial decision notification.

    :param pip: Really finalized proposal. Example: two real decisions and target3.0.
    :return: None. Example: correct recipient, both decisions and version, no earnings copy.
    :raises AssertionError: If delivery count, recipient, content or destination differs.
    """
    outbox = getattr(mail, "outbox", [])
    assert len(outbox) == 1
    message = outbox[0]
    assert message.to == [pip.created_by.email]
    assert message.subject == f'Your PIP "{pip.title}" — Partially accepted'
    assert "Overall: Partially accepted." in message.body
    assert f"{pip.playbook.name} is now v3.0." in message.body
    assert f"/pips/{pip.pk}/" in message.body
    assert _PARTIAL_NOTE in message.body
    for change in pip.changes.order_by("order", "pk"):
        assert f'{change.change_type} Activity "{change.name}"' in message.body
        assert f"Decision: {change.admin_decision}" in message.body
    assert (
        "Karma" not in message.body
        and "8700" not in message.body
        and "500" not in message.body
    )


def _assert_partial_log_story(
    caplog: LogCaptureFixture, pip: ProcessImprovementProposal, dataset: CedarDataset
) -> None:
    """Check five declared log owners and omission of rejected classification/PII.

    :param caplog: Actual INFO capture. Example: real mixed finalization lifecycle.
    :param pip: Real decided proposal. Example: accepted_partial with one accepted ADD.
    :param dataset: Original actors. Example: Mike staff reviewer.
    :return: None. Example: major500 and accepted1/rejected1; no minor100/rejected award.
    :raises AssertionError: If a beat, identity, privacy or classification differs.
    """
    accepted = pip.changes.get(change_type=PipChange.CHANGE_ADD)
    rejected = pip.changes.get(change_type=PipChange.CHANGE_ALTER)
    _assert_partial_policy_logs(caplog, pip, accepted)
    _assert_partial_finalizer_logs(caplog, pip, dataset)
    policy = [r.getMessage() for r in caplog.records if r.name == _PARTIAL_LOGGERS[0]]
    assert not any(
        "source_kind=minor" in text or "points=100" in text for text in policy
    )
    assert not any(f"change_id={rejected.pk} " in text for text in policy)
    forbidden = (
        pip.title,
        pip.summary,
        accepted.content,
        rejected.content,
        _PARTIAL_NOTE,
        *User.objects.values_list("email", flat=True),
    )
    assert all(
        not value or all(value not in text for text in policy) for value in forbidden
    )


def _partial_totals() -> tuple[tuple[int, int], ...]:
    """Read an independent total for every real account, including zero-award actors.

    :return: Ordered actor/total pairs. Example: Maria8200, Mike12450, Bob absent account.
    :raises DatabaseError: If the actual immutable ledger cannot be aggregated.
    """
    return tuple(
        (
            pk,
            KarmaAward.objects.filter(recipient_id=pk).aggregate(total=Sum("points"))[
                "total"
            ]
            or 0,
        )
        for pk in User.objects.order_by("pk").values_list("pk", flat=True)
    )


def _assert_partial_scores(
    dataset: CedarDataset, pip: ProcessImprovementProposal, before: PartialState
) -> None:
    """Check accepted500 and all counterpart totals from independent real aggregation.

    :param dataset: Original users. Example: Maria, Hana and Mike.
    :param pip: Really partially accepted proposal. Example: submitter Maria.
    :param before: Actual all-user totals. Example: original immutable ledger totals.
    :return: None. Example: Maria8700/Design7700/Development1000, others identical.
    :raises AssertionError: If rejected100, author/admin points or other drift appears.
    """
    expected = dict(before.totals)
    expected[pip.created_by_id] += _MAJOR_POINTS
    assert dict(_partial_totals()) == expected
    projection = ExpertsService().project_user(pip.created_by_id)
    assert projection.total_points == 8700 and projection.total_points != 8800
    assert dict(projection.category_points) == {"design": 7700, "development": 1000}
    assert expected[dataset.users_by_username["hkim"].pk] == 5800
    assert expected[dataset.users_by_username["mchen"].pk] == 12450


def _assert_partial_content(
    pip: ProcessImprovementProposal, accepted: PipChange, activity: Activity
) -> None:
    """Compare the actual new Activity and the persisted accepted/rejected choices.

    :param pip: Really finalized proposal. Example: accepted_partial.
    :param accepted: Accepted ADD change. Example: Activity at actual parent workflow.
    :param activity: Sole newly created global Activity. Example: original requested guidance.
    :return: None. Example: accepted content exists, rejected ALTER was never applied.
    :raises AssertionError: If the actual name, guidance, ownership or choices differ.
    """
    rejected = pip.changes.get(change_type=PipChange.CHANGE_ALTER)
    assert accepted.admin_decision == PipChange.ADMIN_ACCEPT
    assert rejected.admin_decision == PipChange.ADMIN_REJECT
    assert (activity.name, activity.guidance, activity.workflow_id) == (
        accepted.name,
        accepted.content,
        accepted.parent_workflow_id,
    )
    original = Activity.objects.get(pk=rejected.target_id)
    assert original.name != rejected.name and original.guidance != rejected.content
    assert activity.workflow.playbook_id == pip.playbook_id


def _assert_partial_policy_logs(
    caplog: LogCaptureFixture, pip: ProcessImprovementProposal, accepted: PipChange
) -> None:
    """Assert actual entry, accepted-only classification and single-created exit beats.

    :param caplog: Actual real policy log capture. Example: correlated pip_finalize42.
    :param pip: Partial proposal. Example: actual PIP42.
    :param accepted: Real accepted ADD. Example: Activity change43.
    :return: None. Example: major500, created1 and existing0 inside the transaction.
    :raises AssertionError: If a required correlated policy beat is missing.
    """
    trace = (f"pip_id={pip.pk}", f"correlation_id=pip_finalize:{pip.pk}")
    assert_log_story(
        caplog,
        where="KarmaService.award_accepted_changes",
        beats={
            "entry": ("| entry |", *trace),
            "exit": (
                "| exit |",
                "created_count=1",
                "existing_count=0",
                "transaction=pending",
                *trace,
            ),
        },
    )
    assert_log_story(
        caplog,
        where="KarmaService._accepted_change_policy",
        beats={
            "processing": (
                "| processing |",
                f"change_id={accepted.pk}",
                "operation=ADD",
                "entity=Activity",
                "source_kind=major",
                "points=500",
            ),
        },
    )


def _assert_partial_finalizer_logs(
    caplog: LogCaptureFixture, pip: ProcessImprovementProposal, dataset: CedarDataset
) -> None:
    """Check real mixed finalization and its actual postcommit notification owner.

    :param caplog: Actual INFO records. Example: existing finalizer and email logs.
    :param pip: Real finalized partial proposal. Example: PIP42.
    :param dataset: Existing actual staff user. Example: Mike.
    :return: None. Example: accepted1/rejected1 and notification verdict=partial.
    :raises AssertionError: If a finalizer/notification beat or actual actor differs.
    """
    assert_log_story(
        caplog,
        where="PIPAdminService.finalize_pip",
        beats={
            "processing": (
                f"pk={pip.pk}",
                f"actor={dataset.users_by_username['mchen'].pk}",
                "accepted=1",
                "rejected=1",
            ),
        },
    )
    assert_log_story(
        caplog,
        where="Sending PIP decision email",
        beats={
            "processing": (f"pip_id={pip.pk}", "verdict=partial"),
        },
    )


def _assert_partial_fixture_changes(pip: ProcessImprovementProposal) -> None:
    """Verify two unapplied changes and the explicit reviewed fixture boundary.

    :param pip: Real draft-origin reviewed proposal. Example: ADD/ALTER Activity.
    :return: None. Example: recommendations set, admin choices unset, published v2.0 intact.
    :raises AssertionError: If the fixture changes structure or crosses finalization early.
    """
    book = pip.playbook
    changes = tuple(pip.changes.order_by("order", "pk"))
    assert len(changes) == 2 and changes[0].pk != changes[1].pk
    assert tuple(c.change_type for c in changes) == (
        PipChange.CHANGE_ADD,
        PipChange.CHANGE_ALTER,
    )
    assert all(
        c.entity_type == PipChange.ENTITY_ACTIVITY
        and c.admin_decision == PipChange.ADMIN_UNSET
        for c in changes
    )
    assert pip.status == pip.STATUS_REVIEWED and pip.decided_at is None
    assert pip.submitted_at == pip.reviewed_at and timezone.is_aware(pip.reviewed_at)
    assert all(c.galdr_recommendation == PipChange.GALDR_ACCEPT for c in changes)
    assert changes[0].parent_workflow.playbook_id == book.pk
    assert Activity.objects.get(pk=changes[1].target_id).workflow.playbook_id == book.pk
    assert not Activity.objects.filter(
        name=changes[0].name, workflow__playbook=book
    ).exists()
    assert not pip.playbook_versions.exists()


def _partial_setup() -> tuple[CedarDataset, ProcessImprovementProposal, PartialState]:
    """Save real mixed choices before the independently owned outer transaction.

    :return: Restored data, reviewed PIP and before state. Example: Maria8200, ADD accept.
    :raises AssertionError: If fixture, autocommit, callbacks or original mail differ.
    """
    assert not connection.in_atomic_block and not connection.run_on_commit
    dataset = load_cedar_baseline()
    pip = create_reviewed_partial_pip(dataset)
    _assert_partial_fixture(dataset, pip)
    PIPAdminService.save_decisions(
        pip, dataset.users_by_username["mchen"], _partial_choices(pip)
    )
    assert not connection.in_atomic_block and not connection.run_on_commit
    assert not getattr(mail, "outbox", [])
    assert pip.status == ProcessImprovementProposal.STATUS_REVIEWED
    for change_id, (decision, note) in _partial_choices(pip).items():
        actual = PipChange.objects.values("admin_decision", "admin_note").get(
            pk=change_id
        )
        assert actual == {"admin_decision": decision, "admin_note": note}
    return dataset, pip, _partial_before(pip)


def _assert_partial_notification_pending() -> None:
    """Observe an actual pending callback without capturing or invoking it.

    :return: None. Example: one queued callback and zero delivered decision messages.
    :raises AssertionError: If finalization sends mail before the outer commit.
    """
    assert connection.in_atomic_block
    assert len(connection.run_on_commit) == 1
    assert not getattr(mail, "outbox", [])


def _partial_transaction_state() -> DomainState:
    """Fingerprint every actual database row with no mutable-field exclusions.

    :return: Full model and M2M row digests. Example: reviewed proposal timestamps included.
    :raises DatabaseError: If the isolated real test database cannot be read.
    """
    state = []
    for model in sorted(
        apps.get_models(include_auto_created=True),
        key=lambda item: item._meta.label_lower,
    ):
        rows = list(model.objects.order_by("pk").values())
        payload = json.dumps(rows, sort_keys=True, default=str).encode()
        state.append(
            (model._meta.label_lower, len(rows), hashlib.sha256(payload).hexdigest())
        )
    return tuple(state)


def _assert_partial_transaction_rolled_back(
    pip: ProcessImprovementProposal, before: PartialState, original: DomainState
) -> None:
    """Require exact original rows, choices and identities after the real rollback.

    :param pip: The transient finalized object. Example: persisted state returns to reviewed.
    :param before: Original identities and all-user totals. Example:2129 historical awards.
    :param original: Unfiltered before digests. Example: every model/M2M field included.
    :return: None. Example: no new Activity, award, receipt or mail, target2.0.
    :raises AssertionError: If any rolled-back state or pending notification remains.
    """
    assert not connection.in_atomic_block and not connection.run_on_commit
    assert not getattr(mail, "outbox", [])
    assert _partial_transaction_state() == original
    pip.refresh_from_db()
    pip.playbook.refresh_from_db()
    assert pip.status == ProcessImprovementProposal.STATUS_REVIEWED
    assert pip.decided_at is None and pip.playbook.version == Decimal("2.0")
    assert _partial_before(pip) == before
    for change_id, (decision, note) in _partial_choices(pip).items():
        actual = PipChange.objects.values("admin_decision", "admin_note").get(
            pk=change_id
        )
        assert actual == {"admin_decision": decision, "admin_note": note}


def _assert_partial_transaction_mail(pip: ProcessImprovementProposal) -> None:
    """Associate each delivered decision with its own actual change header.

    :param pip: Committed partial proposal. Example: ADD accepted, ALTER rejected.
    :return: None. Example: the delivered ADD line is followed by ACCEPT, not REJECT.
    :raises AssertionError: If a correct-looking message swaps the two decisions.
    """
    _assert_partial_mail(pip)
    body = mail.outbox[0].body
    for number, change in enumerate(pip.changes.order_by("order", "pk"), start=1):
        header = f'Change {number}: {change.change_type} Activity "{change.name}"'
        assert f"{header}\n  Decision: {change.admin_decision}" in body
