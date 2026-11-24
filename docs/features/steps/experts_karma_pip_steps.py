"""Karma acceptance bindings for the existing staff decision flow."""

from __future__ import annotations

from decimal import Decimal

from behave import given, then, when
from behave.runner import Context
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from methodology.models import (
    Activity,
    Artifact,
    EventChannel,
    KarmaAward,
    PipChange,
    Skill,
    VersionSource,
)
from methodology.services.experts_service import ExpertsService
from tests.support.experts_data import CedarDataset, create_reviewed_major_add_pip

_TARGET_ID = 6106
_TARGET_NAME = "Accessible Forms Review"
_VERSION_BEFORE = Decimal("2.0")
_VERSION_AFTER = Decimal("3.0")
_DESIGN = "design"
_DEVELOPMENT = "development"
_MARIA_DESIGN_BEFORE = 7200
_MARIA_DEVELOPMENT = 1000
_MAJOR_POINTS = 500
_RELEASE = KarmaAward.SourceKind.RELEASE


@given("Maria's new PIP targets Hana's Accessible Forms Review version 2.0")
def prepare_maria_major_add_target(context: Context) -> None:
    """Retain the independently restored real target before the Example selects type.

    :param context: Isolated AT context. Example: context.cedar_dataset from S03.
    :return: None. Example: real target 6106 is retained at version 2.0.
    :raises AssertionError: If baseline authorship or version differs.
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
    assert dict(projection.category_points) == {
        _DESIGN: _MARIA_DESIGN_BEFORE,
        _DEVELOPMENT: _MARIA_DEVELOPMENT,
    }
    context.major_add_target = target
    context.major_add_ledger_count = KarmaAward.objects.count()
    context.major_add_release_count = KarmaAward.objects.filter(
        source_kind=_RELEASE
    ).count()
    context.major_add_version_count = target.versions.count()
    context.major_add_other_projections = tuple(
        experts.project_user(user_id) for user_id in (hana.pk, staff.pk)
    )
    assert not mail.outbox


@when("an Administrator accepts its eligible ADD {entity} change")
@when("an Administrator accepts Maria's independent {operation} {entity} change")
def accept_maria_change(context: Context, entity: str, operation: str = "ADD") -> None:
    """Finalize one explicitly selected major/minor real reviewed fixture through the existing staff POST.

    :param context: Real Cedar state and actual response. Example: Hana target v2.0.
    :param entity: Exact major or minor matrix entity. Example: Activity or Workflow.
    :param operation: Exact operation, default ADD for the major phrase. Example: ALTER.
    :return: None after the real decision applies the selected change once.
    :raises AssertionError: If the real permission, decision or content differs.
    :raises NotImplementedError: If the independent minor fixture is not bound yet.
    """
    if "major_add_target" not in context:
        raise NotImplementedError(
            "The independent minor-change case is not implemented."
        )
    assert operation == PipChange.CHANGE_ADD
    dataset: CedarDataset = context.cedar_dataset
    pip = create_reviewed_major_add_pip(dataset, entity)
    assert pip.created_by_id == dataset.user_ids["mrodriguez"]
    assert pip.playbook_id == context.major_add_target.pk
    change = pip.changes.get()
    assert (change.change_type, change.entity_type) == (operation, entity)
    assert _matching_added_content_count(change) == 0
    _finalize_maria_single_change(context, change)
    assert _matching_added_content_count(change) == 1
    context.maria_accepted_change = change


def _finalize_maria_single_change(context: Context, change: PipChange) -> None:
    """POST one acceptance as Cedar's existing staff account.

    :param context: Real Django test client and Cedar fixture.
    :param change: Undecided persisted proposal change, for example ADD Skill.
    :return: None after the production callback is captured and run.
    :raises AssertionError: If the decision, HTTP result or callback differs.
    """
    pip = change.pip
    assert pip.status == pip.STATUS_REVIEWED and not change.admin_decision
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
        assert dict(projection.category_points) == {
            _DESIGN: design,
            _DEVELOPMENT: _MARIA_DEVELOPMENT,
        }
        _assert_major_award(context, context.maria_accepted_change)


def _assert_major_award(context: Context, change: PipChange) -> None:
    """Match the single new event to the real terminal decision and recipient.

    :param context: Cedar acceptance state with the original ledger counts.
    :param change: Accepted proposal change. Example: ADD Activity.
    :return: None when award and unaffected contributions match.
    :raises AssertionError: If award identity, provenance, counts or totals differ.
    """
    pip = change.pip
    award = KarmaAward.objects.get(event_identity=f"accepted_change:{change.pk}")
    assert (
        award.recipient_id,
        award.playbook_id_snapshot,
        award.change_id_snapshot,
    ) == (pip.created_by_id, pip.playbook_id, change.pk)
    assert (award.event_channel, award.source_kind, award.points, award.category) == (
        EventChannel.ACCEPTED_CHANGE,
        KarmaAward.SourceKind.MAJOR,
        _MAJOR_POINTS,
        _DESIGN,
    )
    assert award.occurred_at == pip.decided_at and timezone.is_aware(award.occurred_at)
    assert KarmaAward.objects.count() == context.major_add_ledger_count + 1
    assert (
        KarmaAward.objects.filter(source_kind=_RELEASE).count()
        == context.major_add_release_count
    )
    experts = ExpertsService()
    for before in context.major_add_other_projections:
        assert experts.project_user(before.user_id) == before


@then("the target playbook is version 3.0")
def assert_major_add_target_version(context: Context) -> None:
    """Assert one actual major publication and its accepted-change receipt.

    :param context: Context with the finalized target. Example: playbook 6106.
    :return: None. Example: one new PIP version at 3.0.
    :raises AssertionError: If the publication or its receipt differs.
    """
    change: PipChange = context.maria_accepted_change
    pip = change.pip
    target = context.major_add_target
    target.refresh_from_db()
    assert target.version == _VERSION_AFTER
    assert target.versions.count() == context.major_add_version_count + 1
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
def assert_major_add_local_notification(context: Context) -> None:
    """Assert the existing postcommit email in local-memory capture.

    :param context: Real isolated AT context. Example: finalized ADD Skill case.
    :return: None. Example: one accepted decision email to Maria includes 3.0.
    :raises AssertionError: If recipient, body, count or delivery timing differs.
    """
    change: PipChange = context.maria_accepted_change
    maria = context.cedar_dataset.users_by_username["mrodriguez"]
    (sent,) = mail.outbox
    assert sent.to == [maria.email] and "Accepted" in sent.subject
    assert f'ADD {change.entity_type} "{change.name}"' in sent.body
    assert "Decision: ACCEPT" in sent.body and f"is now v{_VERSION_AFTER}" in sent.body


@when("Maria's PIP is draft, submitted, processing, reviewed or rejected without an accepted eligible change")
def exercise_maria_nonaccepted_states(context: Context) -> None:
    """Record five independently restored cases and real rejected finalization.

    :param context: Real AT context. Example: context.cedar_dataset.
    :return: None. Example: five persisted outcomes retained for shared assertions.
    :raises AssertionError: If any case awards points or changes target content.
    """
    raise NotImplementedError()

@given("Maria's PIP contains one ADD Activity and one ALTER Activity")
def prepare_maria_partial_pip(context: Context) -> None:
    """Prepare the independent two-change fixture using the shared Cedar context.

    :param context: Behave state. Example: context.cedar_dataset from S03.
    :return: None. Example: real reviewed proposal retained for finalization.
    :raises AssertionError: Baseline or fixture violates Section C.
    """
    raise NotImplementedError()

@when('the Administrator accepts ADD and rejects ALTER')
def finalize_maria_partial_pip(context: Context) -> None:
    """POST real staff decisions accepting ADD and rejecting ALTER.

    :param context: Prepared AT state. Example: actual ADD/ALTER primary keys.
    :return: None. Example: actual response and persisted terminal PIP retained.
    :raises AssertionError: Unauthorized response or unsuccessful finalization.
    """
    raise NotImplementedError()

@then("Maria's total becomes 8700 rather than 8800")
def assert_maria_partial_total(context: Context) -> None:
    """Assert exact accepted-only totals, immutable award and publication effects.

    :param context: Finalized real AT state. Example: accepted_partial PIP42.
    :return: None. Example: Maria8700/Design7700 with one500 award, not8800.
    :raises AssertionError: Totals, rejected content, award or receipt differ.
    """
    raise NotImplementedError()

@then('{points:d} points are attributed to the target Design category')
def minor_change_design_attribution_matches(context: Context, points: int) -> None:
    """Inspect the actual new immutable award: Maria recipient, target Design category, accepted change identity and original decision time.

:param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
:param points: Expected immutable target-category credit. Example: 100.
:return: None when the described real observation holds. Example: None.
:raises AssertionError: Actual domain, response or recorded boundary differs."""
    raise NotImplementedError()

@then('her total remains {total:d}')
def nonaccepted_total_remains(context: Context, total: int) -> None:
    """Check every independent nonaccepted/rejected state and complete unchanged ledger snapshots, not only the last total.

:param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
:param total: Expected actual ledger total. Example: 8200.
:return: None when the described real observation holds. Example: None.
:raises AssertionError: Actual domain, response or recorded boundary differs."""
    raise NotImplementedError()
