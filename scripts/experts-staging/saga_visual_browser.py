"""Native S04 variant matrix; browser process has no Django imports or DB access."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, Route, expect

import saga_browser as shared
import saga_visual_cards as cards
from browser import loaded_fonts
from saga_visual_contract import (
    FIXTURE_SHA256,
    allow_visual_request,
    expected_contributors,
    source_constants,
    validate_case,
    validate_output,
)

logger = logging.getLogger(__name__)
_ORIGIN = "https://cedar-web:8443"
_SOURCE = Path("/app/tests/e2e/test_expert_cards.py")
_FIXTURE = Path("/app/test-data/experts/cedar-rfp-01.json")


def write_record(output: Path, name: str, record: dict[str, Any]) -> None:
    """Exclusively retain an actual safe observation.

    :param output: Owned evidence root.
    :param name: Fixed module-owned filename.
    :param record: Public safe observation without credentials.
    :return: None after exclusive mode0600 creation.
    :raises OSError: An original acquisition already exists.
    """
    descriptor = os.open(
        output / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w") as stream:
        json.dump(record, stream, indent=2)


def check_oracle(output: Path, case: str) -> dict[str, Any]:
    """Independently rederive all public expectations in the DB-free process.

    :param output: Current owned evidence root.
    :param case: Explicit variant.
    :return: Checked safe independent fixture oracle.
    :raises AssertionError: Source, fixture, ranking or declared preparation differs.
    """
    validate_case(case)
    validate_output(output)
    constants = source_constants(_SOURCE)
    assert hashlib.sha256(_FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA256
    document = json.loads(_FIXTURE.read_text())
    category, rows = expected_contributors(document, case, constants)
    oracle = json.loads((output / "saga-visual-oracle.json").read_text())
    assert oracle["case"] == case and oracle["category"] == category
    assert oracle["contributors"] == rows
    assert oracle["constants"] == json.loads(json.dumps(constants))
    assert cards._LONG_SUMMARY == constants["_LONG_SUMMARY"]
    assert cards._MIKE_FALLBACK == constants["_MIKE_FALLBACK"]
    return oracle


def restrict_request(route: Route, blocked: list[str]) -> None:
    """Continue actual allowed requests and abort every other destination.

    :param route: Actual native request route; responses are never fabricated.
    :param blocked: Safe method-only rejection records, no query secrets.
    :return: None after the original request continues or aborts.
    """
    if allow_visual_request(route.request.url, route.request.method):
        route.continue_()
    else:
        blocked.append(route.request.method)
        route.abort("blockedbyclient")


def observe_viewport(
    page: Page, output: Path, oracle: dict[str, Any], size: list[int]
) -> dict[str, Any]:
    """Check the exact IA recipe and retain actual unmodified original pixels.

    :param page: Actual Elena page after normal login.
    :param output: Private acquisition root.
    :param oracle: Checked independent variant rows.
    :param size: One exact required CSS viewport pair.
    :return: Actual screenshot/hash/font/viewport and computed shell observations.
    :raises AssertionError: Any real IA, identity, action, geometry or font differs.
    """
    page.set_viewport_size({"width": size[0], "height": size[1]})
    people = tuple(cards._Contributor(**row) for row in oracle["contributors"])
    path = "/experts/?category=" + oracle["category"].lower()
    _check_native_list(page, output, oracle, people, path, size)
    shared.capture_private_values(page)
    _assert_public_page(page)
    expect(page.get_by_test_id("user-display")).to_have_text("esvensson")
    _scroll_to_capture_start(page)
    fonts = loaded_fonts(page)
    name = f"visual-{oracle['case']}-{size[0]}-{size[1]}.png"
    target = output / "screenshots" / name
    assert not target.exists()
    page.screenshot(path=str(target), full_page=True)
    row = {
        "viewport": page.viewport_size,
        "screenshot": name,
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "fonts": fonts,
        "path": path,
        "computed_design": measured_shell(page),
        "capture_scroll_y": page.evaluate("scrollY"),
        "ranks": [person.username for person in people],
    }
    write_record(output, name + ".json", row)
    assert "Montserrat" in fonts and "Font Awesome 6 Pro" in fonts
    return row


def _assert_public_page(page: Page) -> None:
    """Reject real fixture-private evidence and account token controls in the DOM.

    :param page: Actual rendered public list after normal Elena authentication.
    :return: None after exact source fixture sentinels and account hooks are absent.
    :raises AssertionError: Any private account or authored evidence is disclosed.
    """
    document = page.content()
    fixture = json.loads(_FIXTURE.read_text())
    for person in fixture["people"]:
        values = list(person.get("private_playbooks", []))
        values.extend(
            person[key] for key in ("private_token", "private_pip") if person.get(key)
        )
        assert not any(value in document for value in values)
    hooks = "[data-testid^='profile-token-'], #profile-api-token, [data-testid='profile-api-token']"
    expect(page.locator(hooks)).to_have_count(0)


def _scroll_to_capture_start(page: Page) -> None:
    """Position the browser viewport after real keyboard checks before acquisition.

    :param page: Real native page after the complete keyboard sequence.
    :return: None once the real title is readable below the native navbar.
    :raises AssertionError: Actual scrolling does not settle or obscures the title.
    """
    page.evaluate("window.scrollTo({top:0,left:0,behavior:'instant'})")
    cards._wait_for_scroll_to_settle(page)
    title = page.get_by_role("heading", name="Experts", exact=True).bounding_box()
    navbar = page.get_by_test_id("realm-navbar").bounding_box()
    assert title is not None and navbar is not None
    assert title["y"] >= navbar["y"] + navbar["height"]


def _check_native_list(
    page: Page,
    output: Path,
    oracle: dict[str, Any],
    people: tuple[cards._Contributor, ...],
    path: str,
    size: list[int],
) -> None:
    """Keep original failed pixels as well as trace when a real assertion fails.

    :param page: Real native Elena page.
    :param output: Owned private acquisition root.
    :param oracle: Independent checked variant.
    :param people: Exact expected ranked contributor values.
    :param path: Required real route.
    :param size: Exact IA viewport.
    :return: None after complete identity, action and computed geometry proof.
    :raises Exception: Original failure after untouched failed pixels are saved.
    """
    try:
        cards._check_list(
            page, _ORIGIN + path, oracle["category"], people, authenticated=True
        )
    except Exception:
        page.screenshot(
            path=str(output / "screenshots" / f"failed-{size[0]}-{size[1]}.png"),
            full_page=True,
        )
        raise


def measured_shell(page: Page) -> dict[str, Any]:
    """Retain actual computed design observations without altering the page.

    :param page: Real checked native variant page.
    :return: Measured body/title/nav and document width facts.
    """
    return page.evaluate("""() => {
        const body=getComputedStyle(document.body), nav=getComputedStyle(document.querySelector('[data-testid=realm-navbar]'));
        const heading=getComputedStyle([...document.querySelectorAll('h1,h2')].find(el=>el.textContent.trim()==='Experts'));
        return {body_font:body.fontFamily,body_size:body.fontSize,title_size:heading.fontSize,title_weight:heading.fontWeight,nav_background:nav.backgroundColor,nav_border:nav.borderBottomColor,document_width:document.documentElement.scrollWidth,viewport_width:innerWidth};
    }""")


def capture_context(
    context: BrowserContext, output: Path, case: str, oracle: dict[str, Any]
) -> dict[str, Any]:
    """Run the actual native form and all seven independently checked screens.

    :param context: New secure service-worker-blocked real browser context.
    :param output: Exact owned acquisition root.
    :param case: Declared variant.
    :param oracle: Independently checked public expectations.
    :return: Actual safe completed browser observation.
    :raises AssertionError: Native actions, requests or expected screens differ.
    """
    blocked: list[str] = []
    context.route("**/*", lambda route: restrict_request(route, blocked))
    page = context.new_page()
    receipts: list[dict[str, Any]] = []
    writes: list[dict[str, str]] = []
    shared.observe_requests(page, receipts, writes)
    login = shared.sign_in(page, "esvensson")
    screens = [
        observe_viewport(page, output, oracle, size)
        for size in oracle["constants"]["VIEWPORTS"]
    ]
    assert writes == [{"method": "POST", "path": "/auth/user/login/"}]
    assert not receipts and not blocked and context.pages == [page]
    return {
        "case": case,
        "status": "BROWSER_OBSERVED",
        "operator": "automated_browser",
        "application_source_revision": oracle["application_source_revision"],
        "s04_source_sha256": oracle["constants"]["source_sha256"],
        "s04_source_blob": oracle["constants"]["source_blob"],
        "fixture_sha256": FIXTURE_SHA256,
        "browser_control_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
        "login_observation": login,
        "screens": screens,
        "nonread_requests": writes,
        "contact_activated": False,
        "full_saga_accepted": False,
    }


def run_visual_case(browser: Browser, case: str, output: Path) -> dict[str, Any]:
    """Observe one real signed-in variant at every required IA viewport.

    :param browser: Real native Chromium instance with exact companion trust.
    :param case: One separately prepared long/missing variant.
    :param output: Existing private run acquisition directory.
    :return: Actual seven-screen metadata and safe login observation.
    :raises AssertionError: Native pixels, DOM, keyboard, fonts or HTTP differ.
    """
    oracle = check_oracle(output, case)
    shared._OUTPUT, shared._FIXTURE = output, _FIXTURE
    (output / "screenshots").mkdir()
    binding = shared.start_private_capture()
    context = _new_context(browser, output)
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    successful = False
    try:
        record = capture_context(context, output, case, oracle)
        write_record(output, "saga-visual-browser.json", record)
        successful = True
        return record
    except Exception as error:
        write_record(
            output,
            "saga-visual-failure.json",
            {"case": case, "status": "FAILED", "exception_class": type(error).__name__},
        )
        raise
    finally:
        context.tracing.stop(path=str(output / "private/saga-trace-original.zip"))
        context.close()
        try:
            _finish_acquisition(output, case, successful)
        finally:
            shared._PRIVATE_VALUES.reset(binding)


def _new_context(browser: Browser, output: Path) -> BrowserContext:
    """Create native media with explicit encoded geometry rather than defaults.

    :param browser: Actual Chromium with the caller's genuine owned SPKI trust.
    :param output: Validated owned mode0700 acquisition root.
    :return: Fresh secure context with native1280x800 recording dimensions.
    """
    return browser.new_context(
        ignore_https_errors=False,
        service_workers="block",
        viewport={"width": 1280, "height": 800},
        record_video_dir=str(output / "video"),
        record_video_size={"width": 1280, "height": 800},
    )


def _finish_acquisition(output: Path, case: str, successful: bool) -> None:
    """Publish a safe trace derivative and exact actual native video identity.

    :param output: Owned original acquisition root after actual context closure.
    :param case: Explicit long/missing variant.
    :param successful: Actual complete seven-size browser result.
    :return: None after failure quarantine or completed media hash publication.
    :raises AssertionError: The expected actual native video is absent or empty.
    """
    shared.finish_evidence(case, successful)
    if successful:
        videos = list((output / "video").glob("*.webm"))
        assert len(videos) == 1 and videos[0].stat().st_size > 0
        video = {
            "case": case,
            "video": videos[0].name,
            "sha256": hashlib.sha256(videos[0].read_bytes()).hexdigest(),
            "record_video_size": {"width": 1280, "height": 800},
            "viewport_policy": "native_seven_size_matrix_scaled_by_browser_into_declared_recording_size",
            "original_native_video": True,
        }
        write_record(output, "saga-visual-video.json", video)
