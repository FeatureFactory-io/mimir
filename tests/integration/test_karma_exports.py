from __future__ import annotations

import json
import logging
import re
import socket
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from types import FrameType
from typing import Literal
from uuid import UUID

import httpx
import pytest
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.db.models import Sum
from fastmcp.exceptions import ToolError
from pytest import LogCaptureFixture
from pytest_django.live_server_helper import LiveServer
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from mcp_integration.facade.client import get_client
from mcp_integration.facade.export_paths import confined_export_path
from methodology.models import Activity, KarmaAward, Playbook, Rule
from methodology.services.playbook_export_service import PlaybookExportService
from methodology.services.workflow_export_service import WorkflowExportService
from tests.support.experts_data import CedarDataset, load_cedar_baseline
from tests.support.experts_exports import (
    assert_complete_self_export,
    assert_owned_export_source,
    assert_self_export_karma_unchanged,
    capture_export_karma_state,
)
from tests.support.experts_logs import capture_experts_logs
from tests.support.karma_mcp import (
    MCPCase,
    MCPClientFactory,
    MCPDataset,
    StdioMCPClient,
    decode_tool_payload,
)
from tests.support.karma_mcp import (
    mcp_dataset as _mcp_dataset,  # noqa: F401 — pytest fixture
)
from tests.support.log_story import assert_log_story

pytestmark = pytest.mark.django_db(transaction=True)

_CEDAR_PLAYBOOK_ID = 6201
_CEDAR_WORKFLOW_ID = 6202
_CEDAR_ACTIVITY_ID = 6203
_EXPORT_FOLDER = "cedar"
_ACTOR = "mrodriguez"
_AUTHOR = "mchen"
_RECEIPT_PATH = "/api/consumption-receipts/"
_FACADE_LOGGERS = (
    "mcp_integration.facade.tools_http",
    "methodology.api.consumption_views",
)
_BUNDLE_ROUTES = {
    "workflow": f"/api/workflows/{_CEDAR_WORKFLOW_ID}/export/",
    "playbook": f"/api/playbooks/{_CEDAR_PLAYBOOK_ID}/export-local/",
}
_ENTITY_IDS = {"workflow": _CEDAR_WORKFLOW_ID, "playbook": _CEDAR_PLAYBOOK_ID}
_EXPORT_PARAMETERS = {
    "workflow": {"workflow_id", "target_directory", "folder_name"},
    "playbook": {
        "playbook_id",
        "target_directory",
        "folder_name",
        "additional_targets",
        "sync_root_rules",
        "ade_targets",
        "force_apply",
        "ade_target",
    },
}
_EXPORT_LOG = {
    "workflow": "WorkflowExportService.export_workflow_to_markdown",
    "playbook": "PlaybookExportService.export_playbook_to_local",
}
_SELF_CONSUMPTION_LOG = "KarmaService.award_successful_consumption"
_SELF_EXPORT_LOGGERS = (
    *_FACADE_LOGGERS,
    "methodology.services.workflow_export_service",
    "methodology.services.karma_service",
)


@pytest.fixture(name="export_facade")
def _configure_real_export_facade(
    live_server: LiveServer, cedar_dataset: CedarDataset
) -> MCPClientFactory:
    """Reuse the real registered facade lifecycle without additional fixture content.

    :param live_server: Isolated pytest Django server. Example: live_server.
    :param cedar_dataset: Cedar actors and content. Example: workflow 6202.
    :return: Shared real client factory. Example: open Maria's facade session.
    :raises RuntimeError: If token/server configuration fails.
    """
    return MCPClientFactory(MCPDataset(cedar_dataset, {}, {}), live_server.url, [])


@async_to_sync
async def _facade_call(
    factory: MCPClientFactory,
    entity: str,
    target: Path,
    *,
    folder: str = _EXPORT_FOLDER,
    options: dict[str, object] | None = None,
    observe: Callable[[httpx.Request], None] | None = None,
    discover: bool = False,
) -> dict:
    """Run a real registered tool and optionally observe the outgoing requests."""
    tool_name = f"export_{entity}_to_local"
    arguments = {
        f"{entity}_id": _ENTITY_IDS[entity],
        "target_directory": str(target),
        "folder_name": folder,
        **(options or {}),
    }
    async with factory.open(actor_username=_ACTOR, entrypoint="facade") as session:
        if observe:
            get_client().event_hooks["request"].append(observe)
        if discover:
            schema = next(
                tool.inputSchema
                for tool in await session.client.list_tools()
                if tool.name == tool_name
            )
            assert set(schema["properties"]) == _EXPORT_PARAMETERS[entity]
            assert schema["required"] == [f"{entity}_id"]
        result = decode_tool_payload(
            await session.client.call_tool(tool_name, arguments)
        )
    assert isinstance(result, dict)
    return result


def _cedar_actors(cedar: CedarDataset) -> tuple[User, User]:
    """Return the existing eligible consumer and author from one baseline."""
    return cedar.users_by_username[_ACTOR], cedar.users_by_username[_AUTHOR]


def _current_award_ids() -> set[int]:
    """Snapshot the ledger identities before an invocation."""
    return set(KarmaAward.objects.values_list("pk", flat=True))


@pytest.mark.parametrize("entity", ("workflow", "playbook"))
def test_karma_export_facade_t1_with_multiple_files_awards_one_pair(
    entity: str, export_facade: MCPClientFactory, tmp_path: Path
) -> None:
    """Prove both registered exports over real HTTP, files and paired ledger.

    :param entity: The exported content kind. Example: "workflow".
    :param export_facade: Isolated real server and fixture. Example: Maria's facade.
    :param tmp_path: Authorized temporary workspace. Example: Path("/tmp/t").
    :return: None after D's T1 assertions. Example: None.
    :raises AssertionError: If registration, files, totals or pair count differ.
    """
    cedar = export_facade.dataset.cedar
    actor, author = _cedar_actors(cedar)
    before = _current_award_ids()
    result = _facade_call(export_facade, entity, tmp_path, discover=True)
    root = tmp_path / _EXPORT_FOLDER
    outputs = tuple(root.rglob("*.md"))
    assert result["status"] == "exported"
    assert result[f"{entity}_id"] == _ENTITY_IDS[entity]
    assert len(outputs) == len(result["files_created"]) > 1
    assert all(path.resolve().is_relative_to(root.resolve()) for path in outputs)
    metadata = next(path for path in outputs if path.name == "_workflow.md")
    workflow = cedar.workflows_by_pk[_CEDAR_WORKFLOW_ID]
    assert f"# {workflow.name}" in metadata.read_text(encoding="utf-8")
    assert any(
        activity.name in path.read_text(encoding="utf-8")
        for activity in cedar.activities_by_pk.values()
        for path in outputs
        if path != metadata
    )
    assert export_facade.request_paths == _expected_export_requests(entity)
    _assert_cedar_export_pair(entity, actor, author, before)


def _legacy_export(
    entity: str, target: Path, actor: User | None, folder: str = _EXPORT_FOLDER
) -> dict:
    """Run an existing shared service against its real Cedar entity."""
    if entity == "workflow":
        return WorkflowExportService.export_workflow_to_markdown(
            _CEDAR_WORKFLOW_ID, str(target), folder_name=folder, user=actor
        )
    return PlaybookExportService.export_playbook_to_local(
        _CEDAR_PLAYBOOK_ID, str(target), folder_name=folder, user=actor
    )


def _assert_cedar_export_pair(
    entity: str, actor: User, author: User, previous_award_ids: set[int]
) -> UUID:
    """Assert the exact ORM ledger delta and return its operation UUID."""
    awards = list(KarmaAward.objects.exclude(pk__in=previous_award_ids))
    assert len(awards) == 2
    assert {(row.recipient_id, row.source_kind, row.points) for row in awards} == {
        (actor.pk, KarmaAward.SourceKind.LEARNING, 5),
        (author.pk, KarmaAward.SourceKind.CONSUMPTION, 5),
    }
    assert awards[0].event_identity == awards[1].event_identity
    assert awards[0].occurred_at == awards[1].occurred_at
    for row in awards:
        assert row.event_channel == "export"
        assert row.category == "development"
        assert row.playbook_id_snapshot == _CEDAR_PLAYBOOK_ID
        assert row.entity_type_snapshot == entity
        assert row.entity_id_snapshot == (
            _CEDAR_WORKFLOW_ID if entity == "workflow" else _CEDAR_PLAYBOOK_ID
        )
        assert row.change_id_snapshot is None
    assert actor.karma_awards.aggregate(total=Sum("points"))["total"] == 8205
    assert author.karma_awards.aggregate(total=Sum("points"))["total"] == 12455
    return UUID(awards[0].event_identity.rsplit(":", 1)[-1])


