"""Read-only ledger projections shared by Experts and contribution displays."""

from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypedDict

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db.models import Count, Sum

from methodology.models import EventChannel, KarmaAward, Playbook
from methodology.services.expert_text import category_label

logger = logging.getLogger(__name__)
LEADERBOARD_LIMIT = 5
SOURCE_BUCKETS = ("Released", "PIP", "Consumption", "Learning")
SOURCE_BUCKET_BY_KIND = {
    KarmaAward.SourceKind.RELEASE: "Released",
    KarmaAward.SourceKind.MAJOR: "PIP",
    KarmaAward.SourceKind.MINOR: "PIP",
    KarmaAward.SourceKind.CONSUMPTION: "Consumption",
    KarmaAward.SourceKind.LEARNING: "Learning",
}
_CORRELATION_ID = re.compile(r"[A-Za-z0-9._:-]{1,100}")
_LIST_LOG = "ExpertsService.list_leaders"


@dataclass(frozen=True)
class ExpertProjection:
    """Allowlisted public identity and live numeric contribution projection."""

    user_id: int
    username: str
    display_name: str
    total_points: int
    primary_category: str | None
    category_points: tuple[tuple[str, int], ...]
    source_points: tuple[tuple[str, int], ...]
    released_public_playbook_count: int
    successful_gui_copy_count: int


@dataclass(frozen=True)
class AwardTotals:
    """All-category persisted award aggregates for one recipient."""

    total_points: int
    category_points: tuple[tuple[str, int], ...]
    source_points: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class LiveContributionCounts:
    """Current public released-book count and explicit GUI author-copy count."""

    released_public_playbook_count: int
    successful_gui_copy_count: int


def resolve_primary_category(
    category_points: Mapping[str, int], released_counts: Mapping[str, int]
) -> str | None:
    """Choose category points, released-book count, then alphabetical label.

    :param category_points: All category totals. Example: {"design": 7200}.
    :param released_counts: Current released distinct books, private included.
        Example: {"design": 1}.
    :return: Canonical winning slug, or None for zero points. Example: "design".
    :raises ValueError: For unknown keys, negative values or noninteger amounts.
    """
    _validate_category_totals(category_points)
    _validate_category_totals(released_counts)
    positive = (slug for slug, points in category_points.items() if points > 0)
    return min(
        positive,
        key=lambda slug: (
            -category_points[slug],
            -released_counts.get(slug, 0),
            category_label(slug),
        ),
        default=None,
    )


def _validate_category_totals(values: Mapping[str, int]) -> None:
    """Validate recognized category keys and nonnegative integral values.

    :param values: Points or released-book counts. Example: {"design": 1}.
    :return: None. Example: None.
    :raises ValueError: For invalid categories, booleans or negative values.
    """
    if not isinstance(values, Mapping):
        raise ValueError("Category totals must be a mapping.")  # noqa: TRY004
    for slug, amount in values.items():
        category_label(slug)
        if type(amount) is not int or amount < 0:
            raise ValueError("Category amounts must be nonnegative integers.")


