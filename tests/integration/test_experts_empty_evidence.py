"""Real-DB certification of positive Experts profiles without eligible evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from html import unescape
from http import HTTPStatus
from typing import cast

import pytest
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.db import connection
from django.http import HttpResponse
from django.test import Client
from django.test.utils import CaptureQueriesContext
from rest_framework.authtoken.models import Token

from methodology.models import (
    AgentInteraction,
    ExpertProfile,
    KarmaAward,
    Playbook,
    ProcessImprovementProposal,
)
from methodology.services.experts_service import ExpertsService
from tests.support.experts_data import CedarDataset
from tests.support.experts_html import (
    _walk_elements,
    assert_karma_source_rows,
    element_text,
    find_by_test_id,
)
from tests.support.experts_privacy import _assert_private_markers_absent

pytestmark = pytest.mark.django_db

_PUBLIC_BOOK_ID = 6101
_EMPTY_EVIDENCE_TEXT = "Public released playbooks No public released playbooks to show"
_READ_ONLY_MODELS = (
    User,
    Token,
    Playbook,
    ProcessImprovementProposal,
    KarmaAward,
    ExpertProfile,
    AgentInteraction,
)
_WRITE_PREFIXES = ("INSERT ", "UPDATE ", "DELETE ", "REPLACE ", "CREATE ", "DROP ")
_SESSION_REFRESH_PREFIX = 'UPDATE "DJANGO_SESSION" SET '
_SAM_SOURCES = {"Released": 0, "PIP": 4600, "Consumption": 0, "Learning": 200}
_SAM_DISPLAY_SOURCES = {
    "Released playbooks": 0,
    "PIP contributions": 4600,
    "Consumption": 0,
    "Learning": 200,
}
_MARIA_SOURCES = {
    "Released playbooks": 5000,
    "PIP contributions": 1600,
    "Consumption": 1200,
    "Learning": 400,
}


def test_expert_detail_with_positive_sam_without_public_playbooks_returns_profile(
    client: Client, cedar_dataset: CedarDataset, mailoutbox: list[EmailMessage]
) -> None:
    """Certify Sam's positive profile independently of authored public releases.

    :param client: Real Django client, e.g. Elena's authenticated client.
    :param cedar_dataset: Independently restored Cedar records, e.g. Sam Kim.
    :param mailoutbox: Local-only mail capture, e.g. an empty list.
    :return: None after identity, empty evidence and read-only checks pass.
    :raises AssertionError: If Sam is rejected or the GET changes persisted state.
    """
    sam = cedar_dataset.users_by_username["skim"]
    assert not Playbook.objects.filter(
        author=sam, visibility="public", status="released"
    ).exists()
    assert not sam.karma_awards.filter(
        source_kind=KarmaAward.SourceKind.RELEASE
    ).exists()
    projection = ExpertsService().project_user(sam.pk)
    assert projection.total_points == 4800 and projection.primary_category == "research"
    assert dict(projection.source_points) == _SAM_SOURCES
    client.force_login(cedar_dataset.users_by_username["esvensson"])
    response = _read_unchanged(client, cedar_dataset, "skim", mailoutbox)
    _assert_identity(response, cedar_dataset, "skim", "Sam Kim", "Research", 4800)
    assert_karma_source_rows(
        response.content, _SAM_DISPLAY_SOURCES, "expert-karma-total", 4800
    )
    _assert_empty_evidence(response)


@pytest.mark.parametrize(
    ("visibility", "status"),
    [("private", "released"), ("public", "draft"), ("public", "disabled")],
)
def test_expert_detail_with_only_ineligible_current_playbook_keeps_positive_profile(
    client: Client,
    cedar_dataset: CedarDataset,
    mailoutbox: list[EmailMessage],
    visibility: str,
    status: str,
) -> None:
    """Exclude each current-state variant without rewriting Maria's history.

    :param client: Real Django client, e.g. Elena's authenticated client.
    :param cedar_dataset: Independently restored Cedar objects, e.g. book6101.
    :param mailoutbox: Local-only mail capture, e.g. an empty list.
    :param visibility: Current visibility, e.g. "private".
    :param status: Current status, e.g. "released".
    :return: None after the positive profile and empty evidence reconcile.
    :raises AssertionError: If ineligible evidence leaks or history changes.
    """
    book = cedar_dataset.playbooks_by_pk[_PUBLIC_BOOK_ID]
    assert (book.visibility, book.status) == ("public", "released")
    Playbook.objects.filter(pk=book.pk).update(visibility=visibility, status=status)
    book.refresh_from_db()
    assert (book.visibility, book.status) == (visibility, status)
    client.force_login(cedar_dataset.users_by_username["esvensson"])
    response = _read_unchanged(client, cedar_dataset, "mrodriguez", mailoutbox)
    _assert_identity(
        response, cedar_dataset, "mrodriguez", "Maria Rodriguez", "Design", 8200
    )
    assert_karma_source_rows(
        response.content, _MARIA_SOURCES, "expert-karma-total", 8200
    )
    _assert_empty_evidence(response)
    if f"expert-playbook-{book.pk}" in response.content.decode(response.charset):
        raise AssertionError("Ineligible playbook retained a public evidence action.")


def _snapshot() -> tuple[tuple[dict[str, object], ...], ...]:
    """Copy every concrete field from the seven guarded model tables.

    :return: Ordered immutable row groups, e.g. an unchanged award ledger.
    :raises RuntimeError: If a real database query fails.
    """
    return tuple(
        tuple(model.objects.order_by("pk").values()) for model in _READ_ONLY_MODELS
    )


def _read_unchanged(
    client: Client,
    dataset: CedarDataset,
    username: str,
    mailoutbox: list[EmailMessage],
) -> HttpResponse:
    """Perform the production GET with actual privacy and no-write guards.

    :param client: Prepared real client, e.g. Elena after force_login.
    :param dataset: Real persisted Cedar fixture, e.g. positive Sam.
    :param username: Exact production subject, e.g. "skim".
    :param mailoutbox: Local mail capture, e.g. an empty list.
    :return: Actual response, e.g. HTTP200 without Location.
    :raises AssertionError: For a write, private leak or unexpected response.
    """
    private_markers = _persisted_private_markers(dataset)
    before, mail_before = _snapshot(), tuple(mailoutbox)
    with CaptureQueriesContext(connection) as queries:
        response = client.get(f"/experts/{username}/")
    assert response.status_code == HTTPStatus.OK and "Location" not in response
    assert response.wsgi_request.user.pk == dataset.user_ids["esvensson"]
    if _snapshot() != before or tuple(mailoutbox) != mail_before:
        raise AssertionError("Public profile GET changed persisted records or mail.")
    # The existing shell refreshes Elena's session on every authenticated request.
    if any(
        query["sql"].lstrip().upper().startswith(_WRITE_PREFIXES)
        and not query["sql"].lstrip().upper().startswith(_SESSION_REFRESH_PREFIX)
        for query in queries
    ):
        raise AssertionError("Public profile GET executed a database write.")
    document = unescape(response.content.decode(response.charset))
    _assert_private_markers_absent(document, dataset, allow_contact=True)
    if any(marker and marker in document for marker in private_markers):
        raise AssertionError("A persisted private field leaked into the response.")
    return response


def _persisted_private_markers(dataset: CedarDataset) -> tuple[str, ...]:
    """Verify actual private fixtures before scanning their real field values.

    :param dataset: Cedar records and independent oracle, e.g. Maria's private book.
    :return: Sensitive strings for omission checks, never diagnostic output.
    :raises AssertionError: If a required private fixture is absent.
    """
    people = cast(Sequence[Mapping[str, object]], dataset.oracle["people"])
    maria = next(person for person in people if person["username"] == "mrodriguez")
    owner = dataset.users_by_username["mrodriguez"]
    token = cast(str, maria["private_token"])
    if not Token.objects.filter(user=owner, key=token).exists():
        raise AssertionError("Actual Cedar private token is missing.")
    titles = cast(list[str], maria["private_playbooks"])
    books = Playbook.objects.filter(author=owner, visibility="private", name__in=titles)
    title = titles[0]
    if not books.filter(name=title).exists():
        raise AssertionError("Actual Cedar private playbook is missing.")
    pips = ProcessImprovementProposal.objects.filter(
        created_by=owner, title=maria["private_pip"], status="draft"
    )
    if not pips.exists():
        raise AssertionError("Actual Cedar private proposal is missing.")
    return (
        token,
        *(value for row in books.values_list("name", "description") for value in row),
        *(value for row in pips.values_list("title", "summary") for value in row),
    )


def _assert_identity(
    response: HttpResponse,
    dataset: CedarDataset,
    username: str,
    name: str,
    category: str,
    total: int,
) -> None:
    """Check production public identity, stored prose and authorized contact.

    :param response: Real public profile response, e.g. Sam's HTTP200.
    :param dataset: Restored Cedar records, e.g. Sam's actual stored profile.
    :param username: Public subject, e.g. "skim".
    :param name: Expected public H1, e.g. "Sam Kim".
    :param category: Display category, e.g. "Research".
    :param total: Historical total, e.g.4800.
    :return: None after independent markup and DTO values reconcile.
    :raises AssertionError: If identity, prose, score or contact differs.
    """
    body = response.content
    heading = find_by_test_id(body, "expert-name")
    assert heading.name == "h1" and element_text(heading) == name
    assert element_text(find_by_test_id(body, "expert-primary-category")) == category
    assert element_text(find_by_test_id(body, "expert-karma-total")) == f"{total:,}"
    person = response.context["person"]
    assert person["subject_id"] == dataset.user_ids[username]
    assert person["formatted_karma"] == f"{total:,}" and person["name"] == name
    stored = ExpertProfile.objects.get(user_id=dataset.user_ids[username])
    assert person["summary"] == stored.contribution_summary
    assert (
        element_text(find_by_test_id(body, "expert-contribution-summary"))
        == stored.contribution_summary
    )
    contact = find_by_test_id(body, f"experts-reach-out-{username}")
    assert contact.name == "a"
    expected_href = f"mailto:{dataset.users_by_username[username].email}"
    if dict(contact.attributes).get("href") != expected_href:
        raise AssertionError("Elena's authorized contact destination changed.")


def _assert_empty_evidence(response: HttpResponse) -> None:
    """Check exact evidence explanation and absence of every evidence anchor.

    :param response: Actual profile with no eligible books, e.g. Sam's profile.
    :return: None after the section and designated public DTO are empty.
    :raises AssertionError: If text differs or an evidence action remains.
    """
    section = find_by_test_id(response.content, "expert-public-playbooks")
    if element_text(section) != _EMPTY_EVIDENCE_TEXT:
        raise AssertionError("Expected the exact empty public-evidence explanation.")
    if any(node.name == "a" for node in _walk_elements(section)):
        raise AssertionError("Empty evidence section contains an anchor.")
    if response.context["person"]["public_playbooks"] != ():
        raise AssertionError("Public DTO retained ineligible evidence.")
