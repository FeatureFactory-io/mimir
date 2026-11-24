from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from django.contrib.auth.models import User
from django.db.models import Model, Sum

from methodology.models import AgentInteraction, ExpertProfile, KarmaAward, Workflow
from methodology.services.playbook_service import PlaybookService
from methodology.services.workflow_export_service import WorkflowExportService
from methodology.services.workflow_service import WorkflowService
from tests.support.experts_data import CedarDataset

_SOURCE_WORKFLOW = 6202
_SOURCE_ACTIVITY = 6203
_DIRECTORY = "CEDAR"
_ADDED_NAME = "Cedar Imported Activity"
_EXPECTED_TOTALS = {"mrodriguez": 8200, "mchen": 12450}


@dataclass(frozen=True)
class ImportCase:
    """Prepared real source and an existing owned draft import target."""

    workflow_id: int
    source_directory: Path
    added_activity_name: str
    expected_guidance: str


@dataclass(frozen=True)
class ExpertsImportState:
    """Complete ordered ORM snapshots; retain every stored field."""

    ledger: tuple[tuple[object, ...], ...]
    profiles: tuple[tuple[object, ...], ...]
    interactions: tuple[tuple[object, ...], ...]


def _prepare_import_case(cedar: CedarDataset, root: Path) -> ImportCase:
    """Self-export Mike's source and prepare Maria's real owned draft.

    :param cedar: Restored dataset. Example: users_by_username["mchen"].
    :param root: Isolated filesystem root. Example: tmp_path.
    :return: Ready import case. Example: target draft and actual Markdown files.
    :raises AssertionError: Setup awards points or lacks actual exported guidance.
    """
    assert isinstance(root, Path) and root.is_dir()
    before = _snapshot_experts_state()
    workflow = _create_owned_target(cedar)
    result = WorkflowExportService.export_workflow_to_markdown(
        workflow_id=_SOURCE_WORKFLOW,
        target_directory=str(root),
        folder_name=_DIRECTORY,
        user=cedar.users_by_username["mchen"],
    )
    assert result["status"] == "exported"
    source = Path(result["export_path"])
    assert source.resolve() == (root / _DIRECTORY).resolve()
    guidance = _write_import_addition(source)
    _assert_experts_unchanged(before)
    return ImportCase(workflow.pk, source, _ADDED_NAME, guidance)


def _snapshot_experts_state() -> ExpertsImportState:
    """Snapshot all ledger, profile and interaction rows in primary-key order.

    :return: Immutable complete state. Example: original historical award rows.
    :raises AssertionError: Expected Cedar schema or baseline is unavailable.
    """
    return ExpertsImportState(
        ledger=_import_model_rows(KarmaAward),
        profiles=_import_model_rows(ExpertProfile),
        interactions=_import_model_rows(AgentInteraction),
    )


def _assert_import_protocol(result: Mapping[str, object], case: ImportCase) -> None:
    """Verify a positive real import result and generated protocol contents.

    :param result: Actual response. Example: status="changes_detected".
    :param case: Prepared source/target. Example: added_activity_name="Cedar Import".
    :return: None. Example: correct draft, positive diff and protocol verified.
    :raises AssertionError: Wrong target, empty diff or absent protocol content.
    """
    assert result["status"] == "changes_detected"
    assert type(result["workflow_id"]) in (int, str)
    assert str(result["workflow_id"]) == str(case.workflow_id)
    workflow = Workflow.objects.select_related("playbook").get(pk=case.workflow_id)
    assert result["workflow_name"] == workflow.name
    assert result["playbook_status"] == workflow.playbook.status == "draft"
    assert workflow.playbook.author.username == "mrodriguez"
    assert workflow.abbreviation == case.source_directory.name == _DIRECTORY
    assert result["changes_count"] == 1
    assert result["changes_summary"] == {
        "new": 1,
        "modified": 0,
        "deleted": 0,
        "reordered": 0,
        "total": 1,
    }
    protocol = case.source_directory / "_Upload_Protocol.md"
    assert Path(str(result["protocol_file"])).resolve() == protocol.resolve()
    text = protocol.read_text(encoding="utf-8")
    assert text.startswith(f"# Upload Protocol for {workflow.name}\n")
    assert f"**Workflow ID**: {workflow.pk}\n" in text
    assert "- **New Activities**: 1\n" in text
    assert "- **Total Changes**: 1\n" in text
    assert f"- **{case.added_activity_name}** (Order: 2, Phase: None)" in text
    assert "**Rationale**: [AI to fill:" in text
    assert result["message"]


