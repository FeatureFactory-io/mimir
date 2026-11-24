"""Karma acceptance bindings for the existing staff decision flow."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from decimal import Decimal
from http import HTTPStatus

from behave import given, then, when
from behave.runner import Context
from django.apps import apps
from django.contrib.auth.models import User
from django.core import mail
from django.db import transaction
from django.db.models import Sum
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from methodology.models import (
    Activity,
    Artifact,
    EventChannel,
    KarmaAward,
    PipChange,
    Playbook,
    PlaybookVersion,
    Skill,
    VersionSource,
)
from methodology.models import (
    ProcessImprovementProposal as PIP,
)
from methodology.services.experts_service import ExpertsService
from methodology.services.karma_service import KarmaService
from tests.support.experts_data import (
    CedarDataset,
    create_nonaccepted_pip_case,
    create_reviewed_major_add_pip,
    create_reviewed_partial_pip,
    load_cedar_baseline,
)
from tests.support.experts_pip_minor import (
    assert_minor_change_applied,
    create_reviewed_minor_pip,
)

_TARGET_ID = 6106
_TARGET_NAME = "Accessible Forms Review"
_VERSION_BEFORE = Decimal("2.0")
_VERSION_AFTER = Decimal("3.0")
_DESIGN = "design"
_DEVELOPMENT = "development"
_MARIA_DESIGN_BEFORE = 7200
_MARIA_DEVELOPMENT = 1000
_MAJOR_POINTS = 500
_MINOR_POINTS = 100
_RELEASE = KarmaAward.SourceKind.RELEASE

_S35_STATES = (
    PIP.STATUS_DRAFT,
    PIP.STATUS_SUBMITTED,
    PIP.STATUS_PROCESSING_GALDR,
    PIP.STATUS_REVIEWED,
    PIP.STATUS_REJECTED,
)
_S35_PIP_FIELDS = frozenset(("status", "decided_at", "status_changed_at", "updated_at"))
_S35_CHANGE_FIELDS = frozenset(("admin_decision", "admin_note"))
_S35_SESSION_FIELDS = frozenset(("session_data", "expire_date"))
_S35_REJECTION_NOTE = "Rejected after checking the unchanged published baseline"
S35DatabaseState = tuple[tuple[str, int, str], ...]
S35Observation = tuple[object, ...]
_S34_NOTE = "Accepted ADD only; preserve the existing recovery step"


@given("Maria's new PIP targets Hana's Accessible Forms Review version 2.0")
def prepare_maria_major_add_target(context: Context) -> None:
    """Retain the independently restored real target before the Example selects type.

    :param context: Isolated AT context. Example: context.cedar_dataset from S03.
    :return: None. Example: real target 6106 is retained at version 2.0.
    :raises AssertionError: If baseline authorship or version differs.
    """
    _record_maria_decision_baseline(context)


def _record_maria_decision_baseline(context: Context) -> None:
    """Retain the pre-decision target, ledger and other actors' projections.

    :param context: Isolated Cedar AT context, for example a minor ALTER case.
    :return: None after recording the pre-decision state.
    :raises AssertionError: If the restored baseline or empty outbox differs.
    """
    dataset: CedarDataset = context.cedar_dataset
    target = dataset.playbooks_by_pk[_TARGET_ID]
    maria = dataset.users_by_username["mrodriguez"]
    hana = dataset.users_by_username["hkim"]
    staff = dataset.users_by_username["mchen"]
    assert (target.name, target.version, target.category, target.author_id) == (
        _TARGET_NAME,
        _VERSION_BEFORE,
        _DESIGN,
        hana.pk,
    )
    assert not maria.is_staff and staff.is_staff
    experts = ExpertsService()
    projection = experts.project_user(maria.pk)
    assert projection.total_points == _MARIA_DESIGN_BEFORE + _MARIA_DEVELOPMENT
    _assert_maria_pip_categories(projection.category_points, _MARIA_DESIGN_BEFORE)
    context.maria_pip_target = target
    context.maria_pip_ledger_count = KarmaAward.objects.count()
    context.maria_pip_release_count = KarmaAward.objects.filter(
        source_kind=_RELEASE
    ).count()
    context.maria_pip_version_count = target.versions.count()
    context.maria_pip_other_projections = tuple(
        experts.project_user(user_id) for user_id in (hana.pk, staff.pk)
    )
    assert not mail.outbox


@when("an Administrator accepts its eligible ADD {entity} change")
@when("an Administrator accepts Maria's independent {operation} {entity} change")
def accept_maria_change(
    context: Context, entity: str, operation: str | None = None
) -> None:
    """Finalize one explicitly selected major/minor real reviewed fixture through the existing staff POST.

    :param context: Real Cedar state and actual response. Example: Hana target v2.0.
    :param entity: Exact major or minor matrix entity. Example: Activity or Workflow.
    :param operation: Exact minor operation, or None for major ADD. Example: ALTER.
    :return: None after the real decision applies the selected change once.
    :raises AssertionError: If the real permission, decision or content differs.
    """
    if operation is not None:
        _accept_maria_minor_change(context, operation, entity)
        return

    dataset: CedarDataset = context.cedar_dataset
    pip = create_reviewed_major_add_pip(dataset, entity)
    assert pip.created_by_id == dataset.user_ids["mrodriguez"]
    assert pip.playbook_id == context.maria_pip_target.pk
    change = pip.changes.get()
    assert (change.change_type, change.entity_type) == (PipChange.CHANGE_ADD, entity)
    assert _matching_added_content_count(change) == 0
    _finalize_maria_single_change(context, change)
    assert _matching_added_content_count(change) == 1
    context.maria_accepted_change = change


def _accept_maria_minor_change(context: Context, operation: str, entity: str) -> None:
    """Build the exact Reviewed Example and verify the persisted staff decision.

    :param context: Independently restored Cedar AT context.
    :param operation: Exact minor operation. Example: LINK.
    :param entity: Exact outline entity. Example: supported existing relationship.
    :return: None after the selected change takes effect through the staff POST.
    :raises ValueError: If the example is outside the approved minor matrix.
    :raises AssertionError: If the persisted change or its concrete effect differs.
    """
    _record_maria_decision_baseline(context)
    dataset: CedarDataset = context.cedar_dataset
    case = create_reviewed_minor_pip(dataset, operation=operation, entity=entity)
    assert (case.pip.created_by_id, case.pip.playbook_id) == (
        dataset.user_ids["mrodriguez"],
        context.maria_pip_target.pk,
    )
    assert (
        case.pip.changes.get() == case.change and case.change.change_type == operation
    )
    if operation in (PipChange.CHANGE_LINK, PipChange.CHANGE_UNLINK):
        assert case.change.entity_type == ""
        assert case.change.relationship_type == PipChange.REL_SKILL_ACTIVITY
    else:
        assert case.change.entity_type == entity
    _finalize_maria_single_change(context, case.change)
    assert_minor_change_applied(case)
    context.maria_accepted_change = case.change


def _finalize_maria_single_change(context: Context, change: PipChange) -> None:
    """POST one acceptance as Cedar's existing staff account.

    :param context: Real Django test client and Cedar fixture.
    :param change: Undecided persisted proposal change, for example ADD Skill.
    :return: None after the production callback is captured and run.
    :raises AssertionError: If the decision, HTTP result or callback differs.
    """
    pip = change.pip
    assert pip.status == pip.STATUS_REVIEWED and not change.admin_decision
    assert pip.decided_at is None
    staff = context.cedar_dataset.users_by_username["mchen"]
    assert staff.is_staff and staff.pk != pip.created_by_id
    context.client.force_login(staff)
    route_args = {"pk": pip.pk}
    data = {"action": "finalize", f"decision_{change.pk}": PipChange.ADMIN_ACCEPT}
    # Behave rolls back each case. Run the real registered callback after the POST.
    with context.test.captureOnCommitCallbacks(execute=True) as callbacks:
        response = context.client.post(
            reverse("pip_admin_review", kwargs=route_args), data
        )
        assert not mail.outbox
    assert len(callbacks) == 1
    assert response.status_code == 302
    assert response.url == reverse("pip_detail", kwargs=route_args)
    assert response.wsgi_request.user.pk == staff.pk
    pip.refresh_from_db()
    change.refresh_from_db()
    assert (
        pip.status == pip.STATUS_ACCEPTED
        and change.admin_decision == PipChange.ADMIN_ACCEPT
    )


def _matching_added_content_count(change: PipChange) -> int:
    """Check persisted content and its owning relationship for a major ADD.

    :param change: Persisted ADD Activity, Skill or Artifact. Example: ADD Artifact.
    :return: Count of exact payload matches under the proposed parent.
    :raises AssertionError: If the change is outside the major ADD matrix.
    """
    target_id = change.pip.playbook_id
    if change.entity_type == PipChange.ENTITY_ACTIVITY:
        return Activity.objects.filter(
            workflow_id=change.parent_workflow_id,
            workflow__playbook_id=target_id,
            name=change.name,
            guidance=change.content,
        ).count()
    if change.entity_type == PipChange.ENTITY_SKILL:
        return Skill.objects.filter(
            playbook_id=target_id, title=change.name, content=change.content
        ).count()
    assert change.entity_type == PipChange.ENTITY_ARTIFACT
    return Artifact.objects.filter(
        playbook_id=target_id,
        produced_by_id=change.produced_by_activity_ref,
        name=change.name,
        description=change.content,
    ).count()


@then("Maria's total becomes {total:d} and Design subtotal becomes {design:d}")
@then("Maria's total becomes {total:d}")
def assert_maria_pip_total(
    context: Context, total: int, design: int | None = None
) -> None:
    """Assert the actual live total and optional Design subtotal after real finalization.

    :param context: Real finalized PIP and pre-event ledger snapshot. Example: context.cedar_dataset.
    :param total: Expected actual overall total. Example: 8700 or 8300.
    :param design: Optional expected Design subtotal. Example: 7700.
    :return: None after recipient and immutable award reconciliation.
    :raises AssertionError: Amount, category, recipient or unrelated state differs."""
    maria_id = context.cedar_dataset.user_ids["mrodriguez"]
    projection = ExpertsService().project_user(maria_id)
    assert projection.total_points == total
    if design is not None:
        _assert_maria_pip_categories(projection.category_points, design)
        _assert_accepted_change_award(
            context, KarmaAward.SourceKind.MAJOR, _MAJOR_POINTS
        )


def _assert_maria_pip_categories(
    category_points: Mapping[str, int], design: int
) -> None:
    """Check the Design and unchanged Development subtotals.

    :param category_points: Actual category subtotals from Maria's ledger.
    :param design: Expected Design subtotal. Example: 7300.
    :return: None after reconciling both categories.
    :raises AssertionError: If a subtotal differs or another category appears.
    """
    assert dict(category_points) == {
        _DESIGN: design,
        _DEVELOPMENT: _MARIA_DEVELOPMENT,
    }


def _assert_accepted_change_award(
    context: Context, source_kind: KarmaAward.SourceKind, points: int
) -> None:
    """Match the single new event to the real terminal decision and recipient.

    :param context: Cedar acceptance state with the original ledger counts.
    :param source_kind: Expected award classification. Example: major.
    :param points: Expected immutable credit. Example: 500.
    :return: None when award and unaffected contributions match.
    :raises AssertionError: If award identity, provenance, counts or totals differ.
    """
    change: PipChange = context.maria_accepted_change
    pip = change.pip
    award = KarmaAward.objects.get(event_identity=f"accepted_change:{change.pk}")
    assert (
        award.recipient_id,
        award.playbook_id_snapshot,
        award.change_id_snapshot,
    ) == (pip.created_by_id, pip.playbook_id, change.pk)
    assert (award.event_channel, award.source_kind, award.points, award.category) == (
        EventChannel.ACCEPTED_CHANGE,
        source_kind,
        points,
        _DESIGN,
    )
    assert award.occurred_at == pip.decided_at and timezone.is_aware(award.occurred_at)
    assert KarmaAward.objects.count() == context.maria_pip_ledger_count + 1
    assert (
        KarmaAward.objects.filter(source_kind=_RELEASE).count()
        == context.maria_pip_release_count
    )
    experts = ExpertsService()
    for before in context.maria_pip_other_projections:
        assert experts.project_user(before.user_id) == before


@then("the target playbook is version 3.0")
def assert_maria_pip_target_version(context: Context) -> None:
    """Assert one actual major publication and its accepted-change receipt.

    :param context: Context with the finalized target. Example: playbook 6106.
    :return: None. Example: one new PIP version at 3.0.
    :raises AssertionError: If the publication or its receipt differs.
    """
    change: PipChange = context.maria_accepted_change
    pip = change.pip
    target = context.maria_pip_target
    target.refresh_from_db()
    assert target.version == _VERSION_AFTER
    assert target.versions.count() == context.maria_pip_version_count + 1
    receipt = pip.playbook_versions.get()
    assert (receipt.playbook_id, receipt.version_number, receipt.source) == (
        target.pk,
        _VERSION_AFTER,
        VersionSource.PIP_SOURCE,
    )
    assert (
        receipt.is_major
        and receipt.created_by_id == context.cedar_dataset.user_ids["mchen"]
    )
    assert receipt.snapshot_data == {
        "pip_id": pip.pk,
        "playbook_name": target.name,
        "version_before": str(_VERSION_BEFORE),
        "version_after": str(_VERSION_AFTER),
        "accepted_change_ids": [change.pk],
        "category": _DESIGN,
    }


@then("the normal decision notification is captured locally")
def assert_maria_pip_local_notification(context: Context) -> None:
    """Assert the existing postcommit email in local-memory capture.

    :param context: Real isolated AT context. Example: finalized DROP Phase case.
    :return: None. Example: one accepted decision email to Maria includes 3.0.
    :raises AssertionError: If recipient, body, count or delivery timing differs.
    """
    change: PipChange = context.maria_accepted_change
    maria = context.cedar_dataset.users_by_username["mrodriguez"]
    (sent,) = mail.outbox
    assert sent.to == [maria.email] and not sent.cc and not sent.bcc
    assert sent.subject == f'Your PIP "{change.pip.title}" — Accepted ✓'
    label = change.name or change.target_name_snapshot or "(unnamed)"
    assert f'Change 1: {change.change_type} {change.entity_type} "{label}"' in sent.body
    assert "Decision: ACCEPT" in sent.body and f"is now v{_VERSION_AFTER}" in sent.body


@when(
    "Maria's PIP is draft, submitted, processing, reviewed or rejected without an accepted eligible change"
)
def exercise_maria_nonaccepted_states(context: Context) -> None:
    """Record five independently restored cases and real rejected finalization.

    :param context: Real AT context. Example: context.cedar_dataset.
    :return: None. Example: five persisted outcomes retained for shared assertions.
    :raises AssertionError: If any case awards points or changes target content.
    """
    assert not mail.outbox
    context.s35_baseline = _s35_database_state()
    context.s35_observations = []
    for status in _S35_STATES:
        assert _s35_database_state() == context.s35_baseline
        context.s35_observations.append(_s35_observe_nonaccepted(context, status))
        # A transaction rollback does not undo delivered locmem mail.
        assert len(mail.outbox) == (1 if status == PIP.STATUS_REJECTED else 0)
        mail.outbox.clear()
        assert _s35_database_state() == context.s35_baseline
    context.s35_observations = tuple(context.s35_observations)


@given("Maria's PIP contains one ADD Activity and one ALTER Activity")
def prepare_maria_partial_pip(context: Context) -> None:
    """Prepare the independent two-change fixture using the shared Cedar context.

    :param context: Behave state. Example: context.cedar_dataset from S03.
    :return: None. Example: real reviewed proposal retained for finalization.
    :raises AssertionError: Baseline or fixture violates Section C.
    """
    _record_maria_decision_baseline(context)
    pip = create_reviewed_partial_pip(context.cedar_dataset)
    context.s34_pip = pip
    changes = tuple(pip.changes.order_by("order", "pk"))
    assert tuple(c.change_type for c in changes) == ("ADD", "ALTER")
    assert all(c.entity_type == "Activity" and not c.admin_decision for c in changes)
    assert pip.status == PIP.STATUS_REVIEWED and pip.decided_at is None
    assert pip.playbook_id == _TARGET_ID and pip.playbook.version == _VERSION_BEFORE
    context.client.handler.enforce_csrf_checks = True
    context.client.force_login(context.cedar_dataset.users_by_username["mchen"])
    assert (
        context.client.get(reverse("pip_admin_review", args=[pip.pk])).status_code
        == HTTPStatus.OK
    )
    assert context.client.cookies["csrftoken"].value and not mail.outbox
    context.s34_ledger_ids = tuple(KarmaAward.objects.values_list("pk", flat=True))
    context.s34_activity_ids = tuple(Activity.objects.values_list("pk", flat=True))
    context.s34_history_ids = tuple(
        PlaybookVersion.objects.values_list("pk", flat=True)
    )
    context.s34_totals = _s34_totals()
    context.s34_before = _s34_database_state(context, {})


@when("the Administrator accepts ADD and rejects ALTER")
def finalize_maria_partial_pip(context: Context) -> None:
    """POST real staff decisions accepting ADD and rejecting ALTER.

    :param context: Prepared AT state. Example: actual ADD/ALTER primary keys.
    :return: None. Example: actual response and persisted terminal PIP retained.
    :raises AssertionError: Unauthorized response or unsuccessful finalization.
    """
    pip = context.s34_pip
    fields = {"action": "finalize"}
    for change in pip.changes.order_by("order", "pk"):
        decision = (
            PipChange.ADMIN_ACCEPT
            if change.change_type == "ADD"
            else PipChange.ADMIN_REJECT
        )
        fields[f"decision_{change.pk}"] = decision
        fields[f"note_{change.pk}"] = _S34_NOTE
    context.s34_started = timezone.now()
    with context.test.captureOnCommitCallbacks(execute=True) as callbacks:
        response = context.client.post(
            reverse("pip_admin_review", args=[pip.pk]),
            fields,
            HTTP_X_CSRFTOKEN=context.client.cookies["csrftoken"].value,
        )
        assert not mail.outbox
    assert len(callbacks) == 1 and response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("pip_detail", args=[pip.pk])
    assert response.wsgi_request.user.pk == context.cedar_dataset.user_ids["mchen"]
    assert response.wsgi_request._messages is not None
    context.s34_response = response


@then("Maria's total becomes 8700 rather than 8800")
def assert_maria_partial_total(context: Context) -> None:
    """Assert exact accepted-only totals, immutable award and publication effects.

    :param context: Finalized real AT state. Example: accepted_partial PIP42.
    :return: None. Example: Maria8700/Design7700 with one500 award, not8800.
    :raises AssertionError: Totals, rejected content, award or receipt differ.
    """
    pip = context.s34_pip
    pip.refresh_from_db()
    pip.playbook.refresh_from_db()
    accepted = pip.changes.get(change_type=PipChange.CHANGE_ADD)
    rejected = pip.changes.get(change_type=PipChange.CHANGE_ALTER)
    award = KarmaAward.objects.exclude(pk__in=context.s34_ledger_ids).get()
    added = Activity.objects.exclude(pk__in=context.s34_activity_ids).get()
    receipt = PlaybookVersion.objects.exclude(pk__in=context.s34_history_ids).get()
    omitted = {
        KarmaAward._meta.label_lower: (award.pk,),
        Activity._meta.label_lower: (added.pk,),
        PlaybookVersion._meta.label_lower: (receipt.pk,),
    }
    assert _s34_database_state(context, omitted) == context.s34_before
    assert pip.status == PIP.STATUS_ACCEPTED_PARTIAL
    assert accepted.admin_decision == PipChange.ADMIN_ACCEPT
    assert rejected.admin_decision == PipChange.ADMIN_REJECT
    assert accepted.admin_note == rejected.admin_note == _S34_NOTE
    assert (added.name, added.guidance, added.workflow_id) == (
        accepted.name,
        accepted.content,
        accepted.parent_workflow_id,
    )
    assert added.workflow.playbook_id == pip.playbook_id
    _s34_assert_award(pip, accepted, award)
    _s34_assert_publication(context, accepted, receipt)
    _s34_assert_scores(context)
    _s34_assert_notification(context)


@then("{points:d} points are attributed to the target Design category")
def minor_change_design_attribution_matches(context: Context, points: int) -> None:
    """Verify the minor decision's category credit, publication and local mail.

    :param context: Independently restored and finalized minor Example.
    :param points: Expected immutable target-category credit. Example: 100.
    :return: None after the ledger, publication, and notification agree.
    :raises AssertionError: If amounts, provenance, publication or mail differ.
    """
    assert points == _MINOR_POINTS
    maria_id = context.cedar_dataset.user_ids["mrodriguez"]
    projection = ExpertsService().project_user(maria_id)
    _assert_maria_pip_categories(
        projection.category_points, _MARIA_DESIGN_BEFORE + points
    )
    _assert_accepted_change_award(context, KarmaAward.SourceKind.MINOR, points)
    assert_maria_pip_target_version(context)
    assert_maria_pip_local_notification(context)


@then("her total remains {total:d}")
def nonaccepted_total_remains(context: Context, total: int) -> None:
    """Check every independent nonaccepted/rejected state and complete unchanged ledger snapshots, not only the last total.

    :param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
    :param total: Expected actual ledger total. Example: 8200.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: Actual domain, response or recorded boundary differs."""
    assert total == _MARIA_DESIGN_BEFORE + _MARIA_DEVELOPMENT
    assert tuple(row[0] for row in context.s35_observations) == _S35_STATES
    for observation in context.s35_observations:
        _s35_assert_observation(observation, total)
    assert _s35_database_state() == context.s35_baseline
    assert not mail.outbox
    maria_id = context.cedar_dataset.user_ids["mrodriguez"]
    assert ExpertsService().project_user(maria_id).total_points == total


def _s35_database_state(
    pip: PIP | None = None, client: Client | None = None
) -> S35DatabaseState:
    """Hash every real row, optionally normalizing only an allowed staff decision.

    :param pip: Current reviewed proposal, or None for exact state. Example: PIP42.
    :param client: Its authenticated client, or None. Example: Mike strict-CSRF client.
    :return: Immutable model/count/hash rows. Example: complete historical ledger hash.
    :raises AssertionError: If only one review normalization parameter is supplied.
    """
    assert (pip is None) == (client is None)
    session_key = client.session.session_key if client is not None else None
    snapshots: list[tuple[str, int, str]] = []
    for model in sorted(
        apps.get_models(include_auto_created=True),
        key=lambda item: item._meta.label_lower,
    ):
        label = model._meta.label_lower
        rows = list(model.objects.order_by("pk").values())
        for row in rows:
            omitted = frozenset()
            if (
                pip is not None
                and label == PIP._meta.label_lower
                and row["id"] == pip.pk
            ):
                omitted = _S35_PIP_FIELDS
            elif (
                pip is not None
                and label == PipChange._meta.label_lower
                and row["pip_id"] == pip.pk
            ):
                omitted = _S35_CHANGE_FIELDS
            elif label == "sessions.session" and row["session_key"] == session_key:
                omitted = _S35_SESSION_FIELDS
            for field in omitted:
                row.pop(field)
        payload = json.dumps(rows, sort_keys=True, default=str).encode()
        snapshots.append((label, len(rows), hashlib.sha256(payload).hexdigest()))
    return tuple(snapshots)


def _s35_finalize_rejection(context: Context, pip: PIP) -> int:
    """Finalize a saved ACCEPT as REJECT through real CSRF-protected staff HTTP.

    :param context: Real AT lifecycle with callback capture. Example: Cedar scenario.
    :param pip: Actual Reviewed fixture. Example: Maria's unapplied ADD Activity.
    :return: Actual locally delivered mail count. Example: one rejection notice.
    :raises AssertionError: If HTTP, notification or protected content differs.
    """
    client = Client(enforce_csrf_checks=True)
    staff = context.cedar_dataset.users_by_username["mchen"]
    client.force_login(staff)
    route = reverse("pip_admin_review", args=[pip.pk])
    assert client.get(route).status_code == 200
    csrf = client.cookies["csrftoken"].value
    change = pip.changes.get()
    assert change.admin_decision == PipChange.ADMIN_ACCEPT
    fields = {"action": "finalize"}
    fields[f"decision_{change.pk}"] = PipChange.ADMIN_REJECT
    fields[f"note_{change.pk}"] = _S35_REJECTION_NOTE
    before, started = _s35_database_state(pip, client), timezone.now()
    with context.test.captureOnCommitCallbacks(execute=True) as callbacks:
        response = client.post(route, fields, HTTP_X_CSRFTOKEN=csrf)
        assert not mail.outbox
    assert response.status_code == 302
    assert response.url == reverse("pip_detail", args=[pip.pk])
    assert len(callbacks) == 1 and client.session["_auth_user_id"] == str(staff.pk)
    pip.refresh_from_db()
    assert (
        started
        <= pip.decided_at
        <= pip.status_changed_at
        <= pip.updated_at
        <= timezone.now()
    )
    assert _s35_database_state(pip, client) == before
    return _s35_rejection_mail(pip)


def _s35_observe_nonaccepted(context: Context, status: str) -> S35Observation:
    """Observe one real eligibility case while its rows live, then roll back it alone.

    :param context: Real AT context. Example: independently restored Cedar baseline.
    :param status: Exact stored boundary. Example: processing_galdr.
    :return: Immutable actual outcome and before/after snapshots. Example: rejected/zero awards.
    :raises AssertionError: If real setup, decision or eligibility differs.
    """
    with transaction.atomic():
        dataset = load_cedar_baseline()
        fixture_status = (
            PIP.STATUS_REVIEWED if status == PIP.STATUS_REJECTED else status
        )
        pip = create_nonaccepted_pip_case(dataset, fixture_status)
        delivered = (
            _s35_finalize_rejection(context, pip)
            if status == PIP.STATUS_REJECTED
            else 0
        )
        before = _s35_database_state()
        outcomes = KarmaService.award_accepted_changes(
            pip=pip, correlation_id=f"s35_at:{status}"
        )
        after = _s35_database_state()
        values = _s35_case_values(dataset, pip, delivered)
        observed = (status, pip.status, before, after, outcomes, *values)
        transaction.set_rollback(True)
    return observed


def _s35_assert_observation(observed: S35Observation, total: int) -> None:
    """Check every independently recorded actual case rather than only the final total.

    :param observed: Real persisted-state observations before rollback. Example: Reviewed case.
    :param total: Expected unchanged Maria total. Example:8200.
    :return: None when ledger/content/status and notification agree.
    :raises AssertionError: If any recorded outcome differs from the contract.
    """
    status, stored, before, after, outcomes = observed[:5]
    projection, times, choices, target, delivered = observed[5:]
    assert status == stored and before == after and outcomes == ()
    assert projection[0:2] == (total, _DESIGN)
    assert dict(projection[2]) == {
        _DESIGN: _MARIA_DESIGN_BEFORE,
        _DEVELOPMENT: _MARIA_DEVELOPMENT,
    }
    assert times == (
        status != PIP.STATUS_DRAFT,
        status in (PIP.STATUS_REVIEWED, PIP.STATUS_REJECTED),
        status == PIP.STATUS_REJECTED,
    )
    assert target == (_TARGET_ID, _VERSION_BEFORE, _DESIGN, True)
    assert delivered == (1 if status == PIP.STATUS_REJECTED else 0)
    if status in (PIP.STATUS_REVIEWED, PIP.STATUS_REJECTED):
        expected = (
            PipChange.ADMIN_REJECT
            if status == PIP.STATUS_REJECTED
            else PipChange.ADMIN_ACCEPT
        )
        assert choices == (PipChange.GALDR_ACCEPT, expected)


def _s35_rejection_mail(pip: PIP) -> int:
    """Verify the actual delivered rejection before owner-local outbox cleanup.

    :param pip: Really rejected proposal. Example: Maria's ADD Activity PIP42.
    :return: Actual local delivery count. Example: one message.
    :raises AssertionError: If recipient, decision or publication wording differs.
    """
    (sent,) = mail.outbox
    assert sent.to == [pip.created_by.email] and not sent.cc and not sent.bcc
    assert sent.subject == f'Your PIP "{pip.title}" — Rejected ✗'
    assert all(
        part in sent.body
        for part in ("Overall: Rejected.", "Decision: REJECT", _S35_REJECTION_NOTE)
    )
    assert "is now v" not in sent.body
    return len(mail.outbox)


def _s35_case_values(dataset: CedarDataset, pip: PIP, delivered: int) -> S35Observation:
    """Read immutable real projection/status/target facts before case rollback.

    :param dataset: Actual imported Cedar records. Example: Maria and Hana6106.
    :param pip: Live independently prepared proposal. Example: Reviewed eligibility case.
    :param delivered: Actual locally observed message count. Example:1 for rejected.
    :return: Immutable live facts. Example:8200/Design and unchanged target2.0.
    :raises AssertionError: If the proposed Activity was actually applied.
    """
    projection = ExpertsService().project_user(dataset.user_ids["mrodriguez"])
    pip.refresh_from_db()
    change = pip.changes.get()
    assert not change.parent_workflow.activities.filter(name=change.name).exists()
    return (
        (
            projection.total_points,
            projection.primary_category,
            projection.category_points,
        ),
        (
            pip.submitted_at is not None,
            pip.reviewed_at is not None,
            pip.decided_at is not None,
        ),
        (change.galdr_recommendation, change.admin_decision),
        (
            pip.playbook_id,
            pip.playbook.version,
            pip.playbook.category,
            pip.playbook.author_id == dataset.user_ids["hkim"],
        ),
        delivered,
    )


def _s34_database_state(
    context: Context, omitted: Mapping[str, tuple[int, ...]]
) -> S35DatabaseState:
    """Fingerprint every original row while allowing only this decision's writes.

    :param context: Prepared partial-decision context. Example: reviewed PIP42.
    :param omitted: Exact verified new row identities. Example: one award/activity/receipt.
    :return: Ordered all-model count/digest tuples. Example:2129 immutable old awards.
    :raises AssertionError: Missing real authenticated session identity.
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
            for field in _s34_allowed_fields(context, label, row):
                row.pop(field)
        payload = json.dumps(rows, sort_keys=True, default=str).encode()
        snapshots.append((label, len(rows), hashlib.sha256(payload).hexdigest()))
    return tuple(snapshots)


