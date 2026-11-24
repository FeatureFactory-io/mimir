"""Real Chromium certification of a positive contributor without public books."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from http import HTTPStatus
from typing import cast

import pytest
from django.core.mail import EmailMessage
from django.urls import reverse
from e2e_helpers import login
from playwright.sync_api import Page, expect

from methodology.models import ExpertProfile, KarmaAward, Playbook
from methodology.services.experts_service import ExpertsService
from tests.integration.test_experts_empty_evidence import (
    _persisted_private_markers,
    _snapshot,
)
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
from tests.support.experts_privacy import _assert_private_markers_absent

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

_SAM = "skim"
_ELENA = "esvensson"
_EMPTY_EVIDENCE = "No public released playbooks to show"
_SAM_POINTS = 4800
_SAM_SOURCES = {"Released": 0, "PIP": 4600, "Consumption": 0, "Learning": 200}
DatabaseSnapshot = tuple[tuple[dict[str, object], ...], ...]


def test_expert_detail_with_positive_sam_shows_empty_evidence_in_browser(
    page: Page,
    live_server_url: str,
    cedar_dataset: CedarDataset,
    mailoutbox: list[EmailMessage],
) -> None:
    """Read Sam's real positive profile after normal Elena authentication.

    :param page: Existing isolated Chromium page, e.g. a fresh browser context.
    :param live_server_url: Function-scoped Django origin, e.g. localhost URL.
    :param cedar_dataset: Restored real Cedar records, e.g. positive Sam Kim.
    :param mailoutbox: Real local mail capture, e.g. an empty message list.
    :return: None after the visible profile, empty evidence and state reconcile.
    :raises AssertionError: For wrong identity, evidence, privacy or side effects.
    """
    summary = _assert_persisted_sam(cedar_dataset)
    private_markers = _persisted_private_markers(cedar_dataset)
    login(page, live_server_url, _ELENA, CEDAR_PASSWORD)
    expect(page.get_by_test_id("user-display")).to_have_text(_ELENA)
    before, mail_before = _snapshot(), tuple(mailoutbox)
    destination = live_server_url + reverse("expert_detail", args=[_SAM])
    navigation = page.goto(destination)
    assert navigation is not None and navigation.status == HTTPStatus.OK
    assert navigation.request.redirected_from is None
    expect(page).to_have_url(destination)
    _assert_visible_sam(page, summary, cedar_dataset)
    _assert_private_content_absent(page, cedar_dataset, private_markers)
    _assert_state_unchanged(before, mail_before, mailoutbox)


def _assert_persisted_sam(dataset: CedarDataset) -> str:
    """Verify real positive history and the independently declared stored prose.

    :param dataset: Restored Cedar objects and oracle, e.g. Sam's 4,800 points.
    :return: Actual stored public paragraph, e.g. Sam's two complete sentences.
    :raises AssertionError: For absent data, an authored release or wrong history.
    """
    sam = dataset.users_by_username[_SAM]
    projection = ExpertsService().project_user(sam.pk)
    assert projection.total_points == _SAM_POINTS
    assert projection.primary_category == "research"
    assert dict(projection.source_points) == _SAM_SOURCES
    assert not sam.karma_awards.filter(
        source_kind=KarmaAward.SourceKind.RELEASE
    ).exists()
    assert not Playbook.objects.filter(
        author=sam, visibility="public", status="released"
    ).exists()
    summary = ExpertProfile.objects.get(user=sam).contribution_summary
    people = cast(Sequence[Mapping[str, object]], dataset.oracle["people"])
    expected = next(person for person in people if person["username"] == _SAM)
    assert summary and summary == expected["summary"]
    return summary


def _assert_visible_sam(page: Page, summary: str, dataset: CedarDataset) -> None:
    """Inspect the actual positive identity, full prose and empty evidence rail.

    :param page: Elena's real browser on Sam's profile.
    :param summary: Complete stored public paragraph, e.g. two Research sentences.
    :param dataset: Restored account data, e.g. Sam's authorized contact destination.
    :return: None when the exact visible page and contact contract agree.
    :raises AssertionError: For missing prose, evidence actions or wrong contact.
    """
    expect(page.get_by_test_id("user-display")).to_have_text(_ELENA)
    expect(page.get_by_role("heading", name="Sam Kim", exact=True)).to_be_visible()
    expect(page.get_by_test_id("expert-primary-category")).to_have_text("Research")
    expect(page.get_by_test_id("expert-karma-total")).to_have_text("4,800")
    paragraph = page.get_by_test_id("expert-contribution-summary")
    expect(paragraph).to_be_visible()
    expect(paragraph).to_have_text(summary)
    evidence = page.get_by_test_id("expert-public-playbooks")
    expect(
        evidence.get_by_role("heading", name="Public released playbooks")
    ).to_be_visible()
    explanation = evidence.get_by_text(_EMPTY_EVIDENCE, exact=True)
    explanation.scroll_into_view_if_needed()
    expect(explanation).to_be_visible()
    expect(explanation).to_be_in_viewport()
    expect(evidence).to_have_text("Public released playbooks " + _EMPTY_EVIDENCE)
    expect(evidence.get_by_role("link")).to_have_count(0)
    contact = page.get_by_test_id("experts-reach-out-skim")
    expect(contact).to_be_visible()
    destination = f"mailto:{dataset.users_by_username[_SAM].email}"
    if contact.get_attribute("href") != destination:
        raise AssertionError("Elena's authorized contact destination changed.")


def _assert_private_content_absent(
    page: Page, dataset: CedarDataset, markers: tuple[str, ...]
) -> None:
    """Check the full live DOM against actual existing private rows.

    :param page: Real positive public profile, e.g. Sam's current browser page.
    :param dataset: Cedar data containing actual private fixtures.
    :param markers: Persisted private strings, never emitted in diagnostics.
    :return: None when no private value or account-token control is present.
    :raises AssertionError: If hidden or visible content breaches the boundary.
    """
    document = page.content()
    _assert_private_markers_absent(document, dataset, allow_contact=True)
    if any(marker and marker in document for marker in markers):
        raise AssertionError("A persisted private field leaked into the browser.")
    expect(page.get_by_test_id("profile-token-field")).to_have_count(0)


def _assert_state_unchanged(
    before: DatabaseSnapshot,
    mail_before: tuple[EmailMessage, ...],
    mailoutbox: list[EmailMessage],
) -> None:
    """Preserve all seven domain models and local mail after the profile GET.

    :param before: Full field/row snapshots taken after normal authentication.
    :param mail_before: Existing local messages, e.g. an empty tuple.
    :param mailoutbox: The same real Django mail capture after browser inspection.
    :return: None when read-only domain state and mail remain unchanged.
    :raises AssertionError: If viewing the profile changes a row or sends mail.
    """
    if _snapshot() != before:
        raise AssertionError("Positive-profile GET changed a tracked domain model.")
    if tuple(mailoutbox) != mail_before:
        raise AssertionError("Positive-profile GET changed the local email outbox.")
