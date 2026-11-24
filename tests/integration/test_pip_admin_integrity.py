"""Protect published decisions through Django's registered admin forms."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from django import forms
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import Permission
from django.urls import reverse

from methodology.models import (
    Activity,
    KarmaAward,
    PipChange,
    ProcessImprovementProposal,
)
from methodology.services.karma_service import KarmaService
from tests.support.experts_data import (
    create_reviewed_major_add_pip,
    load_cedar_baseline,
)

if TYPE_CHECKING:
    from django.core.mail import EmailMessage
    from django.test import Client

pytestmark = pytest.mark.django_db(transaction=True)

_PROPOSAL = "processimprovementproposal"
_CHANGE = "pipchange"
_DECIDED_MESSAGE = "This PIP has already been decided and cannot be modified."
_PUBLISHED_NOTE = "Published review note"


@pytest.fixture
def registered_review(client: Client) -> ProcessImprovementProposal:
    """Log in as Cedar's existing staff reviewer with ordinary admin permissions."""
    cedar = load_cedar_baseline()
    staff = cedar.users_by_username["mchen"]
    assert staff.is_staff and not staff.is_superuser
    codenames = [
        f"{action}_{model}"
        for action in ("add", "change", "delete")
        for model in (_PROPOSAL, _CHANGE)
    ]
    staff.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="methodology", codename__in=codenames
        )
    )
    client.force_login(staff)
    return create_reviewed_major_add_pip(cedar, PipChange.ENTITY_ACTIVITY)


def _admin_url(model: str, view: str, *args: int) -> str:
    """Resolve a normal Django Admin URL for the registered model."""
    return reverse(f"admin:methodology_{model}_{view}", args=args)


def _form_data(form: forms.BaseForm) -> dict[str, object]:
    """Supply the current inputs of a real bound-to-instance admin form."""
    data = {}
    for name, field in form.fields.items():
        value = form[name].value()
        key = form.add_prefix(name)
        if isinstance(field.widget, forms.SplitDateTimeWidget):
            date, time = field.widget.decompress(value)
            data[f"{key}_0"] = date or ""
            data[f"{key}_1"] = time or ""
        elif not isinstance(field.widget, forms.CheckboxInput) or value:
            data[key] = "" if value is None else value
    return data


def _stale_form(
    client: Client, pip: ProcessImprovementProposal, model: str
) -> tuple[str, dict[str, object]]:
    """Open an undecided edit and retain the exact inputs for a normal POST."""
    change = pip.changes.get()
    url = _admin_url(model, "change", change.pk if model == _CHANGE else pip.pk)
    response = client.get(url)
    assert response.status_code == 200 and response.context["has_change_permission"]
    data = {**_form_data(response.context["adminform"].form), "_save": "Save"}
    if model == _PROPOSAL:
        inline = response.context["inline_admin_formsets"][0].formset
        data.update(_form_data(inline.management_form))
        data.update(_form_data(inline.forms[0]))
        prefix = inline.forms[0].prefix + "-"
    else:
        prefix = ""
    assert f"{prefix}admin_decision" in data and f"{prefix}admin_note" in data
    data.update(
        {
            f"{prefix}admin_decision": PipChange.ADMIN_REJECT,
            f"{prefix}admin_note": "Edited review note",
        }
    )
    return url, data


def _publish(
    client: Client, pip: ProcessImprovementProposal, change: PipChange
) -> None:
    """Publish through the standard staff review action and capture its real effects."""
    response = client.post(
        reverse("pip_admin_review", args=[pip.pk]),
        {
            "action": "finalize",
            f"decision_{change.pk}": PipChange.ADMIN_ACCEPT,
            f"note_{change.pk}": _PUBLISHED_NOTE,
        },
    )
    assert (response.status_code, response.url) == (
        302,
        reverse("pip_detail", args=[pip.pk]),
    )
    pip.refresh_from_db()
    change.refresh_from_db()
    assert pip.status == pip.STATUS_ACCEPTED and pip.decided_at
    assert (change.admin_decision, change.admin_note) == (
        PipChange.ADMIN_ACCEPT,
        _PUBLISHED_NOTE,
    )


def _publication(
    pip: ProcessImprovementProposal, change: PipChange
) -> tuple[object, ...]:
    """Read the exact persisted proposal, change, publication, content and award."""
    receipt = pip.playbook_versions.values().get()
    award = KarmaAward.objects.values().get(
        event_identity=f"accepted_change:{change.pk}"
    )
    activity = (
        Activity.objects.filter(workflow__playbook_id=pip.playbook_id, name=change.name)
        .values()
        .get()
    )
    assert receipt["snapshot_data"]["accepted_change_ids"] == [change.pk]
    assert award["points"] == 500 and activity["guidance"] == change.content
    assert pip.playbook.version == Decimal("3.0")
    return (
        ProcessImprovementProposal.objects.values().get(pk=pip.pk),
        pip.changes.values().get(),
        receipt,
        activity,
        award,
    )


def _assert_read_only(client: Client, url: str) -> None:
    """A published form shows the saved note and has no editing controls."""
    view = client.get(url)
    assert view.status_code == 200
    assert not view.context["has_change_permission"]
    assert not view.context["has_delete_permission"]
    assert _DECIDED_MESSAGE in view.content.decode()
    assert (
        b'name="_save"' not in view.content and b"Finalize Decision" not in view.content
    )
    assert not re.search(rb'\bname="(?:[^"]+-)?admin_(?:decision|note)"', view.content)
    assert _PUBLISHED_NOTE in view.content.decode()