@pytest.mark.parametrize("entity", ("workflow", "playbook"))
def test_karma_export_service_t2_with_multiple_files_awards_one_pair(
    entity: str, tmp_path: Path, caplog: LogCaptureFixture
) -> None:
    """Prove each real export writes Cedar files and one paired ledger event."""
    cedar = load_cedar_baseline()
    actor, author = (cedar.users_by_username[name] for name in ("mrodriguez", "mchen"))
    award_ids = set(KarmaAward.objects.values_list("pk", flat=True))
    caplog.set_level(logging.INFO)
    result = _legacy_export(entity, tmp_path, actor)
    root = tmp_path / _EXPORT_FOLDER
    outputs = tuple(root.rglob("*.md"))
    assert result["status"] == "exported"
    assert len(outputs) > 1
    assert all(output.resolve().is_relative_to(root.resolve()) for output in outputs)
    workflow = cedar.workflows_by_pk[_CEDAR_WORKFLOW_ID]
    metadata = next(output for output in outputs if output.name == "_workflow.md")
    assert f"# {workflow.name}" in metadata.read_text(encoding="utf-8")
    assert any(
        row.name in output.read_text(encoding="utf-8")
        for row in cedar.activities_by_pk.values()
        for output in outputs
        if output != metadata
    )
    operation = _assert_cedar_export_pair(entity, actor, author, award_ids)
    _assert_service_export_story(caplog, entity, operation, actor.pk, len(outputs))
    assert str(tmp_path) not in _export_log_text(caplog, entity)


def _export_log_text(caplog: LogCaptureFixture, entity: str) -> str:
    """Read only records emitted by this service entrypoint."""
    return "\n".join(
        record.message
        for record in caplog.records
        if _EXPORT_LOG[entity] in record.message
    )


def _assert_service_export_story(
    caplog: LogCaptureFixture, entity: str, operation: UUID, actor_id: int, count: int
) -> None:
    """Require ordered, safe and operation-correlated service log beats."""
    trace = f"operation_uuid={operation}"
    beats = {
        "entry": ("| entry |", trace, f"actor_id={actor_id}"),
        "validation": ("| validation |", trace, f"destination_count={count}"),
        "processing": (
            "| processing |",
            trace,
            f"file_count={count}",
            "files_written=true",
        ),
        "exit": ("| exit |", trace, "channel=export", "outcome=awarded"),
    }
    assert_log_story(caplog, where=_EXPORT_LOG[entity], beats=beats)
    logged = _export_log_text(caplog, entity)
    indices = [logged.index(f"| {beat} |") for beat in beats]
    assert indices == sorted(indices)


@pytest.mark.parametrize("entity", ("workflow", "playbook"))
@pytest.mark.parametrize("escape", ("traversal", "absolute", "symlink"))
def test_karma_export_service_t2_log_story_reject_with_escape_makes_no_writes(
    entity: str, escape: str, tmp_path: Path, caplog: LogCaptureFixture
) -> None:
    """Reject invalid children before creating files or crediting the export."""
    cedar = load_cedar_baseline()
    target, outside = tmp_path / "inside", tmp_path / "outside"
    target.mkdir()
    outside.mkdir()
    sentinel = outside / "existing.md"
    sentinel.write_text("unchanged", encoding="utf-8")
    folder = {"traversal": "../outside", "absolute": str(outside), "symlink": "alias"}[
        escape
    ]
    if escape == "symlink":
        (target / folder).symlink_to(outside, target_is_directory=True)
    before = KarmaAward.objects.count()
    caplog.set_level(logging.INFO)
    with pytest.raises(ValueError):
        _legacy_export(entity, target, cedar.users_by_username["mrodriguez"], folder)
    assert tuple(outside.iterdir()) == (sentinel,)
    assert sentinel.read_text(encoding="utf-8") == "unchanged"
    assert len(tuple(target.iterdir())) == (1 if escape == "symlink" else 0)
    assert KarmaAward.objects.count() == before
    _assert_service_export_reject_story(caplog, entity, "invalid_destination", 0)


@pytest.mark.parametrize("entity", ("workflow", "playbook"))
def test_karma_export_service_t2_log_story_reject_with_partial_io_creates_no_awards(
    entity: str, tmp_path: Path, caplog: LogCaptureFixture
) -> None:
    """Use an actual directory in place of a later file to fail an export."""
    cedar = load_cedar_baseline()
    actor = cedar.users_by_username["mrodriguez"]
    reference = _legacy_export(entity, tmp_path / "reference", None)
    before = KarmaAward.objects.count()
    assert not KarmaAward.objects.filter(event_channel="export").exists()
    target = tmp_path / "attempt"
    root = target / _EXPORT_FOLDER
    first, blocked, *_ = reference["files_created"]
    (root / blocked).mkdir(parents=True)
    caplog.set_level(logging.INFO)
    caplog.clear()
    with pytest.raises(IsADirectoryError):
        _legacy_export(entity, target, actor)
    assert (root / first).is_file()
    assert (root / blocked).is_dir()
    assert KarmaAward.objects.count() == before
    _assert_service_export_reject_story(caplog, entity, "filesystem_failure", 1)


def _assert_service_export_reject_story(
    caplog: LogCaptureFixture, entity: str, reason: str, completed: int
) -> None:
    """Require a safe error record with no completion or award acknowledgement."""
    log = _export_log_text(caplog, entity)
    operation = log.split("operation_uuid=", 1)[1].split()[0]
    assert UUID(operation).version == 4
    assert_log_story(
        caplog,
        where=_EXPORT_LOG[entity],
        beats={
            "error": (
                "| error |",
                f"operation_uuid={operation}",
                f"reason={reason}",
                f"completed_file_count={completed}",
                "receipt_sent=false",
            )
        },
    )
    assert "files_written=true" not in log
    assert "outcome=awarded" not in log


@pytest.mark.parametrize("entity", ("workflow", "playbook"))
def test_karma_export_service_t2_with_private_content_denied_before_writes(
    entity: str, tmp_path: Path
) -> None:
    """Prove normal read permissions are checked before files and awards."""
    cedar = load_cedar_baseline()
    Playbook.objects.filter(pk=_CEDAR_PLAYBOOK_ID).update(visibility="private")
    before = KarmaAward.objects.count()
    with pytest.raises(PermissionError):
        _legacy_export(entity, tmp_path, cedar.users_by_username["mrodriguez"])
    assert not tuple(tmp_path.iterdir())
    assert KarmaAward.objects.count() == before


@pytest.mark.parametrize(
    "relative", ("", ".", " ", "bad\0file", "C:\\outside", "a/../b")
)
def test_karma_export_service_t2_with_invalid_relative_child_rejects(
    relative: str, tmp_path: Path
) -> None:
    """Reject empty, malformed and traversing children without filesystem writes."""
    with pytest.raises(ValueError):
        confined_export_path(tmp_path, relative)
    assert not tuple(tmp_path.iterdir())


@pytest.mark.parametrize("entity", ("workflow", "playbook"))
def test_karma_export_service_t2_with_file_alias_outside_export_tree_rejects(
    entity: str, tmp_path: Path
) -> None:
    """Protect unrelated siblings inside the caller's base directory."""
    cedar = load_cedar_baseline()
    root = tmp_path / _EXPORT_FOLDER
    root.mkdir()
    sentinel = tmp_path / "unrelated.md"
    sentinel.write_text("unchanged", encoding="utf-8")
    name = "_workflow.md" if entity == "workflow" else "playbook.md"
    alias = root / name
    alias.symlink_to(sentinel)
    before = KarmaAward.objects.count()
    with pytest.raises(ValueError):
        _legacy_export(entity, tmp_path, cedar.users_by_username["mrodriguez"])
    assert tuple(root.iterdir()) == (alias,)
    assert sentinel.read_text(encoding="utf-8") == "unchanged"
    assert KarmaAward.objects.count() == before


