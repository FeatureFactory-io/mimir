"""Browser assertions shared by the anonymous list and detail contracts."""

from __future__ import annotations

from typing import Literal

from playwright.sync_api import Locator, Page, expect

from tests.support.experts_guest_contact import GUEST_CONTACT_EXPLANATION

_MAX_TAB_PRESSES = 40
_FOCUS_SETTLE_FRAME_LIMIT = 120
_FOCUS_STABLE_FRAME_COUNT = 3
_TOOLTIP_TIMEOUT_MS = 2500


def guest_contact_wrapper(page: Page, container_test_id: str | None) -> Locator:
    """Locate the guest wrapper with semantic test hooks and fail on ambiguity.

    :param page: Actual browser page. Example: production Design list.
    :param container_test_id: Card scope or document root. Example: "experts-card-mrodriguez"; None for detail.
    :return: Unique wrapper Locator. Example: scoped experts-reach-out-guest-tooltip.
    :raises AssertionError: If the expected wrapper is absent or ambiguous.
    """
    scope = page.get_by_test_id(container_test_id) if container_test_id else page
    wrapper = scope.get_by_test_id("experts-reach-out-guest-tooltip")
    expect(wrapper).to_have_count(1)
    expect(wrapper).to_be_visible()
    expect(wrapper).to_have_attribute("tabindex", "0")
    return wrapper


def tab_to_guest_control(page: Page, target: Locator) -> None:
    """Reach a control through native sequential focus from the current stop.

    Wait for each native focus scroll before the next Tab so rapid automation
    cannot leave a later control behind an earlier smooth-scroll destination.
    Intermediate focus stops may be partly visible; the requested target must
    end fully in the viewport.

    :param page: Page accepting keyboard input. Example: the anonymous Design list.
    :param target: Expected focus stop. Example: the Sign In link or Maria's wrapper.
    :return: None when the actual active element is the target.
    :raises AssertionError: If focus scrolling fails or traversal misses the target.
    """
    expect(target).not_to_be_focused()
    for _ in range(_MAX_TAB_PRESSES):
        page.keyboard.press("Tab")
        assert page.evaluate(
            """async ({frameLimit, stableFrames}) => {
            let previous = '', stable = 0;
            const focused = document.activeElement;
            for (let frame = 0; frame < frameLimit; frame++) {
                await new Promise(requestAnimationFrame);
                if (document.activeElement !== focused) return false;
                const box = focused.getBoundingClientRect();
                const geometry = JSON.stringify([scrollX, scrollY, box.x, box.y, box.width, box.height]);
                stable = geometry === previous ? stable + 1 : 0;
                previous = geometry;
                if (stable >= stableFrames) return true;
            }
            return false;
        }""",
            {
                "frameLimit": _FOCUS_SETTLE_FRAME_LIMIT,
                "stableFrames": _FOCUS_STABLE_FRAME_COUNT,
            },
        ), "Native Tab focus scrolling or focus identity did not settle"
        if target.evaluate("(control) => control === document.activeElement"):
            break
    expect(target).to_be_focused(timeout=_TOOLTIP_TIMEOUT_MS)
    expect(target).to_be_in_viewport(ratio=1, timeout=_TOOLTIP_TIMEOUT_MS)


def _settle_guest_control_position(wrapper: Locator) -> None:
    """Finish native hover scrolling before the pointer enters the control.

    :param wrapper: Actual guest control. Example: Maria's disabled-contact span.
    :return: None at stable visible geometry. Example: three equal native frames.
    :raises AssertionError: If native scrolling or layout does not settle.
    :raises Error: If the actual browser cannot scroll or inspect the control.
    """
    wrapper.scroll_into_view_if_needed(timeout=_TOOLTIP_TIMEOUT_MS)
    assert wrapper.evaluate(
        """async (control, {frameLimit, stableFrames}) => {
        let previous = '', stable = 0;
        for (let frame = 0; frame < frameLimit; frame++) {
            await new Promise(requestAnimationFrame);
            const box = control.getBoundingClientRect();
            const geometry = JSON.stringify([scrollX, scrollY, box.x, box.y, box.width, box.height]);
            stable = geometry === previous ? stable + 1 : 0;
            previous = geometry;
            const visible = box.top >= 0 && box.left >= 0 &&
                box.bottom <= innerHeight && box.right <= innerWidth;
            if (visible && stable >= stableFrames) return true;
        }
        return false;
    }""",
        {
            "frameLimit": _FOCUS_SETTLE_FRAME_LIMIT,
            "stableFrames": _FOCUS_STABLE_FRAME_COUNT,
        },
    ), "Native hover scrolling did not settle inside the viewport"


