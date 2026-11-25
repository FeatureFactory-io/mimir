"""Literal browser-only Saga actions on the identified owned HTTPS companion.

This module never starts a local Django server, replaces an HTTP response,
sets a product state through an API, or activates a contact destination.
"""

from __future__ import annotations

import hashlib
import json
import os
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Locator,
    Page,
    Request,
    Response,
    Route,
    expect,
)

from browser import assert_public_body, loaded_fonts
from saga_contract import (
    ACTORS,
    allow_saga_request,
    validate_case,
    validate_copy_attempts,
)
from saga_trace import redact_trace

_ORIGIN = "https://cedar-web:8443"
_OUTPUT = Path("/output")
_FIXTURE = Path("/app/test-data/experts/cedar-rfp-01.json")
_PASSWORD = "Cedar-fictional-tests-only-2026"
_PRIVATE_VALUES: ContextVar[set[str] | None] = ContextVar(
    "saga_private_values", default=None
)
_DESIGN = "/experts/?category=design"
_MARIA = "/experts/mrodriguez/"
_AUDIT = "/playbooks/6101/"
_CONTACT = "mailto:maria.rodriguez@example.com"
_ACTIVITIES = (
    "Trace Keyboard Focus",
    "Review Form Feedback",
    "Document Recovery Paths",
)
_RANKS = (
    ("sreed", "Sofia Reed", "15,400"),
    ("mrodriguez", "Maria Rodriguez", "8,200"),
    ("pnair", "Priya Nair", "7,600"),
    ("dortiz", "Daniel Ortiz", "6,900"),
    ("hkim", "Hana Kim", "5,800"),
)


def document(page: Page, path: str) -> None:
    """Open an actual same-origin document and require a direct HTTP200 GET.

    :param page: Real controlled browser page.
    :param path: Actual expected route, e.g. /experts/.
    :return: None after genuine successful navigation and font readiness.
    :raises AssertionError: HTTP, route, method or secure context differs.
    """
    response = page.goto(_ORIGIN + path)
    assert response is not None and response.status == 200
    assert response.request.method == "GET" and response.request.redirected_from is None
    expect(page).to_have_url(_ORIGIN + path)
    settle(page)


def settle(page: Page) -> None:
    """Settle actual fonts and ordinary first-visit consent using its real button.

    :param page: Actual loaded candidate document.
    :return: None when fonts and the visible consent dismissal are complete.
    :raises AssertionError: The page is insecure or the real dismissal fails.
    """
    assert page.evaluate("window.isSecureContext") is True
    dismiss = page.get_by_role("button", name="Not now", exact=True)
    if dismiss.is_visible():
        dismiss.click()
        expect(dismiss).to_be_hidden()
    page.wait_for_load_state("networkidle")
    page.evaluate("() => document.fonts.ready")
    capture_private_values(page)


def follow(page: Page, link: Locator, path: str) -> None:
    """Follow a rendered anchor while checking its actual document response.

    :param page: Actual current document.
    :param link: Actual visible native anchor.
    :param path: Exact expected href, e.g. /experts/mrodriguez/.
    :return: None after the real link reaches the direct200 destination.
    :raises AssertionError: Link, response, method, redirect or URL differs.
    """
    expect(link).to_have_attribute("href", path)
    with page.expect_navigation() as navigation:
        link.click()
    response = navigation.value
    assert response is not None and response.status == 200
    assert response.url == _ORIGIN + path and response.request.method == "GET"
    assert response.request.redirected_from is None
    expect(page).to_have_url(_ORIGIN + path)
    settle(page)


def back(page: Page, path: str) -> None:
    """Use native history and require the exact restored destination.

    :param page: Actual browser after following a public evidence link.
    :param path: Previous route including its category query.
    :return: None when a real or cached successful document is restored.
    :raises AssertionError: Actual history route or response differs.
    """
    response = page.go_back()
    if response is not None:
        assert response.status == 200 and response.request.method == "GET"
        assert response.url == _ORIGIN + path
    expect(page).to_have_url(_ORIGIN + path)
    settle(page)


def snapshot(page: Page, case: str, step: str, public: bool = True) -> None:
    """Retain real rendered pixels and exact native font/viewport metadata.

    :param page: Actual current browser document.
    :param case: Implemented case used for a portable artifact name.
    :param step: Fixed source-controlled step identifier.
    :param public: Whether the page must exclude private account values.
    :return: None after original pixels and actual measurements are saved.
    :raises AssertionError: Privacy, fonts or actual viewport geometry differs.
    """
    if public:
        assert_public_body(page)
    for attempt in (1, 2):
        fonts = loaded_fonts(page)
        snapshot_actual(page, case, f"{step}-attempt-{attempt}", fonts)
        if "Montserrat" in fonts and "Font Awesome 6 Pro" in fonts:
            return
        if attempt == 1:
            page.reload(wait_until="networkidle")
            settle(page)
    raise AssertionError(
        "Actual external fonts did not load; original acquisitions retained."
    )


