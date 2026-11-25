"""Real on-idle Chromium readiness capture, not a Saga/UAT acceptance verdict."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from time import monotonic
from typing import Any

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Route,
    expect,
    sync_playwright,
)

from contract import allow_browser_request, validate_source_files

_ORIGIN = "https://cedar-web:8443"
_OUTPUT = Path("/output")
_VIEWPORTS = (
    (1280, 800),
    (1920, 1080),
    (1512, 982),
    (768, 1024),
    (1024, 768),
    (390, 844),
    (360, 800),
)


def loaded_fonts(page: Page) -> list[str]:
    """Read actual browser font readiness; never inject a replacement stylesheet.

    :param page: Actual candidate page, e.g. the guest Design leaderboard.
    :return: Sorted loaded font family names.
    """
    return page.evaluate("""async () => {
        await document.fonts.ready;
        return [...new Set([...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replaceAll('"','')))].sort();
    }""")


def capture(page: Page, path: str, case: str) -> dict[str, Any]:
    """Retain a real capture and at most one actual external-font recapture.

    :param page: Actual Chromium page with a real network/viewport.
    :param path: Exact owned public route.
    :param case: Caller-constructed portable acquisition name.
    :return: Real matching HTTP/font/geometry observation.
    :raises AssertionError: Real HTTP, font or viewport checks fail.
    """
    for attempt in (1, 2):
        response = page.goto(_ORIGIN + path, wait_until="networkidle")
        assert response is not None and response.status == 200
        assert page.url == _ORIGIN + path and page.evaluate("window.isSecureContext")
        assert_public_body(page)
        fonts = loaded_fonts(page)
        observation = capture_observation(page, path, case, attempt, fonts)
        assert observation["document_width"] == page.viewport_size["width"]
        if "Montserrat" in fonts and "Font Awesome 6 Pro" in fonts:
            return observation
    raise AssertionError("Actual external fonts did not load; acquisitions retained.")


def assert_public_body(page: Page) -> None:
    """Reject known private sentinels in the real rendered guest document.

    :param page: Actual anonymous list/profile/copy surface.
    :return: None when no fictional private fixture sentinel appears in HTML.
    :raises AssertionError: Private evidence appears anywhere in the response DOM.
    """
    document = page.content()
    for sentinel in (
        "Cedar Bid Pricing",
        "Internal staffing notes for Cedar",
        "DEMO_ONLY_NOT_A_REAL_TOKEN",
    ):
        assert sentinel not in document


def capture_observation(
    page: Page, path: str, case: str, attempt: int, fonts: list[str]
) -> dict[str, Any]:
    """Save the actual source pixels and associated rendered-browser measurements.

    :param page: Actual candidate page.
    :param path: Observed route.
    :param case: Portable case name.
    :param attempt: Actual acquisition number.
    :param fonts: Actual browser-reported loaded families.
    :return: Original screenshot and geometry declaration.
    """
    name = f"{case}-attempt-{attempt}"
    screenshot = f"screenshots/{name}.png"
    page.screenshot(path=str(_OUTPUT / screenshot), full_page=True)
    row = {
        "case": case,
        "route": path,
        "viewport": page.viewport_size,
        "document_width": page.evaluate("document.documentElement.scrollWidth"),
        "fonts": fonts,
        "screenshot": screenshot,
        "secure_context": True,
    }
    write_json(f"{name}.json", row)
    return row


def write_json(name: str, payload: dict[str, Any]) -> None:
    """Write one original safe acquisition/readiness record.

    :param name: Fixed portable filename.
    :param payload: Actual observation metadata without credentials.
    :return: None after the record exists.
    """
    (_OUTPUT / name).write_text(json.dumps(payload, indent=2) + "\n")


def capture_guest(context: BrowserContext) -> list[dict[str, Any]]:
    """Browse fourteen real guest list/profile views at the seven IA sizes.

    :param context: Fresh anonymous context on the actual candidate.
    :return: Fourteen actual source/font/geometry observations.
    :raises AssertionError: A genuine public affordance or required capture fails.
    """
    page, rows = context.new_page(), []
    for width, height in _VIEWPORTS:
        page.set_viewport_size({"width": width, "height": height})
        rows.append(
            capture(page, "/experts/?category=design", f"guest-list-{width}-{height}")
        )
        assert_design_names(page)
        rows.append(
            capture(page, "/experts/mrodriguez/", f"guest-profile-{width}-{height}")
        )
        expect(
            page.get_by_role("heading", name="Maria Rodriguez", exact=True)
        ).to_be_visible()
        assert not page.locator('a[href^="mailto:"]').count()
    return rows


def assert_design_names(page: Page) -> None:
    """Require the actual canonical five ordered Design contributor names.

    :param page: Genuine Design leaderboard.
    :return: None after exact article-container order matches Cedar.
    :raises AssertionError: An actual name/card/order differs.
    """
    names = (
        page.locator("article").get_by_test_id("expert-card-name").all_text_contents()
    )
    assert names == [
        "Sofia Reed",
        "Maria Rodriguez",
        "Priya Nair",
        "Daniel Ortiz",
        "Hana Kim",
    ]


def real_guest_clipboard(context: BrowserContext) -> dict[str, Any]:
    """Prove genuine secure-context clipboard completion with no guest receipt.

    :param context: Fresh anonymous context on the owned HTTPS origin.
    :return: Exact public prompt digest/length and real no-receipt observation.
    :raises AssertionError: Clipboard, HTTP, network or secure-context checks fail.
    """
    oracle = json.loads((_OUTPUT / "public-copy.json").read_text())
    context.grant_permissions(["clipboard-read", "clipboard-write"], origin=_ORIGIN)
    page, receipts = context.new_page(), []
    observe_receipts(page, receipts)
    response = page.goto(_ORIGIN + oracle["path"])
    assert response is not None and response.status == 200
    prepare_real_clipboard(page)
    page.get_by_test_id("activity-header-actions").get_by_test_id(
        "copy-prompt-btn"
    ).click()
    expect(page.get_by_test_id("copy-prompt-toast")).to_be_visible()
    copied = page.evaluate("navigator.clipboard.readText()")
    assert hashlib.sha256(copied.encode()).hexdigest() == oracle["sha256"]
    assert len(copied.encode()) == oracle["bytes"] and receipts == []
    page.screenshot(
        path=str(_OUTPUT / "screenshots/guest-native-clipboard.png"), full_page=True
    )
    return {
        "secure_context": True,
        "actual_clipboard_sha256": oracle["sha256"],
        "bytes": oracle["bytes"],
        "guest_receipt_requests": 0,
    }


def observe_receipts(page: Page, receipts: list[str]) -> None:
    """Observe attempted actual receipt traffic without replacing its responses.

    :param page: Actual anonymous copy page.
    :param receipts: Real request URL observations.
    :return: None after the passive request listener is installed.
    """
    page.on(
        "request",
        lambda request: (
            receipts.append(request.url)
            if "consumption-receipts" in request.url or "/karma/copy" in request.url
            else None
        ),
    )


def prepare_real_clipboard(page: Page) -> None:
    """Replace stale clipboard text through the real browser clipboard API.

    :param page: Actual owned HTTPS page with origin-scoped clipboard permission.
    :return: None after actual secure-context and native read/write checks pass.
    :raises AssertionError: Native clipboard access or secure context is absent.
    """
    assert page.evaluate("window.isSecureContext") is True
    page.evaluate("navigator.clipboard.writeText('Cedar readiness clipboard marker')")
    assert (
        page.evaluate("navigator.clipboard.readText()")
        == "Cedar readiness clipboard marker"
    )


def restrict_requests(route: Route, blocked: list[str]) -> None:
    """Continue genuine allowed requests and abort every undeclared destination.

    :param route: Actual intercepted request; no response is ever fabricated.
    :param blocked: Safe destination records for any unexpected request attempt.
    :return: None after continue or abort.
    """
    request = route.request
    if allow_browser_request(request.url, request.method):
        route.continue_()
    else:
        blocked.append(request.method + " " + request.url.split("?", 1)[0])
        route.abort("blockedbyclient")


def main() -> None:
    """Check actual browser-image bytes and run genuine bounded readiness.

    :return: None for core readiness only; no full Saga/UAT verdict is produced.
    :raises Exception: Actual TLS/browser/font/clipboard failure propagates.
    """
    source = json.loads(Path("/runtime/source.json").read_text())
    validate_source_files(Path("/app"), source["files"])
    identity = json.loads(Path("/runtime/browser-identity.json").read_text())
    (_OUTPUT / "screenshots").mkdir(exist_ok=True)
    with sync_playwright() as engine:
        browser = engine.chromium.launch(
            args=[
                "--ignore-certificate-errors-spki-list="
                + identity["certificate_spki_sha256_base64"]
            ]
        )
        try:
            run_readiness(browser)
        finally:
            browser.close()


def run_readiness(browser: Browser) -> None:
    """Retain actual trace/video even when the real smoke path fails.

    :param browser: Actual Chromium process on the idle host.
    :return: None after genuine core readiness observations are saved.
    :raises Exception: Actual readiness errors are retained and re-raised."""
    context = browser.new_context(
        ignore_https_errors=False,
        service_workers="block",
        record_video_dir=str(_OUTPUT / "video"),
        record_video_size={"width": 1280, "height": 720},
    )
    blocked: list[str] = []
    context.route("**/*", lambda route: restrict_requests(route, blocked))
    context.tracing.start(screenshots=False, snapshots=True, sources=True)
    try:
        perform_readiness(context, browser.version, blocked, monotonic())
    except Exception as error:
        write_json(
            "browser-failure.json",
            {
                "status": "FAILED",
                "exception_class": type(error).__name__,
                "undeclared_requests": blocked,
            },
        )
        raise
    finally:
        context.tracing.stop(path=str(_OUTPUT / "browser-trace.zip"))
        context.close()


def perform_readiness(
    context: BrowserContext, version: str, blocked: list[str], started: float
) -> None:
    """Run actual source/clipboard observations and clearly label their scope.

    :param context: Real anonymous browser context.
    :param version: Actual Chromium version.
    :param blocked: Recorded undeclared-destination attempts.
    :param started: Real monotonic operator-run start time.
    :return: None after a SMOKE_ONLY_UAT_PENDING record exists.
    :raises AssertionError: Any real browser observation differs.
    """
    rows = capture_guest(context)
    clipboard = real_guest_clipboard(context)
    assert blocked == []
    result = {
        "status": "SMOKE_ONLY_UAT_PENDING",
        "operator": "automated_on_idle_Chromium",
        "elapsed_seconds": monotonic() - started,
        "browser": version,
        "captures": rows,
        "clipboard": clipboard,
        "tls_trust": "only_owned_certificate_public_key",
        "full_uat_contracts_passed": 0,
        "undeclared_requests": blocked,
    }
    write_json("browser-readiness.json", result)


if __name__ == "__main__":
    main()
