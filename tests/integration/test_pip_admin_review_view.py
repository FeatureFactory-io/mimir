"""Integration tests for PIP admin review view (FOB-PIP-ADMIN-07..17)."""

from decimal import Decimal

import pytest
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import Client
from django.test.html import parse_html
from django.urls import reverse

from methodology.models import (
    Activity,
    PipChange,
    Playbook,
    ProcessImprovementProposal,
    Workflow,
)
from methodology.services.pip_admin_service import PIPAdminService
from methodology.services.pip_service import PIPService
from tests.support.experts_html import find_by_test_id

User = get_user_model()


@pytest.fixture
def alice(db):
    """Regular user (PIP author)."""
    return User.objects.create_user(
        username="alice_admin_test", password="pw", email="alice@example.test"
    )


@pytest.fixture
def bob_staff(db):
    """Staff user (admin reviewer)."""
    u = User.objects.create_user(
        username="bob_staff_admin", password="pw", email="bob@example.test"
    )
    u.is_staff = True
    u.save(update_fields=["is_staff"])
    return u


@pytest.fixture
def playbook_bundle(db, alice):
    """Released playbook with one workflow and one activity."""
    pb = Playbook.objects.create(
        name="Admin Review Test PB",
        description="desc",
        category="development",
        author=alice,
        status="released",
        version=Decimal("1.0"),
    )
    wf = Workflow.objects.create(
        playbook=pb,
        name="Main Workflow",
        description="wf",
        order=1,
    )
    act = Activity.objects.create(
        workflow=wf,
        name="Existing Activity",
        guidance="existing guidance",
        order=1,
    )
    return pb, wf, act


@pytest.fixture
def reviewed_pip_all_accept(alice, bob_staff, playbook_bundle):
    """PIP with 2 changes, Galdr recommended ACCEPT for both."""
    pb, wf, act = playbook_bundle
    pip = PIPService.create_draft_for_playbook(
        actor=alice,
        playbook_id=pb.pk,
        title="Two accepts",
        summary="Test all accept",
    )
    PIPService.add_change(
        actor=alice,
        pip=pip,
        change_type=PipChange.CHANGE_ALTER,
        entity_type=PipChange.ENTITY_ACTIVITY,
        target_id=act.pk,
        content="altered guidance",
        name="",
    )
    PIPService.add_change(
        actor=alice,
        pip=pip,
        change_type=PipChange.CHANGE_ADD,
        entity_type=PipChange.ENTITY_ACTIVITY,
        parent_workflow_id=wf.pk,
        name="New Activity",
        content="new activity body",
    )
    PIPService.submit_for_review(actor=alice, pip=pip)
    pip.refresh_from_db()
    for ch in pip.changes.all():
        ch.galdr_recommendation = "ACCEPT"
        ch.galdr_reasoning = "Looks good"
        ch.save(update_fields=["galdr_recommendation", "galdr_reasoning"])
    return pip


@pytest.fixture
def reviewed_pip_partial(alice, bob_staff, playbook_bundle):
    """PIP with 2 changes, one ACCEPT, one REJECT from Galdr."""
    pb, wf, act = playbook_bundle
    pip = PIPService.create_draft_for_playbook(
        actor=alice,
        playbook_id=pb.pk,
        title="Partial accept",
        summary="Test partial",
    )
    ch1 = PIPService.add_change(
        actor=alice,
        pip=pip,
        change_type=PipChange.CHANGE_ALTER,
        entity_type=PipChange.ENTITY_ACTIVITY,
        target_id=act.pk,
        content="good alteration",
        name="",
    )
    ch2 = PIPService.add_change(
        actor=alice,
        pip=pip,
        change_type=PipChange.CHANGE_ADD,
        entity_type=PipChange.ENTITY_ACTIVITY,
        parent_workflow_id=wf.pk,
        name="Bad Activity",
        content="bad body",
    )
    PIPService.submit_for_review(actor=alice, pip=pip)
    pip.refresh_from_db()
    ch1.galdr_recommendation = "ACCEPT"
    ch1.galdr_reasoning = "Good"
    ch1.save(update_fields=["galdr_recommendation", "galdr_reasoning"])
    ch2.galdr_recommendation = "REJECT"
    ch2.galdr_reasoning = "Bad"
    ch2.save(update_fields=["galdr_recommendation", "galdr_reasoning"])
    return pip


