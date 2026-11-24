from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pytest
from behave.model import ScenarioOutline
from behave.parser import parse_file
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.db import connection, transaction
from django.db.models import Model, Sum
from django.http import HttpResponse
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from pytest import LogCaptureFixture

from methodology.models import (
    Activity,
    Agent,
    Artifact,
    KarmaAward,
    Phase,
    PipChange,
    ProcessImprovementProposal,
    Rule,
    Skill,
    Workflow,
)
from methodology.services.pip_admin_service import PIPAdminService
from tests.support.experts_data import CedarDataset, load_cedar_baseline
from tests.support.experts_logs import capture_experts_logs
from tests.support.experts_pip_minor import (
    MINOR_CASES,
    MinorPipCase,
    assert_minor_change_applied,
    create_reviewed_minor_pip,
)
from tests.support.log_story import assert_log_story

_FEATURE = (
    Path(__file__).resolve().parents[2]
    / "docs/features/act-18-experts/karma-accrual.feature"
)
_OUTLINE = "KARMA-PIP-02 Award an accepted minor change"
_TARGET_ID = 6106
_VERSION_BEFORE = Decimal("2.0")
_VERSION_AFTER = Decimal("3.0")
_MINOR_POINTS = 100
_REVIEW_NOTE = "Confirmed the accessibility review change."
_POLICY_LOGGER = "methodology.services.karma_service"
_ADMIN_LOGGER = "methodology.services.pip_admin_service"
_APPLY_LOGGER = "methodology.services.pip_apply_changes_service"
_AWARD_STORY = "KarmaService.award_accepted_changes"
_CLASSIFICATION_STORY = "KarmaService._accepted_change_policy"
_DECISION_STORY = "PIPAdminService._award_finalized_pip"
_RELATIONSHIP = "supported existing relationship"
_EXCLUDED_MAJOR_ROWS = (("ADD", "Activity"), ("ADD", "Skill"), ("ADD", "Artifact"))
_ADDED_MODELS = {"Workflow": Workflow, "Phase": Phase, "Agent": Agent, "Rule": Rule}
_NAME_AND_CONTENT = {
    "Activity": ("name", "guidance"),
    "Skill": ("title", "content"),
    "Artifact": ("name", "description"),
    "Workflow": ("name", "description"),
    "Phase": ("name", "description"),
    "Agent": ("name", "description"),
    "Rule": ("title", "content"),
}


@dataclass(frozen=True)
class _RecordedRows:
    """Full persisted values for ledger and target history comparisons."""

    ledger: list[dict[str, object]]
    history: list[dict[str, object]]


def test_minor_case_matrix_with_literal_examples_matches_all_twenty_rows() -> None:
    """Prove literal rows equal exact feature Examples, with no sampled coverage.

    :return: None. Example: exactly twenty unique correctly ordered rows.
    :raises AssertionError: For missing, extra, duplicate or excluded rows.
    """
    feature = parse_file(str(_FEATURE))
    (outline,) = [
        scenario for scenario in feature.scenarios if scenario.name == _OUTLINE
    ]
    assert isinstance(outline, ScenarioOutline)
    (examples,) = outline.examples
    assert examples.table.headings == ["operation", "entity"]
    rows = tuple(tuple(row.cells) for row in examples.table.rows)
    assert rows == MINOR_CASES
    assert len(rows) == len(set(rows)) == 20
    assert set(rows).isdisjoint(_EXCLUDED_MAJOR_ROWS)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(("operation", "entity"), MINOR_CASES)
def test_minor_fixture_with_each_literal_row_persists_independent_reviewed_change(
    operation: str, entity: str, mailoutbox: list[EmailMessage]
) -> None:
    """Verify persisted pre-finalization state for every independently loaded Example.

    :param operation: Exact operation. Example: "UNLINK".
    :param entity: Exact case label. Example: "supported existing relationship".
    :param mailoutbox: Real locmem mail capture. Example: [] before finalization.
    :return: None. Example: real reviewed, undecided UNLINK of an existing pair.
    :raises AssertionError: If setup points, publication, identity or change differ.
    """
    cedar = load_cedar_baseline()
    prior_ledger = list(KarmaAward.objects.order_by("pk").values())
    book = cedar.playbooks_by_pk[_TARGET_ID]
    prior_versions = list(book.versions.order_by("pk").values())

    case = create_reviewed_minor_pip(cedar, operation=operation, entity=entity)

    assert (case.operation, case.entity) == (operation, entity)
    _assert_reviewed_minor_case(case, cedar)
    assert list(book.versions.order_by("pk").values()) == prior_versions
    assert not case.pip.playbook_versions.exists()
    assert list(KarmaAward.objects.order_by("pk").values()) == prior_ledger
    assert not mailoutbox


