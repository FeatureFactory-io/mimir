"""S03 real service, rendered HTTP and captured-log proofs."""

from __future__ import annotations

import logging
import re
from dataclasses import fields

import pytest
from django.db import connection
from django.http import HttpResponse
from django.test import Client
from django.test.html import Element
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from pytest import LogCaptureFixture

from methodology.models import EventChannel, KarmaAward, Playbook
from methodology.services.experts_service import ExpertProjection, ExpertsService
from tests.support.experts_data import CedarBaseline
from tests.support.experts_html import element_text, find_by_test_id
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

pytestmark = pytest.mark.django_db
SERVICE_LOGGER = "methodology.services.experts_service"
VIEW_LOGGER = "methodology.expert_views"
LIST_STORY = "ExpertsService.list_leaders"
DESIGN_PATH = "/experts/?category=design"


def test_list_leaders_with_design_uses_total_and_limits_five(
    cedar_baseline: CedarBaseline, caplog: LogCaptureFixture
) -> None:
    """Prove exact totals/subtotals/order and service happy log beats.

    :param cedar_baseline: Real Cedar data. Example: CedarBaseline({}, {}, {}).
    :param caplog: Captured service records. Example: INFO records.
    :return: None. Example: None.
    :raises AssertionError: For wrong arithmetic, order, limit or log story.
    """
    with (
        capture_experts_logs(caplog, (SERVICE_LOGGER,)),
        CaptureQueriesContext(connection) as queries,
    ):
        people = ExpertsService().list_leaders("design", correlation_id="cedar-s03")
    assert len(queries) <= 5
    assert [
        (person.username, person.total_points, dict(person.category_points)["design"])
        for person in people
    ] == [
        ("sreed", 15400, 13900),
        ("mrodriguez", 8200, 7200),
        ("pnair", 7600, 7600),
        ("dortiz", 6900, 6900),
        ("hkim", 5800, 5800),
    ]
    assert people[1].user_id == cedar_baseline.user_ids["mrodriguez"]
    assert people[1].source_points == (
        ("Released", 5000),
        ("PIP", 1600),
        ("Consumption", 1200),
        ("Learning", 400),
    )
    assert {field.name for field in fields(ExpertProjection)} == {
        "user_id",
        "username",
        "display_name",
        "total_points",
        "primary_category",
        "category_points",
        "source_points",
        "released_public_playbook_count",
        "successful_gui_copy_count",
    }
    _assert_design_query_log_story(caplog, "correlation_id=cedar-s03")


def test_list_leaders_with_development_excludes_secondary_design_contributor(
    cedar_baseline: CedarBaseline,
) -> None:
    """Prove Mike/Jordan order and exclusion of Maria.

    :param cedar_baseline: Real Cedar data. Example: CedarBaseline({}, {}, {}).
    :return: None. Example: None.
    :raises AssertionError: If secondary-category points qualify Maria.
    """
    people = ExpertsService().list_leaders("development", correlation_id="cedar-s03")
    assert [(person.username, person.total_points) for person in people] == [
        ("mchen", 12450),
        ("jlee", 6100),
    ]
    assert people[0].user_id == cedar_baseline.user_ids["mchen"]
    assert dict(people[0].category_points) == {"development": 12450}


def test_list_leaders_with_changed_award_reads_live_projection(
    cedar_baseline: CedarBaseline,
) -> None:
    """Prove a real additional award changes results without cached totals.

    :param cedar_baseline: Restored baseline. Example: CedarBaseline({}, {}, {}).
    :return: None. Example: None.
    :raises AssertionError: If projection remains stale.
    """
    service = ExpertsService()
    assert (
        service.list_leaders("design", correlation_id="cedar-before")[-1].username
        == "hkim"
    )
    KarmaAward.objects.create(
        recipient=cedar_baseline.users_by_username["tmartin"],
        category="design",
        source_kind=KarmaAward.SourceKind.MAJOR,
        event_channel=EventChannel.HISTORICAL,
        event_identity="cedar-test:theo-promotion",
        points=601,
        occurred_at=timezone.now(),
    )
    people = service.list_leaders("design", correlation_id="cedar-after")
    assert [person.username for person in people] == [
        "sreed",
        "mrodriguez",
        "pnair",
        "dortiz",
        "tmartin",
    ]
    assert people[-1].total_points == 5801


