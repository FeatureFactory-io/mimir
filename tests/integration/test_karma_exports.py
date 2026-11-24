from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

import pytest
from django.contrib.auth.models import User
from django.db.models import Sum
from fastmcp import FastMCP
from pytest import LogCaptureFixture
from pytest_django.live_server_helper import LiveServer

from mcp_integration.facade.export_paths import confined_export_path
from methodology.models import KarmaAward, Playbook, Rule
from methodology.services.playbook_export_service import PlaybookExportService
from methodology.services.workflow_export_service import WorkflowExportService
from tests.support.experts_data import load_cedar_baseline
from tests.support.log_story import assert_log_story

pytestmark = pytest.mark.django_db(transaction=True)

_CEDAR_PLAYBOOK_ID = 6201
_CEDAR_WORKFLOW_ID = 6202
_EXPORT_FOLDER = "cedar"
_EXPORT_LOG = {
    "workflow": "WorkflowExportService.export_workflow_to_markdown",
    "playbook": "PlaybookExportService.export_playbook_to_local",
}


def _configure_real_export_facade(live_server: LiveServer, actor: User) -> FastMCP:
    """Configure real token HTTP and return existing registered facade.

    :param live_server: Isolated pytest Django server. Example: live_server.
    :param actor: Cedar consumer. Example: Maria.
    :return: Existing registered FastMCP instance. Example: _build_mcp().
    :raises RuntimeError: If token/server configuration fails.
    """
    raise NotImplementedError()


def test_karma_export_facade_t1_with_multiple_files_awards_one_pair(
    live_server: LiveServer, tmp_path: Path
) -> None:
    """Prove both registered exports over real HTTP, files and paired ledger.

    :param live_server: Isolated real server. Example: live_server.
    :param tmp_path: Authorized temporary workspace. Example: Path("/tmp/t").
    :return: None after D's T1 assertions. Example: None.
    :raises AssertionError: If registration, files, totals or pair count differ.
    """
    raise NotImplementedError()


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
def cedar_export_rule() -> tuple[User, User, Rule]:
    """Restore the Cedar actors and attach an actual workflow rule to export."""
    cedar = load_cedar_baseline()
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
    result = _legacy_playbook_with_copies(
        canonical, mirror, actor, ade_targets=["devin"]
    )
    assert result["export_paths"] == [
        str(base / _EXPORT_FOLDER) for base in (canonical, mirror)
    ]
    exported = f"rules/{rule.slug}.mdc"
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


def test_karma_export_with_mirrors_and_ade_files_awards_one_pair(
    live_server: LiveServer, tmp_path: Path
) -> None:
    """Prove requested extra copies do not multiply awards.

    :param live_server: Real token-authenticated HTTP server. Example: live_server.
    :param tmp_path: Canonical/mirror/ADE workspace. Example: Path("/tmp/t").
    :return: None after actual-copy and pair assertions. Example: None.
    :raises AssertionError: If copies differ or awards multiply.
    """
    raise NotImplementedError()


def test_karma_export_with_second_independent_call_creates_new_identity(
    live_server: LiveServer, tmp_path: Path
) -> None:
    """Prove two intentional invocations are two distinct successful events.

    :param live_server: Real HTTP server. Example: live_server.
    :param tmp_path: Actual file destination. Example: Path("/tmp/t").
    :return: None after four-row/two-UUID assertions. Example: None.
    :raises AssertionError: If independent invocations are deduplicated.
    """
    raise NotImplementedError()


def test_karma_export_bundle_with_generation_only_creates_no_awards() -> None:
    """Prove both authenticated bundle endpoints are non-awarding.

    :return: None after real REST response/ledger assertions. Example: None.
    :raises AssertionError: If generating a bundle creates an award.
    """
    raise NotImplementedError()


def test_karma_export_with_receipt_replay_preserves_single_pair(
    live_server: LiveServer, tmp_path: Path
) -> None:
    """Prove replaying a completed export receipt preserves rows and timestamps.

    :param live_server: Real HTTP server. Example: live_server.
    :param tmp_path: Actual successful export destination. Example: Path("/tmp/t").
    :return: None after same-UUID receipt replay assertions. Example: None.
    :raises AssertionError: If retry duplicates or mutates committed awards.
    """
    raise NotImplementedError()


def test_karma_export_with_escaping_folder_or_symlink_rejects_before_write(
    live_server: LiveServer, tmp_path: Path
) -> None:
    """Prove real traversal/symlink escapes cannot produce outside files.

    :param live_server: Real HTTP server. Example: live_server.
    :param tmp_path: Confined root and outside sentinel. Example: Path("/tmp/t").
    :return: None after rejection/file/ledger assertions. Example: None.
    :raises AssertionError: If any outside mutation or award occurs.
    """
    raise NotImplementedError()


