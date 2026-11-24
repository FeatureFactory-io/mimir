"""Certify anonymous detail with native input and real public evidence."""

from __future__ import annotations

from http import HTTPStatus
from urllib.parse import urlsplit

import pytest
from django.apps import apps
from django.core.mail import EmailMessage
from django.db import connection
from django.urls import reverse
from playwright.sync_api import Locator, Page, expect

from methodology.models import Workflow
from tests.integration.test_experts_not_found import _FORBIDDEN_HOOKS
from tests.support.experts_data import CedarDataset
from tests.support.experts_guest_assertions import (
    assert_no_private_account_controls,
    assert_public_design_ranking,
)
from tests.support.experts_guest_browser import (
    activate_guest_tooltip,
    assert_guest_tooltip_in_viewport,
    guest_contact_wrapper,
    tab_to_guest_control,
)
from tests.support.experts_guest_contact import GUEST_CONTACT_EXPLANATION
from tests.support.experts_privacy import (
    _assert_private_markers_absent,
    _assert_public_html,
    assert_private_rows_exist,
    load_privacy_case,
)

VIEWPORTS = (
    (1280, 800),
    (1920, 1080),
    (1512, 982),
    (768, 1024),
    (1024, 768),
    (390, 844),
    (360, 800),
)
_MARIA = "mrodriguez"
_PUBLIC_BOOK = 6101
_ACTION_TIMEOUT_MS = 2500
_BOOTSTRAP_MD_WIDTH = 768
_PIXEL_TOLERANCE = 1
_OTHER_EMPTY = "No experts in Other yet — release a playbook to be the first"
DatabaseState = tuple[tuple[str, tuple[dict[str, object], ...]], ...]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("viewport", VIEWPORTS)
def test_guest_detail_with_required_viewport_keeps_tooltip_and_evidence_accessible(
    page: Page,
    live_server_url: str,
    viewport: tuple[int, int],
    mailoutbox: list[EmailMessage],
) -> None:
    """Certify the complete anonymous guest journey at one required viewport.

    :param page: Existing isolated browser page. Example: fresh anonymous Page.
    :param live_server_url: Existing real server URL. Example: http://localhost:8081.
    :param viewport: CSS width/height. Example: (360, 800).
    :param mailoutbox: Real local mail capture. Example: [].
    :return: None. Example: native inputs and unchanged database after reading.
    :raises AssertionError: If tooltip, focus, geometry, privacy or evidence fails.
    """
    dataset = load_privacy_case()
    assert_private_rows_exist(dataset)
    before = _read_only_state(mailoutbox)
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    visited = _observed_document_routes(page)
    assert not page.context.cookies()
    path = reverse("expert_detail", args=[_MARIA])
    _open_guest_design(page, live_server_url, dataset)
    _assert_native_explanations(page, viewport, f"experts-card-{_MARIA}")
    _open_guest_detail(page, f"{live_server_url}{path}", dataset, via_profile=True)
    _assert_public_layout(page, viewport[0])
    _assert_breakdown(page)
    _follow_evidence_and_return(page, dataset, live_server_url, path)
    _assert_native_explanations(page, viewport)
    _assert_guest_privacy(page, dataset)
    _read_other_and_rejections(page, live_server_url, dataset)
    _assert_composed_routes(visited)
    assert not page.context.cookies(), "Composed guest reading created a cookie"
    if _read_only_state(mailoutbox) != before:
        raise AssertionError("Composed guest reading changed rows, callbacks or mail.")


def _observed_document_routes(page: Page) -> list[str]:
    """Observe actual main-frame routes without replacing browser navigation.

    :param page: Existing anonymous browser. Example: fresh Chromium page.
    :return: Live list of public paths and queries. Example: /experts/?category=design.
    :raises Error: If the real browser cannot register its navigation listener.
    """
    routes: list[str] = []
    page.on(
        "framenavigated",
        lambda frame: (
            routes.append(
                urlsplit(frame.url).path
                + (f"?{urlsplit(frame.url).query}" if urlsplit(frame.url).query else "")
            )
            if frame == page.main_frame
            else None
        ),
    )
    return routes


