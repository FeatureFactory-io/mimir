"""Execute the later-major living specification through real publication paths."""

from __future__ import annotations

from decimal import Decimal

from behave import given, then, when
from behave.runner import Context
from django.test import Client
from django.urls import reverse

from methodology.models import (
    Activity,
    PipChange,
    ProcessImprovementProposal,
    VersionSource,
)
from methodology.services.playbook_service import PlaybookService
from tests.support.experts_release import (
    NoraReleaseCase,
    assert_release_history_preserved,
    build_nora_release_case,
    capture_release_history,
    prepare_reviewed_next_major_pip,
)

_PLAYBOOK_ID = 6302
_FIRST_VERSION = Decimal("1.0")
_LATER_VERSION = Decimal("2.0")
_FIRST_RELEASE_POINTS = 5000
_RELEASE_NOTES = "Publish the accessible workshop guide"


@given("a playbook has already earned its first-release award")
def playbook_has_first_release_award(context: Context) -> None:
    """Normally publish Nora's real draft and retain its complete first award.

    :param context: Real AT context. Example: context.cedar_dataset and client.
    :return: None. Example: retained Nora/6302, v1.0 and single 5000-point award snapshot.
    :raises AssertionError: If baseline identity or actual first release differs.
    """
    case = build_nora_release_case()
    assert case.author == context.cedar_dataset.users_by_username["nberg"]
    assert case.playbook == context.cedar_dataset.playbooks_by_pk[_PLAYBOOK_ID]
    PlaybookService.update_playbook(case.playbook.pk, visibility="public")
    response = case.client.post(
        reverse("playbook_release", kwargs={"pk": case.playbook.pk}),
        {"release_description": _RELEASE_NOTES},
        follow=True,
    )
    assert response.status_code == 200 and response.redirect_chain
    case.playbook.refresh_from_db()
    assert (
        case.playbook.status == "released" and case.playbook.version == _FIRST_VERSION
    )
    original = capture_release_history(case.playbook)
    assert original.recipient_id == case.author.pk
    context.later_release_case = case
    context.original_release_history = original


@when("an accepted PIP publishes its next major version")
def accepted_pip_publishes_next_major(context: Context) -> None:
    """Prepare reviewed fixture, then POST real staff finalization with CSRF.

    :param context: Completed first-release context. Example: Nora/6302 at v1.0.
    :return: None. Example: accepted ADD Activity and v2.0/PIP_SOURCE retained.
    :raises AssertionError: If permission, acceptance, content or next major fails.
    """
    case: NoraReleaseCase = context.later_release_case
    pip = prepare_reviewed_next_major_pip(
        case.playbook, context.cedar_dataset.users_by_username["mrodriguez"]
    )
    change = pip.changes.get()
    assert not Activity.objects.filter(
        workflow=change.parent_workflow, name=change.name
    ).exists()
    staff = Client(enforce_csrf_checks=True)
    actor = context.cedar_dataset.users_by_username["mchen"]
    assert actor.is_staff and actor.pk != pip.created_by_id
    staff.force_login(actor)
    route = reverse("pip_admin_review", kwargs={"pk": pip.pk})
    review = staff.get(route)
    assert review.status_code == 200
    with context.test.captureOnCommitCallbacks(execute=True) as callbacks:
        response = staff.post(
            route,
            {
                "action": "finalize",
                f"decision_{change.pk}": PipChange.ADMIN_ACCEPT,
                "csrfmiddlewaretoken": str(review.context["csrf_token"]),
            },
        )
    assert len(callbacks) == 1 and response.status_code == 302
    assert response.url == reverse("pip_detail", kwargs={"pk": pip.pk})
    assert response.wsgi_request.user.pk == actor.pk
    _assert_later_pip_application(pip, actor.pk)
    context.later_release_pip = pip


def _assert_later_pip_application(
    pip: ProcessImprovementProposal, actor_id: int
) -> None:
    """Require the exact accepted Activity and its single legitimate major receipt.

    :param pip: Actually finalized proposal. Example: Maria's ADD under Nora's book.
    :param actor_id: Real staff ID. Example: Cedar Mike's persisted ID.
    :return: None. Example: accepted change and one v2.0 PIP_SOURCE receipt.
    :raises AssertionError: If the applied content, decision or receipt differs.
    """
    pip.refresh_from_db()
    change = pip.changes.get()
    assert pip.status == pip.STATUS_ACCEPTED and pip.decided_at is not None
    assert change.admin_decision == PipChange.ADMIN_ACCEPT
    assert change.parent_workflow.playbook_id == pip.playbook_id
    assert (
        Activity.objects.filter(
            workflow=change.parent_workflow, name=change.name, guidance=change.content
        ).count()
        == 1
    )
    receipt = pip.playbook.versions.get(version_number=_LATER_VERSION)
    assert (receipt.source, receipt.pip_id, receipt.created_by_id) == (
        VersionSource.PIP_SOURCE,
        pip.pk,
        actor_id,
    )


@then("its author receives no additional 5000 first-release points")
def author_receives_no_repeated_first_release_points(context: Context) -> None:
    """Read the actual complete immutable award and Nora's live release history.

    :param context: Actual finalized-PIP context. Example: Nora/6302 at v2.0.
    :return: None. Example: original row and Nora total 5000 unchanged.
    :raises AssertionError: If any release-award field/count/amount changes.
    """
    case: NoraReleaseCase = context.later_release_case
    assert context.later_release_pip.playbook_id == case.playbook.pk
    assert_release_history_preserved(
        case.playbook,
        context.original_release_history,
        version=str(_LATER_VERSION),
        recipient_total=_FIRST_RELEASE_POINTS,
    )