class ExpertsService:
    """Read real ORM state without awarding points or invoking a model."""

    def list_leaders(
        self, category: str, *, correlation_id: str
    ) -> tuple[ExpertProjection, ...]:
        """Return five positive primary-category contributors in total order.

        :param category: Canonical selected category. Example: "design".
        :param correlation_id: Safe request identity. Example: "cedar-s03".
        :return: Total-descending, username-ascending snapshots. Example: ().
        :raises ValueError: For invalid category or blank correlation identity.
        """
        self._validate_query(category, correlation_id)
        request_tag = f"correlation_id={correlation_id}"
        logger.info(
            f"{_LIST_LOG} | entry | category={category} limit={LEADERBOARD_LIMIT} {request_tag}"
        )
        totals = self._load_award_totals()
        logger.info(
            f"{_LIST_LOG} | processing | scope=all_categories recipients={len(totals)} {request_tag}"
        )
        user_ids = tuple(totals)
        people = self._project_candidates(
            totals,
            self._load_released_counts(user_ids),
            self._load_identities(user_ids),
            self._load_live_counts(user_ids),
        )
        eligible_count = sum(person.primary_category == category for person in people)
        logger.info(
            f"{_LIST_LOG} | branch | primary_category={category} eligible_count={eligible_count} {request_tag}"
        )
        result = self._select_leaders(people, category)
        logger.info(
            f"{_LIST_LOG} | exit | returned_count={len(result)} order=total_desc_username_asc {request_tag}"
        )
        return result

    def project_user(self, user_id: int) -> ExpertProjection:
        """Project an existing account, including a zero-contribution account.

        :param user_id: Existing positive account PK. Example: 42.
        :return: Numeric/public identity snapshot. Example: a zero Nora projection.
        :raises ValueError: For invalid or nonexistent account identifiers.
        """
        if type(user_id) is not int or user_id <= 0:
            raise ValueError("Expert account ID must be a positive integer.")
        logger.info("ExpertsService.project_user | entry | account_id=%s", user_id)
        user_ids = (user_id,)
        identities = self._load_identities(user_ids)
        if user_id not in identities:
            logger.info(
                "ExpertsService.project_user | validation | rejected=missing_account account_id=%s",
                user_id,
            )
            raise ValueError("Expert account does not exist.")
        totals = self._load_award_totals(user_ids)
        counts = self._load_live_counts(user_ids)
        people = self._project_candidates(
            totals,
            self._load_released_counts(user_ids),
            identities,
            counts,
        )
        projection = (
            people[0]
            if people
            else self._zero_projection(user_id, identities[user_id], counts[user_id])
        )
        logger.info(
            "ExpertsService.project_user | exit | account_id=%s total=%s",
            user_id,
            projection.total_points,
        )
        return projection

    def _validate_query(self, category: str, correlation_id: str) -> None:
        """Validate explicit service inputs before queries.

        :param category: Canonical category slug. Example: "design".
        :param correlation_id: Request identity. Example: "cedar-s03".
        :return: None. Example: None.
        :raises ValueError: For invalid inputs.
        """
        if not isinstance(correlation_id, str) or not _CORRELATION_ID.fullmatch(
            correlation_id
        ):
            logger.info("%s | validation | rejected=invalid_correlation_id", _LIST_LOG)
            raise ValueError("A safe request correlation ID is required.")
        try:
            category_label(category)
        except ValueError:
            logger.info(
                "%s | validation | rejected=invalid_category correlation_id=%s",
                _LIST_LOG,
                correlation_id,
            )
            raise

    def _load_award_totals(
        self, user_ids: Sequence[int] | None = None
    ) -> dict[int, AwardTotals]:
        """Aggregate all category/source awards, merging major/minor into PIP.

        :param user_ids: Optional recipient restriction. Example: (42,).
        :return: Per-recipient immutable aggregates. Example: {}.
        :raises ValueError: For invalid recipient identifiers.
        """
        queryset = KarmaAward.objects.all()
        if user_ids is not None:
            if any(type(user_id) is not int or user_id <= 0 for user_id in user_ids):
                raise ValueError("Recipient IDs must be positive integers.")
            queryset = queryset.filter(recipient_id__in=user_ids)
        rows = (
            queryset.order_by()
            .values_list("recipient_id", "category", "source_kind")
            .annotate(amount=Sum("points"))
        )
        categories: defaultdict[int, Counter[str]] = defaultdict(Counter)
        sources: defaultdict[int, Counter[str]] = defaultdict(Counter)
        for recipient_id, category, source_kind, points in rows:
            categories[recipient_id][category] += points
            sources[recipient_id][SOURCE_BUCKET_BY_KIND[source_kind]] += points
        return {
            user_id: AwardTotals(
                sum(category_points.values()),
                tuple(sorted(category_points.items())),
                tuple((source, sources[user_id][source]) for source in SOURCE_BUCKETS),
            )
            for user_id, category_points in categories.items()
        }

    def _load_released_counts(
        self, user_ids: Sequence[int]
    ) -> dict[int, dict[str, int]]:
        """Count current released authored Playbook PKs by category in bulk.

        :param user_ids: Candidate account IDs. Example: (42,).
        :return: Counts including private released books. Example: {42: {"design": 1}}.
        :raises ValueError: For invalid account identifiers.
        """
        rows = (
            Playbook.objects.filter(author_id__in=user_ids, status="released")
            .order_by()
            .values_list("author_id", "category")
            .annotate(amount=Count("pk", distinct=True))
        )
        counts: defaultdict[int, dict[str, int]] = defaultdict(dict)
        for author_id, category, count in rows:
            counts[author_id][category] = count
        return dict(counts)

    def _load_live_counts(
        self, user_ids: Sequence[int]
    ) -> dict[int, LiveContributionCounts]:
        """Read current public released books and explicit GUI consumption rows.

        :param user_ids: Candidate account IDs. Example: (42,).
        :return: Per-account live counts. Example: {42: LiveContributionCounts(2, 47)}.
        :raises ValueError: For invalid account identifiers.
        """
        public_books = dict(
            Playbook.objects.filter(
                author_id__in=user_ids, status="released", visibility="public"
            )
            .order_by()
            .values_list("author_id")
            .annotate(amount=Count("pk", distinct=True))
        )
        gui_copies = dict(
            KarmaAward.objects.filter(
                recipient_id__in=user_ids,
                source_kind=KarmaAward.SourceKind.CONSUMPTION,
                event_channel=EventChannel.GUI_COPY,
            )
            .order_by()
            .values_list("recipient_id")
            .annotate(amount=Count("pk"))
        )
        return {
            user_id: LiveContributionCounts(
                public_books.get(user_id, 0), gui_copies.get(user_id, 0)
            )
            for user_id in user_ids
        }

    def _load_identities(self, user_ids: Sequence[int]) -> dict[int, tuple[str, str]]:
        """Bulk-load username and display-name fields without account secrets.

        :param user_ids: Candidate account IDs. Example: (42,).
        :return: Username/name pairs. Example: {42: ("mchen", "Mike Chen")}.
        :raises ValueError: For invalid account identifiers.
        """
        rows = (
            get_user_model()
            .objects.filter(pk__in=user_ids)
            .values_list("pk", "username", "first_name", "last_name")
        )
        return {
            user_id: (
                username,
                " ".join(part.strip() for part in (first, last) if part.strip())
                or username,
            )
            for user_id, username, first, last in rows
        }

    def _project_candidates(
        self,
        totals: Mapping[int, AwardTotals],
        release_counts: Mapping[int, Mapping[str, int]],
        identities: Mapping[int, tuple[str, str]],
        live_counts: Mapping[int, LiveContributionCounts],
    ) -> tuple[ExpertProjection, ...]:
        """Build immutable projections without additional database reads.

        :param totals: Complete award aggregates. Example: {}.
        :param release_counts: Primary-category tie counts. Example: {}.
        :param identities: Allowlisted account identity pairs. Example: {}.
        :param live_counts: Public/fallback counts. Example: {}.
        :return: Unranked positive-contribution projections. Example: ().
        :raises ValueError: For inconsistent aggregate/account references.
        """
        projections: list[ExpertProjection] = []
        for user_id, award in totals.items():
            if user_id not in identities or user_id not in live_counts:
                raise ValueError(
                    "Award aggregates are missing account projection data."
                )
            if award.total_points <= 0:
                continue
            username, display_name = identities[user_id]
            counts = live_counts[user_id]
            projections.append(
                ExpertProjection(
                    user_id=user_id,
                    username=username,
                    display_name=display_name,
                    total_points=award.total_points,
                    primary_category=resolve_primary_category(
                        dict(award.category_points), release_counts.get(user_id, {})
                    ),
                    category_points=award.category_points,
                    source_points=award.source_points,
                    released_public_playbook_count=counts.released_public_playbook_count,
                    successful_gui_copy_count=counts.successful_gui_copy_count,
                )
            )
        return tuple(projections)

    def _zero_projection(
        self, user_id: int, identity: tuple[str, str], counts: LiveContributionCounts
    ) -> ExpertProjection:
        """Build the existing zero-account projection used by own-profile UI.

        :param user_id: Existing account PK. Example: 42.
        :param identity: Username/name pair. Example: ("nberg", "Nora Berg").
        :param counts: Current numeric counts. Example: LiveContributionCounts(0, 0).
        :return: Zero total, four zero source buckets and no primary category.
        :raises ValueError: For invalid identity or count data.
        """
        username, display_name = identity
        return ExpertProjection(
            user_id=user_id,
            username=username,
            display_name=display_name,
            total_points=0,
            primary_category=None,
            category_points=(),
            source_points=tuple((source, 0) for source in SOURCE_BUCKETS),
            released_public_playbook_count=counts.released_public_playbook_count,
            successful_gui_copy_count=counts.successful_gui_copy_count,
        )

    def _select_leaders(
        self, people: Sequence[ExpertProjection], category: str
    ) -> tuple[ExpertProjection, ...]:
        """Filter positive primary-category users, sort overall total and limit.

        :param people: Complete candidate projections. Example: ().
        :param category: Selected slug. Example: "design".
        :return: At most five ordered projections. Example: ().
        :raises ValueError: For invalid category or projection data.
        """
        category_label(category)
        eligible = (
            person
            for person in people
            if person.total_points > 0 and person.primary_category == category
        )
        ranked = sorted(
            eligible, key=lambda person: (-person.total_points, person.username)
        )
        return tuple(ranked[:LEADERBOARD_LIMIT])

    @classmethod
    def public_detail(cls, username: str, *, correlation_id: str) -> PublicExpertDetail:
        """Read an eligible public profile without writes or generation.

        :param username: Exact account name. Example: "mrodriguez".
        :param correlation_id: Safe request identifier. Example: "cedar-s17".
        :return: Allowlisted public payload. Example: {"name": "Maria Rodriguez", ...}.
        :raises ValueError: For malformed inputs.
        :raises LookupError: For a missing or nonpositive contributor.
        """
        raise NotImplementedError()

    @classmethod
    def _detail_subject(cls, username: str) -> AbstractUser:
        """Resolve a subject without exposing account fields.

        :param username: Validated username. Example: "mrodriguez".
        :return: Internal user for projection only. Example: Maria's persisted user.
        :raises LookupError: When the account does not exist.
        """
        raise NotImplementedError()

    @classmethod
    def _detail_public_books(cls, subject_id: int) -> tuple[PublicExpertBook, ...]:
        """Project only currently public released authored playbooks.

        :param subject_id: Real account key. Example: 101.
        :return: Allowlisted evidence ordered deterministically. Example: ({"pk": 6101, ...},).
        :raises ValueError: For an invalid subject key.
        """
        raise NotImplementedError()

    @staticmethod
    def _detail_book(playbook: Playbook) -> PublicExpertBook:
        """Extract safe evidence fields without broad model serialization.

        :param playbook: Public released book. Example: Accessibility Audit Playbook.
        :return: Public display fields. Example: {"pk": 6101, "version": "1.0", ...}.
        :raises ValueError: If visibility or release preconditions fail.
        """
        raise NotImplementedError()

    @classmethod
    def _detail_payload(
        cls,
        subject: AbstractUser,
        projection: ExpertProjection,
        public_books: tuple[PublicExpertBook, ...],
    ) -> PublicExpertDetail:
        """Combine foundation numeric values and unchanged stored public prose.

        :param subject: Internal subject. Example: Maria's user.
        :param projection: S03 numeric projection. Example: total 8200, primary Design.
        :param public_books: Safe evidence. Example: Accessibility Audit Playbook v1.0.
        :return: Escapable public values only. Example: summary equals the stored paragraph.
        :raises LookupError: When total Karma is not positive.
        :raises ValueError: When the projection contract is invalid.
        """
        raise NotImplementedError()

    @staticmethod
    def _detail_log(detail: PublicExpertDetail, *, correlation_id: str) -> None:
        """Record projection metadata without prose or contact information.

        :param detail: Safe detail projection. Example: Maria's 8200-point payload.
        :param correlation_id: Shared request ID. Example: "cedar-s17".
        :return: None. Example: no value.
        :raises ValueError: When correlation identity is invalid.
        """
        raise NotImplementedError()


class PublicExpertBook(TypedDict):
    pk: int
    title: str
    version: str
    category: str


class PublicExpertDetail(TypedDict):
    subject_id: int
    username: str
    name: str
    initials: str
    total_karma: int
    formatted_karma: str
    primary_category: str
    summary: str
    numeric_fallback: str
    source_rows: tuple[Mapping[str, object], ...]
    category_rows: tuple[Mapping[str, object], ...]
    public_playbooks: tuple[PublicExpertBook, ...]