def snapshot_actual(page: Page, case: str, step: str, fonts: list[str]) -> None:
    """Retain original screenshot bytes before deciding whether fonts passed.

    :param page: Actual current page.
    :param case: Implemented lane.
    :param step: Exact source-controlled step and actual acquisition number.
    :param fonts: Actual loaded font families from this acquisition.
    :return: None after original image and safe measurements exist.
    :raises AssertionError: Actual document overflows the current viewport.
    """
    width = page.viewport_size["width"]
    assert page.evaluate("document.documentElement.scrollWidth") == width
    name = f"saga-{case}-{step}"
    prepare_capture(page)
    page.screenshot(
        path=str(_OUTPUT / "screenshots" / f"{name}.png"),
        full_page=True,
        mask=[page.get_by_test_id("profile-token-field")],
    )
    if step.startswith("C04-confirm"):
        snapshot_modal_viewport(page, case, name)
    write_result(
        f"{name}.json",
        {
            "case": case,
            "step": step,
            "path": urlsplit(page.url).path,
            "viewport": page.viewport_size,
            "fonts": fonts,
            "secure_context": True,
            "capture_kind": "full_document",
            "modal_viewport_acquired": step.startswith("C04-confirm"),
        },
    )


def prepare_capture(page: Page) -> None:
    """Wait for actual finite animations and position the native document capture.

    :param page: Real rendered current state; no DOM or style mutation.
    :return: None after animations settle and native scroll reaches top.
    :raises TimeoutError: The genuine rendered state does not settle.
    """
    page.wait_for_function(
        "!document.getAnimations().some(a => a.playState === 'running' && a.effect?.getTiming().iterations !== Infinity)"
    )
    page.mouse.move(page.viewport_size["width"] / 2, page.viewport_size["height"] / 2)
    page.mouse.wheel(0, -100000)
    page.wait_for_function("scrollY===0")


def snapshot_modal_viewport(page: Page, case: str, name: str) -> None:
    """Acquire the actual settled modal viewport alongside its document capture.

    :param page: Actual open native modal, without scroll or style replacement.
    :param case: True summary case.
    :param name: Fixed source-owned screenshot stem.
    :return: None after original viewport PNG and explicit geometry metadata.
    """
    page.screenshot(
        path=str(_OUTPUT / "screenshots" / f"{name}-viewport.png"),
        full_page=False,
        mask=[page.get_by_test_id("profile-token-field")],
    )
    write_result(
        f"{name}-viewport.json",
        {
            "case": case,
            "viewport": page.viewport_size,
            "capture_kind": "native_viewport",
            "secure_context": True,
            "modal_viewport_acquired": True,
        },
    )


def write_result(name: str, record: dict[str, Any]) -> None:
    """Write one newly acquired safe case observation without replacing evidence.

    :param name: Fixed portable output filename from this module.
    :param record: Actual observations excluding passwords and private model bodies.
    :return: None after an exclusive public evidence file is created.
    :raises FileExistsError: A prior acquisition uses this filename.
    """
    with (_OUTPUT / name).open("x") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")


def sign_in(page: Page, username: str) -> dict[str, Any]:
    """Use the ordinary rendered form, genuine CSRF and actual session lifecycle.

    :param page: Fresh real browser page on the owned origin.
    :param username: Explicit fictional Cedar actor, e.g. esvensson.
    :return: Safe actual POST/302 UTC bounds and a session-cookie digest.
    :raises AssertionError: Form response or resulting actor is incorrect.
    """
    document(page, "/auth/user/login/")
    assert not any(
        cookie["name"] == "sessionid" for cookie in page.context.cookies([_ORIGIN])
    )
    expect(page.locator('input[name="password"]')).to_have_attribute("type", "password")
    page.locator('input[name="username"]').fill(username)
    page.locator('input[name="password"]').fill(_PASSWORD)
    observed: dict[str, Any] = {"actor": username}
    with page.expect_response(partial(observe_login_response, observed)) as response:
        observed["started_at"] = datetime.now(timezone.utc).isoformat(
            timespec="microseconds"
        )
        page.locator('button[type="submit"]').click()
    assert response.value.status == 302
    expect(page).not_to_have_url(_ORIGIN + "/auth/user/login/")
    expect(page.get_by_test_id("user-display")).to_have_text(username)
    settle(page)
    observed["session_key_sha256"] = actual_session_digest(page)
    return observed


def observe_login_response(observed: dict[str, Any], response: Response) -> bool:
    """Record the actual response event time without changing its native delivery.

    :param observed: Safe mutable metadata for this exact actual login action.
    :param response: Actual unmodified HTTP response event.
    :return: Whether this is the same-origin normal login POST response.
    """
    if (
        response.url != _ORIGIN + "/auth/user/login/"
        or response.request.method != "POST"
    ):
        return False
    observed.update(
        completed_at=datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        method="POST",
        path="/auth/user/login/",
        status=response.status,
    )
    return True


def actual_session_digest(page: Page) -> str:
    """Hash the actual normal login cookie without exporting its private value.

    :param page: Actual signed-in browser after native POST/302 completion.
    :return: SHA256 of the one origin-scoped session cookie.
    :raises AssertionError: The ordinary session cookie is absent or ambiguous.
    """
    cookies = [
        cookie
        for cookie in page.context.cookies([_ORIGIN])
        if cookie["name"] == "sessionid"
    ]
    assert len(cookies) == 1 and cookies[0]["secure"] is True
    return hashlib.sha256(cookies[0]["value"].encode()).hexdigest()


