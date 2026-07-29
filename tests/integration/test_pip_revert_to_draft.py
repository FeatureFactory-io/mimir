"""Integration tests: PIPService.revert_to_draft + pip_revert_to_draft view.

Log-story beats asserted per assert-log-story rule.
"""
import logging
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from methodology.models import (
    Activity,
    PipChange,
    Playbook,
    ProcessImprovementProposal,
    Workflow,
)
from methodology.services.pip_service import PIPService
from tests.support.log_story import assert_log_story

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def alice(db):
    return User.objects.create_user(username="alice_revert", password="pw", email="alice_r@example.test")


@pytest.fixture
def bob(db):
    return User.objects.create_user(username="bob_revert", password="pw", email="bob_r@example.test")


@pytest.fixture
def released_pb(db, alice):
    pb = Playbook.objects.create(
        name="Revert PB",
        description="d" * 30,
        category="development",
        author=alice,
        status="released",
        version=Decimal("1.0"),
    )
    wf = Workflow.objects.create(playbook=pb, name="Main", description="wf", order=1)
    Activity.objects.create(workflow=wf, name="Step One", guidance="legacy", order=1)
    return pb


@pytest.fixture
def submitted_pip(db, alice, released_pb):
    pip = PIPService.create_draft_for_playbook(
        actor=alice,
        playbook_id=released_pb.pk,
        title="Revert me",
        summary="",
    )
    act = released_pb.workflows.first().activities.first()
    PIPService.add_change(
        actor=alice,
        pip=pip,
        change_type=PipChange.CHANGE_ALTER,
        entity_type=PipChange.ENTITY_ACTIVITY,
        target_id=act.pk,
        content="updated guidance",
        name="",
    )
    pip.status = ProcessImprovementProposal.STATUS_SUBMITTED
    pip.galdr_holistic_assessment = "some holistic text"
    pip.save(update_fields=["status", "galdr_holistic_assessment"])
    pip.changes.update(
        galdr_recommendation=PipChange.GALDR_ACCEPT,
        galdr_reasoning="looks good",
    )
    return pip


# ---------------------------------------------------------------------------
# Service: happy path
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_revert_to_draft_clears_galdr_fields_and_status(alice, submitted_pip, caplog):
    with caplog.at_level(logging.INFO, logger="methodology.services.pip_service"):
        PIPService.revert_to_draft(submitted_pip, alice)

    submitted_pip.refresh_from_db()
    assert submitted_pip.status == ProcessImprovementProposal.STATUS_DRAFT
    assert submitted_pip.galdr_holistic_assessment == ""

    for change in submitted_pip.changes.all():
        assert change.galdr_recommendation == ""
        assert change.galdr_reasoning == ""

    assert_log_story(
        caplog,
        where="revert_to_draft",
        beats={
            "entry": ["revert_to_draft entry"],
            "validation": ["revert_to_draft validation allowed"],
            "processing": ["revert_to_draft processing"],
            "exit": ["revert_to_draft exit"],
        },
    )


@pytest.mark.django_db
def test_revert_to_draft_from_processing_galdr_status(alice, released_pb):
    pip = PIPService.create_draft_for_playbook(
        actor=alice, playbook_id=released_pb.pk, title="Processing revert", summary=""
    )
    act = released_pb.workflows.first().activities.first()
    PIPService.add_change(
        actor=alice, pip=pip,
        change_type=PipChange.CHANGE_ALTER,
        entity_type=PipChange.ENTITY_ACTIVITY,
        target_id=act.pk,
        content="x", name="",
    )
    pip.status = ProcessImprovementProposal.STATUS_PROCESSING_GALDR
    pip.save(update_fields=["status"])

    PIPService.revert_to_draft(pip, alice)
    pip.refresh_from_db()
    assert pip.status == ProcessImprovementProposal.STATUS_DRAFT


# ---------------------------------------------------------------------------
# Service: reject paths
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_revert_to_draft_raises_for_draft_status(alice, released_pb, caplog):
    pip = PIPService.create_draft_for_playbook(
        actor=alice, playbook_id=released_pb.pk, title="Draft reject", summary=""
    )
    with caplog.at_level(logging.INFO, logger="methodology.services.pip_service"), pytest.raises(ValidationError, match="Cannot revert PIP to Draft"):
        PIPService.revert_to_draft(pip, alice)

    assert_log_story(
        caplog,
        where="revert_to_draft",
        beats={"error": ["revert_to_draft error cannot revert"]},
    )