def _assert_experts_unchanged(before: ExpertsImportState) -> None:
    """Compare global stored state and actual Maria/Mike ledger totals.

    :param before: Snapshot after non-awarding setup. Example: baseline state.
    :return: None. Example: identical rows and totals 8200/12450.
    :raises AssertionError: Any award, summary metadata or interaction changed.
    """
    assert isinstance(before, ExpertsImportState)
    assert _snapshot_experts_state() == before
    totals = {
        user.username: KarmaAward.objects.filter(recipient=user).aggregate(
            total=Sum("points")
        )["total"]
        or 0
        for user in User.objects.filter(username__in=_EXPECTED_TOTALS)
    }
    assert totals == _EXPECTED_TOTALS


def _create_owned_target(cedar: CedarDataset) -> Workflow:
    """Create the actual authorized draft without releasing source content.

    :param cedar: Independent real actors. Example: Maria and Mike.
    :return: Empty owned workflow. Example: Maria's CEDAR draft.
    :raises AssertionError: Source ownership or target status differs.
    """
    source = cedar.workflows_by_pk[_SOURCE_WORKFLOW]
    assert source.playbook.author_id == cedar.users_by_username["mchen"].pk
    book = PlaybookService.create_playbook(
        name="Cedar Import Draft",
        description="Isolated import certification target.",
        category="design",
        author=cedar.users_by_username["mrodriguez"],
    )
    workflow = WorkflowService.create_workflow(
        book, "Cedar Import Workflow", abbreviation=_DIRECTORY
    )
    assert workflow.playbook.status == "draft" and not workflow.activities.exists()
    return workflow


def _write_import_addition(source: Path) -> str:
    """Copy actual exported guidance into one explicitly ID-free fixture file.

    :param source: Actual self-export directory. Example: tmp_path / "CEDAR".
    :return: Stored normalized guidance. Example: "" for Cedar's empty source.
    :raises AssertionError: Source export, guidance or unique activity differs.
    """
    activity = Workflow.objects.get(pk=_SOURCE_WORKFLOW).activities.get(
        pk=_SOURCE_ACTIVITY
    )
    exports = []
    for file in source.glob("*.md"):
        text = file.read_text(encoding="utf-8")
        if f"**Activity ID**: {activity.pk}\n" in text:
            exports.append(text)
    assert len(exports) == 1
    text = exports[0]
    assert f"**Activity ID**: {activity.pk}\n" in text
    guidance = activity.guidance or "No guidance provided."
    assert f"## Guidance\n\n{guidance}\n" in text
    text = re.sub(r"(?m)^# Activity:.*$", f"# Activity: {_ADDED_NAME}", text)
    text = re.sub(r"(?m)^\*\*Activity ID\*\*:.*$", "**Activity ID**: ", text)
    text = re.sub(r"(?m)^\*\*Order\*\*:.*$", "**Order**: 2", text)
    (source / "CEDAR-02-Cedar_Imported_Activity.md").write_text(text, encoding="utf-8")
    return activity.guidance or ""


def _import_model_rows(model: type[Model]) -> tuple[tuple[object, ...], ...]:
    """Read every stored column in stable identity order.

    :param model: Actual ORM model. Example: KarmaAward.
    :return: Complete independent values. Example: timestamps plus payload fields.
    :raises AssertionError: The supplied dependency is not a model class.
    """
    assert isinstance(model, type) and issubclass(model, Model)
    return tuple(model.objects.order_by("pk").values_list())