def assert_design(page: Page) -> None:
    """Read all five actual ranked Design cards and both available actions.

    :param page: Real Design leaderboard.
    :return: None after ordered identities, ranks, totals and exclusions agree.
    :raises AssertionError: A displayed contributor or action differs.
    """
    expect(page.get_by_test_id("experts-category-design")).to_have_attribute(
        "aria-current", "page"
    )
    cards = page.get_by_test_id("experts-leaderboard").get_by_role("article")
    expect(cards).to_have_count(5)
    for index, (username, name, points) in enumerate(_RANKS):
        card = cards.nth(index)
        expect(card).to_have_attribute("data-testid", f"experts-card-{username}")
        expect(card.get_by_role("heading", name=name, exact=True)).to_be_visible()
        expect(card.get_by_test_id("expert-card-rank")).to_have_text(str(index + 1))
        expect(card.get_by_test_id("expert-card-karma")).to_have_text(points)
        expect(
            card.get_by_role("link", name="View profile", exact=True)
        ).to_have_attribute("href", f"/experts/{username}/")
    for username in ("mchen", "tmartin"):
        expect(page.get_by_test_id(f"experts-card-{username}")).to_have_count(0)


def profile_summary(page: Page, username: str, oracle: dict[str, Any]) -> str:
    """Read the complete public paragraph against the independently loaded oracle.

    :param page: Actual public expert detail reached by a real anchor.
    :param username: sreed or mrodriguez.
    :param oracle: Safe exact baseline route and public-summary record.
    :return: The actual full paragraph read from the page.
    :raises AssertionError: Text, visibility or unclamped layout differs.
    """
    summary = page.get_by_test_id("expert-contribution-summary")
    expect(summary).to_be_visible()
    expect(summary).to_have_css("-webkit-line-clamp", "none")
    actual = summary.inner_text()
    assert actual and actual == oracle["public_summaries"][username]
    assert_public_body(page)
    return actual


def open_ranked_profile(page: Page, username: str) -> None:
    """Follow the selected contributor's own View profile action.

    :param page: Actual Design leaderboard.
    :param username: Actual target username from the five displayed cards.
    :return: None after the correct public profile loads.
    :raises AssertionError: The action or its actual response differs.
    """
    card = page.get_by_test_id(f"experts-card-{username}")
    follow(
        page,
        card.get_by_test_id(f"experts-view-profile-{username}"),
        f"/experts/{username}/",
    )


def maria_breakdown(page: Page, total: int = 8200, development: int = 1000) -> None:
    """Reconcile actual public source and category rows with the displayed total.

    :param page: Actual Maria public detail.
    :param total: Expected total, e.g. 8200 or 8205 after a real copy.
    :param development: Exact Development amount, e.g. 1000 or 1005.
    :return: None after every baseline or expected-delta row agrees.
    :raises AssertionError: A source, subtotal, category or total differs.
    """
    expect(page.get_by_test_id("expert-karma-total")).to_have_text(f"{total:,}")
    expect(page.get_by_test_id("expert-primary-category")).to_have_text("Design")
    source = page.get_by_test_id("karma-source-breakdown")
    expect(source.locator("tbody").get_by_role("rowheader")).to_have_text(
        ["Released playbooks", "PIP contributions", "Consumption", "Learning"]
    )
    expect(source.locator("tbody").get_by_role("cell")).to_have_text(
        ["5,000", "1,600", "1,200", f"{400 + total - 8200:,}"]
    )
    expect(source.locator("tfoot").get_by_role("cell")).to_have_text(f"{total:,}")
    expect(
        page.get_by_test_id("karma-category-breakdown").locator("dt, dd")
    ).to_have_text(["Design", "7,200", "Development", f"{development:,}"])


def inspect_evidence(page: Page, oracle: dict[str, Any]) -> tuple[str, ...]:
    """Follow the actual public release and inspect its genuine workflow graph.

    :param page: Actual Maria public profile.
    :param oracle: Actual fixture-derived public workflow path.
    :return: Three actual on-screen labels; raises AssertionError on any mismatch.
    """
    follow(page, page.get_by_test_id("expert-playbook-6101"), _AUDIT)
    header = page.get_by_test_id("playbook-header")
    expect(
        header.get_by_role("heading", name="Accessibility Audit Playbook", exact=True)
    ).to_be_visible()
    expect(header.get_by_test_id("version-badge")).to_have_text("v1.0")
    expect(header.get_by_test_id("visibility-badge")).to_have_text("Public")
    expect(header.get_by_test_id("status-badge")).to_have_text("Released")
    snapshot(page, "nomination", "E06-public-release")
    link = page.get_by_test_id("workflows-section").get_by_role(
        "link", name="Lead an Accessibility Review", exact=True
    )
    follow(page, link, oracle["workflow_path"])
    graph = page.get_by_test_id("activities-graph").locator("svg")
    expect(graph).to_be_visible()
    for name in _ACTIVITIES:
        label = graph.get_by_text(name, exact=True)
        label.scroll_into_view_if_needed()
        expect(label).to_be_in_viewport(ratio=1)
    snapshot(page, "nomination", "E06-workflow")
    return tuple(
        graph.get_by_text(name, exact=True).text_content() for name in _ACTIVITIES
    )


def perform_nomination(page: Page, oracle: dict[str, Any]) -> dict[str, Any]:
    """Execute literal E01–E08 through public evidence and an unsent handoff.

    :param page: Actual Elena browser after normal sign-in.
    :param oracle: Positively owned baseline's safe public oracle.
    :return: Observed external nomination and measured automated operator time.
    :raises AssertionError: A literal route, rank, evidence or handoff differs.
    """
    sidebar = page.get_by_test_id("app-sidebar").get_by_role(
        "list", name="Collaborate", exact=True
    )
    link = sidebar.get_by_role("link", name="Experts", exact=True)
    expect(link).to_be_visible()
    started = monotonic()
    follow(page, link, "/experts/")
    expect(page.get_by_test_id("experts-category-development")).to_have_attribute(
        "aria-current", "page"
    )
    follow(page, page.get_by_test_id("experts-category-design"), _DESIGN)
    assert_design(page)
    snapshot(page, "nomination", "E02-design")
    review_sofia(page, oracle)
    back(page, _DESIGN)
    assert_design(page)
    open_ranked_profile(page, "mrodriguez")
    profile_summary(page, "mrodriguez", oracle)
    maria_breakdown(page)
    snapshot(page, "nomination", "E04-maria")
    activities = inspect_evidence(page, oracle)
    return nomination_handoff(page, activities, started)


