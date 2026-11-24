from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Model
from django.utils import timezone

from methodology.models import (
    Activity,
    Agent,
    Artifact,
    Phase,
    PipChange,
    Playbook,
    ProcessImprovementProposal,
    Rule,
    Skill,
    Workflow,
)
from methodology.services.pip_service import PIPService
from tests.support.experts_data import CedarDataset

_TARGET_ID = 6106
_TARGET_NAME = "Accessible Forms Review"
_TARGET_VERSION = Decimal("2.0")
_CEDAR_ACTORS = ("mrodriguez", "hkim", "mchen")
_RELATIONSHIP_OPERATIONS = (PipChange.CHANGE_LINK, PipChange.CHANGE_UNLINK)
_ENTITY_FIELDS = {
    "Activity": (Activity, "name", "guidance"),
    "Skill": (Skill, "title", "content"),
    "Artifact": (Artifact, "name", "description"),
    "Workflow": (Workflow, "name", "description"),
    "Phase": (Phase, "name", "description"),
    "Agent": (Agent, "name", "description"),
    "Rule": (Rule, "title", "content"),
}
_ORIGINAL_CONTENT = "Review how the current form communicates validation errors."
_PROPOSED_CONTENT = "Verify focus and announce validation errors before resubmission."
_DROP_RATIONALE = "Remove this redundant check from the form review."
_LINK_RATIONALE = "Update the guidance relationship for this accessibility check."

MINOR_CASES: tuple[tuple[str, str], ...] = (
    ("ALTER", "Activity"),
    ("ALTER", "Skill"),
    ("ALTER", "Artifact"),
    ("ALTER", "Workflow"),
    ("ALTER", "Phase"),
    ("ALTER", "Agent"),
    ("ALTER", "Rule"),
    ("DROP", "Activity"),
    ("DROP", "Skill"),
    ("DROP", "Artifact"),
    ("DROP", "Workflow"),
    ("DROP", "Phase"),
    ("DROP", "Agent"),
    ("DROP", "Rule"),
    ("LINK", "supported existing relationship"),
    ("UNLINK", "supported existing relationship"),
    ("ADD", "Workflow"),
    ("ADD", "Phase"),
    ("ADD", "Agent"),
    ("ADD", "Rule"),
)


@dataclass(frozen=True)
class MinorPipCase:
    """Real fixture references; example: one independent DROP Phase proposal."""

    pip: ProcessImprovementProposal
    change: PipChange
    operation: str
    entity: str
    targets: Mapping[str, Model]
    original_target_id: int | None
    expected_name: str
    expected_content: str


def create_reviewed_minor_pip(
    cedar: CedarDataset, *, operation: str, entity: str
) -> MinorPipCase:
    """Build real draft/change services and establish the Reviewed fixture boundary.

    :param cedar: Isolated baseline. Example: freshly loaded CEDAR-RFP-01.
    :param operation: Explicit allowed operation. Example: "DROP".
    :param entity: Exact outline value. Example: "Phase".
    :return: Reviewed case with unset admin decision. Example: Maria's DROP Phase.
    :raises ValueError: Before writes for an unknown or excluded case.
    :raises ValidationError: For invalid baseline or actual service preconditions.
    """
    if (operation, entity) not in MINOR_CASES:
        raise ValueError("Expected an exact S33 minor Example (operation, entity).")
    with transaction.atomic():
        playbook, maria = _resolve_minor_baseline(cedar)
        targets = _create_minor_targets(playbook, operation, entity)
        payload = _minor_change_payload(operation, entity, targets)
        pip = PIPService.create_draft_for_playbook(
            actor=maria,
            playbook_id=playbook.pk,
            title=f"Accessibility form review: {operation} {entity}",
        )
        change = PIPService.add_change(actor=maria, pip=pip, **payload)
        _mark_minor_reviewed(pip)
        change.refresh_from_db()
        return MinorPipCase(
            pip=pip,
            change=change,
            operation=operation,
            entity=entity,
            targets=targets,
            original_target_id=change.target_id,
            expected_name=str(payload.get("name", "")),
            expected_content=str(payload["content"]),
        )


