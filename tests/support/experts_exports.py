from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from django.contrib.auth.models import User
from django.db.models import Model

from methodology.models import (
    Activity,
    AgentInteraction,
    ExpertProfile,
    KarmaAward,
    Playbook,
    Rule,
)
from methodology.services.experts_service import ExpertsService
from tests.support.experts_data import CedarDataset

_MIKE = "mchen"
_MIKE_POINTS = 12450
_MIKE_GUI_COPIES = 47
_PLAYBOOK_ID = 6201
_WORKFLOW_ID = 6202
_ACTIVITY_ID = 6203
_EXPORT_DATE = re.compile(
    r"(?m)^\*\*Export Date\*\*: (\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC)$"
)
_EXPORT_DATE_FORMAT = "%Y-%m-%d %H:%M UTC"
_PLAYBOOK_SECTIONS = (
    ("rules", "rule_files", ".mdc"),
    ("agents", "agent_files", ".md"),
    ("skills", "skill_files", ".md"),
    ("artifacts", "artifact_files", ".md"),
)
_CONTENT_FIELDS = {
    "agents": ("name", "description"),
    "skills": ("title", "content"),
    "artifacts": ("name", "description"),
}


@dataclass(frozen=True)
class ExportKarmaState:
    """Immutable real-ledger/projection snapshot for successful-export proofs."""

    ledger_rows: tuple[tuple[object, ...], ...]
    user_totals: tuple[tuple[int, int], ...]
    category_source_totals: tuple[tuple[object, ...], ...]
    mike_gui_copy_count: int
    profile_rows: tuple[tuple[object, ...], ...]
    interaction_rows: tuple[tuple[object, ...], ...]


def assert_owned_export_source(cedar: CedarDataset) -> User:
    """Resolve actual Cedar ownership and the public released source.

    :param cedar: Cedar adapter result. Example: load_cedar_baseline().
    :return: Authenticated existing author. Example: Mike Chen.
    :raises AssertionError: The stored ownership, release, or entity graph differs.
    """
    mike = cedar.users_by_username[_MIKE]
    activity = Activity.objects.select_related("workflow__playbook").get(
        pk=_ACTIVITY_ID
    )
    book = activity.workflow.playbook
    assert mike.is_authenticated and mike.is_active
    assert activity.pk == cedar.activities_by_pk[_ACTIVITY_ID].pk
    assert (
        activity.workflow_id == cedar.workflows_by_pk[_WORKFLOW_ID].pk == _WORKFLOW_ID
    )
    assert book.pk == cedar.playbooks_by_pk[_PLAYBOOK_ID].pk == _PLAYBOOK_ID
    assert (book.author_id, book.status, book.visibility) == (
        mike.pk,
        "released",
        "public",
    )
    return mike


def capture_export_karma_state() -> ExportKarmaState:
    """Capture every award field and all live numeric projections.

    :return: Immutable snapshot. Example: Mike=12450 and GUI copies=47.
    :raises AssertionError: Cedar baseline or required projection is absent.
    """
    service = ExpertsService()
    users = User.objects.order_by("pk").values_list("pk", flat=True)
    projections = tuple(service.project_user(user_id) for user_id in users)
    mike = next(
        projection for projection in projections if projection.username == _MIKE
    )
    assert mike.total_points == _MIKE_POINTS
    assert dict(mike.category_points) == {"development": _MIKE_POINTS}
    assert mike.successful_gui_copy_count == _MIKE_GUI_COPIES
    ledger = _model_rows(KarmaAward)
    assert ledger
    return ExportKarmaState(
        ledger_rows=ledger,
        user_totals=tuple((row.user_id, row.total_points) for row in projections),
        category_source_totals=tuple(
            (row.user_id, row.category_points, row.source_points) for row in projections
        ),
        mike_gui_copy_count=mike.successful_gui_copy_count,
        profile_rows=_model_rows(ExpertProfile),
        interaction_rows=_model_rows(AgentInteraction),
    )


def _model_rows(model: type[Model]) -> tuple[tuple[object, ...], ...]:
    """Take an ordered value snapshot across every stored model column."""
    return tuple(model.objects.order_by("pk").values_list())


def assert_complete_self_export(
    *,
    result: Mapping[str, Any],
    bundle: Mapping[str, Any],
    workspace: Path,
    started_at: datetime,
    finished_at: datetime,
    targets: tuple[Path, ...] | None = None,
    folder: str = "cedar",
    facade: bool = False,
    sync_root_rules: bool = False,
) -> None:
    """Verify complete confined files, bytes, formats and source content.

    :param result: Real successful export result. Example: status='exported'.
    :param bundle: Real authorized content bundle. Example: workflow_id=6202.
    :param workspace: Real isolated root. Example: tmp_path / 'workspace'.
    :param started_at: Invocation start. Example: UTC 2026-11-23T12:00:00.
    :param finished_at: Invocation completion. Example: UTC 2026-11-23T12:00:02.
    :param targets: Approved target bases. Example: (workspace / 'workflows',).
    :param folder: Explicitly requested export folder. Example: 'cedar'.
    :param facade: Bundle came from the actual HTTP response. Example: True.
    :param sync_root_rules: Both file ADE and both inline targets requested. Example: True.
    :return: None. Example: every expected file and inline output verified.
    :raises AssertionError: Missing/extra file, invalid timestamp, bytes or format.
    """
    assert result["status"] == "exported" and result["message"]
    assert bundle["folder_name"] == folder and Path(folder).name == folder
    workspace = workspace.resolve()
    if "workflow_id" in bundle:
        (target,) = targets or (workspace / "workflows",)
        files = _assert_workflow_result(result, bundle, target, facade)
    else:
        target_bases = targets or (workspace / ".cursor/playbooks",)
        files = _assert_playbook_result(
            result, bundle, target_bases, workspace, facade, sync_root_rules
        )
    paths = {
        path for path in workspace.rglob("*") if path.is_file() or path.is_symlink()
    }
    assert paths == files.keys()
    for path, text in files.items():
        assert path.resolve() == path and path.is_relative_to(workspace)
        _assert_file_bytes(path, text, started_at, finished_at, facade)


def _entry_files(entries: Iterable[Mapping[str, str]], suffix: str) -> dict[str, str]:
    """Collect unique relative filenames of the expected format."""
    files = {}
    for entry in entries:
        name, text = entry["filename"], entry["content"]
        assert Path(name).name == name and Path(name).suffix == suffix
        assert name not in files and text.strip()
        files[name] = text
    return files


def _assert_workflow_result(
    result: Mapping[str, Any], bundle: Mapping[str, Any], target: Path, facade: bool
) -> dict[Path, str]:
    """Check the workflow result and plan its complete workflow and rule files."""
    activity = Activity.objects.select_related("workflow").get(pk=_ACTIVITY_ID)
    assert result["workflow_id"] == bundle["workflow_id"] == activity.workflow_id
    assert result["workflow_name"] == bundle["workflow_name"] == activity.workflow.name
    root = target / bundle["folder_name"]
    workflow_files = _entry_files(bundle["workflow_files"], ".md")
    _assert_owned_workflow_text(workflow_files, activity)
    rule_files = _entry_files(bundle["rule_files"], ".mdc")
    _assert_canonical_rules(rule_files, activity.rules.all())
    rules_root = target.parent / "rules"
    assert result["export_path"] == str(root)
    assert result["rules_export_path"] == (str(rules_root) if rule_files else "")
    assert result["rule_export_paths"] == [
        str(rules_root / name) for name in rule_files
    ]
    legacy_rule_names = [f"rules/{name}" for name in rule_files]
    assert result["rule_files_created"] == (
        list(rule_files) if facade else legacy_rule_names
    )
    assert result["files_created"] == list(workflow_files) + (
        [] if facade else legacy_rule_names
    )
    return {
        **{root / name: text for name, text in workflow_files.items()},
        **{rules_root / name: text for name, text in rule_files.items()},
    }


def _assert_owned_workflow_text(files: Mapping[str, str], activity: Activity) -> None:
    """Check source identity and the actual stored guidance or its empty fallback."""
    assert len(files) == activity.workflow.activities.count() + 1
    assert files["_workflow.md"].startswith(f"# {activity.workflow.name}\n")
    assert f"**Workflow ID**: {_WORKFLOW_ID}\n" in files["_workflow.md"]
    [content] = [
        text for text in files.values() if f"**Activity ID**: {_ACTIVITY_ID}\n" in text
    ]
    assert content.startswith(f"# Activity: {activity.name}\n")
    guidance = activity.guidance or "No guidance provided."
    assert f"## Guidance\n\n{guidance}\n\n## Agent\n" in content


def _assert_canonical_rules(files: Mapping[str, str], rules: Iterable[Rule]) -> None:
    """Check stored flags and full Markdown independently against actual rule rows."""
    expected = {
        f"{rule.slug}.mdc": _cursor_rule_text(rule.content.strip(), rule.always_apply)
        for rule in rules
    }
    assert files == expected


def _cursor_rule_text(body: str, always_apply: bool) -> str:
    """Build the exact Cursor frontmatter followed by nonempty stored guidance."""
    return f"---\nalwaysApply: {str(always_apply).lower()}\n---\n\n" + (
        f"{body}\n" if body else ""
    )


