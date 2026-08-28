"""Integration tests for PIP admin review view (FOB-PIP-ADMIN-07..17)."""

from decimal import Decimal

import pytest
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import Client
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
