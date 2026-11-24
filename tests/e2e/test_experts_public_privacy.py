"""Real Chromium certification of the public contribution boundary."""

from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.test import Client
from django.urls import reverse
from playwright.sync_api import Page, expect
from rest_framework.authtoken.models import Token

from methodology.models import (
    AgentInteraction,
    ExpertProfile,
    KarmaAward,
    Playbook,
    ProcessImprovementProposal,
)
from tests.support.experts_data import CedarDataset
from tests.support.experts_privacy import (
    EXCLUDED_EVIDENCE_CASES,
    _assert_excluded_evidence,
    _assert_private_markers_absent,
    _assert_public_html,
    assert_private_rows_exist,
    assert_public_response,
    load_privacy_case,
)

_MARIA = "mrodriguez"
_PUBLIC_BOOK_ID = 6101
_READ_ONLY_MODELS = (
    User,
    Token,
    Playbook,
    ProcessImprovementProposal,
    KarmaAward,
    ExpertProfile,
    AgentInteraction,
)
DatabaseState = tuple[tuple[dict[str, object], ...], ...]


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_public_detail_with_guest_browser_omits_private_markup(
    page: Page,
    live_server_url: str,
    client: Client,
    mailoutbox: list[EmailMessage],
) -> None:
    """Read a real public profile while its private records actually exist.

    :param page: Existing isolated guest Chromium page, e.g. no account cookies.
    :param live_server_url: Function-scoped Django origin, e.g. localhost URL.
    :param client: Real anonymous Django client for the designated public DTO.
    :param mailoutbox: Real local mail capture, e.g. an empty list.
    :return: None after actual HTML/DOM, evidence and read-only checks pass.
    :raises AssertionError: For a leak, lost public content or changed persistence.
    """
    dataset = load_privacy_case()
    assert_private_rows_exist(dataset)
    state_before, mail_before = _database_state(), tuple(mailoutbox)
    path = reverse("expert_detail", args=[_MARIA])
    response = client.get(path)
    assert_public_response(response, dataset, authenticated=False)
    person = response.context["person"]
    assert not page.context.cookies()
    navigation = page.goto(f"{live_server_url}{path}")
    assert navigation is not None and navigation.status == HTTPStatus.OK
    assert navigation.request.redirected_from is None
    expect(page).to_have_url(f"{live_server_url}{path}")
    _assert_public_browser_content(page, dataset, person)
    assert all(
        cookie["name"] != settings.SESSION_COOKIE_NAME
        for cookie in page.context.cookies()
    )
    _assert_state_unchanged(state_before, mail_before, mailoutbox)


def _assert_public_browser_content(
    page: Page, dataset: CedarDataset, person: Mapping[str, object]
) -> None:
    """Check the entire live DOM and visible public evidence, without secret dumps.

    :param page: Actual guest page after its successful production navigation.
    :param dataset: Persisted Cedar privacy case with independent summary oracle.
    :param person: Allowlisted DTO from the separate real anonymous HTTP request.
    :return: None when hidden and visible markup preserve the public boundary.
    :raises AssertionError: For private text/controls or missing public content.
    """
    html = page.content()
    _assert_private_markers_absent(html, dataset, allow_contact=False)
    _assert_public_html(html, dataset)
    for visibility, status in EXCLUDED_EVIDENCE_CASES:
        _assert_excluded_evidence(html, person, dataset, visibility, status)
    expect(page.get_by_test_id("expert-name")).to_have_text("Maria Rodriguez")
    summary = page.get_by_test_id("expert-contribution-summary")
    expect(summary).to_be_visible()
    expect(summary).to_have_text(str(person["summary"]))
    evidence = page.get_by_test_id(f"expert-playbook-{_PUBLIC_BOOK_ID}")
    expect(evidence).to_be_visible()
    expect(evidence).to_have_attribute(
        "href", reverse("playbook_detail", args=[_PUBLIC_BOOK_ID])
    )
    expect(evidence).to_have_accessible_name("View Accessibility Audit Playbook")
    expect(page.get_by_test_id("expert-karma-total")).to_have_text("8,200")


def _database_state() -> DatabaseState:
    """Snapshot all rows and fields of the seven privacy-sensitive domain models.

    :return: Ordered immutable outer snapshots, e.g. unchanged award PK/timestamps.
    :raises RuntimeError: An actual ORM failure propagates rather than passing.
    """
    return tuple(
        tuple(model.objects.order_by("pk").values()) for model in _READ_ONLY_MODELS
    )


def _assert_state_unchanged(
    before: DatabaseState,
    mail_before: tuple[EmailMessage, ...],
    mailoutbox: list[EmailMessage],
) -> None:
    """Reject any persisted or mail effect without printing private row values.

    :param before: Complete snapshots after owned fixture setup.
    :param mail_before: Existing local messages before either read request.
    :param mailoutbox: The same actual Django mail capture after browser reading.
    :return: None when all tracked records and mail are byte-equivalent in value.
    :raises AssertionError: If either guest GET changed rows or mail.
    """
    if _database_state() != before:
        raise AssertionError("Guest privacy reads changed a tracked domain model.")
    if tuple(mailoutbox) != mail_before:
        raise AssertionError("Guest privacy reads changed the local email outbox.")