def activate_guest_tooltip(
    page: Page, wrapper: Locator, activation: Literal["hover", "keyboard"]
) -> Locator:
    """Reveal the actual Bootstrap tooltip by pointer or bounded Tab traversal.

    Locator hover performs another implicit scroll even after prepositioning.
    Move the real pointer to the verified native hitpoint without restarting it.

    :param page: Actual page. Example: fresh anonymous Chromium context.
    :param wrapper: Unique focusable contact wrapper. Example: Maria's list wrapper.
    :param activation: Real interaction. Example: "keyboard" uses Tab.
    :return: Visible page-level tooltip Locator with exact restriction text.
    :raises AssertionError: If the trigger fails or its visible explanation differs.
    :raises ValueError: If activation is unsupported.
    """
    if activation == "hover":
        expect(wrapper).not_to_be_focused()
        _settle_guest_control_position(wrapper)
        point = wrapper.evaluate("""control => {
            const box = control.getBoundingClientRect();
            const x = box.x + box.width / 2, y = box.y + box.height / 2;
            const hit = document.elementFromPoint(x, y);
            return control.contains(hit) ? {x, y} : null;
        }""")
        assert point is not None, "The actual pointer target is covered"
        page.mouse.move(point["x"], point["y"])
        expect(wrapper).not_to_be_focused()
    elif activation == "keyboard":
        tab_to_guest_control(page, wrapper)
    else:
        raise ValueError(f"Unsupported guest tooltip activation: {activation}")

    tooltip_id = wrapper.get_attribute("aria-describedby")
    assert tooltip_id, "Activation left the wrapper without its description"
    tooltip = page.get_by_role("tooltip").and_(page.locator(f'[id="{tooltip_id}"]'))
    expect(tooltip).to_be_visible(timeout=_TOOLTIP_TIMEOUT_MS)
    expect(tooltip).to_have_text(GUEST_CONTACT_EXPLANATION)
    expect(wrapper).to_have_accessible_description(GUEST_CONTACT_EXPLANATION)
    return tooltip


def assert_guest_tooltip_in_viewport(
    page: Page, tooltip: Locator, viewport: tuple[int, int]
) -> None:
    """Check the visible tooltip panel and every rendered line for occlusion.

    :param page: Actual page after tooltip activation. Example: scrolled Maria card.
    :param tooltip: Visible rendered tooltip. Example: Bootstrap role=tooltip portal.
    :param viewport: CSS pixel dimensions. Example: (360, 800).
    :return: None when the entire tooltip and text are inside the document viewport.
    :raises AssertionError: For missing geometry, clipping or horizontal overflow.
    """
    width, height = viewport
    assert page.viewport_size == {"width": width, "height": height}
    assert tooltip.evaluate("""async tooltip => {
            await Promise.all(tooltip.getAnimations().map(animation => animation.finished));
            const panel = tooltip.getBoundingClientRect();
            const inner = tooltip.querySelector('.tooltip-inner');
            if (!inner?.firstChild || !Number(getComputedStyle(tooltip).opacity)) return false;
            const content = inner.getBoundingClientRect();
            const range = document.createRange();
            range.selectNodeContents(inner);
            const lines = Array.from(range.getClientRects());
            const within = (rect, bounds) => rect.left >= bounds.left &&
                rect.right <= bounds.right && rect.top >= bounds.top && rect.bottom <= bounds.bottom;
            const screen = {left: 0, top: 0, right: innerWidth, bottom: innerHeight};
            return within(panel, screen) && lines.length > 0 && lines.every(line => {
                const y = line.top + line.height / 2;
                return within(line, content) && within(line, screen) &&
                    [0.1, 0.5, 0.9].every(fraction =>
                        inner.contains(document.elementFromPoint(line.left + line.width * fraction, y))
                    );
            });
        }"""), f"Guest explanation is clipped or covered at {width}×{height}"
    assert page.evaluate("document.documentElement.scrollWidth === innerWidth")
