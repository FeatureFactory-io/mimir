"""Import the declared Cedar category ties as historical runner-owned data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, TypedDict, cast

from django.contrib.auth.models import User
from django.db import transaction

from methodology.models import EventChannel, KarmaAward, Playbook, PlaybookVersion
from methodology.models.karma_award import first_release_identity
from methodology.models.playbook_version import VersionSource
from tests.support.experts_data import (
    CEDAR_BASELINE_TIME_ISO,
    CedarDataset,
    load_cedar_baseline,
)

TieVariant = Literal["TIE01", "TIE02"]
_TIE_VARIANTS = ("TIE01", "TIE02")
_CATEGORY_SLUG_BY_LABEL = {label: slug for slug, label in Playbook.CATEGORY_CHOICES}
_INITIAL_RELEASE = Decimal("1.0")
_HISTORICAL_RELEASE_POINTS = 5_000
# Insert Development first so the alphabetical result cannot depend on insert order.
_TIED_CATEGORIES = ("development", "design")


class _TieRecord(TypedDict):
    """The inputs read from either declared category variant."""

    id: str
    username: str
    name: str
    released_playbooks: dict[str, int]


@dataclass(frozen=True)
class CategoryTieDataset:
    """Baseline and actual database identities for an additional tie case."""

    baseline: CedarDataset
    variant: TieVariant
    user: User
    playbook_ids: tuple[int, ...]


def load_category_tie(variant: str) -> CategoryTieDataset:
    """Extend a real Cedar baseline with one isolated historical variant.

    :param variant: TIE01 or TIE02. Example: "TIE01".
    :return: Real ORM references. Example: arao plus one Development release.
    :raises ValueError: For an unknown variant, before any database interaction,
        or when the shared Cedar importer rejects the effective database.
    """
    if variant not in _TIE_VARIANTS:
        raise ValueError("Unknown Cedar tie variant. Choose TIE01 or TIE02.")
    tie_variant = cast(TieVariant, variant)
    with transaction.atomic():
        baseline = load_cedar_baseline()
        records = cast("list[_TieRecord]", baseline.oracle["tie_variants"])
        record = next(row for row in records if row["id"] == tie_variant)
        first_name, _, last_name = record["name"].partition(" ")
        username = record["username"]
        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=f"{username}@example.com",
        )
        books = tuple(
            _create_tie_playbook(user, _CATEGORY_SLUG_BY_LABEL[label], ordinal)
            for label, count in record["released_playbooks"].items()
            for ordinal in range(1, count + 1)
        )
        _create_tie_awards(user, tie_variant)
    return CategoryTieDataset(
        baseline, tie_variant, user, tuple(book.pk for book in books)
    )


def _create_tie_playbook(user: User, category: str, ordinal: int) -> Playbook:
    """Store a released playbook and its initial version as imported history.

    :param user: Persisted variant author. Example: the arao account.
    :param category: Canonical category. Example: "development".
    :param ordinal: Positive sequence within the category. Example: 1.
    :return: Released ORM playbook and initial history. Example: a v1.0 release.
    :raises ValueError: For an invalid user, category or ordinal.
    """
    if not user.pk or user._state.adding:
        raise ValueError("Tie playbooks require a persisted author.")
    if category not in _CATEGORY_SLUG_BY_LABEL.values():
        raise ValueError("Tie playbooks require a canonical category.")
    if type(ordinal) is not int or ordinal <= 0:
        raise ValueError("Tie playbook ordinal must be a positive integer.")

    # These records were already released at the ledger snapshot. A live
    # release would record new Karma and invalidate the declared tie.
    book = Playbook.objects.create(
        author=user,
        name=f"Cedar tie {category} {ordinal}",
        category=category,
        status="released",
        visibility="public",
        version=_INITIAL_RELEASE,
    )
    PlaybookVersion.objects.create(
        playbook=book,
        version_number=_INITIAL_RELEASE,
        source=VersionSource.RELEASE,
        created_by=user,
        is_major=True,
        snapshot_data={
            "name": book.name,
            "category": category,
            "version": str(_INITIAL_RELEASE),
        },
    )
    return book


def _create_tie_awards(user: User, variant: TieVariant) -> None:
    """Import two immutable historical category awards without a live event.

    :param user: Persisted recipient. Example: the bquinn account.
    :param variant: Identity namespace. Example: "TIE02".
    :return: None. Example: two new 5,000-point category snapshots.
    :raises ValueError: For a missing recipient or unknown variant.
    """
    if not user.pk or user._state.adding or variant not in _TIE_VARIANTS:
        raise ValueError("Tie awards require a saved recipient and known variant.")
    released = dict(
        Playbook.objects.filter(author=user, status="released").values_list(
            "category", "pk"
        )
    )
    for category in _TIED_CATEGORIES:
        playbook_id = released.get(category)
        KarmaAward.objects.create(
            recipient=user,
            category=category,
            points=_HISTORICAL_RELEASE_POINTS,
            source_kind=KarmaAward.SourceKind.RELEASE,
            event_channel=EventChannel.HISTORICAL,
            event_identity=(
                first_release_identity(playbook_id)
                if playbook_id is not None
                else f"cedar-tie:{variant}:unknown-release:{category}"
            ),
            playbook_id_snapshot=playbook_id,
            occurred_at=datetime.fromisoformat(CEDAR_BASELINE_TIME_ISO),
        )
