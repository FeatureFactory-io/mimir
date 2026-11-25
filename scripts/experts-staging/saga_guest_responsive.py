"""Authenticated Elena responsive outlines; caller owns the real signed-in page."""

from __future__ import annotations

import hashlib
import logging
from html import unescape
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.parse import unquote, urlsplit

from playwright.sync_api import Locator, Page, expect
from saga_guest import (
    VIEWPORTS,
    GuestOracle,
    _assert_detail,
    _assert_ranking,
    _settle,
    assert_disjoint_boxes,
    validate_oracle,
    validate_origin,
    validate_output,
)

from tests.support.experts_guest_browser import tab_to_guest_control

logger = logging.getLogger(__name__)
_DESIGN_PATH = "/experts/?category=design"
_DETAIL_PATH = "/experts/mrodriguez/"
_NAMES = ("sreed", "mrodriguez", "pnair", "dortiz", "hkim")
_CONTACTS = (
    "sofia.reed@example.com",
    "maria.rodriguez@example.com",
    "priya.nair@example.com",
    "daniel.ortiz@example.com",
    "hana.kim@example.com",
)
_CATEGORIES = ("Product", "Development", "Research", "Design", "Other")
_MAX_SCROLLS = 20
_READING_FRACTION = 0.5
_SETTLE_TIMEOUT_MS = 5000
_LINE_STATE = """(el, fraction) => {
    const range=document.createRange(); range.selectNodeContents(el);
    const top=Math.max(0,document.querySelector('[data-testid=realm-navbar]').getBoundingClientRect().bottom);
    const lines=[...range.getClientRects()], readable=[], covered=[];
    lines.forEach((line,index)=>{ if(line.top<top || line.bottom>innerHeight)return;
        const y=(line.top+line.bottom)/2;
        const points=[line.left+1,(line.left+line.right)/2,line.right-1];
        if(points.every(x=>el.contains(document.elementFromPoint(x,y)))) readable.push(index);
        else covered.push(index);
    });
    return {count:lines.length,readable,covered,scrollY,
        step:Math.max(1,Math.floor((innerHeight-top)*fraction)),
        maxScroll:document.documentElement.scrollHeight-innerHeight};
}"""


def run_elena_matrix(
    page: Page,
    origin: str,
    output: Path,
    oracle: GuestOracle,
    *,
    local_verification: bool = False,
) -> dict[str, Any]:
    """Execute both authenticated seven-size outlines against the real server.

    :param page: Actual caller-signed-in Elena page.
    :param origin: Owned companion origin or explicit loopback proof.
    :param output: Existing private acquisition directory.
    :param oracle: Exact current public/source/fixture facts.
    :param local_verification: Explicit local-only evidence label.
    :return: Fourteen actual screen observations, not a complete Saga verdict.
    :raises ValueError: Run identities/output are unsafe.
    :raises AssertionError: Native identity or responsive observations differ.
    """
    validate_origin(origin, local_verification)
    validate_output(output)
    validate_oracle(oracle)
    expect(page.get_by_test_id("user-display")).to_have_text("esvensson")
    started = monotonic()
    logger.info("staging_elena_responsive | entry | viewports=%s", len(VIEWPORTS))
    rows = [_one_viewport(page, origin, output, oracle, size) for size in VIEWPORTS]
    logger.info("staging_elena_responsive | exit | screen_pairs=%s", len(rows))
    return _matrix_result(oracle, rows, started, local_verification)


def _one_viewport(
    page: Page, origin: str, output: Path, oracle: GuestOracle, size: tuple[int, int]
) -> dict[str, Any]:
    """Observe the actual list and detail at one required CSS viewport.

    :param page: Real Elena browser page.
    :param origin: Validated actual origin.
    :param output: Private matrix directory.
    :param oracle: Exact current public text.
    :param size: Required CSS width/height pair.
    :return: Actual list/detail capture metadata.
    :raises AssertionError: Any native content/geometry observation differs.
    """
    page.set_viewport_size({"width": size[0], "height": size[1]})
    destination = output / f"elena-{size[0]}-{size[1]}"
    destination.mkdir(mode=0o700)
    _open_elena(page, origin + _DESIGN_PATH)
    _assert_ranking(page, guest=False)
    _assert_shell(page)
    _assert_cards(page)
    listing = _capture(page, destination, "list", "FOB-EXPERTS-LIST+FIND-1")
    _open_elena(page, origin + _DETAIL_PATH)
    _assert_detail(page, oracle)
    _read_all_lines(page.get_by_test_id("expert-contribution-summary"))
    _assert_detail_actions(page)
    detail = _capture(page, destination, "detail", "FOB-EXPERT-VIEW-1")
    return {"viewport": page.viewport_size, "list": listing, "detail": detail}