def review_sofia(page: Page, oracle: dict[str, Any]) -> None:
    """Read the leading contributor's actual service and operations evidence.

    :param page: Actual Design leaderboard.
    :param oracle: Independently prepared exact public paragraph.
    :return: None after Sofia's full paragraph and public examples are read.
    :raises AssertionError: Identity, full text or released examples differ.
    """
    open_ranked_profile(page, "sreed")
    expect(page.get_by_role("heading", name="Sofia Reed", exact=True)).to_be_visible()
    prose = profile_summary(page, "sreed", oracle)
    assert (
        "service boundaries, operating models, and cross-team design coordination"
        in prose
    )
    evidence = page.get_by_test_id("expert-public-playbooks")
    for title in (
        "Service Blueprinting for Complex Portfolios",
        "Design Operations Governance",
    ):
        expect(evidence.get_by_role("heading", name=title, exact=True)).to_be_visible()
        link = evidence.get_by_role("link", name=f"View {title}", exact=True)
        link.scroll_into_view_if_needed()
        expect(link).to_be_in_viewport(ratio=1)
    snapshot(page, "nomination", "E03-sofia")


def nomination_handoff(
    page: Page, activities: tuple[str, ...], started: float
) -> dict[str, Any]:
    """Inspect the genuine contact link and derive the external nomination note.

    :param page: Actual Accessibility Audit workflow after reading its examples.
    :param activities: Three exact rendered activity labels.
    :param started: Actual monotonic timer started at Experts navigation.
    :return: Scripted operator note with availability unconfirmed; no mail sent.
    :raises AssertionError: History, actor, identity or unsent destination differs.
    """
    back(page, _AUDIT)
    back(page, _MARIA)
    expect(page.get_by_test_id("user-display")).to_have_text("esvensson")
    name = page.get_by_role("heading", name="Maria Rodriguez", exact=True).inner_text()
    contact = page.get_by_role("toolbar", name="Expert contact").get_by_role(
        "link", name="Reach out", exact=True
    )
    contact.scroll_into_view_if_needed()
    contact_geometry = assert_contact_reachable(contact)
    expect(contact).to_have_attribute("href", _CONTACT)
    destination = contact.get_attribute("href")
    snapshot(page, "nomination", "E07-unsent-contact")
    result = nomination_record(name, activities, destination, monotonic() - started)
    result["contact_geometry_css_pixels"] = contact_geometry
    return result


def assert_contact_reachable(contact: Locator) -> dict[str, Any]:
    """Check native actionability and real bounds with the established1px tolerance.

    :param contact: Actual unsent Reach out anchor, never activated.
    :return: Actual measured CSS bounds for evidence of subpixel clipping tolerance.
    :raises AssertionError: A meaningful edge is outside or its center is covered.
    """
    contact.click(trial=True)
    geometry = contact.evaluate("""control => {
        const b = control.getBoundingClientRect();
        return {left:b.left, right:b.right, top:b.top, bottom:b.bottom,
            viewport_width:innerWidth, viewport_height:innerHeight,
            center_uncovered:control.contains(document.elementFromPoint(
                b.left+b.width/2,b.top+b.height/2))};
    }""")
    assert geometry["left"] >= -1 and geometry["top"] >= -1
    assert geometry["right"] <= geometry["viewport_width"] + 1
    assert geometry["bottom"] <= geometry["viewport_height"] + 1
    assert geometry["center_uncovered"] is True
    return geometry


def nomination_record(
    name: str, activities: tuple[str, ...], destination: str, elapsed: float
) -> dict[str, Any]:
    """Write a scripted external note from the actual observed public examples.

    :param name: Actual observed contributor identity.
    :param activities: Actual read workflow labels.
    :param destination: Inspected unsent contact URI.
    :param elapsed: Actual automated operator seconds, never human task time.
    :return: Derived note, exact observed destination and honest timer result.
    """
    note = (
        f"I nominate {name} for a discussion about Noor's Cedar bank onboarding brief. "
        f"Her Accessibility Audit Playbook v1.0 includes {', '.join(activities)}. "
        "These public examples address keyboard navigation, understandable form errors and recovery. "
        "Next step is to request a discussion. Availability is unconfirmed."
    )
    return {
        "nomination_text": note,
        "inspected_contact_destination": destination,
        "elapsed_monotonic_seconds": elapsed,
        "proposed_target_seconds": 300,
        "automated_path_within_proposed_target": elapsed <= 300,
        "contact_activated": False,
        "email_sent": False,
    }


def observe_requests(
    page: Page, receipts: list[dict[str, Any]], writes: list[dict[str, str]]
) -> None:
    """Passively observe writes and permitted receipt facts without request secrets.

    :param page: Actual browser page before login or document actions.
    :param receipts: Actual receipt metadata, never authorization values.
    :param writes: Actual nonread method and local path observations.
    :return: None after the observer is installed.
    """

    page.on("request", partial(observe_write, receipts, writes))


