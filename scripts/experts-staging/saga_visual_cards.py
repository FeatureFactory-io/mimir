"""Credential-free S04 geometry recipe copied from checked candidate04 source.

Original test blob5993562e018f62cff3d8973bc20c54756dbf5ba8, SHA256
896285a8b9281e28cda5f66515c7e09a5c3bbcab96caa0d3f5e712046abac379.
Only browser assertions/literal constants are copied: no ORM imports or mutation.
The caller separately verifies source bytes and independently derives expected rows.
"""

from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Locator, Page, expect

_LONG_SUMMARY = (
    "Maria's published playbooks describe accessible form validation, keyboard recovery "
    "and inclusive user research across complex multi-stage workflows. "
    "The examples cover errors, focus restoration, and assistive technology testing. "
    "They document how status messages communicate corrections, how linked summaries let "
    "readers return to invalid fields, and how designers verify recovery in long forms. "
    "The released checklists include repeatable keyboard-only examples and explain which "
    "steps need further review with screen readers and magnification. "
    "Availability and project fit require a conversation."
)

_GUEST_EXPLANATION = "You need to be logged in to reach out to the expert"

_CATEGORIES = ("Product", "Development", "Research", "Design", "Other")

_MIKE_FALLBACK = "2 released playbooks · 47 copies"

_MAX_HINT_LINES = 2

_BOOTSTRAP_MD = 768

_CONSENT_PANEL = "[data-analytics-consent]"

_CONSENT_KEY = "ff_analytics_consent_v1"


@dataclass(frozen=True)
class _Contributor:
    """Independent Cedar display expectation for one article."""

    username: str
    name: str
    total: str
    hint: str
    email: str


def _open(page: Page, url: str) -> None:
    """Open the actual HTTP route and wait for settled text metrics."""
    response = page.goto(url)
    assert response is not None and response.ok
    expect(page).to_have_url(url)
    page.evaluate("() => document.fonts.ready.then(() => true)")


def _check_list(
    page: Page,
    url: str,
    category: str,
    contributors: tuple[_Contributor, ...],
    *,
    authenticated: bool,
) -> None:
    """Check ordered DOM, card geometry, and the complete keyboard action sequence."""
    _open(page, url)
    _assert_list_shell(page, category, authenticated)
    if not authenticated:
        _assert_fresh_guest_consent(page)
    cards = page.get_by_test_id("experts-leaderboard").get_by_role("article")
    expect(cards).to_have_count(len(contributors))
    tab_stops: list[Locator] = []
    previous_bottom = float("-inf")
    for rank, contributor in enumerate(contributors, 1):
        card = cards.nth(rank - 1)
        top, bottom = _assert_card(card, contributor, rank, category)
        assert previous_bottom <= top
        previous_bottom = bottom
        tab_stops.extend(_card_actions(card, contributor, authenticated))
    _assert_tab_order(page, tab_stops)
    for index, action in enumerate(tab_stops):
        if authenticated or index % 2 == 0:
            action.click(trial=True)
        else:
            action.hover()
    _assert_no_page_overflow(page)
    if not authenticated:
        _assert_fresh_guest_consent(page)


def _assert_fresh_guest_consent(page: Page) -> None:
    """Prove the guest action sequence leaves the initial consent panel untouched."""
    expect(page.locator(_CONSENT_PANEL)).to_be_visible()
    assert page.evaluate("(key) => localStorage.getItem(key)", _CONSENT_KEY) is None


