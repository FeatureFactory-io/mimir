"""Companion-only same-worker finite provider and passive private observations.

Django initializes first. No application endpoint, scheduler, model service or
response body is replaced. This is never the normal deployment WSGI target.
"""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from django.core.wsgi import get_wsgi_application

_django_application = get_wsgi_application()

from django.conf import settings
from django.db import connection
from methodology.models import ProcessImprovementProposal
from tests.support.experts_summary_data import SUMMARY_SCRIPTS, load_summary_script
from tests.support.scripted_llm import ScriptedLLM

import saga_summary_fixture as fixture
from saga_summary_fixture import capture_reviewed, prepared_change, read_baseline
from suite_runtime import verify
from suite_worker_verify import start_server


def configure_provider() -> tuple[ScriptedLLM, dict[str, Any]]:
    """Bind one finite port in the actual serving worker after scope/target checks.

    :return: Actual provider instance and private prepared identity.
    :raises AssertionError: Wrong case, worker, database, state or scheduler mode.
    """
    assert os.environ.get("EXPERTS_SAGA_CASE") == "summary-acceptance"
    assert connection.vendor == "postgresql" and settings.GALDR_EAGER is False
    assert (
        settings.GALDR_USE_TARGET_STATE is True
        and settings.GALDR_USE_ANTHROPIC is False
    )
    assert not getattr(settings, "CONTRIBUTION_SUMMARY_LLM", None)
    baseline = read_baseline()
    change = prepared_change(baseline)
    assert change.pip.status == ProcessImprovementProposal.STATUS_DRAFT
    port = ScriptedLLM(
        load_summary_script(SUMMARY_SCRIPTS / "PRF-EXPERTS-01/happy.json", change.pk)
    )
    settings.CONTRIBUTION_SUMMARY_LLM = port
    settings.CONTRIBUTION_SUMMARY_MODEL_RATES = {}
    return port, baseline


_port, _baseline = configure_provider()
_lock = threading.Lock()


def observe(environ: dict[str, Any], previous: dict[str, Any] | None) -> None:
    """Read actual persisted Reviewed once; append body-free actual worker count.

    :param environ: Actual original request metadata, never body or cookies.
    :param previous: Actual auth-route session rows before the original request.
    :return: None after real precise private observations.
    :raises AssertionError: Effects do not match the immutable predecision oracle.
    :raises OSError: A private exclusive observation cannot be retained.
    """
    with _lock:
        fixture.scope()
        calls = len(_port.calls)
        pip = ProcessImprovementProposal.objects.get(pk=_baseline["pip_id"])
        if (
            pip.status == pip.STATUS_REVIEWED
            and not (fixture._ROOT / "saga-summary-reviewed.json").exists()
        ):
            capture_reviewed(_baseline, calls)
        record_worker(environ, previous, calls)


def record_worker(
    environ: dict[str, Any], previous: dict[str, Any] | None, calls: int
) -> None:
    """Retain private actual count and exact auth-route session lifecycle snapshots.

    :param environ: Actual method/path metadata; no request body or cookies.
    :param previous: Private precise session snapshot before the real auth action.
    :param calls: Actual serving-process port count.
    :return: None after an append-only private record.
    """
    descriptor = os.open(
        fixture._ROOT / "saga-summary-worker.jsonl",
        os.O_APPEND | os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "a") as stream:
        stream.write(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "provider_calls": calls,
                    "galdr_eager": settings.GALDR_EAGER,
                    "path": environ.get("PATH_INFO"),
                    "method": environ.get("REQUEST_METHOD"),
                    "sessions_before": previous,
                    "sessions_after": (
                        fixture.domain_rows()["sessions.session"]
                        if previous is not None
                        else None
                    ),
                }
            )
            + "\n"
        )


def application(
    environ: dict[str, Any], start_response: Callable[..., Any]
) -> Iterable[bytes]:
    """Serve genuine Django requests, requiring observation before native finalization.

    :param environ: Real Gunicorn WSGI request environment.
    :param start_response: Actual server response callback.
    :return: Unmodified original response iterable.
    :raises AssertionError: Staff acceptance precedes the required Reviewed proof.
    """
    if (
        environ.get("REQUEST_METHOD") == "POST"
        and environ.get("PATH_INFO") == f"/pips/{_baseline['pip_id']}/admin-review/"
    ):
        assert (fixture._ROOT / "saga-summary-reviewed.json").exists()
    previous = (
        fixture.domain_rows()["sessions.session"]
        if environ.get("PATH_INFO") in {"/auth/user/login/", "/auth/user/logout/"}
        else None
    )
    response = _django_application(environ, start_response)
    try:
        yield from response
    finally:
        if hasattr(response, "close"):
            response.close()
        observe(environ, previous)


def verify_loaded_worker() -> None:
    """Run the unchanged complete ORM/mail oracle without duplicate Django memory.

    :return: None only after the existing original effects and mail checks pass.
    :raises Exception: Any exact scope, browser, data, session or mail check fails.
    """
    with _lock:
        verify()


_verification_worker = start_server(
    fixture._ROOT,
    json.loads(Path("/runtime/run.json").read_text())["nonce"],
    verify_loaded_worker,
)
