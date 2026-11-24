"""S25 certification of existing production PIP controls."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

import pytest
from django.core.mail import EmailMessage
from django.test import override_settings
from django.urls import reverse
from e2e_helpers import login
from playwright.sync_api import Page, expect

from methodology.llm.base import LLMResponse
from methodology.models import (
    Activity,
    AgentInteraction,
    ExpertProfile,
    KarmaAward,
    PipChange,
    PlaybookVersion,
    ProcessImprovementProposal,
)
from methodology.services.experts_service import ExpertsService
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
from tests.support.experts_summary_data import (
    SUMMARY_CHANGE_BODY,
    SUMMARY_PIP_BODY,
    SUMMARY_PIP_TITLE,
    SUMMARY_SCRIPTS,
    load_summary_script,
    prepare_summary_submission,
    summary_processing_scope,
)
from tests.support.scripted_llm import ScriptedLLMCall

_HAPPY_SCRIPT = SUMMARY_SCRIPTS / "PRF-EXPERTS-01/resubmission_happy.json"
_REVISED_BODY = "Unpublished revision clarifying the screen reader recovery rationale."
_INITIAL_REASONING = "The proposed activity fits the review workflow."
_REVISED_REASONING = "The revised proposal clarifies recovery in the review workflow."
_CEDAR_KARMA = 8200
_TARGET_VERSION = Decimal("2.0")
_DomainRows = tuple[tuple[tuple[object, ...], ...], ...]


class _SavedRefresh(NamedTuple):
    """Stored profile and interaction identity at a browser milestone."""

    profile: dict[str, object]
    updated_at: datetime
    interaction_ids: tuple[int, ...]


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(GALDR_USE_TARGET_STATE=True)
def test_s25_browser_withdraw_and_resubmit_refreshes_before_decision(
    page: Page,
    live_server_url: str,
    cedar_dataset: CedarDataset,
    mailoutbox: list[EmailMessage],
) -> None:
    """Exercise real withdrawal modal and normal resubmission in the browser.

    :param page: Existing browser fixture. Example: isolated Maria page.
    :param live_server_url: Existing server origin. Example: http://localhost:8081.
    :param cedar_dataset: Real Cedar baseline with Maria and Hana's playbook.
    :param mailoutbox: The isolated Django in-memory outbox.
    :return: None. Example: None after Reviewed/Draft/Reviewed assertions.
    :raises AssertionError: For broken controls, missing refresh or any award.
    """
    pip = prepare_summary_submission(cedar_dataset)
    change = pip.changes.get()
    script = load_summary_script(_HAPPY_SCRIPT, change.pk)
    initial, _, revised, _ = script
    assert isinstance(initial, LLMResponse) and isinstance(revised, LLMResponse)
    baseline = _award_and_publication_rows(pip)
    _assert_undecided(pip, baseline)
    assert not pip.created_by.is_staff
    login(page, live_server_url, pip.created_by.username, CEDAR_PASSWORD)
    detail_url = live_server_url + reverse("pip_detail", kwargs={"pk": pip.pk})
    page.goto(detail_url)
    with summary_processing_scope(script) as llm:
        _submit_and_expect_reviewed(page, detail_url, change, _INITIAL_REASONING)
        first = _assert_saved_refresh(pip, initial.content, 1, pip.STATUS_REVIEWED)
        first_calls = llm.calls
        assert len(first_calls) == 2
        _assert_undecided(pip, baseline)
        _withdraw_and_edit(page, pip, detail_url, change)
        assert llm.calls == first_calls
        assert _assert_saved_refresh(pip, initial.content, 1, pip.STATUS_DRAFT) == first
        _assert_undecided(pip, baseline)
        _submit_and_expect_reviewed(page, detail_url, change, _REVISED_REASONING)
        refreshed = _assert_saved_refresh(pip, revised.content, 2, pip.STATUS_REVIEWED)
        assert refreshed.updated_at > first.updated_at
        assert refreshed.interaction_ids[:1] == first.interaction_ids
        _open_and_expect_profile_summary(page, revised.content)
        _assert_model_requests(llm.calls)
    _assert_undecided(pip, baseline)
    assert not mailoutbox


def _submit_and_expect_reviewed(
    page: Page, detail_url: str, change: PipChange, reasoning: str
) -> None:
    """Submit using the detail control and verify the resulting review.

    :param page: Maria's browser session displaying the Draft.
    :param detail_url: Existing detail URL for this same PIP.
    :param change: The original proposal's one ADD Activity.
    :param reasoning: The private Galdr assessment expected for this submission.
    :return: None after the Reviewed badge and assessment appear.
    :raises AssertionError: If submission, review or permissions differ.
    """
    expect(page.get_by_test_id("pip-status-badge")).to_have_text("Draft")
    page.get_by_test_id("pip-detail-submit").click()
    expect(page).to_have_url(detail_url)
    expect(page.get_by_test_id("pip-status-badge")).to_have_text("Reviewed")
    expect(page.get_by_test_id(f"galdr-reason-{change.order}")).to_contain_text(
        reasoning
    )
    expect(page.get_by_test_id("pip-admin-review")).to_have_count(0)
    expect(page.get_by_test_id("pip-detail-submit")).to_have_count(0)
    change.refresh_from_db()
    assert (change.galdr_recommendation, change.galdr_reasoning) == (
        PipChange.GALDR_ACCEPT,
        reasoning,
    )


def _withdraw_and_edit(
    page: Page, pip: ProcessImprovementProposal, detail_url: str, change: PipChange
) -> None:
    """Withdraw, edit the private rationale and return to the same Draft detail.

    :param page: Maria's browser session displaying the Reviewed PIP.
    :param pip: The initial proposal, kept through withdrawal and edit.
    :param detail_url: Existing detail URL for this proposal.
    :param change: Original ADD Activity whose assessment must clear.
    :return: None when the saved edit is visible on the same Draft.
    :raises AssertionError: If the modal, state transition or saved edit fails.
    """
    page.get_by_test_id("pip-detail-revert-open").click()
    dialog = page.get_by_role("dialog", name="Return PIP to Draft?")
    expect(dialog.and_(page.get_by_test_id("pip-revert-modal"))).to_be_visible()
    dialog.get_by_test_id("pip-detail-revert-confirm").click()
    expect(page).to_have_url(detail_url)
    expect(page.get_by_test_id("pip-status-badge")).to_have_text("Draft")
    expect(page.get_by_test_id(f"galdr-reason-{change.order}")).to_have_count(0)
    pip.refresh_from_db()
    change.refresh_from_db()
    assert pip.status == pip.STATUS_DRAFT and not pip.galdr_holistic_assessment
    assert change.galdr_recommendation == change.galdr_reasoning == ""
    _save_draft_edit(page, detail_url)
    pip.refresh_from_db()
    assert pip.status == pip.STATUS_DRAFT and pip.summary == _REVISED_BODY


def _save_draft_edit(page: Page, detail_url: str) -> None:
    """Save a real editor field and read the revised rationale in Draft.

    :param page: Maria's browser displaying Draft detail after withdrawal.
    :param detail_url: Expected route on returning from the editor.
    :return: None when the revised text survives the editor POST and navigation.
    :raises AssertionError: If the form did not persist Maria's edit.
    """
    page.get_by_test_id("pip-detail-edit-draft").click()
    editor = page.get_by_test_id("pip-draft-editor")
    summary = editor.get_by_test_id("pip-header-form").get_by_label("Summary")
    expect(summary).to_have_value(SUMMARY_PIP_BODY)
    summary.fill(_REVISED_BODY)
    editor.get_by_test_id("pip-save-header").click()
    expect(summary).to_have_value(_REVISED_BODY)
    editor.get_by_test_id("pip-view-readonly").click()
    expect(page).to_have_url(detail_url)
    expect(page.get_by_test_id("pip-status-badge")).to_have_text("Draft")
    expect(page.get_by_test_id("pip-detail-summary")).to_contain_text(_REVISED_BODY)


def _assert_saved_refresh(
    pip: ProcessImprovementProposal, text: str, expected_count: int, status: str
) -> _SavedRefresh:
    """Check real persisted summary interactions and return the profile snapshot.

    :param pip: Proposal that triggered the expected summary processing.
    :param text: Expected full validated public paragraph.
    :param expected_count: Number of completed summary refreshes on this PIP.
    :param status: Expected PIP state at the browser milestone.
    :return: The saved profile fields and identifiers of successful calls.
    :raises AssertionError: If a refresh did not finish before review or changes identity.
    """
    runs = tuple(AgentInteraction.objects.filter(pip=pip).order_by("pk"))
    assert len(runs) == expected_count
    for run in runs:
        assert (
            run.subject_id == pip.created_by_id and run.call_id and run.correlation_id
        )
        assert run.workflow_id == "contribution_summary"
        assert run.outcome == AgentInteraction.Outcome.SUCCESS
    assert len({run.call_id for run in runs}) == expected_count
    assert len({run.correlation_id for run in runs}) == expected_count
    pip.refresh_from_db()
    assert pip.status == status
    if status == pip.STATUS_REVIEWED:
        assert pip.galdr_holistic_assessment
        assert pip.submitted_at is not None and pip.reviewed_at is not None
        assert pip.submitted_at <= runs[-1].created_at <= pip.reviewed_at
    profile = ExpertProfile.objects.values().get(user_id=pip.created_by_id)
    assert profile["contribution_summary"] == text
    assert profile["summary_status"] == ExpertProfile.SummaryStatus.SUCCESS
    assert profile["last_summary_correlation_id"] == runs[-1].correlation_id
    updated_at = profile["summary_updated_at"]
    assert isinstance(updated_at, datetime)
    return _SavedRefresh(profile, updated_at, tuple(run.pk for run in runs))


def _open_and_expect_profile_summary(page: Page, text: str) -> None:
    """Read the full refreshed contribution summary via Maria's own profile.

    :param page: Maria's authenticated browser after normal resubmission.
    :param text: Exact stored validated paragraph from the second run.
    :return: None when the paragraph and original Karma total are visible.
    :raises AssertionError: If the profile renders a different or hidden result.
    """
    page.get_by_test_id("user-display").click()
    page.get_by_test_id("nav-view-profile").click()
    card = page.get_by_test_id("profile-karma-card")
    summary = card.get_by_test_id("profile-contribution-summary")
    expect(summary).to_be_visible()
    expect(summary).to_have_text(text)
    expect(card.get_by_test_id("profile-karma-total")).to_have_text(f"{_CEDAR_KARMA:,}")
    expect(card.get_by_test_id("profile-summary-toggle")).to_be_hidden()


def _assert_model_requests(calls: tuple[ScriptedLLMCall, ...]) -> None:
    """Check the two actual model request pairs and the public-data boundary.

    :param calls: Actual ordered requests retained by the finite model port.
    :return: None for two public summaries and two private assessments.
    :raises AssertionError: If private proposal text entered a public request.
    """
    first, first_assessment, second, second_assessment = calls
    unpublished = (
        SUMMARY_PIP_TITLE,
        SUMMARY_PIP_BODY,
        SUMMARY_CHANGE_BODY,
        _REVISED_BODY,
    )
    for public_call in (first, second):
        public_input = "\n".join(
            (public_call.system, *(message.content for message in public_call.messages))
        )
        assert "Accessibility Audit Playbook" in public_input
        assert "Keyboard Navigation Audit" in public_input
        assert not any(text in public_input for text in unpublished)
    assert SUMMARY_PIP_BODY in first_assessment.messages[0].content
    assert _REVISED_BODY in second_assessment.messages[0].content


def _award_and_publication_rows(
    pip: ProcessImprovementProposal,
) -> _DomainRows:
    """Read all award rows and the target playbook's published content state.

    :param pip: Proposal identifying Hana's target playbook.
    :return: Sorted full award, target activity and version receipt rows.
    """
    return (
        tuple(KarmaAward.objects.order_by("pk").values_list()),
        tuple(
            Activity.objects.filter(workflow__playbook_id=pip.playbook_id)
            .order_by("pk")
            .values_list()
        ),
        tuple(
            PlaybookVersion.objects.filter(playbook_id=pip.playbook_id)
            .order_by("pk")
            .values_list()
        ),
    )


def _assert_undecided(
    pip: ProcessImprovementProposal,
    baseline: _DomainRows,
) -> None:
    """Verify that browser operations never decide, publish or award the PIP.

    :param pip: Same PIP at the current point in the browser lifecycle.
    :param baseline: Complete pre-submission ledger and target rows for comparison.
    :return: None when Cedar's observed starting state remains intact.
    :raises AssertionError: If a proposal is decided, published or rewarded.
    """
    pip.refresh_from_db()
    pip.playbook.refresh_from_db()
    change = pip.changes.get()
    assert pip.decided_at is None
    assert change.admin_decision == PipChange.ADMIN_UNSET and not change.admin_note
    assert pip.playbook.version == _TARGET_VERSION
    assert ExpertsService().project_user(pip.created_by_id).total_points == _CEDAR_KARMA
    assert _award_and_publication_rows(pip) == baseline
