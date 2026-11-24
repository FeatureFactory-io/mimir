"""Prove receipt negotiation against real old and current Django FOBs."""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from functools import partial
from pathlib import Path
from typing import Any, Literal

import pytest
from asgiref.sync import async_to_sync
from django.db import connections
from django.test import Client
from pytest import FixtureRequest
from pytest_django.live_server_helper import LiveServer
from rest_framework.authtoken.models import Token

from mcp_integration.facade import tools_http
from mcp_integration.facade.client import get_client
from methodology.models import KarmaAward, Playbook
from mimir.middleware import ConsumptionReceiptCapabilityMiddleware
from tests.support.experts_data import CedarDataset
from tests.support.experts_logs import capture_experts_logs
from tests.support.karma_mcp import MCPClientFactory, MCPDataset

_BASELINE = "333c36ded6bf58bdef94049ca0f5bf98c9ce3124"
_REPO = Path(__file__).resolve().parents[2]
_MIDDLEWARE = "mimir.middleware.ConsumptionReceiptCapabilityMiddleware"
_HEADER = "X-Mimir-Consumption-Receipts"
_RECEIPT = "/api/consumption-receipts/"
_Operation = Literal["detail", "workflow_export", "playbook_export"]


class UnknownReceiptCapabilityMiddleware(ConsumptionReceiptCapabilityMiddleware):
    """Exercise a genuine future server advertisement through real middleware."""

    receipt_version = "v2"


@pytest.fixture
def capability_server(
    request: FixtureRequest, settings: Any, transactional_db: None
) -> Iterator[LiveServer]:
    """Start the actual server only after selecting its actual middleware stack.

    :param request: Fixture request with mode parameter. Example: legacy.
    :param settings: Restoring Django settings fixture. Example: middleware list.
    :param transactional_db: Actual runner-owned transactional test database.
    :return: Real live server. Example: http://localhost:55000.
    :raises ValueError: Unknown test configuration.
    """
    mode = request.param
    middleware = [path for path in settings.MIDDLEWARE if path != _MIDDLEWARE]
    if mode == "current":
        middleware.append(_MIDDLEWARE)
    elif mode == "unknown":
        middleware.append(f"{__name__}.UnknownReceiptCapabilityMiddleware")
    elif mode != "legacy":
        raise ValueError("Unknown test capability mode.")
    settings.MIDDLEWARE = middleware
    settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "localhost"]
    server = LiveServer("localhost")
    try:
        yield server
    finally:
        server.stop()


