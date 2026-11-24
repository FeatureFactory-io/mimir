"""
MCP HTTP facade tools.

Synchronous functions, each mapping one MCP tool to one or more
REST API calls via httpx.  Same tool names, same parameter signatures,
same semantic return shapes as the ORM-based tools.py (where applicable).

No Django, no ORM — only the standard library + httpx.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Mapping
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Literal, NamedTuple, Optional
from uuid import UUID, uuid4

import httpx

from mcp_integration.facade.client import check_response, get_client, get_server_url
from mcp_integration.facade.export_paths import confined_export_path
from mcp_integration.facade.workspace_mount import (
    ensure_import_supported_on_server,
    ensure_readable_workspace_path,
    ensure_writable_workspace_path,
    resolve_dev_root_from_export_target,
)

logger = logging.getLogger(__name__)
_RECEIPT_PATH = "/api/consumption-receipts/"
_RECEIPT_ATTEMPTS = 2
_RETRYABLE_RECEIPT_STATUS = {408, 429, 500, 502, 503, 504}
_MCP_DETAIL_CHANNEL = "mcp_detail"
_DETAIL_REJECT_LOG = "%s | branch | entity_id=%s event_identity=%s reason=read_rejected"
_EXPORT_CHANNEL = "export"
_ADE_RULE_FOLDERS = {"cursor": (".cursor", "rules"), "devin": (".windsurf", "rules")}


class _ExportWrite(NamedTuple):
    """One ordered output rooted in an approved workspace path."""

    root: Path
    folders: tuple[str, ...]
    filename: str
    content: str
    only_if_missing: bool = False


class _LocalExportPlan(NamedTuple):
    """Complete ordered file work and the existing result assembled afterward."""

    writes: tuple[_ExportWrite, ...]
    build_result: Callable[[], dict]


# ============================================================================
# PLAYBOOK TOOLS (5)
# ============================================================================


def create_playbook(
    name: str,
    description: str,
    category: str,
    visibility: Literal["private", "public"] = "private",
) -> dict:
    """
    Create draft playbook.

    :param name: Playbook name. Example: "React Development"
    :param description: Description. Example: "Modern React patterns"
    :param category: Category. Example: "development"
    :param visibility: private or public (default private)
    :return: Created playbook dict
    """
    logger.info(f'HTTP Tool: create_playbook name="{name}"')
    r = get_client().post(
        "/api/playbooks/",
        json={
            "name": name,
            "description": description,
            "category": category,
            "visibility": visibility,
        },
    )
    return check_response(r, "create_playbook")


def list_playbooks(
    status: Literal["draft", "released", "active", "all"] = "all",
) -> list:
    """
    List playbooks filtered by status.

    :param status: Filter by status or "all". Example: "draft"
    :return: List of playbook dicts
    """
    logger.info(f"HTTP Tool: list_playbooks status={status}")
    params = {} if status == "all" else {"status": status}
    r = get_client().get("/api/playbooks/", params=params)
    data = check_response(r, "list_playbooks")
    return data.get("results", data) if isinstance(data, dict) else data


def get_playbook(
    playbook_id: int,
    include_history: bool = False,
    version: str | None = None,
    event_identity: str | None = None,
) -> dict:
    """
    Get playbook details with workflows and optional version history.

    :param playbook_id: Playbook ID. Example: 1
    :param include_history: When True, adds a ``versions`` list to the response
        (ordered newest-first). Each entry has ``version_number``, ``source``
        (pip/author/release/admin), ``pip_id``, ``change_summary``,
        ``created_at`` (ISO-8601), ``is_major``.
        Ignored when ``version`` is also provided. Example: True
    :param version: When provided, returns only the recorded snapshot at that
        version (``snapshot_data`` + metadata). Raises ValueError if not found.
        Takes precedence over ``include_history``. Example: "1.0"
    :param event_identity: Optional UUID to reuse when retrying this read.
    :return: Playbook dict with nested workflows (and optionally ``versions``);
        or snapshot dict when ``version`` is supplied (contains
        ``snapshot_data``, no top-level ``workflows`` key).
    :raises ValueError: if the requested version does not exist.
    """
    tool = "get_playbook"
    identity = _resolve_consumption_event_identity(event_identity)
    params = {}
    if include_history:
        params["include_history"] = "true"
    if version is not None:
        params["version"] = version
    try:
        response = get_client().get(f"/api/playbooks/{playbook_id}/", params=params)
        if version is not None and response.status_code == 404:
            raise ValueError(
                response.json().get(
                    "detail", f"Version {version} not found for playbook {playbook_id}."
                )
            )
        payload = check_response(response, tool)
    except ValueError, PermissionError, RuntimeError, httpx.HTTPError:
        logger.info(_DETAIL_REJECT_LOG, tool, playbook_id, identity)
        raise
    return _complete_mcp_detail(
        payload,
        tool_name=tool,
        entity_type="playbook",
        entity_id=playbook_id,
        event_identity=identity,
    )


def update_playbook(
    playbook_id: int,
    name: str = None,
    description: str = None,
    category: str = None,
    visibility: Optional[Literal["private", "public"]] = None,
) -> dict:
    """
    Update DRAFT playbook. Auto-increments version.

    :param playbook_id: Playbook ID. Example: 1
    :param name: New name or None
    :param description: New description or None
    :param category: New category or None
    :param visibility: New visibility or None
    :return: Updated playbook dict
    """
    logger.info(f"HTTP Tool: update_playbook id={playbook_id}")
    payload = {
        k: v
        for k, v in {
            "name": name,
            "description": description,
            "category": category,
            "visibility": visibility,
        }.items()
        if v is not None
    }
    r = get_client().patch(f"/api/playbooks/{playbook_id}/", json=payload)
    return check_response(r, "update_playbook")


def delete_playbook(playbook_id: int) -> dict:
    """
    Delete DRAFT playbook.

    :param playbook_id: Playbook ID. Example: 1
    :return: Confirmation dict
    """
    logger.info(f"HTTP Tool: delete_playbook id={playbook_id}")
    r = get_client().delete(f"/api/playbooks/{playbook_id}/")
    return check_response(r, "delete_playbook")


# ============================================================================
# WORKFLOW TOOLS (5)
# ============================================================================


def create_workflow(
    playbook_id: int,
    name: str,
    description: str = "",
    order: int = None,
    abbreviation: str = None,
) -> dict:
    """
    Create workflow in DRAFT playbook.

    :param playbook_id: Parent playbook ID. Example: 1
    :param name: Workflow name. Example: "Design Phase"
    :param description: Workflow description (optional)
    :param order: Optional 1-based position. Example: 2
    :param abbreviation: Optional 2–8 letter code. Example: "IDA"
    :return: Created workflow dict
    """
    logger.info(f'HTTP Tool: create_workflow name="{name}" playbook={playbook_id}')
    payload = {
        "playbook_id": playbook_id,
        "name": name,
        "description": description,
    }
    if order is not None:
        payload["order"] = order
    if abbreviation is not None:
        payload["abbreviation"] = abbreviation
    r = get_client().post("/api/workflows/", json=payload)
    return check_response(r, "create_workflow")


def list_workflows(playbook_id: int) -> list:
    """
    List workflows for playbook.

    :param playbook_id: Parent playbook ID. Example: 1
    :return: List of workflow dicts
    """
    logger.info(f"HTTP Tool: list_workflows playbook={playbook_id}")
    r = get_client().get("/api/workflows/", params={"playbook_id": playbook_id})
    data = check_response(r, "list_workflows")
    return data.get("results", data) if isinstance(data, dict) else data


def get_workflow(workflow_id: int, event_identity: str | None = None) -> dict:
    """
    Get workflow details with activities.

    :param workflow_id: Workflow ID. Example: 1
    :param event_identity: Optional UUID to reuse when retrying this read.
    :return: Workflow dict with nested activities
    :raises ValueError: Invalid identity or unavailable resource.
    """
    tool = "get_workflow"
    identity = _resolve_consumption_event_identity(event_identity)
    try:
        response = get_client().get(f"/api/workflows/{workflow_id}/")
        payload = check_response(response, tool)
    except ValueError, PermissionError, RuntimeError, httpx.HTTPError:
        logger.info(_DETAIL_REJECT_LOG, tool, workflow_id, identity)
        raise
    return _complete_mcp_detail(
        payload,
        tool_name=tool,
        entity_type="workflow",
        entity_id=workflow_id,
        event_identity=identity,
    )


def update_workflow(
    workflow_id: int,
    name: str = None,
    description: str = None,
    order: int = None,
    abbreviation: str = None,
) -> dict:
    """
    Update workflow in DRAFT playbook. Increments parent version.

    :param workflow_id: Workflow ID. Example: 1
    :param name: New name or None
    :param description: New description or None
    :param order: New order or None
    :param abbreviation: New 2–8 letter code or None. Example: "IDA"
    :return: Updated workflow dict
    """
    logger.info(f"HTTP Tool: update_workflow id={workflow_id}")
    payload = {
        k: v
        for k, v in {
            "name": name,
            "description": description,
            "order": order,
            "abbreviation": abbreviation,
        }.items()
        if v is not None
    }
    r = get_client().patch(f"/api/workflows/{workflow_id}/", json=payload)
    return check_response(r, "update_workflow")


def delete_workflow(workflow_id: int) -> dict:
    """
    Delete workflow in DRAFT playbook.

    :param workflow_id: Workflow ID. Example: 1
    :return: Confirmation dict
    """
    logger.info(f"HTTP Tool: delete_workflow id={workflow_id}")
    r = get_client().delete(f"/api/workflows/{workflow_id}/")
    return check_response(r, "delete_workflow")


# ============================================================================
# ACTIVITY TOOLS (6)
# ============================================================================


def create_activity(
    workflow_id: int,
    name: str,
    guidance: str = "",
    phase_id: int = None,
    predecessor_id: int = None,
) -> dict:
    """
    Create activity in workflow (DRAFT playbook).

    :param workflow_id: Parent workflow ID. Example: 1
    :param name: Activity name. Example: "Design Component"
    :param guidance: Rich Markdown guidance (optional)
    :param phase_id: Phase ID to assign (optional)
    :param predecessor_id: Predecessor activity ID (optional)
    :return: Created activity dict
    """
    logger.info(f'HTTP Tool: create_activity name="{name}" workflow={workflow_id}')
    payload = {"workflow_id": workflow_id, "name": name, "guidance": guidance}
    if phase_id is not None:
        payload["phase_id"] = phase_id
    if predecessor_id is not None:
        payload["predecessor_id"] = predecessor_id
    r = get_client().post("/api/activities/", json=payload)
    return check_response(r, "create_activity")


def list_activities(workflow_id: int) -> list:
    """
    List activities for workflow.

    :param workflow_id: Parent workflow ID. Example: 1
    :return: List of activity dicts
    """
    logger.info(f"HTTP Tool: list_activities workflow={workflow_id}")
    r = get_client().get("/api/activities/", params={"workflow_id": workflow_id})
    data = check_response(r, "list_activities")
    return data.get("results", data) if isinstance(data, dict) else data


def get_activity(activity_id: int, event_identity: str | None = None) -> dict:
    """
    Get activity details with dependencies, agent, skill, and artifacts.

    :param activity_id: Activity ID. Example: 1
    :param event_identity: Optional UUID to reuse when retrying this read.
    :return: Activity dict with predecessor/successor, agent, skill, artifacts
    :raises ValueError: Invalid identity or unavailable resource.
    """
    tool = "get_activity"
    identity = _resolve_consumption_event_identity(event_identity)
    try:
        response = get_client().get(f"/api/activities/{activity_id}/")
        payload = check_response(response, tool)
    except ValueError, PermissionError, RuntimeError, httpx.HTTPError:
        logger.info(_DETAIL_REJECT_LOG, tool, activity_id, identity)
        raise
    return _complete_mcp_detail(
        payload,
        tool_name=tool,
        entity_type="activity",
        entity_id=activity_id,
        event_identity=identity,
    )


def update_activity(
    activity_id: int,
    name: str = None,
    guidance: str = None,
    phase_id: int = None,
    order: int = None,
) -> dict:
    """
    Update activity in DRAFT playbook.

    :param activity_id: Activity ID. Example: 1
    :param name: New name or None
    :param guidance: New guidance or None
    :param phase_id: New phase ID or None
    :param order: New order or None
    :return: Updated activity dict
    """
    logger.info(f"HTTP Tool: update_activity id={activity_id}")
    payload = {
        k: v
        for k, v in {
            "name": name,
            "guidance": guidance,
            "phase_id": phase_id,
            "order": order,
        }.items()
        if v is not None
    }
    r = get_client().patch(f"/api/activities/{activity_id}/", json=payload)
    return check_response(r, "update_activity")


def delete_activity(activity_id: int) -> dict:
    """
    Delete activity in DRAFT playbook.

    :param activity_id: Activity ID. Example: 1
    :return: Confirmation dict
    """
    logger.info(f"HTTP Tool: delete_activity id={activity_id}")
    r = get_client().delete(f"/api/activities/{activity_id}/")
    return check_response(r, "delete_activity")


def set_predecessor(activity_id: int, predecessor_id: int) -> dict:
    """
    Set activity predecessor (validates no circular dependencies).

    :param activity_id: Activity ID. Example: 2
    :param predecessor_id: Predecessor activity ID. Example: 1
    :return: Updated activity dict
    """
    logger.info(
        f"HTTP Tool: set_predecessor activity={activity_id} predecessor={predecessor_id}"
    )
    r = get_client().put(
        f"/api/activities/{activity_id}/predecessor/",
        json={"predecessor_id": predecessor_id},
    )
    return check_response(r, "set_predecessor")


# ============================================================================
# WORKFLOW EXPORT / IMPORT TOOLS (4)
# ============================================================================


def _find_cursor_rules_dir(resolved_target: Path) -> Path | None:
    """
    Locate ``.cursor/rules`` from a Cursor playbook export target.

    :param resolved_target: Export target. Example: Path("/repo/.cursor/playbooks/Edda")
    :return: ``.cursor/rules`` path or None when the tree is not under ``.cursor``
    """
    for parent in (resolved_target, *resolved_target.parents):
        if parent.name == ".cursor":
            return parent / "rules"
        if parent.name == "playbooks" and parent.parent.name == ".cursor":
            return parent.parent / "rules"
    return None


def _cursor_rules_sync_report(
    cursor_rules_dir: Path | None, rule_paths: list[str]
) -> dict:
    """
    Compare exported rule files against active ``.cursor/rules`` copies.

    :param cursor_rules_dir: Active Cursor rules directory or None
    :param rule_paths: Absolute paths of exported playbook rule files
    :return: Sync status dict
    """
    if not rule_paths:
        return {
            "active_cursor_rules_dir": (
                str(cursor_rules_dir) if cursor_rules_dir else ""
            ),
            "active_cursor_rules_synchronized": None,
            "stale_or_missing_active_rules": [],
        }
    if cursor_rules_dir is None:
        return {
            "active_cursor_rules_dir": "",
            "active_cursor_rules_synchronized": False,
            "stale_or_missing_active_rules": [Path(path).name for path in rule_paths],
        }
    stale = []
    for path in rule_paths:
        src = Path(path)
        dest = cursor_rules_dir / src.name
        if not dest.exists() or dest.read_text(encoding="utf-8") != src.read_text(
            encoding="utf-8"
        ):
            stale.append(src.name)
    return {
        "active_cursor_rules_dir": str(cursor_rules_dir),
        "active_cursor_rules_synchronized": len(stale) == 0,
        "stale_or_missing_active_rules": stale,
    }


def _workflow_export_message(
    wf_dir: Path,
    rules_dir: Path | None,
    rule_paths: list[str],
    sync_report: dict,
) -> str:
    """Build the operator-facing export summary including rule destinations."""
    if not rule_paths:
        return (
            f"Workflow exported to {wf_dir}. No linked rules. "
            "Edit files locally and use import_workflow_from_local to apply changes."
        )
    names = ", ".join(Path(path).name for path in rule_paths)
    dest = rules_dir or Path(rule_paths[0]).parent
    active_dir = (
        sync_report.get("active_cursor_rules_dir") or "(not a Cursor playbook tree)"
    )
    if sync_report.get("active_cursor_rules_synchronized") is True:
        sync_text = f"Active Cursor rules at {active_dir} are synchronized."
    else:
        stale = ", ".join(sync_report.get("stale_or_missing_active_rules") or [])
        sync_text = (
            f"Active Cursor rules at {active_dir} are NOT synchronized"
            + (f" (stale or missing: {stale})" if stale else "")
            + ". Copy or re-export before execution."
        )
    return (
        f"Workflow exported to {wf_dir}. {len(rule_paths)} linked rules "
        f"({names}) were written to {dest}. {sync_text}"
    )


def export_workflow_to_local(
    workflow_id: int,
    target_directory: str = ".windsurf/workflows",
    folder_name: str = None,
) -> dict:
    """
    Export workflow to local AI workspace as markdown files.

    When running in Docker, set MIMIR_DEV_ROOT and bind-mount that folder in
    the MCP container config. Relative target_directory values resolve against
    MIMIR_DEV_ROOT.

    Linked rules are written to the sibling ``rules/`` folder. When the target
    is a Cursor playbook tree, missing files are also copied to ``.cursor/rules/``.
    Existing different copies are left untouched and reported as stale.

    :param workflow_id: Workflow ID. Example: 42
    :param target_directory: Target directory. Example: ".windsurf/workflows"
    :param folder_name: Folder name. Example: "FFE" (defaults to workflow slug)
    :return: Export result with file paths, rule paths, and Cursor sync status
    """
    return _run_local_export(
        entity_type="workflow",
        entity_id=workflow_id,
        route=f"/api/workflows/{workflow_id}/export/",
        target_directory=target_directory,
        payload={"folder_name": folder_name} if folder_name else {},
        planner=_preflight_workflow_export,
    )


def _workflow_export_result(
    data: dict,
    wf_dir: Path,
    rules_dir: Path | None,
    rule_export_paths: list[str],
    cursor_rules_dir: Path | None,
) -> dict:
    """Report the files and active Cursor rule status in the existing result shape."""
    sync_report = _cursor_rules_sync_report(cursor_rules_dir, rule_export_paths)
    return {
        "status": "exported",
        "workflow_id": data["workflow_id"],
        "workflow_name": data["workflow_name"],
        "export_path": str(wf_dir),
        "files_created": [f["filename"] for f in data["workflow_files"]],
        "rule_files_created": [Path(path).name for path in rule_export_paths],
        "rule_export_paths": rule_export_paths,
        "rules_export_path": str(rules_dir) if rules_dir else "",
        "active_cursor_rules_dir": sync_report["active_cursor_rules_dir"],
        "active_cursor_rules_synchronized": sync_report[
            "active_cursor_rules_synchronized"
        ],
        "stale_or_missing_active_rules": sync_report["stale_or_missing_active_rules"],
        "message": _workflow_export_message(
            wf_dir, rules_dir, rule_export_paths, sync_report
        ),
    }


def export_playbook_to_local(
    playbook_id: int,
    target_directory: str = ".cursor/playbooks",
    folder_name: str = None,
    additional_targets: list[str] | None = None,
    sync_root_rules: bool = False,
    ade_targets: list[str] | None = None,
    force_apply: bool = False,
    ade_target: str | None = None,
) -> dict:
    """
    Export full playbook tree and optional ADE apply-on rule copies for IDE agents.

    Writes the canonical playbook markdown tree under ``target_directory``. When
    ``sync_root_rules`` is true, also writes apply-on rule files to ADE load paths
    implied by ``ade_targets`` (for example ``.cursor/rules/`` for Cursor).

    :param playbook_id: Playbook ID. Example: 3 (Edda / FeatureFactory)
    :param target_directory: Canonical export root. Example: ".cursor/playbooks"
    :param folder_name: Playbook folder name under target. Example: "Edda"
    :param additional_targets: Extra roots that receive a copy of the canonical tree only.
        Example: [".windsurf/workflows"]
    :param sync_root_rules: When true, write apply-on copies to paths from ``ade_targets``.
        Requires a non-empty ``ade_targets`` list.
    :param ade_targets: ADE keys: cursor, devin, claude, copilot. At least one required
        when ``sync_root_rules`` or ``force_apply`` is true. Multiple allowed.
        Examples: ["cursor"], ["cursor", "devin"], ["claude"]
    :param force_apply: ADE copies use apply-on frontmatter even when DB ``always_apply``
        is false. Canonical tree under ``target_directory`` keeps stored flags.
    :param ade_target: Singular alias merged into ``ade_targets``. Example: "cursor"
    :return: Export summary with counts, ``files_created``, ``ade_rule_files``, and
        ``inline_rules_markdown`` (non-empty for claude/copilot targets)
    :raises ValueError: Playbook not accessible or ``ade_targets`` missing when required

    Example:
        export_playbook_to_local(
            playbook_id=3,
            target_directory=".cursor/playbooks",
            folder_name="Edda",
            ade_targets=["cursor", "devin"],
            sync_root_rules=True,
        )
    """
    payload: dict[str, object] = {
        "force_apply": force_apply,
        "sync_root_rules": sync_root_rules,
    }
    if folder_name:
        payload["folder_name"] = folder_name
    if ade_targets is not None:
        payload["ade_targets"] = ade_targets
    if ade_target:
        payload["ade_target"] = ade_target
    return _run_local_export(
        entity_type="playbook",
        entity_id=playbook_id,
        route=f"/api/playbooks/{playbook_id}/export-local/",
        target_directory=target_directory,
        payload=payload,
        planner=partial(
            _preflight_playbook_export,
            additional_targets=additional_targets,
            sync_root_rules=sync_root_rules,
            ade_targets=ade_targets,
            ade_target=ade_target,
        ),
    )


def _playbook_export_result(
    data: dict, roots: tuple[Path, ...], files_written: list[str]
) -> dict:
    """Report canonical file names, requested roots and existing bundle metadata."""
    counts = data.get("counts", {})
    inline_md = data.get("inline_rules_markdown") or ""
    return {
        "status": "exported",
        "playbook_id": data["playbook_id"],
        "playbook_name": data["playbook_name"],
        "export_paths": [str(root / data["folder_name"]) for root in roots],
        "workflows": counts.get("workflows", 0),
        "activities": counts.get("activities", 0),
        "rules": counts.get("rules", 0),
        "skills": counts.get("skills", 0),
        "agents": counts.get("agents", 0),
        "artifacts": counts.get("artifacts", 0),
        "files_created": files_written,
        "ade_rule_files": data.get("ade_rule_files") or [],
        "inline_rules_markdown": inline_md,
        "message": "Playbook exported successfully.",
    }


def import_workflow_from_local(
    workflow_id: int, source_directory: str, auto_apply: bool = False
) -> dict:
    """
    Import workflow from local markdown files with change detection.

    When running in Docker, set MIMIR_DEV_ROOT and bind-mount that folder.
    Import against a hosted FOB requires mimir-local or a local FOB URL.

    :param workflow_id: Workflow ID. Example: 42
    :param source_directory: Source directory. Example: ".windsurf/workflows/FFE"
    :param auto_apply: Auto-apply for draft playbooks. Example: False
    :return: Change detection result with protocol path
    """
    logger.info(f"HTTP Tool: import_workflow_from_local workflow={workflow_id}")
    ensure_import_supported_on_server(get_server_url(), purpose="import")
    resolved_source = ensure_readable_workspace_path(
        source_directory,
        purpose="import",
    )
    r = get_client().post(
        f"/api/workflows/{workflow_id}/import_workflow/",
        json={
            "source_directory": str(resolved_source),
            "auto_apply": auto_apply,
        },
    )
    return check_response(r, "import_workflow_from_local")


def apply_upload_protocol(protocol_file: str) -> dict:
    """
    Apply upload protocol to draft playbook.

    When running in Docker, set MIMIR_DEV_ROOT and bind-mount that folder.
    Protocol apply against a hosted FOB requires mimir-local or a local FOB URL.

    :param protocol_file: Path to _Upload_Protocol.md
    :return: Application result with change counts
    """
    logger.info(f"HTTP Tool: apply_upload_protocol protocol_file={protocol_file}")
    ensure_import_supported_on_server(get_server_url(), purpose="apply_upload_protocol")
    resolved_protocol = ensure_readable_workspace_path(
        protocol_file,
        purpose="apply_upload_protocol",
    )
    r = get_client().post(
        "/api/workflows/0/apply-protocol/",
        json={
            "protocol_file": str(resolved_protocol),
        },
    )
    return check_response(r, "apply_upload_protocol")


def create_pip_from_protocol(protocol_file: str, pip_title: str) -> dict:
    """
    Create PIP from upload protocol for released playbook.

    When running in Docker, set MIMIR_DEV_ROOT and bind-mount that folder.
    PIP creation against a hosted FOB requires mimir-local or a local FOB URL.

    :param protocol_file: Path to _Upload_Protocol.md
    :param pip_title: PIP title. Example: "Improve workflow"
    :return: Created PIP dict with ID and status
    """
    logger.info(f'HTTP Tool: create_pip_from_protocol title="{pip_title}"')
    ensure_import_supported_on_server(
        get_server_url(), purpose="create_pip_from_protocol"
    )
    resolved_protocol = ensure_readable_workspace_path(
        protocol_file,
        purpose="create_pip_from_protocol",
    )
    r = get_client().post(
        "/api/workflows/0/create-pip/",
        json={
            "protocol_file": str(resolved_protocol),
            "pip_title": pip_title,
        },
    )
    return check_response(r, "create_pip_from_protocol")


# ============================================================================
# SKILL TOOLS (7)
# ============================================================================


def create_skill(
    playbook_id: int,
    title: str,
    content: str = "",
    capability_domain: str = "",
    technology_stack: str = "",
) -> dict:
    """
    Create skill in draft playbook.

    :param playbook_id: Parent playbook ID. Example: 1
    :param title: Skill title (required). Example: "Build Login Form"
    :param content: Markdown content (optional)
    :param capability_domain: What capability (optional). Example: "GUI_FORM"
    :param technology_stack: Tech stack (optional). Example: "React+Redux"
    :return: Created skill dict
    """
    logger.info(f'HTTP Tool: create_skill title="{title}"')
    r = get_client().post(
        "/api/skills/",
        json={
            "playbook_id": playbook_id,
            "title": title,
            "content": content,
            "capability_domain": capability_domain,
            "technology_stack": technology_stack,
        },
    )
    return check_response(r, "create_skill")


def list_skills(
    playbook_id: int, domain: str = "", stack: str = "", search: str = ""
) -> list:
    """
    List skills for playbook with optional filters.

    :param playbook_id: Playbook ID. Example: 1
    :param domain: Filter by capability_domain. Example: "GUI_FORM"
    :param stack: Filter by technology_stack. Example: "React+Redux"
    :param search: Free-text search. Example: "login"
    :return: List of skill dicts
    """
    logger.info(f"HTTP Tool: list_skills playbook={playbook_id}")
    params = {"playbook_id": playbook_id}
    if domain:
        params["domain"] = domain
    if stack:
        params["stack"] = stack
    if search:
        params["search"] = search
    r = get_client().get("/api/skills/", params=params)
    data = check_response(r, "list_skills")
    return data.get("results", data) if isinstance(data, dict) else data


def get_skill(skill_id: int, event_identity: str | None = None) -> dict:
    """
    Get skill details with activity count.

    :param skill_id: Skill ID. Example: 1
    :param event_identity: Optional UUID to reuse when retrying this read.
    :return: Skill dict with activity_count
    :raises ValueError: Invalid identity or unavailable resource.
    """
    tool = "get_skill"
    identity = _resolve_consumption_event_identity(event_identity)
    try:
        response = get_client().get(f"/api/skills/{skill_id}/")
        payload = check_response(response, tool)
    except ValueError, PermissionError, RuntimeError, httpx.HTTPError:
        logger.info(_DETAIL_REJECT_LOG, tool, skill_id, identity)
        raise
    return _complete_mcp_detail(
        payload,
        tool_name=tool,
        entity_type="skill",
        entity_id=skill_id,
        event_identity=identity,
    )


def update_skill(
    skill_id: int,
    title: str = None,
    content: str = None,
    capability_domain: str = None,
    technology_stack: str = None,
) -> dict:
    """
    Update skill in draft playbook.

    :param skill_id: Skill ID. Example: 1
    :param title: New title (optional)
    :param content: New content (optional)
    :param capability_domain: New domain (optional)
    :param technology_stack: New stack (optional)
    :return: Updated skill dict
    """
    logger.info(f"HTTP Tool: update_skill id={skill_id}")
    payload = {
        k: v
        for k, v in {
            "title": title,
            "content": content,
            "capability_domain": capability_domain,
            "technology_stack": technology_stack,
        }.items()
        if v is not None
    }
    r = get_client().patch(f"/api/skills/{skill_id}/", json=payload)
    return check_response(r, "update_skill")


def delete_skill(skill_id: int) -> dict:
    """
    Delete skill in draft playbook.

    :param skill_id: Skill ID. Example: 1
    :return: Dict with deleted=True
    """
    logger.info(f"HTTP Tool: delete_skill id={skill_id}")
    r = get_client().delete(f"/api/skills/{skill_id}/")
    return check_response(r, "delete_skill")


def link_skill_to_activity(activity_id: int, skill_id: int) -> dict:
    """
    Link a skill to an activity.

    :param activity_id: Activity ID. Example: 1
    :param skill_id: Skill ID. Example: 5
    :return: Dict with updated activity_id and skill_id
    """
    logger.info(
        f"HTTP Tool: link_skill_to_activity activity={activity_id} skill={skill_id}"
    )
    r = get_client().put(
        f"/api/activities/{activity_id}/skill/", json={"skill_id": skill_id}
    )
    return check_response(r, "link_skill_to_activity")


def unlink_skill_from_activity(activity_id: int, skill_id: int) -> dict:
    """
    Unlink a specific skill from an activity.

    :param activity_id: Activity ID. Example: 1
    :param skill_id: Skill ID. Example: 5
    :return: Dict with updated activity_id and remaining skill_ids
    """
    logger.info(
        f"HTTP Tool: unlink_skill_from_activity activity={activity_id} skill={skill_id}"
    )
    r = get_client().delete(
        f"/api/activities/{activity_id}/skill/",
        json={"skill_id": skill_id},
    )
    return check_response(r, "unlink_skill_from_activity")


def set_activity_skills(activity_id: int, skill_ids: list) -> dict:
    """
    Replace all skills linked to an activity.

    :param activity_id: Activity ID. Example: 1
    :param skill_ids: List of skill IDs (empty clears all). Example: [5, 7]
    :return: Dict with activity_id and skill_ids
    """
    logger.info(
        f"HTTP Tool: set_activity_skills activity={activity_id} skill_ids={skill_ids}"
    )
    r = get_client().put(
        f"/api/activities/{activity_id}/skills/",
        json={"skill_ids": skill_ids},
    )
    return check_response(r, "set_activity_skills")


# ============================================================================
# RULE TOOLS (6)
# ============================================================================


def create_rule(
    playbook_id: int,
    title: str,
    content: str = "",
    slug: str = "",
    always_apply: bool = True,
) -> dict:
    """
    Create playbook rule (.mdc export).

    :param playbook_id: Parent playbook ID. Example: 1
    :param title: Rule title (required)
    :param content: Rule content (optional)
    :param slug: Rule slug (optional)
    :param always_apply: Whether to always apply. Example: True
    :return: Created rule dict
    """
    logger.info(f'HTTP Tool: create_rule title="{title}"')
    r = get_client().post(
        "/api/rules/",
        json={
            "playbook_id": playbook_id,
            "title": title,
            "content": content,
            "slug": slug,
            "always_apply": always_apply,
        },
    )
    return check_response(r, "create_rule")


def list_rules(playbook_id: int, search: str = "", unlinked_only: bool = False) -> list:
    """
    List rules for playbook.

    :param playbook_id: Playbook ID. Example: 1
    :param search: Free-text search. Example: "reviewer"
    :param unlinked_only: Only return unlinked rules. Example: False
    :return: List of rule dicts
    """
    logger.info(f"HTTP Tool: list_rules playbook={playbook_id}")
    params = {"playbook_id": playbook_id}
    if search:
        params["search"] = search
    if unlinked_only:
        params["unlinked_only"] = "true"
    r = get_client().get("/api/rules/", params=params)
    data = check_response(r, "list_rules")
    return data.get("results", data) if isinstance(data, dict) else data


def get_rule(rule_id: int, event_identity: str | None = None) -> dict:
    """
    Get rule by ID.

    :param rule_id: Rule ID. Example: 1
    :param event_identity: Optional UUID to reuse when retrying this read.
    :return: Rule dict
    :raises ValueError: Invalid identity or unavailable resource.
    """
    tool = "get_rule"
    identity = _resolve_consumption_event_identity(event_identity)
    try:
        response = get_client().get(f"/api/rules/{rule_id}/")
        payload = check_response(response, tool)
    except ValueError, PermissionError, RuntimeError, httpx.HTTPError:
        logger.info(_DETAIL_REJECT_LOG, tool, rule_id, identity)
        raise
    return _complete_mcp_detail(
        payload,
        tool_name=tool,
        entity_type="rule",
        entity_id=rule_id,
        event_identity=identity,
    )


def update_rule(
    rule_id: int,
    title: str = None,
    content: str = None,
    slug: str = None,
    always_apply: bool = None,
) -> dict:
    """
    Update rule in draft playbook.

    :param rule_id: Rule ID. Example: 1
    :param title: New title (optional)
    :param content: New content (optional)
    :param slug: New slug (optional)
    :param always_apply: New always_apply (optional)
    :return: Updated rule dict
    """
    logger.info(f"HTTP Tool: update_rule id={rule_id}")
    payload = {
        k: v
        for k, v in {
            "title": title,
            "content": content,
            "slug": slug,
            "always_apply": always_apply,
        }.items()
        if v is not None
    }
    r = get_client().patch(f"/api/rules/{rule_id}/", json=payload)
    return check_response(r, "update_rule")


def delete_rule(rule_id: int) -> dict:
    """
    Delete rule from draft playbook.

    :param rule_id: Rule ID. Example: 1
    :return: Dict with deleted=True
    """
    logger.info(f"HTTP Tool: delete_rule id={rule_id}")
    r = get_client().delete(f"/api/rules/{rule_id}/")
    return check_response(r, "delete_rule")


def set_activity_rules(activity_id: int, rule_ids: list) -> dict:
    """
    Replace activity's linked rules (same playbook only).

    :param activity_id: Activity ID. Example: 1
    :param rule_ids: List of rule IDs. Example: [1, 2, 3]
    :return: Dict with activity_id and rule_ids
    """
    logger.info(
        f"HTTP Tool: set_activity_rules activity={activity_id} rules={rule_ids}"
    )
    r = get_client().put(
        f"/api/activities/{activity_id}/rules/", json={"rule_ids": rule_ids}
    )
    return check_response(r, "set_activity_rules")


# ============================================================================
# AGENT TOOLS (7)
# ============================================================================


def create_agent(playbook_id: int, name: str, description: str = "") -> dict:
    """
    Create agent in draft playbook.

    :param playbook_id: Parent playbook ID. Example: 1
    :param name: Agent name (required, unique per playbook). Example: "Code Reviewer"
    :param description: Description (optional)
    :return: Created agent dict
    """
    logger.info(f'HTTP Tool: create_agent name="{name}"')
    r = get_client().post(
        "/api/agents/",
        json={"playbook_id": playbook_id, "name": name, "description": description},
    )
    return check_response(r, "create_agent")


def list_agents(playbook_id: int, search: str = "") -> list:
    """
    List agents for playbook with optional search.

    :param playbook_id: Playbook ID. Example: 1
    :param search: Free-text search. Example: "reviewer"
    :return: List of agent dicts
    """
    logger.info(f"HTTP Tool: list_agents playbook={playbook_id}")
    params = {"playbook_id": playbook_id}
    if search:
        params["search"] = search
    r = get_client().get("/api/agents/", params=params)
    data = check_response(r, "list_agents")
    return data.get("results", data) if isinstance(data, dict) else data


def get_agent(agent_id: int, event_identity: str | None = None) -> dict:
    """
    Get agent details with activity count.

    :param agent_id: Agent ID. Example: 1
    :param event_identity: Optional UUID to reuse when retrying this read.
    :return: Agent dict with activity_count
    :raises ValueError: Invalid identity or unavailable resource.
    """
    tool = "get_agent"
    identity = _resolve_consumption_event_identity(event_identity)
    try:
        response = get_client().get(f"/api/agents/{agent_id}/")
        payload = check_response(response, tool)
    except ValueError, PermissionError, RuntimeError, httpx.HTTPError:
        logger.info(_DETAIL_REJECT_LOG, tool, agent_id, identity)
        raise
    return _complete_mcp_detail(
        payload,
        tool_name=tool,
        entity_type="agent",
        entity_id=agent_id,
        event_identity=identity,
    )


def update_agent(agent_id: int, name: str = None, description: str = None) -> dict:
    """
    Update agent in draft playbook.

    :param agent_id: Agent ID. Example: 1
    :param name: New name (optional)
    :param description: New description (optional)
    :return: Updated agent dict
    """
    logger.info(f"HTTP Tool: update_agent id={agent_id}")
    payload = {
        k: v
        for k, v in {"name": name, "description": description}.items()
        if v is not None
    }
    r = get_client().patch(f"/api/agents/{agent_id}/", json=payload)
    return check_response(r, "update_agent")


def delete_agent(agent_id: int) -> dict:
    """
    Delete agent in draft playbook.

    :param agent_id: Agent ID. Example: 1
    :return: Dict with deleted=True
    """
    logger.info(f"HTTP Tool: delete_agent id={agent_id}")
    r = get_client().delete(f"/api/agents/{agent_id}/")
    return check_response(r, "delete_agent")


def link_agent_to_activity(activity_id: int, agent_id: int) -> dict:
    """
    Link an agent to an activity.

    :param activity_id: Activity ID. Example: 1
    :param agent_id: Agent ID. Example: 3
    :return: Dict with updated activity_id and agent_id
    """
    logger.info(
        f"HTTP Tool: link_agent_to_activity activity={activity_id} agent={agent_id}"
    )
    r = get_client().put(
        f"/api/activities/{activity_id}/agent/", json={"agent_id": agent_id}
    )
    return check_response(r, "link_agent_to_activity")


def unlink_agent_from_activity(activity_id: int) -> dict:
    """
    Unlink agent from an activity (set FK to NULL).

    :param activity_id: Activity ID. Example: 1
    :return: Dict with updated activity_id and agent_id=None
    """
    logger.info(f"HTTP Tool: unlink_agent_from_activity activity={activity_id}")
    r = get_client().delete(f"/api/activities/{activity_id}/agent/")
    return check_response(r, "unlink_agent_from_activity")


# ============================================================================
# ARTIFACT TOOLS (7)
# ============================================================================


def create_artifact(
    playbook_id: int,
    produced_by_id: int,
    name: str,
    description: str = "",
    type: str = "Document",
    is_required: bool = False,
) -> dict:
    """
    Create artifact in draft playbook.

    :param playbook_id: Parent playbook ID. Example: 1
    :param produced_by_id: Activity ID that produces this artifact. Example: 5
    :param name: Artifact name (required). Example: "API Specification"
    :param description: Description (optional)
    :param type: Artifact type. Example: "Document"
    :param is_required: Whether required. Example: True
    :return: Created artifact dict
    """
    logger.info(f'HTTP Tool: create_artifact name="{name}"')
    r = get_client().post(
        "/api/artifacts/",
        json={
            "playbook_id": playbook_id,
            "produced_by_id": produced_by_id,
            "name": name,
            "description": description,
            "type": type,
            "is_required": is_required,
        },
    )
    return check_response(r, "create_artifact")


def list_artifacts(
    playbook_id: int, search: str = "", type_filter: str = "", required_filter: str = ""
) -> list:
    """
    List artifacts for playbook with optional filters.

    :param playbook_id: Playbook ID. Example: 1
    :param search: Free-text search in name/description. Example: "API"
    :param type_filter: Filter by type. Example: "Document"
    :param required_filter: Filter by required ("true"/"false"). Example: "true"
    :return: List of artifact dicts
    """
    logger.info(f"HTTP Tool: list_artifacts playbook={playbook_id}")
    params = {"playbook_id": playbook_id}
    if search:
        params["search"] = search
    if type_filter:
        params["type"] = type_filter
    if required_filter:
        params["is_required"] = required_filter
    r = get_client().get("/api/artifacts/", params=params)
    data = check_response(r, "list_artifacts")
    return data.get("results", data) if isinstance(data, dict) else data


def get_artifact(artifact_id: int, event_identity: str | None = None) -> dict:
    """
    Get artifact details with consumer count.

    :param artifact_id: Artifact ID. Example: 1
    :param event_identity: Optional UUID to reuse when retrying this read.
    :return: Artifact dict with consumer_count
    :raises ValueError: Invalid identity or unavailable resource.
    """
    tool = "get_artifact"
    identity = _resolve_consumption_event_identity(event_identity)
    try:
        response = get_client().get(f"/api/artifacts/{artifact_id}/")
        payload = check_response(response, tool)
    except ValueError, PermissionError, RuntimeError, httpx.HTTPError:
        logger.info(_DETAIL_REJECT_LOG, tool, artifact_id, identity)
        raise
    return _complete_mcp_detail(
        payload,
        tool_name=tool,
        entity_type="artifact",
        entity_id=artifact_id,
        event_identity=identity,
    )


def update_artifact(
    artifact_id: int,
    name: str = None,
    description: str = None,
    type: str = None,
    is_required: bool = None,
) -> dict:
    """
    Update artifact in DRAFT playbook.

    :param artifact_id: Artifact ID. Example: 1
    :param name: New name or None
    :param description: New description or None
    :param type: New type or None
    :param is_required: New required flag or None
    :return: Updated artifact dict
    """
    logger.info(f"HTTP Tool: update_artifact id={artifact_id}")
    payload = {
        k: v
        for k, v in {
            "name": name,
            "description": description,
            "type": type,
            "is_required": is_required,
        }.items()
        if v is not None
    }
    r = get_client().patch(f"/api/artifacts/{artifact_id}/", json=payload)
    return check_response(r, "update_artifact")


def delete_artifact(artifact_id: int) -> dict:
    """
    Delete artifact in DRAFT playbook.

    :param artifact_id: Artifact ID. Example: 1
    :return: Confirmation dict with deleted=True
    """
    logger.info(f"HTTP Tool: delete_artifact id={artifact_id}")
    r = get_client().delete(f"/api/artifacts/{artifact_id}/")
    return check_response(r, "delete_artifact")


def link_artifact_to_activity(
    artifact_id: int, activity_id: int, is_required: bool = True
) -> dict:
    """
    Link artifact as input to a consumer activity.

    :param artifact_id: Artifact ID. Example: 1
    :param activity_id: Consumer activity ID. Example: 5
    :param is_required: Whether input is required. Example: True
    :return: Dict with id, artifact_id, activity_id, is_required
    """
    logger.info(
        f"HTTP Tool: link_artifact_to_activity artifact={artifact_id} activity={activity_id}"
    )
    r = get_client().post(
        f"/api/artifacts/{artifact_id}/consumers/",
        json={"activity_id": activity_id, "is_required": is_required},
    )
    return check_response(r, "link_artifact_to_activity")


def unlink_artifact_from_activity(artifact_input_id: int) -> dict:
    """
    Remove artifact input relationship.

    :param artifact_input_id: ArtifactInput ID. Example: 1
    :return: Dict with deleted=True
    """
    logger.info(f"HTTP Tool: unlink_artifact_from_activity input={artifact_input_id}")
    r = get_client().delete(f"/api/artifact-inputs/{artifact_input_id}/")
    return check_response(r, "unlink_artifact_from_activity")


# ============================================================================
# PHASE TOOLS (6)
# ============================================================================


def create_phase(
    playbook_id: int, name: str, description: str = "", order: int = None
) -> dict:
    """
    Create phase in draft playbook.

    :param playbook_id: Parent playbook ID. Example: 1
    :param name: Phase name (required, unique per playbook). Example: "Planning"
    :param description: Description (optional)
    :param order: Display order (optional)
    :return: Created phase dict
    """
    logger.info(f'HTTP Tool: create_phase name="{name}"')
    payload = {"playbook_id": playbook_id, "name": name, "description": description}
    if order is not None:
        payload["order"] = order
    r = get_client().post("/api/phases/", json=payload)
    return check_response(r, "create_phase")


def list_phases(playbook_id: int) -> list:
    """
    List all phases for a playbook.

    :param playbook_id: Playbook ID. Example: 1
    :return: List of phase dicts with activity counts
    """
    logger.info(f"HTTP Tool: list_phases playbook={playbook_id}")
    r = get_client().get("/api/phases/", params={"playbook_id": playbook_id})
    data = check_response(r, "list_phases")
    return data.get("results", data) if isinstance(data, dict) else data


def get_phase(phase_id: int, event_identity: str | None = None) -> dict:
    """
    Get phase details with activities.

    :param phase_id: Phase ID. Example: 1
    :param event_identity: Optional UUID to reuse when retrying this read.
    :return: Phase dict with activities list
    :raises ValueError: Invalid identity or unavailable resource.
    """
    tool = "get_phase"
    identity = _resolve_consumption_event_identity(event_identity)
    try:
        response = get_client().get(f"/api/phases/{phase_id}/")
        payload = check_response(response, tool)
    except ValueError, PermissionError, RuntimeError, httpx.HTTPError:
        logger.info(_DETAIL_REJECT_LOG, tool, phase_id, identity)
        raise
    return _complete_mcp_detail(
        payload,
        tool_name=tool,
        entity_type="phase",
        entity_id=phase_id,
        event_identity=identity,
    )


def update_phase(
    phase_id: int, name: str = None, description: str = None, order: int = None
) -> dict:
    """
    Update phase in draft playbook.

    :param phase_id: Phase ID. Example: 1
    :param name: New name (optional)
    :param description: New description (optional)
    :param order: New order (optional)
    :return: Updated phase dict
    """
    logger.info(f"HTTP Tool: update_phase id={phase_id}")
    payload = {
        k: v
        for k, v in {"name": name, "description": description, "order": order}.items()
        if v is not None
    }
    r = get_client().patch(f"/api/phases/{phase_id}/", json=payload)
    return check_response(r, "update_phase")


def delete_phase(phase_id: int) -> dict:
    """
    Delete phase in draft playbook.

    :param phase_id: Phase ID. Example: 1
    :return: Dict with deleted=True
    """
    logger.info(f"HTTP Tool: delete_phase id={phase_id}")
    r = get_client().delete(f"/api/phases/{phase_id}/")
    return check_response(r, "delete_phase")


def reorder_phases(playbook_id: int, phase_order: list) -> dict:
    """
    Reorder phases in draft playbook.

    :param playbook_id: Playbook ID. Example: 1
    :param phase_order: List of phase IDs in desired order. Example: [3, 1, 2]
    :return: Dict with reordered=True and count
    """
    logger.info(f"HTTP Tool: reorder_phases playbook={playbook_id}")
    r = get_client().put(
        f"/api/playbooks/{playbook_id}/phases/reorder/",
        json={"phase_order": phase_order},
    )
    return check_response(r, "reorder_phases")


# ============================================================================
# PROCESS IMPROVEMENT PROPOSALS (PIP) — Act 9  (8 tools)
# ============================================================================


def list_pips(
    scope: str = "mine",
    status_codes: Optional[str] = None,
    playbook_id: Optional[int] = None,
) -> list:
    """
    List PIPs for the current user (staff may use scope=all).

    :param scope: "mine" (default) or "all" (staff only)
    :param status_codes: Comma-separated statuses to filter, e.g. "draft,reviewed"
    :param playbook_id: Optional playbook ID filter. Example: 1
    :return: List of PIP summary dicts
    """
    logger.info(f"HTTP Tool: list_pips scope={scope} status_codes={status_codes}")
    params: dict = {"scope": scope}
    if status_codes:
        params["status_codes"] = status_codes
    if playbook_id is not None:
        params["playbook_id"] = playbook_id
    r = get_client().get("/api/pips/", params=params)
    data = check_response(r, "list_pips")
    return data.get("results", data) if isinstance(data, dict) else data


def get_pip(pip_id: int, event_identity: str | None = None) -> dict:
    """
    Get a single PIP with nested change rows.

    :param pip_id: PIP ID. Example: 1
    :param event_identity: Optional UUID to reuse when retrying this read.
    :return: PIP dict with nested changes list
    :raises ValueError: Invalid identity or unavailable resource.
    """
    tool = "get_pip"
    identity = _resolve_consumption_event_identity(event_identity)
    try:
        response = get_client().get(f"/api/pips/{pip_id}/")
        payload = check_response(response, tool)
    except ValueError, PermissionError, RuntimeError, httpx.HTTPError:
        logger.info(_DETAIL_REJECT_LOG, tool, pip_id, identity)
        raise
    return _complete_mcp_detail(
        payload,
        tool_name=tool,
        entity_type="pip",
        entity_id=pip_id,
        event_identity=identity,
    )


def create_pip(playbook_id: int, title: str, summary: str = "") -> dict:
    """
    Create a Draft PIP targeting a Released playbook.

    :param playbook_id: Released playbook ID. Example: 1
    :param title: PIP title (required). Example: "Add caching activity"
    :param summary: Optional summary text
    :return: Created PIP dict
    """
    logger.info(f'HTTP Tool: create_pip playbook={playbook_id} title="{title}"')
    r = get_client().post(
        "/api/pips/",
        json={"playbook_id": playbook_id, "title": title, "summary": summary},
    )
    return check_response(r, "create_pip")


def add_pip_change(
    pip_id: int,
    change_type: str,
    entity_type: str = "",
    name: str = "",
    content: str = "",
    target_id: Optional[int] = None,
    parent_workflow_id: Optional[int] = None,
    parent_workflow_ref: str = "",
    insert_after_activity_id: Optional[int] = None,
    insert_after_activity_ref: str = "",
    phase_ref: str = "",
    produced_by_activity_ref: str = "",
    artifact_type: str = "",
    artifact_is_required: bool = False,
    append_to_playbook_end: bool = False,
    internal_ref: str = "",
    relationship_type: str = "",
    source_entity_ref: str = "",
    target_entity_ref: str = "",
    display_order: Optional[int] = None,
) -> dict:
    """
    Add a typed change row to a Draft PIP.

    change_type values and required fields:
    - ADD   : entity_type + name + content required.
              ADD Activity: parent_workflow_id OR parent_workflow_ref (pk or #slug).
              ADD Artifact: produced_by_activity_ref required.
              Optionally set internal_ref="#slug" for later LINK/ref rows in this PIP.
              Never embed internal_ref slugs (#slug) in ADD/ALTER guidance content — use
              entity display names; slugs are PIP-only plumbing for ref fields.
    - ALTER : entity_type + target_id + at least one of name/content/display_order required.
              Activity/Workflow: display_order moves to a 1-based container position; beyond end appends.
              Activity: optional phase_ref (pk or #slug).
    - DROP  : entity_type + target_id + rationale in content.
    - LINK  : relationship_type + source_entity_ref + target_entity_ref (entity_type="").
    - UNLINK: same as LINK.

    entity_type (ADD/ALTER/DROP): Workflow, Activity, Phase, Skill, Agent, Rule, Artifact.

    relationship_type (LINK/UNLINK): skill_activity, rule_activity, agent_activity,
    activity_workflow, artifact_activity.

    Full subtree recipe (call add_pip_change in order):
      1. ADD Phase       internal_ref="#phase1"  name="Construction"
      2. ADD Workflow    internal_ref="#wf1"     name="Performance"
      3. ADD Activity    internal_ref="#act1"    parent_workflow_ref="#wf1"  phase_ref="#phase1"
      4. ADD Activity    name="Step 2"           parent_workflow_ref="#wf1"  insert_after_activity_ref="#act1"
      5. ADD Skill       internal_ref="#sk1"     ...
      6. LINK            relationship_type="skill_activity"  source_entity_ref="#sk1"  target_entity_ref="#act1"

    :param pip_id: PIP ID. Example: 1
    :param change_type: ADD, ALTER, DROP, LINK, or UNLINK
    :param entity_type: Required for ADD/ALTER/DROP. Choices: Workflow, Activity, Phase, Skill,
                        Agent, Rule, Artifact. Leave empty ("") for LINK/UNLINK.
    :param name: Entity name — required for ADD, optional override for ALTER.
    :param content: Markdown body — required for ADD, optional for ALTER.
    :param target_id: DB primary key of the entity to ALTER or DROP.
    :param parent_workflow_id: Live workflow PK for ADD Activity (mutually exclusive with ref).
    :param parent_workflow_ref: Pending or live workflow ref for ADD Activity. Example: "#wf1"
    :param insert_after_activity_id: Live activity PK to insert after.
    :param insert_after_activity_ref: Pending or live activity ref. Example: "#act1"
    :param phase_ref: Phase pk or #slug for ADD/ALTER Activity.
    :param produced_by_activity_ref: Required for ADD Artifact. Example: "#act1"
    :param artifact_type: Artifact type string for ADD/ALTER Artifact.
    :param artifact_is_required: Whether artifact is required (ADD/ALTER Artifact).
    :param append_to_playbook_end: Append Activity at playbook end regardless of workflow.
    :param internal_ref: "#slug" label for ADD rows. Example: "#new-skill"
    :param relationship_type: Required for LINK/UNLINK.
    :param source_entity_ref: Source entity — numeric PK or "#internal_ref".
    :param target_entity_ref: Target entity — numeric PK or "#internal_ref".
    :param display_order: ALTER Activity/Workflow position, 1..32767; beyond end appends.
    :return: Dict with change_id
    """
    logger.info(
        f"HTTP Tool: add_pip_change pip={pip_id} type={change_type} entity={entity_type}"
    )
    payload: dict = {
        "change_type": change_type,
        "entity_type": entity_type,
        "name": name,
        "content": content,
        "append_to_playbook_end": append_to_playbook_end,
        "artifact_is_required": artifact_is_required,
    }
    if target_id is not None:
        payload["target_id"] = target_id
    if parent_workflow_id is not None:
        payload["parent_workflow_id"] = parent_workflow_id
    if parent_workflow_ref:
        payload["parent_workflow_ref"] = parent_workflow_ref
    if insert_after_activity_id is not None:
        payload["insert_after_activity_id"] = insert_after_activity_id
    if insert_after_activity_ref:
        payload["insert_after_activity_ref"] = insert_after_activity_ref
    if phase_ref:
        payload["phase_ref"] = phase_ref
    if produced_by_activity_ref:
        payload["produced_by_activity_ref"] = produced_by_activity_ref
    if artifact_type:
        payload["artifact_type"] = artifact_type
    if internal_ref:
        payload["internal_ref"] = internal_ref
    if relationship_type:
        payload["relationship_type"] = relationship_type
    if source_entity_ref:
        payload["source_entity_ref"] = source_entity_ref
    if target_entity_ref:
        payload["target_entity_ref"] = target_entity_ref
    if display_order is not None:
        payload["display_order"] = display_order
    r = get_client().post(f"/api/pips/{pip_id}/changes/", json=payload)
    return check_response(r, "add_pip_change")


def remove_pip_change(pip_id: int, change_id: int) -> dict:
    """
    Remove a change row from a Draft PIP.

    :param pip_id: PIP ID. Example: 1
    :param change_id: Change ID to remove. Example: 5
    :return: Dict with removed=True and change_id
    """
    logger.info(f"HTTP Tool: remove_pip_change pip={pip_id} change={change_id}")
    r = get_client().delete(f"/api/pips/{pip_id}/changes/{change_id}/")
    return check_response(r, "remove_pip_change")


def submit_pip(pip_id: int) -> dict:
    """
    Submit a Draft PIP for Galdr evaluation.

    :param pip_id: PIP ID. Example: 1
    :return: Updated PIP dict with new status
    """
    logger.info(f"HTTP Tool: submit_pip id={pip_id}")
    r = get_client().post(f"/api/pips/{pip_id}/submit/")
    return check_response(r, "submit_pip")


def cancel_pip(pip_id: int) -> dict:
    """
    Withdraw a PIP owned by the current user (terminal ``withdrawn`` status).

    Allowed from: draft, submitted, processing_galdr, reviewed.
    Use to abandon a PIP. To fix Galdr feedback and resubmit the same pip_id,
    use ``revert_pip_to_draft`` instead.

    :param pip_id: PIP ID. Example: 1
    :return: Dict with cancelled=True and pip_id
    """
    logger.info(f"HTTP Tool: cancel_pip id={pip_id}")
    r = get_client().post(f"/api/pips/{pip_id}/cancel/")
    return check_response(r, "cancel_pip")


def revert_pip_to_draft(pip_id: int) -> dict:
    """
    Revert a PIP to draft for editing and resubmission (clears Galdr fields).

    Allowed from: submitted, processing_galdr, reviewed.
    After Galdr REJECT: get_pip → revert_pip_to_draft → edit changes → submit_pip
    on the same pip_id. Use cancel_pip only to abandon.

    :param pip_id: PIP ID. Example: 1
    :return: Dict with reverted=True and pip_id
    """
    logger.info(f"HTTP Tool: revert_pip_to_draft id={pip_id}")
    r = get_client().post(f"/api/pips/{pip_id}/revert-to-draft/")
    return check_response(r, "revert_pip_to_draft")


def preview_pip_diff(pip_id: int) -> dict:
    """
    Return human-readable preview rows for diff-style inspection.

    :param pip_id: PIP ID. Example: 1
    :return: Dict with pip_id and rows list (section, change_type, snippet)
    """
    logger.info(f"HTTP Tool: preview_pip_diff id={pip_id}")
    r = get_client().get(f"/api/pips/{pip_id}/preview/")
    return check_response(r, "preview_pip_diff")


def report_bug(
    description: str,
    page_context: str = "",
    reporter_email: str = "",
) -> dict:
    """
    File a GitHub Issue with structured context (same as UI feedback; requires auth token).

    :param description: What went wrong or what to improve
    :param page_context: Optional assistant/session context
    :param reporter_email: Optional email override; defaults to token user
    :return: Dict with issue_url and issue_number
    """
    logger.info(
        "HTTP Tool: report_bug desc_len=%s has_context=%s",
        len(description or ""),
        bool((page_context or "").strip()),
    )
    payload: dict = {
        "description": description,
        "page_context": page_context,
    }
    if (reporter_email or "").strip():
        payload["reporter_email"] = reporter_email.strip()
    r = get_client().post("/api/feedback/report/", json=payload)
    return check_response(r, "report_bug")


# ============================================================================
# TEAM TOOLS (7)
# ============================================================================


def list_teams() -> list:
    """
    List all teams visible to the current user.

    :return: List of team dicts
    """
    logger.info("HTTP Tool: list_teams")
    r = get_client().get("/api/teams/")
    data = check_response(r, "list_teams")
    return data.get("results", data) if isinstance(data, dict) else data


def get_team(team_id: int) -> dict:
    """
    Get detailed information about a specific team.

    :param team_id: Team primary key. Example: 42
    :return: Team dict with members and playbooks
    :raises ValueError: if team not found or not visible to user
    """
    logger.info(f"HTTP Tool: get_team team_id={team_id}")
    r = get_client().get(f"/api/teams/{team_id}/")
    return check_response(r, "get_team")


def create_team(
    name: str,
    description: str = "",
    visibility: Literal["Public", "Hidden"] = "Public",
    join_policy: Literal[
        "Auto-approve", "Requires Approval", "Invite Only"
    ] = "Auto-approve",
    category: Literal[
        "Engineering", "Design", "Research", "Product", "Private", "Other"
    ] = "Engineering",
) -> dict:
    """
    Create a new team. Caller becomes admin and first member.

    :param name: Team name (unique). Example: "Platform Engineering"
    :param description: Optional description. Example: "Core platform team"
    :param visibility: "Public" or "Hidden". Default "Public"
    :param join_policy: Join policy. Default "Auto-approve"
    :param category: Team category. Default "Engineering"
    :return: Created team dict with id, name, visibility, join_policy, category, admin_id, member_count
    :raises ValueError: if name is empty or already taken
    """
    logger.info(f'HTTP Tool: create_team name="{name}"')
    r = get_client().post(
        "/api/teams/",
        json={
            "name": name,
            "description": description,
            "visibility": visibility,
            "join_policy": join_policy,
            "category": category,
        },
    )
    return check_response(r, "create_team")


def move_playbook_to_team(playbook_id: int, team_id: int) -> dict:
    """
    Add a playbook to a team (requires team admin).

    :param playbook_id: Playbook primary key. Example: 12
    :param team_id: Team primary key. Example: 42
    :return: Dict with success=True, team_id, playbook_id, playbook_name
    :raises ValueError: if team or playbook not found
    :raises PermissionError: if user is not team admin
    """
    logger.info(
        f"HTTP Tool: move_playbook_to_team playbook_id={playbook_id} team_id={team_id}"
    )
    r = get_client().post(
        f"/api/teams/{team_id}/move_playbook_to_team/",
        json={
            "playbook_id": playbook_id,
        },
    )
    return check_response(r, "move_playbook_to_team")


def move_playbook_from_team(playbook_id: int, team_id: int) -> dict:
    """
    Remove a playbook from a team (requires team admin).

    :param playbook_id: Playbook primary key. Example: 12
    :param team_id: Team primary key. Example: 42
    :return: Dict with success=True, team_id, playbook_id
    :raises ValueError: if team or playbook not found
    :raises PermissionError: if user is not team admin
    """
    logger.info(
        f"HTTP Tool: move_playbook_from_team playbook_id={playbook_id} team_id={team_id}"
    )
    r = get_client().post(
        f"/api/teams/{team_id}/move_playbook_from_team/",
        json={
            "playbook_id": playbook_id,
        },
    )
    return check_response(r, "move_playbook_from_team")


def invite_to_team(team_id: int, emails: list[str], welcome_text: str = "") -> dict:
    """
    Invite users to join a team (requires team admin).

    :param team_id: Team primary key. Example: 42
    :param emails: List of email addresses to invite. Example: ["user@example.com"]
    :param welcome_text: Optional custom welcome message. Example: "Join our platform team!"
    :return: Dict with success=True, team_id, invited_count, results
    :raises ValueError: if team not found or emails list empty
    :raises PermissionError: if user is not team admin
    """
    logger.info(f"HTTP Tool: invite_to_team team_id={team_id} emails={emails}")
    r = get_client().post(
        f"/api/teams/{team_id}/invite/",
        json={
            "emails": emails,
            "welcome_text": welcome_text,
        },
    )
    return check_response(r, "invite_to_team")


def manage_team_invite(
    team_id: int, request_id: int, action: Literal["approve", "reject"]
) -> dict:
    """
    Approve or reject a join request (requires team admin).

    :param team_id: Team primary key. Example: 42
    :param request_id: JoinRequest primary key. Example: 123
    :param action: "approve" or "reject". Example: "approve"
    :return: Dict with success=True, team_id, request_id, action, user_email
    :raises ValueError: if team or request not found, or invalid action
    :raises PermissionError: if user is not team admin
    """
    logger.info(
        f"HTTP Tool: manage_team_invite team_id={team_id} request_id={request_id} action={action}"
    )
    r = get_client().post(
        f"/api/teams/{team_id}/manage_invite/",
        json={
            "request_id": request_id,
            "action": action,
        },
    )
    return check_response(r, "manage_team_invite")


def _resolve_consumption_event_identity(value: str | None) -> UUID:
    """Validate a supplied UUID or allocate one for an intentional invocation.

    :param value: Optional caller retry identity. Example: None.
    :return: Stable invocation UUID. Example: UUID(int=1).
    :raises ValueError: Malformed supplied identity.
    """
    if value is None:
        return uuid4()
    try:
        return UUID(value)
    except ValueError, AttributeError, TypeError:
        logger.info(
            "_resolve_consumption_event_identity | branch | reason=invalid_event_identity"
        )
        raise ValueError("event_identity must be a UUID.") from None


def _complete_mcp_detail(
    payload: dict,
    *,
    tool_name: str,
    entity_type: str,
    entity_id: int,
    event_identity: UUID,
) -> dict:
    """Record consumption only after authorized retrieval and serialization.

    :param payload: Decoded actual content. Example: {"id": 6203}.
    :param tool_name: Existing registered tool. Example: "get_activity".
    :param entity_type: Supported kind. Example: "activity".
    :param entity_id: Actual entity ID. Example: 6203.
    :param event_identity: Invocation UUID. Example: UUID(int=1).
    :return: Original unchanged payload. Example: {"id": 6203}.
    :raises RuntimeError: Receipt outcome cannot be confirmed.
    :raises PermissionError: Receipt revalidation denies access.
    """
    if not isinstance(payload, dict) or not (
        payload.get("id") == entity_id
        or (entity_type == "playbook" and "snapshot_data" in payload)
    ):
        logger.info(_DETAIL_REJECT_LOG, tool_name, entity_id, event_identity)
        raise ValueError("The authorized detail response is invalid.")
    logger.info(
        "_complete_mcp_detail | entry | tool=%s entity_type=%s entity_id=%s event_identity=%s channel=%s",
        tool_name,
        entity_type,
        entity_id,
        event_identity,
        _MCP_DETAIL_CHANNEL,
    )
    _post_consumption_receipt(
        entity_type=entity_type,
        entity_id=entity_id,
        event_identity=event_identity,
        channel=_MCP_DETAIL_CHANNEL,
    )
    return payload


def _post_consumption_receipt(
    *,
    entity_type: str,
    entity_id: int,
    event_identity: UUID,
    channel: Literal["mcp_detail", "export"],
) -> dict[str, object]:
    """Forward one explicit receipt; reused by S42 after completed local writes.

    :param entity_type: Supported kind. Example: "workflow".
    :param entity_id: Actual entity ID. Example: 6202.
    :param event_identity: UUID retained across retries. Example: UUID(int=1).
    :param channel: Trusted operation channel. Example: "export".
    :return: Safe Django result. Example: {"status": "replayed", "created_count": 0}.
    :raises ValueError: Invalid reference, identity, channel or response.
    :raises PermissionError: Current target access is denied.
    :raises RuntimeError: Transport outcome remains uncertain.
    """
    payload = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "event_identity": str(event_identity),
        "channel": channel,
    }
    response = _request_consumption_receipt(payload)
    if response.status_code != 200:
        logger.info(
            "_post_consumption_receipt | branch | entity_type=%s entity_id=%s event_identity=%s "
            "channel=%s reason=receipt_rejected status_code=%s",
            entity_type,
            entity_id,
            event_identity,
            channel,
            response.status_code,
        )
        if response.status_code in {401, 403, 404}:
            raise PermissionError(
                "The consumption receipt target or token is unavailable."
            )
        if response.status_code in {400, 409}:
            raise ValueError("The consumption receipt was rejected.")
        raise RuntimeError(
            f"Consumption receipt could not be confirmed. Retry with event_identity={event_identity}."
        )
    return _validate_consumption_receipt_response(response.json(), event_identity)


def _request_consumption_receipt(payload: Mapping[str, object]) -> httpx.Response:
    """Perform bounded real HTTP retries using the same immutable payload.

    :param payload: Four approved receipt fields. Example: original action UUID.
    :return: Actual HTTP response. Example: receipt HTTP 200.
    :raises RuntimeError: Bounded transport/retryable-server attempts exhausted.
    """
    identity = str(payload["event_identity"])
    for attempt in range(1, _RECEIPT_ATTEMPTS + 1):
        try:
            response = get_client().post(
                _RECEIPT_PATH, json=payload, headers={"X-Request-ID": identity}
            )
        except httpx.TransportError:
            reason = "transport_error"
        else:
            if response.status_code not in _RETRYABLE_RECEIPT_STATUS:
                return response
            reason = "retryable_status"
        logger.info(
            "_request_consumption_receipt | branch | event_identity=%s attempt=%s reason=%s",
            identity,
            attempt,
            reason,
        )
    raise RuntimeError(
        f"Consumption receipt could not be confirmed. Retry with event_identity={identity}."
    )


def _validate_consumption_receipt_response(
    payload: object, event_identity: UUID
) -> dict[str, object]:
    """Validate the safe receipt envelope without deriving domain eligibility.

    :param payload: Actual decoded receipt result. Example: applied/count=2.
    :param event_identity: Expected original UUID. Example: UUID(int=1).
    :return: Validated safe response. Example: skipped/self_consumption.
    :raises ValueError: Unexpected status, count, identity or response shape.
    """
    if not isinstance(payload, dict) or payload.get("event_identity") != str(
        event_identity
    ):
        raise ValueError("Unexpected consumption receipt identity or response.")
    status, count = payload.get("status"), payload.get("created_count")
    if status not in ("applied", "replayed", "skipped") or type(count) is not int:
        raise ValueError("Unexpected consumption receipt status or award count.")
    if (
        status == "skipped"
        and count == 0
        and payload.get("reason") == "self_consumption"
    ):
        return payload
    if status in ("applied", "replayed") and count == (2 if status == "applied" else 0):
        occurred_at = payload.get("occurred_at")
        if (
            isinstance(occurred_at, str)
            and datetime.fromisoformat(occurred_at).tzinfo is not None
        ):
            return payload
    raise ValueError("Unexpected consumption receipt outcome.")


def _preflight_workflow_export(
    *, bundle: dict, resolved_target: Path
) -> _LocalExportPlan:
    """Validate workflow, sibling rule and applicable Cursor destinations.

    Retain existing workspace guards for every root; call shared path guard.
    Revalidate destinations in existing writers immediately before each write.

    :param bundle: Authorized REST bundle. Example: {"folder_name": "BPE"}.
    :param resolved_target: Guarded target. Example: Path("/repo/playbooks").
    :return: Complete write plan and workflow summary builder.
    :raises ValueError: If bundle paths are invalid or escape approved roots.
    """
    folder = bundle["folder_name"]
    confined_export_path(resolved_target, folder)
    wf_dir = resolved_target / folder
    writes = [
        _export_write(resolved_target, (folder,), entry)
        for entry in bundle["workflow_files"]
    ]
    rule_files = bundle.get("rule_files") or []
    cursor_dir = _find_cursor_rules_dir(resolved_target)
    rules_dir = resolved_target.parent / "rules" if rule_files else None
    rule_paths = []
    if rules_dir is not None:
        writes.extend(_workflow_rule_writes(rules_dir, rule_files))
        rule_paths = [str(rules_dir / entry["filename"]) for entry in rule_files]
        if cursor_dir is not None and cursor_dir != rules_dir:
            writes.extend(
                _workflow_rule_writes(cursor_dir, rule_files, only_if_missing=True)
            )
    return _LocalExportPlan(
        tuple(writes),
        partial(
            _workflow_export_result, bundle, wf_dir, rules_dir, rule_paths, cursor_dir
        ),
    )


def _workflow_rule_writes(
    directory: Path, entries: list[dict], *, only_if_missing: bool = False
) -> Iterator[_ExportWrite]:
    """Approve the selected rule directory and plan the linked rule writes."""
    root, folders = directory.parent, (directory.name,)
    _approve_export_subdirectory(root, folders)
    for entry in entries:
        yield _export_write(root, folders, entry, only_if_missing=only_if_missing)


def _record_completed_export(
    *,
    entity_type: Literal["workflow", "playbook"],
    entity_id: int,
    event_identity: UUID,
    files_written: int,
) -> None:
    """Post S39's export receipt after the entire local invocation succeeds.

    Forward only identity/type/ID/channel; no business decisions here.
    Receipt transport retries retain this UUID and never repeat file writes.

    :param entity_type: Exported entity type. Example: "workflow".
    :param entity_id: Source primary key. Example: 6202.
    :param event_identity: Invocation UUID. Example: UUID(int=42).
    :param files_written: Successful write count for logs. Example: 4.
    :return: None after acknowledged receipt. Example: None.
    :raises ValueError: If arguments or receipt payload are invalid.
    :raises PermissionError: If receipt revalidation denies access.
    :raises RuntimeError: If receipt remains unavailable after allowed retry.
    """
    trace = f"entity_type={entity_type} entity_id={entity_id} event_identity={event_identity} channel={_EXPORT_CHANNEL}"
    try:
        result = _post_consumption_receipt(
            entity_type=entity_type,
            entity_id=entity_id,
            event_identity=event_identity,
            channel=_EXPORT_CHANNEL,
        )
    except (ValueError, PermissionError, RuntimeError) as exc:
        logger.info(
            "export_receipt | error | %s file_count=%s files_written=true receipt_status=failed",
            trace,
            files_written,
        )
        raise type(exc)(
            f"Export files were written. The export receipt could not be confirmed. "
            f"Retry only the receipt with event_identity={event_identity}."
        ) from None
    logger.info(
        "export_receipt | exit | %s file_count=%s receipt_status=%s created_count=%s",
        trace,
        files_written,
        result["status"],
        result["created_count"],
    )


def _preflight_playbook_export(
    *,
    bundle: dict,
    resolved_target: Path,
    additional_targets: list[str] | None,
    sync_root_rules: bool,
    ade_targets: list[str] | None,
    ade_target: str | None,
) -> _LocalExportPlan:
    """Validate canonical, mirror and explicitly requested ADE destinations.

    Merge the actual singular/plural ADE requests and validate returned file
    destinations against those requested target roots. Retain existing
    workspace guards and use the shared standard-library confinement utility.
    Complete preflight before the first canonical write.

    :param bundle: Authorized REST bundle. Example: {"folder_name": "Edda"}.
    :param resolved_target: Guarded canonical root. Example: Path("/repo/playbooks").
    :param additional_targets: Explicit mirror roots. Example: ["/repo/mirror"].
    :param sync_root_rules: Whether ADE writes are requested. Example: True.
    :param ade_targets: Actual requested ADE keys. Example: ["cursor"].
    :param ade_target: Actual singular alias. Example: "devin".
    :return: Complete write plan and playbook summary builder.
    :raises ValueError: If a root, child path or returned ADE destination is invalid.
    """
    targets = (
        resolved_target,
        *(
            ensure_writable_workspace_path(target, purpose="export")
            for target in additional_targets or []
        ),
    )
    folder = bundle["folder_name"]
    tree_files = tuple(_playbook_tree_files(bundle))
    writes = []
    for target in targets:
        confined_export_path(target, folder)
        writes.extend(
            _export_write(target, (folder, *directories), entry)
            for directories, entry in tree_files
        )
    if sync_root_rules:
        writes.extend(
            _playbook_ade_writes(
                resolved_target,
                ade_targets,
                ade_target,
                bundle.get("ade_rule_files") or [],
            )
        )
    canonical_filenames = [
        "/".join((*dirs, entry["filename"])) for dirs, entry in tree_files
    ]
    return _LocalExportPlan(
        tuple(writes),
        partial(_playbook_export_result, bundle, targets, canonical_filenames),
    )


def _playbook_tree_files(bundle: dict) -> Iterator[tuple[tuple[str, ...], dict]]:
    """Enumerate canonical files once in the established output order."""
    yield (), bundle["playbook_md"]
    for directory, files_key in (
        ("rules", "rule_files"),
        ("agents", "agent_files"),
        ("skills", "skill_files"),
        ("artifacts", "artifact_files"),
    ):
        for entry in bundle.get(files_key, []):
            yield (directory,), entry
    for workflow in bundle.get("workflows", []):
        for entry in workflow.get("workflow_files", []):
            yield (workflow["folder_name"],), entry


def _playbook_ade_writes(
    target: Path,
    ade_targets: list[str] | None,
    ade_target: str | None,
    entries: list[dict],
) -> Iterator[_ExportWrite]:
    """Approve explicitly requested file-based ADE roots and their actual entries."""
    requested = {
        key.strip().lower() for key in (*(ade_targets or []), ade_target or "")
    }
    folders_by_ade = {
        key: folders for key, folders in _ADE_RULE_FOLDERS.items() if key in requested
    }
    if not folders_by_ade and not entries:
        return
    root = ensure_writable_workspace_path(
        str(resolve_dev_root_from_export_target(target)), purpose="export"
    )
    for folders in folders_by_ade.values():
        _approve_export_subdirectory(root, folders)
    for entry in entries:
        folders = folders_by_ade.get(entry["ade_target"])
        if folders is None or entry["path"] != "/".join((*folders, entry["filename"])):
            raise ValueError("The ADE file must use a requested export rule directory.")
        yield _export_write(root, folders, entry)


def _approve_export_subdirectory(root: Path, folders: tuple[str, ...]) -> None:
    """Confine an implied directory to its parent tree and check its workspace mount."""
    expected = _resolve_export_directories(root, folders)
    guarded = ensure_writable_workspace_path(
        str(root.joinpath(*folders)), purpose="export"
    )
    if guarded != expected:
        raise ValueError("Export directory changed during validation.")


def _resolve_export_directories(root: Path, folders: tuple[str, ...]) -> Path:
    """Check each child tree against its own parent before resolving the leaves."""
    for folder in folders:
        root = confined_export_path(root, folder)
    return root


def _export_write(
    root: Path, folders: tuple[str, ...], entry: dict, *, only_if_missing: bool = False
) -> _ExportWrite:
    """Capture a file's immutable content and workspace-relative destination."""
    filename, content = entry["filename"], entry["content"]
    if not isinstance(filename, str) or not isinstance(content, str):
        raise ValueError("Invalid export file entry.")  # noqa: TRY004
    return _ExportWrite(root, folders, filename, content, only_if_missing)


def _resolve_export_write(write: _ExportWrite) -> Path:
    """Resolve the output leaf within its independently confined directory."""
    directory = _resolve_export_directories(write.root, write.folders)
    return confined_export_path(directory, write.filename)


def _write_export_file(write: _ExportWrite, expected: Path) -> int:
    """Recheck the destination before creating parents and again before writing."""
    if _resolve_export_write(write) != expected:
        raise ValueError("Export destination changed after validation.")
    if write.only_if_missing and expected.exists():
        return 0
    expected.parent.mkdir(parents=True, exist_ok=True)
    if _resolve_export_write(write) != expected:
        raise ValueError("Export destination changed after validation.")
    if write.only_if_missing:
        try:
            with expected.open("x", encoding="utf-8") as active_rule:
                active_rule.write(write.content)
        except FileExistsError:
            return 0
    else:
        expected.write_text(write.content, encoding="utf-8")
    return 1


def _write_export_plan(
    prepare: Callable[[], _LocalExportPlan], trace: str
) -> tuple[int, dict]:
    """Validate all outputs, execute ordered writes, and prepare the existing result."""
    completed = 0
    try:
        plan = prepare()
        destinations = tuple(_resolve_export_write(write) for write in plan.writes)
        logger.info(
            "facade_export | validation | %s destination_count=%s",
            trace,
            len(destinations),
        )
        for write, destination in zip(plan.writes, destinations, strict=True):
            completed += _write_export_file(write, destination)
        result = plan.build_result()
    except (OSError, ValueError) as exc:
        reason = (
            "filesystem_failure" if isinstance(exc, OSError) else "invalid_destination"
        )
        logger.info(
            "facade_export | error | %s reason=%s completed_file_count=%s receipt_sent=false",
            trace,
            reason,
            completed,
        )
        if isinstance(exc, OSError):
            raise OSError(exc.errno, exc.strerror) from None
        raise
    logger.info(
        "facade_export | processing | %s file_count=%s files_written=true",
        trace,
        completed,
    )
    return completed, result


def _run_local_export(
    *,
    entity_type: Literal["workflow", "playbook"],
    entity_id: int,
    route: str,
    target_directory: str,
    payload: dict[str, object],
    planner: Callable[..., _LocalExportPlan],
) -> dict:
    """Fetch the authorized export bundle, finish all local files, and attest success."""
    event_identity = uuid4()
    tool = f"export_{entity_type}_to_local"
    trace = f"tool={tool} entity_type={entity_type} entity_id={entity_id} event_identity={event_identity} channel={_EXPORT_CHANNEL}"
    logger.info("facade_export | entry | %s", trace)
    try:
        bundle = check_response(get_client().post(route, json=payload), tool)
    except httpx.TransportError, PermissionError, RuntimeError, ValueError:
        logger.info(
            "facade_export | error | %s reason=bundle_unavailable completed_file_count=0 receipt_sent=false",
            trace,
        )
        raise
    files_written, result = _write_export_plan(
        lambda: planner(
            bundle=bundle,
            resolved_target=ensure_writable_workspace_path(
                target_directory, purpose="export"
            ),
        ),
        trace,
    )
    _record_completed_export(
        entity_type=entity_type,
        entity_id=entity_id,
        event_identity=event_identity,
        files_written=files_written,
    )
    return result