@pytest.mark.django_db
def test_revert_to_draft_from_reviewed_status(alice, submitted_pip, caplog):
    """Reviewed PIP can be reverted to Draft — primary Galdr-feedback loop."""
    submitted_pip.status = ProcessImprovementProposal.STATUS_REVIEWED
    submitted_pip.save(update_fields=["status"])

    with caplog.at_level(logging.INFO, logger="methodology.services.pip_service"):
        PIPService.revert_to_draft(submitted_pip, alice)

    submitted_pip.refresh_from_db()
    assert submitted_pip.status == ProcessImprovementProposal.STATUS_DRAFT
    assert submitted_pip.galdr_holistic_assessment == ""
    for change in submitted_pip.changes.all():
        assert change.galdr_recommendation == ""
        assert change.galdr_reasoning == ""

    assert_log_story(
        caplog,
        where="revert_to_draft",
        beats={
            "entry": ["revert_to_draft entry"],
            "validation": ["revert_to_draft validation allowed"],
            "processing": ["revert_to_draft processing"],
            "exit": ["revert_to_draft exit"],
        },
    )


@pytest.mark.django_db
def test_revert_to_draft_raises_for_accepted_status(alice, submitted_pip, caplog):
    """Accepted is a terminal status — revert must remain blocked."""
    submitted_pip.status = ProcessImprovementProposal.STATUS_ACCEPTED
    submitted_pip.save(update_fields=["status"])

    with caplog.at_level(logging.INFO, logger="methodology.services.pip_service"), pytest.raises(ValidationError, match="Cannot revert PIP to Draft"):
        PIPService.revert_to_draft(submitted_pip, alice)

    assert_log_story(
        caplog,
        where="revert_to_draft",
        beats={"error": ["revert_to_draft error cannot revert"]},
    )


@pytest.mark.django_db
def test_revert_to_draft_raises_for_non_owner(bob, submitted_pip):
    with pytest.raises((ValidationError, PermissionError)):
        PIPService.revert_to_draft(submitted_pip, bob)


# ---------------------------------------------------------------------------
# View: POST /pips/<pk>/revert-to-draft/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_pip_revert_to_draft_view_happy_path(alice, submitted_pip):
    client = Client(enforce_csrf_checks=False)
    client.force_login(alice)
    url = reverse("pip_revert_to_draft", kwargs={"pk": submitted_pip.pk})
    rsp = client.post(url)
    assert rsp.status_code == 302
    assert rsp.url == reverse("pip_detail", kwargs={"pk": submitted_pip.pk})
    submitted_pip.refresh_from_db()
    assert submitted_pip.status == ProcessImprovementProposal.STATUS_DRAFT


@pytest.mark.django_db
def test_pip_revert_to_draft_view_shows_success_message(alice, submitted_pip):
    client = Client(enforce_csrf_checks=False)
    client.force_login(alice)
    url = reverse("pip_revert_to_draft", kwargs={"pk": submitted_pip.pk})
    rsp = client.post(url, follow=True)
    messages = [str(m) for m in rsp.context["messages"]]
    assert any("Draft" in m for m in messages)


@pytest.mark.django_db
def test_pip_revert_to_draft_view_rejects_wrong_status(alice, submitted_pip):
    """Accepted is terminal — view must surface the error message."""
    submitted_pip.status = ProcessImprovementProposal.STATUS_ACCEPTED
    submitted_pip.save(update_fields=["status"])
    client = Client(enforce_csrf_checks=False)
    client.force_login(alice)
    url = reverse("pip_revert_to_draft", kwargs={"pk": submitted_pip.pk})
    rsp = client.post(url, follow=True)
    messages = [str(m) for m in rsp.context["messages"]]
    assert any("Cannot revert" in m for m in messages)
    submitted_pip.refresh_from_db()
    assert submitted_pip.status == ProcessImprovementProposal.STATUS_ACCEPTED


@pytest.mark.django_db
def test_pip_revert_to_draft_view_succeeds_for_reviewed(alice, submitted_pip):
    """View POST on Reviewed PIP reverts to Draft."""
    submitted_pip.status = ProcessImprovementProposal.STATUS_REVIEWED
    submitted_pip.save(update_fields=["status"])
    client = Client(enforce_csrf_checks=False)
    client.force_login(alice)
    url = reverse("pip_revert_to_draft", kwargs={"pk": submitted_pip.pk})
    rsp = client.post(url)
    assert rsp.status_code == 302
    submitted_pip.refresh_from_db()
    assert submitted_pip.status == ProcessImprovementProposal.STATUS_DRAFT


@pytest.mark.django_db
def test_pip_revert_to_draft_view_requires_login(submitted_pip):
    client = Client(enforce_csrf_checks=False)
    url = reverse("pip_revert_to_draft", kwargs={"pk": submitted_pip.pk})
    rsp = client.post(url)
    assert rsp.status_code == 302
    assert "/login/" in rsp.url or "/accounts/login/" in rsp.url