def observe_write(
    receipts: list[dict[str, Any]], writes: list[dict[str, str]], request: Request
) -> None:
    """Capture safe actual request facts without passwords, cookies or CSRF values.

    :param receipts: Safe actual receipt facts.
    :param writes: Actual nonread method/path facts.
    :param request: Real emitted browser request.
    :return: None after the safe observation is appended.
    """
    parsed = urlsplit(request.url)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        writes.append({"method": request.method, "path": parsed.path})
    if "consumption-receipts" in parsed.path or "/karma/copy" in parsed.path:
        receipts.append(
            {
                "method": request.method,
                "path": parsed.path,
                "payload": request.post_data_json,
                "csrf": bool(request.header_value("x-csrftoken")),
            }
        )


def perform_copy(page: Page, case: str, oracle: dict[str, Any]) -> dict[str, Any]:
    """Execute the actual native clipboard action and public numeric observations.

    :param page: Real page after optional normal actor sign-in.
    :param case: copy-maria, copy-guest or copy-self.
    :param oracle: Real server-built public prompt digest and route.
    :return: Actual clipboard SHA/length and observed response status.
    :raises AssertionError: Native clipboard, feedback, HTTP or public totals differ.
    """
    if case == "copy-maria":
        own_summary(page, oracle, 8200)
    document(page, oracle["copy_path"])
    assert_copy_surface(page, case, oracle)
    page.context.grant_permissions(
        ["clipboard-read", "clipboard-write"], origin=_ORIGIN
    )
    page.evaluate("navigator.clipboard.writeText('Cedar Saga native clipboard marker')")
    assert (
        page.evaluate("navigator.clipboard.readText()")
        == "Cedar Saga native clipboard marker"
    )
    button = page.get_by_test_id("activity-header-actions").get_by_test_id(
        "copy-prompt-btn"
    )
    response_body = click_copy(button, case)
    result = assert_clipboard(page, case, oracle)
    inspect_copy_totals(page, case)
    if case == "copy-maria":
        own_summary(page, oracle, 8205)
    return {**result, "receipt_response": response_body}


def own_summary(page: Page, oracle: dict[str, Any], total: int) -> None:
    """Exercise the literal own-profile/source/keyboard/stable-prose journey.

    :param page: Actual signed-in Maria browser before or after copying.
    :param oracle: Original complete public paragraph.
    :param total: Exact expected baseline or post-copy total.
    :return: None after real account controls, expansion and source reconciliation.
    :raises AssertionError: Numeric, text, keyboard or retained controls differ.
    """
    document(page, "/auth/user/profile/")
    profile = page.get_by_test_id("profile-page")
    expect(page.get_by_test_id("user-display")).to_have_text("mrodriguez")
    expect(profile.get_by_test_id("profile-karma-total")).to_have_text(f"{total:,}")
    expect(profile.get_by_test_id("profile-primary-category")).to_have_text("Design")
    expect(profile.get_by_test_id("profile-contribution-summary")).to_have_text(
        oracle["public_summaries"]["mrodriguez"]
    )
    own_sources(profile, total)
    account_controls(profile)
    own_keyboard(page, profile)
    snapshot(page, "copy-maria", f"own-summary-{total}", public=False)


def own_sources(profile: Locator, total: int) -> None:
    """Reconcile all four real source rows and both category subtotals.

    :param profile: Actual Maria own-profile region.
    :param total: Expected8200 or8205 from this one real copy.
    :return: None when every displayed source and category agrees.
    :raises AssertionError: Any numeric reconciliation differs.
    """
    sources = profile.get_by_test_id("profile-karma-source-breakdown")
    expect(sources.get_by_role("rowheader")).to_have_text(
        ["Released", "PIP", "Consumption", "Learning", "Total"]
    )
    amounts = sources.get_by_role("cell").all_inner_texts()
    assert [int(value.replace(",", "")) for value in amounts] == [
        5000,
        1600,
        1200,
        400 + total - 8200,
        total,
    ]
    categories = profile.get_by_test_id("profile-karma-category-breakdown")
    expect(categories.get_by_role("term")).to_have_text(["Design", "Development"])
    amounts = categories.get_by_role("definition").all_inner_texts()
    assert [int(value.replace(",", "")) for value in amounts] == [
        7200,
        1000 + total - 8200,
    ]


def account_controls(profile: Locator) -> None:
    """Require retained native account controls without exposing or copying tokens.

    :param profile: Actual own-profile region.
    :return: None when private token stays masked and existing controls remain usable.
    :raises AssertionError: Masking, editing or retained account sections differ.
    """
    expect(profile.get_by_test_id("profile-token-field")).to_have_attribute(
        "type", "password"
    )
    expect(profile.get_by_test_id("profile-edit-btn")).to_have_attribute(
        "href", "/auth/user/profile/edit/"
    )
    password = profile.get_by_test_id("profile-token-regenerate-password")
    expect(password).to_be_editable()
    expect(password).to_have_attribute("required", "")
    for name in (
        "profile-edit-btn",
        "profile-token-toggle",
        "profile-token-copy",
        "profile-token-regenerate-submit",
    ):
        profile.get_by_test_id(name).click(trial=True)
    for name in (
        "profile-pips-table",
        "profile-playbooks-table",
        "profile-teams-section",
    ):
        expect(profile.get_by_test_id(name)).to_be_visible()