def _assert_list_shell(page: Page, category: str, authenticated: bool) -> None:
    """Check IA wording, typography, shared colors and category reachability."""
    header = page.get_by_role("heading", name="Experts", exact=True)
    expect(header).to_have_text("Experts")
    expect(header).to_have_css("font-size", "28px")
    expect(header).to_have_css("font-weight", "600")
    expect(
        page.get_by_text("Top contributors by playbook category", exact=True)
    ).to_be_visible()
    body_style = page.evaluate("""() => {
            const body = getComputedStyle(document.body);
            return [body.fontFamily.split(',')[0].replaceAll('"', '').trim(), body.fontSize];
        }""")
    assert body_style == ["Montserrat", "16px"]
    navigation = page.get_by_test_id("realm-navbar")
    expect(navigation).to_have_css("background-color", "rgb(31, 58, 95)")
    expect(navigation).to_have_css("border-bottom-color", "rgb(201, 162, 39)")
    tabs = page.get_by_test_id("experts-category-tabs")
    expect(tabs.get_by_role("link")).to_have_text(list(_CATEGORIES))
    selected = tabs.get_by_test_id(f"experts-category-{category.lower()}")
    expect(selected).to_have_attribute("aria-current", "page")
    expect(selected).to_have_css("background-color", "rgb(31, 58, 95)")
    for tab in tabs.get_by_role("link").all():
        tab.click(trial=True)
    banner = page.get_by_test_id("guest-auth-banner")
    if authenticated:
        expect(banner).to_have_count(0)
    else:
        banner.get_by_role("link", name="Sign In", exact=True).click(trial=True)
        banner.get_by_role("link", name="Register", exact=True).click(trial=True)


def _assert_card(
    card: Locator, person: _Contributor, rank: int, category: str
) -> tuple[float, float]:
    """Check readable identity, exact public contribution text and ordered bounds."""
    expect(card).to_have_attribute("data-testid", f"experts-card-{person.username}")
    rank_label = card.get_by_test_id("expert-card-rank")
    expect(rank_label).to_have_attribute("aria-label", f"Rank {rank}")
    initials = "".join(part[0].upper() for part in person.name.split()[:2])
    text_signals = {
        "expert-card-rank": str(rank),
        "expert-card-name": person.name,
        f"experts-card-initials-{person.username}": initials,
        "expert-card-karma": person.total,
        "expert-card-category": category,
    }
    for test_id, text in text_signals.items():
        signal = card.get_by_test_id(test_id)
        expect(signal).to_have_text(text)
        _assert_full_text(signal)
    avatar = card.get_by_role("img", name=f"{person.name} initials", exact=True)
    expect(avatar).to_have_text(initials)
    expect(avatar).to_have_css("color", "rgb(31, 58, 95)")
    _assert_excerpt(
        card.get_by_test_id(f"experts-card-hint-{person.username}"), person.hint
    )
    _assert_geometry(card)
    top, bottom = card.evaluate(
        "card => [card.getBoundingClientRect().top + scrollY, card.getBoundingClientRect().bottom + scrollY]"
    )
    return top, bottom


def _assert_full_text(element: Locator) -> None:
    """Check text coverage from actual range bounds and the unclamped content area."""
    expect(element).to_be_visible()
    metrics = element.evaluate("""el => {
            const style = getComputedStyle(el);
            const bounds = el.getBoundingClientRect();
            const text = document.createRange();
            text.selectNodeContents(el);
            const lines = [...text.getClientRects()];
            return {
                clamp: Number(style.webkitLineClamp) || 0,
                clipped: el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth,
                contained: lines.length > 0 && lines.every(line =>
                    line.left >= bounds.left - 1 && line.right <= bounds.right + 1 &&
                    line.top >= bounds.top - 1 && line.bottom <= bounds.bottom + 1),
            };
        }""")
    assert metrics == {"clamp": 0, "clipped": False, "contained": True}, metrics


def _assert_excerpt(element: Locator, full_text: str) -> None:
    """Measure visible line capacity while proving the exact full DOM paragraph."""
    expect(element).to_be_visible()
    assert element.text_content() == full_text
    lines, clamp, rendered_height, content_height = element.evaluate("""el => {
            const style = getComputedStyle(el);
            return [
                el.getBoundingClientRect().height / parseFloat(style.lineHeight),
                Number(style.webkitLineClamp), el.clientHeight, el.scrollHeight,
            ];
        }""")
    assert 0 < round(lines) <= _MAX_HINT_LINES
    assert clamp == _MAX_HINT_LINES
    if full_text == _LONG_SUMMARY:
        assert round(lines) == _MAX_HINT_LINES and content_height > rendered_height
    if full_text == _MIKE_FALLBACK:
        assert content_height == rendered_height