@pytest.fixture
def cedar_export_rule(cedar_dataset: CedarDataset) -> tuple[User, User, Rule]:
    """Restore the Cedar actors and attach an actual workflow rule to export."""
    cedar = cedar_dataset
    rule = Rule.objects.create(
        playbook_id=_CEDAR_PLAYBOOK_ID,
        slug="export-check",
        title="Export check",
        always_apply=False,
        content="Review the exported files.",
    )
    next(iter(cedar.activities_by_pk.values())).rules.add(rule)
    return cedar.users_by_username["mrodriguez"], cedar.users_by_username["mchen"], rule


def _legacy_playbook_with_copies(
    canonical: Path, mirror: Path, actor: User, *, ade_targets: list[str] | None = None
) -> dict:
    """Run a real playbook export with canonical, mirror and ADE destinations."""
    return PlaybookExportService.export_playbook_to_local(
        _CEDAR_PLAYBOOK_ID,
        str(canonical),
        folder_name=_EXPORT_FOLDER,
        additional_targets=[str(mirror)],
        sync_root_rules=True,
        ade_targets=ade_targets,
        ade_target="cursor",
        force_apply=True,
        user=actor,
    )


def test_karma_export_service_t2_with_mirror_and_ade_copies_credits_one_pair(
    cedar_export_rule: tuple[User, User, Rule], tmp_path: Path
) -> None:
    """Complete the canonical, mirror and ADE writes with one award pair."""
    actor, author, rule = cedar_export_rule
    before = set(KarmaAward.objects.values_list("pk", flat=True))
    canonical, mirror = tmp_path / ".cursor/playbooks", tmp_path / "mirror"
    exported = f"rules/{rule.slug}.mdc"
    existing_outputs = (
        canonical / _EXPORT_FOLDER / exported,
        mirror / _EXPORT_FOLDER / exported,
        tmp_path / ".cursor" / exported,
        tmp_path / ".windsurf/rules" / f"{rule.slug}.md",
    )
    for output in existing_outputs:
        output.parent.mkdir(parents=True)
        output.write_text("Previous export.", encoding="utf-8")
        output.with_name("unrelated.md").write_text("Keep me.", encoding="utf-8")
    result = _legacy_playbook_with_copies(
        canonical, mirror, actor, ade_targets=["devin"]
    )
    assert result["export_paths"] == [
        str(base / _EXPORT_FOLDER) for base in (canonical, mirror)
    ]
    definition = (canonical / _EXPORT_FOLDER / exported).read_text(encoding="utf-8")
    assert "alwaysApply: false" in definition
    assert (mirror / _EXPORT_FOLDER / exported).read_text(
        encoding="utf-8"
    ) == definition
    assert result["files_created"].count(exported) == 2
    for entry in result["ade_rule_files"]:
        assert (tmp_path / entry["path"]).read_text(encoding="utf-8") == entry[
            "content"
        ]
    assert {entry["ade_target"] for entry in result["ade_rule_files"]} == {
        "cursor",
        "devin",
    }
    for output in existing_outputs:
        assert output.read_text(encoding="utf-8") != "Previous export."
        assert (
            output.with_name("unrelated.md").read_text(encoding="utf-8") == "Keep me."
        )
    _assert_cedar_export_pair("playbook", actor, author, before)


@pytest.mark.parametrize("destination", ("sibling_rules", "mirror", "ade"))
def test_karma_export_service_t2_with_secondary_root_escape_prevents_all_writes(
    destination: str, cedar_export_rule: tuple[User, User, Rule], tmp_path: Path
) -> None:
    """Preflight secondary roots before starting canonical output."""
    actor, _, rule = cedar_export_rule
    project, outside = tmp_path / "project", tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / f"{rule.slug}.mdc"
    sentinel.write_text("unchanged", encoding="utf-8")
    target, mirror = project / ".cursor/playbooks", project / "mirror"
    alias = {
        "sibling_rules": target.parent / "rules",
        "mirror": mirror / _EXPORT_FOLDER,
        "ade": project / ".cursor/rules",
    }[destination]
    alias.parent.mkdir(parents=True)
    alias.symlink_to(outside, target_is_directory=True)
    before = KarmaAward.objects.count()
    with pytest.raises(ValueError):
        if destination == "sibling_rules":
            _legacy_export("workflow", target, actor)
        else:
            _legacy_playbook_with_copies(target, mirror, actor)
    assert not target.exists()
    assert tuple(outside.iterdir()) == (sentinel,)
    assert sentinel.read_text(encoding="utf-8") == "unchanged"
    assert KarmaAward.objects.count() == before


@pytest.mark.parametrize(
    ("destination", "alias_directory"),
    (
        ("cursor", False),
        ("devin", False),
        ("cursor", True),
        ("devin", True),
        ("mirror", False),
    ),
)
def test_legacy_playbook_with_workspace_sibling_alias_rejects_before_all_writes(
    destination: str,
    alias_directory: bool,
    cedar_export_rule: tuple[User, User, Rule],
    tmp_path: Path,
) -> None:
    """A workspace-local alias must still stay inside its approved output tree.

    :param destination: Requested mirror or file-based ADE. Example: "devin".
    :param alias_directory: Alias the IDE rules directory instead of its leaf.
    :param cedar_export_rule: Actual Cedar rule and export actor.
    :param tmp_path: Real isolated work area.
    """
    actor, _, rule = cedar_export_rule
    canonical, mirror = tmp_path / ".cursor/playbooks", tmp_path / "mirror"
    output = {
        "cursor": tmp_path / ".cursor/rules" / f"{rule.slug}.mdc",
        "devin": tmp_path / ".windsurf/rules" / f"{rule.slug}.md",
        "mirror": mirror / _EXPORT_FOLDER / "playbook.md",
    }[destination]
    sibling = output.parent.parent / "unrelated"
    sibling.mkdir(parents=True)
    sentinel = sibling / output.name
    sentinel.write_text("Keep me.", encoding="utf-8")
    alias = output.parent if alias_directory else output
    alias.parent.mkdir(parents=True, exist_ok=True)
    alias.symlink_to(
        sibling if alias_directory else sentinel, target_is_directory=alias_directory
    )
    before = set(tmp_path.rglob("*")), _current_award_ids()
    with pytest.raises(ValueError):
        _legacy_playbook_with_copies(canonical, mirror, actor, ade_targets=["devin"])
    assert alias.is_symlink()
    assert (set(tmp_path.rglob("*")), _current_award_ids()) == before
    assert sentinel.read_text(encoding="utf-8") == "Keep me."


@contextmanager
def _observe_parent_creation(
    parent: Path, on_created: Callable[[], None]
) -> Iterator[None]:
    """Run a real filesystem mutation when the selected real mkdir returns.

    :param parent: Absolute parent created by the writer. Example: /tmp/cedar.
    :param on_created: Callback to exercise the next path recheck.
    :return: Context observing the calling thread without replacing I/O methods.
    """
    previous_profile = sys.getprofile()

    def observe(frame: FrameType, event: str, _result: object) -> None:
        if (
            event == "return"
            and frame.f_code is Path.mkdir.__code__
            and frame.f_locals["self"] == parent
            and parent.is_dir()
        ):
            sys.setprofile(previous_profile)
            on_created()

    sys.setprofile(observe)
    try:
        yield
    finally:
        sys.setprofile(previous_profile)


@pytest.mark.parametrize(
    ("entity", "placement", "alias_directory"),
    (
        ("workflow", "canonical", False),
        ("workflow", "rules", True),
        ("playbook", "canonical", False),
        ("playbook", "mirror", False),
        ("playbook", "rules", True),
    ),
)
def test_legacy_export_with_alias_inserted_after_mkdir_rejects_before_write(
    entity: str,
    placement: str,
    alias_directory: bool,
    cedar_export_rule: tuple[User, User, Rule],
    tmp_path: Path,
) -> None:
    """Reject a changed destination even when the new leaf resolves in-tree.

    :param entity: Existing shared export service. Example: "workflow".
    :param placement: File whose real parent creation triggers a swap.
    :param alias_directory: Replace the parent, or alias an in-tree leaf.
    :param cedar_export_rule: Actual Cedar rule and export actor.
    :param tmp_path: Real isolated work area.
    """
    actor, _, rule = cedar_export_rule
    project = tmp_path.resolve()
    canonical, mirror = project / ".cursor/playbooks", project / "mirror"
    name = "_workflow.md" if entity == "workflow" else "playbook.md"
    output = {
        "canonical": canonical / _EXPORT_FOLDER / name,
        "mirror": mirror / _EXPORT_FOLDER / name,
        "rules": project / ".cursor/rules" / f"{rule.slug}.mdc",
    }[placement]
    sentinel = (
        project / "unrelated" / output.name
        if alias_directory
        else output.parent / "unrelated.md"
    )
    alias = output.parent if alias_directory else output

    def change_destination() -> None:
        if alias_directory:
            output.parent.rmdir()
            sentinel.parent.mkdir()
        sentinel.write_text("Keep me.", encoding="utf-8")
        alias.symlink_to(
            sentinel.parent if alias_directory else sentinel,
            target_is_directory=alias_directory,
        )

    before = _current_award_ids()
    with (
        _observe_parent_creation(output.parent, change_destination),
        pytest.raises(ValueError),
    ):
        if entity == "workflow":
            _legacy_export(entity, canonical, actor)
        else:
            _legacy_playbook_with_copies(canonical, mirror, actor)
    assert alias.is_symlink()
    assert sentinel.read_text(encoding="utf-8") == "Keep me."
    assert _current_award_ids() == before


def _expected_export_requests(entity: str, receipts: int = 1) -> list[tuple[str, str]]:
    """Expect precisely one bundle request and the stated receipt attempts."""
    return [("POST", _BUNDLE_ROUTES[entity])] + [("POST", _RECEIPT_PATH)] * receipts


def _playbook_copy_options(mirror: Path) -> dict[str, object]:
    """Request an explicit mirror and both active rule directories."""
    return {
        "additional_targets": [str(mirror)],
        "sync_root_rules": True,
        "ade_targets": ["devin"],
        "ade_target": "Cursor",
        "force_apply": True,
    }


def test_karma_export_with_mirrors_and_ade_files_awards_one_pair(
    export_facade: MCPClientFactory,
    tmp_path: Path,
    cedar_export_rule: tuple[User, User, Rule],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Observe every requested copy on disk at the first actual receipt POST.

    :param export_facade: Real token HTTP factory. Example: Maria's registered facade.
    :param tmp_path: Canonical/mirror/ADE workspace. Example: isolated temporary repo.
    :param cedar_export_rule: Real linked rule and its actors. Example: export-check.
    :param monkeypatch: Isolate workspace configuration. Example: MIMIR_DEV_ROOT.
    :return: None after actual-copy and pair assertions. Example: None.
    :raises AssertionError: If copies differ or awards multiply.
    """
    actor, author, rule = cedar_export_rule
    before = _current_award_ids()
    canonical, mirror = tmp_path / ".cursor/playbooks", tmp_path / "mirror"
    monkeypatch.setenv("MIMIR_DEV_ROOT", str(tmp_path))
    observed: set[Path] = set()

    def observe(request: httpx.Request) -> None:
        if request.url.path == _RECEIPT_PATH:
            observed.update(path for path in tmp_path.rglob("*") if path.is_file())

    result = _facade_call(
        export_facade,
        "playbook",
        canonical.relative_to(tmp_path),
        options=_playbook_copy_options(mirror.relative_to(tmp_path)),
        observe=observe,
    )
    tree = canonical / _EXPORT_FOLDER
    assert result["export_paths"] == [str(tree), str(mirror / _EXPORT_FOLDER)]
    for relative in result["files_created"]:
        assert (tree / relative).read_bytes() == (
            mirror / _EXPORT_FOLDER / relative
        ).read_bytes()
        assert {tree / relative, mirror / _EXPORT_FOLDER / relative} <= observed
    rule_file = tree / "rules" / f"{rule.slug}.mdc"
    assert "alwaysApply: false" in rule_file.read_text(encoding="utf-8")
    assert {entry["ade_target"] for entry in result["ade_rule_files"]} == {
        "cursor",
        "devin",
    }
    for entry in result["ade_rule_files"]:
        path = tmp_path / entry["path"]
        assert path in observed and path.read_text(encoding="utf-8") == entry["content"]
    assert (
        "alwaysApply: true" in (tmp_path / ".cursor/rules" / rule_file.name).read_text()
    )
    assert export_facade.request_paths == _expected_export_requests("playbook")
    _assert_cedar_export_pair("playbook", actor, author, before)


@pytest.mark.parametrize("existing_cursor_rule", (False, True))
def test_karma_export_with_cursor_workflow_preserves_active_rules(
    existing_cursor_rule: bool,
    export_facade: MCPClientFactory,
    tmp_path: Path,
    cedar_export_rule: tuple[User, User, Rule],
) -> None:
    """Copy a missing active rule and preserve an existing different local rule."""
    actor, author, rule = cedar_export_rule
    before = _current_award_ids()
    canonical = tmp_path / ".cursor/playbooks/Edda"
    sibling = canonical.parent / "rules" / f"{rule.slug}.mdc"
    active = canonical.parent.parent / "rules" / sibling.name
    sentinel = "Local active override."
    if existing_cursor_rule:
        active.parent.mkdir(parents=True)
        active.write_text(sentinel, encoding="utf-8")
    result = _facade_call(export_facade, "workflow", canonical)
    assert result["rule_export_paths"] == [str(sibling)]
    assert rule.content in sibling.read_text(encoding="utf-8")
    assert active.read_text(encoding="utf-8") == (
        sentinel if existing_cursor_rule else sibling.read_text(encoding="utf-8")
    )
    assert result["active_cursor_rules_synchronized"] is not existing_cursor_rule
    assert result["stale_or_missing_active_rules"] == (
        [sibling.name] if existing_cursor_rule else []
    )
    assert export_facade.request_paths == _expected_export_requests("workflow")
    _assert_cedar_export_pair("workflow", actor, author, before)


def test_karma_export_with_second_independent_call_creates_new_identity(
    export_facade: MCPClientFactory, tmp_path: Path
) -> None:
    """Prove two intentional invocations are two distinct successful events.

    :param export_facade: Real facade factory. Example: Maria's registered session.
    :param tmp_path: Actual file destination. Example: Path("/tmp/t").
    :return: None after four-row/two-UUID assertions. Example: None.
    :raises AssertionError: If independent invocations are deduplicated.
    """
    actor, author = _cedar_actors(export_facade.dataset.cedar)
    before = _current_award_ids()
    first = _facade_call(export_facade, "workflow", tmp_path)
    identity = _assert_cedar_export_pair("workflow", actor, author, before)
    root = tmp_path / _EXPORT_FOLDER
    metadata = root / "_workflow.md"
    original = metadata.read_bytes()
    metadata.write_text(
        "Local edits to replace on explicit re-export.", encoding="utf-8"
    )
    unrelated = root / "unrelated.md"
    unrelated.write_text("Preserve this file.", encoding="utf-8")
    second = _facade_call(export_facade, "workflow", tmp_path)
    assert second == first and metadata.read_bytes() == original
    assert unrelated.read_text(encoding="utf-8") == "Preserve this file."
    delta = KarmaAward.objects.exclude(pk__in=before)
    identities = {
        UUID(value.rsplit(":", 1)[-1])
        for value in delta.values_list("event_identity", flat=True)
    }
    assert delta.count() == 4 and len(identities) == 2 and identity in identities
    assert actor.karma_awards.aggregate(total=Sum("points"))["total"] == 8210
    assert author.karma_awards.aggregate(total=Sum("points"))["total"] == 12460
    assert export_facade.request_paths == _expected_export_requests("workflow") * 2


def test_karma_export_bundle_with_generation_only_creates_no_awards(
    cedar_dataset: CedarDataset,
) -> None:
    """Prove both authenticated bundle endpoints are non-awarding.

    :param cedar_dataset: Real eligible Cedar data. Example: Mike's released workflow.
    :return: None after real REST response/ledger assertions. Example: None.
    :raises AssertionError: If generating a bundle creates an award.
    """
    actor, _ = _cedar_actors(cedar_dataset)
    client = _token_api_client(actor)
    before = _current_award_ids()
    for entity, route in _BUNDLE_ROUTES.items():
        response = client.post(route, {"folder_name": _EXPORT_FOLDER}, format="json")
        assert response.status_code == 200
        bundle = response.json()
        assert bundle[f"{entity}_id"] == _ENTITY_IDS[entity]
        assert bundle["folder_name"] == _EXPORT_FOLDER
        assert bundle["workflow_files" if entity == "workflow" else "workflows"]
    assert _current_award_ids() == before


def _token_api_client(actor: User) -> APIClient:
    """Authenticate an actual Django REST client with its real fixture token."""
    token, _ = Token.objects.get_or_create(user=actor)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


def _receipt_only_file_observer(
    observed: list[tuple[dict, int]], path: Path, port: int, *, fail_attempts: int
) -> Callable[[httpx.Request], None]:
    """Observe actual completed files and route selected receipt attempts to a closed port."""

    def observe(request: httpx.Request) -> None:
        if request.url.path != _RECEIPT_PATH:
            return
        payload = json.loads(request.content)
        assert request.headers["x-request-id"] == payload["event_identity"]
        observed.append((payload, path.stat().st_mtime_ns))
        if len(observed) <= fail_attempts:
            request.url = request.url.copy_with(host="127.0.0.1", port=port)

    return observe


def test_karma_export_with_receipt_replay_preserves_single_pair(
    export_facade: MCPClientFactory, tmp_path: Path
) -> None:
    """Prove replaying a completed export receipt preserves rows and timestamps.

    :param export_facade: Real facade factory. Example: Maria's registered session.
    :param tmp_path: Actual successful export destination. Example: Path("/tmp/t").
    :return: None after same-UUID receipt replay assertions. Example: None.
    :raises AssertionError: If retry duplicates or mutates committed awards.
    """
    actor, author = _cedar_actors(export_facade.dataset.cedar)
    before = _current_award_ids()
    metadata = tmp_path / _EXPORT_FOLDER / "_workflow.md"
    observed: list[tuple[dict, int]] = []
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as unavailable:
        unavailable.bind(("127.0.0.1", 0))
        _facade_call(
            export_facade,
            "workflow",
            tmp_path,
            observe=_receipt_only_file_observer(
                observed,
                metadata,
                unavailable.getsockname()[1],
                fail_attempts=1,
            ),
        )
    identity = _assert_cedar_export_pair("workflow", actor, author, before)
    assert export_facade.request_paths == _expected_export_requests(
        "workflow", receipts=2
    )
    assert len(observed) == 2 and observed[0] == observed[1]
    payload, written_at = observed[0]
    assert payload == {
        "event_identity": str(identity),
        "entity_type": "workflow",
        "entity_id": _CEDAR_WORKFLOW_ID,
        "channel": "export",
    }
    created = list(KarmaAward.objects.exclude(pk__in=before).order_by("pk").values())
    replay = _token_api_client(actor).post(_RECEIPT_PATH, payload, format="json")
    assert replay.status_code == 200
    assert replay.json()["status"] == "replayed" and replay.json()["created_count"] == 0
    assert (
        list(KarmaAward.objects.exclude(pk__in=before).order_by("pk").values())
        == created
    )
    assert metadata.stat().st_mtime_ns == written_at


@pytest.mark.parametrize(
    ("entity", "escape"),
    (
        ("workflow", "traversal"),
        ("playbook", "traversal"),
        ("workflow", "folder"),
        ("playbook", "folder"),
        ("workflow", "sibling"),
        ("workflow", "active_directory"),
        ("workflow", "active_leaf"),
        ("playbook", "mirror"),
        ("playbook", "active_directory"),
        ("playbook", "active_leaf"),
    ),
)
def test_karma_export_with_escaping_folder_or_symlink_rejects_before_write(
    entity: str,
    escape: str,
    export_facade: MCPClientFactory,
    tmp_path: Path,
    cedar_export_rule: tuple[User, User, Rule],
) -> None:
    """Prove real traversal/symlink escapes cannot produce outside files.

    :param entity: Export kind. Example: "workflow".
    :param escape: Traversal, symlink directory or leaf. Example: "active_leaf".
    :param export_facade: Real HTTP server factory. Example: Maria's facade.
    :param tmp_path: Confined root and outside sentinel. Example: Path("/tmp/t").
    :param cedar_export_rule: Real linked rule and actors. Example: export-check.
    :return: None after rejection/file/ledger assertions. Example: None.
    :raises AssertionError: If any outside mutation or award occurs.
    """
    _, _, rule = cedar_export_rule
    before = _current_award_ids()
    project, outside = tmp_path / "project", tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / f"{rule.slug}.mdc"
    sentinel.write_text("Unchanged outside file.", encoding="utf-8")
    target = (
        project / ".cursor/playbooks/Edda"
        if entity == "workflow"
        else project / ".cursor/playbooks"
    )
    mirror, active = project / "mirror", project / ".cursor/rules"
    options = _playbook_copy_options(mirror) if entity == "playbook" else None
    _install_export_escape(escape, target, mirror, active, sentinel)
    project_paths = set(project.rglob("*"))
    folder = "../outside" if escape == "traversal" else _EXPORT_FOLDER
    with pytest.raises(ToolError, match="relative|escapes"):
        _facade_call(export_facade, entity, target, folder=folder, options=options)
    assert set(project.rglob("*")) == project_paths
    if escape == "active_leaf":
        assert (active.parent / "other" / sentinel.name).read_text(
            encoding="utf-8"
        ) == "Unchanged sibling file."
    assert tuple(outside.iterdir()) == (sentinel,)
    assert sentinel.read_text(encoding="utf-8") == "Unchanged outside file."
    assert export_facade.request_paths == _expected_export_requests(entity, receipts=0)
    assert _current_award_ids() == before


def _install_export_escape(
    escape: str, target: Path, mirror: Path, active: Path, sentinel: Path
) -> None:
    """Place a genuine outside alias at the selected output directory or leaf."""
    if escape == "traversal":
        return
    alias = {
        "folder": target / _EXPORT_FOLDER,
        "sibling": target.parent / "rules",
        "mirror": mirror / _EXPORT_FOLDER,
        "active_directory": active,
        "active_leaf": active / sentinel.name,
    }[escape]
    alias.parent.mkdir(parents=True)
    if escape == "active_leaf":
        sibling = active.parent / "other"
        sibling.mkdir()
        local_sentinel = sibling / sentinel.name
        local_sentinel.write_text("Unchanged sibling file.", encoding="utf-8")
        alias.symlink_to(local_sentinel)
    else:
        alias.symlink_to(sentinel.parent, target_is_directory=True)
    assert alias.is_symlink()


def _block_workflow_write(root: Path, actor: User) -> Path:
    """Use the actual second bundle filename as a directory to provoke a write failure."""
    bundle = (
        _token_api_client(actor)
        .post(
            _BUNDLE_ROUTES["workflow"], {"folder_name": _EXPORT_FOLDER}, format="json"
        )
        .json()
    )
    blocked = root / _EXPORT_FOLDER / bundle["workflow_files"][1]["filename"]
    blocked.mkdir(parents=True)
    return blocked


@pytest.mark.parametrize("blocked_at", ("workflow", "mirror", "ade"))
def test_karma_export_with_partial_file_failure_creates_no_receipt(
    blocked_at: str,
    export_facade: MCPClientFactory,
    tmp_path: Path,
    cedar_export_rule: tuple[User, User, Rule],
) -> None:
    """Use a real conflicting directory to fail a later file write.

    :param blocked_at: Later output to block. Example: "mirror".
    :param export_facade: Real HTTP factory. Example: Maria's registered facade.
    :param tmp_path: Workspace with later destination blocked. Example: Path("/tmp/t").
    :param cedar_export_rule: Real linked rule and actors. Example: export-check.
    :return: None after failure and zero-award assertions. Example: None.
    :raises AssertionError: If partial completion sends a receipt.
    """
    actor, _, rule = cedar_export_rule
    before = _current_award_ids()
    target, mirror = tmp_path / ".cursor/playbooks", tmp_path / "mirror"
    options = None
    if blocked_at == "workflow":
        entity = "workflow"
        blocked = _block_workflow_write(target, actor)
        first_file = "_workflow.md"
    else:
        entity = "playbook"
        options = _playbook_copy_options(mirror)
        blocked = (
            mirror / _EXPORT_FOLDER / "playbook.md"
            if blocked_at == "mirror"
            else tmp_path / ".cursor/rules" / f"{rule.slug}.mdc"
        )
        blocked.mkdir(parents=True)
        first_file = "playbook.md"
    with pytest.raises(ToolError, match="Is a directory"):
        _facade_call(export_facade, entity, target, options=options)
    assert (target / _EXPORT_FOLDER / first_file).is_file() and blocked.is_dir()
    assert export_facade.request_paths == _expected_export_requests(entity, receipts=0)
    assert _current_award_ids() == before


@pytest.mark.parametrize("entity", ("workflow", "playbook"))
def test_karma_export_stdio_t3_with_success_returns_clean_jsonrpc(
    entity: str, live_server: LiveServer, cedar_dataset: CedarDataset, tmp_path: Path
) -> None:
    """Prove actual facade stdio registration, clean output and paired effects.

    :param entity: Existing export variant. Example: "workflow".
    :param live_server: Isolated server shared with subprocess. Example: live_server.
    :param cedar_dataset: Restored Cedar baseline. Example: workflow 6202.
    :param tmp_path: Subprocess workspace. Example: Path("/tmp/t").
    :return: None after protocol/file/ledger assertions. Example: None.
    :raises AssertionError: If stdout is polluted or effects differ.
    """
    actor, author = _cedar_actors(cedar_dataset)
    before = _current_award_ids()
    workspace = tmp_path.resolve()
    case = _stdio_export_case(entity, workspace)
    with StdioMCPClient(
        entrypoint="facade",
        actor_username=actor.username,
        dataset=MCPDataset(cedar_dataset, {}, {}),
        server_url=live_server.url,
        root=workspace,
    ) as wire:
        schemas = {tool["name"]: tool["inputSchema"] for tool in wire.list_tools()}
        assert set(schemas[case.tool_name]["properties"]) == _EXPORT_PARAMETERS[entity]
        assert schemas[case.tool_name]["required"] == [f"{entity}_id"]
        assert _current_award_ids() == before
        result = wire.call(case)
    wire.assert_protocol_clean()
    _assert_stdio_export_files(entity, workspace, result, cedar_dataset)
    identity = _assert_cedar_export_pair(entity, actor, author, before)
    assert re.findall(r"HTTP Request: (.+)", wire.stderr) == [
        f'POST {live_server.url}{route} "HTTP/1.1 200 OK"'
        for route in (case.route, _RECEIPT_PATH)
    ]
    assert re.search(
        rf"export_receipt \| exit \| .*event_identity={identity} .*"
        r"receipt_status=applied created_count=2",
        wire.stderr,
    )


def _stdio_export_case(entity: str, workspace: Path) -> MCPCase:
    """Build the existing public export call for one owned stdio workspace.

    :param entity: Registered export kind. Example: "workflow".
    :param workspace: Actual child working directory. Example: Path("/tmp/t").
    :return: Tool name, public arguments and real bundle route.
    :raises KeyError: The export kind is unsupported.
    """
    tool = f"export_{entity}_to_local"
    return MCPCase(
        name=tool,
        actor_username=_ACTOR,
        tool_name=tool,
        fixture_key=f"mike_{entity}",
        arguments={
            f"{entity}_id": _ENTITY_IDS[entity],
            "target_directory": str(workspace / "exports"),
            "folder_name": _EXPORT_FOLDER,
        },
        route=_BUNDLE_ROUTES[entity],
        expected={},
    )


def _assert_stdio_export_files(
    entity: str, workspace: Path, result: object, cedar: CedarDataset
) -> None:
    """Compare the actual child output tree with its response and Cedar content.

    :param entity: Registered export kind. Example: "playbook".
    :param workspace: Isolated subprocess workspace.
    :param result: Actual tools/call payload.
    :param cedar: Original workflow and activity content.
    :return: None after checking every written file.
    :raises AssertionError: Missing, misplaced or different output files.
    """
    assert isinstance(result, dict) and result["status"] == "exported"
    assert result[f"{entity}_id"] == _ENTITY_IDS[entity]
    root = workspace / "exports" / _EXPORT_FOLDER
    paths = [result["export_path"]] if entity == "workflow" else result["export_paths"]
    assert paths == [str(root)]
    outputs = {root / filename for filename in result["files_created"]}
    assert len(outputs) == len(result["files_created"]) > 1
    assert all(path.resolve().is_relative_to(root) for path in outputs)
    rules = {Path(path) for path in result.get("rule_export_paths", ())}
    assert all(path.resolve().is_relative_to(workspace / "rules") for path in rules)
    assert {path for path in workspace.rglob("*") if path.is_file()} == outputs | rules
    content = {path.name: path.read_text(encoding="utf-8") for path in outputs}
    assert all(text.strip() for text in content.values())
    assert (
        f"# {cedar.workflows_by_pk[_CEDAR_WORKFLOW_ID].name}" in content["_workflow.md"]
    )
    activity = cedar.activities_by_pk[_CEDAR_ACTIVITY_ID]
    assert any(f"# Activity: {activity.name}" in text for text in content.values())


def test_karma_export_log_story_happy(
    export_facade: MCPClientFactory, tmp_path: Path, caplog: LogCaptureFixture
) -> None:
    """Prove E's completed-export and receipt beats through real execution.

    :param export_facade: Real HTTP factory. Example: Maria's registered facade.
    :param tmp_path: Actual workspace. Example: Path("/tmp/t").
    :param caplog: Captured structured logs. Example: caplog.
    :return: None after assert_log_story assertions. Example: None.
    :raises AssertionError: If any required safe beat is absent.
    """
    cedar = export_facade.dataset.cedar
    actor, author = _cedar_actors(cedar)
    before = _current_award_ids()
    with capture_experts_logs(caplog, _FACADE_LOGGERS):
        result = _facade_call(export_facade, "workflow", tmp_path)
    identity = _assert_cedar_export_pair("workflow", actor, author, before)
    context = (
        f"event_identity={identity}",
        f"entity_id={_CEDAR_WORKFLOW_ID}",
        "entity_type=workflow",
        "channel=export",
    )
    count = len(result["files_created"])
    assert_log_story(
        caplog,
        where="facade_export",
        beats={
            "entry": ("| entry |", "tool=export_workflow_to_local", *context),
            "validation": ("| validation |", f"destination_count={count}", *context),
            "processing": (
                "| processing |",
                f"file_count={count}",
                "files_written=true",
                *context,
            ),
        },
    )
    assert_log_story(
        caplog,
        where="export_receipt",
        beats={
            "exit": ("| exit |", "receipt_status=applied", "created_count=2", *context),
        },
    )
    assert_log_story(
        caplog,
        where="ConsumptionReceiptView.post",
        beats={
            "exit": (
                "| exit |",
                f"actor_id={actor.pk}",
                "status=applied",
                "created_count=2",
                *context,
            ),
        },
    )
    export_logs = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name in _FACADE_LOGGERS
    )
    assert Token.objects.get(user=actor).key not in export_logs
    assert cedar.workflows_by_pk[_CEDAR_WORKFLOW_ID].name not in export_logs
    assert str(tmp_path) not in export_logs


@pytest.mark.parametrize(
    "failure", ("invalid_destination", "filesystem_failure", "receipt_unavailable")
)
def test_karma_export_log_story_reject(
    failure: str,
    export_facade: MCPClientFactory,
    tmp_path: Path,
    caplog: LogCaptureFixture,
) -> None:
    """Prove confinement and partial-write errors never claim receipt success.

    :param failure: Actual filesystem or receipt issue. Example: "filesystem_failure".
    :param export_facade: Real HTTP factory. Example: Maria's registered facade.
    :param tmp_path: Rejected/blocked workspace. Example: Path("/tmp/t").
    :param caplog: Captured structured logs. Example: caplog.
    :return: None after reject-story assertions. Example: None.
    :raises AssertionError: If errors omit context or include false success.
    """
    actor, author = _cedar_actors(export_facade.dataset.cedar)
    before = _current_award_ids()
    if failure == "receipt_unavailable":
        _assert_receipt_outage_story(
            export_facade, tmp_path, caplog, actor, author, before
        )
        return
    folder = "../../outside" if failure == "invalid_destination" else _EXPORT_FOLDER
    if failure == "filesystem_failure":
        _block_workflow_write(tmp_path, actor)
    with capture_experts_logs(caplog, _FACADE_LOGGERS), pytest.raises(ToolError):
        _facade_call(export_facade, "workflow", tmp_path, folder=folder)
    operation = _facade_log_uuid(caplog)
    completed = 1 if failure == "filesystem_failure" else 0
    assert_log_story(
        caplog,
        where="facade_export",
        beats={
            "error": (
                "| error |",
                f"reason={failure}",
                f"event_identity={operation}",
                f"completed_file_count={completed}",
                "receipt_sent=false",
            ),
        },
    )
    assert (
        "files_written=true" not in caplog.text
        and "export_receipt | exit |" not in caplog.text
    )
    assert export_facade.request_paths == _expected_export_requests(
        "workflow", receipts=0
    )
    assert _current_award_ids() == before


def _facade_log_uuid(caplog: LogCaptureFixture) -> UUID:
    """Read the invocation UUID from the actual facade entry log."""
    entry = next(
        record.getMessage()
        for record in caplog.records
        if "facade_export | entry |" in record.getMessage()
    )
    return UUID(entry.split("event_identity=", 1)[1].split()[0])


def _assert_receipt_outage_story(
    factory: MCPClientFactory,
    root: Path,
    caplog: LogCaptureFixture,
    actor: User,
    author: User,
    before: set[int],
) -> None:
    """Exhaust the real receipt connection and retry just the original attestation."""
    metadata = root / _EXPORT_FOLDER / "_workflow.md"
    observed: list[tuple[dict, int]] = []
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as unavailable:
        unavailable.bind(("127.0.0.1", 0))
        observer = _receipt_only_file_observer(
            observed, metadata, unavailable.getsockname()[1], fail_attempts=2
        )
        with (
            capture_experts_logs(caplog, _FACADE_LOGGERS),
            pytest.raises(ToolError) as exc,
        ):
            _facade_call(factory, "workflow", root, observe=observer)
    operation = _facade_log_uuid(caplog)
    assert "files were written" in str(exc.value).lower()
    assert f"event_identity={operation}" in str(exc.value)
    assert_log_story(
        caplog,
        where="export_receipt",
        beats={
            "error": (
                "| error |",
                f"event_identity={operation}",
                "files_written=true",
                "receipt_status=failed",
                "channel=export",
            ),
        },
    )
    assert "export_receipt | exit |" not in caplog.text
    assert factory.request_paths == _expected_export_requests("workflow", receipts=2)
    assert _current_award_ids() == before
    assert len(observed) == 2 and observed[0] == observed[1]
    payload, written_at = observed[0]
    assert payload["event_identity"] == str(operation)
    result = _token_api_client(actor).post(_RECEIPT_PATH, payload, format="json")
    assert result.status_code == 200 and result.json()["status"] == "applied"
    assert _assert_cedar_export_pair("workflow", actor, author, before) == operation
    assert metadata.stat().st_mtime_ns == written_at


@pytest.fixture(name="self_export_dataset")
def _self_export_dataset(mcp_dataset: MCPDataset) -> MCPDataset:
    """Link a real non-apply-on rule to Mike's existing Cedar activity."""
    rule = Rule.objects.get(pk=mcp_dataset.entity_ids["mike_rule"])
    rule.always_apply = False
    rule.save(update_fields=["always_apply"])
    mcp_dataset.cedar.activities_by_pk[_CEDAR_ACTIVITY_ID].rules.add(rule)
    return mcp_dataset


def _self_export_targets(entity: str, workspace: Path) -> tuple[Path, ...]:
    """Define the exact requested canonical and mirror destinations."""
    if entity == "playbook":
        return workspace / ".cursor/playbooks", workspace / "mirror"
    return (workspace / "workflows",)


def _self_export_playbook_options(mirror: Path) -> dict[str, object]:
    """Exercise both file ADEs and both inline ADEs in one real export."""
    return {
        **_playbook_copy_options(mirror),
        "ade_targets": ["devin", "claude", "copilot"],
    }


def _self_export_bundle(entity: str, mike: User) -> dict:
    """Read the real bundle without writing files, for legacy/service comparison."""
    if entity == "workflow":
        return WorkflowExportService.generate_workflow_files(
            _CEDAR_WORKFLOW_ID, _EXPORT_FOLDER
        )
    return PlaybookExportService.generate_playbook_export_bundle(
        _CEDAR_PLAYBOOK_ID,
        _EXPORT_FOLDER,
        ade_targets=["devin", "claude", "copilot"],
        ade_target="Cursor",
        force_apply=True,
        sync_root_rules=True,
        user=mike,
    )


def _observe_self_export_response(
    responses: dict[str, dict], entity: str, response: httpx.Response
) -> None:
    """Read the exact successful real payload before the facade handles it."""
    path = response.request.url.path
    if path in (_BUNDLE_ROUTES[entity], _RECEIPT_PATH):
        assert path not in responses
        response.raise_for_status()
        response.read()
        responses[path] = response.json()


@async_to_sync
async def _registered_self_export(
    factory: MCPClientFactory,
    entrypoint: Literal["facade", "legacy"],
    tool_name: str,
    entity: str,
    targets: tuple[Path, ...],
) -> tuple[dict, dict[str, dict]]:
    """Discover and call the real registered tool as Mike, returning HTTP observations."""
    responses: dict[str, dict] = {}
    arguments = {
        f"{entity}_id": _ENTITY_IDS[entity],
        "target_directory": str(targets[0]),
        "folder_name": _EXPORT_FOLDER,
    }
    if entity == "playbook":
        arguments.update(_self_export_playbook_options(targets[1]))
    async with factory.open(actor_username=_AUTHOR, entrypoint=entrypoint) as session:
        if entrypoint == "facade":
            hook = partial(_observe_self_export_response, responses, entity)
            get_client().event_hooks["response"].append(hook)
        [schema] = [
            tool.inputSchema
            for tool in await session.client.list_tools()
            if tool.name == tool_name
        ]
        assert set(schema["properties"]) == _EXPORT_PARAMETERS[entity]
        assert schema["required"] == [f"{entity}_id"]
        result = decode_tool_payload(
            await session.client.call_tool(tool_name, arguments)
        )
    assert isinstance(result, dict)
    return result, responses


def _verify_registered_self_export(
    factory: MCPClientFactory,
    entrypoint: Literal["facade", "legacy"],
    tool_name: str,
    workspace: Path,
) -> None:
    """Run one registered self-export and verify every output before persisted state."""
    entity = tool_name.split("_")[1]
    mike = assert_owned_export_source(factory.dataset.cedar)
    before = capture_export_karma_state()
    targets = _self_export_targets(entity, workspace)
    facade = entrypoint == "facade"
    bundle = {} if facade else _self_export_bundle(entity, mike)
    started = datetime.now(UTC)
    result, responses = _registered_self_export(
        factory, entrypoint, tool_name, entity, targets
    )
    finished = datetime.now(UTC)
    if facade:
        bundle = responses[_BUNDLE_ROUTES[entity]]
    assert_complete_self_export(
        result=result,
        bundle=bundle,
        workspace=workspace,
        started_at=started,
        finished_at=finished,
        targets=targets,
        facade=facade,
        sync_root_rules=entity == "playbook",
    )
    assert_self_export_karma_unchanged(before)
    if facade:
        assert factory.request_paths == _expected_export_requests(entity)
        _assert_self_export_receipt(responses[_RECEIPT_PATH])
    else:
        assert not factory.request_paths and not responses


def _assert_self_export_receipt(receipt: dict[str, object]) -> None:
    """Verify the newly completed action received the shared exclusion outcome."""
    identity = UUID(str(receipt["event_identity"]))
    assert receipt == {
        "event_identity": str(identity),
        "status": "skipped",
        "created_count": 0,
        "reason": "self_consumption",
    }


@pytest.mark.parametrize(
    "tool_name", ["export_workflow_to_local", "export_playbook_to_local"]
)
def test_self_export_facade_t1_with_owned_content_writes_files_without_awards(
    tool_name: str,
    live_server: LiveServer,
    tmp_path: Path,
    self_export_dataset: MCPDataset,
) -> None:
    """Certify real facade registration, HTTP/token and complete self-export.

    :param tool_name: Registered tool. Example: 'export_workflow_to_local'.
    :param live_server: Real isolated Django HTTP server. Example: localhost port.
    :param tmp_path: Actual empty filesystem root. Example: /tmp/pytest/self.
    :param self_export_dataset: Real Cedar plus linked rule and nonempty export collections.
    :return: None. Example: all files verified before zero-award assertions.
    :raises AssertionError: Registration, successful files or unchanged state fail.
    """
    factory = MCPClientFactory(self_export_dataset, live_server.url, [])
    _verify_registered_self_export(factory, "facade", tool_name, tmp_path.resolve())


@pytest.mark.parametrize(
    "tool_name", ["export_workflow_to_local", "export_playbook_to_local"]
)
def test_self_export_legacy_t1_with_owned_content_writes_files_without_awards(
    tool_name: str, tmp_path: Path, self_export_dataset: MCPDataset
) -> None:
    """Certify registered legacy tools with Mike's real user context.

    :param tool_name: Existing tool. Example: 'export_playbook_to_local'.
    :param tmp_path: Actual isolated filesystem root. Example: /tmp/pytest/legacy.
    :param self_export_dataset: Real Cedar including Mike's linked rule. Example: playbook 6201.
    :return: None. Example: complete export and unchanged global ledger.
    :raises AssertionError: Tool registration, user context or output differs.
    """
    factory = MCPClientFactory(self_export_dataset, "", [])
    _verify_registered_self_export(factory, "legacy", tool_name, tmp_path.resolve())


@pytest.mark.parametrize(
    "tool_name", ["export_workflow_to_local", "export_playbook_to_local"]
)
def test_self_export_service_t2_with_owned_content_writes_files_without_awards(
    tool_name: str, tmp_path: Path, self_export_dataset: MCPDataset
) -> None:
    """Certify both real filesystem services and shared self-exclusion.

    :param tool_name: Export kind selector. Example: 'export_workflow_to_local'.
    :param tmp_path: Real filesystem root. Example: /tmp/pytest/service.
    :param self_export_dataset: Real Cedar plus nonempty playbook export collections.
    :return: None. Example: successful bytes and Mike12450/GUI47 unchanged.
    :raises AssertionError: Output incomplete or any user's awards change.
    """
    entity = tool_name.split("_")[1]
    mike = assert_owned_export_source(self_export_dataset.cedar)
    before = capture_export_karma_state()
    workspace = tmp_path.resolve()
    targets = _self_export_targets(entity, workspace)
    bundle = _self_export_bundle(entity, mike)
    started = datetime.now(UTC)
    if entity == "playbook":
        result = PlaybookExportService.export_playbook_to_local(
            _CEDAR_PLAYBOOK_ID,
            str(targets[0]),
            folder_name=_EXPORT_FOLDER,
            user=mike,
            **_self_export_playbook_options(targets[1]),
        )
    else:
        result = _legacy_export(entity, targets[0], mike)
    assert_complete_self_export(
        result=result,
        bundle=bundle,
        workspace=workspace,
        started_at=started,
        finished_at=datetime.now(UTC),
        targets=targets,
        sync_root_rules=entity == "playbook",
    )
    assert_self_export_karma_unchanged(before)


@pytest.mark.parametrize("entrypoint", ["facade", "legacy"])
def test_self_export_log_story_happy(
    entrypoint: Literal["facade", "legacy"],
    live_server: LiveServer,
    tmp_path: Path,
    caplog: LogCaptureFixture,
    self_export_dataset: MCPDataset,
) -> None:
    """Prove successful files precede the self-consumption zero-award branch.

    :param entrypoint: Actual server path. Example: 'facade'.
    :param live_server: Real HTTP server. Example: localhost random port.
    :param tmp_path: Real destination root. Example: /tmp/pytest/logs.
    :param caplog: Actual captured records. Example: INFO export/receipt beats.
    :param self_export_dataset: Actual Cedar entities. Example: Mike owns workflow 6202.
    :return: None. Example: ordered shared identity and created_count=0.
    :raises AssertionError: Missing beats, false failure or leaked credentials.
    """
    factory = MCPClientFactory(self_export_dataset, live_server.url, [])
    workspace = tmp_path.resolve()
    with capture_experts_logs(caplog, _SELF_EXPORT_LOGGERS):
        _verify_registered_self_export(
            factory, entrypoint, "export_workflow_to_local", workspace
        )
    mike = self_export_dataset.cedar.users_by_username[_AUTHOR]
    count = sum(path.is_file() for path in workspace.rglob("*"))
    _assert_self_export_log_story(caplog, entrypoint, mike, count)
    _assert_self_export_logs_safe(caplog, mike, workspace)


def _assert_self_export_logs_safe(
    caplog: LogCaptureFixture, mike: User, workspace: Path
) -> None:
    """Check correlated export/receipt logs omit credentials, paths and prose."""
    relevant = (
        "facade_export",
        "export_receipt",
        _EXPORT_LOG["workflow"],
        _SELF_CONSUMPTION_LOG,
        "ConsumptionReceiptView.post",
    )
    messages = "\n".join(
        record.message
        for record in caplog.records
        if record.message.startswith(relevant)
    )
    activity = Activity.objects.select_related("workflow").get(pk=_CEDAR_ACTIVITY_ID)
    sensitive = (
        str(workspace),
        Token.objects.get(user=mike).key,
        mike.email,
        activity.workflow.name,
        activity.guidance,
        activity.rules.get().content,
    )
    assert all(secret not in messages for secret in sensitive if secret)


def _assert_self_export_log_story(
    caplog: LogCaptureFixture,
    entrypoint: Literal["facade", "legacy"],
    mike: User,
    file_count: int,
) -> None:
    """Prove correlated file completion, self-exclusion and zero-created exit in order."""
    facade = entrypoint == "facade"
    operation = "facade_export" if facade else _EXPORT_LOG["workflow"]
    identity_key = "event_identity" if facade else "operation_uuid"
    identity = _self_export_processing_identity(caplog, operation, identity_key)
    source = (
        f"{identity_key}={identity}",
        "entity_type=workflow",
        f"entity_id={_CEDAR_WORKFLOW_ID}",
    )
    assert file_count > 0
    processing = (*source, f"file_count={file_count}", "files_written=true")
    branch = (
        f"action_uuid={identity}",
        "channel=export",
        f"actor_id={mike.pk}",
        f"playbook_id={_CEDAR_PLAYBOOK_ID}",
        f"author_id={mike.pk}",
        "reason=self_consumption",
        "awards=0",
    )
    exit_owner = "export_receipt" if facade else operation
    outcome = "receipt_status=skipped" if facade else "outcome=ineligible"
    exited = (*source, "channel=export", outcome, "created_count=0")
    beats = (
        (operation, "processing", processing),
        (_SELF_CONSUMPTION_LOG, "branch", branch),
        (exit_owner, "exit", exited),
    )
    _assert_ordered_self_export_beats(caplog, beats)
    _assert_no_self_export_award_or_error(caplog, identity)


def _self_export_processing_identity(
    caplog: LogCaptureFixture, operation: str, identity_key: str
) -> UUID:
    """Read the unique invocation UUID from its actual file-completion log."""
    prefix = f"{operation} | processing |"
    [message] = [
        record.message for record in caplog.records if record.message.startswith(prefix)
    ]
    match = re.search(rf"\b{identity_key}=([\w-]+)", message)
    assert match
    return UUID(match[1])


def _assert_ordered_self_export_beats(
    caplog: LogCaptureFixture, beats: tuple[tuple[str, str, tuple[str, ...]], ...]
) -> None:
    """Require one exact, ordered INFO record for each declared beat."""
    indices = []
    for owner, beat, fragments in beats:
        prefix = f"{owner} | {beat} |"
        assert_log_story(caplog, where=owner, beats={beat: (prefix, *fragments)})
        [index] = [
            index
            for index, record in enumerate(caplog.records)
            if record.levelno >= logging.INFO
            and record.message.startswith(prefix)
            and set(fragments).issubset(record.message.split())
        ]
        indices.append(index)
    assert indices == sorted(set(indices))


def _assert_no_self_export_award_or_error(
    caplog: LogCaptureFixture, identity: UUID
) -> None:
    """Check the correlated action has no award-created or failure beat."""
    related = [
        record.message for record in caplog.records if str(identity) in record.message
    ]
    assert not any(
        "| error |" in message
        or "reason=eligible" in message
        or "outcome=awarded" in message
        or "status=applied" in message
        for message in related
    )


@pytest.mark.parametrize("entrypoint", ["facade", "legacy"])
@pytest.mark.parametrize(
    "tool_name", ["export_workflow_to_local", "export_playbook_to_local"]
)
def test_self_export_stdio_t3_with_owned_content_returns_clean_jsonrpc(
    entrypoint: str, tool_name: str, live_server: LiveServer, tmp_path: Path
) -> None:
    """Certify real subprocess protocol, content, files and unchanged awards.

    :param entrypoint: Real facade or legacy entrypoint. Example: 'legacy'.
    :param tool_name: Existing export tool. Example: 'export_playbook_to_local'.
    :param live_server: Isolated HTTP backend for facade. Example: localhost port.
    :param tmp_path: Real export/legacy-DB root. Example: /tmp/pytest/stdio.
    :return: None. Example: clean JSON-RPC and complete zero-award export.
    :raises AssertionError: Protocol noise, tool error, missing file or new award.
    """
    raise NotImplementedError()