def test_list_leaders_with_nonprimary_positive_category_excludes_user(
    cedar_baseline: CedarBaseline,
) -> None:
    """Prove membership follows primary category before ranking/limiting.

    :param cedar_baseline: Real Cedar data. Example: CedarBaseline({}, {}, {}).
    :return: None. Example: None.
    :raises AssertionError: If a secondary category confers eligibility.
    """
    service = ExpertsService()
    maria = service.project_user(cedar_baseline.user_ids["mrodriguez"])
    assert maria.primary_category == "design"
    assert dict(maria.category_points) == {"design": 7200, "development": 1000}
    noras_projection = service.project_user(cedar_baseline.user_ids["nberg"])
    assert noras_projection.total_points == 0
    assert noras_projection.primary_category is None
    assert noras_projection.category_points == ()
    assert noras_projection.source_points == tuple(
        (kind, 0) for kind in ("Released", "PIP", "Consumption", "Learning")
    )
    assert noras_projection.released_public_playbook_count == 0
    assert service.list_leaders("other", correlation_id="cedar-s03") == ()


def test_list_leaders_with_invalid_category_rejects_service_input() -> None:
    """Prove unsupported service input raises a clear ValueError.

    :return: None. Example: None.
    :raises AssertionError: If invalid service input is accepted.
    """
    with pytest.raises(ValueError, match="category"):
        ExpertsService().list_leaders("unrecognized", correlation_id="cedar-reject")


def test_list_leaders_with_positive_user_without_release_remains_eligible(
    cedar_baseline: CedarBaseline,
) -> None:
    """Prove Sam's positive Research contributions qualify without a release.

    :param cedar_baseline: Real Cedar data. Example: CedarBaseline({}, {}, {}).
    :return: None. Example: None.
    :raises AssertionError: If a release requirement is invented.
    """
    people = ExpertsService().list_leaders("research", correlation_id="cedar-s03")
    assert [(person.username, person.total_points) for person in people] == [
        ("skim", 4800)
    ]
    assert people[0].user_id == cedar_baseline.user_ids["skim"]
    assert people[0].released_public_playbook_count == 0


def test_experts_list_with_design_renders_exact_order_and_boundary(
    client: Client, cedar_baseline: CedarBaseline
) -> None:
    """Prove the real HTML contains precisely the five expected Design cards.

    :param client: Real Django client. Example: Client().
    :param cedar_baseline: Real Cedar data. Example: CedarBaseline({}, {}, {}).
    :return: None. Example: None.
    :raises AssertionError: For wrong order, totals or excluded contributors.
    """
    client.force_login(cedar_baseline.users_by_username["esvensson"])
    award_count = KarmaAward.objects.count()
    response = client.get(DESIGN_PATH)
    assert response.status_code == 200
    assert _rendered_ranking(response) == [
        ("sreed", "15,400", "15400", "13900"),
        ("mrodriguez", "8,200", "8200", "7200"),
        ("pnair", "7,600", "7600", "7600"),
        ("dortiz", "6,900", "6900", "6900"),
        ("hkim", "5,800", "5800", "5800"),
    ]
    for username in ("tmartin", "mchen", "nberg"):
        assert f'experts-card-{username}"'.encode() not in response.content
    assert KarmaAward.objects.count() == award_count