def _s34_allowed_fields(
    context: Context, label: str, row: Mapping[str, object]
) -> frozenset[str]:
    """Normalize only current decision fields, target version and staff session.

    :param context: Actual partial fixture and prepared client. Example: Mike session.
    :param label: Actual model label. Example: methodology.pipchange.
    :param row: Real persisted row. Example: the current proposal change.
    :return: Precisely permitted fields. Example: admin_decision/admin_note.
    :raises AssertionError: Prepared staff session is absent.
    """
    pip = context.s34_pip
    if label == PIP._meta.label_lower and row["id"] == pip.pk:
        return _S35_PIP_FIELDS
    if label == PipChange._meta.label_lower and row["pip_id"] == pip.pk:
        return _S35_CHANGE_FIELDS
    if label == Playbook._meta.label_lower and row["id"] == pip.playbook_id:
        return frozenset(("version", "updated_at"))
    if label == "sessions.session":
        assert context.client.session.session_key
        if row["session_key"] == context.client.session.session_key:
            return _S35_SESSION_FIELDS
    return frozenset()


def _s34_totals() -> dict[int, int]:
    """Read independent ledger totals for every actual account, including zeros.

    :return: Every actual user/total pair. Example: Maria8200 and Mike12450.
    :raises DatabaseError: The owned test database cannot be queried.
    """
    return {
        pk: KarmaAward.objects.filter(recipient_id=pk).aggregate(total=Sum("points"))[
            "total"
        ]
        or 0
        for pk in User.objects.order_by("pk").values_list("pk", flat=True)
    }