def _assert_playbook_result(
    result: Mapping[str, Any],
    bundle: Mapping[str, Any],
    targets: tuple[Path, ...],
    workspace: Path,
    facade: bool,
    sync_root_rules: bool,
) -> dict[Path, str]:
    """Check the full playbook response and build the expected authorized tree."""
    book = Playbook.objects.get(pk=_PLAYBOOK_ID)
    assert result["playbook_id"] == bundle["playbook_id"] == book.pk
    assert result["playbook_name"] == bundle["playbook_name"] == book.name
    tree = _playbook_files(bundle, book)
    roots = [target / bundle["folder_name"] for target in targets]
    assert result["export_paths"] == [str(root) for root in roots]
    assert result["files_created"] == list(tree) * (1 if facade else len(roots))
    assert {key: result[key] for key in bundle["counts"]} == bundle["counts"]
    outputs = {root / name: text for root in roots for name, text in tree.items()}
    assert result["ade_rule_files"] == bundle["ade_rule_files"]
    assert result["inline_rules_markdown"] == bundle["inline_rules_markdown"]
    if sync_root_rules:
        outputs.update(_assert_requested_ade_outputs(result, book, workspace))
    else:
        assert not result["ade_rule_files"] and not result["inline_rules_markdown"]
    return outputs


def _playbook_files(bundle: Mapping[str, Any], book: Playbook) -> dict[str, str]:
    """Collect each content type and verify the live Cedar source in the bundle."""
    files = _entry_files([bundle["playbook_md"]], ".md")
    assert files["playbook.md"].startswith(
        f"# {book.name}\n\n**Playbook ID**: {book.pk}\n"
    )
    for directory, key, suffix in _PLAYBOOK_SECTIONS:
        entries = _entry_files(bundle[key], suffix)
        _assert_section_sources(book, directory, entries)
        files.update({f"{directory}/{name}": text for name, text in entries.items()})
    assert len(bundle["workflows"]) == book.workflows.count() > 0
    for workflow in bundle["workflows"]:
        own_files = _entry_files(workflow["workflow_files"], ".md")
        if workflow["workflow_id"] == _WORKFLOW_ID:
            _assert_owned_workflow_text(
                own_files, Activity.objects.get(pk=_ACTIVITY_ID)
            )
        files.update(
            {
                f"{workflow['folder_name']}/{name}": text
                for name, text in own_files.items()
            }
        )
    assert _WORKFLOW_ID in {workflow["workflow_id"] for workflow in bundle["workflows"]}
    return files


def _assert_section_sources(
    book: Playbook, directory: str, files: Mapping[str, str]
) -> None:
    """Confirm every section file represents its stored source and fixture prose."""
    rows = getattr(book, directory)
    assert len(files) == rows.count() > 0
    if directory == "rules":
        _assert_canonical_rules(files, rows.all())
        return
    for title, body in rows.values_list(*_CONTENT_FIELDS[directory]):
        assert body.strip()
        [text] = [
            content
            for content in files.values()
            if content.startswith(f"# {title}\n\n")
        ]
        assert body.strip() in text


def _assert_requested_ade_outputs(
    result: Mapping[str, Any],
    book: Playbook,
    root: Path,
) -> dict[Path, str]:
    """Check exact Cursor/Devin paths and content plus Claude/Copilot inline content."""
    rules = list(book.rules.order_by("slug"))
    assert any(not rule.always_apply for rule in rules)
    cursor = {
        f".cursor/rules/{rule.slug}.mdc": _cursor_rule_text(rule.content.strip(), True)
        for rule in rules
    }
    devin = {
        f".windsurf/rules/{rule.slug}.md": f"# {rule.title}\n\n{rule.content.strip()}\n"
        for rule in rules
    }
    actual = result["ade_rule_files"]
    assert len(actual) == len(cursor) + len(devin)
    assert {entry["ade_target"] for entry in actual} == {"cursor", "devin"}
    for target, expected in (("cursor", cursor), ("devin", devin)):
        assert {
            entry["path"]: entry["content"]
            for entry in actual
            if entry["ade_target"] == target
        } == expected
    sections = [
        f"### {rule.title} (`{rule.slug}`)\n\n{rule.content.strip()}\n"
        for rule in rules
    ]
    assert result["inline_rules_markdown"] == "## Playbook Rules\n\n" + "\n".join(
        sections
    )
    return {root / path: text for path, text in (cursor | devin).items()}


def _assert_file_bytes(
    path: Path,
    expected: str,
    start: datetime,
    finish: datetime,
    facade: bool,
) -> None:
    """Normalize only the export timestamp when the bundle was generated separately."""
    actual = path.read_bytes()
    if path.name in {"_workflow.md", "playbook.md"}:
        [stamp] = _EXPORT_DATE.findall(actual.decode("utf-8"))
        stamped = datetime.strptime(stamp, _EXPORT_DATE_FORMAT).replace(tzinfo=UTC)
        assert start.replace(second=0, microsecond=0) <= stamped <= finish
        if not facade:
            expected, count = _EXPORT_DATE.subn(f"**Export Date**: {stamp}", expected)
            assert count == 1
    assert actual == expected.encode("utf-8"), path.name


def assert_self_export_karma_unchanged(before: ExportKarmaState) -> None:
    """Compare complete persisted state after a verified successful self-export.

    :param before: Pre-invocation state. Example: Mike=12450, GUI copies=47.
    :return: None. Example: global ledger and projections remain identical.
    :raises AssertionError: Any row, recipient, total, timestamp or count changed.
    """
    assert capture_export_karma_state() == before
