"""Literal remote-browser guest UAT; the caller owns server, database and tracing."""

from __future__ import annotations

import hashlib
import logging
import math
import os
import re
import stat
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from time import monotonic
from typing import Any, Literal
from urllib.parse import unquote, urlsplit

from playwright.sync_api import Locator, Page, Response, expect

from tests.support.experts_guest_browser import (
    activate_guest_tooltip,
    assert_guest_tooltip_in_viewport,
    guest_contact_wrapper,
    tab_to_guest_control,
)

logger = logging.getLogger(__name__)
VIEWPORTS = (
    (1280, 800),
    (1920, 1080),
    (1512, 982),
    (768, 1024),
    (1024, 768),
    (390, 844),
    (360, 800),
)
_DESIGN = (
    ("sreed", "Sofia Reed", "15,400"),
    ("mrodriguez", "Maria Rodriguez", "8,200"),
    ("pnair", "Priya Nair", "7,600"),
    ("dortiz", "Daniel Ortiz", "6,900"),
    ("hkim", "Hana Kim", "5,800"),
)
_EXPLANATION = "You need to be logged in to reach out to the expert"
_OTHER = "No experts in Other yet — release a playbook to be the first"
_DETAIL = "/experts/mrodriguez/"
_DESIGN_PATH = "/experts/?category=design"
_MD_WIDTH = 768
_TOLERANCE = 1.0
_PRIVATE_HOOKS = (
    "profile-api-token",
    "profile-token-",
    "profile-karma-card",
    "profile-contribution-summary",
    "nav-view-profile",
    "user-display",
    "navbar-user-menu",
    "notification-bell",
)
_REJECTED_HOOKS = (
    "expert-name",
    "expert-karma-total",
    "expert-read-column",
    "expert-context-rail",
    "expert-contribution-summary",
    "expert-public-playbooks",
)


@dataclass(frozen=True)
class GuestOracle:
    """Public expected content plus private in-memory disclosure probes."""

    source_revision: str
    fixture_sha256: str
    summary: str
    workflow_path: str
    private_values: tuple[str, ...]


def validate_origin(origin: str, local_verification: bool = False) -> str:
    """Validate an explicit owned endpoint before any browser action.

    :param origin: Private companion origin; example https://cedar-web:8443.
    :param local_verification: Explicit local-only proof; never staging evidence.
    :return: Validated origin without normalization.
    :raises ValueError: Origin could address an undeclared external application.
    """
    if not isinstance(origin, str) or not isinstance(local_verification, bool):
        raise TypeError("An explicit origin and verification mode are required.")
    if origin == "https://cedar-web:8443" and not local_verification:
        return origin
    parsed = urlsplit(origin)
    if (
        local_verification
        and re.fullmatch(r"http://(?:localhost|127\.0\.0\.1):[1-9][0-9]{0,4}", origin)
        and parsed.port is not None
        and parsed.port <= 65535
    ):
        return origin
    raise ValueError("Only the owned companion or explicit loopback proof is allowed.")


def validate_oracle(oracle: GuestOracle) -> None:
    """Reject incomplete identities, content and public-workflow expectations.

    :param oracle: Explicit caller-provided fixture facts.
    :return: None when all facts are populated.
    :raises ValueError: The oracle is incomplete or malformed.
    """
    valid = (
        isinstance(oracle, GuestOracle)
        and isinstance(oracle.source_revision, str)
        and re.fullmatch(r"[a-f0-9]{40}", oracle.source_revision)
        and isinstance(oracle.fixture_sha256, str)
        and re.fullmatch(r"[a-f0-9]{64}", oracle.fixture_sha256)
        and isinstance(oracle.summary, str)
        and bool(oracle.summary.strip())
        and isinstance(oracle.workflow_path, str)
        and re.fullmatch(
            r"/playbooks/6101/workflows/[1-9][0-9]*/", oracle.workflow_path
        )
        and isinstance(oracle.private_values, tuple)
        and bool(oracle.private_values)
        and all(
            isinstance(value, str) and value.strip() for value in oracle.private_values
        )
    )
    if not valid:
        raise ValueError(
            "Complete source, fixture, public content and privacy probes required."
        )


