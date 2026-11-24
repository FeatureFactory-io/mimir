"""Read-only, allowlisted public contribution evidence."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, fields
from decimal import Decimal
from itertools import chain

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Prefetch, Q

from methodology.models import (
    Activity,
    Agent,
    Artifact,
    Phase,
    PipChange,
    Playbook,
    PlaybookVersion,
    ProcessImprovementProposal,
    Rule,
    Skill,
    VersionSource,
    Workflow,
)

logger = logging.getLogger(__name__)

MAX_EVIDENCE_CHARACTERS = 24000
_COLLECT = "PublicContributionEvidenceService.collect"
_MAX_DATABASE_ID = (1 << 63) - 1
_PUBLIC_RELEASED = {"visibility": "public", "status": "released"}
_PUBLISHED_PIP_STATES = (
    ProcessImprovementProposal.STATUS_ACCEPTED,
    ProcessImprovementProposal.STATUS_ACCEPTED_PARTIAL,
)
_RELATIONSHIP_OPERATIONS = (PipChange.CHANGE_LINK, PipChange.CHANGE_UNLINK)
_OPERATIONS = {value for value, _ in PipChange.CHANGE_TYPE_CHOICES}
_CATEGORIES = {value for value, _ in Playbook.CATEGORY_CHOICES}
_CATEGORY_LABELS = "|".join(re.escape(label) for _, label in Playbook.CATEGORY_CHOICES)
_INITIAL_RELEASE = Decimal("1.0")
_VERSION_NUMBER = re.compile(r"[0-9]{1,4}\.[0-9]")
_ENTITY_FIELDS = {
    PipChange.ENTITY_WORKFLOW: (Workflow, "playbook", "name", "description", 100),
    PipChange.ENTITY_ACTIVITY: (
        Activity,
        "workflow__playbook",
        "name",
        "guidance",
        200,
    ),
    PipChange.ENTITY_PHASE: (Phase, "playbook", "name", "description", 200),
    PipChange.ENTITY_SKILL: (Skill, "playbook", "title", "content", 200),
    PipChange.ENTITY_AGENT: (Agent, "playbook", "name", "description", 200),
    PipChange.ENTITY_ARTIFACT: (Artifact, "playbook", "name", "description", 200),
    PipChange.ENTITY_RULE: (Rule, "playbook", "title", "content", 200),
}
# Horizontal whitespace keeps metric prose matches within a single source line.
_SPACE = r"[^\S\r\n]"
_LABEL_SEPARATOR = r"[^\S\r\n]|[-_\u2010\u2011]"
_LABEL_GAP = rf"(?:{_LABEL_SEPARATOR})+"
_LABEL_JOINER = rf"(?:{_LABEL_SEPARATOR})*"
_NUMBER_GAP = r"[ \t\u00a0\u202f\u2010\u2011-]+"
# Twenty-four tokens cover English numbers through billions, including "and"
# between groups. Bounding the run also limits work on unstructured source text.
_MAX_ADDITIONAL_NUMBER_WORDS = 23
_NUMBER_WORD = (
    r"(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
    r"|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty"
    r"|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundreds?|thousands?"
    r"|millions?|billions?|dozen"
    r"|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth"
    r"|eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|seventeenth"
    r"|eighteenth|nineteenth|twentieth|thirtieth|fortieth|fiftieth|sixtieth"
    r"|seventieth|eightieth|ninetieth|hundredth|thousandth|millionth|billionth)\b"
)
_DIGIT_NUMBER = (
    r"(?:\d{1,3}(?:[., \u00a0\u202f]\d{3})+|\d+)(?:[.,]\d+)?(?:st|nd|rd|th)?\b"
)
_WRITTEN_NUMBER = (
    rf"{_NUMBER_WORD}(?:{_NUMBER_GAP}(?:and{_NUMBER_GAP})?{_NUMBER_WORD})"
    rf"{{0,{_MAX_ADDITIONAL_NUMBER_WORDS}}}"
)
# Consume the value as a unit. A trailing pattern may not backtrack into its
# grouped digits or ordinal words to match the shorter cardinal prefix.
_NUMBER = rf"(?>{_DIGIT_NUMBER}|{_WRITTEN_NUMBER})"
_PROSE_CONNECTOR = (
    rf"{_SPACE}+(?:is|are|was|were|of|at|reached|rose{_SPACE}+to|stands?{_SPACE}+at)"
    rf"{_SPACE}+"
)
_ASSIGNMENT_SEPARATOR = r"[:=–—]"
_PUNCTUATION_CONNECTOR = rf"{_SPACE}*{_ASSIGNMENT_SEPARATOR}{_SPACE}*"
_VALUE_CONNECTOR = rf"(?:{_PUNCTUATION_CONNECTOR}|{_PROSE_CONNECTOR})"
_OPTIONAL_CONNECTOR = rf"(?:{_VALUE_CONNECTOR}|{_SPACE}*)"
_VALUE_QUALIFIER = (
    rf"(?:(?:about|around|roughly|approximately|over|under|at{_SPACE}+(?:least|most))"
    rf"{_SPACE}+)?"
)
_VALUE = rf"{_VALUE_QUALIFIER}{_NUMBER}"
_COUNT_NOUN = (
    rf"(?:(?:released|public|authored|published|accepted){_LABEL_GAP})*"
    r"(?:playbooks?|pips?|proposals?|contributions?|copies|copy)"
)
_KARMA_LABEL = rf"karma(?:{_LABEL_GAP}(?:total|score|points))?"
_CATEGORY_METRIC = (
    rf"(?:category|(?:{_CATEGORY_LABELS})(?:{_LABEL_GAP}category)?)(?:['’]s)?{_LABEL_GAP}"
    rf"(?:score|points|(?:points?{_LABEL_GAP})?(?:subtotals?|totals?)|{_KARMA_LABEL})"
)
_LEADERBOARD = rf"(?:the{_SPACE}+)?(?:(?:{_CATEGORY_LABELS}){_SPACE}+)?leaderboard"
_PERCENT_SUFFIX = rf"(?:{_SPACE}*%|{_SPACE}+percent\b)?"
_REDACTED = "[redacted]"
_CREDENTIAL_LABEL = (
    rf"(?:api{_LABEL_JOINER}(?:key|token)|(?:access|auth){_LABEL_JOINER}token"
    rf"|client{_LABEL_JOINER}secret|password)"
)
_CREDENTIAL_CONNECTOR = (
    rf"(?:\s*{_ASSIGNMENT_SEPARATOR}\s*|{_SPACE}+(?:is|was){_SPACE}+)"
)
_CREDENTIAL_VALUE = (
    r"""(?:"[^"\r\n]*"|'[^'\r\n]*'|`[^`\r\n]*`|\[[^\]\r\n]*\]"""
    r"""|[^\s;,()[\]{}<>"'`]+(?<![.!?:]))"""
)
_CREDENTIAL_PATTERNS = (
    r"-----BEGIN\ [A-Z\ ]*PRIVATE\ KEY-----[\s\S]*?(?:-----END\ [A-Z\ ]*PRIVATE\ KEY-----|\Z)",
    r"(?<=://)[^\s/@]+:[^\s/@]+(?=@)",
    r"\b[\w.%+!-]+@[\w.-]+\.[a-z]{2,}\b",
    rf"""\b{_CREDENTIAL_LABEL}["']?{_CREDENTIAL_CONNECTOR}{_CREDENTIAL_VALUE}""",
    r"\bbearer\s+[a-z0-9._~+/=-]+(?<![.])",
    r"\b(?:sk-(?:ant-|proj-)?|gh[pousr]_|github_pat_|xox[baprs]-)[a-z0-9_-]{12,}\b",
    r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    r"\beyJ[a-z0-9_-]+\.[a-z0-9_-]+\.[a-z0-9_-]+\b",
    r"\b[a-f0-9]{40}\b",
)
_AGGREGATE_PATTERNS = (
    rf"\b{_NUMBER}{_SPACE}+(?:(?:{_CATEGORY_LABELS}|management|karma){_SPACE}+)?points\b",
    rf"\b{_NUMBER}{_SPACE}+{_COUNT_NOUN}\b",
    rf"\b{_NUMBER}{_SPACE}+karma\b",
    rf"\b(?:copied|downloaded){_SPACE}+{_VALUE}{_SPACE}+times\b",
    (
        rf"\b(?:total{_LABEL_GAP}(?:karma|score|points)|{_KARMA_LABEL}|"
        rf"category{_LABEL_GAP}(?:points|point{_LABEL_GAP}subtotals?))\b"
        rf"{_OPTIONAL_CONNECTOR}{_VALUE}{_PERCENT_SUFFIX}"
    ),
    rf"\b{_COUNT_NOUN}{_LABEL_GAP}(?:counts?|totals?)\b{_OPTIONAL_CONNECTOR}{_VALUE}",
    rf"\btotal{_LABEL_GAP}{_COUNT_NOUN}\b{_VALUE_CONNECTOR}{_VALUE}",
    (
        rf"\b(?:counts?|(?:total{_LABEL_GAP})?number){_LABEL_GAP}of{_LABEL_GAP}"
        rf"{_COUNT_NOUN}\b{_OPTIONAL_CONNECTOR}{_VALUE}"
    ),
    # A named category requires an explicit connector to preserve Design Score 2.0.
    rf"\b{_CATEGORY_METRIC}\b{_VALUE_CONNECTOR}{_VALUE}{_PERCENT_SUFFIX}",
    rf"\b(?:rank(?:ed)?|placed)\b{_OPTIONAL_CONNECTOR}\#?{_SPACE}*{_VALUE}",
    rf"\b(?:position|number){_SPACE}*\#?{_SPACE}*{_VALUE}{_SPACE}+on{_SPACE}+{_LEADERBOARD}\b",
    (
        rf"\b(?:top{_SPACE}+)?{_NUMBER}{_SPACE}+"
        rf"(?:place|rank|on{_SPACE}+{_LEADERBOARD})\b"
    ),
)
_POLICY_FLAGS = re.IGNORECASE | re.VERBOSE
# The boundary also checks its string metadata for recognizable credentials.
_SENSITIVE_TEXT = re.compile("|".join(_CREDENTIAL_PATTERNS), _POLICY_FLAGS)
_PUBLIC_TEXT_PATTERNS = tuple(
    re.compile(pattern, _POLICY_FLAGS)
    for pattern in (*_CREDENTIAL_PATTERNS, *_AGGREGATE_PATTERNS, re.escape(_REDACTED))
)


