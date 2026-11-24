"""CEDAR-JOURNEY-01 and automated UAT-18-01 on the real Experts surfaces."""

from __future__ import annotations

import json
from collections.abc import Callable
from http import HTTPStatus
from time import monotonic

import pytest
from django.core.mail import EmailMessage
from django.urls import reverse
from e2e_helpers import LOGIN_URL_PATH, login
from playwright.sync_api import Locator, Page, Request, Response, expect
from rest_framework.authtoken.models import Token

from methodology.models import AgentInteraction, ExpertProfile, KarmaAward, Workflow
from tests.e2e.test_experts_list_s03 import DESIGN_RANKING
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
from tests.support.experts_logs import capture_experts_logs

_ELENA = "esvensson"
_MARIA = "mrodriguez"
_SOFIA = "sreed"
_LIST_PATH = "/experts/"
_DESIGN_PATH = f"{_LIST_PATH}?category=design"
_MARIA_PATH = f"{_LIST_PATH}{_MARIA}/"
_AUDIT_ID = 6101
_AUDIT_PATH = f"/playbooks/{_AUDIT_ID}/"
_AUDIT_TITLE = "Accessibility Audit Playbook"
_AUDIT_VERSION = "v1.0"
_WORKFLOW_NAME = "Lead an Accessibility Review"
_ACTIVITIES = (
    "Trace Keyboard Focus",
    "Review Form Feedback",
    "Document Recovery Paths",
)
_SOFIA_PLAYBOOKS = (
    "Service Blueprinting for Complex Portfolios",
    "Design Operations Governance",
)
_MARIA_TOTAL = 8200
_MARIA_SENTENCES = 9
_SOURCES = (
    ("Released playbooks", 5000),
    ("PIP contributions", 1600),
    ("Consumption", 1200),
    ("Learning", 400),
)
_CATEGORY_ROWS = ("Design", "7,200", "Development", "1,000")
_CONTACT_DESTINATION = "mailto:maria.rodriguez@example.com"
_PRIVATE_SENTINELS = (
    "Cedar Bid Pricing",
    "Internal staffing notes for Cedar",
    "DEMO_ONLY_NOT_A_REAL_TOKEN",
)
_SUMMARY_LOGGERS = (
    "methodology.services.contribution_summary_service",
    "methodology.services.contribution_summary_boundary",
)
_READ_METHODS = {"GET", "HEAD", "OPTIONS"}
_TARGET_SECONDS = 5 * 60


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_cedar_nomination_with_elena_follows_evidence_and_records_contact_handoff(
    page: Page,
    live_server_url: str,
    cedar_dataset: CedarDataset,
    mailoutbox: list[EmailMessage],
    caplog: pytest.LogCaptureFixture,
    record_property: Callable[[str, str], None],
) -> None:
    """Certify Elena's evidence-led journey and record a scripted nomination.

    :param page: Existing fresh Chromium page.
    :param live_server_url: Function-scoped Django server, e.g. http://localhost:8081.
    :param cedar_dataset: Independently restored Cedar accounts and oracle.
    :param mailoutbox: Real test email backend's outbox.
    :param caplog: Real summary and model-boundary logger capture.
    :param record_property: Pytest result metadata for the external receipt.
    :return: None once the full browser path and read-only behavior are verified.
    :raises AssertionError: If browser evidence or persisted state differs.
    """
    baseline = _domain_rows()
    assert baseline[0] and baseline[1] and not mailoutbox
    nonread_requests = _observe_nonread_requests(page)
    elena = cedar_dataset.users_by_username[_ELENA]
    login(page, live_server_url, elena.username, CEDAR_PASSWORD)

    with capture_experts_logs(caplog, _SUMMARY_LOGGERS):
        note, elapsed_seconds = _perform_nomination(
            page, live_server_url, cedar_dataset
        )

    assert _domain_rows() == baseline
    assert not mailoutbox and not any(
        row.name in _SUMMARY_LOGGERS for row in caplog.records
    )
    assert nonread_requests == [("POST", f"{live_server_url}{LOGIN_URL_PATH}")]
    assert page.context.pages == [page]
    _record_nomination(record_property, page, note, elapsed_seconds)


