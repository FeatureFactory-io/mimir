"""Exercise the installed facade against a real independently selected FOB."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from mcp_integration.facade import tools_http
from mcp_integration.facade.client import configure, get_client


def _invoke(operation: str, target: Path) -> dict[str, Any]:
    """Invoke the real native detail or export tool.

    :param operation: Selected native operation. Example: workflow_export.
    :param target: Private export root. Example: Path('/tmp/probe/export').
    :return: Original native result. Example: a playbook dictionary.
    :raises ValueError: Unknown operation or invalid fixture identifiers.
    """
    book = int(os.environ["PROBE_BOOK"])
    if operation == "detail":
        return tools_http.get_playbook(book)
    if operation == "workflow_export":
        return tools_http.export_workflow_to_local(
            int(os.environ["PROBE_WORKFLOW"]), str(target), folder_name="compatibility"
        )
    if operation == "playbook_export":
        return tools_http.export_playbook_to_local(
            book, str(target), folder_name="compatibility"
        )
    raise ValueError("Unknown compatibility operation.")


def _files(target: Path) -> list[dict[str, str | int]]:
    """Fingerprint the actual written files without changing them.

    :param target: Private export root. Example: Path('/tmp/probe/export').
    :return: Sorted file fingerprints. Example: [{'bytes': 20, ...}].
    :raises OSError: An output file cannot be read.
    """
    return [
        {
            "path": str(file.relative_to(target)),
            "bytes": file.stat().st_size,
            "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
        }
        for file in sorted(target.rglob("*"))
        if file.is_file()
    ]


def _operation(operation: str, root: Path) -> dict[str, Any]:
    """Retain the actual operation result and any completed files.

    :param operation: Native operation. Example: detail.
    :param root: Private probe root. Example: Path('/tmp/probe').
    :return: Body-free failure or native success. Example: status=success.
    :raises OSError: A written file cannot be fingerprinted.
    """
    target = root / operation
    try:
        result = _invoke(operation, target)
    except Exception as error:  # noqa: BLE001 — external probe reports actual failures
        return {
            "operation": operation,
            "status": "failure",
            "error_class": type(error).__name__,
            "files": _files(target),
        }
    return {
        "operation": operation,
        "status": "success",
        "result": result,
        "files": _files(target),
    }


def main() -> None:
    """Exercise actual HTTP while retaining no credentials in the report.

    :return: None after printing JSON. Example: three successful operations.
    :raises ValueError: Explicit probe environment is malformed.
    """
    configure(os.environ["PROBE_ORIGIN"], os.environ["PROBE_TOKEN"])
    paths: list[dict[str, str | int]] = []
    get_client().event_hooks["response"].append(
        lambda response: paths.append(
            {
                "method": response.request.method,
                "path": response.request.url.path,
                "status": response.status_code,
            }
        )
    )
    root = Path(os.environ["PROBE_EXPORT_ROOT"])
    results = [
        _operation(name, root)
        for name in ("detail", "workflow_export", "playbook_export")
    ]
    print(json.dumps({"results": results, "http": paths}))


if __name__ == "__main__":
    main()