@async_to_sync
async def _invoke(
    factory: MCPClientFactory, operation: _Operation, target: Path
) -> dict[str, Any]:
    """Invoke the genuine configured facade without replacing its HTTP client.

    :param factory: Restoring actual client context. Example: Maria's session.
    :param operation: Native operation. Example: workflow_export.
    :param target: Private export root. Example: pytest tmp_path.
    :return: Original native payload. Example: the actual playbook dictionary.
    :raises ValueError: Unsupported capability or invalid real response.
    """
    async with factory.open(actor_username="mrodriguez", entrypoint="facade"):
        if operation == "detail":
            return tools_http.get_playbook(6201)
        if operation == "workflow_export":
            return tools_http.export_workflow_to_local(6202, str(target))
        return tools_http.export_playbook_to_local(6201, str(target))


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("capability_server", "expected_receipts"),
    [("current", 1), ("legacy", 0)],
    indirect=["capability_server"],
)
@pytest.mark.parametrize("operation", ["detail", "workflow_export", "playbook_export"])
def test_facade_with_actual_server_advertisement_preserves_native_operations(
    capability_server: LiveServer,
    cedar_dataset: CedarDataset,
    operation: _Operation,
    expected_receipts: int,
    tmp_path: Path,
) -> None:
    """Use actual HTTP to preserve legacy reads and current paired receipts.

    :param capability_server: Actual selected middleware/server stack.
    :param cedar_dataset: Actual independent Cedar baseline.
    :param operation: Real native operation. Example: detail.
    :param expected_receipts: Required count from the independent case. Example: 1.
    :param tmp_path: Private export directory.
    :return: None after checking actual payload, HTTP and ledger changes.
    :raises AssertionError: Native content or advertised receipt behavior differs.
    """
    paths: list[tuple[str, str]] = []
    factory = MCPClientFactory(
        MCPDataset(cedar_dataset, {}, {}), capability_server.url, paths
    )
    before = list(KarmaAward.objects.order_by("pk").values())
    result = _invoke(factory, operation, tmp_path / "export")
    assert isinstance(result, dict)
    assert (result["id"] if operation == "detail" else result["status"]) == (
        6201 if operation == "detail" else "exported"
    )
    receipts = [path for _, path in paths if path == _RECEIPT]
    after = list(KarmaAward.objects.order_by("pk").values())
    assert len(receipts) == expected_receipts
    if expected_receipts:
        assert len(receipts) == 1 and len(paths) == 2
        assert after[: len(before)] == before and len(after) == len(before) + 2
    else:
        assert len(paths) == 1 and after == before


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("capability_server", ["unknown"], indirect=True)
@pytest.mark.parametrize("operation", ["detail", "workflow_export", "playbook_export"])
def test_facade_with_unknown_advertised_protocol_rejects_before_writes(
    capability_server: LiveServer,
    cedar_dataset: CedarDataset,
    operation: _Operation,
    tmp_path: Path,
) -> None:
    """An actual future-version server cannot silently disable receipt checks.

    :param capability_server: Actual middleware advertising v2.
    :param cedar_dataset: Actual independent Cedar baseline.
    :param operation: Native operation. Example: playbook_export.
    :param tmp_path: Private output root, which must remain empty.
    :return: None once the unsupported protocol is rejected without side effects.
    :raises AssertionError: A receipt or local write happens before rejection.
    """
    paths: list[tuple[str, str]] = []
    factory = MCPClientFactory(
        MCPDataset(cedar_dataset, {}, {}), capability_server.url, paths
    )
    before = list(KarmaAward.objects.order_by("pk").values())
    with pytest.raises(ValueError, match="Unsupported consumption receipt protocol"):
        _invoke(factory, operation, tmp_path / "export")
    assert len(paths) == 1 and not any(path == _RECEIPT for _, path in paths)
    assert list(KarmaAward.objects.order_by("pk").values()) == before
    assert not list(tmp_path.rglob("*"))


def test_receipt_capability_header_is_api_only(client: Client) -> None:
    """Keep transport metadata off ordinary user-facing HTML.

    :param client: Actual Django test client.
    :return: None after checking the real public landing response.
    :raises AssertionError: Internal protocol metadata leaks to non-API responses.
    """
    assert _HEADER not in client.get("/")


def _baseline_checkout(destination: Path) -> Path:
    """Materialize the exact known baseline without fetching from the network.

    :param destination: Private pytest directory. Example: tmp_path / 'baseline'.
    :return: Baseline source root. Example: destination.
    :raises AssertionError: Required CI baseline object is unavailable.
    """
    available = subprocess.run(
        ["git", "cat-file", "-e", f"{_BASELINE}^{{commit}}"],
        cwd=_REPO,
        capture_output=True,
        check=False,
    )
    if available.returncode:
        if os.environ.get("MIMIR_REQUIRE_FOB_COMPAT") == "1":
            pytest.fail("Required exact baseline Git object is unavailable.")
        pytest.skip(
            "Old-FOB proof needs the exact baseline Git object; CI requires it."
        )
    archive = subprocess.check_output(
        ["git", "archive", "--format=tar", _BASELINE], cwd=_REPO
    )
    destination.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        source.extractall(destination, filter="data")
    return destination


def _baseline_harness(baseline: Path) -> Path:
    """Place only the separate proof harness beside unchanged baseline sources.

    :param baseline: Exact baseline source directory.
    :return: External harness path. Example: compatibility_proof/test_legacy_fob.py.
    :raises OSError: The test harness cannot be materialized.
    """
    harness = baseline / "compatibility_proof"
    harness.mkdir()
    script = harness / "test_legacy_fob.py"
    shutil.copyfile(_REPO / "tests/support/legacy_fob_compatibility_case.py", script)
    return script