def _perform_nomination(
    page: Page, origin: str, dataset: CedarDataset
) -> tuple[str, float]:
    """Follow and time the scripted operator's real route from the sidebar.

    :param page: Existing Chromium page already authenticated as Elena.
    :param origin: Function-scoped live-server origin.
    :param dataset: Restored Cedar history and independent oracle.
    :return: Completed external note and monotonic elapsed seconds.
    :raises AssertionError: If the observed evidence or contact path differs.
    """
    sidebar_link = _authenticated_experts_link(page)
    started_at = monotonic()
    _follow_link(page, sidebar_link, origin, _LIST_PATH)
    _select_design(page, origin)
    _review_sofia(page, origin, dataset)
    _back_to_design(page, origin)
    candidate = _review_maria(page, origin, dataset)
    example = _follow_audit_playbook(page, origin)
    activities = _review_workflow(page, origin)
    destination = _return_to_contact(page, origin, candidate)
    note = _nomination_note(candidate, example, activities, destination)
    return note, monotonic() - started_at


def _authenticated_experts_link(page: Page) -> Locator:
    """Find the real Experts action in Elena's existing app sidebar.

    :param page: Browser already logged in as Elena.
    :return: Rendered Experts anchor in the Collaborate group.
    :raises AssertionError: If the actor or action is missing.
    """
    expect(page.get_by_test_id("user-display")).to_have_text(_ELENA)
    sidebar = page.get_by_test_id("app-sidebar")
    collaborate = sidebar.get_by_role("list", name="Collaborate", exact=True)
    link = collaborate.get_by_role("link", name="Experts", exact=True)
    expect(link).to_be_visible()
    expect(link).to_have_attribute("data-testid", "nav-experts")
    return link


def _follow_link(page: Page, link: Locator, origin: str, path: str) -> None:
    """Click a rendered anchor and require a direct, successful document GET.

    :param page: Current Chromium page.
    :param link: Actual rendered control, e.g. Maria's View profile anchor.
    :param origin: Function-scoped live-server origin.
    :param path: Expected local href, e.g. /experts/mrodriguez/.
    :return: None when the clicked document has loaded.
    :raises AssertionError: If the href, response or final URL differs.
    """
    expect(link).to_have_attribute("href", path)
    with page.expect_response(
        lambda response: response.request.is_navigation_request()
        and response.frame == page.main_frame
    ) as navigation:
        link.click()
    destination = f"{origin}{path}"
    _assert_document(navigation.value, destination)
    assert navigation.value.request.redirected_from is None
    expect(page).to_have_url(destination)


def _assert_document(response: Response, destination: str) -> None:
    """Check an observed document response independently of the final location.

    :param response: Playwright's actual navigation response.
    :param destination: Full expected URL, including a category query when present.
    :return: None when this is the successful GET for the expected document.
    :raises AssertionError: If the status, method or route differs.
    """
    assert response.url == destination
    assert response.status == HTTPStatus.OK
    assert response.request.method == "GET"
    assert response.request.resource_type == "document"


def _select_design(page: Page, origin: str) -> None:
    """Select Design from Experts and read the five ranked cards.

    :param page: Chromium at the real default Experts page.
    :param origin: Function-scoped live-server origin.
    :return: None once navigation, current category and order are verified.
    :raises AssertionError: If the visible list or its state differs.
    """
    expect(page.get_by_role("heading", name="Experts", exact=True)).to_be_visible()
    expect(page.get_by_test_id("experts-category-development")).to_have_attribute(
        "aria-current", "page"
    )
    design = page.get_by_role("link", name="Design", exact=True).and_(
        page.get_by_test_id("experts-category-design")
    )
    _follow_link(page, design, origin, _DESIGN_PATH)
    _assert_design_ranking(page)


def _assert_design_ranking(page: Page) -> None:
    """Read the exact five ordered Design cards, including the overall totals.

    :param page: Current page at the clicked or restored Design leaderboard.
    :return: None once ranks, identities and displayed totals are verified.
    :raises AssertionError: If the five browser cards or selected category differ.
    """
    expect(page.get_by_test_id("experts-category-design")).to_have_attribute(
        "aria-current", "page"
    )
    leaderboard = page.get_by_test_id("experts-leaderboard")
    cards = leaderboard.get_by_role("article")
    expect(cards).to_have_count(len(DESIGN_RANKING))
    for rank, (name, points) in enumerate(DESIGN_RANKING, start=1):
        card = cards.nth(rank - 1)
        expect(card.get_by_role("heading", name=name, exact=True)).to_be_visible()
        expect(card.get_by_test_id("expert-card-rank")).to_have_text(str(rank))
        karma = card.get_by_test_id("expert-card-karma")
        expect(karma).to_be_visible()
        expect(karma).to_have_text(points)
    for username in ("mchen", "tmartin"):
        expect(leaderboard.get_by_test_id(f"experts-card-{username}")).to_have_count(0)


