"""Certify Maria's submission and the existing staff decision in Chromium."""

from __future__ import annotations

from decimal import Decimal
from http import HTTPStatus

import pytest
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from e2e_helpers import login
from playwright.sync_api import Locator, Page, expect

from methodology.llm.base import LLMResponse
from methodology.models import (
    Activity,
    AgentInteraction,
    EventChannel,
    ExpertProfile,
    KarmaAward,
    PipChange,
    PlaybookVersion,
    VersionSource,
)
from methodology.services.experts_service import ExpertsService
from tests.e2e.test_experts_own_profile import _assert_account_controls
from tests.e2e.test_experts_profile_summary import (
    _assert_summary_state,
    _open_own_profile,
    _tab_past_assistant_link,
)
from tests.e2e.test_experts_summary_resubmission import (
    _assert_saved_refresh,
    _assert_undecided,
    _award_and_publication_rows,
    _DomainRows,
    _SavedRefresh,
    _submit_and_expect_reviewed,
)
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
from tests.support.experts_summary_data import (
    SUMMARY_PIP_TITLE,
    SUMMARY_SCRIPTS,
    load_summary_script,
    prepare_summary_submission,
    summary_processing_scope,
)

_SUMMARY_SCRIPT = SUMMARY_SCRIPTS / "PRF-EXPERTS-01/happy.json"
_ASSESSMENT_REASON = "The proposed activity fits the review workflow."
_TARGET_V2 = Decimal("2.0")
_TARGET_V3 = Decimal("3.0")
_INITIAL_TOTAL = 8_200
_INITIAL_DESIGN = 7_200
_INITIAL_PIP = 1_600
_DEVELOPMENT = 1_000
_MAJOR_POINTS = 500
_UAT_VIEWPORT = {"width": 1280, "height": 800}


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(GALDR_USE_TARGET_STATE=True, GALDR_USE_ANTHROPIC=False)
def test_admin_browser_with_major_add_finalization_awards_maria(
    page: Page,
    live_server_url: str,
    cedar_dataset: CedarDataset,
    mailoutbox: list[EmailMessage],
) -> None:
    """Show UAT-18-03 through baseline, submission, staff decision and live totals.

    :param page: Existing Chromium page with isolated browser context.
    :param live_server_url: Actual function-scoped Django server origin.
    :param cedar_dataset: Restored Cedar users and Hana's Design playbook at v2.0.
    :param mailoutbox: Django's real test-local mail capture.
    :return: None once the page and persisted state agree on v3.0 and 8,700 Karma.
    :raises AssertionError: If predecision, confirmation, persistence or mail differs.
    """
    pip = prepare_summary_submission(cedar_dataset)
    change = pip.changes.get()
    maria, mike = pip.created_by, cedar_dataset.users_by_username["mchen"]
    assert not maria.is_staff and mike.is_staff and mike.pk != maria.pk
    baseline = _award_and_publication_rows(pip)
    unaffected = (mike.pk, pip.playbook.author_id)
    experts = ExpertsService()
    initial_projections = tuple(experts.project_user(user_id) for user_id in unaffected)
    _open_maria_baseline(page, live_server_url, maria)
    script = load_summary_script(_SUMMARY_SCRIPT, change.pk)
    with summary_processing_scope(script) as llm:
        _submit_normal_proposal(page, live_server_url, change)
        assert isinstance(script[0], LLMResponse)
        refresh = _assert_saved_refresh(pip, script[0].content, 1, pip.STATUS_REVIEWED)
        assert len(llm.calls) == 2
        _assert_undecided(pip, baseline)
        _check_post_submission_profile(page, script[0].content)
        assert not mailoutbox
        _sign_out(page)
        login(page, live_server_url, mike.username, CEDAR_PASSWORD)
        original_award = _finalize_as_mike(page, live_server_url, change, mike)
        _reopen_decided_review(page, live_server_url, change)
        _check_profiles_after_decision(page, live_server_url, change, refresh)
        assert len(llm.calls) == 2
    _assert_saved_decision(change, mike.pk, baseline, original_award)
    assert (
        tuple(experts.project_user(user_id) for user_id in unaffected)
        == initial_projections
    )
    _assert_local_notification(change, mailoutbox)