def _redact_public_text(text: str) -> str:
    """Replace matching sensitive or mutable claims in a public source field.

    :param text: Published field. Example: "Karma total is 900."
    :return: Scrubbed field. Example: "[redacted]."
    """
    # Match against the original field. A replacement could hide a label from
    # another rule or leave a trailing number fragment from an overlapping match.
    spans = sorted(
        match.span()
        for pattern in _PUBLIC_TEXT_PATTERNS
        for match in pattern.finditer(text)
    )
    parts: list[str] = []
    end = 0
    for start, match_end in spans:
        if not parts or start > end:
            parts.extend((text[end:start], _REDACTED))
        end = max(end, match_end)
    parts.append(text[end:])
    return "".join(parts)


def _contains_restricted_summary_text(text: str) -> bool:
    """Recognize the same restricted forms in an assembled model paragraph.

    :param text: Validated plain prose. Example: "Her Karma total is 900."
    :return: Whether it contains a restricted span. Example: True.
    """
    return any(pattern.search(text) for pattern in _PUBLIC_TEXT_PATTERNS)


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
        self._validate_subject(subject_id)
        logger.info("%s | entry | subject_id=%s", _COLLECT, subject_id)
        logger.info(
            "%s | validation | subject_id=%s scope=public_released",
            _COLLECT,
            subject_id,
        )
        with transaction.atomic():
            authored = map(
                self._playbook_facts, self._released_public_playbooks(subject_id)
            )
            changes = map(self._change_facts, self._published_changes(subject_id))
            facts = tuple(chain.from_iterable(chain(authored, changes)))
        result = self._validate_snapshot(PublicContributionEvidence(subject_id, facts))
        logger.info("%s | exit | subject_id=%s outcome=success", _COLLECT, subject_id)
        return result

    def _validate_subject(self, subject_id: int) -> None:
        """Reject invalid or nonexistent subjects.

        :param subject_id: Positive non-bool user ID. Example: 42.
        :return: None when valid.
        :raises ValueError: For invalid input or missing user.
        """
        if type(subject_id) is not int or not 0 < subject_id <= _MAX_DATABASE_ID:
            logger.info("%s | error | reason_code=invalid_subject", _COLLECT)
            raise ValueError("A positive integer subject ID is required.")
        if not get_user_model().objects.filter(pk=subject_id).exists():
            logger.info(
                "%s | error | subject_id=%s reason_code=missing_subject",
                _COLLECT,
                subject_id,
            )
            raise ValueError("The subject does not exist.")

    def _released_public_playbooks(self, subject_id: int) -> tuple[Playbook, ...]:
        """Select only authored public released playbooks in stable order.

        :param subject_id: Valid user ID. Example: 42.
        :return: Ordered rows. Example: (accessibility_playbook,).
        """
        return tuple(
            Playbook.objects.filter(author_id=subject_id, **_PUBLIC_RELEASED)
            .only("name", "description", "category", "visibility", "status")
            .order_by("pk")
        )

    def _published_changes(self, subject_id: int) -> tuple[PipChange, ...]:
        """Select accepted rows with matching committed publication receipts.

        :param subject_id: Valid contributor ID. Example: 42.
        :return: Ordered eligible changes. Example: (keyboard_audit_add,).
        """
        receipts = PlaybookVersion.objects.filter(
            source=VersionSource.PIP_SOURCE,
            playbook_id=F("pip__playbook_id"),
            version_number__lte=F("playbook__version"),
        ).only("pip_id", "version_number", "is_major", "snapshot_data")
        candidates = (
            PipChange.objects.filter(
                Q(entity_type__in=_ENTITY_FIELDS)
                | Q(change_type__in=_RELATIONSHIP_OPERATIONS),
                pip__created_by_id=subject_id,
                pip__status__in=_PUBLISHED_PIP_STATES,
                pip__playbook__visibility="public",
                pip__playbook__status="released",
                admin_decision=PipChange.ADMIN_ACCEPT,
                change_type__in=_OPERATIONS,
            )
            .select_related("pip__playbook")
            .only(
                "change_type",
                "entity_type",
                "target_id",
                "name",
                "pip__playbook__name",
                "pip__playbook__category",
                "pip__playbook__visibility",
                "pip__playbook__status",
            )
            .prefetch_related(
                Prefetch(
                    "pip__playbook_versions",
                    queryset=receipts,
                    to_attr="publication_receipts",
                )
            )
            .order_by("pip__playbook_id", "pip_id", "order", "pk")
        )
        published = []
        for change in candidates:
            for receipt in change.pip.publication_receipts:
                snapshot = receipt.snapshot_data
                if (
                    not isinstance(snapshot, dict)
                    or type(snapshot.get("pip_id")) is not int
                    or snapshot["pip_id"] != change.pip_id
                ):
                    continue
                version = str(receipt.version_number)
                before = snapshot.get("version_before")
                current_format = (
                    isinstance(before, str)
                    and _VERSION_NUMBER.fullmatch(before)
                    and _INITIAL_RELEASE <= Decimal(before) < receipt.version_number
                    and snapshot.get("version_after") == version
                )
                # The older aggregate writer recorded only the new minor version.
                legacy_format = (
                    not receipt.is_major
                    and "version_before" not in snapshot
                    and "version_after" not in snapshot
                    and snapshot.get("version") == version
                    and receipt.version_number > _INITIAL_RELEASE
                )
                if not (current_format or legacy_format):
                    continue
                # Cedar receipts additionally declare the exact historical change IDs.
                accepted_ids = snapshot.get("accepted_change_ids", [change.pk])
                if isinstance(accepted_ids, list) and any(
                    type(pk) is int and pk == change.pk for pk in accepted_ids
                ):
                    published.append(change)
                    break
        return tuple(published)

    def _playbook_facts(self, playbook: Playbook) -> tuple[PublicContributionFact, ...]:
        """Project allowlisted current public playbook/workflow/entity fields.

        :param playbook: Released public row. Example: Accessibility Audit.
        :return: Immutable sanitized facts. Example: (trace_focus_fact,).
        :raises ValueError: If visibility/status preconditions no longer hold.
        """
        if playbook.visibility != "public" or playbook.status != "released":
            raise ValueError("Public evidence requires a public released playbook.")
        labels = [("Playbook", playbook.name, playbook.description)]
        for entity_type, (
            model,
            scope,
            title_field,
            body_field,
            _,
        ) in _ENTITY_FIELDS.items():
            rows = (
                model.objects.filter(
                    **{
                        f"{scope}_id": playbook.pk,
                        f"{scope}__visibility": "public",
                        f"{scope}__status": "released",
                    }
                )
                .order_by("pk")
                .values_list(title_field, body_field)
            )
            labels.extend((entity_type, title, body) for title, body in rows)
        playbook_name = self._safe_text(playbook.name)
        category = playbook.category if playbook.category in _CATEGORIES else ""
        return tuple(
            PublicContributionFact(
                playbook.pk,
                playbook_name,
                category,
                "authored",
                entity_type,
                "",
                self._safe_text(title),
                self._safe_text(body),
            )
            for entity_type, title, body in labels
        )

    def _change_facts(self, change: PipChange) -> tuple[PublicContributionFact, ...]:
        """Project published attribution without copying proposal payloads.

        :param change: Eligible published accepted row. Example: ADD Activity.
        :return: Safe attribution/detail facts. Example: (keyboard_audit_fact,).
        :raises ValueError: If publication preconditions no longer hold.
        """
        playbook = change.pip.playbook
        if playbook.visibility != "public" or playbook.status != "released":
            raise ValueError(
                "Published attribution requires a public released playbook."
            )
        detail = self._resolve_current_entity_fact(change)
        if detail is not None:
            return (detail,)
        category = playbook.category if playbook.category in _CATEGORIES else ""
        entity_type = (
            change.entity_type
            if change.entity_type in _ENTITY_FIELDS
            else "Relationship"
        )
        return (
            PublicContributionFact(
                playbook.pk,
                self._safe_text(playbook.name),
                category,
                "published_change",
                entity_type,
                change.change_type,
                "",
                "",
            ),
        )

    def _resolve_current_entity_fact(
        self, change: PipChange
    ) -> PublicContributionFact | None:
        """Resolve only current same-playbook detail; omit ambiguous ADD matches.

        :param change: Published accepted row. Example: Keyboard Audit ADD.
        :return: Public detail or None. Example: keyboard_audit_fact.
        """
        operation = change.change_type
        if operation not in (PipChange.CHANGE_ADD, PipChange.CHANGE_ALTER):
            return None
        model, scope, title_field, body_field, added_title_limit = _ENTITY_FIELDS[
            change.entity_type
        ]
        if change.target_id is not None:
            identity = {"pk": change.target_id}
        elif operation == PipChange.CHANGE_ADD and change.name.strip():
            identity = {title_field: change.name.strip()[:added_title_limit]}
        else:
            return None
        playbook = change.pip.playbook
        matches = list(
            model.objects.filter(
                **identity,
                **{
                    f"{scope}_id": playbook.pk,
                    f"{scope}__visibility": "public",
                    f"{scope}__status": "released",
                },
            )
            .order_by("pk")
            .values_list(title_field, body_field)[:2]
        )
        if len(matches) != 1:
            return None
        title, body = matches[0]
        category = playbook.category if playbook.category in _CATEGORIES else ""
        return PublicContributionFact(
            playbook.pk,
            self._safe_text(playbook.name),
            category,
            "published_change",
            change.entity_type,
            operation,
            self._safe_text(title),
            self._safe_text(body),
        )

    def _safe_text(self, text: str) -> str:
        """Remove sensitive material and mutable aggregate claims from public text.

        :param text: Allowlisted published field. Example: "Review focus order".
        :return: Sanitized text. Example: "Review focus order".
        :raises ValueError: For non-string input.
        """
        if not isinstance(text, str):
            raise ValueError("Public evidence text must be a string.")  # noqa: TRY004
        return _redact_public_text(text)

    def _validate_snapshot(
        self, evidence: PublicContributionEvidence
    ) -> PublicContributionEvidence:
        """Validate immutable field shapes and full serialized size.

        :param evidence: Collected snapshot. Example: Maria's public facts.
        :return: Valid evidence unchanged. Example: the same snapshot.
        :raises ValueError: If malformed or over 24,000 serialized characters.
        """
        text_field_names = tuple(
            field.name
            for field in fields(PublicContributionFact)
            if field.name != "playbook_id"
        )
        if (
            type(evidence) is not PublicContributionEvidence
            or type(evidence.subject_id) is not int
            or evidence.subject_id <= 0
            or type(evidence.facts) is not tuple
            or any(
                type(fact) is not PublicContributionFact
                or type(fact.playbook_id) is not int
                or fact.playbook_id <= 0
                or any(
                    type(getattr(fact, name)) is not str for name in text_field_names
                )
                for fact in evidence.facts
            )
        ):
            raise ValueError("Malformed public evidence snapshot.")
        serialized = json.dumps(
            asdict(evidence), ensure_ascii=False, separators=(",", ":"), sort_keys=True
        )
        logger.info(
            "%s | processing | subject_id=%s fact_count=%s evidence_chars=%s",
            _COLLECT,
            evidence.subject_id,
            len(evidence.facts),
            len(serialized),
        )
        if len(serialized) > MAX_EVIDENCE_CHARACTERS:
            logger.info(
                "%s | error | subject_id=%s reason_code=invalid_snapshot",
                _COLLECT,
                evidence.subject_id,
            )
            raise ValueError("Public evidence exceeds the 24,000-character limit.")
        return evidence
