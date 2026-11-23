"""Read-only ledger projections shared by Experts and contribution displays."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypedDict
from django.contrib.auth.models import AbstractUser
from methodology.models import Playbook

from dataclasses import dataclass
from typing import Sequence

LEADERBOARD_LIMIT = 5
SOURCE_BUCKETS = ("Released", "PIP", "Consumption", "Learning")


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
    raise NotImplementedError()


def _validate_category_totals(values: Mapping[str, int]) -> None:
    """Validate recognized category keys and nonnegative integral values.

    :param values: Points or released-book counts. Example: {"design": 1}.
    :return: None. Example: None.
    :raises ValueError: For invalid categories, booleans or negative values.
    """
    raise NotImplementedError()


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
        raise NotImplementedError()

    def project_user(self, user_id: int) -> ExpertProjection:
        """Project an existing account, including a zero-contribution account.

        :param user_id: Existing positive account PK. Example: 42.
        :return: Numeric/public identity snapshot. Example: a zero Nora projection.
        :raises ValueError: For invalid or nonexistent account identifiers.
        """
        raise NotImplementedError()

    def _validate_query(self, category: str, correlation_id: str) -> None:
        """Validate explicit service inputs before queries.

        :param category: Canonical category slug. Example: "design".
        :param correlation_id: Request identity. Example: "cedar-s03".
        :return: None. Example: None.
        :raises ValueError: For invalid inputs.
        """
        raise NotImplementedError()

    def _load_award_totals(
        self, user_ids: Sequence[int] | None = None
    ) -> dict[int, AwardTotals]:
        """Aggregate all category/source awards, merging major/minor into PIP.

        :param user_ids: Optional recipient restriction. Example: (42,).
        :return: Per-recipient immutable aggregates. Example: {}.
        :raises ValueError: For invalid recipient identifiers.
        """
        raise NotImplementedError()

    def _load_released_counts(
        self, user_ids: Sequence[int]
    ) -> dict[int, dict[str, int]]:
        """Count current released authored Playbook PKs by category in bulk.

        :param user_ids: Candidate account IDs. Example: (42,).
        :return: Counts including private released books. Example: {42: {"design": 1}}.
        :raises ValueError: For invalid account identifiers.
        """
        raise NotImplementedError()

    def _load_live_counts(
        self, user_ids: Sequence[int]
    ) -> dict[int, LiveContributionCounts]:
        """Read current public released books and explicit GUI consumption rows.

        :param user_ids: Candidate account IDs. Example: (42,).
        :return: Per-account live counts. Example: {42: LiveContributionCounts(2, 47)}.
        :raises ValueError: For invalid account identifiers.
        """
        raise NotImplementedError()

    def _load_identities(self, user_ids: Sequence[int]) -> dict[int, tuple[str, str]]:
        """Bulk-load username and display-name fields without account secrets.

        :param user_ids: Candidate account IDs. Example: (42,).
        :return: Username/name pairs. Example: {42: ("mchen", "Mike Chen")}.
        :raises ValueError: For invalid account identifiers.
        """
        raise NotImplementedError()

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
        raise NotImplementedError()

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
        raise NotImplementedError()

    def _select_leaders(
        self, people: Sequence[ExpertProjection], category: str
    ) -> tuple[ExpertProjection, ...]:
        """Filter positive primary-category users, sort overall total and limit.

        :param people: Complete candidate projections. Example: ().
        :param category: Selected slug. Example: "design".
        :return: At most five ordered projections. Example: ().
        :raises ValueError: For invalid category or projection data.
        """
        raise NotImplementedError()

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