def _open_maria_baseline(page: Page, origin: str, maria: User) -> None:
    """Verify Maria's initial totals, account controls and keyboard summary.

    :param page: Existing Chromium page with an isolated browser context.
    :param origin: Existing function-scoped server URL.
    :param maria: Existing nonstaff submitter.
    :return: None after restoring the initial summary preview.
    :raises AssertionError: If baseline or keyboard behavior differs.
    """
    initial = ExpertProfile.objects.get(user=maria)
    assert initial.summary_updated_at is None
    page.set_viewport_size(_UAT_VIEWPORT)
    profile, _ = _open_own_profile(page, origin, maria)
    _assert_own_profile(profile, _INITIAL_PIP, _INITIAL_DESIGN)
    _assert_account_controls(profile)
    _expand_and_collapse_with_keyboard(page, profile, initial.contribution_summary)


def _assert_own_profile(profile: Locator, pip_points: int, design_points: int) -> None:
    """Read live contribution totals and the four separately visible source rows.

    :param profile: Actual rendered own-profile region for Maria.
    :param pip_points: Expected accepted contributions, for example 1,600.
    :param design_points: Expected Design subtotal, for example 7,200.
    :return: None when all displayed figures reconcile.
    :raises AssertionError: If any label, subtotal or displayed total differs.
    """
    total = design_points + _DEVELOPMENT
    expect(profile.get_by_test_id("profile-karma-total")).to_have_text(f"{total:,}")
    expect(profile.get_by_test_id("profile-primary-category")).to_have_text("Design")
    sources = profile.get_by_test_id("profile-karma-source-breakdown")
    expect(sources.get_by_role("rowheader")).to_have_text(
        ["Released", "PIP", "Consumption", "Learning", "Total"]
    )
    cells = sources.get_by_role("cell").all_inner_texts()
    assert [int(cell.replace(",", "")) for cell in cells] == [
        5_000,
        pip_points,
        1_200,
        400,
        total,
    ]
    _assert_categories(
        profile.get_by_test_id("profile-karma-category-breakdown"), design_points
    )


def _assert_categories(categories: Locator, design_points: int) -> None:
    """Check the exact actual Design and Development entries.

    :param categories: The visible category list on either Maria profile.
    :param design_points: Expected live Design amount, for example 7,700.
    :return: None when both displayed categories have exact points.
    :raises AssertionError: If another category or a wrong subtotal appears.
    """
    expect(categories).to_be_visible()
    expect(categories.get_by_role("term")).to_have_text(["Design", "Development"])
    amounts = categories.get_by_role("definition").all_inner_texts()
    assert [int(amount.replace(",", "")) for amount in amounts] == [
        design_points,
        _DEVELOPMENT,
    ]


def _expand_and_collapse_with_keyboard(
    page: Page, profile: Locator, paragraph: str
) -> None:
    """Use native Tab, Enter and Space on the real four-line preview.

    :param page: Real Maria browser after opening her initial own profile.
    :param profile: Profile wrapper containing the account-to-summary Tab path.
    :param paragraph: Exact original cached contribution summary.
    :return: None after focus, expansion and restoration are visible.
    :raises AssertionError: If the preview, keyboard order or state differs.
    """
    _assert_summary_state(page, paragraph, expanded=False)
    toggle = profile.get_by_test_id("profile-summary-toggle")
    _tab_past_assistant_link(page, profile)
    expect(toggle).to_be_focused()
    page.keyboard.press("Enter")
    _assert_summary_state(page, paragraph, expanded=True)
    expect(toggle).to_be_focused()
    page.keyboard.press("Space")
    _assert_summary_state(page, paragraph, expanded=False, restored=True)


def _submit_normal_proposal(page: Page, origin: str, change: PipChange) -> None:
    """Use the normal proposal submit action and observe its actual POST.

    :param page: Existing logged-in Maria page returned from her profile.
    :param origin: Existing function-scoped server URL.
    :param change: Her Screen Reader Error Recovery proposal change.
    :return: None when production processing reaches Reviewed.
    :raises AssertionError: If the action omits the real submission or shows acceptance.
    """
    detail_url = origin + reverse("pip_detail", args=[change.pip_id])
    page.goto(detail_url)
    expect(page.get_by_test_id("pip-detail-title")).to_contain_text(SUMMARY_PIP_TITLE)
    expect(page.get_by_test_id("pip-detail-header")).to_contain_text(
        f"{change.pip.playbook.name} v{_TARGET_V2}"
    )
    submit_url = origin + reverse("pip_submit_review", args=[change.pip_id])
    with page.expect_response(
        lambda response: (
            response.url == submit_url and response.request.method == "POST"
        )
    ) as submission:
        _submit_and_expect_reviewed(page, detail_url, change, _ASSESSMENT_REASON)
    assert submission.value.status == HTTPStatus.FOUND
    expect(page.get_by_test_id(f"admin-verdict-{change.order}")).to_have_count(0)