def _open_elena(page: Page, url: str) -> None:
    """Open actual application content while retaining authenticated identity.

    :param page: Real signed-in browser page.
    :param url: Caller-constructed exact owned URL.
    :return: None after native200, identity, fonts and public-data checks.
    :raises AssertionError: Native response, identity or privacy differs.
    """
    response = page.goto(url, wait_until="networkidle")
    assert response is not None and response.status == 200
    assert response.request.redirected_from is None
    expect(page).to_have_url(url)
    expect(page.get_by_test_id("user-display")).to_have_text("esvensson")
    _settle(page)
    for html in (response.text(), page.content()):
        _assert_public_evidence(html)


def _assert_public_evidence(document: str) -> None:
    """Reject fixture-private evidence while allowing authenticated contact hrefs.

    :param document: Actual HTTP or hydrated DOM content.
    :return: None when protected fiction probes are absent.
    :raises AssertionError: Private book, PIP or token appears.
    """
    surface = unquote(unescape(document)).casefold()
    for value in (
        "Cedar Bid Pricing",
        "Internal staffing notes for Cedar",
        "DEMO_ONLY_NOT_A_REAL_TOKEN",
    ):
        if value.casefold() in surface:
            raise AssertionError("Private evidence appeared in a public expert screen.")
    assert 'data-testid="profile-api-token"' not in surface


def _assert_shell(page: Page) -> None:
    """Read actual Mimir typography, colors and category navigation.

    :param page: Actual authenticated Design leaderboard.
    :return: None when shell tokens and all categories remain usable.
    :raises AssertionError: Typography, colors or navigation differ.
    """
    title = page.get_by_role("heading", name="Experts", exact=True)
    expect(title).to_have_css("font-size", "28px")
    expect(title).to_have_css("font-weight", "600")
    expect(
        page.get_by_text("Top contributors by playbook category", exact=True)
    ).to_be_visible()
    assert page.evaluate(
        "() => [getComputedStyle(document.body).fontFamily.split(',')[0].replaceAll('\"','').trim(),getComputedStyle(document.body).fontSize]"
    ) == ["Montserrat", "16px"]
    expect(page.get_by_test_id("realm-navbar")).to_have_css(
        "background-color", "rgb(31, 58, 95)"
    )
    expect(page.get_by_test_id("realm-navbar")).to_have_css(
        "border-bottom-color", "rgb(201, 162, 39)"
    )
    tabs = page.get_by_test_id("experts-category-tabs")
    expect(tabs.get_by_role("link")).to_have_text(list(_CATEGORIES))
    for link in tabs.get_by_role("link").all():
        link.click(trial=True)
    expect(page.get_by_test_id("guest-auth-banner")).to_have_count(0)


def _assert_cards(page: Page) -> None:
    """Check every real card's text lanes, pointer access and native Tab order.

    :param page: Actual authenticated Design leaderboard.
    :return: None after all ten native actions remain reachable in rank order.
    :raises AssertionError: Text, overlap, action or sequential focus differs.
    """
    actions = []
    last_bottom = float("-inf")
    for username, email in zip(_NAMES, _CONTACTS, strict=True):
        card = page.get_by_test_id(f"experts-card-{username}")
        top, bottom = card.evaluate(
            "el => { const b=el.getBoundingClientRect(); return [b.top+scrollY,b.bottom+scrollY]; }"
        )
        assert top >= last_bottom
        last_bottom = bottom
        _card_geometry(card)
        _full_text(card.get_by_test_id("expert-card-name"))
        _full_text(card.get_by_test_id("expert-card-karma"))
        actions.extend(_card_actions(card, username, email))
    _native_action_order(page, actions)
    assert page.evaluate("document.documentElement.scrollWidth===innerWidth")