def own_keyboard(page: Page, profile: Locator) -> None:
    """Use native Tab, Enter and Space through the real summary expansion control.

    :param page: Actual Maria browser at her own profile.
    :param profile: Existing own-profile region.
    :return: None after full expansion and restored four-line preview.
    :raises AssertionError: Native focus order, accessible state or clipping differs.
    """
    summary = profile.get_by_test_id("profile-contribution-summary")
    toggle = profile.get_by_test_id("profile-summary-toggle")
    own_preview(summary, toggle, False)
    assistant = profile.get_by_role("link", name="Configure your AI Assistant")
    for _ in range(
        page.locator("a[href],button,input,select,textarea,[tabindex]").count()
    ):
        page.keyboard.press("Tab")
        if assistant.evaluate("link => document.activeElement === link"):
            page.keyboard.press("Tab")
            break
    expect(toggle).to_be_focused()
    page.keyboard.press("Enter")
    own_preview(summary, toggle, True)
    expect(toggle).to_be_focused()
    page.keyboard.press("Space")
    own_preview(summary, toggle, False)
    expect(toggle).to_be_focused()


def own_preview(summary: Locator, toggle: Locator, expanded: bool) -> None:
    """Check the actual accessible label, relationship and rendered preview bounds.

    :param summary: Actual retained full paragraph region.
    :param toggle: Actual native summary button.
    :param expanded: Expected accessible and visual state.
    :return: None after native full/preview geometry and state agree.
    :raises AssertionError: Semantic controls or visible line geometry differs.
    """
    expect(toggle).to_have_js_property("tagName", "BUTTON")
    expect(toggle).to_have_attribute("aria-expanded", str(expanded).lower())
    expect(toggle).to_have_accessible_name("Show less" if expanded else "Show more")
    expect(toggle).to_have_attribute("aria-controls", summary.get_attribute("id"))
    expect(toggle).to_have_accessible_description(
        "Show or hide the full contribution summary"
    )
    geometry = summary.evaluate(
        """element => { const s=getComputedStyle(element),b=element.getBoundingClientRect();
        return {height:b.height,line_height:parseFloat(s.lineHeight),clamp:s.webkitLineClamp,
            overflow:s.overflowY,client:element.clientHeight,scroll:element.scrollHeight}; }"""
    )
    assert geometry["line_height"] > 0 and geometry["height"] > 0
    assert geometry["clamp"] == ("none" if expanded else "4")
    if expanded:
        assert geometry["client"] + 1 >= geometry["scroll"]
    else:
        assert geometry["height"] <= 4 * geometry["line_height"] + 1
        assert (
            geometry["overflow"] == "hidden" and geometry["scroll"] > geometry["client"]
        )


def click_copy(button: Locator, case: str) -> dict[str, Any] | None:
    """Click the genuine native control and observe its exact real receipt.

    :param button: Real visible Copy Prompt button.
    :param case: Independently owned actor lane.
    :return: Actual receipt response or None for anonymous copy.
    :raises AssertionError: Native HTTP status or receipt outcome differs.
    """
    if case == "copy-guest":
        button.click()
        return None
    with button.page.expect_response(is_copy_response) as response:
        button.click()
    assert response.value.status == 200
    body = response.value.json()
    assert body == (
        {"status": "applied"}
        if case == "copy-maria"
        else {"status": "skipped", "reason": "self_consumption"}
    )
    return body


def is_copy_response(response: Response) -> bool:
    """Identify only the real same-origin POST response for the native GUI receipt.

    :param response: Real Playwright HTTP response.
    :return: Whether exact owned endpoint and method match.
    """
    return (
        response.url == _ORIGIN + "/karma/copy-receipts/"
        and response.request.method == "POST"
    )


def assert_copy_surface(page: Page, case: str, oracle: dict[str, Any]) -> None:
    """Check actual public navigation and actor-specific existing affordances.

    :param page: Real activity6203 document before native copying.
    :param case: Explicit actor lane with independent baseline.
    :param oracle: Actual imported activity/workflow names and public route.
    :return: None after title, breadcrumbs, identity and guest controls agree.
    :raises AssertionError: Content, navigation, actor or guest edit policy differs.
    """
    expect(page.get_by_test_id("activity-title")).to_have_text(
        oracle["copy_activity_name"]
    )
    expect(page.get_by_test_id("activity-back-btn")).to_have_attribute(
        "href", "/playbooks/6201/workflows/6202/activities/"
    )
    links = page.get_by_role("navigation", name="breadcrumb").get_by_role(
        "link", name=oracle["copy_workflow_name"], exact=True
    )
    assert links.evaluate_all(
        "links => links.map(link => link.getAttribute('href'))"
    ) == ["/playbooks/6201/", "/playbooks/6201/workflows/6202/"]
    actor = ACTORS[case]
    if actor is not None:
        expect(page.get_by_test_id("user-display")).to_have_text(actor)
        expect(page.get_by_test_id("guest-auth-banner")).to_have_count(0)
    else:
        assert_guest_surface(page, oracle["copy_path"])


def assert_guest_surface(page: Page, path: str) -> None:
    """Require public reading with sign-in/register and no editing affordance.

    :param page: Actual anonymous activity page.
    :param path: Actual public activity route.
    :return: None after exact guest navigation controls are observed.
    :raises AssertionError: Guest identity, edit policy or navigation differs.
    """
    expect(page.get_by_test_id("user-display")).to_have_count(0)
    expect(page.get_by_test_id("guest-auth-banner")).to_be_visible()
    expect(page.get_by_test_id("edit-btn")).to_have_count(0)
    expect(page.get_by_test_id("guest-banner-register")).to_have_attribute(
        "href", "/auth/user/register/"
    )
    target = urlsplit(
        page.get_by_test_id("guest-banner-sign-in").get_attribute("href") or ""
    )
    assert target.path == "/auth/user/login/" and parse_qs(target.query) == {
        "next": [path]
    }


