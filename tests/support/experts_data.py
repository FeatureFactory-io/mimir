"""Real Cedar ORM history import for isolated test or ownership-verified demo DBs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Mapping, Sequence
from django.contrib.auth.models import User
from methodology.models import (
    Activity,
    Playbook,
    PlaybookVersion,
    ProcessImprovementProposal,
    Workflow,
)

CEDAR_PASSWORD = "Cedar-fictional-tests-only-2026"
CEDAR_BASELINE_TIME_ISO = "2026-11-22T00:00:00+00:00"


@dataclass(frozen=True)
class CedarDatabaseScope:
    """Expected database identity plus optional local-demo ownership evidence."""

    kind: Literal["test", "owned_demo"]
    database_name: str
    ownership_manifest: Path | None = None
    owner_id: str | None = None


@dataclass(frozen=True)
class CedarDataset:
    """Real object maps and unchanged independent JSON oracle."""

    users_by_username: Mapping[str, User]
    playbooks_by_pk: Mapping[int, Playbook]
    oracle: Mapping[str, object]
    workflows_by_pk: Mapping[int, Workflow] = field(default_factory=dict)
    activities_by_pk: Mapping[int, Activity] = field(default_factory=dict)
    pips_by_key: Mapping[str, ProcessImprovementProposal] = field(default_factory=dict)

    @property
    def user_ids(self) -> Mapping[str, int]:
        """Expose compatibility IDs for existing planned consumers.

        :return: Username-to-real-PK mapping. Example: {"mrodriguez": 42}.
        :raises ValueError: If an imported user is unsaved.
        """
        raise NotImplementedError()

    @property
    def playbook_ids(self) -> Mapping[int, int]:
        """Expose oracle-book-PK to actual-book-PK compatibility mapping.

        :return: Book identity mapping. Example: {6101: 6101}.
        :raises ValueError: If an imported book is unsaved.
        """
        raise NotImplementedError()


CedarBaseline = CedarDataset


@dataclass(frozen=True)
class HistoricalAward:
    """Fully normalized direct-import row; unknown content snapshots stay null."""

    recipient_id: int
    event_identity: str
    source_kind: str
    event_channel: str
    points: int
    category: str
    playbook_id_snapshot: int | None
    change_id_snapshot: int | None
    entity_type_snapshot: str | None
    entity_id_snapshot: int | None
    occurred_at: datetime


def load_cedar_baseline(
    fixture_path: Path | None = None, *, scope: CedarDatabaseScope | None = None
) -> CedarDataset:
    """Validate and atomically import real baseline objects without live hooks.

    :param fixture_path: Optional domain source. Example: Path("cedar-rfp-01.json").
    :param scope: Explicit ownership evidence or inferred runner scope. Example: None.
    :return: Real imported objects and oracle. Example: a CedarDataset.
    :raises ValueError: For unsafe scope, conflicts or inconsistent oracle data.
    :raises OSError: If the supplied fixture/ownership evidence cannot be read.
    """
    raise NotImplementedError()


def _resolve_database_scope(scope: CedarDatabaseScope | None) -> CedarDatabaseScope:
    """Accept verified runner isolation or explicitly evidenced demo ownership.

    :param scope: Optional caller ownership evidence. Example: None.
    :return: Checked effective scope. Example: an in-memory test scope.
    :raises ValueError: If no safe database ownership can be established.
    """
    raise NotImplementedError()


def _validate_database_scope(scope: CedarDatabaseScope) -> None:
    """Match actual connection/settings/path against the claimed owned database.

    :param scope: Resolved ownership claim. Example: a runner-owned test scope.
    :return: None. Example: None.
    :raises ValueError: For ambient dev, tracked seed, idle or production databases.
    """
    raise NotImplementedError()


def _read_cedar_document(fixture_path: Path | None) -> dict[str, object]:
    """Read the domain contract without treating it as a loaddata fixture.

    :param fixture_path: Optional explicit source. Example: Path("cedar.json").
    :return: Parsed document. Example: {"people": []}.
    :raises ValueError: For malformed JSON/document structure.
    :raises OSError: If the file cannot be read.
    """
    raise NotImplementedError()


def _validate_cedar_document(document: Mapping[str, object]) -> None:
    """Validate identities, categories, counts, unit arithmetic and oracle totals.

    :param document: Independent source document. Example: {"people": []}.
    :return: None. Example: None.
    :raises ValueError: For invalid values or inconsistent totals/history.
    """
    raise NotImplementedError()


def _baseline_time() -> datetime:
    """Return the deterministic aware historical fixture timestamp.

    :return: Original import event time. Example: 2026-11-22T00:00:00+00:00.
    :raises ValueError: If the configured fixture timestamp is invalid.
    """
    raise NotImplementedError()


def _create_cedar_users(document: Mapping[str, object]) -> dict[str, User]:
    """Create real named accounts, preserving declared staff flags and identities.

    :param document: Validated oracle. Example: {"people": []}.
    :return: Actual users keyed by username. Example: {"mchen": a User}.
    :raises ValueError: For conflicting unrelated account ownership.
    """
    raise NotImplementedError()


def _verify_cedar_user_email(user: User) -> None:
    """Use existing real verification state so browser login is functional.

    :param user: Imported account. Example: User(username="esvensson").
    :return: None. Example: None.
    :raises ValueError: If the user is unsaved or not fixture-owned.
    """
    raise NotImplementedError()


def _create_cedar_playbooks(
    document: Mapping[str, object], users: Mapping[str, User]
) -> dict[int, Playbook]:
    """Create only declared current books with actual category/status/visibility.

    :param document: Validated current-book oracle. Example: {"people": []}.
    :param users: Actual imported authors. Example: {"mchen": a User}.
    :return: Oracle-PK keyed real books. Example: {6201: a Playbook}.
    :raises ValueError: For conflicting identities or missing authors.
    """
    raise NotImplementedError()


def _create_cedar_public_content(
    dataset: CedarDataset,
) -> tuple[dict[int, Workflow], dict[int, Activity]]:
    """Create the explicitly declared public workflows/activities from the contract.

    :param dataset: Imported users/books and oracle. Example: a CedarDataset.
    :return: Actual workflow/activity maps. Example: ({6202: workflow}, {6203: activity}).
    :raises ValueError: For missing parents or conflicting content identities.
    """
    raise NotImplementedError()


def _create_cedar_private_boundaries(dataset: CedarDataset) -> None:
    """Persist specified private book/PIP/token sentinels without public exposure.

    :param dataset: Fixture-owned accounts/books and oracle. Example: a CedarDataset.
    :return: None. Example: None.
    :raises ValueError: For conflicting sentinel ownership or missing parents.
    """
    raise NotImplementedError()


def _create_cedar_historical_pips(
    dataset: CedarDataset,
) -> dict[str, ProcessImprovementProposal]:
    """Create real accepted historical PIPs/changes without decision hooks.

    :param dataset: Imported parents and historical contract. Example: a CedarDataset.
    :return: PIPs keyed by historical ID. Example: {"HIST-MARIA-DESIGN-01": a PIP}.
    :raises ValueError: For mismatched authors, changes or published version facts.
    """
    raise NotImplementedError()


def _publish_cedar_historical_changes(dataset: CedarDataset) -> None:
    """Materialize declared accepted changes in their specified current books.

    :param dataset: Real historical PIPs and public parent content. Example: dataset.
    :return: None. Example: None.
    :raises ValueError: For inconsistent accepted/publication relationships.
    """
    raise NotImplementedError()


def _import_cedar_versions(dataset: CedarDataset) -> None:
    """Persist known release and published-PIP history without award hooks.

    :param dataset: Actual books, PIPs and oracle. Example: a CedarDataset.
    :return: None. Example: None.
    :raises ValueError: For conflicting version source, number or PIP linkage.
    """
    raise NotImplementedError()


def _version_snapshot(
    playbook: Playbook, *, include_current_content: bool
) -> dict[str, object]:
    """Build a real snapshot without inventing unknown historical content.

    :param playbook: Actual imported book. Example: Playbook(pk=6106).
    :param include_current_content: Whether current published content applies.
        Example: True for the known current v2.0.
    :return: Explicitly supported snapshot fields. Example: {"name": "Accessible Forms Review"}.
    :raises ValueError: For an unsaved book or unsupported historical reconstruction.
    """
    raise NotImplementedError()


def _store_cedar_version(
    playbook: Playbook,
    version_number: str,
    source: str,
    pip: ProcessImprovementProposal | None,
    snapshot: Mapping[str, object],
) -> PlaybookVersion:
    """Insert or verify one real unique book/version receipt.

    :param playbook: Imported real book. Example: Playbook(pk=6106).
    :param version_number: Known decimal version. Example: "2.0".
    :param source: Existing VersionSource value. Example: "pip".
    :param pip: Actual producing PIP, if known. Example: an accepted PIP.
    :param snapshot: Supported version content. Example: {"name": "Accessible Forms Review"}.
    :return: Persisted matching version. Example: PlaybookVersion(version_number=2).
    :raises ValueError: For conflicting or unsupported history.
    """
    raise NotImplementedError()


def _import_cedar_profiles(dataset: CedarDataset) -> None:
    """Store supplied public prose, normalizing JSON null to empty text.

    :param dataset: Actual fixture accounts and oracle. Example: a CedarDataset.
    :return: None. Example: None.
    :raises ValueError: For conflicting profile ownership or malformed prose.
    """
    raise NotImplementedError()


def _normalize_cedar_awards(dataset: CedarDataset) -> tuple[HistoricalAward, ...]:
    """Expand count/unit rows and bind only known content/change references.

    :param dataset: Imported identities, history and independent oracle. Example: dataset.
    :return: Deterministic direct-import awards. Example: ().
    :raises ValueError: For inconsistent totals, channels or known references.
    """
    raise NotImplementedError()


def _historical_release_rows(
    dataset: CedarDataset,
    username: str,
    ledger_row: Mapping[str, object],
    row_index: int,
) -> tuple[HistoricalAward, ...]:
    """Bind known releases canonically; retain unknown historical refs as null.

    :param dataset: Actual current books and known history. Example: dataset.
    :param username: Recipient username. Example: "sreed".
    :param ledger_row: Aggregate release row. Example: {"count": 2, "points_each": 5000}.
    :param row_index: Stable source-row position. Example: 0.
    :return: One award per historical release. Example: ().
    :raises ValueError: For incompatible known release bindings or arithmetic.
    """
    raise NotImplementedError()


def _historical_nonrelease_rows(
    dataset: CedarDataset,
    username: str,
    ledger_row: Mapping[str, object],
    row_index: int,
) -> tuple[HistoricalAward, ...]:
    """Expand other historical rows with explicit known GUI-subset attribution.

    :param dataset: Actual objects and oracle. Example: dataset.
    :param username: Recipient. Example: "mchen".
    :param ledger_row: Aggregate source row. Example: {"count": 470, "event": "consumption"}.
    :param row_index: Stable source position. Example: 1.
    :return: Historical awards with exact channel attribution. Example: ().
    :raises ValueError: If declared GUI subset exceeds eligible author events.
    """
    raise NotImplementedError()


def _historical_event_id(username: str, row_index: int, ordinal: int) -> str:
    """Build stable identities for historical events without known release keys.

    :param username: Oracle recipient. Example: "mrodriguez".
    :param row_index: Zero-based source row. Example: 1.
    :param ordinal: Zero-based item within aggregate row. Example: 0.
    :return: Stable identity. Example: "cedar:baseline:mrodriguez:1:0".
    :raises ValueError: For invalid username or negative indices.
    """
    raise NotImplementedError()


def _persist_cedar_awards(awards: Sequence[HistoricalAward]) -> None:
    """Directly insert or verify immutable history without live service hooks.

    :param awards: Validated deterministic historical rows. Example: ().
    :return: None. Example: None.
    :raises ValueError: For conflicting existing logical rows or timestamps.
    """
    raise NotImplementedError()


def _verify_cedar_projection(dataset: CedarDataset) -> None:
    """Independently reconcile real totals, counts, known history and sentinels.

    :param dataset: Complete actual baseline and independent oracle. Example: dataset.
    :return: None. Example: None.
    :raises AssertionError: For any persisted/oracle mismatch.
    """
    raise NotImplementedError()


def seed_s27_summary_privacy_variant() -> Mapping[str, Any]:
    """Extend the real Cedar baseline with independent privacy/publication cases.

    :return: Real ORM rows and expected sentinels. Example: Maria plus draft PIPs.
    :raises ValueError: If baseline/publication receipt invariants do not reconcile.
    """
    raise NotImplementedError()


def create_reviewed_major_add_pip(
    dataset: CedarDataset, entity_type: str
) -> ProcessImprovementProposal:
    """Create an independent real reviewed Maria proposal targeting Hana's v2.0.

    :param dataset: Independently restored Cedar data. Example: load_cedar_baseline().
    :param entity_type: Major ADD entity. Example: "Artifact".
    :return: Real reviewed proposal with one undecided change. Example: ADD Artifact PIP.
    :raises ValueError: For unsupported entity or missing target structure.
    """
    raise NotImplementedError()


def _major_add_change_payload(
    dataset: CedarDataset, entity_type: str
) -> dict[str, object]:
    """Supply real service fields, including parent and producer references.

    :param dataset: Restored Cedar relationships. Example: playbook 6106 and its workflow.
    :param entity_type: Eligible ADD entity. Example: "Activity".
    :return: Existing PIPService.add_change keyword payload. Example: parent_workflow_id.
    :raises ValueError: If a required workflow or producer cannot be resolved.
    """
    raise NotImplementedError()


def create_nonaccepted_pip_case(
    dataset: CedarDataset, status: str
) -> ProcessImprovementProposal:
    """Prepare an explicit eligibility fixture; rejected uses real finalization.

    :param dataset: Real restored Cedar objects. Example: load_cedar_baseline().
    :param status: Exact supported stored state. Example: "processing_galdr".
    :return: Persisted proposal. Example: reviewed PIP targeting playbook 6106.
    :raises ValueError: If status is outside the five contracted states.
    :raises ValidationError: If real creation or rejected finalization fails.
    """
    raise NotImplementedError()
