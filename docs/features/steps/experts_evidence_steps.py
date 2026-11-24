"""S19-specific Django-client acceptance bindings."""

from __future__ import annotations

from http import HTTPStatus

from behave import given, then, when
from behave.runner import Context
from django.http import HttpResponse
from django.test.html import Element
from django.urls import reverse

from tests.support.experts_html import _walk_elements, element_text, find_by_test_id

_ELENA_USERNAME = "esvensson"
_MARIA_USERNAME = "mrodriguez"
_PLAYBOOK_ID = 6101
_WORKFLOW_ID = 6203


@given("Elena is on Maria's public expert profile")
def elena_on_maria_public_profile(context: Context) -> None:
    """Authenticate baseline Elena and request Maria's real public detail.

    :param context: Shared Cedar/client context. Example: context.cedar_dataset.
    :return: None. Example: context.response contains HTTP 200.
    :raises AssertionError: If the real public profile is unavailable.
    """
    path = reverse("expert_detail", args=[_MARIA_USERNAME])
    context.execute_steps(f'Given Elena is authenticated\nWhen Elena opens "{path}"')
    _assert_destination(context, path, "experts/detail.html")
    assert context.response.context["person"]["subject_id"] == (
        context.cedar_dataset.user_ids[_MARIA_USERNAME]
    )


@when('she follows "{title}" version "{version}"')
def follow_public_evidence(context: Context, title: str, version: str) -> None:
    """Match an evidence item and request its extracted local href.

    :param context: Real profile response. Example: Maria's public detail.
    :param title: Exact playbook title. Example: "Accessibility Audit Playbook".
    :param version: Exact displayed version. Example: "1.0".
    :return: None. Example: context.response contains the destination response.
    :raises AssertionError: If evidence is missing, ambiguous or mismatched.
    """
    link = _public_evidence_link(context.response.content, title, version)
    expected_path = reverse("playbook_detail", args=[_PLAYBOOK_ID])
    _follow_expected_anchor(context, link, expected_path)


@then('the existing playbook detail route "{path}" is shown')
def existing_playbook_route_shown(context: Context, path: str) -> None:
    """Check actual request path, status and existing detail template.

    :param context: Followed real response. Example: playbook 6101 response.
    :param path: Required destination. Example: "/playbooks/6101/".
    :return: None. Example: None after HTTP 200 and template assertions.
    :raises AssertionError: If actual routing differs or redirects to login.
    """
    _assert_destination(context, path, "playbooks/detail.html")
    playbook = context.response.context["playbook"]
    assert playbook.pk == _PLAYBOOK_ID
    assert playbook.author_id == context.cedar_dataset.user_ids[_MARIA_USERNAME]


@then('its workflow "{workflow}" includes "{first}" and "{second}"')
def followed_workflow_includes_activities(
    context: Context, workflow: str, first: str, second: str
) -> None:
    """Follow the real workflow anchor and inspect returned activity evidence.

    :param context: Real playbook detail response. Example: playbook 6101.
    :param workflow: Exact workflow. Example: "Lead an Accessibility Review".
    :param first: Required activity. Example: "Trace Keyboard Focus".
    :param second: Required activity. Example: "Review Form Feedback".
    :return: None. Example: None after real workflow HTTP 200/content checks.
    :raises AssertionError: If workflow membership or either activity differs.
    """
    html = context.response.content
    section = find_by_test_id(html, "workflows-section")
    link = find_by_test_id(html, f"workflow-name-link-{_WORKFLOW_ID}")
    assert link in section and element_text(link) == workflow
    path = reverse("workflow_detail", args=[_PLAYBOOK_ID, _WORKFLOW_ID])
    _follow_expected_anchor(context, link, path)
    _assert_destination(context, path, "workflows/detail.html")
    _assert_workflow_activities(context.response, workflow, {first, second})


def _public_evidence_link(html: bytes, title: str, version: str) -> Element:
    """Find the titled and versioned entry with the real public evidence anchor.

    :param html: Public profile response content. Example: response.content.
    :param title: Required entry heading. Example: "Accessibility Audit Playbook".
    :param version: Required version without prefix. Example: "1.0".
    :return: Parsed anchor. Example: the entry's accessible View link.
    :raises AssertionError: For an incorrect heading, version or link name.
    """
    section = find_by_test_id(html, "expert-public-playbooks")
    assert "Public released playbooks" in element_text(section)
    link = find_by_test_id(html, f"expert-playbook-{_PLAYBOOK_ID}")
    entries = [node for node in _walk_elements(section) if link in node.children]
    assert len(entries) == 1, "The anchor must belong to one public evidence entry."
    fields = {
        child.name: element_text(child)
        for child in entries[0].children
        if isinstance(child, Element)
    }
    assert fields.get("h3") == title, "The evidence heading differs."
    assert fields.get("p", "").split()[-1:] == [f"v{version}"]
    assert dict(link.attributes).get("aria-label") == f"View {title}"
    return link


def _follow_expected_anchor(context: Context, link: Element, path: str) -> None:
    """Request the extracted href after checking it against the reversed local route.

    :param context: Existing signed-in Django client. Example: Elena's session.
    :param link: Rendered anchor. Example: expert-playbook-6101.
    :param path: Reversed local path. Example: "/playbooks/6101/".
    :return: None. Example: context.response now contains the playbook detail.
    :raises AssertionError: If href does not exactly match the expected route.
    """
    assert link.name == "a", "The evidence destination must be an anchor."
    href = dict(link.attributes).get("href")
    assert href == path, "The rendered href differs from its existing local route."
    context.execute_steps(f'When Elena opens "{href}"')


def _assert_destination(context: Context, path: str, template: str) -> None:
    """Confirm a real detail response at the expected route in Elena's session.

    :param context: Current Django-client response. Example: context.response.
    :param path: Expected request path. Example: "/playbooks/6101/".
    :param template: Expected real template. Example: "playbooks/detail.html".
    :return: None. Example: no redirect and correct response identity.
    :raises AssertionError: If status, request path, template or user differs.
    """
    response = context.response
    assert response.status_code == HTTPStatus.OK and "Location" not in response
    assert response.wsgi_request.get_full_path() == path
    assert (
        response.wsgi_request.user
        == context.cedar_dataset.users_by_username[_ELENA_USERNAME]
    )
    context.test.assertTemplateUsed(response, template)


def _assert_workflow_activities(
    response: HttpResponse, workflow: str, expected: set[str]
) -> None:
    """Check the rendered graph labels and membership in the selected workflow.

    :param response: Real workflow detail response. Example: HTTP 200 for Cedar 6203.
    :param workflow: Expected workflow name. Example: "Lead an Accessibility Review".
    :param expected: Required activity names. Example: {"Trace Keyboard Focus"}.
    :return: None. Example: all expected activities are rendered and related.
    :raises AssertionError: If the workflow, its owner or its activities differ.
    """
    assert response.context["playbook"].pk == _PLAYBOOK_ID
    actual_workflow = response.context["workflow"]
    assert actual_workflow.pk == _WORKFLOW_ID
    assert actual_workflow.playbook_id == _PLAYBOOK_ID
    assert element_text(find_by_test_id(response.content, "workflow-name")) == workflow
    graph = find_by_test_id(response.content, "activities-graph")
    labels = {
        element_text(node) for node in _walk_elements(graph) if node.name == "text"
    }
    assert expected <= labels, "A required activity label is missing from the graph."
    activity_names = {
        activity.name
        for activity in response.context["activities"]
        if activity.workflow_id == actual_workflow.pk
    }
    assert (
        expected <= activity_names
    ), "A required activity belongs to another workflow."