def _check_post_submission_profile(page: Page, paragraph: str) -> None:
    """Read the refreshed prose and original Karma via normal profile navigation.

    :param page: Maria's session after the normal Reviewed result.
    :param paragraph: Exact stored text from the successful summary refresh.
    :return: None when the refreshed paragraph appears with the original total.
    :raises AssertionError: If normal submission altered Karma or omitted the refresh.
    """
    page.get_by_test_id("user-display").click()
    page.get_by_test_id("nav-view-profile").click()
    profile = page.get_by_test_id("profile-page")
    _assert_own_profile(profile, _INITIAL_PIP, _INITIAL_DESIGN)
    expect(profile.get_by_test_id("profile-contribution-summary")).to_have_text(
        paragraph
    )


def _sign_out(page: Page) -> None:
    """Use the profile menu to end the current signed-in session.

    :param page: Real signed-in browser page.
    :return: None when the Login page is active.
    :raises AssertionError: If the authenticated session remains visible.
    """
    page.get_by_test_id("user-display").click()
    page.get_by_test_id("logout-link").click()
    expect(page.get_by_test_id("login-link")).to_be_visible()
    expect(page.get_by_test_id("user-display")).to_have_count(0)


def _open_staff_review(page: Page, origin: str, change: PipChange, mike: User) -> str:
    """Follow Review PIP as the existing administrator.

    :param page: Same browser now authenticated as the independent staff actor.
    :param origin: Function-scoped server URL.
    :param change: The real proposal awaiting decision.
    :param mike: Cedar's existing staff account.
    :return: Canonical URL of this review page.
    :raises AssertionError: If the browser fails to reach the actual reviewed form.
    """
    page.goto(origin + reverse("pip_detail", args=[change.pip_id]))
    expect(page.get_by_test_id("user-display")).to_have_text(mike.username)
    page.get_by_test_id("pip-admin-review").click()
    review_url = origin + reverse("pip_admin_review", args=[change.pip_id])
    expect(page).to_have_url(review_url)
    expect(page.get_by_test_id("pip-admin-review-page")).to_be_visible()
    expect(page.get_by_test_id("admin-review-header")).to_contain_text(f"v{_TARGET_V2}")
    return review_url


def _finalize_as_mike(
    page: Page, origin: str, change: PipChange, mike: User
) -> KarmaAward:
    """Accept the change using the native decision and confirmation controls.

    :param page: Existing browser after a separate Mike sign-in.
    :param origin: Existing function-scoped server URL.
    :param change: Reviewed ADD Activity awaiting a decision.
    :param mike: The existing administrator's account.
    :return: The actual award recorded before revisiting the accepted PIP.
    :raises AssertionError: If native review, confirmation or terminal display differs.
    """
    review_url = _open_staff_review(page, origin, change, mike)
    decision = page.get_by_test_id("admin-decision-1")
    finalize = page.get_by_test_id("finalize-btn")
    expect(decision).to_have_value("")
    expect(finalize).to_be_disabled()
    decision.select_option(PipChange.ADMIN_ACCEPT)
    expect(page.get_by_test_id("accepted-count")).to_have_text("1")
    expect(page.get_by_test_id("pending-count")).to_have_text("0")
    expect(finalize).to_be_enabled()
    finalize.click()
    modal = page.get_by_test_id("finalize-confirm-modal")
    expect(modal).to_be_visible()
    expect(modal.get_by_role("heading")).to_have_text("Confirm Finalize")
    expect(modal).to_contain_text("You are accepting 1 of 1 changes.")
    expect(modal).to_contain_text("will be updated to a new major version.")
    expect(decision).to_have_accessible_name("Decision for change 1")
    expect(modal).to_have_accessible_name("Confirm Finalize")
    expect(modal.get_by_role("button", name="Close", exact=True)).to_be_visible()
    with page.expect_response(
        lambda response: (
            response.url == review_url and response.request.method == "POST"
        )
    ) as submission:
        modal.get_by_test_id("confirm-finalize-btn").click()
    assert submission.value.status == HTTPStatus.FOUND
    return _read_accepted_decision(page, origin, change)


