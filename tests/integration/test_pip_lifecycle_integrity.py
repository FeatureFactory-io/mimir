"""Prove submitter mutations serialize with normal review and draft editing."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event
from typing import TYPE_CHECKING, Any

import pytest
from django.contrib.messages import get_messages
from django.db import connection, connections
from django.test import Client
from django.urls import reverse

from methodology.models import (
    Activity,
    KarmaAward,
    PipChange,
    Playbook,
    ProcessImprovementProposal,
    Workflow,
)
from methodology.services.karma_service import KarmaService
from methodology.services.pip_service import PIPService
from tests.support.experts_data import (
    create_reviewed_major_add_pip,
    load_cedar_baseline,
)
from tests.support.experts_summary_data import summary_processing_scope

if TYPE_CHECKING:
    from django.core.mail import EmailMessage
    from django.http import HttpResponseBase

pytestmark = pytest.mark.django_db(transaction=True)
_TIMEOUT = 15
_NOTE = "Published review note"
_PARENT_TABLE = ProcessImprovementProposal._meta.db_table
_CHANGE_TABLE = PipChange._meta.db_table
_EDIT_ACTIONS = frozenset(
    {"pip_edit", "pip_add_change", "pip_remove_change", "add_link"}
)


def _interleave(
    pending: Callable[[], HttpResponseBase],
    commit_first: Callable[[], None],
    *,
    tables: tuple[str, ...] = (_PARENT_TABLE, _CHANGE_TABLE),
) -> HttpResponseBase:
    """Pause a real request before its first relevant transactional SQL statement."""
    waiting, resume = Event(), Event()
    main_connection = connections["default"]

    def pause(
        execute: Callable[..., Any], sql: str, params: Any, many: bool, context: dict
    ) -> Any:
        owner_connection = context["connection"]
        if (
            owner_connection.in_atomic_block
            and not waiting.is_set()
            and any(f'"{table}"' in sql for table in tables)
        ):
            assert owner_connection is not main_connection
            waiting.set()
            assert resume.wait(_TIMEOUT), "concurrent request did not finish"
        return execute(sql, params, many, context)

    def request() -> HttpResponseBase:
        try:
            with connection.execute_wrapper(pause):
                return pending()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(request)
        try:
            assert waiting.wait(_TIMEOUT), "submitter never reached transactional SQL"
            commit_first()
        finally:
            resume.set()
        return future.result(timeout=_TIMEOUT)


def _publish(
    client: Client, pip: ProcessImprovementProposal, change: PipChange
) -> None:
    """Finalize an ADD through Mike's ordinary staff review endpoint."""
    response = client.post(
        reverse("pip_admin_review", args=[pip.pk]),
        {
            "action": "finalize",
            f"decision_{change.pk}": PipChange.ADMIN_ACCEPT,
            f"note_{change.pk}": _NOTE,
        },
    )
    assert (response.status_code, response.url) == (
        302,
        reverse("pip_detail", args=[pip.pk]),
    )


def _publication(
    pip: ProcessImprovementProposal, change: PipChange
) -> tuple[object, ...]:
    """Check the accepted invariants and retain every persisted publication field."""
    state = ProcessImprovementProposal.objects.values().get(pk=pip.pk)
    assert state["status"] == pip.STATUS_ACCEPTED and state["decided_at"]
    (decision,) = pip.changes.values()
    assert (decision["admin_decision"], decision["admin_note"]) == (
        PipChange.ADMIN_ACCEPT,
        _NOTE,
    )
    receipt = pip.playbook_versions.values().get()
    assert receipt["snapshot_data"]["accepted_change_ids"] == [change.pk]
    activity = (
        Activity.objects.filter(workflow__playbook_id=pip.playbook_id, name=change.name)
        .values()
        .get()
    )
    award = KarmaAward.objects.values().get(
        event_identity=f"accepted_change:{change.pk}"
    )
    assert award["points"] == 500 and activity["guidance"] == change.content
    assert Playbook.objects.get(pk=pip.playbook_id).version == Decimal("3.0")
    return state, decision, receipt, activity, award


def _owner_request(
    owner: Client, action: str, pip: ProcessImprovementProposal, change: PipChange
) -> HttpResponseBase:
    """Post real editor or lifecycle form fields to the standard submitter route."""
    if action == "pip_edit":
        return owner.post(
            reverse(action, args=[pip.pk]),
            {"action": "save_header", "title": "Stale title", "summary": "Stale body"},
        )
    if action == "pip_add_change":
        return owner.post(
            reverse(action, args=[pip.pk]),
            {"change_type": "ADD", "entity_type": "Skill", "name": "Stale Skill"},
        )
    if action == "add_link":
        target = pip.playbook.workflows.exclude(pk=change.parent_workflow_id).first()
        assert target is not None
        return owner.post(
            reverse("pip_add_change", args=[pip.pk]),
            {
                "change_type": "LINK",
                "relationship_type": PipChange.REL_ACTIVITY_WORKFLOW,
                "source_entity_ref": str(change.parent_workflow.activities.first().pk),
                "target_entity_ref": str(target.pk),
            },
        )
    args = [pip.pk, change.pk] if action == "pip_remove_change" else [pip.pk]
    return owner.post(reverse(action, args=args))


