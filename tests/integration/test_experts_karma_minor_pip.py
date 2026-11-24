from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from behave.model import ScenarioOutline
from behave.parser import parse_file
from django.core.mail import EmailMessage
from django.db import connection
from django.db.models import Model
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from pytest import LogCaptureFixture

from methodology.models import (
    Activity,
    Agent,
    Artifact,
    KarmaAward,
    Phase,
    PipChange,
    Rule,
    Skill,
    Workflow,
)
from tests.support.experts_data import CedarDataset, load_cedar_baseline
from tests.support.experts_pip_minor import (
    MINOR_CASES,
    MinorPipCase,
    create_reviewed_minor_pip,
)

_FEATURE = (
    Path(__file__).resolve().parents[2]
    / "docs/features/act-18-experts/karma-accrual.feature"
)
_OUTLINE = "KARMA-PIP-02 Award an accepted minor change"
_TARGET_ID = 6106
_VERSION_BEFORE = Decimal("2.0")
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
    _assert_reviewed_minor_identity(case, cedar)
    if entity == _RELATIONSHIP:
        _assert_minor_relationship_fixture(case)
    else:
        _assert_minor_entity_fixture(case)
    assert list(book.versions.order_by("pk").values()) == prior_versions
    assert not case.pip.playbook_versions.exists()
    assert list(KarmaAward.objects.order_by("pk").values()) == prior_ledger
    assert not mailoutbox


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
    client: Client, operation: str, entity: str
) -> None:
    """Prove real POST, concrete effect, singleton receipt, totals and local mail.

    :param client: Real Django client. Example: authenticated staff Mike.
    :param operation: Exact matrix operation. Example: "ALTER".
    :param entity: Exact matrix entity. Example: "Artifact".
    :return: None. Example: Maria 8300/7300, target 3.0, one 100-point minor.
    :raises AssertionError: If any Section D invariant fails.
    """
    raise NotImplementedError()


@pytest.mark.django_db(transaction=True)
def test_finalize_pip_with_minor_service_call_preserves_proposal_return() -> None:
    """Prove legacy direct finalization returns the actual persisted proposal.

    :return: None. Example: same accepted PIP PK with one award/version receipt.
    :raises AssertionError: If return contract or domain effects differ.
    """
    raise NotImplementedError()


@pytest.mark.django_db(transaction=True)
def test_finalize_pip_with_nonstaff_preserves_minor_target_and_ledger(
    client: Client,
) -> None:
    """Prove unchanged authorization denies a real nonstaff finalization POST.

    :param client: Real client. Example: Maria authenticated without staff.
    :return: None. Example: 403, unchanged content/version/ledger, no mail.
    :raises AssertionError: If denial mutates state or awards points.
    """
    raise NotImplementedError()


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
    caplog: LogCaptureFixture, operation: str, entity: str
) -> None:
    """Prove S32-owned minor log beats for every actual supported Example.

    :param caplog: Real log capture. Example: INFO award-service records.
    :param operation: Exact operation. Example: "LINK".
    :param entity: Exact entity. Example: "supported existing relationship".
    :return: None. Example: minor/100 classification and one-created exit.
    :raises AssertionError: For missing beats, wrong attribution or unsafe logs.
    """
    raise NotImplementedError()