def _open_profile(page: Page, origin: str, username: str) -> None:
    """Follow the selected expert card's own accessible View profile anchor.

    :param page: Existing Design page with the five ranked cards.
    :param origin: Function-scoped live-server origin.
    :param username: Target Cedar account, e.g. mrodriguez.
    :return: None once that card's anchor loaded its public profile.
    :raises AssertionError: If the link or direct response is wrong.
    """
    card = page.get_by_test_id(f"experts-card-{username}")
    link = card.get_by_test_id(f"experts-view-profile-{username}").and_(
        card.get_by_role("link", name="View profile", exact=True)
    )
    _follow_link(page, link, origin, f"{_LIST_PATH}{username}/")


def _public_summary(page: Page, dataset: CedarDataset, username: str) -> str:
    """Compare the full displayed prose to the persisted and fixture originals.

    :param page: Public profile opened via the ranked card.
    :param dataset: Independently restored real Cedar dataset.
    :param username: Profile being read, e.g. sreed.
    :return: Complete observed text, without a visual line clamp.
    :raises AssertionError: If the displayed, stored or fixture prose differs.
    """
    person = next(
        person for person in dataset.oracle["people"] if person["username"] == username
    )
    stored = ExpertProfile.objects.get(user=dataset.users_by_username[username])
    prose = page.get_by_test_id("expert-read-column").get_by_test_id(
        "expert-contribution-summary"
    )
    expect(prose).to_be_visible()
    expect(prose).to_have_css("-webkit-line-clamp", "none")
    actual = prose.inner_text()
    assert actual and actual == stored.contribution_summary == person["summary"]
    return actual


def _review_sofia(page: Page, origin: str, dataset: CedarDataset) -> None:
    """Read Sofia's credible service-blueprint and design-operations evidence.

    :param page: Existing ranked Design page.
    :param origin: Function-scoped live-server origin.
    :param dataset: Real Cedar history and independent fixture prose.
    :return: None once Sofia's public summary and released entries are readable.
    :raises AssertionError: If her identity or displayed evidence differs.
    """
    _open_profile(page, origin, _SOFIA)
    expect(page.get_by_role("heading", name="Sofia Reed", exact=True)).to_be_visible()
    prose = _public_summary(page, dataset, _SOFIA)
    assert (
        "service boundaries, operating models, and cross-team design coordination"
        in prose
    )
    evidence = page.get_by_test_id("expert-public-playbooks")
    for title in _SOFIA_PLAYBOOKS:
        expect(evidence.get_by_role("heading", name=title, exact=True)).to_be_visible()
        link = evidence.get_by_role("link", name=f"View {title}", exact=True)
        link.scroll_into_view_if_needed()
        expect(link).to_be_in_viewport(ratio=1)


def _back_to_design(page: Page, origin: str) -> None:
    """Use browser history from Sofia so the Design query must survive.

    :param page: Actual Sofia profile opened from Design.
    :param origin: Function-scoped live-server origin.
    :return: None when history restores the same ranked Design state.
    :raises AssertionError: If history drops the selection or ranking.
    """
    _go_back(page, f"{origin}{_DESIGN_PATH}")
    _assert_design_ranking(page)


def _go_back(page: Page, destination: str) -> None:
    """Return with native browser history, allowing a cached document restore.

    :param page: Chromium on a document reached through a real anchor.
    :param destination: Exact previous URL, potentially with its category query.
    :return: None once browser history restores the expected location.
    :raises AssertionError: If a response fails or the wrong location is restored.
    """
    response = page.go_back()
    if response is not None:
        _assert_document(response, destination)
    expect(page).to_have_url(destination)


def _review_maria(page: Page, origin: str, dataset: CedarDataset) -> str:
    """Read Maria's full profile, reconciled totals and public-only context.

    :param page: Design list restored after reading Sofia.
    :param origin: Function-scoped live-server origin.
    :param dataset: Real Cedar history and independent fixture prose.
    :return: Observed profile name, e.g. Maria Rodriguez.
    :raises AssertionError: If identity, full evidence or privacy checks fail.
    """
    _open_profile(page, origin, _MARIA)
    name = page.get_by_role("heading", name="Maria Rodriguez", exact=True)
    expect(name).to_be_visible()
    expect(page.get_by_test_id("expert-primary-category")).to_have_text("Design")
    expect(page.get_by_test_id("expert-karma-total")).to_have_text(f"{_MARIA_TOTAL:,}")
    paragraph = _public_summary(page, dataset, _MARIA)
    assert paragraph.count(".") == _MARIA_SENTENCES
    _assert_maria_breakdown(page)
    _assert_maria_private_values_absent(page, dataset)
    return name.inner_text()