@pytest.mark.django_db
def test_admin_16_non_staff_gets_403(alice, reviewed_pip_all_accept):
    """FOB-PIP-ADMIN-16: Regular user cannot access admin review page."""
    client = Client()
    client.force_login(alice)
    url = reverse("pip_admin_review", kwargs={"pk": reviewed_pip_all_accept.pk})
    response = client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_04_staff_can_access_review_form(bob_staff, reviewed_pip_all_accept):
    """FOB-PIP-ADMIN-04: Staff user can access admin review page for Reviewed PIP."""
    client = Client()
    client.force_login(bob_staff)
    url = reverse("pip_admin_review", kwargs={"pk": reviewed_pip_all_accept.pk})
    response = client.get(url)
    assert response.status_code == 200
    assert b"Admin Review" in response.content or b"admin-review-page" in response.content


@pytest.mark.django_db
def test_admin_05_galdr_output_shown(bob_staff, reviewed_pip_all_accept):
    """FOB-PIP-ADMIN-05: Galdr recommendations and reasoning are displayed."""
    client = Client()
    client.force_login(bob_staff)
    url = reverse("pip_admin_review", kwargs={"pk": reviewed_pip_all_accept.pk})
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    assert "ACCEPT" in content
    assert "Looks good" in content


@pytest.fixture
def admin_review_response(
    client: Client,
    bob_staff: AbstractUser,
    reviewed_pip_all_accept: ProcessImprovementProposal,
) -> HttpResponse:
    """Open the review form as staff for the two-change PIP.

    :param client: Real Django client.
    :param bob_staff: Reviewer account authorized to open the PIP.
    :param reviewed_pip_all_accept: Reviewed PIP holding two proposed changes.
    :return: Successful review response. Example: the staff review page.
    :raises AssertionError: If the review page cannot be opened.
    """
    client.force_login(bob_staff)
    url = reverse("pip_admin_review", kwargs={"pk": reviewed_pip_all_accept.pk})
    response = client.get(url)
    assert response.status_code == 200
    return response


@pytest.mark.django_db
def test_admin_review_with_two_changes_labels_each_decision(
    admin_review_response: HttpResponse,
    reviewed_pip_all_accept: ProcessImprovementProposal,
) -> None:
    """Verify each decision has a distinct native label linked to its select.

    :param admin_review_response: Actual staff review HTML response.
    :param reviewed_pip_all_accept: Reviewed PIP holding two proposed changes.
    :return: None when both native label associations are unique.
    :raises AssertionError: If a decision is missing its matching label or ID.
    """
    html = admin_review_response.content.decode()
    changes = list(reviewed_pip_all_accept.changes.order_by("order"))
    assert [change.order for change in changes] == [1, 2]
    for change in changes:
        row = find_by_test_id(html, f"admin-change-row-{change.order}")
        decision = find_by_test_id(str(row), f"admin-decision-{change.order}")
        assert decision.name == "select"
        assert ("name", f"decision_{change.pk}") in decision.attributes
        decision_id = dict(decision.attributes).get("id")
        assert decision_id, f"Change {change.order} decision needs a label target"
        assert html.count(f' id="{decision_id}"') == 1
        label = parse_html(
            f'<label class="visually-hidden" for="{decision_id}">'
            f"Decision for change {change.order}</label>"
        )
        assert row.count(label) == 1


@pytest.mark.django_db
def test_admin_review_with_finalize_dialog_associates_visible_title(
    admin_review_response: HttpResponse,
) -> None:
    """Verify the existing heading names the finalization dialog.

    :param admin_review_response: Actual staff review HTML response.
    :return: None when the dialog points to its unique confirmation heading.
    :raises AssertionError: If the rendered dialog has no linked heading.
    """
    html = admin_review_response.content.decode()
    modal = find_by_test_id(html, "finalize-confirm-modal")
    title_id = dict(modal.attributes).get("aria-labelledby")
    assert title_id, "The confirmation dialog needs a title association"
    assert html.count(f' id="{title_id}"') == 1
    heading = parse_html(
        f'<h5 class="modal-title" id="{title_id}">Confirm Finalize</h5>'
    )
    assert modal.count(heading) == 1


