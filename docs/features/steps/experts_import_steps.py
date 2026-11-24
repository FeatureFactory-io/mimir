from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from behave import when
from behave.runner import Context
from rest_framework.authtoken.models import Token

from methodology.models import Workflow
from tests.support.experts_imports import (
    ExpertsImportState,
    ImportCase,
    _assert_experts_unchanged,
    _assert_import_protocol,
    _prepare_import_case,
    _snapshot_experts_state,
)
from tests.support.karma_mcp import collection_snapshot


@when("she imports a workflow")
def imports_a_workflow(context: Context) -> None:
    """Perform real positive protocol import using the existing Django API.

    :param context: Real AT context. Example: Cedar dataset, Maria token/client.
    :return: None. Example: actual positive diff/protocol verified, result retained.
    :raises AssertionError: Setup awards, import fails or real protocol is absent.
    """
    directory = TemporaryDirectory(prefix="mimir-s44-at-")
    context.test.addCleanup(directory.cleanup)
    case = _prepare_import_case(context.cedar_dataset, Path(directory.name))
    before = _snapshot_experts_state()
    context.mcp_state_before = collection_snapshot()
    token = Token.objects.get(user=context.mcp_actor)
    context.mcp_import_response = context.client.post(
        f"/api/workflows/{case.workflow_id}/import_workflow/",
        {"source_directory": str(case.source_directory)},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Token {token.key}",
    )
    context.mcp_import_result = _assert_import_server_response(context, case, before)
    context.mcp_import_case = case
    context.mcp_import_protocol = (
        case.source_directory / "_Upload_Protocol.md"
    ).read_text(encoding="utf-8")


def _assert_import_server_response(
    context: Context, case: ImportCase, before: ExpertsImportState
) -> dict[str, object]:
    """Verify actual authorized import and complete unchanged Experts state.

    :param context: Real response and actor. Example: Maria's token POST.
    :param case: Actual files and draft target. Example: one ID-free new activity.
    :param before: Complete pre-operation rows. Example: all 2,129 awards.
    :return: Positive native payload. Example: changes_detected and one new change.
    :raises AssertionError: Authentication, protocol, target or state differs.
    """
    response = context.mcp_import_response
    assert response.status_code == 200
    assert response.wsgi_request.user == context.mcp_actor
    assert (response.wsgi_request.method, response.wsgi_request.path) == (
        "POST",
        f"/api/workflows/{case.workflow_id}/import_workflow/",
    )
    result = response.json()
    assert isinstance(result, dict)
    _assert_import_protocol(result, case)
    assert not Workflow.objects.get(pk=case.workflow_id).activities.exists()
    _assert_experts_unchanged(before)
    assert collection_snapshot() == context.mcp_state_before
    return result
