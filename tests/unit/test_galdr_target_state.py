"""Unit tests for Galdr target-state dry-run summary."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from methodology.models import Activity, Artifact, PipChange, Playbook, Skill, Workflow
from methodology.services.galdr_prompts import (
    build_extended_playbook_summary,
    build_playbook_context_summary,
)
from methodology.services.pip_apply_changes_service import PipApplyChangesService
from methodology.services.pip_service import PIPService

User = get_user_model()


@pytest.fixture
def author(db):
    return User.objects.create_user(username="target_state", password="pw")


@pytest.fixture
def released_playbook(db, author):
    pb = Playbook.objects.create(
        name="Target PB",
        description="desc",
        category="development",
        author=author,
        status="released",
        version=Decimal("1.0"),
    )
    wf = Workflow.objects.create(playbook=pb, name="Deploy", description="wf", order=1)
    Activity.objects.create(workflow=wf, name="Step", guidance="eks only", order=1)
    return pb


@pytest.fixture
def draft_pip(db, author, released_playbook):
    return PIPService.create_draft_for_playbook(
        actor=author,
        playbook_id=released_playbook.pk,
        title="Multi-change PIP",
    )


@pytest.mark.django_db
def test_build_target_state_summary_reflects_add_and_link(
    author, draft_pip, released_playbook
):
    act = Activity.objects.filter(workflow__playbook=released_playbook).first()
    PIPService.add_change(
        actor=author,
        pip=draft_pip,
        change_type=PipChange.CHANGE_ADD,
        entity_type=PipChange.ENTITY_SKILL,
        name="EB Blue/Green",
        content="Elastic Beanstalk patterns",
        internal_ref="#eb-skill",
    )
    PIPService.add_change(
        actor=author,
        pip=draft_pip,
        change_type=PipChange.CHANGE_LINK,
        relationship_type=PipChange.REL_SKILL_ACTIVITY,
        source_entity_ref="#eb-skill",
        target_entity_ref=str(act.pk),
        content="Link EB skill to activity",
    )

    summary = PipApplyChangesService.build_target_state_summary(
        pip=draft_pip,
        playbook=released_playbook,
    )

    assert "EB Blue/Green" in summary
    assert "Skill → Activity links" in summary
    assert "→ Activity" in summary
    assert Skill.objects.filter(playbook=released_playbook, title="EB Blue/Green").count() == 0


@pytest.mark.django_db
def test_build_extended_playbook_summary_includes_artifact_catalog(
    author, released_playbook
):
    act = Activity.objects.filter(workflow__playbook=released_playbook).first()
    Artifact.objects.create(
        name="User Journey",
        type="Document",
        produced_by=act,
        playbook=released_playbook,
    )

    summary = build_extended_playbook_summary(released_playbook)

    assert "--- Artifacts ---" in summary
    assert "User Journey" in summary
    assert "(Document)" in summary


@pytest.mark.django_db
def test_build_playbook_context_summary_includes_artifacts(author, released_playbook):
    act = Activity.objects.filter(workflow__playbook=released_playbook).first()
    Artifact.objects.create(
        name="Feature Files",
        type="Template",
        produced_by=act,
        playbook=released_playbook,
    )

    summary = build_playbook_context_summary(released_playbook)

    assert "--- Artifacts ---" in summary
    assert "Feature Files" in summary


@pytest.mark.django_db
def test_build_target_state_summary_reflects_artifact_add_and_link(
    author, draft_pip, released_playbook
):
    wf = released_playbook.workflows.first()
    producer = wf.activities.get(order=1)
    consumer = Activity.objects.create(
        workflow=wf, name="Review Step", guidance="review", order=2
    )
    PIPService.add_change(
        actor=author,
        pip=draft_pip,
        change_type=PipChange.CHANGE_ADD,
        entity_type=PipChange.ENTITY_ARTIFACT,
        name="Handoff Checklist",
        content="Checklist for team handoff",
        internal_ref="#art-handoff",
        produced_by_activity_ref=str(producer.pk),
    )
    PIPService.add_change(
        actor=author,
        pip=draft_pip,
        change_type=PipChange.CHANGE_LINK,
        relationship_type=PipChange.REL_ARTIFACT_ACTIVITY,
        source_entity_ref="#art-handoff",
        target_entity_ref=str(consumer.pk),
        content="Link handoff artifact to review activity",
    )

    summary = PipApplyChangesService.build_target_state_summary(
        pip=draft_pip,
        playbook=released_playbook,
    )

    assert "Handoff Checklist" in summary
    assert "--- Artifacts ---" in summary
    assert "Artifact → Activity links" in summary
    assert "→ Activity" in summary
    assert (
        Artifact.objects.filter(
            playbook=released_playbook, name="Handoff Checklist"
        ).count()
        == 0
    )