def _assert_composed_routes(routes: list[str]) -> None:
    """Reject direct-detail-only evidence for the full assigned guest journey.

    :param routes: Actually observed main-frame document routes. Example: Design first.
    :return: None when list, detail, Other and both rejections were actually visited.
    :raises AssertionError: If a composed UAT branch is missing.
    """
    assert (
        len(routes) == 10
    ), "The assigned composed guest document sequence is incomplete"
    assert routes[:3] == [
        "/experts/?category=design",
        "/experts/mrodriguez/",
        "/playbooks/6101/",
    ], "The guest must follow Design, Maria and her public evidence in order"
    assert routes[3].startswith("/playbooks/6101/workflows/")
    assert routes[4:] == [
        "/experts/mrodriguez/",
        "/experts/?category=design",
        "/experts/?category=other",
        "/experts/nberg/",
        "/experts/no-such-cedar-user/",
        "/experts/",
    ], "The guest must return, inspect Other and both 404s, then recover"


def _database_state() -> DatabaseState:
    """Capture complete persisted rows without exporting their private values.

    :return: Ordered in-memory model snapshots. Example: unchanged award timestamps.
    :raises DatabaseError: If a genuine database read fails.
    """
    return tuple(
        (model._meta.label, tuple(model.objects.order_by("pk").values()))
        for model in sorted(
            apps.get_models(include_auto_created=True),
            key=lambda model: model._meta.label,
        )
    )


def _read_only_state(
    mailoutbox: list[EmailMessage],
) -> tuple[DatabaseState, tuple[EmailMessage, ...], tuple[object, ...]]:
    """Capture all persisted/M2M rows, pending callbacks and local mail in memory.

    :param mailoutbox: Actual local Django mail capture. Example: [].
    :return: Full before/after state without exporting values. Example: unchanged rows.
    :raises DatabaseError: If a genuine model-table read fails.
    """
    return _database_state(), tuple(mailoutbox), tuple(connection.run_on_commit)


def _settle_guest_document(page: Page) -> None:
    """Dismiss ordinary first-visit consent and settle actual document fonts.

    :param page: Current real guest document. Example: Design or Maria profile.
    :return: None after the native consent click and browser font readiness.
    :raises AssertionError: If the visible consent prompt cannot be dismissed.
    """
    dismiss = page.get_by_role("button", name="Not now", exact=True)
    if dismiss.is_visible():
        dismiss.click()
        expect(dismiss).to_be_hidden()
    page.evaluate("() => document.fonts.ready")


def _open_guest_design(page: Page, origin: str, dataset: CedarDataset) -> None:
    """Read the actual anonymous Design list with all five independent ranks.

    :param page: Same fresh anonymous browser. Example: no cookies.
    :param origin: Actual live-server origin. Example: http://localhost:8081.
    :param dataset: Real public/private case. Example: Maria private sentinels.
    :return: None with correct list order, public values and usable Maria link.
    :raises AssertionError: If list navigation, ranks or privacy differ.
    """
    url = f"{origin}/experts/?category=design"
    response = page.goto(url)
    assert response is not None and response.status == HTTPStatus.OK
    assert response.request.redirected_from is None
    expect(page).to_have_url(url)
    _settle_guest_document(page)
    assert_public_design_ranking(page.content())
    assert_no_private_account_controls(page.content())
    _assert_guest_privacy(page, dataset)
    expect(page.get_by_test_id("experts-category-design")).to_have_attribute(
        "aria-current", "page"
    )
    link = page.get_by_test_id(f"experts-view-profile-{_MARIA}")
    expect(link).to_have_accessible_name("View profile")
    expect(link).to_have_attribute("href", reverse("expert_detail", args=[_MARIA]))