def assert_guest_document(document: str, private_values: tuple[str, ...]) -> None:
    """Reject disclosure in a real response or hydrated DOM without value dumps.

    :param document: Actual response HTML or current browser DOM.
    :param private_values: Nonempty private sentinels, retained only in memory.
    :return: None for a valid public document.
    :raises AssertionError: Private content or authenticated controls appear.
    :raises ValueError: There is no meaningful document or disclosure probe.
    """
    if not isinstance(document, str) or not document.strip() or not private_values:
        raise ValueError("Public HTML and nonempty private disclosure probes required.")
    if any(not isinstance(value, str) or not value for value in private_values):
        raise ValueError("Every private disclosure probe must be nonempty text.")
    surface = unquote(unescape(document)).casefold()
    disclosed = "mailto:" in surface or any(
        value.casefold() in surface for value in private_values
    )
    private_control = any(
        re.search(r"(?:data-testid|id)\s*=\s*[\'\"]" + re.escape(hook), surface)
        for hook in _PRIVATE_HOOKS
    )
    if disclosed or private_control:
        raise AssertionError(
            "Guest document disclosed private content or account controls."
        )


def assert_column_geometry(
    read: dict[str, float], rail: dict[str, float], width: int
) -> None:
    """Check measured eight/four columns or below-md stacking.

    :param read: Actual read-column box from Chromium.
    :param rail: Actual context-rail box from Chromium.
    :param width: Actual required viewport width.
    :return: None when geometry follows the IA recipe.
    :raises AssertionError: Boxes overlap or use incorrect proportions/order.
    :raises ValueError: Metrics are nonfinite, nonpositive or incomplete.
    """
    _validate_box(read)
    _validate_box(rail)
    if type(width) is not int or width not in {size[0] for size in VIEWPORTS}:
        raise ValueError("A required IA viewport width is needed.")
    if width < _MD_WIDTH:
        assert abs(rail["x"] - read["x"]) <= _TOLERANCE
        assert abs(rail["width"] - read["width"]) <= _TOLERANCE
        assert rail["y"] >= read["y"] + read["height"]
    else:
        assert abs(rail["y"] - read["y"]) <= _TOLERANCE
        assert rail["x"] >= read["x"] + read["width"] - _TOLERANCE
        assert abs(read["width"] - 2 * rail["width"]) <= _TOLERANCE


def validate_output(output: Path) -> Path:
    """Require an existing private acquisition directory before writing evidence.

    :param output: Invocation-owned, absolute output directory.
    :return: The unchanged safe directory.
    :raises ValueError: It is missing, linked, public or not owned by this process.
    """
    if not isinstance(output, Path) or not output.is_absolute():
        raise ValueError("An absolute private acquisition directory is required.")
    if not output.is_dir() or output.resolve() != output or output.is_symlink():
        raise ValueError("Acquisition directory must exist without linked components.")
    info = output.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("Acquisition directory must be privately owned mode0700.")
    return output


