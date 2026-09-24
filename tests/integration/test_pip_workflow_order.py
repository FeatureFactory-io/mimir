"""Released workflow positions must survive the hosted MCP API (#186)."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from methodology.models import PipChange, Playbook, Workflow
from methodology.services.pip_admin_service import PIPAdminService
from methodology.services.pip_apply_changes_service import PipApplyChangesService
from methodology.services.pip_service import PIPService


@pytest.fixture
def order_bundle(db):
    author = get_user_model().objects.create_user(username="pip_order", is_staff=True)
    playbook = Playbook.objects.create(
        name="Ordering",
        author=author,
        status="released",
        version="1.0",
    )
    workflows = [
        Workflow.objects.create(playbook=playbook, name=f"Stage {n}", order=n)
        for n in range(1, 4)
    ]
    pip = PIPService.create_draft_for_playbook(
        actor=author,
        playbook_id=playbook.pk,
        title="Move workflow",
    )
    client = APIClient()
    client.force_authenticate(author)
    return author, playbook, workflows, pip, client


def _post_order(bundle, position, index=2):
    _, _, workflows, pip, client = bundle
    return client.post(
        f"/api/pips/{pip.pk}/changes/",
        {
            "change_type": "ALTER",
            "entity_type": "Workflow",
            "target_id": workflows[index].pk,
            "display_order": position,
        },
        format="json",
    )


def test_add_change_with_workflow_position_persists_and_reads_back(order_bundle):
    _, _, workflows, pip, client = order_bundle
    response = _post_order(order_bundle, 1)
    assert response.status_code == 201, response.data
    change = pip.changes.get()
    assert change.display_order == 1
    assert client.get(f"/api/pips/{pip.pk}/").data["changes"][0]["display_order"] == 1
    workflows[-1].refresh_from_db()
    assert workflows[-1].order == 3


@pytest.mark.parametrize(
    "index,position,expected", [(2, 1, [2, 0, 1]), (0, 3, [1, 2, 0]), (1, 2, [0, 1, 2])]
)
def test_finalize_with_workflow_position_shifts_siblings(
    order_bundle, index, position, expected, caplog
):
    author, playbook, workflows, pip, _ = order_bundle
    change = PIPService.add_change(
        actor=author,
        pip=pip,
        change_type="ALTER",
        entity_type="Workflow",
        target_id=workflows[index].pk,
        display_order=position,
    )
    target, _ = PipApplyChangesService.build_target_state_context(
        pip=pip, playbook=playbook
    )
    assert f"Workflow [{workflows[index].pk}] Stage {index + 1} (#{position})" in target
    assert list(playbook.workflows.order_by("order").values_list("pk", flat=True)) == [
        w.pk for w in workflows
    ]
    PIPService.submit_for_review(actor=author, pip=pip)
    pip.refresh_from_db()
    change.admin_decision = PipChange.ADMIN_ACCEPT
    change.save(update_fields=["admin_decision"])
    PIPAdminService.finalize_pip(pip, author)
    assert list(playbook.workflows.order_by("order").values_list("pk", flat=True)) == [
        workflows[i].pk for i in expected
    ]
    assert list(
        playbook.workflows.order_by("order").values_list("order", flat=True)
    ) == [1, 2, 3]
    assert "PIP apply ALTER Workflow" in caplog.text


@pytest.mark.parametrize("position", [0, -1, True, 1.5, "first", 32768])
def test_add_change_with_invalid_position_returns_validation_error(
    order_bundle, position
):
    response = _post_order(order_bundle, position)
    assert response.status_code == 400, response.data
    assert "display_order" in str(response.data)
    assert not order_bundle[3].changes.exists()


@pytest.mark.parametrize(
    "change_type,entity_type", [("ADD", "Workflow"), ("ALTER", "Rule"), ("LINK", "")]
)
def test_add_change_with_unsupported_position_rejects_before_persistence(
    order_bundle, change_type, entity_type
):
    _, _, workflows, pip, client = order_bundle
    response = client.post(
        f"/api/pips/{pip.pk}/changes/",
        {
            "change_type": change_type,
            "entity_type": entity_type,
            "target_id": workflows[0].pk,
            "name": "Ignored order",
            "display_order": 1,
        },
        format="json",
    )
    assert response.status_code == 400
    assert "display_order" in str(response.data)
    assert not pip.changes.exists()