def _assert_reviewed_minor_case(case: MinorPipCase, cedar: CedarDataset) -> None:
    """Verify the real proposal and the original operation-specific precondition."""
    _assert_reviewed_minor_identity(case, cedar)
    if case.entity == _RELATIONSHIP:
        _assert_minor_relationship_fixture(case)
    else:
        _assert_minor_entity_fixture(case)


def _assert_reviewed_minor_identity(case: MinorPipCase, cedar: CedarDataset) -> None:
    """Verify saved Cedar roles, released target and undecided prerequisite state."""
    pip = case.pip
    pip.refresh_from_db()
    book = pip.playbook
    maria, hana, mike = (
        cedar.users_by_username[username]
        for username in ("mrodriguez", "hkim", "mchen")
    )
    maria.refresh_from_db()
    mike.refresh_from_db()
    assert not maria.is_staff and not maria.is_superuser
    assert mike.is_staff and mike.pk not in (maria.pk, hana.pk)
    assert pip.created_by_id == maria.pk
    assert (book.pk, book.author_id) == (_TARGET_ID, hana.pk)
    assert (book.name, book.category) == ("Accessible Forms Review", "design")
    assert (book.status, book.visibility) == ("released", "public")
    assert book.version == _VERSION_BEFORE
    assert pip.status == pip.STATUS_REVIEWED and pip.decided_at is None
    assert timezone.is_aware(pip.submitted_at) and timezone.is_aware(pip.reviewed_at)
    assert (
        pip.created_at <= pip.submitted_at <= pip.reviewed_at <= pip.status_changed_at
    )
    assert pip.changes.get() == case.change
    case.change.refresh_from_db()
    assert case.change.change_type == case.operation
    assert case.change.galdr_recommendation == PipChange.GALDR_ACCEPT
    assert case.change.admin_decision == PipChange.ADMIN_UNSET
    assert not case.change.admin_note


def _assert_minor_relationship_fixture(case: MinorPipCase) -> None:
    """Verify exact persisted relationship roles and initial M2M state."""
    change = case.change
    skill = case.targets["Skill"]
    activity = case.targets["Activity"]
    assert isinstance(skill, Skill) and isinstance(activity, Activity)
    assert skill.playbook_id == activity.workflow.playbook_id == case.pip.playbook_id
    assert change.entity_type == "" and change.target_id is None
    assert change.relationship_type == PipChange.REL_SKILL_ACTIVITY
    assert (change.source_entity_type, change.source_entity_ref) == (
        "Skill",
        str(skill.pk),
    )
    assert (change.target_entity_type, change.target_entity_ref) == (
        "Activity",
        str(activity.pk),
    )
    assert activity.skills.filter(pk=skill.pk).exists() == (case.operation == "UNLINK")
    assert case.original_target_id is None and change.content.strip()


def _assert_minor_entity_fixture(case: MinorPipCase) -> None:
    """Verify precise persisted identity, ownership and meaningful proposed payload."""
    change = case.change
    assert change.entity_type == case.entity and not change.relationship_type
    name_field, content_field = _NAME_AND_CONTENT[case.entity]
    assert change.content == case.expected_content and change.content.strip()
    if case.operation == "ADD":
        assert change.target_id is None and case.original_target_id is None
        assert change.name == case.expected_name and change.name.strip()
        model = _ADDED_MODELS[case.entity]
        assert not model.objects.filter(
            playbook_id=case.pip.playbook_id, **{name_field: change.name}
        ).exists()
        return
    target = case.targets[case.entity]
    target.refresh_from_db()
    assert target.playbook.pk == case.pip.playbook_id
    assert target.pk == case.original_target_id == change.target_id
    original_name = getattr(target, name_field)
    if case.operation == "ALTER":
        assert change.name == case.expected_name and change.name.strip()
        assert change.name != original_name
        assert change.content != getattr(target, content_field)
    else:
        assert change.target_name_snapshot == original_name
    _assert_minor_target_dependencies(case, target)


