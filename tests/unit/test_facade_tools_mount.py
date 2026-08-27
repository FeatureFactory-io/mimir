"""Unit tests for export mount guard in HTTP facade tools."""

from unittest.mock import MagicMock

import pytest

import mcp_integration.facade.tools_http as tools
from mcp_integration.facade import workspace_mount as workspace_mount
from mcp_integration.facade.client import configure


@pytest.fixture
def configured_client():
    configure("https://mimir.featurefactory.io", "test-token")


def test_export_raises_in_docker_without_mount_before_write(
    configured_client,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(workspace_mount, "is_running_in_docker", lambda: True)
    monkeypatch.delenv("MIMIR_DEV_ROOT", raising=False)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "workflow_id": 8,
        "workflow_name": "Envision the System",
        "folder_name": "ESM",
        "workflow_files": [
            {"filename": "_workflow.md", "content": "# Workflow\n"},
        ],
        "rule_files": [],
    }
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    monkeypatch.setattr(tools, "get_client", lambda: mock_client)

    export_dir = tmp_path / "export"
    with pytest.raises(ValueError, match="MIMIR_DEV_ROOT"):
        tools.export_workflow_to_local(
            workflow_id=8,
            target_directory=str(export_dir),
            folder_name="ESM",
        )

    assert not export_dir.exists()
    mock_client.post.assert_called_once()


def test_export_writes_when_not_in_docker(
    configured_client,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(workspace_mount, "is_running_in_docker", lambda: False)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "workflow_id": 8,
        "workflow_name": "Envision the System",
        "folder_name": "ESM",
        "workflow_files": [
            {"filename": "_workflow.md", "content": "# Workflow\n"},
        ],
        "rule_files": [],
    }
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    monkeypatch.setattr(tools, "get_client", lambda: mock_client)

    export_dir = tmp_path / "export"
    result = tools.export_workflow_to_local(
        workflow_id=8,
        target_directory=str(export_dir),
        folder_name="ESM",
    )

    workflow_md = export_dir / "ESM" / "_workflow.md"
    assert result["status"] == "exported"
    assert workflow_md.exists()
    assert workflow_md.read_text(encoding="utf-8") == "# Workflow\n"


def _playbook_export_bundle() -> dict:
    return {
        "playbook_id": 3,
        "playbook_name": "Edda",
        "folder_name": "Edda",
        "playbook_md": {"filename": "playbook.md", "content": "# Edda\n"},
        "rule_files": [
            {
                "filename": "pytest.mdc",
                "content": "---\nalwaysApply: true\n---\nUse pytest\n",
            }
        ],
        "agent_files": [{"filename": "Dobbs.md", "content": "# Dobbs\n"}],
        "skill_files": [{"filename": "Pytest.md", "content": "# Skill\n"}],
        "artifact_files": [{"filename": "Plan.md", "content": "# Plan\n"}],
        "workflows": [
            {
                "folder_name": "BPE",
                "workflow_files": [
                    {"filename": "_workflow.md", "content": "# BPE\n"},
                ],
            }
        ],
        "counts": {
            "workflows": 1,
            "activities": 1,
            "rules": 1,
            "skills": 1,
            "agents": 1,
            "artifacts": 1,
        },
    }


def _mock_playbook_export_client(monkeypatch, bundle: dict) -> MagicMock:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = bundle
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    monkeypatch.setattr(tools, "get_client", lambda: mock_client)
    return mock_client


def test_playbook_export_raises_in_docker_without_mount_before_write(
    configured_client,
    tmp_path,
    monkeypatch,
):
    """Docker facade must not write playbook dump without MIMIR_DEV_ROOT bind."""
    monkeypatch.setattr(workspace_mount, "is_running_in_docker", lambda: True)
    monkeypatch.delenv("MIMIR_DEV_ROOT", raising=False)
    mock_client = _mock_playbook_export_client(monkeypatch, _playbook_export_bundle())

    export_dir = tmp_path / "playbooks"
    with pytest.raises(ValueError, match="MIMIR_DEV_ROOT"):
        tools.export_playbook_to_local(
            playbook_id=3,
            target_directory=str(export_dir),
            folder_name="Edda",
        )

    assert not export_dir.exists()
    mock_client.post.assert_called_once()


