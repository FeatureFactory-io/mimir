from __future__ import annotations

"""Allowlisted presentation of public expert cards."""
from dataclasses import dataclass
from typing import Literal
from methodology.services.experts_service import ExpertProjection


@dataclass(frozen=True)
class ExpertCardPresentation:
    """Public display fields; excludes account and contact information."""

    username: str
    display_name: str
    initials: str
    formatted_karma: str
    primary_category: str
    hint: str
    hint_source: Literal["stored_summary", "live_counts"]


class ExpertCardPresentationService:
    """Present existing public evidence without generating or ranking it."""

    def present(
        self,
        projection: ExpertProjection,
        stored_summary: str | None,
        *,
        correlation_id: str,
    ) -> ExpertCardPresentation:
        """Build public card display values.

        :param projection: S03 live projection. Example: Maria, total_points=8200.
        :param stored_summary: Approved stored prose. Example: "Maria maintains…".
        :param correlation_id: Safe request identifier. Example: "cedar-s04".
        :return: Immutable display fields. Example: formatted_karma="8,200".
        :raises ValueError: If projection, summary type or correlation ID is invalid.
        """
        raise NotImplementedError()

    def _validate(
        self,
        projection: ExpertProjection,
        stored_summary: str | None,
        correlation_id: str,
    ) -> None:
        """Validate identity, category, positive total and nonnegative integer counts.

        :param projection: Public live values. Example: total_points=8200.
        :param stored_summary: Optional public prose. Example: None.
        :param correlation_id: Safe identifier. Example: "cedar-s04".
        :return: None. Example: None after valid inputs.
        :raises ValueError: For malformed identity, values or unsupported category.
        """
        raise NotImplementedError()

    def _hint(
        self, projection: ExpertProjection, stored_summary: str | None
    ) -> tuple[str, Literal["stored_summary", "live_counts"]]:
        """Select complete public prose or the exact live-count fallback.

        :param projection: Live counts. Example: 2 released books and 47 GUI copies.
        :param stored_summary: Complete stored paragraph. Example: None.
        :return: Text and source. Example: ("2 released playbooks · 47 copies", "live_counts").
        :raises ValueError: If supplied values violate the presentation contract.
        """
        raise NotImplementedError()