def _assert_minor_target_dependencies(case: MinorPipCase, target: Model) -> None:
    """Check producer ownership, artifact metadata and safe deletion prerequisites."""
    if isinstance(target, Phase):
        assert not target.activities.exists()
    if isinstance(target, Artifact):
        assert target.produced_by.workflow.playbook_id == target.playbook_id
        if case.operation == "ALTER":
            change = case.change
            assert (change.artifact_type, change.artifact_is_required) == (
                target.type,
                target.is_required,
            )
    if case.operation == "DROP" and isinstance(target, (Workflow, Activity)):
        dependents = (
            target.activities
            if isinstance(target, Workflow)
            else target.output_artifacts
        )
        assert not dependents.exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(("operation", "entity"), MINOR_CASES)
def test_finalize_pip_with_each_minor_change_applies_once_and_awards_submitter(
    client: Client,
    caplog: LogCaptureFixture,
    operation: str,
    entity: str,
    mailoutbox: list[EmailMessage],
) -> None:
    """Prove real POST, concrete effect, singleton receipt, totals and local mail.

    :param client: Real Django client. Example: authenticated staff Mike.
    :param caplog: Real apply logger capture. Example: no apply beat on retry.
    :param operation: Exact matrix operation. Example: "ALTER".
    :param entity: Exact matrix entity. Example: "Artifact".
    :param mailoutbox: Local Django mail. Example: one decision message.
    :return: None. Example: Maria 8300/7300, target 3.0, one 100-point minor.
    :raises AssertionError: If any Section D invariant fails.
    """
    cedar = load_cedar_baseline()
    case = create_reviewed_minor_pip(cedar, operation=operation, entity=entity)
    _assert_reviewed_minor_case(case, cedar)
    staff = cedar.users_by_username["mchen"]
    client.force_login(staff)
    _assert_cedar_totals(case, staff, accepted=False)
    before = _recorded_rows(case)
    assert not mailoutbox

    with capture_experts_logs(caplog, (_APPLY_LOGGER,)):
        _assert_decision_redirect(_post_acceptance(client, case), case)
    assert any(record.name == _APPLY_LOGGER for record in caplog.records)
    _assert_applied_and_awarded(case, staff, before)
    _assert_decision_mail(case, mailoutbox)
    decided_at = case.pip.decided_at
    after = _recorded_rows(case)

    with capture_experts_logs(caplog, (_APPLY_LOGGER,)):
        caplog.clear()
        _assert_decision_redirect(_post_acceptance(client, case), case)
    assert not any(record.name == _APPLY_LOGGER for record in caplog.records)
    _assert_applied_and_awarded(case, staff, before)
    assert case.pip.decided_at == decided_at
    assert _recorded_rows(case) == after
    _assert_decision_mail(case, mailoutbox)


@pytest.mark.django_db(transaction=True)
def test_finalize_pip_with_minor_service_call_preserves_proposal_return(
    mailoutbox: list[EmailMessage],
) -> None:
    """Prove legacy direct finalization returns the actual persisted proposal.

    :param mailoutbox: Local Django mail. Example: empty until the owning commit.
    :return: None. Example: same accepted PIP PK with one award/version receipt.
    :raises AssertionError: If return contract or domain effects differ.
    """
    cedar = load_cedar_baseline()
    case = create_reviewed_minor_pip(cedar, operation="DROP", entity="Phase")
    staff = cedar.users_by_username["mchen"]
    before = _recorded_rows(case)
    phase = Phase.objects.values().get(pk=case.original_target_id)

    with transaction.atomic():
        _finalize_with_saved_choice(case, staff)
        _assert_applied_and_awarded(case, staff, before)
        assert not mailoutbox
        transaction.set_rollback(True)

    _assert_reviewed_minor_identity(case, cedar)
    assert _recorded_rows(case) == before
    assert Phase.objects.values().get(pk=case.original_target_id) == phase
    assert not mailoutbox
    _finalize_with_saved_choice(case, staff)
    _assert_applied_and_awarded(case, staff, before)
    _assert_decision_mail(case, mailoutbox)