def _validate_box(box: dict[str, float]) -> None:
    """Require real finite layout metrics before recipe assertions.

    :param box: Browser bounding box, for example x/y/width/height.
    :return: None for a usable box.
    :raises ValueError: Missing, nonnumeric, infinite or empty dimensions.
    """
    if not isinstance(box, dict) or not {"x", "y", "width", "height"} <= box.keys():
        raise ValueError("Complete Chromium geometry is required.")
    for key in ("x", "y", "width", "height"):
        value = box[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError("Geometry must contain finite numeric metrics.")
    if box["width"] <= 0 or box["height"] <= 0:
        raise ValueError("Geometry dimensions must be positive.")


def run_guest(
    page: Page,
    origin: str,
    output: Path,
    oracle: GuestOracle,
    *,
    local_verification: bool = False,
) -> dict[str, Any]:
    """Execute literal G01–G04 using the caller's actual fresh browser.

    :param page: Real anonymous page with caller-owned tracing/network guards.
    :param origin: Explicit owned origin or loopback proof.
    :param output: Existing private acquisition directory.
    :param oracle: Exact public facts and private in-memory disclosure probes.
    :param local_verification: Explicit local-only label; never staged acceptance.
    :return: Actual observations; companion DB/mail verification remains required.
    :raises ValueError: Unsafe input or incomplete identity.
    :raises AssertionError: Any literal condition differs.
    """
    _validate_request(page, origin, output, oracle, local_verification)
    viewport = _fresh_viewport(page)
    logger.info(
        "staging_guest | entry | viewport=%s local=%s", viewport, local_verification
    )
    started, rows = monotonic(), []
    _run_public_reading(page, origin, output, oracle, rows)
    _run_rejections(page, origin, output, oracle, rows)
    assert not page.context.cookies(), "Anonymous reading created a cookie."
    logger.info("staging_guest | exit | observations=%s", len(rows))
    return _result(page, oracle, rows, started, local_verification)


def _fresh_viewport(page: Page) -> tuple[int, int]:
    """Require a fresh real context and one exact IA viewport.

    :param page: Actual anonymous browser page before navigation.
    :return: Width and height in CSS pixels.
    :raises AssertionError: Authentication cookies or an unsupported viewport exist.
    """
    assert not page.context.cookies(), "Fresh anonymous context required."
    size = page.viewport_size
    assert size is not None and (size["width"], size["height"]) in VIEWPORTS
    return size["width"], size["height"]


def _run_public_reading(
    page: Page,
    origin: str,
    output: Path,
    oracle: GuestOracle,
    rows: list[dict[str, Any]],
) -> None:
    """Read the real ranking, public detail and accessibility workflow.

    :param page: Real fresh anonymous page.
    :param origin: Validated companion origin.
    :param output: Private evidence directory.
    :param oracle: Exact public facts/private probes.
    :param rows: Actual acquired observations.
    :return: None after G01–G03.
    :raises AssertionError: A native action or literal observation differs.
    """
    _open(page, origin, _DESIGN_PATH, oracle)
    _assert_ranking(page)
    rows.append(_capture(page, output, "G01-design"))
    _native_explanations(page, output, "experts-card-mrodriguez", "G02-list", rows)
    _follow_maria(page, origin, oracle)
    _assert_detail(page, oracle)
    rows.append(_capture(page, output, "G01-detail"))
    _native_explanations(page, output, None, "G02-detail", rows)
    _follow_public_work(page, origin, output, oracle, rows)


def _settle(page: Page) -> None:
    """Settle real fonts and dismiss only a visible first-visit consent prompt.

    :param page: Actual loaded document.
    :return: None when real text/icon fonts are loaded.
    :raises AssertionError: Consent cannot close or required fonts are unavailable.
    """
    dismiss = page.get_by_role("button", name="Not now", exact=True)
    if dismiss.is_visible():
        dismiss.click()
        expect(dismiss).to_be_hidden()
    fonts = page.evaluate(
        """async () => { await document.fonts.ready;
        return [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replaceAll('"', '')); }"""
    )
    assert "Montserrat" in fonts and "Font Awesome 6 Pro" in fonts
    assert page.evaluate("document.documentElement.scrollWidth === innerWidth")


def _assert_response(
    page: Page,
    response: Response | None,
    url: str,
    oracle: GuestOracle,
    status: int = 200,
) -> None:
    """Check actual response and hydrated DOM without replacing network behavior.

    :param page: Actual browser after navigation.
    :param response: Real document response.
    :param url: Exact expected destination.
    :param oracle: In-memory disclosure probes.
    :param status: Required native HTTP result, normally200 or404.
    :return: None after both surfaces pass.
    :raises AssertionError: Redirect, status, identity or disclosure differs.
    """
    assert response is not None and response.status == status
    assert response.request.redirected_from is None
    expect(page).to_have_url(url)
    assert_guest_document(response.text(), oracle.private_values)
    _settle(page)
    assert_guest_document(page.content(), oracle.private_values)


def _open(
    page: Page, origin: str, path: str, oracle: GuestOracle, status: int = 200
) -> None:
    """Open the actual local companion path and inspect its document response.

    :param page: Actual browser page.
    :param origin: Validated endpoint.
    :param path: Fixed module-owned route.
    :param oracle: Disclosure probes.
    :param status: Exact expected HTTP result.
    :return: None after genuine HTTP and DOM checks.
    :raises AssertionError: Native behavior differs.
    """
    url = origin + path
    _assert_response(
        page, page.goto(url, wait_until="networkidle"), url, oracle, status
    )


def _follow(page: Page, link: Locator, url: str, oracle: GuestOracle) -> None:
    """Follow the actual public anchor and preserve its native navigation result.

    :param page: Real public browser.
    :param link: Real rendered public link.
    :param url: Exact expected absolute destination.
    :param oracle: In-memory private probes.
    :return: None after native anchor navigation succeeds.
    :raises AssertionError: Rendered href, HTTP or destination differs.
    """
    expect(link).to_have_attribute(
        "href",
        urlsplit(url).path + ("?" + urlsplit(url).query if urlsplit(url).query else ""),
    )
    with page.expect_navigation(wait_until="networkidle") as navigation:
        link.click()
    _assert_response(page, navigation.value, url, oracle)


def _assert_ranking(page: Page, guest: bool = True) -> None:
    """Read every exact rank, identity and score and the excluded boundary people.

    :param page: Actual anonymous Design leaderboard.
    :param guest: Whether the actual caller is anonymous.
    :return: None after five ordered cards and guest auth actions pass.
    :raises AssertionError: Ranking, category, score or usable actions differ.
    """
    cards = page.get_by_test_id("experts-leaderboard").get_by_role("article")
    expect(cards).to_have_count(len(_DESIGN))
    for rank, (username, name, total) in enumerate(_DESIGN, 1):
        card = cards.nth(rank - 1)
        expect(card).to_have_attribute("data-testid", f"experts-card-{username}")
        expect(card.get_by_test_id("expert-card-name")).to_have_text(name)
        expect(card.get_by_test_id("expert-card-karma")).to_have_text(total)
        expect(card.get_by_test_id("expert-card-rank")).to_have_attribute(
            "aria-label", f"Rank {rank}"
        )
        card.get_by_test_id(f"experts-view-profile-{username}").click(trial=True)
    for username in ("tmartin", "mchen", "nberg"):
        expect(page.get_by_test_id(f"experts-card-{username}")).to_have_count(0)
    expect(page.get_by_test_id("experts-category-design")).to_have_attribute(
        "aria-current", "page"
    )
    if guest:
        banner = page.get_by_test_id("guest-auth-banner")
        banner.get_by_role("link", name="Sign In", exact=True).click(trial=True)
        banner.get_by_role("link", name="Register", exact=True).click(trial=True)


def _native_explanations(
    page: Page, output: Path, scope: str | None, label: str, rows: list[dict[str, Any]]
) -> None:
    """Exercise real hover and native Tab on the scoped disabled contact wrapper.

    :param page: Actual guest list or detail.
    :param output: Safe evidence directory.
    :param scope: Maria's card hook or None for detail.
    :param label: Fixed step/surface acquisition label.
    :param rows: Actual screenshot observations.
    :return: None after both activation modes pass.
    :raises AssertionError: Disabled state, focus, explanation or geometry differs.
    """
    wrapper = guest_contact_wrapper(page, scope)
    button = wrapper.get_by_test_id("experts-reach-out-disabled-mrodriguez")
    expect(button).to_be_disabled()
    expect(wrapper).to_have_accessible_description(_EXPLANATION)
    expect(wrapper.locator("a, form")).to_have_count(0)
    for activation in ("hover", "keyboard"):
        _activate_and_capture(page, output, wrapper, scope, label, activation, rows)
        expect(button).to_be_disabled()


def _activate_and_capture(
    page: Page,
    output: Path,
    wrapper: Locator,
    scope: str | None,
    label: str,
    activation: Literal["hover", "keyboard"],
    rows: list[dict[str, Any]],
) -> None:
    """Retain a genuine tooltip and dismiss it through native input.

    :param page: Actual browser page.
    :param output: Safe output directory.
    :param wrapper: Unique real explanatory wrapper.
    :param scope: List-card hook or None for detail.
    :param label: Fixed acquisition label.
    :param activation: Native hover or keyboard input.
    :param rows: Actual observations.
    :return: None after display, geometry and dismissal pass.
    :raises AssertionError: Actual input or tooltip differs.
    """
    if activation == "keyboard" and scope is not None:
        tab_to_guest_control(
            page, page.get_by_test_id("experts-view-profile-mrodriguez")
        )
    tooltip = activate_guest_tooltip(page, wrapper, activation)
    _settle_tooltip(tooltip)
    _tooltip_geometry(page, tooltip)
    rows.append(_capture(page, output, label + "-" + activation))
    _dismiss_tooltip(page, wrapper, tooltip, activation)


def _settle_tooltip(tooltip: Locator) -> None:
    """Observe actual Popper placement and native scrolling until stable.

    :param tooltip: Actual visible Bootstrap tooltip.
    :return: None after three stable frames.
    :raises AssertionError: Placement fails to settle within120 frames.
    """
    assert tooltip.evaluate("""async panel => { let previous='', stable=0;
        for (let frame=0; frame<120; frame++) { await new Promise(requestAnimationFrame);
            const box=panel.getBoundingClientRect();
            const geometry=JSON.stringify([scrollX,scrollY,box.x,box.y,box.width,box.height]);
            stable=geometry===previous?stable+1:0; previous=geometry;
            if(stable>=3 && panel.getAnimations().every(a=>a.playState==='finished')) return true;
        } return false; }""")


def _assert_detail(page: Page, oracle: GuestOracle) -> None:
    """Read complete public prose, reconciled amounts and measured body/rail layout.

    :param page: Actual Maria detail browser.
    :param oracle: Complete stored public paragraph.
    :return: None when exact content and IA layout pass.
    :raises AssertionError: Identity, prose, figures or layout differs.
    """
    expect(page.get_by_test_id("expert-name")).to_have_text("Maria Rodriguez")
    expect(page.get_by_test_id("expert-karma-total")).to_have_text("8,200")
    summary = page.get_by_test_id("expert-contribution-summary")
    expect(summary).to_have_text(oracle.summary)
    assert summary.inner_text() == oracle.summary
    _assert_full_paragraph(summary)
    _assert_breakdown(page)
    read, rail = (
        page.get_by_test_id(hook)
        for hook in ("expert-read-column", "expert-context-rail")
    )
    assert read.evaluate(
        "el => Boolean(el.compareDocumentPosition(document.querySelector('[data-testid=expert-context-rail]')) & Node.DOCUMENT_POSITION_FOLLOWING)"
    )
    size = page.viewport_size
    assert size is not None
    assert_column_geometry(read.bounding_box(), rail.bounding_box(), size["width"])
    page.get_by_test_id("expert-back-link").click(trial=True)
    rail.get_by_test_id("expert-playbook-6101").click(trial=True)


def _assert_full_paragraph(summary: Locator) -> None:
    """Require actual full-text line bounds without clamp or ellipsis.

    :param summary: Real public paragraph locator.
    :return: None after all line boxes fit the untruncated paragraph.
    :raises AssertionError: Computed style clips, clamps or truncates public prose.
    """
    assert summary.evaluate(
        """el => { const s=getComputedStyle(el), box=el.getBoundingClientRect();
        const range=document.createRange(); range.selectNodeContents(el);
        return s.overflowX==='visible' && s.overflowY==='visible' && s.textOverflow!=='ellipsis' &&
            s.webkitLineClamp==='none' && [...range.getClientRects()].every(line=>
                line.left>=box.left-1 && line.right<=box.right+1 && line.top>=box.top-1 && line.bottom<=box.bottom+1);
    }"""
    )


def _assert_breakdown(page: Page) -> None:
    """Read all four sources separately from category subtotals.

    :param page: Actual public Maria detail.
    :return: None after exact baseline figures reconcile.
    :raises AssertionError: Any label, amount or category differs.
    """
    table = page.get_by_test_id("karma-source-breakdown")
    expect(table.locator("tbody th")).to_have_text(
        ["Released playbooks", "PIP contributions", "Consumption", "Learning"]
    )
    expect(table.locator("tbody td")).to_have_text(["5,000", "1,600", "1,200", "400"])
    expect(table.locator("tfoot th")).to_have_text("Total")
    expect(table.locator("tfoot td")).to_have_text("8,200")
    expect(
        page.get_by_test_id("karma-category-breakdown").locator("dt, dd")
    ).to_have_text(["Design", "7,200", "Development", "1,000"])


def _follow_public_work(
    page: Page,
    origin: str,
    output: Path,
    oracle: GuestOracle,
    rows: list[dict[str, Any]],
) -> None:
    """Follow the actual released playbook and its exact public workflow.

    :param page: Actual Maria detail page.
    :param origin: Validated origin.
    :param output: Private evidence directory.
    :param oracle: Workflow route and disclosure probes.
    :param rows: Actual acquired observations.
    :return: None after G03 and return to Maria.
    :raises AssertionError: Native evidence content or identity differs.
    """
    link = page.get_by_test_id("expert-playbook-6101")
    expect(link).to_have_accessible_name("View Accessibility Audit Playbook")
    _follow(page, link, origin + "/playbooks/6101/", oracle)
    expect(page.get_by_test_id("playbook-header")).to_contain_text(
        "Accessibility Audit Playbook"
    )
    rows.append(_capture(page, output, "G03-playbook"))
    _follow_workflow(page, origin, oracle)
    rows.append(_capture(page, output, "G03-workflow"))
    _open(page, origin, _DETAIL, oracle)


def _run_rejections(
    page: Page,
    origin: str,
    output: Path,
    oracle: GuestOracle,
    rows: list[dict[str, Any]],
) -> None:
    """Read honest Other, two identical native404s and real recovery.

    :param page: Actual anonymous detail after public reading.
    :param origin: Validated origin.
    :param output: Private acquisition directory.
    :param oracle: Disclosure probes.
    :param rows: Actual observations.
    :return: None after G04.
    :raises AssertionError: Empty, rejection or recovery differs.
    """
    _open_other(page, origin, oracle)
    rows.append(_capture(page, output, "G04-other"))
    presentations = [
        _rejection(page, origin, output, oracle, name, rows)
        for name in ("nberg", "no-such-cedar-user")
    ]
    assert presentations[0] == presentations[1]
    _follow(
        page,
        page.get_by_test_id("expert-unavailable-back-link"),
        origin + "/experts/",
        oracle,
    )


def _rejection(
    page: Page,
    origin: str,
    output: Path,
    oracle: GuestOracle,
    username: str,
    rows: list[dict[str, Any]],
) -> tuple[str, str, str | None]:
    """Inspect one actual generic404 without a success-shaped profile.

    :param page: Actual anonymous browser.
    :param origin: Validated endpoint.
    :param output: Safe evidence directory.
    :param oracle: In-memory disclosure probes.
    :param username: Fixed zero or missing fixture subject.
    :param rows: Actual observations.
    :return: Native heading/back-label/back-href presentation.
    :raises AssertionError: Native rejection or generic privacy presentation differs.
    """
    _open(page, origin, f"/experts/{username}/", oracle, status=404)
    for hook in _REJECTED_HOOKS:
        expect(page.get_by_test_id(hook)).to_have_count(0)
    heading = page.get_by_test_id("expert-unavailable")
    back = page.get_by_test_id("expert-unavailable-back-link")
    expect(heading).to_have_text("Expert unavailable")
    expect(back).to_have_accessible_name("Back to Experts")
    expect(back).to_have_attribute("href", "/experts/")
    back.click(trial=True)
    rows.append(_capture(page, output, "G04-" + username))
    return heading.inner_text(), back.inner_text(), back.get_attribute("href")


def _capture(page: Page, output: Path, label: str) -> dict[str, Any]:
    """Acquire original pixels and safe measured metadata after actual assertions.

    :param page: Actual browser page at the checked step.
    :param output: Existing private evidence directory.
    :param label: Fixed portable module-owned step label.
    :return: Actual path, viewport and original screenshot digest.
    :raises ValueError: A duplicate or unsafe acquisition path exists.
    """
    if not re.fullmatch(r"G0[1-4]-[A-Za-z0-9-]+", label):
        raise ValueError("Fixed portable guest step label required.")
    target = output / (label + ".png")
    if target.exists() or target.is_symlink():
        raise ValueError("Original guest acquisition cannot be overwritten.")
    page.screenshot(path=str(target), full_page=True)
    return {
        "step": label,
        "path": urlsplit(page.url).path,
        "query": urlsplit(page.url).query,
        "viewport": page.viewport_size,
        "screenshot": target.name,
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "document_width": page.evaluate("document.documentElement.scrollWidth"),
    }


def _validate_request(
    page: Page, origin: str, output: Path, oracle: GuestOracle, local: bool
) -> None:
    """Validate all caller-owned run boundaries before browser actions.

    :param page: Actual browser page, validated by subsequent native operations.
    :param origin: Explicit companion or loopback origin.
    :param output: Existing private acquisition directory.
    :param oracle: Exact expected facts and probes.
    :param local: Explicit local-only label.
    :return: None when input identities are valid.
    :raises ValueError: Endpoint, output or oracle is unsafe.
    """
    validate_origin(origin, local)
    validate_oracle(oracle)
    validate_output(output)
    assert page.viewport_size is not None


def _result(
    page: Page,
    oracle: GuestOracle,
    rows: list[dict[str, Any]],
    started: float,
    local: bool,
) -> dict[str, Any]:
    """Describe the actual completed browser lane without a companion verdict.

    :param page: Actual completed guest page.
    :param oracle: Source/fixture identities.
    :param rows: Actual acquired observations.
    :param started: Monotonic start of the real automated operator.
    :param local: Explicit local-only label.
    :return: Safe public browser evidence metadata.
    """
    return {
        "contract": "UAT-18-02",
        "steps": ["G01", "G02", "G03", "G04"],
        "operator": "automated_browser",
        "environment": "local_verification" if local else "owned_staging",
        "elapsed_seconds": monotonic() - started,
        "viewport": page.viewport_size,
        "source_revision": oracle.source_revision,
        "fixture_sha256": oracle.fixture_sha256,
        "observations": rows,
        "companion_state_check": "REQUIRED_SEPARATELY",
    }


def _follow_maria(page: Page, origin: str, oracle: GuestOracle) -> None:
    """Follow Maria's actual leaderboard profile action.

    :param page: Actual Design leaderboard.
    :param origin: Validated origin.
    :param oracle: Disclosure probes.
    :return: None after native navigation to Maria.
    :raises AssertionError: Link or document differs.
    """
    _follow(
        page,
        page.get_by_test_id("experts-view-profile-mrodriguez"),
        origin + _DETAIL,
        oracle,
    )


def _dismiss_tooltip(
    page: Page, wrapper: Locator, tooltip: Locator, activation: str
) -> None:
    """Dismiss the actual tooltip with the same pointer/keyboard input mode.

    :param page: Actual guest page.
    :param wrapper: Actual tooltip trigger.
    :param tooltip: Actual visible tooltip.
    :param activation: Already-validated input mode.
    :return: None after the real tooltip disappears.
    :raises AssertionError: Keyboard focus or dismissal differs.
    """
    if activation == "hover":
        page.mouse.move(0, 0)
    else:
        expect(wrapper).to_be_focused()
        page.keyboard.press("Tab")
        expect(wrapper).not_to_be_focused()
    expect(tooltip).to_be_hidden(timeout=2500)


def _follow_workflow(page: Page, origin: str, oracle: GuestOracle) -> None:
    """Follow the exact public workflow and read its real activity evidence.

    :param page: Actual public playbook detail.
    :param origin: Validated origin.
    :param oracle: Exact workflow route/disclosure probes.
    :return: None when the public workflow and three activities match.
    :raises AssertionError: Native identity or evidence content differs.
    """
    workflow_id = oracle.workflow_path.rstrip("/").rsplit("/", 1)[1]
    _follow(
        page,
        page.get_by_test_id("workflow-name-link-" + workflow_id),
        origin + oracle.workflow_path,
        oracle,
    )
    expect(page.get_by_test_id("workflow-name")).to_have_text(
        "Lead an Accessibility Review"
    )
    for title in (
        "Trace Keyboard Focus",
        "Review Form Feedback",
        "Document Recovery Paths",
    ):
        expect(page.get_by_test_id("activities-graph")).to_contain_text(title)


def _open_other(page: Page, origin: str, oracle: GuestOracle) -> None:
    """Use actual Back and category links to reach honest empty Other.

    :param page: Actual Maria detail.
    :param origin: Validated origin.
    :param oracle: Disclosure probes.
    :return: None after empty Other is shown with its current-category marker.
    :raises AssertionError: Native navigation or empty content differs.
    """
    _follow(
        page, page.get_by_test_id("expert-back-link"), origin + _DESIGN_PATH, oracle
    )
    _follow(
        page,
        page.get_by_test_id("experts-category-other"),
        origin + "/experts/?category=other",
        oracle,
    )
    expect(
        page.get_by_test_id("experts-leaderboard").get_by_role("article")
    ).to_have_count(0)
    expect(page.get_by_test_id("experts-empty")).to_have_text(_OTHER)
    expect(page.get_by_test_id("experts-category-other")).to_have_attribute(
        "aria-current", "page"
    )


def assert_disjoint_boxes(first: dict[str, float], second: dict[str, float]) -> None:
    """Reject overlapping actual card identity, score and action rectangles.

    :param first: First real Chromium box.
    :param second: Second real Chromium box.
    :return: None for disjoint boxes, including touching edges.
    :raises AssertionError: Rectangles overlap.
    :raises ValueError: Geometry is missing, nonfinite or empty.
    """
    _validate_box(first)
    _validate_box(second)
    assert (
        first["x"] + first["width"] <= second["x"]
        or second["x"] + second["width"] <= first["x"]
        or first["y"] + first["height"] <= second["y"]
        or second["y"] + second["height"] <= first["y"]
    ), "Actual card lanes overlap."


def _tooltip_geometry(page: Page, tooltip: Locator) -> None:
    """Check the actual tooltip's line bounds against its real viewport.

    :param page: Actual browser page.
    :param tooltip: Actual visible explanation.
    :return: None after native geometry and occlusion pass.
    :raises AssertionError: Actual viewport or tooltip geometry differs.
    """
    size = page.viewport_size
    assert size is not None
    assert_guest_tooltip_in_viewport(page, tooltip, (size["width"], size["height"]))