@pytest.mark.parametrize(
    ("action", "error"),
    [
        ("pip_withdraw", "This PIP can no longer be withdrawn."),
        ("pip_revert_to_draft", "Cannot revert PIP to Draft from status 'accepted'."),
        ("pip_edit", "Editable only while Draft."),
        ("pip_add_change", "Editable only while Draft."),
        pytest.param("add_link", "Editable only while Draft.", id="link"),
        ("pip_remove_change", "Editable only while Draft."),
    ],
)
def test_owner_post_with_stale_state_preserves_accepted_publication(
    action: str, error: str, mailoutbox: list[EmailMessage]
) -> None:
    """Pause the old owner request while real submission/review publishes v3.0."""
    cedar = load_cedar_baseline()
    pip = create_reviewed_major_add_pip(cedar, PipChange.ENTITY_ACTIVITY)
    maria, mike = (cedar.users_by_username[name] for name in ("mrodriguez", "mchen"))
    owner, submitter, reviewer = Client(), Client(), Client()
    owner.force_login(maria)
    submitter.force_login(maria)
    reviewer.force_login(mike)
    change = pip.changes.get()
    if action in _EDIT_ACTIONS:
        PIPService.revert_to_draft(pip, maria)
    if action == "add_link":
        Workflow.objects.create(playbook_id=pip.playbook_id, name="Secondary workflow")
    before = ()

    def publish_first() -> None:
        nonlocal before
        if action in _EDIT_ACTIONS:
            response = submitter.post(reverse("pip_submit_review", args=[pip.pk]))
            assert response.url == reverse("pip_detail", args=[pip.pk])
        _publish(reviewer, pip, change)
        before = _publication(pip, change)
        assert len(mailoutbox) == 1

    stale = _interleave(
        lambda: _owner_request(owner, action, pip, change), publish_first
    )

    assert _publication(pip, change) == before
    assert stale.status_code == 302
    assert [str(message) for message in get_messages(stale.wsgi_request)] == [error]
    pip.refresh_from_db()
    (replay,) = KarmaService.award_accepted_changes(
        pip=pip, correlation_id="s32:stale_submitter"
    )
    assert not replay.created and replay.reason == "duplicate"
    assert replay.award.points == 500 and replay.award.recipient_id == maria.pk
    (email,) = mailoutbox
    assert email.to == [maria.email] and "Decision: ACCEPT" in email.body


def test_submit_with_concurrently_removed_dependency_keeps_draft_without_provider_turn() -> (
    None
):
    """The preflight structure may change before the submission owns the parent lock."""
    cedar = load_cedar_baseline()
    maria = cedar.users_by_username["mrodriguez"]
    pip = PIPService.create_draft_for_playbook(
        actor=maria, playbook_id=6106, title="Dependent changes"
    )
    parent = PIPService.add_change(
        actor=maria,
        pip=pip,
        change_type="ADD",
        entity_type="Workflow",
        name="Accessibility Review",
        content="A separate review process.",
        internal_ref="#review-flow",
    )
    child = PIPService.add_change(
        actor=maria,
        pip=pip,
        change_type="ADD",
        entity_type="Activity",
        name="Inspect forms",
        content="Check focus and error recovery.",
        parent_workflow_ref="#review-flow",
    )
    submitting, editing = Client(), Client()
    submitting.force_login(maria)
    editing.force_login(maria)

    def remove_dependency() -> None:
        response = editing.post(reverse("pip_remove_change", args=[pip.pk, parent.pk]))
        assert (response.status_code, response.url) == (
            302,
            reverse("pip_edit", args=[pip.pk]),
        )
        assert pip.changes.get().pk == child.pk

    with summary_processing_scope(
        ("Maria contributes published design guidance.",)
    ) as model:
        stale = _interleave(
            lambda: submitting.post(reverse("pip_submit_review", args=[pip.pk])),
            remove_dependency,
            tables=(_PARENT_TABLE,),
        )

    pip.refresh_from_db()
    assert pip.status == pip.STATUS_DRAFT and pip.submitted_at is None
    assert (stale.status_code, stale.url) == (302, reverse("pip_edit", args=[pip.pk]))
    assert not model.calls
    assert pip.changes.get().pk == child.pk
    assert not pip.playbook.workflows.filter(name=parent.name).exists()


def test_submitter_with_current_draft_can_edit_reorder_and_cancel() -> None:
    """Draft mutators retain their existing return values and cancel remains an alias."""
    cedar = load_cedar_baseline()
    maria = cedar.users_by_username["mrodriguez"]
    pip = PIPService.create_draft_for_playbook(
        actor=maria, playbook_id=6106, title="Original title"
    )
    saved = PIPService.save_draft_header(
        actor=maria, pip=pip, title=" Edited ", summary=" Summary "
    )
    assert saved is pip and (pip.title, pip.summary) == ("Edited", "Summary")
    first, second = (
        PIPService.add_change(
            actor=maria, pip=pip, change_type="ADD", entity_type="Skill", name=name
        )
        for name in ("First skill", "Second skill")
    )
    assert (first.order, second.order) == (1, 2)
    assert PIPService.remove_change(actor=maria, pip=pip, change_id=first.pk) is None
    assert (pip.changes.get().pk, pip.changes.get().order) == (second.pk, 1)
    assert PIPService.cancel_pip(pip, maria) is None
    assert pip.status == pip.STATUS_WITHDRAWN
