"""Run inside the immutable pre-Experts checkout, with its real Django models."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from django.contrib.auth.models import User
from pytest_django.live_server_helper import LiveServer
from rest_framework.authtoken.models import Token

from methodology.models import Activity, Playbook, Workflow


def _fixture() -> tuple[Token, Playbook, Workflow]:
    """Create fictional public content only in the actual pytest database.

    :return: Real token, playbook and workflow. Example: one released book.
    :raises ValueError: The actual ORM rejects fixture fields.
    """
    owner = User.objects.create_user(username="compatibility_owner")
    reader = User.objects.create_user(username="compatibility_reader")
    book = Playbook.objects.create(
        author=owner,
        name="Compatibility review",
        description="Public guidance.",
        category="design",
        visibility="public",
        status="released",
        version=Decimal("1.0"),
    )
    workflow = Workflow.objects.create(
        playbook=book, name="Review compatibility", abbreviation="RC", order=1
    )
    Activity.objects.create(
        workflow=workflow,
        name="Read published work",
        guidance="Review this public example.",
        order=1,
    )
    return Token.objects.create(user=reader), book, workflow


def _probe(
    source: Path,
    origin: str,
    token: Token,
    book: Playbook,
    workflow: Workflow,
    target: Path,
) -> dict[str, Any]:
    """Run the chosen actual facade source in a separate interpreter.

    :param source: Actual client checkout. Example: immutable baseline.
    :param origin: Actual baseline server. Example: http://localhost:55000.
    :param token: Fictional real token, never printed.
    :param book: Existing released public book. Example: saved fixture book.
    :param workflow: Existing workflow. Example: saved fixture workflow.
    :param target: Private export root. Example: Path('/tmp/old-client').
    :return: Parsed real subprocess results. Example: successful native reads.
    :raises AssertionError: The probe process fails.
    """
    environment = dict(
        os.environ,
        PYTHONPATH=str(source),
        PROBE_ORIGIN=origin,
        PROBE_TOKEN=token.key,
        PROBE_BOOK=str(book.pk),
        PROBE_WORKFLOW=str(workflow.pk),
        PROBE_EXPORT_ROOT=str(target),
        NO_PROXY="localhost,127.0.0.1",
    )
    completed = subprocess.run(
        [sys.executable, os.environ["FOB_COMPAT_PROBE"]],
        cwd=source,
        env=environment,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert completed.returncode == 0, "Actual facade probe process failed."
    return json.loads(completed.stdout)


def _comparable_files(results: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Compare every output byte except the exporter-generated UTC minute label.

    :param results: Actual native operation reports, including original raw hashes.
    :return: Content fingerprints retaining paths and byte counts.
    :raises KeyError: A genuine probe report omits its file evidence.
    """
    return [
        [
            {key: value for key, value in file.items() if key != "sha256"}
            for file in row["files"]
        ]
        for row in results
    ]


@pytest.mark.django_db(transaction=True)
def test_actual_old_fob_accepts_old_and_new_clients(
    live_server: LiveServer, tmp_path: Path
) -> None:
    """Preserve both native clients against the genuine pre-Experts server.

    :param live_server: Actual baseline Django server on its pytest database.
    :param tmp_path: Private export root. Example: pytest's temporary directory.
    :return: None after native content, files and HTTP assertions.
    :raises AssertionError: Any existing operation or native result regresses.
    """
    token, book, workflow = _fixture()
    baseline = Path.cwd()
    results = {
        name: _probe(source, live_server.url, token, book, workflow, tmp_path / name)
        for name, source in (
            ("baseline", baseline),
            ("candidate", Path(os.environ["FOB_COMPAT_CANDIDATE"])),
        )
    }
    Path(os.environ["FOB_COMPAT_OUTPUT"]).write_text(
        json.dumps(results, indent=2) + "\n"
    )
    for result in results.values():
        assert all(row["status"] == "success" for row in result["results"])
        assert len(result["http"]) == 3
        assert all(row["status"] == 200 for row in result["http"])
        assert not any(
            row["path"] == "/api/consumption-receipts/" for row in result["http"]
        )
    old, new = results["baseline"]["results"], results["candidate"]["results"]
    assert old[0]["result"] == new[0]["result"]
    assert _comparable_files(old) == _comparable_files(new)