def _s34_assert_award(pip: PIP, accepted: PipChange, award: KarmaAward) -> None:
    """Check every field of the sole new accepted-change ledger row.

    :param pip: Actually finalized partial proposal. Example: Maria's PIP42.
    :param accepted: Sole accepted ADD Activity. Example: change43.
    :param award: Sole newly persisted global award. Example:500 Design points.
    :return: None. Example: exact identity, category, amount and decision timestamp.
    :raises AssertionError: Any immutable award field differs.
    """
    assert KarmaAward.objects.values().get(pk=award.pk) == {
        "id": award.pk,
        "recipient_id": pip.created_by_id,
        "event_identity": f"accepted_change:{accepted.pk}",
        "event_channel": EventChannel.ACCEPTED_CHANGE,
        "source_kind": KarmaAward.SourceKind.MAJOR,
        "points": _MAJOR_POINTS,
        "category": _DESIGN,
        "playbook_id_snapshot": pip.playbook_id,
        "change_id_snapshot": accepted.pk,
        "entity_type_snapshot": None,
        "entity_id_snapshot": None,
        "occurred_at": pip.decided_at,
    }


def _s34_assert_publication(
    context: Context, accepted: PipChange, receipt: PlaybookVersion
) -> None:
    """Verify the one real major receipt and accepted-only publication summary.

    :param context: Real finalization and lower time bound. Example: Hana2.0 to3.0.
    :param accepted: Actual accepted ADD. Example: new Activity43.
    :param receipt: Sole new global version receipt. Example: source=pip/is_major.
    :return: None. Example: one PIP receipt containing only accepted43.
    :raises AssertionError: Version, snapshot, attribution or timestamps differ.
    """
    pip = context.s34_pip
    assert receipt.playbook_id == pip.playbook_id and receipt.pip_id == pip.pk
    assert receipt.version_number == pip.playbook.version == _VERSION_AFTER
    assert receipt.source == VersionSource.PIP_SOURCE and receipt.is_major
    assert receipt.created_by_id == context.cedar_dataset.user_ids["mchen"]
    assert receipt.snapshot_data == {
        "pip_id": pip.pk,
        "playbook_name": pip.playbook.name,
        "version_before": "2.0",
        "version_after": "3.0",
        "accepted_change_ids": [accepted.pk],
        "category": _DESIGN,
    }
    assert receipt.change_summary == f"ADD {accepted.name}"
    assert pip.playbook_versions.count() == 1
    assert context.s34_started <= receipt.created_at <= timezone.now()
    assert (
        context.s34_started
        <= pip.decided_at
        <= pip.status_changed_at
        <= pip.updated_at
        <= timezone.now()
    )
    assert timezone.is_aware(pip.decided_at)
    assert context.s34_started <= pip.playbook.updated_at <= timezone.now()