def _assert_maria_breakdown(page: Page) -> None:
    """Reconcile Maria's actual source and category rows to the headline total.

    :param page: Maria's public detail page.
    :return: None once the four source rows and two category rows are verified.
    :raises AssertionError: If the recorded sources or their reconciliation differ.
    """
    rail = page.get_by_test_id("expert-context-rail")
    table = rail.get_by_test_id("karma-source-breakdown")
    expect(table).to_be_visible()
    rows = table.locator("tbody").get_by_role("row")
    expect(rows.get_by_role("rowheader")).to_have_text([label for label, _ in _SOURCES])
    amounts = rows.get_by_role("cell")
    expect(amounts).to_have_text([f"{points:,}" for _, points in _SOURCES])
    actual_total = sum(
        int(amount.replace(",", "")) for amount in amounts.all_inner_texts()
    )
    assert actual_total == _MARIA_TOTAL
    expect(table.locator("tfoot").get_by_role("cell")).to_have_text(f"{actual_total:,}")
    categories = rail.get_by_test_id("karma-category-breakdown")
    expect(categories).to_be_visible()
    expect(categories.locator("dt, dd")).to_have_text(list(_CATEGORY_ROWS))
    assert (
        sum(
            int(amount.replace(",", ""))
            for amount in categories.locator("dd").all_inner_texts()
        )
        == actual_total
    )


def _assert_maria_private_values_absent(page: Page, dataset: CedarDataset) -> None:
    """Check rendered markup for Cedar's private values and Maria's actual token.

    :param page: Maria's public profile as viewed by Elena.
    :param dataset: Independently restored history, including Maria's account.
    :return: None once the public document is free of these values.
    :raises AssertionError: If the browser receives private fixture content.
    """
    token = Token.objects.get(user=dataset.users_by_username[_MARIA])
    html = page.content()
    assert not any(
        value in html for value in (*_PRIVATE_SENTINELS, token.key)
    ), "Maria's public profile included a private value."


def _follow_audit_playbook(page: Page, origin: str) -> str:
    """Open Maria's actual evidence entry and confirm the public release version.

    :param page: Maria's public profile with the listed release.
    :param origin: Function-scoped live-server origin.
    :return: Title and version from the opened document.
    :raises AssertionError: If the evidence link or release badges differ.
    """
    evidence = page.get_by_test_id("expert-public-playbooks")
    entry = evidence.get_by_test_id(f"expert-playbook-{_AUDIT_ID}").and_(
        evidence.get_by_role("link", name=f"View {_AUDIT_TITLE}", exact=True)
    )
    expect(
        entry.locator("..").get_by_text(f"Design · {_AUDIT_VERSION}", exact=True)
    ).to_be_visible()
    _follow_link(page, entry, origin, _AUDIT_PATH)
    header = page.get_by_test_id("playbook-header")
    title = header.get_by_role("heading", name=_AUDIT_TITLE, exact=True)
    version = header.get_by_test_id("version-badge")
    expect(title).to_be_visible()
    expect(version).to_have_text(_AUDIT_VERSION)
    expect(header.get_by_test_id("visibility-badge")).to_have_text("Public")
    expect(header.get_by_test_id("status-badge")).to_have_text("Released")
    return f"{title.inner_text()} {version.inner_text()}"


def _review_workflow(page: Page, origin: str) -> tuple[str, ...]:
    """Open the existing workflow and read three on-screen activity labels.

    :param page: Released Accessibility Audit Playbook detail.
    :param origin: Function-scoped live-server origin.
    :return: Observed activity labels in the Cedar example, including recovery.
    :raises AssertionError: If the clicked workflow or readable examples differ.
    """
    workflow = Workflow.objects.get(playbook_id=_AUDIT_ID, name=_WORKFLOW_NAME)
    path = reverse("workflow_detail", args=[_AUDIT_ID, workflow.pk])
    link = page.get_by_test_id("workflows-section").get_by_role(
        "link", name=_WORKFLOW_NAME, exact=True
    )
    _follow_link(page, link, origin, path)
    detail = page.get_by_test_id("workflow-detail-page")
    expect(
        detail.get_by_role("heading", name=_WORKFLOW_NAME, exact=True)
    ).to_be_visible()
    graph = detail.get_by_test_id("activities-graph").locator("svg")
    expect(graph).to_be_visible()
    observed: list[str] = []
    for activity in _ACTIVITIES:
        label = graph.get_by_text(activity, exact=True)
        label.scroll_into_view_if_needed()
        expect(label).to_be_in_viewport(ratio=1)
        actual = label.text_content()
        assert actual == activity
        observed.append(actual)
    return tuple(observed)