def _card_geometry(card: Locator) -> None:
    """Measure actual identity, score and action lanes for overlap/stacking.

    :param card: Actual rendered ranked article.
    :return: None for disjoint responsive lanes within the card.
    :raises AssertionError: Card lanes overlap or narrow actions fail to stack.
    """
    identity, score, actions, narrow = card.evaluate("""card => [
        ...['.expert-identification','.expert-score','.expert-card-actions'].map(s=>{
            const b=card.querySelector(s).getBoundingClientRect(); return {x:b.x,y:b.y,width:b.width,height:b.height};
        }), innerWidth<768]""")
    assert_disjoint_boxes(identity, score)
    assert_disjoint_boxes(identity, actions)
    assert_disjoint_boxes(score, actions)
    assert actions["y"] >= identity["y"] + identity["height"] or (
        not narrow and actions["x"] >= identity["x"] + identity["width"]
    )


def _full_text(element: Locator) -> None:
    """Check real text range bounds and computed truncation for identity/score.

    :param element: Actual card name or numeric total.
    :return: None when text is visible and fits without truncation.
    :raises AssertionError: Text is clipped, clamped or outside its box.
    """
    expect(element).to_be_visible()
    assert element.evaluate(
        """el => { const s=getComputedStyle(el),b=el.getBoundingClientRect();
        const r=document.createRange();r.selectNodeContents(el); const lines=[...r.getClientRects()];
        return !(Number(s.webkitLineClamp)||0) && el.scrollHeight<=el.clientHeight && el.scrollWidth<=el.clientWidth &&
            lines.length>0 && lines.every(l=>l.left>=b.left-1 && l.right<=b.right+1 && l.top>=b.top-1 && l.bottom<=b.bottom+1);
    }"""
    )


def _card_actions(card: Locator, username: str, email: str) -> list[Locator]:
    """Inspect both actual named anchors without activating external contact.

    :param card: Actual ranked card.
    :param username: Exact fixture contributor identity.
    :param email: Exact synthetic public contact target.
    :return: Profile then contact anchors in native expected focus order.
    :raises AssertionError: Either native action is absent, wrong or obstructed.
    """
    profile = card.get_by_test_id(f"experts-view-profile-{username}")
    contact = card.get_by_test_id(f"experts-reach-out-{username}")
    for control, name, href in (
        (profile, "View profile", f"/experts/{username}/"),
        (contact, "Reach out", "mailto:" + email),
    ):
        expect(control).to_have_accessible_name(name)
        expect(control).to_have_attribute("href", href)
        control.click(trial=True)
    return [profile, contact]


def _native_action_order(page: Page, actions: list[Locator]) -> None:
    """Reach the first action by Tab, then require the complete ten-action order.

    :param page: Actual authenticated leaderboard.
    :param actions: Actual ordered profile/contact anchors.
    :return: None after native keyboard traversal.
    :raises AssertionError: Native focus order or visibility differs.
    """
    tab_to_guest_control(page, actions[0])
    for index, action in enumerate(actions):
        if index:
            page.keyboard.press("Tab")
        expect(action).to_be_focused()
        _focus_settle(action)
        expect(action).to_be_in_viewport(ratio=1)
        _action_readable(action)


def _focus_settle(action: Locator) -> None:
    """Observe real native focus-scroll geometry before testing visibility.

    :param action: Actual currently focused native anchor.
    :return: None after three stable frames without forced scrolling.
    :raises AssertionError: Native focus geometry fails to settle.
    """
    assert action.evaluate("""async el=>{let previous='',stable=0;
        for(let frame=0;frame<120;frame++){await new Promise(requestAnimationFrame);
            const b=el.getBoundingClientRect(),state=JSON.stringify([scrollX,scrollY,b.x,b.y,b.width,b.height]);
            stable=state===previous?stable+1:0;previous=state;
            if(stable>=3)return true;
        }return false;}""")


def _action_readable(action: Locator) -> None:
    """Hit-test actual action text rather than only its enclosing control box.

    :param action: Actual focused profile or contact anchor.
    :return: None when each visible text line is unobstructed.
    :raises AssertionError: Another component obscures the action label.
    """
    assert action.evaluate("""el=>{const label=el.querySelector('button')||el;
        const node=[...label.childNodes].find(n=>n.nodeType===Node.TEXT_NODE && n.textContent.trim());
        if(!node)return false;const r=document.createRange();r.selectNodeContents(node);
        const lines=[...r.getClientRects()];return lines.length>0 && lines.every(line=>
            [line.left+1,(line.left+line.right)/2,line.right-1].every(x=>
                el.contains(document.elementFromPoint(x,(line.top+line.bottom)/2))));
    }""")