def _read_accepted_decision(page: Page, origin: str, change: PipChange) -> KarmaAward:
    """Read the Accepted page and retain the original award before any revisit.

    :param page: Real staff browser after the confirmation POST.
    :param origin: Function-scoped server URL.
    :param change: The single accepted ADD Activity.
    :return: The first committed decision's accepted-change award.
    :raises AssertionError: If terminal display or persisted award differs.
    """
    expect(page).to_have_url(origin + reverse("pip_detail", args=[change.pip_id]))
    expect(page.get_by_test_id("pip-status-badge")).to_have_text("Accepted")
    expect(page.get_by_test_id("pip-detail-header")).to_contain_text(f"v{_TARGET_V3}")
    expect(page.get_by_test_id("admin-verdict-1")).to_have_text("ADMIN ACCEPT")
    expect(page.get_by_test_id("alert-message")).to_contain_text(
        "PIP accepted — changes applied."
    )
    change.pip.refresh_from_db()
    return _assert_new_award(change)


def _reopen_decided_review(page: Page, origin: str, change: PipChange) -> None:
    """Reopen the decided page using the same existing admin route.

    :param page: Real staff session displaying the accepted PIP.
    :param origin: Existing live-server origin.
    :param change: The accepted ADD Activity.
    :return: None when the read-only review shows the persisted decision.
    :raises AssertionError: If the page offers a second finalization action.
    """
    response = page.goto(origin + reverse("pip_admin_review", args=[change.pip_id]))
    assert response is not None and response.status == HTTPStatus.OK
    expect(page.get_by_test_id("already-decided-banner")).to_be_visible()
    expect(page.get_by_test_id("admin-review-header")).to_contain_text(f"v{_TARGET_V3}")
    decision = page.get_by_test_id("admin-decision-1")
    expect(decision).to_have_value(PipChange.ADMIN_ACCEPT)
    expect(decision).to_be_disabled()
    expect(page.get_by_test_id("finalize-btn")).to_have_count(0)


def _check_profiles_after_decision(
    page: Page, origin: str, change: PipChange, refresh: _SavedRefresh
) -> None:
    """Reopen public and own profiles and confirm the original refresh still serves them.

    :param page: Real browser initially authenticated as the reviewing staff member.
    :param origin: Existing function-scoped server URL.
    :param change: Accepted ADD Activity, identifying Maria by its actual owner.
    :param refresh: Stored successful predecision summary and interaction.
    :return: None if new totals render with the cached prose.
    :raises AssertionError: If either view or its persisted data differs.
    """
    maria = change.pip.created_by
    paragraph = refresh.profile["contribution_summary"]
    assert isinstance(paragraph, str)
    public_url = origin + reverse("expert_detail", kwargs={"username": maria.username})
    response = page.goto(public_url)
    assert response is not None and response.status == HTTPStatus.OK
    expect(page.get_by_test_id("expert-name")).to_have_text(maria.get_full_name())
    expect(page.get_by_test_id("expert-karma-total")).to_have_text(
        f"{_INITIAL_TOTAL + _MAJOR_POINTS:,}"
    )
    expect(page.get_by_test_id("expert-contribution-summary")).to_have_text(paragraph)
    design = _INITIAL_DESIGN + _MAJOR_POINTS
    _assert_categories(page.get_by_test_id("karma-category-breakdown"), design)
    _sign_out(page)
    own_profile, _ = _open_own_profile(page, origin, maria)
    _assert_own_profile(own_profile, _INITIAL_PIP + _MAJOR_POINTS, design)
    expect(own_profile.get_by_test_id("profile-contribution-summary")).to_have_text(
        paragraph
    )
    assert ExpertProfile.objects.values().get(user=maria) == refresh.profile
    interactions = AgentInteraction.objects.filter(pip_id=change.pip_id).order_by("pk")
    assert tuple(interactions.values_list("pk", flat=True)) == refresh.interaction_ids


