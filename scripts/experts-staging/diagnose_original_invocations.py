"""Read the eleven fixed original SSM invocations; never issue host commands."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import boto3

ROOT = Path(__file__).resolve().parent
FIXED = json.loads((ROOT / "original-invocations-45550540519.json").read_text())
KNOWN = {
    "ValueError",
    "RuntimeError",
    "AssertionError",
    "TypeError",
    "TimeoutError",
    "FileNotFoundError",
    "PermissionError",
}
FRAME = re.compile(
    r'^  File "([^"\r\n]{1,512})", line ([0-9]{1,6}), in ([^\r\n]{1,100})$',
    re.MULTILINE,
)


def sources() -> dict[str, Any]:
    """Index only exact reviewed source bytes, function scopes and literal raises.

    :return: Fixed basename to source AST; no application imports or execution.
    :raises ValueError: Reviewed source bytes or path differ.
    """
    result = {}
    for name, digest in FIXED["sources"].items():
        path = ROOT / name
        if (
            Path(name).name != name
            or path.is_symlink()
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise ValueError("Reviewed diagnostic source differs")
        tree = ast.parse(path.read_text())
        functions = [
            n
            for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        result[name] = (tree, functions, len(path.read_text().splitlines()))
    return result


def frame_record(
    name: str, line: int, function: str, index: dict[str, Any]
) -> dict[str, Any]:
    """Validate a frame against the exact file length and innermost AST scope.

    :param name: Already prefix-stripped basename; :param line: Trace line.
    :param function: Untrusted reported scope; :param index: Reviewed source ASTs.
    :return: Closed source frame, or empty when no exact scope matches.
    """
    if name not in index or not 1 <= line <= index[name][2]:
        return {}
    scopes = [n for n in index[name][1] if n.lineno <= line <= n.end_lineno]
    expected = (
        min(scopes, key=lambda n: n.end_lineno - n.lineno).name
        if scopes
        else "<module>"
    )
    return (
        {"file": name, "line": line, "function": expected}
        if function == expected
        else {}
    )


def facts(stderr: str, nonce: str, index: dict[str, Any]) -> dict[str, Any]:
    """Keep ordered source-bound exception contexts separately from terminal facts.

    :param stderr: Unexported actual stderr; :param nonce: Fixed original owner.
    :param index: Reviewed source ASTs.
    :return: Safe segments and terminal classification; unknown remains unknown.
    """
    parts = stderr.split("Traceback (most recent call last):")[1:]
    if len(parts) > 8:
        raise ValueError("Bounded original exception chain required")
    segments = [segment(part, nonce, index) for part in parts]
    for number, item in enumerate(segments):
        item["kind"] = (
            "terminal_exception"
            if number == len(segments) - 1
            else "earlier_exception_context"
        )
    terminal = segments[-1] if segments else {"frames": [], "classification": "unknown"}
    return {
        "traceback_segments": segments,
        "frames": terminal["frames"],
        "classification": terminal["classification"],
        "stderr_line_count": len(stderr.splitlines()),
        "exception_count": len(segments),
    }


def segment(stderr: str, nonce: str, index: dict[str, Any]) -> dict[str, Any]:
    """Project only exact reviewed frames from one actual traceback segment.

    :param stderr: One unexported exception segment; :param nonce: Original owner.
    :param index: Reviewed source ASTs; :return: Closed facts and counts.
    """
    matches, frames = FRAME.findall(stderr), []
    prefix = f"/var/tmp/mimir-experts-{nonce}/runtime/"
    for filename, line, function in matches:
        if filename.startswith(prefix):
            record = frame_record(filename[len(prefix) :], int(line), function, index)
            if record:
                frames.append(record)
    if len(frames) > 32:
        raise ValueError("Bounded original traceback required")
    return {
        "frames": frames,
        "unknown_frame_count": len(matches) - len(frames),
        "classification": classification(stderr, frames, index),
    }


def classification(
    stderr: str, frames: list[dict[str, Any]], index: dict[str, Any]
) -> str:
    """Recognize literal reviewed raises only when their actual source frame exists.

    :param stderr: Unexported stored bytes decoded by SSM.
    :param frames: Source-verified frames; :param index: Reviewed source ASTs.
    :return: Finite source-derived code, never exception text or unknown class.
    """
    endings = re.findall(r"^([A-Za-z_][A-Za-z0-9_.]*): ?(.*)$", stderr, re.MULTILINE)
    ending = endings[-1] if endings else None
    for frame in reversed(frames):
        for node in ast.walk(index[frame["file"]][0]):
            if not isinstance(node, ast.Raise) or node.lineno != frame["line"]:
                continue
            call = node.exc
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id in KNOWN
                and len(call.args) == 1
                and isinstance(call.args[0], ast.Constant)
                and isinstance(call.args[0].value, str)
                and ending == (call.func.id, call.args[0].value)
            ):
                return f"known_{frame['file'].replace('.', '_')}_{node.lineno}_{call.func.id}"
    return "unknown"


def unknown(row: dict[str, Any]) -> dict[str, Any]:
    """Create fixed unknown facts without copying any external values.

    :param row: Trusted original invocation from the committed receipt fixture.
    :return: Closed unknown projection; no cloud response fields are used.
    """
    return {
        "nonce": row["nonce"],
        "phase": row["phase"],
        "status": "Unknown",
        "responseCode": -1,
        "read_status": "response_rejected",
    }


def summarize(
    response: dict[str, Any], row: dict[str, Any], index: dict[str, Any]
) -> dict[str, Any]:
    """Admit one exact original identity before interpreting any stored output.

    :param response: Untrusted SSM response, never copied or logged.
    :param row: Fixed original invocation; :param index: Reviewed source ASTs.
    :return: Closed derivative; rejects identity/protocol mismatches without text.
    """
    result = unknown(row)
    stdout = response.get("StandardOutputContent")
    stderr = response.get("StandardErrorContent")
    expected = {
        "CommandId": row["command"],
        "InstanceId": FIXED["instance"],
        "Status": "Failed",
        "ResponseCode": 1,
    }
    if (
        any(response.get(k) != v for k, v in expected.items())
        or type(response.get("ResponseCode")) is not int
    ):
        return result
    if (
        not isinstance(stdout, str)
        or not isinstance(stderr, str)
        or max(len(stdout), len(stderr)) > 65536
    ):
        return result
    if not start_matches(stdout, row["nonce"]):
        return result
    result.update(
        status="Failed",
        responseCode=1,
        read_status="verified",
        stdout_line_count=len(stdout.splitlines()),
        **facts(stderr, row["nonce"], index),
    )
    return result


def start_matches(stdout: str, nonce: str) -> bool:
    """Require exactly one candidate/owner start declaration.

    :param stdout: Unexported output; :param nonce: Fixed original owner.
    :return: Whether the exact original start identity matches.
    """
    starts = []
    for line in stdout.splitlines():
        try:
            value = json.loads(line)
            if (
                isinstance(value, dict)
                and value.get("stage") == "owned_companion_start"
            ):
                starts.append(value)
        except (ValueError, RecursionError):
            pass
    return starts == [
        {
            "stage": "owned_companion_start",
            "source_revision": FIXED["candidate"],
            "nonce": nonce,
        }
    ]


def main() -> dict[str, Any]:
    """Read fixed original invocations and export one exclusively created JSON file.

    :return: Closed derivative; API failures stay unknown, never raw exceptions.
    :raises ValueError: Account, region/ref or original reviewed source differs.
    """
    if (
        os.environ.get("GITHUB_REF")
        != "refs/heads/diagnostics/experts-full-stage-45550540519"
    ):
        raise ValueError("Fixed diagnostic ref required")
    index = sources()
    session = boto3.Session(region_name="us-east-1")
    if session.client("sts").get_caller_identity()["Account"] != "411113550285":
        raise ValueError("Fixed diagnostic account required")
    client, rows = session.client("ssm"), []
    for row in FIXED["invocations"]:
        try:
            response = client.get_command_invocation(
                CommandId=row["command"], InstanceId=FIXED["instance"]
            )
            rows.append(summarize(response, row, index))
        except Exception:  # noqa: BLE001 -- Never expose arbitrary SDK/parser messages.
            failed = summarize({}, row, index)
            failed["read_status"] = "read_or_projection_failed"
            rows.append(failed)
    return {"status": "read_completed", "invocation_count": len(rows), "rows": rows}


def publish(result: dict[str, Any]) -> None:
    """Publish only the constructed derivative, then authorize its exact upload.

    :param result: Internally constructed safe projection, never an API response.
    :return: None after exclusive write; existing/linked files are never admitted.
    :raises OSError: Output already exists or cannot be exclusively written.
    """
    with Path("diagnostic-45550540519.json").open("x") as output:
        json.dump(result, output, sort_keys=True)
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as marker:
        marker.write("safe_json=true\n")


if __name__ == "__main__":
    try:
        result = main()
    except Exception:  # noqa: BLE001 -- Never expose credential/SDK errors.
        result = {"status": "diagnostic_failed", "invocation_count": 0, "rows": []}
    try:
        publish(result)
    except Exception:  # noqa: BLE001 -- Never log a failed output write.
        raise SystemExit(1) from None
