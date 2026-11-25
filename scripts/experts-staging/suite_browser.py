"""Actual image-bound browser dispatch for each independently owned suite case."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, Route, sync_playwright

import browser as core
import saga_browser as shared
from contract import allow_browser_request, validate_source_files
from saga_guest import VIEWPORTS, GuestOracle, run_guest
from saga_guest_responsive import run_elena_matrix
from saga_summary_browser import run_summary_case
from saga_visual_browser import run_visual_case
from suite_contract import selected_case
from suite_guest_trace import finish_guest, original_path

_OUTPUT = Path("/output")
_ORIGIN = "https://cedar-web:8443"


def dispatch(browser: Browser, case: str) -> None:
    """Select only one true native browser lane.

    :param browser: Real Chromium trusting exactly the owned SPKI.
    :param case: Closed validated true case ID.
    :return: None after the actual recording completes.
    :raises ValueError: Unknown lane; original native failures propagate.
    """
    if case == "core":
        core.run_readiness(browser)
    elif case in {"nomination", "copy-maria", "copy-guest", "copy-self"}:
        shared.run_case(browser, case)
    elif case in {"guest-public", "authenticated-matrix"}:
        run_readonly(browser, case)
    elif case in {"long_identity_and_prose", "missing_summary"}:
        run_visual_case(browser, case, _OUTPUT)
    elif case == "summary-acceptance":
        run_summary_case(browser)
    else:
        raise ValueError("Closed implemented browser case required.")


def restrict(route: Route, case: str, blocked: list[str]) -> None:
    """Allow actual public reads and only the matrix actor's native login POST.

    :param route: Original native browser request.
    :param case: True readonly case.
    :param blocked: Private request observations, never exported as URLs.
    :return: None after continuing or aborting the original request.
    """
    request = route.request
    allowed = allow_browser_request(request.url, request.method)
    login = (
        case == "authenticated-matrix"
        and request.method == "POST"
        and request.url == _ORIGIN + "/auth/user/login/"
    )
    if allowed or login:
        route.continue_()
    else:
        blocked.append(request.method + " " + request.url)
        route.abort("blockedbyclient")


def _oracle(record: dict[str, Any]) -> GuestOracle:
    """Build exact public expectations with private disclosure probes in memory.

    :param record: Owned prepared public readonly oracle.
    :return: Immutable guest/matrix oracle.
    """
    fixture = json.loads(shared._FIXTURE.read_text())
    values = []
    for person in fixture["people"]:
        values.extend(person.get("private_playbooks", []))
        values.extend(
            person[key] for key in ("private_token", "private_pip") if person.get(key)
        )
    return GuestOracle(
        record["source_revision"],
        record["fixture_sha256"],
        record["summary"],
        record["workflow_path"],
        tuple(values),
    )


def _observe_readonly(context: BrowserContext, case: str) -> None:
    """Acquire both normal matrices with actual guest or Elena identity.

    :param context: Actual fresh secure context.
    :param case: True readonly case.
    :return: None after exact seven-size observations.
    :raises AssertionError: Native traffic, actors, pixels or observations differ.
    """
    record = json.loads((_OUTPUT / "suite-readonly-oracle.json").read_text())
    assert record["case"] == case
    oracle, page, blocked = _oracle(record), context.new_page(), []
    context.route("**/*", lambda route: restrict(route, case, blocked))
    login = (
        shared.sign_in(page, "esvensson") if case == "authenticated-matrix" else None
    )
    if case == "authenticated-matrix":
        result = run_elena_matrix(page, _ORIGIN, _OUTPUT / "screenshots", oracle)
    else:
        result = _guest_matrix(page, oracle)
    assert not blocked
    if case == "authenticated-matrix":
        assert context.pages == [page]
        shared.capture_private_values(page)
    else:
        assert not context.pages
    shared.write_result(
        "suite-readonly-browser.json", _readonly_record(case, record, result, login)
    )


def _readonly_record(
    case: str, oracle: dict[str, Any], observed: Any, login: dict[str, Any] | None
) -> dict[str, Any]:
    """Retain actual seven-size observations and exact source/fixture/actor evidence.

    :param case: True readonly case.
    :param oracle: Exact prepared source/fixture identity.
    :param observed: Actual completed guest results or authenticated screen pairs.
    :param login: Actual native safe login envelope or None.
    :return: Safe actual browser observation awaiting39model verification.
    """
    rows = observed if case == "guest-public" else observed["screen_pairs"]
    viewports = [row["viewport"] for row in rows]
    return {
        "case": case,
        "status": "BROWSER_OBSERVED",
        "viewport_count": len(viewports),
        "viewports": viewports,
        "completed_steps": (
            ["G01", "G02", "G03", "G04"] if case == "guest-public" else []
        ),
        "login_observation": login,
        "fixture_sha256": oracle["fixture_sha256"],
        "source_revision": oracle["source_revision"],
        "observations": observed,
        "full_saga_accepted": False,
    }


def _guest_matrix(page: Page, oracle: GuestOracle) -> list[dict[str, Any]]:
    """Run literal G01–G04 independently at every actual IA size.

    :param page: Genuine anonymous page; cookies must remain absent.
    :param oracle: Actual pristine public expectations.
    :return: Seven actual native outcomes.
    """
    rows, context = [], page.context
    for index, (width, height) in enumerate(VIEWPORTS):
        if index:
            assert not context.pages
            context.tracing.start_chunk()
            page = context.new_page()
        assert context.pages == [page]
        try:
            rows.append(_guest_viewport(page, oracle, width, height))
        finally:
            try:
                context.tracing.stop_chunk(
                    path=str(original_path(_OUTPUT, width, height))
                )
            finally:
                page.close()
    return rows


def _guest_viewport(
    page: Page, oracle: GuestOracle, width: int, height: int
) -> dict[str, Any]:
    """Acquire the complete independent journey before releasing its renderer.

    :param page: Sole actual anonymous page in the unchanged recording context.
    :param oracle: Original pristine public expectations.
    :param width: Exact reviewed IA width.
    :param height: Exact reviewed IA height.
    :return: Actual unchanged G01–G04 outcome and all native acquisitions.
    :raises Exception: Every original browser/action/capture assertion propagates.
    """
    page.set_viewport_size({"width": width, "height": height})
    destination = _OUTPUT / "screenshots" / f"guest-{width}-{height}"
    destination.mkdir(mode=0o700)
    row = run_guest(page, _ORIGIN, destination, oracle, native_viewport_captures=True)
    shared.capture_private_values(page)
    return row


def run_readonly(browser: Browser, case: str) -> None:
    """Capture real private originals and publish only scanned derivatives.

    :param browser: Actual pinned Chromium.
    :param case: True guest/matrix lane.
    :return: None after actual trace/video closure.
    :raises Exception: Original browser assertion preserved on any failure.
    """
    shared._OUTPUT = _OUTPUT
    (_OUTPUT / "screenshots").mkdir(mode=0o700)
    context = browser.new_context(
        ignore_https_errors=False,
        service_workers="block",
        viewport={"width": 1280, "height": 800},
        record_video_dir=str(_OUTPUT / "video"),
        record_video_size={"width": 1280, "height": 800},
    )
    binding = shared.start_private_capture()
    success = False
    context.tracing.start(screenshots=False, snapshots=True, sources=True)
    try:
        _observe_readonly(context, case)
        success = True
    finally:
        if case == "guest-public":
            context.tracing.stop()
        else:
            context.tracing.stop(path=str(_OUTPUT / "private/saga-trace-original.zip"))
        context.close()
        try:
            if case == "guest-public":
                finish_guest(_OUTPUT, success)
            else:
                shared.finish_evidence(case, success)
        finally:
            shared._PRIVATE_VALUES.reset(binding)


def main() -> None:
    """Validate actual image/source then launch genuine private pinned HTTPS.

    :return: None after actual browser lane completion.
    :raises Exception: Source, TLS, native browser or contract failure propagates.
    """
    manifest = json.loads(Path("/runtime/run.json").read_text())
    case = selected_case(manifest).case
    source = json.loads(Path("/runtime/source.json").read_text())
    validate_source_files(Path("/app"), source["files"])
    identity = json.loads(Path("/runtime/browser-identity.json").read_text())
    with sync_playwright() as engine:
        browser = engine.chromium.launch(
            args=[
                "--ignore-certificate-errors-spki-list="
                + identity["certificate_spki_sha256_base64"]
            ]
        )
        try:
            dispatch(browser, case)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