@pytest.mark.django_db
def test_pip_revert_to_draft_view_requires_post(alice, submitted_pip):
    client = Client()
    client.force_login(alice)
    url = reverse("pip_revert_to_draft", kwargs={"pk": submitted_pip.pk})
    rsp = client.get(url)
    assert rsp.status_code == 405


# ---------------------------------------------------------------------------
# Context: can_revert_to_draft flag in detail view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_pip_detail_shows_revert_button_for_submitted(alice, submitted_pip):
    client = Client()
    client.force_login(alice)
    rsp = client.get(reverse("pip_detail", kwargs={"pk": submitted_pip.pk}))
    body = rsp.content.decode()
    assert 'data-testid="pip-detail-revert-open"' in body


@pytest.mark.django_db
def test_pip_detail_hides_revert_button_for_draft(alice, released_pb):
    pip = PIPService.create_draft_for_playbook(
        actor=alice, playbook_id=released_pb.pk, title="Draft only", summary=""
    )
    client = Client()
    client.force_login(alice)
    rsp = client.get(reverse("pip_detail", kwargs={"pk": pip.pk}))
    body = rsp.content.decode()
    assert 'data-testid="pip-detail-revert-open"' not in body


@pytest.mark.django_db
def test_pip_detail_shows_revert_button_for_reviewed(alice, submitted_pip):
    """Reviewed PIP must show the Withdraw (revert-to-draft) button."""
    submitted_pip.status = ProcessImprovementProposal.STATUS_REVIEWED
    submitted_pip.save(update_fields=["status"])
    client = Client()
    client.force_login(alice)
    rsp = client.get(reverse("pip_detail", kwargs={"pk": submitted_pip.pk}))
    body = rsp.content.decode()
    assert 'data-testid="pip-detail-revert-open"' in body


@pytest.mark.django_db
def test_pip_detail_shows_withdraw_button_for_reviewed(alice, submitted_pip):
    """Reviewed PIP must show the Cancel PIP (withdraw) button."""
    submitted_pip.status = ProcessImprovementProposal.STATUS_REVIEWED
    submitted_pip.save(update_fields=["status"])
    client = Client()
    client.force_login(alice)
    rsp = client.get(reverse("pip_detail", kwargs={"pk": submitted_pip.pk}))
    body = rsp.content.decode()
    assert 'data-testid="pip-detail-withdraw-open"' in body


@pytest.mark.django_db
def test_withdraw_pip_from_reviewed_status(alice, submitted_pip):
    """withdraw_pip on Reviewed PIP permanently cancels it."""
    submitted_pip.status = ProcessImprovementProposal.STATUS_REVIEWED
    submitted_pip.save(update_fields=["status"])
    PIPService.withdraw_pip(submitted_pip, alice)
    submitted_pip.refresh_from_db()
    assert submitted_pip.status == ProcessImprovementProposal.STATUS_WITHDRAWN


# ---------------------------------------------------------------------------
# Full Galdr feedback loop: Reviewed → revert → fix → resubmit
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_full_galdr_feedback_loop_revert_and_resubmit(alice, submitted_pip, released_pb):
    """Reviewed PIP can be reverted, fixed, and resubmitted — the core Galdr loop."""
    submitted_pip.status = ProcessImprovementProposal.STATUS_REVIEWED
    submitted_pip.save(update_fields=["status"])

    PIPService.revert_to_draft(submitted_pip, alice)
    submitted_pip.refresh_from_db()
    assert submitted_pip.status == ProcessImprovementProposal.STATUS_DRAFT
    assert submitted_pip.galdr_holistic_assessment == ""
    for change in submitted_pip.changes.all():
        assert change.galdr_recommendation == ""
        assert change.galdr_reasoning == ""

    act = released_pb.workflows.first().activities.first()
    PIPService.add_change(
        actor=alice,
        pip=submitted_pip,
        change_type=PipChange.CHANGE_ALTER,
        entity_type=PipChange.ENTITY_ACTIVITY,
        target_id=act.pk,
        content="revised guidance after Galdr feedback",
        name="",
    )

    result = PIPService.submit_for_review(actor=alice, pip=submitted_pip)
    result.refresh_from_db()
    assert result.status in (
        ProcessImprovementProposal.STATUS_PROCESSING_GALDR,
        ProcessImprovementProposal.STATUS_REVIEWED,
    ), f"Expected resubmitted status, got: {result.status}"


@pytest.mark.django_db
def test_submit_directly_from_reviewed_raises(alice, submitted_pip):
    """submit_for_review must be blocked when PIP is already Reviewed (revert first)."""
    submitted_pip.status = ProcessImprovementProposal.STATUS_REVIEWED
    submitted_pip.save(update_fields=["status"])

    with pytest.raises(ValidationError, match="Submit is only allowed from Draft"):
        PIPService.submit_for_review(actor=alice, pip=submitted_pip)