def _resolve_minor_baseline(cedar: CedarDataset) -> tuple[Playbook, User]:
    """Resolve persisted Cedar roles and the exact public Design v2.0 target.

    :param cedar: Restored Cedar fixture. Example: load_cedar_baseline().
    :return: The actual Hana playbook and Maria submitter. Example: (6106, mrodriguez).
    :raises ValidationError: If any expected actor role or target is missing.
    """
    if not isinstance(cedar, CedarDataset):
        raise ValidationError("S33 requires the isolated Cedar baseline.")
    book = cedar.playbooks_by_pk.get(_TARGET_ID)
    if not isinstance(book, Playbook) or book.pk != _TARGET_ID:
        raise ValidationError("S33 requires Cedar playbook 6106.")
    users = User.objects.filter(is_active=True, username__in=_CEDAR_ACTORS).in_bulk(
        field_name="username"
    )
    if any(
        users.get(name) != cedar.users_by_username.get(name) or name not in users
        for name in _CEDAR_ACTORS
    ):
        raise ValidationError("S33 requires persisted Cedar actors.")
    maria, hana, mike = (users[name] for name in _CEDAR_ACTORS)
    if maria.is_staff or maria.is_superuser or not mike.is_staff:
        raise ValidationError("S33 requires nonstaff Maria and existing staff Mike.")
    target = Playbook.objects.filter(
        pk=book.pk,
        name=_TARGET_NAME,
        author=hana,
        category="design",
        status="released",
        visibility="public",
        version=_TARGET_VERSION,
    ).first()
    if target is None:
        raise ValidationError(
            "S33 requires Hana's public released Design playbook 6106 at 2.0."
        )
    return target, maria


def _create_minor_targets(
    playbook: Playbook, operation: str, entity: str
) -> Mapping[str, Model]:
    """Create valid dedicated targets without release or accepted-change hooks.

    :param playbook: Hana's released target. Example: playbook 6106 at 2.0.
    :param operation: Validated outline operation. Example: "UNLINK".
    :param entity: Validated outline entity. Example: "Phase".
    :return: Read-only map of required entities. Example: {"Phase": empty_phase}.
    """
    if operation == PipChange.CHANGE_ADD:
        return MappingProxyType({})
    if operation in _RELATIONSHIP_OPERATIONS:
        skill = _create_minor_entity_target(playbook, "Skill")
        activity = _create_minor_activity(playbook)
        if operation == PipChange.CHANGE_UNLINK:
            activity.skills.add(skill.pk)
        return MappingProxyType({"Skill": skill, "Activity": activity})
    return MappingProxyType({entity: _create_minor_entity_target(playbook, entity)})


def _create_minor_entity_target(playbook: Playbook, entity: str) -> Model:
    """Create the dedicated persistent entity a single ALTER or DROP may target.

    :param playbook: Verified released target. Example: Cedar playbook 6106.
    :param entity: Validated existing entity type. Example: "Artifact".
    :return: Persisted entity with its required parents. Example: an Artifact.
    :raises ValidationError: If artifact fixture content fails model validation.
    """
    if entity == "Activity":
        return _create_minor_activity(playbook)
    model, name_field, content_field = _ENTITY_FIELDS[entity]
    fields: dict[str, object] = {
        "playbook": playbook,
        name_field: f"Cedar Minor Existing {entity}",
        content_field: _ORIGINAL_CONTENT,
    }
    if entity == "Artifact":
        fields.update(produced_by=_create_minor_activity(playbook), is_required=True)
    elif entity == "Rule":
        fields["slug"] = "cedar-minor-existing-rule"
    elif entity == "Phase":
        last_order = playbook.phases.aggregate(last=Max("order"))["last"]
        fields["order"] = (last_order or 0) + 1
    return model.objects.create(**fields)


def _create_minor_activity(playbook: Playbook) -> Activity:
    """Create an activity and workflow independent of Cedar historical evidence.

    :param playbook: Verified released target. Example: Cedar playbook 6106.
    :return: Real activity in its own workflow with no phase or artifacts.
    """
    workflow = Workflow.objects.create(
        playbook=playbook,
        name="Cedar Minor Supporting Workflow",
    )
    return Activity.objects.create(
        workflow=workflow,
        name="Cedar Minor Existing Activity",
        guidance=_ORIGINAL_CONTENT,
    )