def test_karma_export_with_partial_file_failure_creates_no_receipt(
    live_server: LiveServer, tmp_path: Path
) -> None:
    """Use a real conflicting directory to fail a later file write.

    :param live_server: Real HTTP server. Example: live_server.
    :param tmp_path: Workspace with later destination blocked. Example: Path("/tmp/t").
    :return: None after failure and zero-award assertions. Example: None.
    :raises AssertionError: If partial completion sends a receipt.
    """
    raise NotImplementedError()


def test_karma_export_stdio_t3_with_success_returns_clean_jsonrpc(
    live_server: LiveServer, tmp_path: Path
) -> None:
    """Prove actual facade stdio registration, clean output and paired effects.

    :param live_server: Isolated server shared with subprocess. Example: live_server.
    :param tmp_path: Subprocess workspace. Example: Path("/tmp/t").
    :return: None after protocol/file/ledger assertions. Example: None.
    :raises AssertionError: If stdout is polluted or effects differ.
    """
    raise NotImplementedError()


def test_karma_export_log_story_happy(
    live_server: LiveServer, tmp_path: Path, caplog: LogCaptureFixture
) -> None:
    """Prove E's completed-export and receipt beats through real execution.

    :param live_server: Real HTTP server. Example: live_server.
    :param tmp_path: Actual workspace. Example: Path("/tmp/t").
    :param caplog: Captured structured logs. Example: caplog.
    :return: None after assert_log_story assertions. Example: None.
    :raises AssertionError: If any required safe beat is absent.
    """
    raise NotImplementedError()


def test_karma_export_log_story_reject(
    live_server: LiveServer, tmp_path: Path, caplog: LogCaptureFixture
) -> None:
    """Prove confinement and partial-write errors never claim receipt success.

    :param live_server: Real HTTP server. Example: live_server.
    :param tmp_path: Rejected/blocked workspace. Example: Path("/tmp/t").
    :param caplog: Captured structured logs. Example: caplog.
    :return: None after reject-story assertions. Example: None.
    :raises AssertionError: If errors omit context or include false success.
    """
    raise NotImplementedError()


@pytest.mark.parametrize(
    "tool_name", ["export_workflow_to_local", "export_playbook_to_local"]
)
def test_self_export_facade_t1_with_owned_content_writes_files_without_awards(
    tool_name: str, live_server: LiveServer, tmp_path: Path
) -> None:
    """Certify real facade registration, HTTP/token and complete self-export.

    :param tool_name: Registered tool. Example: 'export_workflow_to_local'.
    :param live_server: Real isolated Django HTTP server. Example: localhost port.
    :param tmp_path: Actual empty filesystem root. Example: /tmp/pytest/self.
    :return: None. Example: all files verified before zero-award assertions.
    :raises AssertionError: Registration, successful files or unchanged state fail.
    """
    raise NotImplementedError()


@pytest.mark.parametrize(
    "tool_name", ["export_workflow_to_local", "export_playbook_to_local"]
)
def test_self_export_legacy_t1_with_owned_content_writes_files_without_awards(
    tool_name: str, tmp_path: Path
) -> None:
    """Certify registered legacy tools with Mike's real user context.

    :param tool_name: Existing tool. Example: 'export_playbook_to_local'.
    :param tmp_path: Actual isolated filesystem root. Example: /tmp/pytest/legacy.
    :return: None. Example: complete export and unchanged global ledger.
    :raises AssertionError: Tool registration, user context or output differs.
    """
    raise NotImplementedError()


@pytest.mark.parametrize(
    "tool_name", ["export_workflow_to_local", "export_playbook_to_local"]
)
def test_self_export_service_t2_with_owned_content_writes_files_without_awards(
    tool_name: str, tmp_path: Path
) -> None:
    """Certify both real filesystem services and shared self-exclusion.

    :param tool_name: Export kind selector. Example: 'export_workflow_to_local'.
    :param tmp_path: Real filesystem root. Example: /tmp/pytest/service.
    :return: None. Example: successful bytes and Mike12450/GUI47 unchanged.
    :raises AssertionError: Output incomplete or any user's awards change.
    """
    raise NotImplementedError()


@pytest.mark.parametrize("entrypoint", ["facade", "legacy"])
def test_self_export_log_story_happy(
    entrypoint: str, live_server: LiveServer, tmp_path: Path, caplog: LogCaptureFixture
) -> None:
    """Prove successful files precede the self-consumption zero-award branch.

    :param entrypoint: Actual server path. Example: 'facade'.
    :param live_server: Real HTTP server. Example: localhost random port.
    :param tmp_path: Real destination root. Example: /tmp/pytest/logs.
    :param caplog: Actual captured records. Example: INFO export/receipt beats.
    :return: None. Example: ordered shared identity and created_count=0.
    :raises AssertionError: Missing beats, false failure or leaked credentials.
    """
    raise NotImplementedError()


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
