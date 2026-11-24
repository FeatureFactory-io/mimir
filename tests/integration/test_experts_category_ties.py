"""Real ledger, playbook and HTTP proofs for category tie resolution."""

from __future__ import annotations

import logging
from collections import Counter
from decimal import Decimal

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from pytest import LogCaptureFixture

from methodology.models import EventChannel, KarmaAward, Playbook, PlaybookVersion
from methodology.models.karma_award import first_release_identity
from methodology.models.playbook_version import VersionSource
from methodology.services.experts_service import (
    ExpertsService,
    resolve_primary_category,
)
from tests.support.experts_category_ties import CategoryTieDataset, load_category_tie
from tests.support.experts_data import CedarDataset
from tests.support.experts_html import element_text, find_by_test_id
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

pytestmark = pytest.mark.django_db

TIED_POINTS = {"design": 5_000, "development": 5_000}
TIED_TOTAL = 10_000
TIED_COUNTS = {"design": 1, "development": 1}
SERVICE_LOGGER = "methodology.services.experts_service"
CATEGORY_STORY = "resolve_primary_category"
LEGACY_CATEGORY = "legacy-unclassified"


@pytest.mark.parametrize(
    "variant,expected", [("TIE01", "development"), ("TIE02", "design")]
)
def test_primary_category_with_cedar_tie_expected_category(
    variant: str, expected: str, cedar_baseline: CedarDataset, client: Client
) -> None:
    """Prove the Cedar oracle, real query and rendered category agree.

    :param variant: Isolated ORM variant. Example: "TIE01".
    :param expected: Required category slug. Example: "development".
    :param cedar_baseline: Imported shared history. Example: the Cedar RFP baseline.
    :param client: Real anonymous HTTP client. Example: Client().
    :return: None. Example: None.
    :raises AssertionError: For incorrect ranking, counts or mutated awards.
    """
    baseline_ledger = _ledger()
    tie = load_category_tie(variant)
    before = _ledger()
    assert _ledger(excluding_recipient=tie.user.pk) == baseline_ledger
    assert tie.baseline.user_ids == cedar_baseline.user_ids
    assert tie.baseline.playbook_ids == cedar_baseline.playbook_ids
    _assert_cedar_tie(tie, expected)

    projection = ExpertsService().project_user(tie.user.pk)
    assert projection.primary_category == expected
    assert projection.total_points == TIED_TOTAL
    assert dict(projection.category_points) == TIED_POINTS
    _assert_leaderboard_placement(client, tie, expected)
    assert _ledger() == before


@pytest.mark.parametrize(
    "case,variant,expected,public_count",
    [
        ("points_first", "TIE01", "design", 1),
        ("private_released_counts", "TIE02", "development", 2),
        ("nonreleased_excluded", "TIE02", "design", 2),
        ("other_author_excluded", "TIE02", "design", 2),
        ("versions_count_once", "TIE02", "design", 2),
        ("nontied_count_excluded", "TIE02", "design", 4),
        ("alphabetical_insertion_independent", "TIE02", "design", 2),
        ("historical_category_preserved", "TIE02", "development", 2),
    ],
)
def test_primary_category_with_policy_boundaries_expected_category(
    case: str, variant: str, expected: str, public_count: int
) -> None:
    """Exercise a category policy boundary through the real database.

    :param case: Named boundary. Example: "versions_count_once".
    :param variant: Historical starting point. Example: "TIE02".
    :param expected: Required winner. Example: "design".
    :param public_count: Independent fallback count. Example: 2.
    :return: None. Example: None.
    :raises AssertionError: For incorrect ranking, count or ledger mutation.
    """
    tie = load_category_tie(variant)
    original = _ledger()
    _apply_boundary(case, tie)
    before_projection = _ledger()
    if case == "historical_category_preserved":
        assert before_projection == original

    projection = ExpertsService().project_user(tie.user.pk)
    assert projection.primary_category == expected
    assert projection.released_public_playbook_count == public_count
    persisted_points: Counter[str] = Counter()
    for category, points in _award_points(tie):
        persisted_points[category] += points
    assert dict(projection.category_points) == persisted_points
    assert projection.total_points == persisted_points.total()
    if case == "historical_category_preserved":
        assert dict(projection.category_points) == TIED_POINTS
    if case == "alphabetical_insertion_independent":
        award_points = _award_points(tie)
        assert [category for category, _points in award_points] == [
            "development",
            "design",
        ]
        for ordered_points in (award_points, tuple(reversed(award_points))):
            assert (
                resolve_primary_category(dict(ordered_points), TIED_COUNTS) == expected
            )
    assert _ledger() == before_projection


def test_primary_category_with_legacy_released_category_preserves_public_count() -> (
    None
):
    """Prove legacy stored categories survive read paths with strict resolver inputs.

    :return: None. Example: None.
    :raises AssertionError: For a broken projection or accepted invalid input.
    """
    tie = load_category_tie("TIE02")
    Playbook.objects.create(
        author=tie.user,
        name="Legacy public release",
        category=LEGACY_CATEGORY,
        status="released",
        visibility="public",
        version=Decimal("1.0"),
    )
    projection = ExpertsService().project_user(tie.user.pk)
    assert projection.primary_category == "design"
    assert projection.released_public_playbook_count == 3
    with pytest.raises(ValueError, match="category"):
        resolve_primary_category(TIED_POINTS, {**TIED_COUNTS, LEGACY_CATEGORY: 1})


