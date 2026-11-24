"""Certify anonymous detail with native input and real public evidence."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from django.apps import apps
from django.conf import settings
from django.core.mail import EmailMessage
from django.urls import reverse
from playwright.sync_api import Locator, Page, expect

from methodology.models import Workflow
from tests.support.experts_data import CedarDataset
from tests.support.experts_guest_browser import (
    activate_guest_tooltip,
    assert_guest_tooltip_in_viewport,
    guest_contact_wrapper,
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
DatabaseState = tuple[tuple[str, tuple[dict[str, object], ...]], ...]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("viewport", VIEWPORTS)
def test_guest_detail_with_required_viewport_keeps_tooltip_and_evidence_accessible(
    page: Page,
    live_server_url: str,
    viewport: tuple[int, int],
    mailoutbox: list[EmailMessage],
) -> None:
    """Certify actual hover, keyboard explanation and readable public evidence.

    :param page: Existing isolated browser page. Example: fresh anonymous Page.
    :param live_server_url: Existing real server URL. Example: http://localhost:8081.
    :param viewport: CSS width/height. Example: (360, 800).
    :param mailoutbox: Real local mail capture. Example: [].
    :return: None. Example: native inputs and unchanged database after reading.
    :raises AssertionError: If tooltip, focus, geometry, privacy or evidence fails.
    """
    dataset = load_privacy_case()
    assert_private_rows_exist(dataset)
    before, mail_before = _database_state(), tuple(mailoutbox)
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    assert not page.context.cookies()
    path = reverse("expert_detail", args=[_MARIA])
    _open_guest_detail(page, f"{live_server_url}{path}", dataset)
    _assert_public_layout(page, viewport[0])
    _assert_breakdown(page)
    _assert_native_explanations(page, viewport)
    _follow_evidence_and_return(page, dataset, live_server_url, path)
    _assert_guest_privacy(page, dataset)
    assert all(
        cookie["name"] != settings.SESSION_COOKIE_NAME
        for cookie in page.context.cookies()
    )
    if _database_state() != before or tuple(mailoutbox) != mail_before:
        raise AssertionError("Guest detail/evidence reading changed database or mail.")


def _database_state() -> DatabaseState:
    """Capture complete persisted rows without exporting their private values.

    :return: Ordered in-memory model snapshots. Example: unchanged award timestamps.
    :raises DatabaseError: If a genuine database read fails.
    """
    return tuple(
        (model._meta.label, tuple(model.objects.order_by("pk").values()))
        for model in sorted(apps.get_models(), key=lambda model: model._meta.label)
    )


def _open_guest_detail(page: Page, url: str, dataset: CedarDataset) -> None:
    """Read the production route directly and settle ordinary consent and fonts.

    :param page: Fresh anonymous Chromium page. Example: empty cookies.
    :param url: Actual detail URL. Example: http://localhost:8081/experts/mrodriguez/.
    :param dataset: Persisted privacy case. Example: Maria and real private book.
    :return: None. Example: full public paragraph rendered without redirect.
    :raises AssertionError: If HTTP, public content or privacy differs.
    """
    response = page.goto(url)
    assert response is not None and response.status == HTTPStatus.OK
    assert response.request.redirected_from is None
    expect(page).to_have_url(url)
    dismiss = page.get_by_role("button", name="Not now", exact=True)
    if dismiss.is_visible():
        dismiss.click()
        expect(dismiss).to_be_hidden()
    page.evaluate("() => document.fonts.ready")
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


def _assert_native_explanations(page: Page, viewport: tuple[int, int]) -> None:
    """Reveal and dismiss the same native explanation by pointer and real Tab.

    :param page: Anonymous production detail. Example: disabled Maria contact.
    :param viewport: Current CSS size. Example: (360, 800).
    :return: None. Example: both input modes reveal a fully visible description.
    :raises AssertionError: If disabled state, actual focus or tooltip fails.
    """
    wrapper = guest_contact_wrapper(page, None)
    button = wrapper.get_by_test_id(f"experts-reach-out-disabled-{_MARIA}")
    expect(button).to_have_js_property("tagName", "BUTTON")
    expect(button).to_be_disabled()
    expect(wrapper).to_have_accessible_description(GUEST_CONTACT_EXPLANATION)
    for activation in ("hover", "keyboard"):
        tooltip = activate_guest_tooltip(page, wrapper, activation)
        assert_guest_tooltip_in_viewport(page, tooltip, viewport)
        expect(button).to_be_disabled()
        if activation == "hover":
            page.mouse.move(0, 0)
        else:
            expect(wrapper).to_be_focused()
            page.keyboard.press("Tab")
            expect(wrapper).not_to_be_focused()
        expect(tooltip).to_be_hidden(timeout=_ACTION_TIMEOUT_MS)
    page.get_by_test_id("expert-back-link").click(trial=True)


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
    expect(page.get_by_test_id("workflow-name")).to_have_text(workflow.name)
    for activity in (
        "Trace Keyboard Focus",
        "Review Form Feedback",
        "Document Recovery Paths",
    ):
        expect(page.get_by_test_id("activities-graph")).to_contain_text(activity)
    _assert_guest_privacy(page, dataset)
    _open_guest_detail(page, f"{origin}{detail_path}", dataset)


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