def _assert_geometry(card: Locator) -> None:
    """Verify non-overlapping identity, score and action lanes in the production card."""
    identity, score, actions, narrow = card.evaluate(
        """(card, breakpoint) => [
            ...[".expert-identification", ".expert-score", ".expert-card-actions"].map(selector =>
                card.querySelector(selector).getBoundingClientRect().toJSON()),
            innerWidth < breakpoint,
        ]""",
        _BOOTSTRAP_MD,
    )
    _assert_disjoint(identity, score)
    _assert_disjoint(identity, actions)
    _assert_disjoint(score, actions)
    assert actions["top"] >= identity["bottom"] or (
        not narrow and actions["left"] >= identity["right"]
    )


def _assert_disjoint(first: dict[str, float], second: dict[str, float]) -> None:
    """Allow touching edges and reject mutually covered rectangular content."""
    assert min(first["bottom"], second["bottom"]) <= max(
        first["top"], second["top"]
    ) or min(first["right"], second["right"]) <= max(first["left"], second["left"]), (
        first,
        second,
    )


def _card_actions(
    card: Locator, person: _Contributor, authenticated: bool
) -> tuple[Locator, Locator]:
    """Check both action names, access policy and destination within one article."""
    profile = card.get_by_test_id(f"experts-view-profile-{person.username}")
    expect(profile).to_have_accessible_name("View profile")
    expect(profile).to_have_attribute("href", f"/experts/{person.username}/")
    if authenticated:
        contact = card.get_by_test_id(f"experts-reach-out-{person.username}")
        expect(contact).to_have_accessible_name("Reach out")
        expect(contact).to_have_accessible_description(
            f"Start an email discussion with {person.name}"
        )
        expect(contact).to_have_attribute("href", f"mailto:{person.email}")
        expect(contact).to_have_css("color", "rgb(31, 58, 95)")
    else:
        button = card.get_by_test_id(f"experts-reach-out-disabled-{person.username}")
        expect(button).to_be_disabled()
        expect(button).to_have_accessible_name(f"Reach out to {person.name}")
        contact = card.get_by_test_id("experts-reach-out-guest-tooltip")
        expect(contact).to_have_accessible_description(_GUEST_EXPLANATION)
        expect(card.get_by_role("link")).to_have_count(1)
    return profile, contact


def _assert_tab_order(page: Page, actions: list[Locator]) -> None:
    """Verify sequential real keyboard access and readable action text on focus."""
    page.get_by_test_id("experts-category-other").focus()
    for action in actions:
        page.keyboard.press("Tab")
        expect(action).to_be_focused()
        _wait_for_scroll_to_settle(page)
        coverings = action.evaluate("""el => {
                const label = el.querySelector("button") || el;
                const node = [...label.childNodes].find(node =>
                    node.nodeType === Node.TEXT_NODE && node.textContent.trim());
                const range = document.createRange();
                range.selectNodeContents(node);
                return [...range.getClientRects()].flatMap(rect =>
                    [rect.left + 1, (rect.left + rect.right) / 2, rect.right - 1].flatMap(x => {
                        const y = (rect.top + rect.bottom) / 2;
                        const hit = document.elementFromPoint(x, y);
                        return el.contains(hit) ? [] : [{
                            x, y, hit: hit?.closest("[data-testid]")?.dataset.testid || hit?.tagName,
                        }];
                    }));
            }""")
        assert (
            not coverings
        ), f"Action label is occluded: {action.get_attribute('data-testid')} {coverings}"


def _wait_for_scroll_to_settle(page: Page) -> None:
    """Wait through the browser's native smooth scrolling before testing focus visibility."""
    assert page.evaluate("""() => new Promise(resolve => {
        let lastScroll = scrollY;
        let stableFrames = 0;
        const deadline = performance.now() + 1000;
        const observe = () => {
            stableFrames = lastScroll === scrollY ? stableFrames + 1 : 0;
            lastScroll = scrollY;
            if (stableFrames >= 3) resolve(true);
            else if (performance.now() >= deadline) resolve(false);
            else requestAnimationFrame(observe);
        };
        requestAnimationFrame(observe);
    })"""), "Native focus scrolling did not settle"


def _assert_no_page_overflow(page: Page) -> None:
    """Leave vertical scrolling available while forbidding horizontal document scroll."""
    assert page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )
