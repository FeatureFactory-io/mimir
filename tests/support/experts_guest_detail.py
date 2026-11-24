"""Server-only assertions for guest public-detail evidence."""

from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, cast

from django.http import HttpResponse
from django.test import Client
from django.test.html import Element
from django.urls import reverse

from methodology.models import ExpertProfile, Playbook, Workflow
from methodology.services.expert_contact_context import ExpertContactContext
from tests.support.experts_data import CedarDataset
from tests.support.experts_guest_contact import (
    GUEST_CONTACT_EXPLANATION,
    assert_guest_contact_markup,
)
from tests.support.experts_html import (
    assert_karma_source_rows,
    element_text,
    find_by_test_id,
)
from tests.support.experts_privacy import (
    assert_public_projection,
    assert_public_response,
)

_MARIA = "mrodriguez"
_PUBLIC_BOOK = 6101
_SOURCE_LABELS = {
    "Released": "Released playbooks",
    "PIP": "PIP contributions",
    "Consumption": "Consumption",
    "Learning": "Learning",
}
_WORKFLOW = "Lead an Accessibility Review"
_ACTIVITIES = (
    "Trace Keyboard Focus",
    "Review Form Feedback",
    "Document Recovery Paths",
)


def assert_guest_detail_evidence_readable(
    client: Client, response: HttpResponse, dataset: CedarDataset
) -> None:
    """Check actual anonymous prose, restricted contact and a readable public release.

    :param client: Anonymous real Django client, e.g. Client().
    :param response: Actual detail response, e.g. GET /experts/mrodriguez/.
    :param dataset: Persisted Cedar rows and independent oracle, e.g. Maria.
    :return: None after complete summary and public evidence assertions pass.
    :raises AssertionError: If status, prose, privacy, contact or evidence differs.
    """
    assert response.status_code == HTTPStatus.OK
    assert not response.wsgi_request.user.is_authenticated
    assert not client.cookies
    assert_public_response(response, dataset, authenticated=False)
    _assert_contact_projection(response, dataset)
    _assert_summary_and_totals(response, dataset)
    evidence = _follow_public_playbook(client, response, dataset)
    _assert_public_workflow(client, evidence)
    assert not client.cookies


def _assert_contact_projection(response: HttpResponse, dataset: CedarDataset) -> None:
    """Validate only designated public/contact values, never the Django context.

    :param response: Actual anonymous Maria detail response.
    :param dataset: Persisted Cedar users supplying account-email probes.
    :return: None after exact contact schema and initial markup checks pass.
    :raises AssertionError: If a contact value or initial disabled control differs.
    """
    presentation = response.context["contact_person"]
    assert type(presentation) is dict
    contact = presentation["contact"]
    assert contact == ExpertContactContext(
        _MARIA, "authentication_required", None, GUEST_CONTACT_EXPLANATION
    )
    assert type(contact) is ExpertContactContext
    public = {key: value for key, value in presentation.items() if key != "contact"}
    assert_public_projection(public, dataset)
    assert_guest_contact_markup(
        response, None, tuple(user.email for user in dataset.users_by_username.values())
    )


def _assert_summary_and_totals(response: HttpResponse, dataset: CedarDataset) -> None:
    """Reconcile full stored prose, total and each source/category value with Cedar.

    :param response: Actual rendered public detail response.
    :param dataset: Real Maria row plus independent imported oracle.
    :return: None when full prose and all displayed breakdown values reconcile.
    :raises AssertionError: If stored prose or a displayed number differs.
    """
    people = cast(list[Mapping[str, Any]], dataset.oracle["people"])
    oracle = next(person for person in people if person["username"] == _MARIA)
    stored = ExpertProfile.objects.get(user=dataset.users_by_username[_MARIA])
    assert stored.contribution_summary == oracle["summary"]
    summary = find_by_test_id(response.content, "expert-contribution-summary")
    assert element_text(summary) == stored.contribution_summary
    assert oracle["total_karma"] == 8200
    assert_karma_source_rows(
        response.content.decode(),
        {
            _SOURCE_LABELS[label]: points
            for label, points in oracle["karma_by_source"].items()
        },
        "expert-karma-total",
        8200,
    )
    category = find_by_test_id(response.content, "karma-category-breakdown")
    rows = [node for node in category.children if isinstance(node, Element)]
    expected = [
        (label, f"{points:,}") for label, points in oracle["karma_by_category"].items()
    ]
    assert [element_text(node) for node in rows] == [
        value for pair in expected for value in pair
    ]


def _follow_public_playbook(
    client: Client, response: HttpResponse, dataset: CedarDataset
) -> HttpResponse:
    """Follow the rendered production evidence anchor using the same guest client.

    :param client: Actual anonymous Django client without session cookies.
    :param response: Actual Maria public-detail response.
    :param dataset: Real public book 6101 owned by Maria.
    :return: Actual public playbook response, e.g. HTTP200 at /playbooks/6101/.
    :raises AssertionError: If eligibility, metadata, link or destination differs.
    """
    book = Playbook.objects.get(pk=dataset.playbooks_by_pk[_PUBLIC_BOOK].pk)
    assert (book.visibility, book.status, str(book.version)) == (
        "public",
        "released",
        "1.0",
    )
    assert book.author_id == dataset.user_ids[_MARIA]
    section = find_by_test_id(response.content, "expert-public-playbooks")
    assert book.name in element_text(section) and "Design · v1.0" in element_text(
        section
    )
    link = find_by_test_id(str(section), f"expert-playbook-{book.pk}")
    assert link.name == "a"
    assert dict(link.attributes).get("aria-label") == f"View {book.name}"
    href = dict(link.attributes).get("href")
    assert href == reverse("playbook_detail", args=[book.pk])
    assert "/mockups/" not in href
    evidence = client.get(href, follow=False)
    assert evidence.status_code == HTTPStatus.OK
    assert not evidence.wsgi_request.user.is_authenticated
    assert evidence.context["playbook"].pk == book.pk
    assert book.name in element_text(
        find_by_test_id(evidence.content, "playbook-header")
    )
    return evidence


def _assert_public_workflow(client: Client, evidence: HttpResponse) -> None:
    """Follow actual workflow navigation into readable keyboard/form-feedback evidence.

    :param client: Same anonymous real Django client, e.g. Client().
    :param evidence: Actual public playbook response for book6101.
    :return: None after real workflow content and actor checks pass.
    :raises AssertionError: If navigation fails or public activity evidence vanishes.
    """
    workflow = Workflow.objects.get(playbook_id=_PUBLIC_BOOK, name=_WORKFLOW)
    section = find_by_test_id(evidence.content, "workflows-section")
    link = find_by_test_id(str(section), f"workflow-name-link-{workflow.pk}")
    assert link.name == "a" and element_text(link) == _WORKFLOW
    href = dict(link.attributes).get("href")
    assert href == reverse("workflow_detail", args=[_PUBLIC_BOOK, workflow.pk])
    response = client.get(href, follow=False)
    assert response.status_code == HTTPStatus.OK
    assert not response.wsgi_request.user.is_authenticated
    assert response.context["workflow"].pk == workflow.pk
    assert element_text(find_by_test_id(response.content, "workflow-name")) == _WORKFLOW
    graph = element_text(find_by_test_id(response.content, "activities-graph"))
    activities = {
        activity.name: activity for activity in response.context["activities"]
    }
    for name in _ACTIVITIES:
        assert name in graph and activities[name].workflow_id == workflow.pk
