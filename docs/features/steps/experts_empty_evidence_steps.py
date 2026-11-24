"""S22-only assertions over real public responses and the existing Cedar DB."""

from __future__ import annotations

from behave import then
from behave.runner import Context

from methodology.models import ExpertProfile, Playbook
from methodology.services.experts_service import ExpertsService
from tests.support.experts_html import _walk_elements, element_text, find_by_test_id

_SAM_USERNAME = "skim"
_SAM_PATH = "/experts/skim/"
_SAM_TOTAL = 4800
_EMPTY_EVIDENCE_MESSAGE = "No public released playbooks to show"


@then("Sam Kim's positive Karma identity is shown")
def sam_positive_identity(context: Context) -> None:
    """Check Sam's identity against persisted contribution and profile records.

    :param context: Actual AT state, e.g. the response to "/experts/skim/".
    :return: None; e.g. Sam Kim, 4,800, Research and stored prose reconcile.
    :raises AssertionError: If actual HTTP, identity, score or prose differs.
    """
    response = context.response
    assert response.status_code == 200 and "Location" not in response
    assert response.wsgi_request.path == _SAM_PATH
    sam_id = context.cedar_dataset.user_ids[_SAM_USERNAME]
    projection = ExpertsService().project_user(sam_id)
    assert projection.total_points == _SAM_TOTAL
    assert projection.primary_category == "research"
    assert not Playbook.objects.filter(
        author_id=sam_id, visibility="public", status="released"
    ).exists()
    heading = find_by_test_id(response.content, "expert-name")
    assert heading.name == "h1" and element_text(heading) == "Sam Kim"
    assert (
        element_text(find_by_test_id(response.content, "expert-karma-total"))
        == f"{_SAM_TOTAL:,}"
    )
    assert (
        element_text(find_by_test_id(response.content, "expert-primary-category"))
        == "Research"
    )
    person = response.context["person"]
    assert person["subject_id"] == sam_id and person["name"] == "Sam Kim"
    stored = ExpertProfile.objects.get(user_id=sam_id).contribution_summary
    assert stored and person["summary"] == stored
    assert (
        element_text(find_by_test_id(response.content, "expert-contribution-summary"))
        == stored
    )


@then('the evidence section says "{message}"')
def evidence_section_says(context: Context, message: str) -> None:
    """Check exact empty evidence text inside the real evidence section.

    :param context: Real response context. Example: Sam's production profile.
    :param message: Required text. Example: "No public released playbooks to show".
    :return: None. Example: exact message and absence of evidence links verified.
    :raises ValueError: If the expected message differs from the exact contract.
    :raises AssertionError: If text is misplaced, absent or evidence links exist.
    """
    if message != _EMPTY_EVIDENCE_MESSAGE:
        raise ValueError("S22 requires the exact public-evidence empty message.")
    response = context.response
    assert response.status_code == 200 and response.wsgi_request.path == _SAM_PATH
    person = response.context["person"]
    assert person["subject_id"] == context.cedar_dataset.user_ids[_SAM_USERNAME]
    assert person["public_playbooks"] == ()
    section = find_by_test_id(response.content, "expert-public-playbooks")
    assert element_text(section) == f"Public released playbooks {message}"
    nodes = tuple(_walk_elements(section))
    assert [element_text(node) for node in nodes if node.name == "h2"] == [
        "Public released playbooks"
    ]
    assert [element_text(node) for node in nodes if node.name == "p"] == [message]
    if any(node.name == "a" for node in nodes):
        raise AssertionError("Empty evidence section contains a public action.")