def test_primary_category_with_zero_karma_excludes_nora(
    cedar_baseline: CedarDataset, client: Client
) -> None:
    """Keep a real zero-award account ineligible on the public surface.

    :param cedar_baseline: Imported baseline. Example: Nora's Cedar account.
    :param client: Real anonymous HTTP client. Example: Client().
    :return: None. Example: None.
    :raises AssertionError: If a zero-score account gets a public projection.
    """
    nora = cedar_baseline.users_by_username["nberg"]
    service = ExpertsService()
    projection = service.project_user(nora.pk)
    assert projection.total_points == 0
    assert projection.primary_category is None
    assert projection.category_points == ()
    for category, _label in Playbook.CATEGORY_CHOICES:
        assert nora.pk not in {
            person.user_id
            for person in service.list_leaders(
                category, correlation_id="cedar-s47-zero"
            )
        }
    nora_response = client.get(reverse("expert_detail", args=[nora.username]))
    missing_response = client.get(reverse("expert_detail", args=["no-such-cedar-user"]))
    assert nora_response.status_code == missing_response.status_code == 404
    assert nora_response.content == missing_response.content


def test_category_tie_loader_with_unknown_variant_rejects(
    cedar_baseline: CedarDataset,
) -> None:
    """Reject an unknown variant before querying or changing shared data.

    :param cedar_baseline: Imported history. Example: the canonical Cedar baseline.
    :return: None. Example: None.
    :raises AssertionError: For a missing ValueError or any database work.
    """
    before = _ledger()
    with (
        CaptureQueriesContext(connection) as queries,
        pytest.raises(ValueError, match="Unknown Cedar tie variant"),
    ):
        load_category_tie("TIE99")
    assert not queries.captured_queries
    assert _ledger() == before
    assert Playbook.objects.filter(
        pk__in=cedar_baseline.playbook_ids.values()
    ).count() == len(cedar_baseline.playbook_ids)


@pytest.mark.parametrize(
    "variant,expected,reason",
    [
        ("TIE01", "development", "released_count"),
        ("TIE02", "design", "alphabetical"),
    ],
)
def test_primary_category_with_cedar_ties_log_story_happy(
    caplog: LogCaptureFixture, variant: str, expected: str, reason: str
) -> None:
    """Observe the production log story for the actual category resolution.

    :param caplog: Capture for the real service logger. Example: INFO records.
    :param variant: Isolated history. Example: "TIE01".
    :param expected: Resolved category. Example: "development".
    :param reason: Governing decision. Example: "released_count".
    :return: None. Example: None.
    :raises AssertionError: For missing, unordered or sensitive log content.
    """
    tie = load_category_tie(variant)
    correlation_id = f"cedar-s47-{variant}"
    with capture_experts_logs(caplog, (SERVICE_LOGGER,)):
        people = ExpertsService().list_leaders(expected, correlation_id=correlation_id)
    assert tie.user.pk in {person.user_id for person in people}

    context = (f"account_id={tie.user.pk}", f"correlation_id={correlation_id}")
    total = f"total={TIED_TOTAL}"
    category = f"category={expected}"
    beats = {
        "entry": ("| entry |", *context),
        "processing": ("| processing |", total, "tied_candidates=2", *context),
        "branch": ("| branch |", f"reason={reason}", category, *context),
        "exit": ("| exit |", total, category, *context),
    }
    assert_log_story(caplog, where=CATEGORY_STORY, beats=beats)
    records = [
        record
        for record in caplog.records
        if record.name == SERVICE_LOGGER
        and record.getMessage().startswith(f"{CATEGORY_STORY} | ")
        and set(context).issubset(record.getMessage().split())
    ]
    assert len(records) == len(beats)
    for record, (beat, fragments) in zip(records, beats.items(), strict=True):
        _where, actual_beat, fields = record.getMessage().split(" | ", 2)
        assert (record.levelno, actual_beat) == (logging.INFO, beat)
        assert set(fragments[1:]).issubset(fields.split())
    assert "@" not in caplog.text
    assert "Cedar Bid Pricing" not in caplog.text
    for title in Playbook.objects.filter(pk__in=tie.playbook_ids).values_list(
        "name", flat=True
    ):
        assert title not in caplog.text
    assert "DEMO_ONLY_NOT_A_REAL_TOKEN" not in caplog.text


def _ledger(
    *, excluding_recipient: int | None = None
) -> tuple[tuple[object, ...], ...]:
    """Take a complete ledger snapshot in primary-key order."""
    awards = KarmaAward.objects.order_by("pk")
    if excluding_recipient is not None:
        awards = awards.exclude(recipient_id=excluding_recipient)
    return tuple(awards.values_list())