def assert_clipboard(page: Page, case: str, oracle: dict[str, Any]) -> dict[str, Any]:
    """Read actual native clipboard bytes, feedback and full feedback interval.

    :param page: Actual activity page immediately after its native Copy action.
    :param case: Explicit independently owned copy lane.
    :param oracle: Real service-generated exact prompt SHA and byte length.
    :return: Actual byte length and SHA; clipboard content is not logged.
    :raises AssertionError: Clipboard, secure context or ordinary feedback differs.
    """
    toast = page.get_by_test_id("copy-prompt-toast")
    expect(toast).to_be_visible()
    expect(toast).to_have_text("Prompt copied to clipboard")
    copied = page.evaluate("navigator.clipboard.readText()")
    digest = hashlib.sha256(copied.encode()).hexdigest()
    assert (
        digest == oracle["copy_sha256"] and len(copied.encode()) == oracle["copy_bytes"]
    )
    expect(page.get_by_test_id("copy-prompt-error-toast")).to_be_hidden()
    expect(
        page.get_by_test_id("alert-message").filter(has_text="You earned")
    ).to_have_count(0)
    snapshot(page, case, "native-clipboard")
    expect(toast).to_be_hidden()
    return {
        "actual_clipboard_sha256": digest,
        "actual_clipboard_bytes": len(copied.encode()),
        "secure_context": True,
    }


def inspect_copy_totals(page: Page, case: str) -> None:
    """Read the actual Maria and Mike public profiles after this one copy.

    :param page: Actual browser after ordinary copy feedback.
    :param case: Explicit lane determining whether the legitimate pair is eligible.
    :return: None after exact totals, categories, fallback count and public link agree.
    :raises AssertionError: Any visible post-copy projection differs.
    """
    eligible = case == "copy-maria"
    document(page, _MARIA)
    maria_breakdown(page, 8205 if eligible else 8200, 1005 if eligible else 1000)
    snapshot(page, case, "maria-after")
    document(page, "/experts/mchen/")
    expect(page.get_by_test_id("expert-karma-total")).to_have_text(
        "12,455" if eligible else "12,450"
    )
    expect(
        page.get_by_test_id("karma-category-breakdown").locator("dt, dd")
    ).to_have_text(["Development", "12,455" if eligible else "12,450"])
    expect(page.get_by_test_id("expert-numeric-fallback")).to_have_text(
        f"2 released playbooks · {48 if eligible else 47} copies"
    )
    expect(page.get_by_test_id("expert-playbook-6201")).to_have_attribute(
        "href", "/playbooks/6201/"
    )
    snapshot(page, case, "mike-after")


def run_case(browser: Browser, case: str) -> None:
    """Run only an implemented literal case in its own real browser context.

    :param browser: Real Chromium launched with only the owned certificate SPKI pin.
    :param case: Explicit implemented lane; there is no full-Saga default.
    :return: None after observations, actual trace and video are retained.
    :raises Exception: Any genuine browser/assertion failure is retained then raised.
    """
    validate_case(case)
    oracle = json.loads((_OUTPUT / "saga-oracle.json").read_text())
    assert oracle["case"] == case
    (_OUTPUT / "screenshots").mkdir(exist_ok=True)
    context = browser.new_context(
        ignore_https_errors=False,
        service_workers="block",
        viewport={"width": 1280, "height": 800},
        record_video_dir=str(_OUTPUT / "video"),
        record_video_size={"width": 1280, "height": 800},
    )
    run_context(context, case, oracle)


def run_context(context: BrowserContext, case: str, oracle: dict[str, Any]) -> None:
    """Close real recording before publishing only its verified safe derivative.

    :param context: Owned real browser context, already service-worker restricted.
    :param case: Implemented explicit lane.
    :param oracle: Actual safe baseline oracle.
    :return: None after safe evidence; propagates every actual acquisition failure.
    """
    binding = start_private_capture()
    successful = False
    try:
        capture_case(context, case, oracle)
        successful = True
    finally:
        try:
            context.close()
            finish_evidence(case, successful)
        finally:
            _PRIVATE_VALUES.reset(binding)


def start_private_capture() -> Token:
    """Collect only in-memory secrets and allocate a non-exported original folder.

    :return: Context binding reset by the exact invocation's owner.
    :raises FileExistsError: A previous private acquisition already exists.
    """
    private = _OUTPUT / "private"
    private.mkdir(mode=0o700)
    values = {_PASSWORD}
    fixture = json.loads(_FIXTURE.read_text())
    for person in fixture["people"]:
        values.update(person.get("private_playbooks", []))
        values.update(
            person[key] for key in ("private_token", "private_pip") if person.get(key)
        )
    return _PRIVATE_VALUES.set(values)


def capture_private_values(page: Page) -> None:
    """Capture actual rotating CSRF/session and masked token values without logging.

    :param page: Actual loaded document before native actions.
    :return: None; values remain in memory until ZIP sanitization completes.
    """
    values = _PRIVATE_VALUES.get()
    if values is None:
        return
    values.update(
        cookie["value"]
        for cookie in page.context.cookies()
        if len(cookie["value"]) >= 8
    )
    fields = page.locator(
        'input[name="csrfmiddlewaretoken"], [data-testid="profile-token-field"]'
    )
    values.update(
        value
        for value in fields.evaluate_all("fields => fields.map(field => field.value)")
        if isinstance(value, str) and len(value) >= 8
    )