def _run_baseline_case(
    baseline: Path, output: Path
) -> subprocess.CompletedProcess[str]:
    """Run the committed actual-old-server harness under its own Django source.

    :param baseline: Exact baseline archive. Example: private baseline directory.
    :param output: Private proof destination. Example: pytest tmp_path.
    :return: Actual process result. Example: exit zero with one passing case.
    :raises OSError: Source cannot be copied or subprocess cannot be launched.
    """
    environment = dict(
        os.environ,
        PYTHONPATH=str(baseline),
        DATABASE_URL="",
        MIMIR_ENV="test",
        FOB_COMPAT_CANDIDATE=str(_REPO),
        FOB_COMPAT_PROBE=str(_REPO / "tests/support/fob_compatibility_probe.py"),
        FOB_COMPAT_OUTPUT=str(output / "old-fob-results.json"),
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            "pytest.ini",
            "-o",
            "addopts=",
            str(_baseline_harness(baseline)),
            "-q",
        ],
        cwd=baseline,
        env=environment,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    (output / "old-fob-run.txt").write_text(completed.stdout + completed.stderr)
    return completed


def test_current_facade_with_actual_pre_experts_fob_is_backward_compatible(
    tmp_path: Path,
) -> None:
    """Require the actual baseline server and both genuine client implementations.

    :param tmp_path: Private baseline, database and export workspace.
    :return: None after the independently executed real server/client matrix.
    :raises AssertionError: Any actual legacy operation regresses.
    """
    baseline = _baseline_checkout(tmp_path / "baseline")
    completed = _run_baseline_case(baseline, tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    proof = json.loads((tmp_path / "old-fob-results.json").read_text())
    assert all(row["status"] == "success" for row in proof["candidate"]["results"])


def _old_client_probe(
    source: Path, origin: str, token: str, target: Path
) -> dict[str, Any]:
    """Invoke the genuine older client against the current running server.

    :param source: Exact older facade source. Example: baseline archive.
    :param origin: Current live-server URL. Example: localhost ephemeral port.
    :param token: Real fictional-user token, never recorded.
    :param target: Private output directory.
    :return: Native operation and HTTP report. Example: three successes.
    :raises AssertionError: The actual older process fails.
    """
    environment = dict(
        os.environ,
        PYTHONPATH=str(source),
        PROBE_ORIGIN=origin,
        PROBE_TOKEN=token,
        PROBE_BOOK="6201",
        PROBE_WORKFLOW="6202",
        PROBE_EXPORT_ROOT=str(target),
        NO_PROXY="localhost,127.0.0.1",
    )
    result = subprocess.run(
        [sys.executable, str(_REPO / "tests/support/fob_compatibility_probe.py")],
        cwd=source,
        env=environment,
        text=True,
        capture_output=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, "Actual older facade process failed."
    return json.loads(result.stdout)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("capability_server", ["current"], indirect=True)
def test_old_facade_with_current_fob_ignores_new_metadata(
    capability_server: LiveServer, cedar_dataset: CedarDataset, tmp_path: Path
) -> None:
    """Keep genuine older clients operational when the FOB upgrades first.

    :param capability_server: Actual current FOB with v1 header enabled.
    :param cedar_dataset: Actual independent Cedar baseline.
    :param tmp_path: Private baseline-source and export workspace.
    :return: None after all three older operations and unchanged-ledger checks.
    :raises AssertionError: A new header changes old-client behavior.
    """
    baseline = _baseline_checkout(tmp_path / "baseline")
    actor = cedar_dataset.users_by_username["mrodriguez"]
    token, _ = Token.objects.get_or_create(user=actor)
    before = list(KarmaAward.objects.order_by("pk").values())
    proof = _old_client_probe(
        baseline, capability_server.url, token.key, tmp_path / "exports"
    )
    (tmp_path / "old-client-new-fob.json").write_text(
        json.dumps(proof, indent=2) + "\n"
    )
    assert all(row["status"] == "success" for row in proof["results"])
    assert len(proof["http"]) == 3 and all(
        row["status"] == 200 for row in proof["http"]
    )
    assert list(KarmaAward.objects.order_by("pk").values()) == before


def _retire_target(mode: str, target: int) -> None:
    """Perform a genuine intervening domain write on a separate DB thread.

    :param mode: Actual race condition. Example: missing.
    :param target: Existing disposable book identifier. Example: 6400.
    :return: None after the committed mutation.
    :raises ValueError: An unsupported test mutation is requested.
    """
    try:
        query = Playbook.objects.filter(pk=target)
        if mode == "missing":
            query.delete()
        elif mode == "private":
            query.update(visibility="private")
        else:
            raise ValueError("Unknown real target mutation.")
    finally:
        connections.close_all()


def _after_detail(mode: str, target: int, response: Any, statuses: list[int]) -> None:
    """Observe the real response and enact the declared intervening condition.

    :param mode: Token expiry, privacy change or deletion. Example: missing.
    :param target: Disposable actual book identifier. Example: 6400.
    :param response: Actual httpx response, never altered.
    :param statuses: Body-free actual HTTP status observations.
    :return: None after the optional real race setup.
    :raises RuntimeError: The actual mutation thread fails.
    """
    statuses.append(response.status_code)
    if response.request.method != "GET" or response.status_code != 200:
        return
    if mode == "expired":
        get_client().headers["Authorization"] = "Token deliberately-revoked-test-token"
    else:
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(_retire_target, mode, target).result(timeout=10)


@async_to_sync
async def _strict_race(
    factory: MCPClientFactory, mode: str, target: int, statuses: list[int]
) -> dict[str, Any]:
    """Keep the current-server receipt path strict after a successful real GET.

    :param factory: Restoring actual facade client context.
    :param mode: Declared real intervening condition. Example: expired.
    :param target: Actual disposable public book identifier.
    :param statuses: Body-free actual status report.
    :return: Native result only if authorized receipt succeeds.
    :raises PermissionError: Actual receipt denies the now-invalid target/token.
    """
    async with factory.open(actor_username="mrodriguez", entrypoint="facade"):
        get_client().event_hooks["response"].append(
            partial(_after_detail, mode, target, statuses=statuses)
        )
        return tools_http.get_playbook(target)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("capability_server", ["current"], indirect=True)
@pytest.mark.parametrize(
    ("mode", "denied_status"), [("missing", 404), ("private", 404), ("expired", 401)]
)
def test_current_fob_receipt_denial_after_successful_get_remains_strict(
    capability_server: LiveServer,
    cedar_dataset: CedarDataset,
    mode: str,
    denied_status: int,
) -> None:
    """Never interpret an actual current-server receipt rejection as legacy support.

    :param capability_server: Real current FOB advertising v1.
    :param cedar_dataset: Existing actual actors and baseline ledger.
    :param mode: Real intervening target/token change. Example: missing.
    :param denied_status: Expected actual receipt response. Example: 404.
    :return: None once rejection and unchanged-ledger assertions pass.
    :raises AssertionError: Failed receipt is swallowed or awards appear.
    """
    owner = cedar_dataset.users_by_username["mchen"]
    book = Playbook.objects.create(
        author=owner,
        name="Disposable compatibility case",
        category="design",
        visibility="public",
        status="released",
        version=Decimal("1.0"),
    )
    paths: list[tuple[str, str]] = []
    statuses: list[int] = []
    factory = MCPClientFactory(
        MCPDataset(cedar_dataset, {}, {}), capability_server.url, paths
    )
    before = list(KarmaAward.objects.order_by("pk").values())
    with pytest.raises(PermissionError):
        _strict_race(factory, mode, book.pk, statuses)
    assert statuses == [200, denied_status]
    assert paths == [("GET", f"/api/playbooks/{book.pk}/"), ("POST", _RECEIPT)]
    assert list(KarmaAward.objects.order_by("pk").values()) == before


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("capability_server", ["legacy"], indirect=True)
def test_legacy_capability_branch_logs_actual_no_receipt(
    capability_server: LiveServer,
    cedar_dataset: CedarDataset,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """Explain actual negotiated legacy behavior without logging response bodies.

    :param capability_server: Actual server without capability advertisement.
    :param cedar_dataset: Actual fictional actors and public content.
    :param caplog: Real production logger capture.
    :param tmp_path: Private output root.
    :return: None after checking the real branch log.
    :raises AssertionError: The no-receipt decision is missing or exposes credentials.
    """
    factory = MCPClientFactory(
        MCPDataset(cedar_dataset, {}, {}), capability_server.url, []
    )
    with capture_experts_logs(caplog, ("mcp_integration.facade.tools_http",)):
        _invoke(factory, "detail", tmp_path)
    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "reason=legacy_server receipt_sent=false" in message for message in messages
    )
    assert not any(
        "Authorization" in message or "Token " in message for message in messages
    )