def _open_guest_detail(
    page: Page, url: str, dataset: CedarDataset, via_profile: bool = False
) -> None:
    """Read the production route directly and settle ordinary consent and fonts.

    :param page: Fresh anonymous Chromium page. Example: empty cookies.
    :param url: Actual detail URL. Example: http://localhost:8081/experts/mrodriguez/.
    :param dataset: Persisted privacy case. Example: Maria and real private book.
    :param via_profile: Follow the actual list anchor. Example: True after Design.
    :return: None. Example: full public paragraph rendered without redirect.
    :raises AssertionError: If HTTP, public content or privacy differs.
    """
    if via_profile:
        with page.expect_navigation() as navigation:
            page.get_by_test_id(f"experts-view-profile-{_MARIA}").click()
        response = navigation.value
    else:
        response = page.goto(url)
    assert response is not None and response.status == HTTPStatus.OK
    assert response.request.redirected_from is None
    expect(page).to_have_url(url)
    _settle_guest_document(page)
    _assert_private_markers_absent(response.text(), dataset, allow_contact=False)
    _assert_guest_privacy(page, dataset)
    _assert_public_html(page.content(), dataset)
    expect(page.get_by_test_id("expert-karma-total")).to_have_text("8,200")
    expect(page.get_by_test_id("karma-source-breakdown")).to_be_visible()
    expect(page.get_by_test_id("karma-category-breakdown")).to_be_visible()


def _assert_guest_privacy(page: Page, dataset: CedarDataset) -> None:
    """Reject private DOM fields and contact destinations without value dumps.

    :param page: Actual anonymous detail or evidence page. Example: rendered DOM.
    :param dataset: Persisted private sentinels. Example: Cedar account addresses.
    :return: None. Example: no account token, private prose or email destination.
    :raises AssertionError: If hidden or visible markup leaks a private value.
    """
    _assert_private_markers_absent(page.content(), dataset, allow_contact=False)
    expect(page.locator('a[href^="mailto:"]')).to_have_count(0)


def _assert_public_layout(page: Page, width: int) -> None:
    """Check genuine paragraph styles, line bounds and read-column/rail ordering.

    :param page: Settled production detail. Example: Maria's public paragraph.
    :param width: Current CSS width. Example: 360.
    :return: None. Example: no clamp, clipping or page horizontal overflow.
    :raises AssertionError: If the required responsive recipe fails.
    """
    summary = page.get_by_test_id("expert-contribution-summary")
    assert summary.evaluate("""element => {
        const style = getComputedStyle(element), box = element.getBoundingClientRect();
        const range = document.createRange(); range.selectNodeContents(element);
        return style.overflowX === 'visible' && style.overflowY === 'visible' &&
            style.textOverflow !== 'ellipsis' && style.webkitLineClamp === 'none' &&
            Array.from(range.getClientRects()).every(line =>
                line.left >= box.left - 1 && line.right <= box.right + 1 &&
                line.top >= box.top - 1 && line.bottom <= box.bottom + 1);
    }""")
    read, rail = (
        page.get_by_test_id(test_id)
        for test_id in ("expert-read-column", "expert-context-rail")
    )
    _assert_column_geometry(read, rail, width)
    assert page.evaluate("document.documentElement.scrollWidth === innerWidth")
    assert read.evaluate("""element => Boolean(element.compareDocumentPosition(
        document.querySelector('[data-testid="expert-context-rail"]')
    ) & Node.DOCUMENT_POSITION_FOLLOWING)""")


def _assert_column_geometry(read: Locator, rail: Locator, width: int) -> None:
    """Require the existing desktop 8+4 and narrow stacked reading recipe.

    :param read: Actual primary reading column. Example: expert-read-column.
    :param rail: Actual supplementary rail. Example: expert-context-rail.
    :param width: CSS viewport width. Example: 390.
    :return: None. Example: rail follows full paragraph below Bootstrap md.
    :raises AssertionError: If columns overlap or stack in the wrong order.
    """
    body, context = read.bounding_box(), rail.bounding_box()
    assert body is not None and context is not None
    if width < _BOOTSTRAP_MD_WIDTH:
        assert context["x"] == pytest.approx(body["x"], abs=_PIXEL_TOLERANCE)
        assert context["width"] == pytest.approx(body["width"], abs=_PIXEL_TOLERANCE)
        assert context["y"] >= body["y"] + body["height"]
    else:
        assert context["y"] == pytest.approx(body["y"], abs=_PIXEL_TOLERANCE)
        assert context["x"] >= body["x"] + body["width"] - _PIXEL_TOLERANCE
        assert body["width"] == pytest.approx(
            2 * context["width"], abs=_PIXEL_TOLERANCE
        )