@pytest.mark.django_db(transaction=True)
def test_finalize_pip_with_nonstaff_preserves_minor_target_and_ledger(
    client: Client, mailoutbox: list[EmailMessage]
) -> None:
    """Prove unchanged authorization denies a real nonstaff finalization POST.

    :param client: Real client. Example: Maria authenticated without staff.
    :param mailoutbox: Local Django mail. Example: empty after the denial.
    :return: None. Example: 403, unchanged content/version/ledger, no mail.
    :raises AssertionError: If denial mutates state or awards points.
    """
    cedar = load_cedar_baseline()
    case = create_reviewed_minor_pip(cedar, operation="ALTER", entity="Phase")
    before = _recorded_rows(case)
    phase = Phase.objects.values().get(pk=case.original_target_id)
    client.force_login(cedar.users_by_username["mrodriguez"])

    assert _post_acceptance(client, case).status_code == 403

    _assert_reviewed_minor_identity(case, cedar)
    assert _recorded_rows(case) == before
    assert Phase.objects.values().get(pk=case.original_target_id) == phase
    assert not mailoutbox


def _recorded_rows(case: MinorPipCase) -> _RecordedRows:
    """Snapshot all ledger entries and the target's entire version history."""
    return _RecordedRows(
        ledger=list(KarmaAward.objects.order_by("pk").values()),
        history=list(case.pip.playbook.versions.order_by("pk").values()),
    )


def _post_acceptance(client: Client, case: MinorPipCase) -> HttpResponse:
    """Submit the existing admin review form for the fixture's single change."""
    return client.post(
        reverse("pip_admin_review", kwargs={"pk": case.pip.pk}),
        {
            "action": "finalize",
            f"decision_{case.change.pk}": PipChange.ADMIN_ACCEPT,
            f"note_{case.change.pk}": _REVIEW_NOTE,
        },
    )


def _assert_decision_redirect(response: HttpResponse, case: MinorPipCase) -> None:
    """Check the decision ends on the persisted proposal's details."""
    assert response.status_code == 302
    assert response["Location"] == reverse("pip_detail", kwargs={"pk": case.pip.pk})


def _finalize_with_saved_choice(case: MinorPipCase, staff: User) -> None:
    """Save the legitimate staff choice and exercise the legacy two-argument call."""
    pip = case.pip
    PIPAdminService.save_decisions(
        pip, staff, {case.change.pk: (PipChange.ADMIN_ACCEPT, _REVIEW_NOTE)}
    )
    result = PIPAdminService.finalize_pip(pip, staff)
    assert isinstance(result, ProcessImprovementProposal)
    assert result.pk == pip.pk and result.status == pip.STATUS_ACCEPTED
    persisted = ProcessImprovementProposal.objects.get(pk=result.pk)
    assert (
        persisted.status == result.status and persisted.decided_at == result.decided_at
    )


def _assert_applied_and_awarded(
    case: MinorPipCase, staff: User, before: _RecordedRows
) -> None:
    """Check the committed case against the independent effect and award expectations."""
    pip, change = case.pip, case.change
    pip.refresh_from_db()
    change.refresh_from_db()
    assert pip.status == pip.STATUS_ACCEPTED
    assert timezone.is_aware(pip.decided_at) and pip.decided_at >= pip.reviewed_at
    assert pip.changes.get() == change
    assert (change.admin_decision, change.admin_note) == (
        PipChange.ADMIN_ACCEPT,
        _REVIEW_NOTE,
    )
    assert_minor_change_applied(case)
    _assert_pip_publication(case, staff, before.history)
    _assert_minor_award(case, before.ledger)
    _assert_cedar_totals(case, staff, accepted=True)


