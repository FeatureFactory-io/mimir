"""Unit tests for Galdr pending #internal_ref identity in prompts (#174)."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from methodology.models import Activity, PipChange, Playbook, ProcessImprovementProposal, Skill, Workflow
from methodology.services.galdr_prompts import (
    INTERNAL_REF_IDENTITY_NOTE,
    build_change_prompt,
    build_internal_ref_identity_lines,
    build_playbook_context_summary,
    build_target_state_prompt,
)
from methodology.services.pip_apply_changes_service import PipApplyChangesService
from methodology.services.pip_service import PIPService

User = get_user_model()


@pytest.fixture
def author(db):
    return User.objects.create_user(username="galdr_ref", password="pw")


@pytest.fixture
def released_playbook(db, author):
    pb = Playbook.objects.create(
        name="Ref PB",
        description="desc",
        category="development",
        author=author,
        status="released",
        version=Decimal("1.0"),
    )
    wf = Workflow.objects.create(playbook=pb, name="Deploy", description="wf", order=1)
    Activity.objects.create(workflow=wf, name="Consumer", guidance="body", order=1)
    return pb


@pytest.fixture
def draft_pip(db, author, released_playbook):
    return PIPService.create_draft_for_playbook(
        actor=author,
        playbook_id=released_playbook.pk,
        title="ADD+LINK ref PIP",
    )


@pytest.mark.django_db
def test_build_internal_ref_identity_lines_maps_add_rows(
    author, draft_pip, released_playbook
):
    producer = Activity.objects.filter(workflow__playbook=released_playbook).first()
    PIPService.add_change(
        actor=author,
        pip=draft_pip,
        change_type=PipChange.CHANGE_ADD,
        entity_type=PipChange.ENTITY_ARTIFACT,
        name="Handoff Checklist",
        content="Checklist",
        internal_ref="#art-handoff",
        produced_by_activity_ref=str(producer.pk),
    )
    PIPService.add_change(
        actor=author,
        pip=draft_pip,
        change_type=PipChange.CHANGE_ADD,
        entity_type=PipChange.ENTITY_ACTIVITY,
        name="TL Closes Sprint",
        content="Close guidance",
        internal_ref="#min07-close",
        parent_workflow_id=released_playbook.workflows.first().pk,
    )
    changes = list(draft_pip.changes.order_by("order", "pk"))

    lines = build_internal_ref_identity_lines(changes)

    assert any("#art-handoff" in line and "Handoff Checklist" in line for line in lines)
    assert any("#min07-close" in line and "TL Closes Sprint" in line for line in lines)


@pytest.mark.django_db
def test_build_target_state_prompt_includes_pending_ref_bindings(
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
        name="DSP Target Selection",
        content="Target doc",
        internal_ref="#artifact-dsp-target",
        produced_by_activity_ref=str(producer.pk),
    )
    PIPService.add_change(
        actor=author,
        pip=draft_pip,
        change_type=PipChange.CHANGE_LINK,
        relationship_type=PipChange.REL_ARTIFACT_ACTIVITY,
        source_entity_ref="#artifact-dsp-target",
        target_entity_ref=str(consumer.pk),
        content="Link artifact to activity",
    )
    changes = list(draft_pip.changes.order_by("order", "pk"))
    pip = ProcessImprovementProposal.objects.get(pk=draft_pip.pk)
    current = build_playbook_context_summary(released_playbook)
    target, ref_map = PipApplyChangesService.build_target_state_context(
        pip=pip,
        playbook=released_playbook,
    )

    prompt = build_target_state_prompt(
        pip,
        current,
        target,
        changes,
        ref_map=ref_map,
    )

    assert "--- Pending internal_ref identities (same PIP) ---" in prompt
    assert "#artifact-dsp-target" in prompt
    assert "DSP Target Selection" in prompt
    assert INTERNAL_REF_IDENTITY_NOTE in prompt
    assert "pending ADD" in prompt
    assert "target-state Artifact" in prompt


@pytest.mark.django_db
def test_format_change_list_annotates_internal_ref_endpoints(
    author, draft_pip, released_playbook
):
    act = Activity.objects.filter(workflow__playbook=released_playbook).first()
    PIPService.add_change(
        actor=author,
        pip=draft_pip,
        change_type=PipChange.CHANGE_ADD,
        entity_type=PipChange.ENTITY_SKILL,
        name="EB Skill",
        content="patterns",
        internal_ref="#eb-skill",
    )
    link = PIPService.add_change(
        actor=author,
        pip=draft_pip,
        change_type=PipChange.CHANGE_LINK,
        relationship_type=PipChange.REL_SKILL_ACTIVITY,
        source_entity_ref="#eb-skill",
        target_entity_ref=str(act.pk),
        content="Link skill",
    )
    changes = list(draft_pip.changes.order_by("order", "pk"))
    from methodology.services.galdr_prompts import _format_change_list

    block = _format_change_list(changes)
    link_row = PipChange.objects.get(pk=link.pk)

    assert "#eb-skill (pending ADD" in block
    assert f"Change [{link_row.pk}]" in block


@pytest.mark.django_db
def test_build_change_prompt_includes_prior_add_refs_for_link(
    author, draft_pip, released_playbook
):
    wf = released_playbook.workflows.first()
    skill = Skill.objects.create(
        playbook=released_playbook,
        title="Lessons Skill",
        capability_domain="X",
        technology_stack="Y",
    )
    PIPService.add_change(
        actor=author,
        pip=draft_pip,
        change_type=PipChange.CHANGE_ADD,
        entity_type=PipChange.ENTITY_ACTIVITY,
        name="IDA Demand Assessment",
        content="Feasibility",
        internal_ref="#min07-close",
        parent_workflow_id=wf.pk,
    )
    PIPService.add_change(
        actor=author,
        pip=draft_pip,
        change_type=PipChange.CHANGE_LINK,
        relationship_type=PipChange.REL_SKILL_ACTIVITY,
        source_entity_ref=str(skill.pk),
        target_entity_ref="#min07-close",
        content="Link lessons skill to close activity",
    )
    changes = list(draft_pip.changes.order_by("order", "pk"))
    link_change = changes[-1]
    summary = build_playbook_context_summary(released_playbook)

    prompt = build_change_prompt(link_change, summary, all_changes=changes)

    assert "--- Pending internal_ref identities (prior in this PIP) ---" in prompt
    assert "#min07-close" in prompt
    assert "IDA Demand Assessment" in prompt
    assert "#min07-close (pending ADD" in prompt


@pytest.mark.django_db
def test_build_target_state_prompt_includes_dry_run_pk_when_available(
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
        content="Checklist",
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
        content="Link handoff",
    )
    changes = list(draft_pip.changes.order_by("order", "pk"))
    pip = ProcessImprovementProposal.objects.get(pk=draft_pip.pk)
    target, ref_map = PipApplyChangesService.build_target_state_context(
        pip=pip,
        playbook=released_playbook,
    )

    assert "#art-handoff" in ref_map
    _entity_type, pk = ref_map["#art-handoff"]
    assert _entity_type == PipChange.ENTITY_ARTIFACT
    assert isinstance(pk, int)

    prompt = build_target_state_prompt(
        pip,
        build_playbook_context_summary(released_playbook),
        target,
        changes,
        ref_map=ref_map,
    )
    assert f"target-state Artifact [{pk}]" in prompt