def finish_evidence(case: str, successful: bool) -> None:
    """Keep failed media private and publish only a fully scanned successful trace.

    :param case: Actual explicit lane.
    :param successful: Whether all actual browser assertions completed.
    :return: None after safe publication or private failure quarantine.
    :raises ValueError: Trace sanitization cannot prove safe public bytes.
    """
    write_result(
        "private/captured-secrets.json",
        {"values": sorted(_PRIVATE_VALUES.get() or set())},
    )
    if not successful:
        quarantine_media()
        return
    try:
        result = redact_trace(
            _OUTPUT / "private/saga-trace-original.zip",
            _OUTPUT / "saga-trace.zip",
            _PRIVATE_VALUES.get() or set(),
        )
        result["original_retention"] = "private_until_verified_owned_cleanup"
        write_result("saga-trace-provenance.json", result)
    except Exception:
        quarantine_media()
        raise


def quarantine_media() -> None:
    """Hold failed native media privately so an unsafe account screen cannot export.

    :return: None after only this case's existing media subtrees move privately.
    :raises OSError: An exact-owned acquisition cannot be retained safely.
    """
    for name in ("screenshots", "video"):
        source = _OUTPUT / name
        if source.exists():
            source.rename(_OUTPUT / "private" / name)


def capture_case(context: BrowserContext, case: str, oracle: dict[str, Any]) -> None:
    """Retain real trace and safe failure facts while preserving original errors.

    :param context: Real secure context with service workers blocked by its caller.
    :param case: Implemented lane name.
    :param oracle: Actual positively owned public baseline metadata.
    :return: None after browser observations; raises the original acquisition error.
    """
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    blocked: list[str] = []
    context.route("**/*", lambda route: restrict_case(route, case, blocked))
    try:
        perform_case(context, case, oracle, blocked)
    except Exception as error:
        write_result(
            "saga-failure.json",
            {
                "case": case,
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


def restrict_case(route: Route, case: str, blocked: list[str]) -> None:
    """Continue genuine declared requests and abort every other destination/write.

    :param route: Actual Playwright route, never a fabricated response.
    :param case: Implemented lane-specific write allowlist.
    :param blocked: Safe method/destination observations.
    :return: None after the original request continues or aborts.
    """
    request = route.request
    if allow_saga_request(case, request.url, request.method):
        route.continue_()
    else:
        blocked.append(request.method + " " + request.url.split("?", 1)[0])
        route.abort("blockedbyclient")


def perform_case(
    context: BrowserContext, case: str, oracle: dict[str, Any], blocked: list[str]
) -> None:
    """Observe one actual case and distinguish browser work from effect verification.

    :param context: Fresh independent real Chromium context.
    :param case: Explicit implemented lane.
    :param oracle: Exact owned baseline's safe public oracle.
    :param blocked: Recorded unexpected real requests.
    :return: None after BROWSER_OBSERVED; this is not yet CASE_VERIFIED or full Saga.
    :raises AssertionError: Any required action, network, context or observation differs.
    """
    page = context.new_page()
    receipts: list[dict[str, Any]] = []
    writes: list[dict[str, str]] = []
    observe_requests(page, receipts, writes)
    actor = ACTORS[case]
    login = sign_in(page, actor) if actor is not None else None
    observed = (
        perform_nomination(page, oracle)
        if case == "nomination"
        else perform_copy(page, case, oracle)
    )
    observed["login_observation"] = login
    assert not blocked and context.pages == [page]
    finalize_observation(page, case, oracle, observed, receipts, writes)


def finalize_observation(
    page: Page,
    case: str,
    oracle: dict[str, Any],
    observed: dict[str, Any],
    receipts: list[dict[str, Any]],
    writes: list[dict[str, str]],
) -> None:
    """Verify exact nonread traffic and retain only the actual lane observation.

    :param page: Actual final page.
    :param case: Explicit implemented lane.
    :param oracle: Safe baseline oracle.
    :param observed: Actual browser observations.
    :param receipts: Actual receipt requests.
    :param writes: Actual nonread requests.
    :return: None after exclusive result creation; raises AssertionError on mismatch.
    """
    actor = ACTORS[case]
    expected = (
        [] if actor is None else [{"method": "POST", "path": "/auth/user/login/"}]
    )
    if case in {"copy-maria", "copy-self"}:
        expected.append({"method": "POST", "path": "/karma/copy-receipts/"})
    assert writes == expected
    if case != "nomination":
        validate_copy_attempts(case, receipts)
    record = browser_record(page, case, oracle, observed)
    record.update(receipt_attempts=receipts, nonread_requests=writes)
    write_result("saga-browser.json", record)


def browser_record(
    page: Page, case: str, oracle: dict[str, Any], observed: dict[str, Any]
) -> dict[str, Any]:
    """Label real operator observations without promoting them to full acceptance.

    :param page: Actual final page with measured viewport.
    :param case: Implemented case name.
    :param oracle: Actual source fixture hash.
    :param observed: Actual acquired browser facts.
    :return: Browser-only result awaiting independent database effect verification.
    """
    return {
        "case": case,
        "status": "BROWSER_OBSERVED",
        "operator": "automated_staged_Saga",
        "viewport": page.viewport_size,
        "fixture_sha256": oracle["fixture_sha256"],
        **observed,
    }