def _minor_change_payload(
    operation: str, entity: str, targets: Mapping[str, Model]
) -> dict[str, object]:
    """Prepare real add_change arguments, including relationship preconditions.

    :param operation: Supported operation. Example: "UNLINK".
    :param entity: Outline entity. Example: "supported existing relationship".
    :param targets: Real same-playbook objects. Example: Skill and Activity.
    :return: Valid service kwargs. Example: skill_activity with real string IDs.
    :raises ValueError: If an ALTER or DROP has no persisted target.
    """
    payload: dict[str, object] = {"change_type": operation}
    if operation in _RELATIONSHIP_OPERATIONS:
        return payload | {
            "relationship_type": PipChange.REL_SKILL_ACTIVITY,
            "source_entity_ref": str(targets["Skill"].pk),
            "target_entity_ref": str(targets["Activity"].pk),
            "content": _LINK_RATIONALE,
        }
    payload["entity_type"] = entity
    if operation != PipChange.CHANGE_ADD:
        target = targets.get(entity)
        if target is None or target.pk is None:
            raise ValueError("S33 ALTER and DROP require a persisted target.")
        payload["target_id"] = target.pk
        if operation == PipChange.CHANGE_ALTER and isinstance(target, Artifact):
            payload.update(
                artifact_type=target.type, artifact_is_required=target.is_required
            )
    if operation == PipChange.CHANGE_DROP:
        return payload | {"content": _DROP_RATIONALE}
    return payload | {
        "name": f"Cedar Minor {operation.capitalize()} {entity}",
        "content": _PROPOSED_CONTENT,
    }


def _mark_minor_reviewed(pip: ProcessImprovementProposal) -> None:
    """Persist assessment/timestamps as fixture state without invoking Galdr.

    :param pip: Fresh real draft with one change. Example: Maria's PIP 42.
    :return: None. Example: Reviewed PIP with ACCEPT recommendation, unset decision.
    :raises ValueError: Unless this is a fresh one-change draft.
    """
    changes = list(pip.changes.all())
    if (
        pip.status != pip.STATUS_DRAFT
        or pip.decided_at is not None
        or len(changes) != 1
    ):
        raise ValueError("S33 review setup requires one undecided draft change.")
    (change,) = changes
    if change.admin_decision != PipChange.ADMIN_UNSET:
        raise ValueError("S33 review setup requires an unset admin decision.")
    # Establish Reviewed locally. The submission and Galdr lifecycles are certified separately.
    pip.status = pip.STATUS_REVIEWED
    pip.submitted_at = pip.reviewed_at = timezone.now()
    pip.save(update_fields=["status", "submitted_at", "reviewed_at", "updated_at"])
    change.galdr_recommendation = PipChange.GALDR_ACCEPT
    change.save(update_fields=["galdr_recommendation", "updated_at"])


def assert_minor_change_applied(case: MinorPipCase) -> None:
    """Verify concrete content, deletion, insertion or relationship effect.

    :param case: Finalized real case. Example: accepted UNLINK skill_activity.
    :return: None. Example: the original Skill/Activity relationship is absent.
    :raises AssertionError: If the precise operation effect is missing.
    :raises ObjectDoesNotExist: If either relationship endpoint is missing.
    """
    assert (case.operation, case.entity) in MINOR_CASES
    if case.operation in _RELATIONSHIP_OPERATIONS:
        _assert_skill_activity_effect(case)
        return
    model, name_field, content_field = _ENTITY_FIELDS[case.entity]
    if case.operation == PipChange.CHANGE_DROP:
        assert case.original_target_id is not None
        assert not model.objects.filter(pk=case.original_target_id).exists()
        return
    playbook_path = "workflow__playbook_id" if model is Activity else "playbook_id"
    owned = model.objects.filter(**{playbook_path: case.pip.playbook_id})
    if case.operation == PipChange.CHANGE_ADD:
        applied = owned.filter(**{name_field: case.expected_name})
    else:
        assert case.original_target_id is not None
        applied = owned.filter(pk=case.original_target_id)
    assert list(applied.values_list(name_field, content_field)) == [
        (case.expected_name, case.expected_content)
    ]


def _assert_skill_activity_effect(case: MinorPipCase) -> None:
    """Check the exact persisted pair and that both endpoints still belong to the target."""
    playbook_id = case.pip.playbook_id
    skill_id, activity_id = case.targets["Skill"].pk, case.targets["Activity"].pk
    skill = Skill.objects.get(pk=skill_id, playbook_id=playbook_id)
    activity = Activity.objects.get(pk=activity_id, workflow__playbook_id=playbook_id)
    expected_link_count = 1 if case.operation == PipChange.CHANGE_LINK else 0
    assert activity.skills.filter(pk=skill.pk).count() == expected_link_count