@pytest.mark.parametrize("model", [_CHANGE, _PROPOSAL])
def test_registered_admin_with_stale_form_preserves_publication(
    client: Client,
    registered_review: ProcessImprovementProposal,
    mailoutbox: list[EmailMessage],
    model: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A reviewed form left open before finalization cannot change the published record."""
    pip = registered_review
    change = pip.changes.get()
    url, stale_data = _stale_form(client, pip, model)
    _publish(client, pip, change)
    before = _publication(pip, change)
    if model == _PROPOSAL:
        stale_data.update(title="Edited title", status=pip.STATUS_DRAFT)

    denied = client.post(url, stale_data)
    pip.refresh_from_db()
    change.refresh_from_db()
    assert (change.admin_decision, change.admin_note) == (
        PipChange.ADMIN_ACCEPT,
        _PUBLISHED_NOTE,
    )
    assert _publication(pip, change) == before
    assert denied.status_code == 403

    _assert_read_only(client, url)
    assert _publication(pip, change) == before
    assert any(
        record.name == "methodology.admin"
        and f"pip_id={pip.pk} correlation_id=pip_review:{pip.pk} reason=decided"
        in record.message
        for record in caplog.records
    )
    (outcome,) = KarmaService.award_accepted_changes(
        pip=pip, correlation_id="s32:registered_admin"
    )
    assert (
        not outcome.created
        and outcome.reason == "duplicate"
        and outcome.award.points == 500
    )
    (email,) = mailoutbox
    assert email.to == [pip.created_by.email] and "Decision: ACCEPT" in email.body


@pytest.mark.parametrize("model", [_CHANGE, _PROPOSAL])
def test_registered_admin_with_reviewed_form_saves_decision(
    client: Client,
    registered_review: ProcessImprovementProposal,
    model: str,
) -> None:
    """Ordinary staff can submit decisions through either undecided form."""
    pip = registered_review
    url, data = _stale_form(client, pip, model)
    saved = client.post(url, data)
    assert saved.status_code == 302, saved.context and saved.context["errors"]
    pip.refresh_from_db()
    change = pip.changes.get()
    assert pip.status == pip.STATUS_REVIEWED and pip.decided_at is None
    assert (change.admin_decision, change.admin_note) == (
        PipChange.ADMIN_REJECT,
        "Edited review note",
    )


def test_registered_admin_with_reviewed_selection_finalizes_normally(
    client: Client,
    registered_review: ProcessImprovementProposal,
    mailoutbox: list[EmailMessage],
) -> None:
    """The existing Django Admin action can still publish a saved decision."""
    pip = registered_review
    url, data = _stale_form(client, pip, _CHANGE)
    data.update(admin_decision=PipChange.ADMIN_ACCEPT, admin_note=_PUBLISHED_NOTE)
    assert client.post(url, data).status_code == 302
    response = client.post(
        _admin_url(_PROPOSAL, "changelist"),
        {
            "action": "finalize_reviewed_pips",
            ACTION_CHECKBOX_NAME: [pip.pk],
            "index": 0,
        },
    )
    assert response.status_code == 302
    pip.refresh_from_db()
    assert pip.status == pip.STATUS_ACCEPTED and pip.decided_at
    assert _publication(pip, pip.changes.get())
    assert len(mailoutbox) == 1


def test_registered_child_admin_with_terminal_destination_denies_add_and_move(
    client: Client,
    registered_review: ProcessImprovementProposal,
) -> None:
    """A child cannot be attached to a finalized proposal through either child form."""
    terminal = registered_review
    terminal_change = terminal.changes.get()
    url, data = _stale_form(client, terminal, _CHANGE)
    _publish(client, terminal, terminal_change)
    editable = ProcessImprovementProposal.objects.create(
        playbook=terminal.playbook, title="Editable draft"
    )
    data["pip"] = editable.pk
    added = client.post(_admin_url(_CHANGE, "add"), data)
    assert added.status_code == 302, added.context and added.context["errors"]
    child = editable.changes.get()

    data["pip"] = terminal.pk
    assert client.post(_admin_url(_CHANGE, "add"), data).status_code == 403
    assert client.post(_admin_url(_CHANGE, "change", child.pk), data).status_code == 403
    child.refresh_from_db()
    assert child.pip_id == editable.pk and terminal.changes.get() == terminal_change
    data["pip"] = editable.pk
    assert client.post(url, data).status_code == 403
    assert terminal.changes.get() == terminal_change


@pytest.mark.parametrize("model", [_CHANGE, _PROPOSAL])
def test_registered_admin_with_terminal_selection_denies_delete(
    client: Client,
    registered_review: ProcessImprovementProposal,
    model: str,
) -> None:
    """Neither direct deletion nor a confirmed bulk deletion removes a terminal row."""
    pip = registered_review
    change = pip.changes.get()
    _publish(client, pip, change)
    pk = change.pk if model == _CHANGE else pip.pk
    assert (
        client.post(_admin_url(model, "delete", pk), {"post": "yes"}).status_code == 403
    )
    assert (
        client.post(
            _admin_url(model, "changelist"),
            {
                "action": "delete_selected",
                ACTION_CHECKBOX_NAME: [pk],
                "post": "yes",
            },
        ).status_code
        == 403
    )
    assert ProcessImprovementProposal.objects.get(pk=pip.pk).changes.get() == change