def _assert_native_explanations(
    page: Page, viewport: tuple[int, int], container_test_id: str | None = None
) -> None:
    """Reveal and dismiss the same native explanation by pointer and real Tab.

    :param page: Anonymous production detail. Example: disabled Maria contact.
    :param viewport: Current CSS size. Example: (360, 800).
    :param container_test_id: Maria's list card or detail root. Example: None.
    :return: None. Example: both input modes reveal a fully visible description.
    :raises AssertionError: If disabled state, actual focus or tooltip fails.
    """
    wrapper = guest_contact_wrapper(page, container_test_id)
    button = wrapper.get_by_test_id(f"experts-reach-out-disabled-{_MARIA}")
    expect(button).to_have_js_property("tagName", "BUTTON")
    expect(button).to_be_disabled()
    expect(wrapper).to_have_accessible_description(GUEST_CONTACT_EXPLANATION)
    for activation in ("hover", "keyboard"):
        if activation == "keyboard" and container_test_id is not None:
            tab_to_guest_control(
                page, page.get_by_test_id(f"experts-view-profile-{_MARIA}")
            )
        tooltip = activate_guest_tooltip(page, wrapper, activation)
        _settle_native_tooltip(tooltip)
        assert_guest_tooltip_in_viewport(page, tooltip, viewport)
        expect(button).to_be_disabled()
        if activation == "hover":
            page.mouse.move(0, 0)
        else:
            expect(wrapper).to_be_focused()
            page.keyboard.press("Tab")
            expect(wrapper).not_to_be_focused()
        expect(tooltip).to_be_hidden(timeout=_ACTION_TIMEOUT_MS)
    if container_test_id is None:
        page.get_by_test_id("expert-back-link").click(trial=True)


def _settle_native_tooltip(tooltip: Locator) -> None:
    """Observe native focus scrolling and Popper placement until both are stable.

    :param tooltip: Actual visible Bootstrap panel. Example: keyboard explanation.
    :return: None after three equal rendered-frame geometries without browser writes.
    :raises AssertionError: If real scrolling/placement does not settle in 120 frames.
    """
    assert tooltip.evaluate("""async panel => {
        let previous = '', stable = 0;
        for (let frame = 0; frame < 120; frame++) {
            await new Promise(requestAnimationFrame);
            const box = panel.getBoundingClientRect();
            const geometry = JSON.stringify([scrollX, scrollY, box.x, box.y, box.width, box.height]);
            stable = geometry === previous ? stable + 1 : 0;
            previous = geometry;
            if (stable >= 3 && panel.getAnimations().every(a => a.playState === 'finished')) return true;
        }
        return false;
    }"""), "Native tooltip scrolling or placement did not settle"


def _follow_evidence_and_return(
    page: Page, dataset: CedarDataset, origin: str, detail_path: str
) -> None:
    """Follow genuine public links to the keyboard/form workflow and return.

    :param page: Same anonymous browser. Example: guest Maria detail.
    :param dataset: Real persisted Cedar evidence. Example: public book6101.
    :param origin: Actual live server origin. Example: http://localhost:8081.
    :param detail_path: Original production path. Example: /experts/mrodriguez/.
    :return: None. Example: real evidence read, then same guest detail restored.
    :raises AssertionError: If an anchor, destination or public content is missing.
    """
    link = page.get_by_test_id(f"expert-playbook-{_PUBLIC_BOOK}")
    expect(link).to_have_attribute(
        "href", reverse("playbook_detail", args=[_PUBLIC_BOOK])
    )
    expect(link).to_have_accessible_name("View Accessibility Audit Playbook")
    link.click()
    expect(page.get_by_test_id("playbook-header")).to_contain_text(
        "Accessibility Audit Playbook"
    )
    _assert_guest_privacy(page, dataset)
    workflow = Workflow.objects.get(
        playbook_id=_PUBLIC_BOOK, name="Lead an Accessibility Review"
    )
    page.get_by_test_id(f"workflow-name-link-{workflow.pk}").click()
    expect(page).to_have_url(
        f"{origin}{reverse('workflow_detail', args=[_PUBLIC_BOOK, workflow.pk])}"
    )
    expect(page.get_by_test_id("workflow-name")).to_have_text(workflow.name)
    for activity in (
        "Trace Keyboard Focus",
        "Review Form Feedback",
        "Document Recovery Paths",
    ):
        expect(page.get_by_test_id("activities-graph")).to_contain_text(activity)
    _assert_guest_privacy(page, dataset)
    _open_guest_detail(page, f"{origin}{detail_path}", dataset)