def _award_points(tie: CategoryTieDataset) -> tuple[tuple[str, int], ...]:
    """Read the variant's persisted category and point pairs in insert order."""
    return tuple(
        KarmaAward.objects.filter(recipient=tie.user)
        .order_by("pk")
        .values_list("category", "points")
    )


def _assert_cedar_tie(tie: CategoryTieDataset, expected: str) -> None:
    """Compare real records with the independent Cedar JSON oracle."""
    records = tie.baseline.oracle["tie_variants"]
    assert isinstance(records, list)
    record = next(record for record in records if record["id"] == tie.variant)
    assert record["expected_primary_category"].lower() == expected
    assert (tie.user.username, tie.user.get_full_name()) == (
        record["username"],
        record["name"],
    )
    assert len(_award_points(tie)) == len(TIED_POINTS)
    assert (
        dict(_award_points(tie))
        == {
            label.lower(): points for label, points in record["category_points"].items()
        }
        == TIED_POINTS
    )

    released = Playbook.objects.filter(author=tie.user, status="released")
    released_ids = set(released.values_list("pk", flat=True))
    counts = Counter(released.values_list("category", flat=True))
    assert released_ids == set(tie.playbook_ids)
    assert counts == Counter(
        {label.lower(): count for label, count in record["released_playbooks"].items()}
    )
    assert PlaybookVersion.objects.filter(playbook_id__in=released_ids).count() == len(
        released_ids
    )
    assert _historical_release_ids(tie) == dict(released.values_list("category", "pk"))


def _historical_release_ids(tie: CategoryTieDataset) -> dict[str, int]:
    """Read known first-release anchors from the fixture ledger."""
    release_ids = {}
    for award in KarmaAward.objects.filter(recipient=tie.user):
        assert award.event_channel == EventChannel.HISTORICAL
        assert award.source_kind == KarmaAward.SourceKind.RELEASE
        if award.playbook_id_snapshot is not None:
            assert award.event_identity == first_release_identity(
                award.playbook_id_snapshot
            )
            release_ids[award.category] = award.playbook_id_snapshot
    return release_ids


def _assert_leaderboard_placement(
    client: Client, tie: CategoryTieDataset, expected: str
) -> None:
    """Check the same person appears only in the winning production tab."""
    list_url = reverse("experts_list")
    card_id = f"experts-card-{tie.user.username}"
    for selected in TIED_POINTS:
        response = client.get(list_url, {"category": selected})
        assert response.status_code == 200
        if selected == expected:
            card = find_by_test_id(response.content, card_id)
            assert dict(card.attributes)["data-category-points"] == "5000"
            assert expected.title() in element_text(card)
            assert (
                element_text(find_by_test_id(str(card), "expert-card-karma"))
                == "10,000"
            )
        else:
            assert f'data-testid="{card_id}"'.encode() not in response.content


def _apply_boundary(case: str, tie: CategoryTieDataset) -> None:
    """Arrange a policy perturbation without running live publication hooks."""
    if case in {"points_first", "nontied_count_excluded"}:
        extra_category = "design" if case == "points_first" else "product"
        KarmaAward.objects.create(
            recipient=tie.user,
            category=extra_category,
            points=5,
            source_kind=KarmaAward.SourceKind.LEARNING,
            event_channel=EventChannel.HISTORICAL,
            event_identity=f"cedar-tie-boundary:{case}",
            occurred_at=timezone.now(),
        )
    match case:
        case "private_released_counts":
            _add_book(tie.user.pk, "development", "released", "private")
        case "nonreleased_excluded":
            for status in ("draft", "active", "disabled"):
                _add_book(tie.user.pk, "development", status)
        case "other_author_excluded":
            _add_book(tie.baseline.user_ids["nberg"], "development", "released")
        case "nontied_count_excluded":
            _add_book(tie.user.pk, "product", "released")
            _add_book(tie.user.pk, "product", "released", suffix="second")
        case "versions_count_once":
            book = Playbook.objects.get(pk__in=tie.playbook_ids, category="development")
            _append_release_history(book)
        case "historical_category_preserved":
            Playbook.objects.filter(pk__in=tie.playbook_ids, category="design").update(
                category="development"
            )
        case "points_first" | "alphabetical_insertion_independent":
            pass
        case _:
            raise ValueError(f"Unknown S47 policy boundary: {case}")


def _add_book(
    author_id: int,
    category: str,
    status: str,
    visibility: str = "public",
    *,
    suffix: str = "",
) -> None:
    """Insert the current playbook state needed to distinguish a counting rule."""
    Playbook.objects.create(
        author_id=author_id,
        category=category,
        status=status,
        visibility=visibility,
        name=f"Tie boundary {category} {status} {visibility} {suffix}".strip(),
        version=Decimal("0.1" if status == "draft" else "1.0"),
    )


def _append_release_history(book: Playbook) -> None:
    """Give an existing released playbook a second real version."""
    book.version = Decimal("2.0")
    book.save(update_fields=["version"])
    PlaybookVersion.objects.create(
        playbook=book,
        version_number=book.version,
        source=VersionSource.ADMIN,
        created_by=book.author,
        is_major=True,
        snapshot_data={"version": "2.0"},
    )
