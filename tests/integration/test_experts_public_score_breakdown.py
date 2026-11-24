"""S18 production score reconciliation proofs."""

from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus

import pytest
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.db import connection
from django.http import HttpResponse
from django.test import Client
from django.test.html import Element
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.authtoken.models import Token

from methodology.models import (
    AgentInteraction,
    ExpertProfile,
    KarmaAward,
    Playbook,
    ProcessImprovementProposal,
)
from methodology.models.karma_award import EventChannel
from methodology.services.expert_text import format_karma
from tests.support.experts_data import CedarDataset
from tests.support.experts_html import (
    _walk_elements,
    assert_karma_source_rows,
    element_text,
    find_by_test_id,
)
from tests.support.experts_privacy import (
    _assert_private_markers_absent,
    assert_private_rows_exist,
    assert_public_projection,
    load_privacy_case,
)

pytestmark = pytest.mark.django_db

_MARIA = "mrodriguez"
_SOURCES = {
    "Released playbooks": 5000,
    "PIP contributions": 1600,
    "Consumption": 1200,
    "Learning": 400,
}
_CATEGORIES = {"Design": 7200, "Development": 1000}
_TOTAL = 8200
_ADDITIONAL_PIP_POINTS = 100
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


def test_public_score_breakdown_with_cedar_sources_reconciles(
    client: Client, mailoutbox: list[EmailMessage]
) -> None:
    """Prove the baseline source breakdown through a real production GET.

    :param client: Real Django client. Example: Client().
    :param mailoutbox: Local mail capture. Example: an empty list.
    :return: None. Example: None after 5000+1600+1200+400=8200.
    :raises AssertionError: If status, exact source rows or total differs.
    """
    dataset = load_privacy_case()
    response = _read_unchanged(client, dataset, mailoutbox)
    _assert_sources(response, _SOURCES, _TOTAL)


def test_public_score_breakdown_with_category_subtotals_keeps_separate_sections(
    client: Client, mailoutbox: list[EmailMessage]
) -> None:
    """Prove independent source and category dimensions in rendered HTML.

    :param client: Real Django client. Example: Client().
    :param mailoutbox: Local mail capture. Example: an empty list.
    :return: None. Example: None for Design=7200, Development=1000.
    :raises AssertionError: If categories enter source tbody or sums differ.
    """
    dataset = load_privacy_case()
    response = _read_unchanged(client, dataset, mailoutbox)
    _assert_sources(response, _SOURCES, _TOTAL)
    _assert_categories(response, _CATEGORIES, _TOTAL)


def test_public_score_breakdown_with_new_ledger_event_reads_live_totals(
    client: Client, mailoutbox: list[EmailMessage]
) -> None:
    """Prove fresh ledger data changes numbers without changing stored prose.

    :param client: Real Django client. Example: Client().
    :param mailoutbox: Local mail capture. Example: an empty list.
    :return: None. Example: None for PIP=1700 and total=8300.
    :raises AssertionError: If the second GET uses stale or fixture totals.
    """
    dataset = load_privacy_case()
    baseline = _read_unchanged(client, dataset, mailoutbox)
    _assert_sources(baseline, _SOURCES, _TOTAL)
    _assert_categories(baseline, _CATEGORIES, _TOTAL)
    profiles_before = tuple(ExpertProfile.objects.order_by("pk").values())
    KarmaAward.objects.create(
        recipient=dataset.users_by_username[_MARIA],
        event_identity="s18:live-public-source",
        source_kind=KarmaAward.SourceKind.MINOR,
        event_channel=EventChannel.HISTORICAL,
        points=_ADDITIONAL_PIP_POINTS,
        category="development",
        occurred_at=timezone.now(),
    )
    response = _read_unchanged(client, dataset, mailoutbox)
    _assert_sources(response, {**_SOURCES, "PIP contributions": 1700}, 8300)
    _assert_categories(response, {**_CATEGORIES, "Development": 1100}, 8300)
    assert tuple(ExpertProfile.objects.order_by("pk").values()) == profiles_before
    assert (
        response.context["person"]["summary"] == baseline.context["person"]["summary"]
    )