def test_experts_list_with_development_renders_expected_order(
    client: Client, cedar_baseline: CedarBaseline
) -> None:
    """Follow the actual Development link and verify the rendered ranking.

    :param client: Real Django client. Example: Client().
    :param cedar_baseline: Real Cedar data. Example: CedarBaseline({}, {}, {}).
    :return: None. Example: None.
    :raises AssertionError: For incorrect link destination or card order.
    """
    client.force_login(cedar_baseline.users_by_username["esvensson"])
    design = client.get(DESIGN_PATH)
    assert design.status_code == 200
    tabs = find_by_test_id(design.content, "experts-category-tabs")
    link = find_by_test_id(str(tabs), "experts-category-development")
    assert link.name == "a"
    assert element_text(link) == "Development"
    href = dict(link.attributes)["href"]
    assert href == "/experts/?category=development"
    development = client.get(href)
    assert development.status_code == 200
    link = find_by_test_id(development.content, "experts-category-development")
    assert dict(link.attributes)["aria-current"] == "page"
    assert _rendered_ranking(development) == [
        ("mchen", "12,450", "12450", "12450"),
        ("jlee", "6,100", "6100", "6100"),
    ]
    assert b'experts-card-mrodriguez"' not in development.content


@pytest.mark.parametrize(
    "request_id",
    ["cedar-s03", None, "untrusted@example.invalid", "A" * 101],
    ids=["safe", "absent", "unsafe", "overlong"],
)
def test_experts_list_with_design_log_story_happy(
    client: Client,
    cedar_baseline: CedarBaseline,
    caplog: LogCaptureFixture,
    request_id: str | None,
) -> None:
    """Prove the complete request/query log story using assert_log_story.

    :param client: Real Django client. Example: Client().
    :param cedar_baseline: Real Cedar data. Example: CedarBaseline({}, {}, {}).
    :param caplog: Captured INFO records. Example: request "cedar-s03".
    :param request_id: Incoming header or omitted. Example: "cedar-s03".
    :return: None. Example: None.
    :raises AssertionError: For missing beats, correlation or safe context.
    """
    client.force_login(cedar_baseline.users_by_username["esvensson"])
    headers = {"X-Request-ID": request_id} if request_id is not None else {}
    with capture_experts_logs(caplog, (VIEW_LOGGER, SERVICE_LOGGER)):
        response = client.get(DESIGN_PATH, headers=headers)
    assert response.status_code == 200
    correlation_id = response.headers["X-Request-ID"]
    if request_id == "cedar-s03":
        assert correlation_id == request_id
    else:
        assert re.fullmatch(r"[a-f0-9-]{36}", correlation_id)
        assert request_id is None or request_id not in caplog.text
    correlation = f"correlation_id={correlation_id}"
    assert_log_story(
        caplog,
        where="experts_list",
        beats={
            "entry": ("| entry |", "category=design", correlation),
            "exit": ("| exit |", "status=200", "count=5", correlation),
        },
    )
    _assert_design_query_log_story(caplog, correlation)
    assert [
        (record.name, record.getMessage().split(" | ")[1])
        for record in caplog.records
        if record.name in (VIEW_LOGGER, SERVICE_LOGGER)
    ] == [
        (VIEW_LOGGER, "entry"),
        (SERVICE_LOGGER, "entry"),
        (SERVICE_LOGGER, "processing"),
        (SERVICE_LOGGER, "branch"),
        (SERVICE_LOGGER, "exit"),
        (VIEW_LOGGER, "exit"),
    ]


def _rendered_ranking(response: HttpResponse) -> list[tuple[str, str, str, str]]:
    """Read each ranked article's visible rank and actual score markup.

    :param response: Rendered leaderboard. Example: client.get(DESIGN_PATH).
    :return: Ordered identity, display total, raw total and subtotal. Example: [].
    :raises AssertionError: For missing rank or score elements.
    """
    leaderboard = find_by_test_id(response.content, "experts-leaderboard")
    cards = [
        node
        for node in leaderboard.children
        if isinstance(node, Element) and node.name == "article"
    ]
    ranking = []
    for rank, card in enumerate(cards, start=1):
        attributes = dict(card.attributes)
        card_html = str(card)
        rank_display = find_by_test_id(card_html, "expert-card-rank")
        assert element_text(rank_display) == str(rank)
        assert dict(rank_display.attributes)["aria-label"] == f"Rank {rank}"
        assert attributes["data-testid"].startswith("experts-card-")
        ranking.append(
            (
                attributes["data-testid"].removeprefix("experts-card-"),
                element_text(find_by_test_id(card_html, "expert-card-karma")),
                attributes["data-total-points"],
                attributes["data-category-points"],
            )
        )
    return ranking


