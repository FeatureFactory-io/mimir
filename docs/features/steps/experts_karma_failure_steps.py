"""S46 server-contract bindings; native clipboard proof remains Playwright."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from behave import then, when
from behave.runner import Context
from django.http import HttpResponse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from methodology.services.experts_service import ExpertsService
from methodology.services.workflow_export_service import WorkflowExportService
from tests.support.experts_data import CedarDataset
from tests.support.karma_failures import (
    LedgerSnapshot,
    assert_global_ledger_unchanged,
    assert_no_private_data,
    prepare_denied_target,
    snapshot_global_ledger,
)

FailureObservation = tuple[str, LedgerSnapshot, LedgerSnapshot]
_FAILURE_CASES = ("private_read", "private_receipt", "forged_receipt", "failed_export")
_RECEIPT_PATH = "/api/consumption-receipts/"
_PUBLIC_ACTIVITY = 6203
_PUBLIC_WORKFLOW = 6202
_EXPORT_FOLDER = "blocked"
_FILE_BLOCKER = b"existing regular file; do not replace"
_BASELINE_TOTALS = {"mrodriguez": 8200, "mchen": 12450}


@when("a private read is denied or a clipboard write or export fails")
def fail_or_deny_consumption(context: Context) -> None:
    """Run actual private-read denial and filesystem-service failure cases.

    :param context: Real AT client and independently restored Cedar baseline.
    :return: None. Example: four server observations and complete ledger snapshots.
    :raises AssertionError: Operation unexpectedly succeeds or lacks evidence.
    """
    dataset = context.cedar_dataset
    actor, target = prepare_denied_target(dataset, "activity", "private")
    token, _ = Token.objects.get_or_create(user=actor)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    context.failure_ledger_before = snapshot_global_ledger()
    context.failure_observations = (
        _denied_read(dataset, client, target),
        _rejected_receipt(dataset, client, target, forged=False),
        _rejected_receipt(dataset, client, _PUBLIC_ACTIVITY, forged=True),
        _failed_export(dataset),
    )


@then("no consumption award is created for either party")
def assert_no_consumption_awards(context: Context) -> None:
    """Assert every captured server failure preserved the complete ledger.

    :param context: Real server observations, e.g. private read and export failure.
    :return: None. Example: no recipient has a new or mutated award.
    :raises AssertionError: Any global ledger field differs or a case is missing.
    """
    observations = context.failure_observations
    if tuple(name for name, _, _ in observations) != _FAILURE_CASES:
        raise AssertionError("All four real server failures must be observed.")
    for _, before, after in observations:
        if before != context.failure_ledger_before or after != before:
            raise AssertionError("A server failure changed the complete global ledger.")
    assert_global_ledger_unchanged(context.failure_ledger_before)
    for username, total in _BASELINE_TOTALS.items():
        person = ExpertsService().project_user(context.cedar_dataset.user_ids[username])
        if person.total_points != total:
            raise AssertionError("A server failure changed a Cedar party's total.")


def _denied_read(
    dataset: CedarDataset, client: APIClient, target: int
) -> FailureObservation:
    """Request an actual activity under a private released playbook as Elena.

    :param dataset: Real Cedar records. Example: Maria's protected activity.
    :param client: Actually token-authenticated reader. Example: nonstaff Elena.
    :param target: Persisted private activity PK. Example: a test-owned child.
    :return: Full-ledger observation. Example: ("private_read", before, after).
    :raises AssertionError: Read succeeds, leaks private data or changes awards.
    """
    before = snapshot_global_ledger()
    response = client.get(f"/api/activities/{target}/")
    _assert_safe_rejection(dataset, response, HTTPStatus.NOT_FOUND)
    assert_global_ledger_unchanged(before)
    return "private_read", before, snapshot_global_ledger()


def _rejected_receipt(
    dataset: CedarDataset, client: APIClient, target: int, *, forged: bool
) -> FailureObservation:
    """Submit a real denied target or forged attribution through the token boundary.

    :param dataset: Original Cedar state. Example: Elena and Maria records.
    :param client: Real authenticated reader. Example: Elena's APIClient.
    :param target: Actual entity ID. Example: the private activity or public6203.
    :param forged: Include a prohibited actor override when true. Example: False.
    :return: Full-ledger observation. Example: ("private_receipt", before, after).
    :raises AssertionError: Invalid receipt succeeds, leaks or changes the ledger.
    """
    before = snapshot_global_ledger()
    payload = {
        "entity_type": "activity",
        "entity_id": target,
        "event_identity": str(uuid4()),
        "channel": "mcp_detail",
    }
    if forged:
        payload["actor_id"] = dataset.user_ids["mrodriguez"]
    response = client.post(_RECEIPT_PATH, payload, format="json")
    status = HTTPStatus.BAD_REQUEST if forged else HTTPStatus.NOT_FOUND
    reason = "invalid_payload" if forged else "target_unavailable"
    _assert_safe_rejection(dataset, response, status, reason=reason)
    assert_global_ledger_unchanged(before)
    name = "forged_receipt" if forged else "private_receipt"
    return name, before, snapshot_global_ledger()


def _assert_safe_rejection(
    dataset: CedarDataset,
    response: HttpResponse,
    status: HTTPStatus,
    *,
    reason: str | None = None,
) -> None:
    """Check actual failure status and sanitize failure diagnostics before comparisons.

    :param dataset: Actual protected fixture values. Example: Cedar tokens.
    :param response: Real Django/DRF response. Example: masked404.
    :param status: Required rejection status. Example: HTTPStatus.NOT_FOUND.
    :param reason: Required safe receipt reason, or None for detail. Example: None.
    :return: None. Example: no secret values enter assertion output.
    :raises AssertionError: Status, envelope or private-content boundary differs.
    """
    assert_no_private_data(dataset, response.content.decode("utf-8"))
    if response.status_code != status:
        raise AssertionError("Server failure did not return its required rejection.")
    if reason is not None and response.json() != {
        "status": "rejected",
        "reason": reason,
    }:
        raise AssertionError("Server failure did not return its safe receipt envelope.")


def _failed_export(dataset: CedarDataset) -> FailureObservation:
    """Cause a genuine file-as-parent error in the existing workflow writer.

    :param dataset: Real authorized Maria/Mike data. Example: public workflow6202.
    :return: Full-ledger observation. Example: ("failed_export", before, after).
    :raises AssertionError: Export succeeds, changes the blocker or creates awards.
    """
    before = snapshot_global_ledger()
    actor = dataset.users_by_username["mrodriguez"]
    with TemporaryDirectory(prefix="mimir-s46-at-export-") as directory:
        root = Path(directory)
        blocker = root / _EXPORT_FOLDER
        blocker.write_bytes(_FILE_BLOCKER)
        try:
            WorkflowExportService.export_workflow_to_markdown(
                _PUBLIC_WORKFLOW, str(root), folder_name=_EXPORT_FOLDER, user=actor
            )
        except OSError:
            if blocker.read_bytes() != _FILE_BLOCKER or set(root.iterdir()) != {
                blocker
            }:
                raise AssertionError(
                    "Failed export changed its original file obstacle."
                )
        else:
            raise AssertionError("Actual file-as-parent export unexpectedly succeeded.")
    assert_global_ledger_unchanged(before)
    return "failed_export", before, snapshot_global_ledger()