def _return_to_contact(page: Page, origin: str, candidate: str) -> str:
    """Return through the playbook and inspect Reach out without activating it.

    :param page: Existing public workflow detail.
    :param origin: Function-scoped live-server origin.
    :param candidate: Previously read profile identity, e.g. Maria Rodriguez.
    :return: Actual href of the authenticated Reach out control.
    :raises AssertionError: If history, actor or destination differs.
    """
    _go_back(page, f"{origin}{_AUDIT_PATH}")
    _go_back(page, f"{origin}{_MARIA_PATH}")
    expect(page.get_by_test_id("user-display")).to_have_text(_ELENA)
    expect(page.get_by_role("heading", name=candidate, exact=True)).to_be_visible()
    toolbar = page.get_by_role("toolbar", name="Expert contact")
    contact = toolbar.get_by_role("link", name="Reach out", exact=True)
    contact.scroll_into_view_if_needed()
    expect(contact).to_be_in_viewport(ratio=1)
    expect(contact).to_have_attribute("href", _CONTACT_DESTINATION)
    destination = contact.get_attribute("href")
    assert destination == _CONTACT_DESTINATION
    return destination


def _nomination_note(
    candidate: str, example: str, activities: tuple[str, ...], destination: str
) -> str:
    """Write the scripted operator's external note from the verified evidence.

    :param candidate: Observed public profile identity.
    :param example: Observed title and release version.
    :param activities: Observed keyboard focus, form feedback and recovery labels.
    :param destination: Inspected mailto href, never activated.
    :return: External nomination note for the fictional Cedar case.
    :raises ValueError: If the observed destination lacks its mailto scheme.
    """
    scheme, address = destination.split(":", maxsplit=1)
    if scheme != "mailto" or not address:
        raise ValueError("A mailto discussion destination is required.")
    keyboard, feedback, recovery = activities
    return (
        f"I nominate {candidate} for a discussion about Noor's Cedar bank onboarding brief. "
        f"Her published {example} includes {keyboard}, {feedback} and {recovery}. "
        "These examples address the brief's keyboard navigation, understandable form errors "
        f"and recovery. Next step is to request a discussion at {address}. "
        "Availability is unconfirmed."
    )


def _domain_rows() -> tuple[tuple[tuple[object, ...], ...], ...]:
    """Snapshot persisted ledger, profile and model interaction rows.

    :return: Complete rows in stable primary-key order before or after the journey.
    """
    return (
        tuple(KarmaAward.objects.order_by("pk").values_list()),
        tuple(ExpertProfile.objects.order_by("pk").values_list()),
        tuple(AgentInteraction.objects.order_by("pk").values_list()),
    )


def _observe_nonread_requests(page: Page) -> list[tuple[str, str]]:
    """Track browser write methods and any attempted external mailto request.

    :param page: Existing page before the normal login helper submits the form.
    :return: Mutable event list populated by real Playwright request events.
    """
    requests: list[tuple[str, str]] = []

    def observe(request: Request) -> None:
        """Record a method and URL without inspecting credentials or payloads.

        :param request: Playwright browser request event.
        :return: None after filtering ordinary read requests.
        """
        if request.method not in _READ_METHODS or request.url.startswith("mailto:"):
            requests.append((request.method, request.url))

    page.on("request", observe)
    return requests


def _record_nomination(
    record_property: Callable[[str, str], None], page: Page, note: str, elapsed: float
) -> None:
    """Attach timing and the external note to the pytest result metadata.

    :param record_property: Pytest's result-property recorder.
    :param page: Final Chromium page, used to read actual viewport dimensions.
    :param note: Scripted operator nomination written after inspecting the handoff.
    :param elapsed: Monotonic seconds from the Experts action through the note.
    :return: None once the complete result is attached.
    :raises AssertionError: If the elapsed time or viewport is unavailable.
    """
    viewport = page.evaluate("() => ({width: innerWidth, height: innerHeight})")
    assert viewport == page.viewport_size and elapsed > 0
    receipt = {
        "classification": "automated UAT path with a scripted external operator note",
        "actor": _ELENA,
        "elapsed_monotonic_seconds": elapsed,
        "proposed_target_seconds": _TARGET_SECONDS,
        "automated_path_within_proposed_target": elapsed <= _TARGET_SECONDS,
        "viewport_css_pixels": viewport,
        "nomination_text": note,
        "contact_activated": False,
        "email_sent": False,
    }
    record_property("cedar_nomination", json.dumps(receipt))
