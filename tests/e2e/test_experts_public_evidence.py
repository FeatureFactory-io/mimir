"""S19 real browser evidence navigation."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from django.core import mail
from django.urls import reverse
from e2e_helpers import login
from playwright.sync_api import Locator, Page, Response, expect

from methodology.models import AgentInteraction, KarmaAward, Workflow
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset, load_cedar_baseline

_ELENA = "esvensson"
_PROFILE_PATH = "/experts/mrodriguez/"
_PLAYBOOK_ID = 6101
_PLAYBOOK_PATH = "/playbooks/6101/"
_PLAYBOOK_TITLE = "Accessibility Audit Playbook"
_WORKFLOW_NAME = "Lead an Accessibility Review"
_ACTIVITY_NAMES = (
    "Trace Keyboard Focus",
    "Review Form Feedback",
    "Document Recovery Paths",
)


@pytest.fixture
def s19_browser_dataset(transactional_db: None) -> CedarDataset:
    """Prepare real Cedar objects before the browser begins navigation.

    :param transactional_db: Shared live-server test DB. Example: None.
    :return: Cedar dataset. Example: dataset.playbooks_by_pk[6101].
    :raises ValueError: If Cedar source data is invalid.
    """
    return load_cedar_baseline()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("username", [_ELENA, None], ids=["elena", "guest"])
def test_public_evidence_with_real_browser_navigation_reaches_cedar_workflow(
    page: Page,
    live_server_url: str,
    s19_browser_dataset: CedarDataset,
    username: str | None,
) -> None:
    """Click existing evidence/workflow links and inspect readable activities.

    :param page: Existing fresh Playwright page. Example: page.
    :param live_server_url: Existing function-scoped server. Example: "http://localhost:8000".
    :param s19_browser_dataset: Prepared Cedar graph. Example: playbook 6101.
    :param username: Authenticated actor or guest. Example: None.
    :return: None. Example: None after real document/status/visibility checks.
    :raises AssertionError: If links, destination, status or readable evidence differ.
    """
    awards = tuple(KarmaAward.objects.order_by("pk").values_list())
    assert awards
    interactions = AgentInteraction.objects.count()
    if username is not None:
        account = s19_browser_dataset.users_by_username[username]
        login(page, live_server_url, account.username, CEDAR_PASSWORD)

    profile_url = f"{live_server_url}{_PROFILE_PATH}"
    _assert_document_response(page.goto(profile_url), profile_url)
    expect(
        page.get_by_role("heading", name="Maria Rodriguez", exact=True)
    ).to_be_visible()
    _assert_profile_permissions(page, username)
    _follow_link(page, _evidence_link(page), live_server_url, _PLAYBOOK_PATH)
    _assert_playbook_detail(page, username)

    workflows = page.get_by_test_id("workflows-section")
    workflow = Workflow.objects.get(playbook_id=_PLAYBOOK_ID, name=_WORKFLOW_NAME)
    workflow_link = workflows.get_by_role("link", name=_WORKFLOW_NAME, exact=True)
    workflow_path = reverse("workflow_detail", args=[_PLAYBOOK_ID, workflow.pk])
    _follow_link(page, workflow_link, live_server_url, workflow_path)
    _assert_workflow_detail(page)
    assert tuple(KarmaAward.objects.order_by("pk").values_list()) == awards
    assert AgentInteraction.objects.count() == interactions
    assert not getattr(mail, "outbox", [])


def _assert_profile_permissions(page: Page, username: str | None) -> None:
    """Check the session identity and existing contact access without using it.

    :param page: Current browser page. Example: Maria's profile.
    :param username: Authenticated viewer or guest. Example: None.
    :return: None when the expected identity and permission controls are present.
    :raises AssertionError: If the current session or contact access differs.
    """
    contact = page.get_by_role("toolbar", name="Expert contact")
    if username is None:
        expect(page.get_by_test_id("login-link")).to_be_visible()
        expect(page.get_by_test_id("user-display")).to_have_count(0)
        expect(
            contact.get_by_role("button", name="Reach out to Maria Rodriguez")
        ).to_be_disabled()
        expect(contact.get_by_role("link")).to_have_count(0)
    else:
        expect(page.get_by_test_id("user-display")).to_have_text(username)
        expect(
            contact.get_by_role("link", name="Reach out", exact=True)
        ).to_be_visible()


def _evidence_link(page: Page) -> Locator:
    """Find the named evidence anchor in the published playbook entry.

    :param page: Current browser page. Example: Maria's profile.
    :return: Rendered evidence anchor. Example: View Accessibility Audit Playbook.
    :raises AssertionError: If the displayed entry or version is missing.
    """
    evidence = page.get_by_test_id("expert-public-playbooks")
    link = evidence.get_by_test_id("expert-playbook-6101").and_(
        evidence.get_by_role("link", name=f"View {_PLAYBOOK_TITLE}", exact=True)
    )
    entry = link.locator("..")
    expect(
        entry.get_by_role("heading", name=_PLAYBOOK_TITLE, exact=True)
    ).to_be_visible()
    expect(entry.get_by_text("Design · v1.0", exact=True)).to_be_visible()
    return link


def _follow_link(page: Page, link: Locator, origin: str, path: str) -> None:
    """Click a rendered anchor and verify its direct document response.

    :param page: Existing browser page. Example: the Cedar expert profile.
    :param link: Rendered anchor. Example: View Accessibility Audit Playbook.
    :param origin: Active local origin. Example: "http://localhost:8000".
    :param path: Expected destination path. Example: "/playbooks/6101/".
    :return: None once the clicked document loads.
    :raises AssertionError: If the href, document response or final URL differs.
    """
    expect(link).to_have_attribute("href", path)
    with page.expect_response(
        lambda response: response.request.is_navigation_request()
        and response.frame == page.main_frame
    ) as navigation:
        link.click()
    destination = f"{origin}{path}"
    _assert_document_response(navigation.value, destination)
    expect(page).to_have_url(destination)


def _assert_document_response(response: Response | None, url: str) -> None:
    """Verify a direct, successful browser document response.

    :param response: Playwright response. Example: click navigation response.
    :param url: Exact destination URL. Example: the existing local detail route.
    :return: None if the document is served directly.
    :raises AssertionError: If the document is missing, redirected, or fails.
    """
    assert response is not None
    assert response.request.resource_type == "document"
    assert response.request.method == "GET"
    assert response.request.redirected_from is None
    assert response.status == HTTPStatus.OK
    assert response.url == url


def _assert_playbook_detail(page: Page, username: str | None) -> None:
    """Check visible public release details and the guest sign-in affordance.

    :param page: Existing browser page. Example: playbook detail.
    :param username: Authenticated viewer or guest. Example: None.
    :return: None when the expected release is displayed.
    :raises AssertionError: If the public version or guest controls differ.
    """
    header = page.get_by_test_id("playbook-header")
    expect(
        header.get_by_role("heading", name=_PLAYBOOK_TITLE, exact=True)
    ).to_be_visible()
    expect(header.get_by_test_id("visibility-badge")).to_have_text("Public")
    expect(header.get_by_test_id("status-badge")).to_have_text("Released")
    expect(header.get_by_test_id("version-badge")).to_have_text("v1.0")
    if username is None:
        expect(page.get_by_test_id("guest-banner-sign-in")).to_be_visible()
    else:
        expect(page.get_by_test_id("guest-auth-banner")).to_have_count(0)


def _assert_workflow_detail(page: Page) -> None:
    """Read the actual workflow graph without triggering any activity actions.

    :param page: Existing browser page. Example: workflow detail.
    :return: None if all three Cedar activity labels can be read.
    :raises AssertionError: If the workflow, available actions or labels differ.
    """
    detail = page.get_by_test_id("workflow-detail-page")
    expect(
        detail.get_by_role("heading", name=_WORKFLOW_NAME, exact=True)
    ).to_be_visible()
    expect(detail.get_by_test_id("workflow-edit-btn")).to_have_count(0)
    expect(detail.get_by_test_id("workflow-submit-pip")).to_have_count(0)
    expect(detail.get_by_test_id("add-activity-btn")).to_have_count(0)
    graph = detail.get_by_test_id("activities-graph").locator("svg")
    expect(graph).to_be_visible()
    for name in _ACTIVITY_NAMES:
        label = graph.get_by_text(name, exact=True)
        expect(label).to_be_visible()
        label.scroll_into_view_if_needed()
        expect(label).to_be_in_viewport(ratio=1)
