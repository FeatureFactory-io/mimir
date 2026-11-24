"""Allowlisted presentation of public expert cards."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Literal, cast

from methodology.services.expert_text import (
    category_label,
    display_initials,
    format_karma,
    format_numeric_fallback,
)
from methodology.services.experts_service import ExpertProjection

logger = logging.getLogger(__name__)
_LOG_STORY = "ExpertCardPresentationService.present"
_CORRELATION_ID = re.compile(r"[A-Za-z0-9._:-]{1,100}")
_REJECTION = "status=rejected reason=invalid_projection"
_HINT_REASONS = {
    "stored_summary": "stored_public_prose",
    "live_counts": "no_stored_public_prose",
}


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
        subject_id = None
        if isinstance(projection, ExpertProjection):
            subject_id = projection.user_id
        subject = subject_id if type(subject_id) is int and subject_id > 0 else "-"
        safe_correlation_id = ""
        if isinstance(correlation_id, str) and _CORRELATION_ID.fullmatch(
            correlation_id
        ):
            safe_correlation_id = correlation_id
        context = f"subject_id={subject} correlation_id={safe_correlation_id or '-'}"
        logger.info("%s | entry | %s", _LOG_STORY, context)
        try:
            self._validate(projection, stored_summary, safe_correlation_id)
        except ValueError:
            logger.info("%s | validation | %s %s", _LOG_STORY, _REJECTION, context)
            raise
        hint, source = self._hint(projection, stored_summary)
        branch = f"hint_source={source} reason={_HINT_REASONS[source]}"
        logger.info("%s | branch | %s %s", _LOG_STORY, branch, context)
        card = ExpertCardPresentation(
            username=projection.username,
            display_name=projection.display_name,
            initials=display_initials(projection.display_name),
            formatted_karma=format_karma(projection.total_points),
            primary_category=category_label(cast(str, projection.primary_category)),
            hint=hint,
            hint_source=source,
        )
        logger.info("%s | exit | status=ok %s", _LOG_STORY, context)
        return card

    def _validate(
        self,
        projection: ExpertProjection,
        stored_summary: str | None,
        correlation_id: str,
    ) -> None:
        """Validate identity, category, positive total and nonnegative integer counts.

        :param projection: Public live values. Example: total_points=8200.
        :param stored_summary: Optional public prose. Example: None.
        :param correlation_id: Validated identifier, empty on invalid input. Example: "cedar-s04".
        :return: None. Example: None after valid inputs.
        :raises ValueError: For malformed inputs or unsupported categories.
        """
        if not isinstance(projection, ExpertProjection):
            raise ValueError("An expert projection is required.")  # noqa: TRY004
        if type(projection.user_id) is not int or projection.user_id <= 0:
            raise ValueError("Expert subject ID must be a positive integer.")
        if not isinstance(projection.username, str) or not projection.username.strip():
            raise ValueError("Expert username must be nonblank text.")
        if (
            not isinstance(projection.display_name, str)
            or not projection.display_name.strip()
        ):
            raise ValueError("Expert display name must be nonblank text.")
        if type(projection.total_points) is not int or projection.total_points <= 0:
            raise ValueError("Karma total must be a positive integer.")
        category_label(projection.primary_category or "")
        counts = (
            projection.released_public_playbook_count,
            projection.successful_gui_copy_count,
        )
        if any(type(count) is not int or count < 0 for count in counts):
            raise ValueError("Live contribution counts must be nonnegative integers.")
        if stored_summary is not None and not isinstance(stored_summary, str):
            raise ValueError("Stored summary must be text or None.")
        if not correlation_id:
            raise ValueError("A safe request correlation ID is required.")

    def _hint(
        self, projection: ExpertProjection, stored_summary: str | None
    ) -> tuple[str, Literal["stored_summary", "live_counts"]]:
        """Select complete public prose or the live-count fallback.

        :param projection: Live counts. Example: 2 released books and 47 GUI copies.
        :param stored_summary: Complete stored paragraph. Example: None.
        :return: Text and source. Example: ("2 released playbooks · 47 copies", "live_counts").
        :raises ValueError: If the fallback counts violate the presentation contract.
        """
        if stored_summary is not None and stored_summary.strip():
            return stored_summary, "stored_summary"
        counts_hint = format_numeric_fallback(
            projection.released_public_playbook_count,
            projection.successful_gui_copy_count,
        )
        return counts_hint, "live_counts"