def test_public_score_breakdown_with_repeated_get_preserves_domain_state(
    client: Client, mailoutbox: list[EmailMessage]
) -> None:
    """Prove public detail reads do not award or refresh summaries.

    :param client: Real Django client. Example: Client().
    :param mailoutbox: Local mail capture. Example: an empty list.
    :return: None. Example: None when ledger/profile snapshots remain equal.
    :raises AssertionError: If authenticated or guest GET changes domain rows.
    """
    dataset = load_privacy_case()
    client.force_login(dataset.users_by_username["esvensson"])
    for authenticated in (True, False):
        if not authenticated:
            client.logout()
        for _ in range(2):
            response = _read_unchanged(client, dataset, mailoutbox)
            assert response.wsgi_request.user.is_authenticated is authenticated
            _assert_sources(response, _SOURCES, _TOTAL)
            _assert_categories(response, _CATEGORIES, _TOTAL)


def _snapshot() -> tuple[tuple[dict[str, object], ...], ...]:
    """Copy every concrete field of the guarded domain models.

    :return: Ordered row groups. Example: the complete unchanged award ledger.
    :raises RuntimeError: If a real database query fails.
    """
    return tuple(
        tuple(model.objects.order_by("pk").values()) for model in _READ_ONLY_MODELS
    )


def _read_unchanged(
    client: Client, dataset: CedarDataset, mailoutbox: list[EmailMessage]
) -> HttpResponse:
    """GET the actual public profile without changing any guarded records.

    :param client: Prepared real client. Example: an authenticated Elena session.
    :param dataset: Persisted Cedar records. Example: Maria and her private PIP.
    :param mailoutbox: Local mail capture. Example: an empty list.
    :return: Actual successful response. Example: Maria's HTTP200 public detail.
    :raises AssertionError: For a private leak, domain write or unexpected status.
    """
    assert_private_rows_exist(dataset)
    before, mail_before = _snapshot(), tuple(mailoutbox)
    with CaptureQueriesContext(connection) as queries:
        response = client.get(f"/experts/{_MARIA}/")
    assert response.status_code == HTTPStatus.OK and "Location" not in response
    authenticated = response.wsgi_request.user.is_authenticated
    if _snapshot() != before or tuple(mailoutbox) != mail_before:
        raise AssertionError("Public profile GET changed persisted records or mail.")
    # The existing shell refreshes only an already authenticated session on GET.
    if any(
        query["sql"].lstrip().upper().startswith(_WRITE_PREFIXES)
        and not (
            authenticated
            and query["sql"].lstrip().upper().startswith(_SESSION_REFRESH_PREFIX)
        )
        for query in queries
    ):
        raise AssertionError(
            "Public profile GET executed an unexpected database write."
        )
    assert_public_projection(response.context["person"], dataset)
    _assert_private_markers_absent(
        response.content.decode(response.charset), dataset, allow_contact=authenticated
    )
    return response


def _assert_sources(
    response: HttpResponse, expected: Mapping[str, int], total: int
) -> None:
    """Reconcile the actual source table with the exact public DTO values.

    :param response: Production GET response. Example: Maria's public detail.
    :param expected: Independent expected source totals. Example: Learning=400.
    :param total: Expected total. Example: 8200.
    :return: None after both surfaces match all four source values.
    :raises AssertionError: If the HTML or designated DTO differs.
    """
    assert_karma_source_rows(
        response.content.decode(response.charset), expected, "expert-karma-total", total
    )
    person = response.context["person"]
    assert person["total_karma"] == total
    assert person["formatted_karma"] == format_karma(total)
    assert person["source_rows"] == tuple(
        {"label": label, "points": format_karma(points)}
        for label, points in expected.items()
    )


def _assert_categories(
    response: HttpResponse, expected: Mapping[str, int], total: int
) -> None:
    """Keep the reconciled category dimension outside the source table body.

    :param response: Production GET response. Example: Maria's public detail.
    :param expected: Independent category totals. Example: Design=7200.
    :param total: Expected total. Example: 8200.
    :return: None after category markup and the public DTO reconcile separately.
    :raises AssertionError: For a wrong subtotal or mixed source/category section.
    """
    assert sum(expected.values()) == total
    section = find_by_test_id(response.content, "karma-category-breakdown")
    assert section.name == "dl"
    actual = [(node.name, element_text(node)) for node in _walk_elements(section)]
    assert actual[1:] == [
        item
        for label, points in expected.items()
        for item in (("dt", label), ("dd", format_karma(points)))
    ]
    source_table = find_by_test_id(response.content, "karma-source-breakdown")
    body = next(
        child
        for child in source_table.children
        if isinstance(child, Element) and child.name == "tbody"
    )
    assert all(label not in element_text(body) for label in expected)
    assert response.context["person"]["category_rows"] == tuple(
        {"label": label, "points": format_karma(points)}
        for label, points in expected.items()
    )