@pytest.mark.django_db
def test_admin_review_with_finalize_dialog_names_close_button(
    admin_review_response: HttpResponse,
) -> None:
    """Verify the icon-only dismiss button has an explicit action name.

    :param admin_review_response: Actual staff review HTML response.
    :return: None when the icon button is named Close and still dismisses.
    :raises AssertionError: If the named dismiss button is absent.
    """
    modal = find_by_test_id(admin_review_response.content, "finalize-confirm-modal")
    button = parse_html(
        '<button type="button" class="btn-close" data-bs-dismiss="modal" '
        'aria-label="Close" data-testid="finalize-modal-close"></button>'
    )
    assert modal.count(button) == 1, "The icon-only dismiss control must be named Close"


@pytest.mark.django_db
def test_admin_10_finalize_blocked_until_all_set(bob_staff, reviewed_pip_all_accept):
    """FOB-PIP-ADMIN-10: Cannot finalize until all admin_decision fields are set."""
    client = Client()
    client.force_login(bob_staff)
    url = reverse("pip_admin_review", kwargs={"pk": reviewed_pip_all_accept.pk})
    
    # Try to finalize without setting decisions
    response = client.post(url, {"action": "finalize"})
    
    # Should fail validation
    reviewed_pip_all_accept.refresh_from_db()
    assert reviewed_pip_all_accept.status == ProcessImprovementProposal.STATUS_REVIEWED


@pytest.mark.django_db
def test_save_decisions_with_partial_form_preserves_existing_choices(
    client: Client,
    bob_staff: AbstractUser,
    reviewed_pip_all_accept: ProcessImprovementProposal,
) -> None:
    """Save recognized choices and trimmed notes without finalizing or clearing invalid input.

    :param client: Actual Django test client for the staff form.
    :param bob_staff: Authorized staff reviewer.
    :param reviewed_pip_all_accept: Reviewed proposal with two changes.
    :return: None. Example: one decision is updated and the other remains intact.
    :raises AssertionError: If saving modifies the proposal lifecycle or previous choice.
    """
    pip = reviewed_pip_all_accept
    first, second = pip.changes.order_by("order")
    second.admin_decision, second.admin_note = PipChange.ADMIN_REJECT, "Previous note"
    second.save(update_fields=["admin_decision", "admin_note"])
    original_updated_at = pip.updated_at
    client.force_login(bob_staff)
    url = reverse("pip_admin_review", args=[pip.pk])
    result = client.post(
        url,
        {
            "action": "save_decisions",
            f"decision_{first.pk}": "  ACCEPT  ",
            f"note_{first.pk}": "  Saved note  ",
            f"decision_{second.pk}": "  Unknown  ",
            f"note_{second.pk}": "Should not replace the previous note",
        },
    )
    assert result.status_code == 302 and result.url == url
    first, second = pip.changes.order_by("order")
    pip.refresh_from_db()
    assert (first.admin_decision, first.admin_note) == (
        PipChange.ADMIN_ACCEPT,
        "Saved note",
    )
    assert (second.admin_decision, second.admin_note) == (
        PipChange.ADMIN_REJECT,
        "Previous note",
    )
    assert pip.status == pip.STATUS_REVIEWED and pip.decided_at is None
    assert pip.updated_at == original_updated_at and not pip.playbook_versions.exists()


@pytest.mark.django_db
def test_admin_07_all_accept_bumps_version(bob_staff, reviewed_pip_all_accept, playbook_bundle):
    """FOB-PIP-ADMIN-07: Accepting all changes bumps playbook version."""
    pb, wf, act = playbook_bundle
    client = Client()
    client.force_login(bob_staff)
    url = reverse("pip_admin_review", kwargs={"pk": reviewed_pip_all_accept.pk})
    
    changes = list(reviewed_pip_all_accept.changes.all())
    post_data = {"action": "finalize"}
    for ch in changes:
        post_data[f"decision_{ch.pk}"] = "ACCEPT"
        post_data[f"note_{ch.pk}"] = "accepted"
    
    response = client.post(url, post_data)
    assert response.status_code == 302
    
    reviewed_pip_all_accept.refresh_from_db()
    pb.refresh_from_db()
    assert reviewed_pip_all_accept.status == ProcessImprovementProposal.STATUS_ACCEPTED
    assert pb.version == Decimal("2.0")
    success_messages = [
        str(message)
        for message in response.wsgi_request._messages
        if message.level == messages.SUCCESS
    ]
    assert success_messages == ["PIP accepted — changes applied."]