def test_playbook_export_writes_when_not_in_docker(
    configured_client,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(workspace_mount, "is_running_in_docker", lambda: False)
    _mock_playbook_export_client(monkeypatch, _playbook_export_bundle())

    export_dir = tmp_path / "playbooks"
    result = tools.export_playbook_to_local(
        playbook_id=3,
        target_directory=str(export_dir),
        folder_name="Edda",
    )

    root = export_dir / "Edda"
    assert result["status"] == "exported"
    assert (root / "playbook.md").read_text(encoding="utf-8") == "# Edda\n"
    assert (root / "rules" / "pytest.mdc").exists()
    assert (root / "agents" / "Dobbs.md").exists()
    assert (root / "skills" / "Pytest.md").exists()
    assert (root / "artifacts" / "Plan.md").exists()
    assert (root / "BPE" / "_workflow.md").read_text(encoding="utf-8") == "# BPE\n"
    assert result["export_paths"] == [str(root)]


def test_playbook_export_docker_bind_mount_resolves_relative_target(
    configured_client,
    tmp_path,
    monkeypatch,
):
    """Relative .cursor/playbooks is anchored to MIMIR_DEV_ROOT on a bind mount."""
    monkeypatch.setattr(workspace_mount, "is_running_in_docker", lambda: True)
    monkeypatch.setenv("MIMIR_DEV_ROOT", str(tmp_path))
    monkeypatch.setattr(workspace_mount, "is_bind_mount", lambda path: True)
    _mock_playbook_export_client(monkeypatch, _playbook_export_bundle())

    result = tools.export_playbook_to_local(
        playbook_id=3,
        target_directory=".cursor/playbooks",
        folder_name="Edda",
    )

    playbook_md = tmp_path / ".cursor" / "playbooks" / "Edda" / "playbook.md"
    assert playbook_md.exists()
    assert playbook_md.read_text(encoding="utf-8") == "# Edda\n"
    assert result["export_paths"] == [str(playbook_md.parent)]


def test_playbook_export_additional_target_rejected_outside_dev_root(
    configured_client,
    tmp_path,
    monkeypatch,
):
    """additional_targets use the same bind-mount guard as target_directory."""
    monkeypatch.setattr(workspace_mount, "is_running_in_docker", lambda: True)
    monkeypatch.setenv("MIMIR_DEV_ROOT", str(tmp_path))
    monkeypatch.setattr(workspace_mount, "is_bind_mount", lambda path: True)
    _mock_playbook_export_client(monkeypatch, _playbook_export_bundle())

    outside = tmp_path.parent / "ephemeral-outside-dev-root"
    with pytest.raises(ValueError, match="outside MIMIR_DEV_ROOT"):
        tools.export_playbook_to_local(
            playbook_id=3,
            target_directory=".cursor/playbooks",
            folder_name="Edda",
            additional_targets=[str(outside)],
        )

    assert (tmp_path / ".cursor" / "playbooks" / "Edda" / "playbook.md").exists()
    assert not (outside / "Edda").exists()


def test_playbook_export_additional_target_writes_when_not_in_docker(
    configured_client,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(workspace_mount, "is_running_in_docker", lambda: False)
    _mock_playbook_export_client(monkeypatch, _playbook_export_bundle())

    primary = tmp_path / "cursor-playbooks"
    extra = tmp_path / "windsurf-playbooks"
    result = tools.export_playbook_to_local(
        playbook_id=3,
        target_directory=str(primary),
        folder_name="Edda",
        additional_targets=[str(extra)],
    )

    assert (primary / "Edda" / "playbook.md").exists()
    assert (extra / "Edda" / "playbook.md").read_text(encoding="utf-8") == "# Edda\n"
    assert (extra / "Edda" / "BPE" / "_workflow.md").exists()
    assert str(extra / "Edda") in result["export_paths"]
