"""MCP and review surfaces must retain the requested PIP position."""

from unittest.mock import MagicMock

from mcp_integration.facade import tools_http
from mcp_integration.tools import _serialize_pip_change
from methodology.models import PipChange
from methodology.services.galdr_prompts import _format_change_list, build_change_prompt


def test_add_pip_change_with_position_forwards_to_hosted_api(monkeypatch):
    client = MagicMock()
    client.post.return_value.status_code = 201
    client.post.return_value.json.return_value = {"change_id": 7}
    monkeypatch.setattr(tools_http, "get_client", lambda: client)
    assert tools_http.add_pip_change(
        1, "ALTER", "Workflow", target_id=2, display_order=1
    ) == {"change_id": 7}
    assert client.post.call_args.args == ("/api/pips/1/changes/",)
    assert client.post.call_args.kwargs["json"]["display_order"] == 1


def test_serialize_pip_change_with_position_includes_position():
    change = PipChange(change_type="ALTER", entity_type="Workflow", display_order=1)
    assert _serialize_pip_change(change)["display_order"] == 1


def test_review_prompts_with_position_include_requested_position():
    change = PipChange(change_type="ALTER", entity_type="Workflow", display_order=1)
    assert "display_order: 1" in _format_change_list([change])
    assert "display_order: 1" in build_change_prompt(change, "Current playbook")