@pytest.mark.django_db
def test_admin_08_partial_accept_applies_only_accepted(bob_staff, reviewed_pip_partial, playbook_bundle):
    """FOB-PIP-ADMIN-08: Accepting some changes applies only those."""
    pb, wf, act = playbook_bundle
    client = Client()
    client.force_login(bob_staff)
    url = reverse("pip_admin_review", kwargs={"pk": reviewed_pip_partial.pk})
    
    changes = list(reviewed_pip_partial.changes.order_by("order"))
    post_data = {"action": "finalize"}
    post_data[f"decision_{changes[0].pk}"] = "ACCEPT"
    post_data[f"note_{changes[0].pk}"] = "good"
    post_data[f"decision_{changes[1].pk}"] = "REJECT"
    post_data[f"note_{changes[1].pk}"] = "bad"
    
    response = client.post(url, post_data)
    assert response.status_code == 302
    
    reviewed_pip_partial.refresh_from_db()
    pb.refresh_from_db()
    assert reviewed_pip_partial.status == ProcessImprovementProposal.STATUS_ACCEPTED_PARTIAL
    assert pb.version == Decimal("2.0")
    
    # Check only first change applied
    act.refresh_from_db()
    assert "good alteration" in act.guidance
    assert Activity.objects.filter(workflow=wf, name="Bad Activity").count() == 0


@pytest.mark.django_db
def test_admin_09_all_reject_no_change(bob_staff, reviewed_pip_all_accept, playbook_bundle):
    """FOB-PIP-ADMIN-09: Rejecting all changes leaves playbook unchanged."""
    pb, wf, act = playbook_bundle
    original_version = pb.version
    client = Client()
    client.force_login(bob_staff)
    url = reverse("pip_admin_review", kwargs={"pk": reviewed_pip_all_accept.pk})
    
    changes = list(reviewed_pip_all_accept.changes.all())
    post_data = {"action": "finalize"}
    for ch in changes:
        post_data[f"decision_{ch.pk}"] = "REJECT"
        post_data[f"note_{ch.pk}"] = "rejected"
    
    response = client.post(url, post_data)
    assert response.status_code == 302
    
    reviewed_pip_all_accept.refresh_from_db()
    pb.refresh_from_db()
    assert reviewed_pip_all_accept.status == ProcessImprovementProposal.STATUS_REJECTED
    assert pb.version == original_version


@pytest.mark.django_db
def test_admin_17_decided_pip_readonly(bob_staff, reviewed_pip_all_accept):
    """FOB-PIP-ADMIN-17: Already-decided PIP shows read-only banner."""
    # First finalize it
    changes = list(reviewed_pip_all_accept.changes.all())
    for ch in changes:
        ch.admin_decision = "ACCEPT"
        ch.admin_note = "accepted"
        ch.save(update_fields=["admin_decision", "admin_note"])
    PIPAdminService.finalize_pip(reviewed_pip_all_accept, bob_staff)
    
    # Now try to access it
    client = Client()
    client.force_login(bob_staff)
    url = reverse("pip_admin_review", kwargs={"pk": reviewed_pip_all_accept.pk})
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    assert "already been decided" in content or "already-decided-banner" in content
    
    # Try to POST anyway - should be blocked
    post_data = {"action": "finalize"}
    for ch in changes:
        post_data[f"decision_{ch.pk}"] = "REJECT"
    response = client.post(url, post_data)
    # Should redirect back without changing anything
    reviewed_pip_all_accept.refresh_from_db()
    assert reviewed_pip_all_accept.status == ProcessImprovementProposal.STATUS_ACCEPTED