def _read_other_and_rejections(page: Page, origin: str, dataset: CedarDataset) -> None:
    """Complete the same anonymous route through empty Other and both safe 404s.

    :param page: Same guest browser after reading Maria's public evidence.
    :param origin: Actual Django live-server origin. Example: http://localhost:8081.
    :param dataset: Persisted privacy probes. Example: Maria and zero-total Nora.
    :return: None after genuine empty/404 pages and usable anonymous recovery.
    :raises AssertionError: If Other, rejection status, privacy or recovery fails.
    """
    page.get_by_test_id("expert-back-link").click()
    page.get_by_test_id("experts-category-other").click()
    expect(page).to_have_url(f"{origin}/experts/?category=other")
    expect(page.get_by_test_id("experts-category-other")).to_have_attribute(
        "aria-current", "page"
    )
    expect(
        page.get_by_test_id("experts-leaderboard").get_by_role("article")
    ).to_have_count(0)
    empty = page.get_by_test_id("experts-empty")
    expect(empty).to_have_text(_OTHER_EMPTY)
    expect(empty).to_be_visible()
    _assert_guest_privacy(page, dataset)
    presentations = [
        _read_guest_rejection(page, origin, username, dataset)
        for username in ("nberg", "no-such-cedar-user")
    ]
    assert presentations[0] == presentations[1]
    page.get_by_test_id("expert-unavailable-back-link").click()
    expect(page).to_have_url(f"{origin}/experts/")
    _assert_guest_privacy(page, dataset)


def _read_guest_rejection(
    page: Page, origin: str, username: str, dataset: CedarDataset
) -> tuple[str, str, str]:
    """Read a real generic 404 using the richer multi-private-book privacy case.

    S21's browser helper assumes exactly one private book; this composed case
    retains S20's multiple persisted boundaries and reuses its safe assertion.

    :param page: Same anonymous browser. Example: Other was just inspected.
    :param origin: Real live-server origin. Example: http://localhost:8081.
    :param username: Requested unavailable subject. Example: nberg.
    :param dataset: Real S20 privacy case. Example: multiple private books.
    :return: Generic presentation tuple. Example: unavailable/Back/Experts.
    :raises AssertionError: If status, safe presentation or actual recovery fails.
    """
    url = f"{origin}/experts/{username}/"
    response = page.goto(url)
    assert response is not None and response.status == HTTPStatus.NOT_FOUND
    assert response.request.redirected_from is None
    expect(page).to_have_url(url)
    _assert_guest_privacy(page, dataset)
    for hook in _FORBIDDEN_HOOKS:
        expect(page.get_by_test_id(hook)).to_have_count(0)
    heading = page.get_by_test_id("expert-unavailable")
    back = page.get_by_test_id("expert-unavailable-back-link")
    expect(heading).to_have_text("Expert unavailable")
    expect(heading).to_be_visible()
    expect(back).to_have_accessible_name("Back to Experts")
    expect(back).to_have_attribute("href", "/experts/")
    back.click(trial=True)
    return heading.inner_text(), back.inner_text(), str(back.get_attribute("href"))


def _assert_breakdown(page: Page) -> None:
    """Read the four displayed sources separately from category subtotals.

    :param page: Real Maria detail page. Example: guest Chromium response.
    :return: None. Example: source rows 5000/1600/1200/400 and total8200.
    :raises AssertionError: If source values, total or category rows differ.
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