def _assert_saved_decision(
    change: PipChange,
    reviewer_id: int,
    baseline: _DomainRows,
    original_award: KarmaAward,
) -> None:
    """Reconcile the sole committed publication, new activity and award after revisits.

    :param change: Actual ADD Activity submitted and finalized by the browser.
    :param reviewer_id: Existing staff account Mike's primary key.
    :param baseline: Full award, activity and version rows before submission.
    :param original_award: Award observed immediately after the first actual decision.
    :return: None when exactly one publication, activity and award have been added.
    :raises AssertionError: If the decision, exact history or its provenance differs.
    """
    pip = change.pip
    pip.refresh_from_db()
    change.refresh_from_db()
    assert (
        pip.status == pip.STATUS_ACCEPTED
        and change.admin_decision == PipChange.ADMIN_ACCEPT
    )
    assert pip.decided_at is not None and timezone.is_aware(pip.decided_at)
    assert pip.playbook.version == _TARGET_V3
    activity = Activity.objects.get(
        workflow_id=change.parent_workflow_id,
        workflow__playbook_id=pip.playbook_id,
        name=change.name,
        guidance=change.content,
    )
    receipt = pip.playbook_versions.get()
    _assert_publication_receipt(receipt, change, reviewer_id)
    award = _assert_new_award(change)
    assert award.pk == original_award.pk
    assert pip.decided_at == original_award.occurred_at
    current = _award_and_publication_rows(pip)
    for rows, originals, added_pk in zip(
        current, baseline, (award.pk, activity.pk, receipt.pk), strict=True
    ):
        assert len(rows) == len(originals) + 1
        assert tuple(row for row in rows if row[0] != added_pk) == originals


def _assert_publication_receipt(
    receipt: PlaybookVersion, change: PipChange, reviewer_id: int
) -> None:
    """Check the actual publication connects one accepted change to the new version.

    :param receipt: Sole new publication receipt attached to this proposal.
    :param change: The accepted ADD Activity transaction.
    :param reviewer_id: Primary key for the actual administrator.
    :return: None after exact receipt and snapshot match.
    :raises AssertionError: If publication source, actor or snapshot differs.
    """
    pip = change.pip
    assert (receipt.playbook_id, receipt.version_number, receipt.source) == (
        pip.playbook_id,
        _TARGET_V3,
        VersionSource.PIP_SOURCE,
    )
    assert receipt.is_major and receipt.created_by_id == reviewer_id
    assert receipt.snapshot_data == {
        "pip_id": pip.pk,
        "playbook_name": pip.playbook.name,
        "version_before": str(_TARGET_V2),
        "version_after": str(_TARGET_V3),
        "accepted_change_ids": [change.pk],
        "category": "design",
    }


def _assert_new_award(change: PipChange) -> KarmaAward:
    """Check exact recipient, amount, time and category of the sole added event.

    :param change: The persisted accepted Activity ADD.
    :return: Actual 500 point accepted-change award.
    :raises AssertionError: If the event or Mara's category projection differs.
    """
    pip = change.pip
    award = KarmaAward.objects.get(event_identity=f"accepted_change:{change.pk}")
    assert (
        award.recipient_id,
        award.playbook_id_snapshot,
        award.change_id_snapshot,
    ) == (
        pip.created_by_id,
        pip.playbook_id,
        change.pk,
    )
    assert (award.event_channel, award.source_kind, award.points, award.category) == (
        EventChannel.ACCEPTED_CHANGE,
        KarmaAward.SourceKind.MAJOR,
        _MAJOR_POINTS,
        "design",
    )
    assert award.occurred_at == pip.decided_at
    projection = ExpertsService().project_user(pip.created_by_id)
    assert projection.total_points == _INITIAL_TOTAL + _MAJOR_POINTS
    assert dict(projection.category_points) == {
        "design": _INITIAL_DESIGN + _MAJOR_POINTS,
        "development": _DEVELOPMENT,
    }
    return award


def _assert_local_notification(
    change: PipChange, mailoutbox: list[EmailMessage]
) -> None:
    """Inspect one ordinary decision notification from the committed staff POST.

    :param change: This accepted Activity ADD.
    :param mailoutbox: Local-memory outbox retained after read-only revisits.
    :return: None if the notification names the exact change and new version.
    :raises AssertionError: If count, recipient, verdict or content differs.
    """
    (notification,) = mailoutbox
    assert notification.to == [change.pip.created_by.email]
    assert "Accepted" in notification.subject
    assert f'ADD Activity "{change.name}"' in notification.body
    assert "Decision: ACCEPT" in notification.body
    assert f"is now v{_TARGET_V3}" in notification.body