def _read_all_lines(summary: Locator) -> None:
    """Read every real paragraph line through native document scrolling/hit tests.

    :param summary: Actual full Maria contribution paragraph.
    :return: None once every line entered an unobscured reading area.
    :raises AssertionError: A line is obscured, reflows or cannot be reached.
    """
    page = summary.page
    page.keyboard.press("Home")
    page.wait_for_function("scrollY===0", timeout=_SETTLE_TIMEOUT_MS)
    expected = summary.evaluate(_LINE_STATE, _READING_FRACTION)["count"]
    assert expected > 0
    seen = set()
    for _ in range(_MAX_SCROLLS):
        state = summary.evaluate(_LINE_STATE, _READING_FRACTION)
        assert state["count"] == expected and not state["covered"]
        seen.update(state["readable"])
        if len(seen) == expected:
            return
        _scroll_next(page, state)
    raise AssertionError("Not all real summary lines became readable.")


def _scroll_next(page: Page, state: dict[str, Any]) -> None:
    """Advance actual document scroll only when unread lines can be reached.

    :param page: Actual browser page.
    :param state: Actual measured current scrolling/reading state.
    :return: None after native wheel scrolling reaches its expected position.
    :raises AssertionError: Remaining text cannot be reached.
    """
    target = min(state["scrollY"] + state["step"], state["maxScroll"])
    assert target > state["scrollY"]
    page.mouse.wheel(0, state["step"])
    page.wait_for_function(
        "target=>Math.abs(scrollY-target)<=1", arg=target, timeout=_SETTLE_TIMEOUT_MS
    )


def _assert_detail_actions(page: Page) -> None:
    """Reach actual public evidence and contact without sending a message.

    :param page: Actual authenticated Maria detail.
    :return: None when both target links remain usable.
    :raises AssertionError: Actual evidence/contact anchor differs or is occluded.
    """
    page.get_by_test_id("expert-playbook-6101").click(trial=True)
    contact = page.get_by_test_id("experts-reach-out-mrodriguez")
    expect(contact).to_have_attribute("href", "mailto:maria.rodriguez@example.com")
    contact.click(trial=True)


def _capture(page: Page, output: Path, name: str, screen: str) -> dict[str, Any]:
    """Capture actual screen pixels and distinguish the authenticated variant.

    :param page: Actual checked browser page.
    :param output: Newly created private viewport directory.
    :param name: Fixed list/detail acquisition name.
    :param screen: Registered IA Screen ID.
    :return: Original screenshot digest and actual geometry.
    :raises ValueError: An original acquisition would be overwritten.
    """
    target = output / (name + ".png")
    if target.exists() or target.is_symlink():
        raise ValueError("Original responsive acquisition cannot be overwritten.")
    page.screenshot(path=str(target), full_page=True)
    return {
        "screen_id": screen,
        "variant": "normal_authenticated_Elena",
        "viewport": page.viewport_size,
        "path": urlsplit(page.url).path,
        "screenshot": str(target.relative_to(output.parent)),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "document_width": page.evaluate("document.documentElement.scrollWidth"),
    }


def _matrix_result(
    oracle: GuestOracle,
    rows: list[dict[str, Any]],
    started: float,
    local_verification: bool,
) -> dict[str, Any]:
    """Describe only the actual fourteen authenticated screen observations.

    :param oracle: Public fixture/source identities.
    :param rows: Actual observed screen pairs.
    :param started: Monotonic operator start.
    :param local_verification: Explicit local-only label.
    :return: Safe observed metadata, with companion check still required.
    """
    return {
        "contracts": ["EXPERTS-LIST-10", "EXPERTS-VIEW-07"],
        "operator": "automated_browser",
        "environment": "local_verification" if local_verification else "owned_staging",
        "source_revision": oracle.source_revision,
        "fixture_sha256": oracle.fixture_sha256,
        "elapsed_seconds": monotonic() - started,
        "screen_pairs": rows,
        "variants": ["normal_authenticated_Elena"],
        "companion_state_check": "REQUIRED_SEPARATELY",
    }
