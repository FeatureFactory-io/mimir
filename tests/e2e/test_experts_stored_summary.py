"""Certify one successfully refreshed paragraph through actual production screens."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator, Mapping
from dataclasses import replace
from http import HTTPStatus
from typing import Any

import pytest
from django.apps import apps
from django.contrib.sessions.models import Session
from django.core.mail import EmailMessage
from django.test import Client, TestCase
from django.urls import reverse
from e2e_helpers import login
from playwright.sync_api import Locator, Page, expect

from methodology.llm.base import LLMResponse
from methodology.models import AgentInteraction, ExpertProfile
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
from tests.support.experts_summary_data import (
    SUMMARY_SCRIPTS,
    load_summary_script,
    prepare_summary_submission,
    summary_processing_scope,
)
from tests.support.scripted_llm import ScriptedLLM

_MARIA = "mrodriguez"
_SENTENCES = 9
_SETUP_CALLS = 2
_PIXEL_TOLERANCE = 1
_CORRELATION_ID = "s24-browser-stored-setup"
_TAB_TARGETS = "a[href], button, input, select, textarea, [tabindex]"
_VIEWPORTS = (
    (1280, 800),
    (1920, 1080),
    (1512, 982),
    (768, 1024),
    (1024, 768),
    (390, 844),
    (360, 800),
)


@pytest.fixture
def cedar_summary(
    cedar_dataset: CedarDataset, client: Client
) -> Iterator[Mapping[str, str]]:
    """Refresh Maria through S23, retaining its actual captured port during reads.

    :param cedar_dataset: Runner-owned real Cedar objects. Example: CEDAR-RFP-01.
    :param client: Real Django client for setup. Example: Maria's signed-in client.
    :return: Username and complete persisted oracle. Example: {"summary": "..."}.
    :raises AssertionError: For failed setup or an extra model call during reading.
    """
    paragraph = _oracle_summary(cedar_dataset)
    pip = prepare_summary_submission(cedar_dataset)
    script = load_summary_script(
        SUMMARY_SCRIPTS / "PRF-EXPERTS-03/submission_happy.json", pip.changes.get().pk
    )
    assert isinstance(script[0], LLMResponse)
    script = (replace(script[0], content=paragraph), *script[1:])
    client.force_login(cedar_dataset.users_by_username[_MARIA])
    with summary_processing_scope(script, rates={"scripted": ("3", "15")}) as llm:
        _submit_refresh(client, paragraph, pip.pk, llm)
        yield {"username": _MARIA, "summary": paragraph}
        assert len(llm.calls) == _SETUP_CALLS, "Reading requested model completion."


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("viewport", _VIEWPORTS)
def test_stored_summary_with_target_viewport_preserves_visual_contract(
    cedar_summary: Mapping[str, str],
    page: Page,
    live_server_url: str,
    viewport: tuple[int, int],
    mailoutbox: list[EmailMessage],
) -> None:
    """Read identical stored prose through real clamps, expansion and public detail.

    :param cedar_summary: Successful refresh's full oracle. Example: nine sentences.
    :param page: Existing isolated Chromium page. Example: page.
    :param live_server_url: Existing real server origin. Example: http://localhost:9000.
    :param viewport: Exact IA CSS dimensions. Example: (390, 844).
    :param mailoutbox: Existing locmem mail. Example: unchanged setup notifications.
    :return: None after the full contract. Example: unchanged text and domain state.
    :raises AssertionError: For changed text, broken geometry, controls or side effects.
    """
    width, height = viewport
    page.set_viewport_size({"width": width, "height": height})
    login(page, live_server_url, cedar_summary["username"], CEDAR_PASSWORD)
    baseline = _domain_state(mailoutbox)
    paragraph = cedar_summary["summary"]
    _certify_own_summary(page, live_server_url, paragraph)
    _certify_card_and_public_summary(page, live_server_url, paragraph)
    if _domain_state(mailoutbox) != baseline:
        raise AssertionError(
            "Stored-summary reading changed domain/session/mail state."
        )


def _oracle_summary(dataset: CedarDataset) -> str:
    """Obtain the independent nine-sentence oracle and reconcile stored baseline.

    :param dataset: Imported Cedar oracle and accounts. Example: CEDAR-RFP-01.
    :return: Complete public paragraph. Example: Maria's original nine sentences.
    :raises AssertionError: For a mismatched fixture or missing final sentence.
    """
    paragraph = next(
        person["summary"]
        for person in dataset.oracle["people"]
        if person["username"] == _MARIA
    )
    assert isinstance(paragraph, str) and len(paragraph.split(". ")) == _SENTENCES
    assert paragraph.endswith(
        "availability and project fit still require a conversation."
    )
    profile = ExpertProfile.objects.get(user=dataset.users_by_username[_MARIA])
    assert profile.contribution_summary == paragraph
    return paragraph


def _submit_refresh(
    client: Client, paragraph: str, pip_id: int, llm: ScriptedLLM
) -> None:
    """Establish successful persisted usage and trace via an actual submission POST.

    :param client: Real Maria client. Example: authenticated Django Client.
    :param paragraph: Full independent public oracle. Example: nine sentences.
    :param pip_id: New draft's primary key. Example: actual database-generated ID.
    :param llm: Existing finite transport. Example: summary then assessment turns.
    :return: None after successful real lifecycle completion. Example: SUCCESS.
    :raises AssertionError: For wrong HTTP state, prose, usage or persisted trace.
    """
    with TestCase.captureOnCommitCallbacks(execute=True):
        response = client.post(
            reverse("pip_submit_review", kwargs={"pk": pip_id}),
            headers={"X-Request-ID": _CORRELATION_ID},
        )
    assert response.status_code == HTTPStatus.FOUND
    assert len(llm.calls) == _SETUP_CALLS
    profile = ExpertProfile.objects.get(user__username=_MARIA)
    assert profile.summary_status == ExpertProfile.SummaryStatus.SUCCESS
    assert profile.contribution_summary == paragraph and profile.summary_updated_at
    interaction = AgentInteraction.objects.get(correlation_id=_CORRELATION_ID)
    assert interaction.outcome == AgentInteraction.Outcome.SUCCESS
    assert interaction.input_tokens and interaction.output_tokens
    assert interaction.estimated_cost_usd is not None and interaction.events
    assert profile.last_summary_correlation_id == interaction.correlation_id


def _certify_own_summary(page: Page, origin: str, paragraph: str) -> None:
    """Follow native keyboard expansion and collapse on the existing own profile.

    :param page: Actual authenticated Maria browser. Example: Chromium page.
    :param origin: Real server origin. Example: http://localhost:9000.
    :param paragraph: Complete expected stored source. Example: nine sentences.
    :return: None after four-line, full, then restored four-line states.
    :raises AssertionError: For wrong text, ARIA, geometry or native focus behavior.
    """
    _open_document(page, origin + reverse("profile"))
    summary = page.get_by_test_id("profile-contribution-summary")
    toggle = page.get_by_test_id("profile-summary-toggle")
    expect(summary).to_have_js_property("textContent", paragraph)
    _assert_summary_geometry(summary, 4)
    _assert_toggle(page, toggle, summary, False)
    _tab_to_toggle(page, toggle)
    _assert_preview_readable(page)
    page.keyboard.press("Enter")
    _assert_toggle(page, toggle, summary, True)
    _assert_summary_geometry(summary, None)
    _read_last_line(page, summary)
    expect(toggle).to_be_focused()
    page.keyboard.press("Space")
    _assert_toggle(page, toggle, summary, False)
    _assert_summary_geometry(summary, 4)
    expect(summary).to_have_js_property("textContent", paragraph)
    expect(toggle).to_be_focused()
    _assert_preview_readable(page)
    _assert_no_horizontal_overflow(page)


def _certify_card_and_public_summary(page: Page, origin: str, paragraph: str) -> None:
    """Follow the real Design-card action into the full public contribution screen.

    :param page: Existing browser after own-profile reading. Example: Maria session.
    :param origin: Real server origin. Example: http://localhost:9000.
    :param paragraph: Exact stored source. Example: full nine-sentence summary.
    :return: None after two-line card and unclipped complete detail checks.
    :raises AssertionError: For a changed source, wrong link or clipped public text.
    """
    _open_document(page, origin + reverse("experts_list") + "?category=design")
    hint = page.get_by_test_id(f"experts-card-hint-{_MARIA}")
    expect(hint).to_have_js_property("textContent", paragraph)
    hint.scroll_into_view_if_needed()
    _assert_summary_geometry(hint, 2)
    _assert_no_horizontal_overflow(page)
    link = page.get_by_test_id(f"experts-view-profile-{_MARIA}")
    path = reverse("expert_detail", args=[_MARIA])
    expect(link).to_have_attribute("href", path)
    with page.expect_response(origin + path) as navigation:
        link.click()
    assert navigation.value.status == HTTPStatus.OK
    assert navigation.value.request.redirected_from is None
    expect(page).to_have_url(origin + path)
    public = page.get_by_test_id("expert-contribution-summary")
    expect(public).to_have_js_property("textContent", paragraph)
    _assert_summary_geometry(public, None)
    _read_last_line(page, public)
    _assert_no_horizontal_overflow(page)


def _assert_summary_geometry(node: Locator, maximum_lines: int | None) -> None:
    """Measure actual line clamp, rendered height and hidden or complete overflow.

    :param node: Actual rendered paragraph. Example: expert-contribution-summary.
    :param maximum_lines: Collapsed limit or full text. Example: 2, 4 or None.
    :return: None for bounded previews or unclipped full text. Example: success.
    :raises AssertionError: For incorrect clamp, clipping or horizontal bounds.
    :raises ValueError: If maximum_lines is not 2, 4 or None.
    """
    if maximum_lines not in (2, 4, None):
        raise ValueError("Expected a two/four-line preview or complete paragraph.")
    expect(node).to_be_visible()
    geometry = node.evaluate("""async element => {
        await document.fonts.ready;
        const style = getComputedStyle(element), box = element.getBoundingClientRect();
        return {height:box.height,line:parseFloat(style.lineHeight),
            client:element.clientHeight,scroll:element.scrollHeight,
            clamp:style.webkitLineClamp,overflow:style.overflowY,
            left:box.left,right:box.right,width:document.documentElement.clientWidth,
            font:style.fontFamily,size:parseFloat(style.fontSize)};
    }""")
    assert geometry["height"] > 0 and geometry["line"] > 0
    assert geometry["size"] >= 14 and "Montserrat" in geometry["font"]
    assert geometry["left"] >= -_PIXEL_TOLERANCE
    assert geometry["right"] <= geometry["width"] + _PIXEL_TOLERANCE
    if maximum_lines is None:
        assert geometry["clamp"] == "none" and geometry["overflow"] == "visible"
        assert abs(geometry["client"] - geometry["scroll"]) <= _PIXEL_TOLERANCE
    else:
        assert geometry["clamp"] == str(maximum_lines)
        assert geometry["overflow"] == "hidden"
        assert geometry["height"] == pytest.approx(
            maximum_lines * geometry["line"], abs=_PIXEL_TOLERANCE
        )
        assert geometry["scroll"] > geometry["client"] + _PIXEL_TOLERANCE


def _assert_toggle(
    page: Page, toggle: Locator, summary: Locator, expanded: bool
) -> None:
    """Check the native expansion control's accessible state and unique target.

    :param page: Real own-profile document. Example: Maria profile.
    :param toggle: Existing native button. Example: profile-summary-toggle.
    :param summary: Controlled paragraph. Example: profile-contribution-summary.
    :param expanded: Expected state. Example: True after Enter.
    :return: None when label, ARIA and target agree. Example: Show less.
    :raises AssertionError: For wrong accessible semantics or target relationship.
    """
    label = "Show less" if expanded else "Show more"
    expect(toggle).to_have_js_property("tagName", "BUTTON")
    expect(toggle).to_have_attribute("type", "button")
    expect(toggle).to_have_attribute("aria-expanded", str(expanded).lower())
    expect(toggle).to_have_accessible_name(label)
    expect(toggle).to_have_text(label, use_inner_text=True)
    target = summary.get_attribute("id")
    assert target and page.locator(f'[id="{target}"]').count() == 1
    expect(toggle).to_have_attribute("aria-controls", target)


def _tab_to_toggle(page: Page, toggle: Locator) -> None:
    """Reach the actual button through the native sequential keyboard order.

    :param page: Newly navigated profile. Example: browser focus starts on body.
    :param toggle: Visible expansion button. Example: Show more.
    :return: None once Tab puts native focus on the button. Example: focused.
    :raises AssertionError: If the native control cannot be reached.
    """
    for _ in range(page.locator(_TAB_TARGETS).count()):
        page.keyboard.press("Tab")
        if toggle.evaluate("element => document.activeElement === element"):
            return
    raise AssertionError("Summary expansion is absent from native Tab order.")


def _assert_preview_readable(page: Page) -> None:
    """Await native focus scrolling so the four-line preview and control are readable.

    :param page: Actual own-profile document. Example: focused Show more button.
    :return: None when both boxes fit. Example: four lines and Show more visible.
    :raises AssertionError: If native scrolling fails to reveal the preview/control.
    """
    page.wait_for_function("""() => {
        const box=id=>document.querySelector(`[data-testid="${id}"]`).getBoundingClientRect();
        const summary=box('profile-contribution-summary'), toggle=box('profile-summary-toggle');
        const header=box('realm-navbar');
        return Math.min(summary.top,toggle.top)>=Math.max(0,header.bottom)-1 &&
            Math.max(summary.bottom,toggle.bottom)<=innerHeight+1;
    }""")


def _read_last_line(page: Page, summary: Locator) -> None:
    """Use ordinary scrolling to expose and hit-test the paragraph's final line.

    :param page: Real browser reading a full paragraph. Example: own/public detail.
    :param summary: Unclamped paragraph. Example: nine-sentence public summary.
    :return: None when its actual final text is visible and unobscured.
    :raises AssertionError: If the final line is clipped or covered.
    """
    summary.scroll_into_view_if_needed()
    bounds = _last_line_bounds(summary)
    viewport = page.viewport_size
    assert viewport is not None
    page.mouse.wheel(0, max(0, bounds["bottom"] - viewport["height"] + 80))
    page.wait_for_function(
        """testId => {
        const e=document.querySelector(`[data-testid="${testId}"]`);
        const range=document.createRange();range.selectNodeContents(e);
        const boxes=[...range.getClientRects()], last=boxes.at(-1);
        const header=document.querySelector('[data-testid="realm-navbar"]');
        return last.bottom <= innerHeight && last.top >= Math.max(0,header?.getBoundingClientRect().bottom ?? 0);
    }""",
        arg=summary.get_attribute("data-testid"),
    )
    bounds = _last_line_bounds(summary)
    assert bounds["visible"] and bounds["unobscured"], "Final summary line is obscured."


def _last_line_bounds(summary: Locator) -> dict[str, Any]:
    """Measure the final actual text rectangle without modifying DOM or scrolling.

    :param summary: Full rendered paragraph. Example: public contribution summary.
    :return: Bounds and native hit-test. Example: {"bottom": 700, "visible": True}.
    :raises AssertionError: If the paragraph has no rendered text rectangle.
    """
    return summary.evaluate("""element => {
        const range=document.createRange();range.selectNodeContents(element);
        const boxes=[...range.getClientRects()], b=boxes.at(-1);
        if (!b) throw new Error('Missing rendered summary text');
        const x=(b.left+b.right)/2,y=(b.top+b.bottom)/2;
        const hit=document.elementFromPoint(x,y);
        return {bottom:b.bottom,visible:b.top>=0&&b.bottom<=innerHeight,
            unobscured:hit===element||element.contains(hit)};
    }""")


def _open_document(page: Page, url: str) -> None:
    """Navigate to an actual production document and wait for final font layout.

    :param page: Existing isolated browser. Example: Chromium page.
    :param url: Runner-owned production URL. Example: /auth/user/profile/.
    :return: None after direct HTTP200 and font readiness. Example: loaded.
    :raises AssertionError: For failure, redirect or a mismatched destination.
    """
    response = page.goto(url)
    assert response is not None and response.status == HTTPStatus.OK
    assert response.request.redirected_from is None
    expect(page).to_have_url(url)
    page.evaluate("document.fonts.ready")


def _assert_no_horizontal_overflow(page: Page) -> None:
    """Require ordinary document flow without unintended horizontal scrolling.

    :param page: Actual current screen. Example: own/list/public detail.
    :return: None when body and root fit the CSS viewport. Example: 390 pixels.
    :raises AssertionError: For unintended root or body horizontal overflow.
    """
    assert page.evaluate("""() => {
        const root=document.documentElement;
        return root.scrollWidth<=root.clientWidth+1&&document.body.scrollWidth<=root.clientWidth+1;
    }"""), "Stored-summary screen overflows horizontally."


def _domain_state(mailoutbox: list[EmailMessage]) -> tuple[str, ...]:
    """Fingerprint all model/M2M rows and mail, preserving decoded session identity.

    :param mailoutbox: Actual existing locmem mail. Example: setup notifications.
    :return: Safe complete state hashes. Example: one SHA-256 per model/session/mail.
    :raises RuntimeError: If the real owned database cannot be read.
    """
    models = sorted(
        apps.get_models(include_auto_created=True), key=lambda m: m._meta.label
    )
    rows = [
        tuple(model.objects.order_by("pk").values_list())
        for model in models
        if model is not Session
    ]
    rows.append(tuple((s.pk, s.get_decoded()) for s in Session.objects.order_by("pk")))
    rows.append(tuple((type(m).__name__, m.__dict__) for m in mailoutbox))
    return tuple(hashlib.sha256(repr(row).encode()).hexdigest() for row in rows)