def _s34_assert_scores(context: Context) -> None:
    """Require exactly Maria's500 increment and unchanged totals for all others.

    :param context: Independent pre-decision all-user totals. Example: Maria8200.
    :return: None. Example:8700/7700/1000, Hana5800 and Mike12450.
    :raises AssertionError: Any wrong recipient, rejected100 or projection drift.
    """
    pip = context.s34_pip
    expected = dict(context.s34_totals)
    expected[pip.created_by_id] += _MAJOR_POINTS
    assert _s34_totals() == expected
    projection = ExpertsService().project_user(pip.created_by_id)
    assert projection.total_points == 8700 and projection.total_points != 8800
    assert dict(projection.category_points) == {_DESIGN: 7700, _DEVELOPMENT: 1000}
    assert expected[context.cedar_dataset.user_ids["hkim"]] == 5800
    assert expected[context.cedar_dataset.user_ids["mchen"]] == 12450


def _s34_assert_notification(context: Context) -> None:
    """Inspect truthful feedback and the one actually executed postcommit email.

    :param context: Real response and decided proposal. Example: partial ADD/ALTER.
    :return: None. Example: both decisions/version3.0, no invented Karma earnings.
    :raises AssertionError: Message, recipient, decisions or mail scope differs.
    """
    pip = context.s34_pip
    assert [
        str(message) for message in context.s34_response.wsgi_request._messages
    ] == ["PIP partially accepted — changes applied."]
    (sent,) = mail.outbox
    assert sent.to == [pip.created_by.email] and not sent.cc and not sent.bcc
    assert sent.subject == f'Your PIP "{pip.title}" — Partially accepted'
    assert "Overall: Partially accepted." in sent.body
    assert f"{pip.playbook.name} is now v3.0." in sent.body
    assert reverse("pip_detail", args=[pip.pk]) in sent.body and _S34_NOTE in sent.body
    for change in pip.changes.order_by("order", "pk"):
        assert f'{change.change_type} Activity "{change.name}"' in sent.body
        assert f"Decision: {change.admin_decision}" in sent.body
    assert all(value not in sent.body for value in ("Karma", "8700", "500"))
