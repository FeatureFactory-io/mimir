"""Literal C01–C05 native browser actions, separate from companion ORM proof."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Locator,
    Page,
    Response,
    Route,
    expect,
)

import saga_browser as shared
from saga_summary_contract import CASE, allow_summary_request

_ORIGIN = "https://cedar-web:8443"
_OUTPUT = Path("/output")


def timestamp() -> str:
    """Return actual UTC at full precision for native action envelopes.

    :return: Full microsecond aware UTC timestamp.
    """
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def own_profile(
    page: Page, pip_points: int, design_points: int, paragraph: str
) -> Locator:
    """Read exact live Maria totals and the cached paragraph through the real profile.

    :param page: Actual Maria session.
    :param pip_points: Expected accepted-change subtotal.
    :param design_points: Expected Design subtotal.
    :param paragraph: Exact expected public prose.
    :return: Real own-profile region.
    :raises AssertionError: A current total, category, source or prose differs.
    """
    shared.document(page, "/auth/user/profile/")
    profile = page.get_by_test_id("profile-page")
    expect(profile.get_by_test_id("profile-karma-total")).to_have_text(
        f"{design_points+1000:,}"
    )
    expect(profile.get_by_test_id("profile-primary-category")).to_have_text("Design")
    sources = profile.get_by_test_id("profile-karma-source-breakdown")
    expect(sources.get_by_role("rowheader")).to_have_text(
        ["Released", "PIP", "Consumption", "Learning", "Total"]
    )
    assert [
        int(value.replace(",", ""))
        for value in sources.get_by_role("cell").all_inner_texts()
    ] == [5000, pip_points, 1200, 400, design_points + 1000]
    categories(
        profile.get_by_test_id("profile-karma-category-breakdown"), design_points
    )
    expect(profile.get_by_test_id("profile-contribution-summary")).to_have_text(
        paragraph
    )
    shared.account_controls(profile)
    return profile


def categories(region: Locator, design: int) -> None:
    """Check exact visible Design/Development entries.

    :param region: Actual profile category breakdown.
    :param design: Expected Design amount.
    :return: None after both labels and amounts match.
    """
    expect(region).to_be_visible()
    expect(region.get_by_role("term")).to_have_text(["Design", "Development"])
    assert [
        int(value.replace(",", ""))
        for value in region.get_by_role("definition").all_inner_texts()
    ] == [design, 1000]


def observe_post(page: Page, path: str, action: Any) -> dict[str, Any]:
    """Capture actual native action-start to matching HTTP POST-response bounds.

    :param page: Real browser displaying a native form.
    :param path: Exact prepared route.
    :param action: Actual native control click, never an API mutation.
    :return: Body-free precise metadata for the real POST/302.
    """
    observation = {"method": "POST", "path": path}

    def matching(response: Response) -> bool:
        if response.url != _ORIGIN + path or response.request.method != "POST":
            return False
        observation.update(completed_at=timestamp(), status=response.status)
        return True

    with page.expect_response(matching) as response:
        observation["started_at"] = timestamp()
        action()
    assert response.value.status == 302
    shared.capture_private_values(page)
    return observation


def submit(page: Page, oracle: dict[str, Any]) -> dict[str, Any]:
    """Submit the actual prepared Draft and wait for the normal asynchronous review.

    :param page: Real Maria browser.
    :param oracle: Safe prepared routes and public paragraph.
    :return: Actual native submission POST envelope after Reviewed without acceptance.
    :raises AssertionError: The real submission, processing or assessment differs.
    """
    shared.document(page, oracle["detail_path"])
    expect(page.get_by_test_id("pip-detail-title")).to_contain_text(
        "Screen Reader Error Recovery"
    )
    expect(page.get_by_test_id("pip-detail-header")).to_contain_text(
        "Accessible Forms Review v2.0"
    )
    expect(page.get_by_test_id("pip-status-badge")).to_have_text("Draft")
    submission = observe_post(
        page, oracle["submit_path"], page.get_by_test_id("pip-detail-submit").click
    )
    for _ in range(60):
        page.reload(wait_until="networkidle")
        if page.get_by_test_id("pip-status-badge").inner_text() == "Reviewed":
            break
        page.wait_for_timeout(250)
    expect(page.get_by_test_id("pip-status-badge")).to_have_text("Reviewed")
    expect(page.get_by_test_id("galdr-reason-1")).to_contain_text(
        "The proposed activity fits the review workflow."
    )
    expect(page.get_by_test_id("admin-verdict-1")).to_have_count(0)
    expect(page.get_by_test_id("pip-admin-review")).to_have_count(0)
    expect(page.get_by_test_id("pip-detail-submit")).to_have_count(0)
    shared.snapshot(page, CASE, "C03-reviewed", public=False)
    own_profile(page, 1600, 7200, oracle["public_summary"])
    shared.snapshot(page, CASE, "C03-refreshed-8200", public=False)
    return submission


def sign_out(page: Page) -> None:
    """Sign out via the existing native menu and verify no identity remains.

    :param page: Actual signed-in browser.
    :return: None after the actual session deletion/navigation.
    """
    page.get_by_test_id("user-display").click()
    page.get_by_test_id("logout-link").click()
    expect(page.get_by_test_id("login-link")).to_be_visible()
    expect(page.get_by_test_id("user-display")).to_have_count(0)
    shared.settle(page)


def finalize(page: Page, oracle: dict[str, Any]) -> dict[str, Any]:
    """Use Mike's native Accept and confirmation form, with no domain writes here.

    :param page: Actual separate staff session.
    :param oracle: Prepared proposal routes.
    :return: Actual finalization POST/302 envelope.
    """
    shared.document(page, oracle["detail_path"])
    expect(page.get_by_test_id("user-display")).to_have_text("mchen")
    page.get_by_test_id("pip-admin-review").click()
    expect(page).to_have_url(_ORIGIN + oracle["review_path"])
    expect(page.get_by_test_id("admin-review-header")).to_contain_text("v2.0")
    decision, button = page.get_by_test_id("admin-decision-1"), page.get_by_test_id(
        "finalize-btn"
    )
    expect(decision).to_have_value("")
    expect(button).to_be_disabled()
    decision.select_option("ACCEPT")
    expect(page.get_by_test_id("accepted-count")).to_have_text("1")
    expect(page.get_by_test_id("pending-count")).to_have_text("0")
    expect(button).to_be_enabled()
    button.click()
    return confirm(page, oracle, decision)


def confirm(page: Page, oracle: dict[str, Any], decision: Locator) -> dict[str, Any]:
    """Confirm the real major-version decision after checking the native dialog.

    :param page: Actual staff form.
    :param oracle: Prepared native route.
    :param decision: Actual native decision select.
    :return: Real matching response metadata.
    """
    modal = page.get_by_test_id("finalize-confirm-modal")
    expect(modal).to_be_visible()
    expect(modal.get_by_role("heading")).to_have_text("Confirm Finalize")
    expect(modal).to_contain_text("You are accepting 1 of 1 changes.")
    expect(modal).to_contain_text("will be updated to a new major version.")
    expect(decision).to_have_accessible_name("Decision for change 1")
    expect(modal).to_have_accessible_name("Confirm Finalize")
    expect(modal.get_by_role("button", name="Close", exact=True)).to_be_visible()
    shared.snapshot(page, CASE, "C04-confirm", public=False)
    result = observe_post(
        page, oracle["review_path"], modal.get_by_test_id("confirm-finalize-btn").click
    )
    expect(page).to_have_url(_ORIGIN + oracle["detail_path"])
    expect(page.get_by_test_id("pip-status-badge")).to_have_text("Accepted")
    expect(page.get_by_test_id("pip-detail-header")).to_contain_text("v3.0")
    expect(page.get_by_test_id("admin-verdict-1")).to_have_text("ADMIN ACCEPT")
    expect(page.get_by_test_id("alert-message")).to_contain_text(
        "PIP accepted — changes applied."
    )
    shared.snapshot(page, CASE, "C04-accepted", public=False)
    return result


def revisit(page: Page, oracle: dict[str, Any]) -> None:
    """Read the decided form and public current totals with stable refreshed prose.

    :param page: Actual staff browser following acceptance.
    :param oracle: Safe native routes and cached public prose.
    :return: None after no second finalization and public 8700/7700/1000.
    """
    shared.document(page, oracle["review_path"])
    expect(page.get_by_test_id("already-decided-banner")).to_be_visible()
    expect(page.get_by_test_id("admin-review-header")).to_contain_text("v3.0")
    expect(page.get_by_test_id("admin-decision-1")).to_have_value("ACCEPT")
    expect(page.get_by_test_id("admin-decision-1")).to_be_disabled()
    expect(page.get_by_test_id("finalize-btn")).to_have_count(0)
    shared.document(page, "/experts/mrodriguez/")
    expect(page.get_by_test_id("expert-name")).to_have_text("Maria Rodriguez")
    expect(page.get_by_test_id("expert-karma-total")).to_have_text("8,700")
    expect(page.get_by_test_id("expert-contribution-summary")).to_have_text(
        oracle["public_summary"]
    )
    categories(page.get_by_test_id("karma-category-breakdown"), 7700)
    shared.snapshot(page, CASE, "C05-public-8700")


def perform(context: BrowserContext, oracle: dict[str, Any]) -> None:
    """Execute every literal C-step through real forms and original network traffic.

    :param context: Fresh HTTPS Chromium context.
    :param oracle: Safe positively owned fixture expectations.
    :return: None after a browser-only receipt, not an ORM acceptance claim.
    """
    page = context.new_page()
    writes: list[dict[str, str]] = []
    page.on(
        "request",
        lambda request: (
            writes.append(
                {"method": request.method, "path": urlsplit(request.url).path}
            )
            if request.method not in {"GET", "HEAD"}
            else None
        ),
    )
    logins = [shared.sign_in(page, "mrodriguez")]
    profile = own_profile(page, 1600, 7200, oracle["initial_summary"])
    shared.snapshot(page, CASE, "C01-own-8200", public=False)
    shared.own_keyboard(page, profile)
    shared.snapshot(page, CASE, "C02-keyboard-preview", public=False)
    submission = submit(page, oracle)
    sign_out(page)
    logins.append(shared.sign_in(page, "mchen"))
    finalization = finalize(page, oracle)
    revisit(page, oracle)
    sign_out(page)
    logins.append(shared.sign_in(page, "mrodriguez"))
    own_profile(page, 2100, 7700, oracle["public_summary"])
    shared.snapshot(page, CASE, "C05-own-8700", public=False)
    assert context.pages == [page]
    record_observation(oracle, writes, logins, finalization, submission)


def record_observation(
    oracle: dict[str, Any],
    writes: list[dict[str, str]],
    logins: list[dict[str, Any]],
    finalization: dict[str, Any],
    submission: dict[str, Any],
) -> None:
    """Require exact native nonread traffic and retain only acquired browser facts.

    :param oracle: Prepared safe source and route identities.
    :param writes: Actual original POST observations.
    :param logins: Actual Maria/Mike/Maria action-response envelopes.
    :param finalization: Actual native decision-response envelope.
    :param submission: Actual native submission-response envelope.
    :return: None after exclusive safe browser receipt.
    """
    assert writes == [
        {"method": "POST", "path": path}
        for path in [
            "/auth/user/login/",
            oracle["submit_path"],
            "/auth/user/login/",
            oracle["review_path"],
            "/auth/user/login/",
        ]
    ]
    shared.write_result(
        "saga-summary-browser.json",
        {
            "case": CASE,
            "status": "BROWSER_OBSERVED",
            "completed_steps": ["C01", "C02", "C03", "C04", "C05"],
            "login_observations": logins,
            "finalization": finalization,
            "submission": submission,
            "nonread_requests": writes,
            "fixture_sha256": oracle["fixture_sha256"],
        },
    )


def restrict(route: Route, oracle: dict[str, Any], blocked: list[str]) -> None:
    """Continue original declared traffic and abort any undeclared destination/write.

    :param route: Real browser route.
    :param oracle: Prepared proposal identity.
    :param blocked: Safe body-free blocked method/path facts.
    :return: None after real request continuation or abort.
    """
    request = route.request
    if allow_summary_request(request.url, request.method, oracle["pip_id"]):
        route.continue_()
    else:
        blocked.append(request.method + " " + urlsplit(request.url).path)
        route.abort("blockedbyclient")


def run_summary_case(browser: Browser) -> None:
    """Acquire only this literal lane with original private trace and safe derivative.

    :param browser: Real Chromium trusting only the owned HTTPS certificate SPKI.
    :return: None after actual acquisition; independent ORM verifier follows.
    :raises Exception: Original browser failure retained privately and propagated.
    """
    oracle = json.loads((_OUTPUT / "saga-summary-oracle.json").read_text())
    assert oracle["case"] == CASE
    shared._OUTPUT = _OUTPUT
    (_OUTPUT / "screenshots").mkdir(exist_ok=True)
    context = browser.new_context(
        ignore_https_errors=False,
        service_workers="block",
        viewport={"width": 1280, "height": 800},
        record_video_dir=str(_OUTPUT / "video"),
        record_video_size={"width": 1280, "height": 800},
    )
    binding = shared.start_private_capture()
    success = False
    try:
        capture(context, oracle)
        success = True
    finally:
        try:
            context.close()
            shared.finish_evidence(CASE, success)
        finally:
            shared._PRIVATE_VALUES.reset(binding)


def capture(context: BrowserContext, oracle: dict[str, Any]) -> None:
    """Retain real trace even on failure without publishing private original bytes.

    :param context: Actual secure browser context.
    :param oracle: Safe preparation record.
    :return: None after every action and closed-network check.
    """
    context.tracing.start(screenshots=False, snapshots=True, sources=True)
    blocked: list[str] = []
    context.route("**/*", lambda route: restrict(route, oracle, blocked))
    try:
        perform(context, oracle)
        assert not blocked
    except Exception as error:
        shared.write_result(
            "saga-summary-failure.json",
            {
                "case": CASE,
                "status": "FAILED",
                "exception_class": type(error).__name__,
                "undeclared_requests": blocked,
            },
        )
        raise
    finally:
        original = _OUTPUT / "private/saga-trace-original.zip"
        context.tracing.stop(path=str(original))
        os.chmod(original, 0o600)
