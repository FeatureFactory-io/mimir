from __future__ import annotations

"""Read-only, allowlisted public contribution evidence."""
from dataclasses import dataclass
from methodology.models import PipChange, Playbook

MAX_EVIDENCE_CHARACTERS = 24000


@dataclass(frozen=True)
class PublicContributionFact:
    """Immutable fact containing only currently public published information."""

    playbook_id: int
    playbook_name: str
    category: str
    kind: str
    entity_type: str
    operation: str
    title: str
    text: str


@dataclass(frozen=True)
class PublicContributionEvidence:
    """Immutable public-only input; no model instances, ledger or account data."""

    subject_id: int
    facts: tuple[PublicContributionFact, ...]


class PublicContributionEvidenceService:
    """Collect deterministic evidence without changing any domain state."""

    def collect(self, subject_id: int) -> PublicContributionEvidence:
        """Collect released public facts and published accepted contributions.

        :param subject_id: Existing positive user ID. Example: 42.
        :return: Immutable public evidence. Example: evidence for Maria.
        :raises ValueError: For invalid/missing subject or oversized evidence.
        """
        raise NotImplementedError()

    def _validate_subject(self, subject_id: int) -> None:
        """Reject invalid or nonexistent subjects.

        :param subject_id: Positive non-bool user ID. Example: 42.
        :return: None when valid.
        :raises ValueError: For invalid input or missing user.
        """
        raise NotImplementedError()

    def _released_public_playbooks(self, subject_id: int) -> tuple[Playbook, ...]:
        """Select only authored public released playbooks in stable order.

        :param subject_id: Valid user ID. Example: 42.
        :return: Ordered rows. Example: (accessibility_playbook,).
        :raises ValueError: For invalid subject ID.
        """
        raise NotImplementedError()

    def _published_changes(self, subject_id: int) -> tuple[PipChange, ...]:
        """Select accepted rows with matching committed publication receipts.

        :param subject_id: Valid contributor ID. Example: 42.
        :return: Ordered eligible changes. Example: (keyboard_audit_add,).
        :raises ValueError: For invalid subject ID.
        """
        raise NotImplementedError()

    def _playbook_facts(self, playbook: Playbook) -> tuple[PublicContributionFact, ...]:
        """Project allowlisted current public playbook/workflow/entity fields.

        :param playbook: Released public row. Example: Accessibility Audit.
        :return: Immutable sanitized facts. Example: (trace_focus_fact,).
        :raises ValueError: If visibility/status preconditions no longer hold.
        """
        raise NotImplementedError()

    def _change_facts(self, change: PipChange) -> tuple[PublicContributionFact, ...]:
        """Project published attribution without copying proposal payloads.

        :param change: Eligible published accepted row. Example: ADD Activity.
        :return: Safe attribution/detail facts. Example: (keyboard_audit_fact,).
        :raises ValueError: If publication preconditions no longer hold.
        """
        raise NotImplementedError()

    def _resolve_current_entity_fact(
        self, change: PipChange
    ) -> PublicContributionFact | None:
        """Resolve only current same-playbook detail; omit ambiguous ADD matches.

        :param change: Published accepted row. Example: Keyboard Audit ADD.
        :return: Public detail or None. Example: keyboard_audit_fact.
        :raises ValueError: For an unsupported or invalid entity reference.
        """
        raise NotImplementedError()

    def _safe_text(self, text: str) -> str:
        """Remove email/recognizable credential material from public text.

        :param text: Allowlisted published field. Example: "Review focus order".
        :return: Sanitized text. Example: "Review focus order".
        :raises ValueError: For non-string input.
        """
        raise NotImplementedError()

    def _validate_snapshot(
        self, evidence: PublicContributionEvidence
    ) -> PublicContributionEvidence:
        """Validate immutable field shapes and full serialized size.

        :param evidence: Collected snapshot. Example: Maria's public facts.
        :return: Valid evidence unchanged. Example: the same snapshot.
        :raises ValueError: If malformed or over 24,000 serialized characters.
        """
        raise NotImplementedError()