def _assert_design_query_log_story(caplog: LogCaptureFixture, correlation: str) -> None:
    """Check the four query beats carry the same request correlation.

    :param caplog: Actual captured records. Example: INFO logging from list_leaders.
    :param correlation: Complete field. Example: "correlation_id=cedar-s03".
    :return: None. Example: None after all query beats match.
    :raises AssertionError: If a required fragment is missing.
    """
    assert_log_story(
        caplog,
        where=LIST_STORY,
        beats={
            "entry": ("| entry |", "category=design", "limit=5", correlation),
            "processing": ("| processing |", "scope=all_categories", correlation),
            "branch": (
                "| branch |",
                "primary_category=design",
                "eligible_count=6",
                correlation,
            ),
            "exit": (
                "| exit |",
                "returned_count=5",
                "order=total_desc_username_asc",
                correlation,
            ),
        },
    )


def test_list_leaders_with_invalid_category_log_story_reject(
    caplog: LogCaptureFixture,
) -> None:
    """Prove explicit rejected-input logging with no sensitive data.

    :param caplog: Captured records. Example: validation rejection.
    :return: None. Example: None.
    :raises AssertionError: For missing validation beat or sensitive leakage.
    """
    logger = logging.getLogger(SERVICE_LOGGER)
    before = (logger.disabled, logger.level, logger.propagate)
    with (
        capture_experts_logs(caplog, (SERVICE_LOGGER,)),
        CaptureQueriesContext(connection) as queries,
        pytest.raises(ValueError),
    ):
        ExpertsService().list_leaders(
            "private-example@example.com", correlation_id="cedar-reject"
        )
    assert (logger.disabled, logger.level, logger.propagate) == before
    assert len(queries) == 0
    assert_log_story(
        caplog,
        where=LIST_STORY,
        beats={
            "validation": (
                "| validation |",
                "rejected=invalid_category",
                "correlation_id=cedar-reject",
            ),
        },
    )
    assert "private-example@example.com" not in caplog.text


def test_list_leaders_with_tied_category_counts_includes_private_releases(
    cedar_baseline: CedarBaseline,
) -> None:
    """Use private current releases for category ties without exposing their count."""
    mike = cedar_baseline.users_by_username["mchen"]
    KarmaAward.objects.create(
        recipient=mike,
        category="design",
        source_kind=KarmaAward.SourceKind.MAJOR,
        event_channel=EventChannel.HISTORICAL,
        event_identity="cedar-test:mike-category-tie",
        points=12450,
        occurred_at=timezone.now(),
    )
    service = ExpertsService()
    assert service.project_user(mike.pk).primary_category == "development"
    for index in range(3):
        Playbook.objects.create(
            author=mike,
            name=f"Private Design {index}",
            category="design",
            visibility="private",
            status="released",
            version=1,
        )
    projection = service.project_user(mike.pk)
    assert projection.primary_category == "design"
    assert projection.released_public_playbook_count == 2
    assert service.list_leaders("design", correlation_id="cedar-tied")[0] == projection


@pytest.mark.parametrize("user_id", [0, True, 123456789])
def test_project_user_with_invalid_account_raises_value_error(user_id: int) -> None:
    """Reject an invalid or missing user identity."""
    with pytest.raises(ValueError, match="account"):
        ExpertsService().project_user(user_id)