def _assert_pip_publication(
    case: MinorPipCase, staff: User, prior_history: list[dict[str, object]]
) -> None:
    """Verify one 3.0 PIP receipt with the actual change and unchanged history."""
    pip = case.pip
    receipt = pip.playbook_versions.get()
    assert receipt.playbook_id == pip.playbook_id == _TARGET_ID
    assert receipt.version_number == pip.playbook.version == _VERSION_AFTER
    assert (
        receipt.source == "pip"
        and receipt.is_major
        and receipt.created_by_id == staff.pk
    )
    assert receipt.snapshot_data == {
        "pip_id": pip.pk,
        "playbook_name": "Accessible Forms Review",
        "version_before": "2.0",
        "version_after": "3.0",
        "accepted_change_ids": [case.change.pk],
        "category": "design",
    }
    other_versions = pip.playbook.versions.exclude(pk=receipt.pk)
    assert list(other_versions.order_by("pk").values()) == prior_history


def _assert_minor_award(
    case: MinorPipCase, prior_ledger: list[dict[str, object]]
) -> None:
    """Verify the only ledger addition is Maria's original 100-point Design receipt."""
    pip, change = case.pip, case.change
    award = KarmaAward.objects.get(event_identity=f"accepted_change:{change.pk}")
    assert (award.event_channel, award.source_kind, award.points, award.category) == (
        "accepted_change",
        "minor",
        _MINOR_POINTS,
        "design",
    )
    assert award.recipient_id == pip.created_by_id
    assert award.playbook_id_snapshot == pip.playbook_id == _TARGET_ID
    assert award.change_id_snapshot == change.pk
    assert award.entity_id_snapshot == case.original_target_id
    assert award.entity_type_snapshot == (
        case.entity if case.original_target_id is not None else None
    )
    assert award.occurred_at == pip.decided_at and timezone.is_aware(award.occurred_at)
    assert (
        list(KarmaAward.objects.exclude(pk=award.pk).order_by("pk").values())
        == prior_ledger
    )


def _assert_cedar_totals(case: MinorPipCase, staff: User, *, accepted: bool) -> None:
    """Check Maria's category totals and the other actors' unchanged balances."""
    maria_totals = _karma_by_category(case.pip.created_by_id)
    assert maria_totals == {"design": 7300 if accepted else 7200, "development": 1000}
    assert sum(maria_totals.values()) == (8300 if accepted else 8200)
    assert sum(_karma_by_category(case.pip.playbook.author_id).values()) == 5800
    assert sum(_karma_by_category(staff.pk).values()) == 12450


def _karma_by_category(user_id: int) -> dict[str, int]:
    """Read category balances directly from the persisted ledger."""
    return dict(
        KarmaAward.objects.filter(recipient_id=user_id)
        .values("category")
        .annotate(total=Sum("points"))
        .values_list("category", "total")
    )


def _assert_decision_mail(case: MinorPipCase, mailoutbox: list[EmailMessage]) -> None:
    """Check the existing postcommit mail contains the accepted change and version."""
    (sent,) = mailoutbox
    pip, change = case.pip, case.change
    assert sent.to == [pip.created_by.email] and not sent.cc and not sent.bcc
    assert sent.subject == f'Your PIP "{pip.title}" — Accepted ✓'
    label = case.expected_name or change.target_name_snapshot or "(unnamed)"
    assert f'Change 1: {case.operation} {change.entity_type} "{label}"' in sent.body
    assert "Decision: ACCEPT" in sent.body and _REVIEW_NOTE in sent.body
    assert "Overall: Accepted. Accessible Forms Review is now v3.0." in sent.body
    assert reverse("pip_detail", kwargs={"pk": pip.pk}) in sent.body


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("operation", "entity"),
    (
        ("REPLACE", "Activity"),
        ("ALTER", "Playbook"),
        ("LINK", "invented_relationship"),
        ("UNLINK", "rule_activity"),
        ("alter", "Activity"),
        ("ADD", " Phase"),
        *_EXCLUDED_MAJOR_ROWS,
    ),
)
def test_minor_fixture_with_unknown_or_major_row_rejects_before_writes(
    operation: str, entity: str
) -> None:
    """Prove the fixture rejects invalid, unsupported and major ADD inputs.

    :param operation: Unsupported operation or part of an excluded pair. Example: ADD.
    :param entity: Unsupported entity or part of an excluded pair. Example: Activity.
    :return: None. Example: ADD Activity rejected without executing SQL.
    :raises AssertionError: If invalid input writes or substitutes another case.
    """
    cedar = load_cedar_baseline()
    with (
        CaptureQueriesContext(connection) as queries,
        pytest.raises(ValueError, match="S33 minor Example"),
    ):
        create_reviewed_minor_pip(cedar, operation=operation, entity=entity)
    assert not queries.captured_queries


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(("operation", "entity"), MINOR_CASES)
def test_minor_acceptance_log_story_happy(
    caplog: LogCaptureFixture,
    operation: str,
    entity: str,
    mailoutbox: list[EmailMessage],
) -> None:
    """Prove S32-owned minor log beats for every actual supported Example.

    :param caplog: Real log capture. Example: INFO award-service records.
    :param operation: Exact operation. Example: "LINK".
    :param entity: Exact entity. Example: "supported existing relationship".
    :param mailoutbox: Local Django mail. Example: one accepted decision.
    :return: None. Example: minor/100 classification and one-created exit.
    :raises AssertionError: For missing beats, wrong attribution or unsafe logs.
    """
    cedar = load_cedar_baseline()
    case = create_reviewed_minor_pip(cedar, operation=operation, entity=entity)
    staff = cedar.users_by_username["mchen"]
    before = _recorded_rows(case)
    with capture_experts_logs(caplog, (_POLICY_LOGGER, _ADMIN_LOGGER)):
        _finalize_with_saved_choice(case, staff)

    _assert_minor_log_story(caplog, case, staff)
    _assert_applied_and_awarded(case, staff, before)
    _assert_decision_mail(case, mailoutbox)


