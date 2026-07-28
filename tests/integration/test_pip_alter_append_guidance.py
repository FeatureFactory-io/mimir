"""
Regression tests for ALTER change delta semantics.

Bug: _apply_alter replaces guidance/content unconditionally.
     Content starting with "APPEND TO GUIDANCE:" must be appended, not replace.

Reproduces the data-loss scenario from PIP #53 (lessons-learned loop) where
applying three ALTER Activity changes with "APPEND TO GUIDANCE:" prefixes would
have silently wiped the existing guidance of BPE-01, PIN-02, and MIN-05.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from methodology.models import (
    Activity,
    PipChange,
    Playbook,
    Rule,
    Workflow,
)
from methodology.services.pip_admin_service import PIPAdminService
from methodology.services.pip_service import PIPService

User = get_user_model()


@pytest.fixture
def author(db):
    return User.objects.create_user(username="append_author", password="pw", email="a@append.test")


@pytest.fixture
def staff(db):
    u = User.objects.create_user(username="append_staff", password="pw", email="s@append.test")
    u.is_staff = True
    u.save(update_fields=["is_staff"])
    return u


@pytest.fixture
def released_bundle(db, author):
    pb = Playbook.objects.create(
        name="Append PB",
        description="desc",
        category="development",
        author=author,
        status="released",
        version=Decimal("1.0"),
    )
    wf = Workflow.objects.create(playbook=pb, name="Append WF", description="w", order=1)
    act = Activity.objects.create(
        workflow=wf,
        name="Rich Activity",
        guidance="## Existing Section\n\nOriginal guidance body.",
        order=1,
    )
    rule = Rule.objects.create(
        playbook=pb,
        title="Existing Rule",
        slug="existing-rule",
        content="Original rule content.",
    )
    return pb, wf, act, rule


def _finalize_all_accept(pip, author, staff):
    PIPService.submit_for_review(actor=author, pip=pip)
    pip.refresh_from_db()
    for ch in pip.changes.all():
        ch.galdr_recommendation = PipChange.GALDR_ACCEPT
        ch.admin_decision = PipChange.ADMIN_ACCEPT
        ch.save(update_fields=["galdr_recommendation", "admin_decision", "updated_at"])
    PIPAdminService.finalize_pip(pip, staff)


@pytest.mark.django_db
def test_alter_activity_append_prefix_appends_not_replaces(author, staff, released_bundle):
    """
    Applying an ALTER Activity change with 'APPEND TO GUIDANCE:' prefix must
    append the delta to existing guidance — not overwrite it.
    """
    pb, _wf, act, _rule = released_bundle
    original_guidance = act.guidance

    pip = PIPService.create_draft_for_playbook(
        actor=author, playbook_id=pb.pk, title="Append section G"
    )
    PIPService.add_change(
        actor=author,
        pip=pip,
        change_type=PipChange.CHANGE_ALTER,
        entity_type=PipChange.ENTITY_ACTIVITY,
        target_id=act.pk,
        content="APPEND TO GUIDANCE:\n\n### Section G — Lessons Learned\n\nNew content here.",
    )

    _finalize_all_accept(pip, author, staff)

    act.refresh_from_db()
    assert original_guidance in act.guidance, (
        "Existing guidance was erased — APPEND TO GUIDANCE: must append, not replace."
    )
    assert "### Section G — Lessons Learned" in act.guidance, (
        "Appended section is missing from guidance."
    )


@pytest.mark.django_db
def test_alter_activity_plain_content_still_replaces(author, staff, released_bundle):
    """
    An ALTER Activity change WITHOUT the append prefix must still fully replace
    guidance (existing behaviour must not regress).
    """
    pb, _wf, act, _rule = released_bundle

    pip = PIPService.create_draft_for_playbook(
        actor=author, playbook_id=pb.pk, title="Full replace"
    )
    PIPService.add_change(
        actor=author,
        pip=pip,
        change_type=PipChange.CHANGE_ALTER,
        entity_type=PipChange.ENTITY_ACTIVITY,
        target_id=act.pk,
        content="## Completely New Guidance\n\nFull replacement body.",
    )

    _finalize_all_accept(pip, author, staff)

    act.refresh_from_db()
    assert act.guidance == "## Completely New Guidance\n\nFull replacement body."
    assert "Existing Section" not in act.guidance


@pytest.mark.django_db
def test_alter_rule_append_prefix_appends_not_replaces(author, staff, released_bundle):
    """
    Applying an ALTER Rule change with 'APPEND TO GUIDANCE:' prefix must
    append to rule content — not overwrite it.
    """
    pb, _wf, _act, rule = released_bundle
    original_content = rule.content

    pip = PIPService.create_draft_for_playbook(
        actor=author, playbook_id=pb.pk, title="Append rule closure section"
    )
    PIPService.add_change(
        actor=author,
        pip=pip,
        change_type=PipChange.CHANGE_ALTER,
        entity_type=PipChange.ENTITY_RULE,
        target_id=rule.pk,
        content="APPEND TO GUIDANCE:\n\n## Issue Closure\n\nClosure requirements here.",
    )

    _finalize_all_accept(pip, author, staff)

    rule.refresh_from_db()
    assert original_content in rule.content, (
        "Existing rule content was erased — APPEND TO GUIDANCE: must append, not replace."
    )
    assert "## Issue Closure" in rule.content, (
        "Appended closure section is missing from rule content."
    )


@pytest.mark.django_db
def test_two_sequential_appends_accumulate(author, staff, released_bundle):
    """
    Two successive PIPs each appending to the same activity must both be
    present in the final guidance — second append must not erase the first.
    This reproduces the PIP #53 + PIP #54 ordering scenario.
    """
    pb, _wf, act, _rule = released_bundle

    pip1 = PIPService.create_draft_for_playbook(
        actor=author, playbook_id=pb.pk, title="First append"
    )
    PIPService.add_change(
        actor=author,
        pip=pip1,
        change_type=PipChange.CHANGE_ALTER,
        entity_type=PipChange.ENTITY_ACTIVITY,
        target_id=act.pk,
        content="APPEND TO GUIDANCE:\n\n### TAF Integration\n\nTAF content.",
    )
    _finalize_all_accept(pip1, author, staff)

    pb.refresh_from_db()
    act.refresh_from_db()
    assert "### TAF Integration" in act.guidance

    pip2 = PIPService.create_draft_for_playbook(
        actor=author, playbook_id=pb.pk, title="Second append"
    )
    PIPService.add_change(
        actor=author,
        pip=pip2,
        change_type=PipChange.CHANGE_ALTER,
        entity_type=PipChange.ENTITY_ACTIVITY,
        target_id=act.pk,
        content="APPEND TO GUIDANCE:\n\n### Lessons Learned Aggregation\n\nLessons content.",
    )
    _finalize_all_accept(pip2, author, staff)

    act.refresh_from_db()
    assert "## Existing Section" in act.guidance, "Original guidance was lost after second PIP."
    assert "### TAF Integration" in act.guidance, "First PIP append was lost after second PIP."
    assert "### Lessons Learned Aggregation" in act.guidance, "Second PIP append is missing."
