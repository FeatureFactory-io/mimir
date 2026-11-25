"""Actual original receipt metadata, with explicitly synthetic output controls."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "original_diagnostic",
    _ROOT / "scripts/experts-staging/diagnose_original_invocations.py",
)
diag = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(diag)


@pytest.fixture(scope="module")
def protocol():
    """Use real ZIP-derived protocol identity; stdout/trace are synthetic controls."""
    index = diag.sources()
    row = diag.FIXED["invocations"][0]
    scopes = [n for n in index["remote.py"][1] if n.lineno <= 230 <= n.end_lineno]
    function = min(scopes, key=lambda n: n.end_lineno - n.lineno).name
    trace = f'  File "/var/tmp/mimir-experts-{row["nonce"]}/runtime/remote.py", line 230, in {function}\n'
    response = {
        "CommandId": row["command"],
        "InstanceId": diag.FIXED["instance"],
        "Status": "Failed",
        "ResponseCode": 1,
        "StandardOutputContent": json.dumps(
            {
                "stage": "owned_companion_start",
                "nonce": row["nonce"],
                "source_revision": diag.FIXED["candidate"],
            }
        ),
        "StandardErrorContent": "Traceback (most recent call last):\n"
        + trace
        + "RuntimeError: Owned command failed; no private command output exported.\n",
    }
    return row, index, response, trace


def test_summarize_with_actual_protocol_identity_and_source_bound_synthetic_trace_accepts(
    protocol,
):
    row, index, response, _ = protocol
    result = diag.summarize(response, row, index)
    assert result["read_status"] == "verified"
    assert result["classification"] == "known_remote_py_230_RuntimeError"
    assert result["frames"][0]["file"] == "remote.py"
    assert len(diag.FIXED["invocations"]) == 11


@pytest.mark.parametrize(
    "mutation",
    [
        "command",
        "instance",
        "candidate",
        "nonce",
        "duplicate",
        "extra",
        "status",
        "bool-code",
        "oversize",
    ],
)
def test_summarize_with_protocol_identity_or_bound_mismatch_rejects(protocol, mutation):
    row, index, original, _ = protocol
    response = copy.deepcopy(original)
    if mutation == "command":
        response["CommandId"] = diag.FIXED["invocations"][1]["command"]
    elif mutation == "instance":
        response["InstanceId"] = "i-00000000000000000"
    elif mutation == "status":
        response["Status"] = "PRIVATE_STATUS_CANARY"
    elif mutation == "bool-code":
        response["ResponseCode"] = True
    elif mutation == "oversize":
        response["StandardErrorContent"] = "PRIVATE_CANARY" * 6000
    else:
        marker = json.loads(response["StandardOutputContent"])
        if mutation == "candidate":
            marker["source_revision"] = "0" * 40
        elif mutation == "nonce":
            marker["nonce"] = "0" * 32
        elif mutation == "extra":
            marker["private"] = "PRIVATE_CANARY"
        response["StandardOutputContent"] = json.dumps(marker)
        if mutation == "duplicate":
            response["StandardOutputContent"] += "\n" + json.dumps(marker)
    result = diag.summarize(response, row, index)
    assert result["read_status"] == "response_rejected"
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize(
    "mutation", ["foreign-nonce", "foreign-file", "unknown-function", "invalid-line"]
)
def test_summarize_with_unreviewed_trace_frame_omits_all_untrusted_text(
    protocol, mutation
):
    row, index, original, _ = protocol
    response = copy.deepcopy(original)
    old = response["StandardErrorContent"]
    if mutation == "foreign-nonce":
        old = old.replace(row["nonce"], "0" * 32)
    elif mutation == "foreign-file":
        old = old.replace("remote.py", "PRIVATE_CANARY.py")
    elif mutation == "unknown-function":
        old = old.replace("in command", "in PRIVATE_CANARY")
    else:
        old = old.replace("line 230", "line 999999")
    response["StandardErrorContent"] = old
    result = diag.summarize(response, row, index)
    assert result["classification"] == "unknown" and result["frames"] == []
    assert "PRIVATE" not in json.dumps(result)


def test_summarize_with_later_unknown_exception_never_relabels_earlier_known_raise(
    protocol,
):
    row, index, original, _ = protocol
    response = copy.deepcopy(original)
    response[
        "StandardErrorContent"
    ] += '\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File "/outside/PRIVATE_CANARY.py", line 2, in secret\nKeyError: PRIVATE_URL_TOKEN_CANARY\n'
    result = diag.summarize(response, row, index)
    assert result["classification"] == "unknown"
    assert result["frames"] == []
    assert result["traceback_segments"][0]["kind"] == "earlier_exception_context"
    assert (
        result["traceback_segments"][0]["classification"]
        == "known_remote_py_230_RuntimeError"
    )
    assert result["traceback_segments"][-1]["kind"] == "terminal_exception"
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("alias", ["existing", "symlink", "hardlink"])
def test_publish_with_existing_or_aliased_output_never_admits_original(
    protocol, tmp_path, monkeypatch, alias
):
    monkeypatch.chdir(tmp_path)
    marker = tmp_path / "github-output"
    marker.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(marker))
    outside = tmp_path / "outside.json"
    outside.write_bytes(b"PRIVATE_OUTSIDE_CANARY")
    output = tmp_path / "diagnostic-45550540519.json"
    if alias == "symlink":
        output.symlink_to(outside)
    elif alias == "hardlink":
        output.hardlink_to(outside)
    else:
        output.write_bytes(b"ORIGINAL_BYTES")
    before = output.read_bytes()
    with pytest.raises(OSError):
        diag.publish({"status": "diagnostic_failed", "invocation_count": 0, "rows": []})
    assert (
        output.read_bytes() == before
        and outside.read_bytes() == b"PRIVATE_OUTSIDE_CANARY"
    )
    assert marker.read_text() == ""


def test_summarize_with_unreviewed_payload_keeps_only_counts(protocol):
    row, index, original, _ = protocol
    response = copy.deepcopy(original)
    response["PrivatePayload"] = "PRIVATE_EXTRA_CANARY"
    response["StandardOutputContent"] += "\nPRIVATE_STDOUT_TOKEN_CANARY"
    response["StandardErrorContent"] += "PRIVATE_STDERR_URL_CANARY"
    result = diag.summarize(response, row, index)
    assert result["read_status"] == "verified"
    assert result["stdout_line_count"] == 2
    assert "PRIVATE" not in json.dumps(result)


def test_main_with_wrong_ref_rejects_before_any_sdk_construction(monkeypatch):
    monkeypatch.delenv("GITHUB_REF", raising=False)
    with pytest.raises(ValueError, match="Fixed diagnostic ref required"):
        diag.main()


def test_workflow_with_manual_fixed_ref_contains_only_read_job():
    workflow = yaml.load(
        (_ROOT / ".github/workflows/build-and-deploy.yml").read_text(),
        Loader=yaml.BaseLoader,
    )
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert list(workflow["jobs"]) == ["read-original-invocations"]
    job = workflow["jobs"]["read-original-invocations"]
    assert (
        job["if"]
        == "github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/diagnostics/experts-full-stage-45550540519'"
    )
    upload = next(
        step
        for step in job["steps"]
        if step.get("uses") == "actions/upload-artifact@v4"
    )
    assert upload["if"] == "always() && steps.read.outputs.safe_json == 'true'"
    assert upload["with"]["path"] == "diagnostic-45550540519.json"
    assert (
        "send_command"
        not in (
            _ROOT / "scripts/experts-staging/diagnose_original_invocations.py"
        ).read_text()
    )
