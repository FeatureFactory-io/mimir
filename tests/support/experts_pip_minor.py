from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from django.db.models import Model
from methodology.models import PipChange, Playbook, ProcessImprovementProposal
from tests.support.experts_data import CedarDataset

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
    raise NotImplementedError()


def _create_minor_targets(playbook: Playbook) -> Mapping[str, Model]:
    """Create valid dedicated targets without release or accepted-change hooks.

    :param playbook: Hana's released target. Example: playbook 6106 at 2.0.
    :return: Read-only entity map. Example: {"Phase": empty_phase, "Skill": skill}.
    :raises ValueError: If the target is not the required released baseline.
    """
    raise NotImplementedError()


def _minor_change_payload(
    operation: str, entity: str, targets: Mapping[str, Model]
) -> dict[str, object]:
    """Prepare real add_change arguments, including relationship preconditions.

    :param operation: Supported operation. Example: "UNLINK".
    :param entity: Outline entity. Example: "supported existing relationship".
    :param targets: Real same-playbook objects. Example: Skill and Activity.
    :return: Valid service kwargs. Example: skill_activity with real string IDs.
    :raises ValueError: For unsupported rows or missing targets.
    """
    raise NotImplementedError()


def _mark_minor_reviewed(pip: ProcessImprovementProposal) -> None:
    """Persist assessment/timestamps as fixture state without invoking Galdr.

    :param pip: Fresh real draft with one change. Example: Maria's PIP 42.
    :return: None. Example: Reviewed PIP with ACCEPT recommendation, unset decision.
    :raises ValueError: Unless this is a fresh one-change draft.
    """
    raise NotImplementedError()


def assert_minor_change_applied(case: MinorPipCase) -> None:
    """Verify concrete content, deletion, insertion or relationship effect.

    :param case: Finalized real case. Example: accepted UNLINK skill_activity.
    :return: None. Example: the original Skill/Activity relationship is absent.
    :raises AssertionError: If the precise operation effect is missing.
    """
    raise NotImplementedError()