def _assert_minor_log_story(
    caplog: LogCaptureFixture, case: MinorPipCase, staff: User
) -> None:
    """Confirm the actual INFO records identify one correlated minor decision."""
    pip = case.pip
    trace = (f"pip_id={pip.pk}", f"correlation_id=pip_finalize:{pip.pk}")
    created = ("created_count=1", "existing_count=0", "transaction=pending")
    actors = (f"actor_id={staff.pk}", f"recipient_id={pip.created_by_id}")
    assert_log_story(
        caplog,
        where=_AWARD_STORY,
        beats={
            "entry": ("| entry |", *trace),
            "exit": ("| exit |", *trace, *created),
        },
    )
    assert_log_story(
        caplog,
        where=_CLASSIFICATION_STORY,
        beats={"classification": _minor_classification_fields(case)},
    )
    assert_log_story(
        caplog,
        where=_DECISION_STORY,
        beats={"exit": ("| exit |", *trace, *actors, "transaction=pending")},
    )
    _assert_log_order_and_privacy(caplog, case, staff)


def _minor_classification_fields(case: MinorPipCase) -> tuple[str, ...]:
    """Tie the minor policy record to the same proposal and exact change."""
    scope = (
        "entity= relationship_type=skill_activity"
        if case.entity == _RELATIONSHIP
        else f"entity={case.entity} relationship_type="
    )
    return (
        "| processing |",
        f"pip_id={case.pip.pk}",
        f"change_id={case.change.pk}",
        f"operation={case.operation}",
        scope,
        "source_kind=minor",
        f"points={_MINOR_POINTS}",
    )


def _assert_log_order_and_privacy(
    caplog: LogCaptureFixture, case: MinorPipCase, staff: User
) -> None:
    """Verify the transaction beats are ordered and the award logs omit private data."""
    messages = [
        record.getMessage()
        for record in caplog.records
        if record.name in (_POLICY_LOGGER, _ADMIN_LOGGER)
    ]
    methods = (_AWARD_STORY, _CLASSIFICATION_STORY, _DECISION_STORY)
    beats = [
        message.split(" | ", maxsplit=2)[:2]
        for message in messages
        if message.startswith(methods)
    ]
    assert beats == [
        [_AWARD_STORY, "entry"],
        [_CLASSIFICATION_STORY, "processing"],
        [_AWARD_STORY, "exit"],
        [_DECISION_STORY, "exit"],
    ]
    logged = "\n".join(messages)
    private_values = (
        case.pip.created_by.email,
        staff.email,
        case.expected_content,
        _REVIEW_NOTE,
    )
    assert all(value and value not in logged for value in private_values)
    assert all(
        field not in logged for field in ("email=", "token=", "password=", "secret=")
    )
