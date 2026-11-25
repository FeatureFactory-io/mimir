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
    assert not blocked and context.pages == [page]
    shared.capture_private_values(page)
    shared.write_result(
        "suite-readonly-browser.json",
        {
            "case": case,
            "status": "BROWSER_OBSERVED",
            "viewport_count": 7,
            "login_observation": login,
            "observations": result,
            "full_saga_accepted": False,
        },
    )


def _guest_matrix(page: Page, oracle: GuestOracle) -> list[dict[str, Any]]:
    """Run literal G01–G04 independently at every actual IA size.

    :param page: Genuine anonymous page; cookies must remain absent.
    :param oracle: Actual pristine public expectations.
    :return: Seven actual native outcomes.
    """
    rows = []
    for width, height in VIEWPORTS:
        page.set_viewport_size({"width": width, "height": height})
        destination = _OUTPUT / "screenshots" / f"guest-{width}-{height}"
        destination.mkdir(mode=0o700)
        rows.append(run_guest(page, _ORIGIN, destination, oracle))
    return rows


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
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    try:
        _observe_readonly(context, case)
        success = True
    finally:
        context.tracing.stop(path=str(_OUTPUT / "private/saga-trace-original.zip"))
        context.close()
        try:
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
