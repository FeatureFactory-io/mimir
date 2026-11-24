"""Real database import and independent-oracle reconciliation."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import User
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from accounts.models import UserEmailVerification
from methodology.models import (
    EventChannel,
    ExpertProfile,
    KarmaAward,
    PipChange,
    Playbook,
    PlaybookVersion,
    ProcessImprovementProposal,
    VersionSource,
)
from methodology.services.expert_text import format_numeric_fallback
from methodology.services.experts_service import ExpertsService
from tests.support import experts_data
from tests.support.experts_data import (
    CEDAR_PASSWORD,
    CedarBaseline,
    CedarDatabaseScope,
    CedarDataset,
    load_cedar_baseline,
)

pytestmark = pytest.mark.django_db
SOURCE = Path(__file__).resolve().parents[2] / "test-data/experts/cedar-rfp-01.json"


def test_load_cedar_baseline_with_historical_rows_reconciles_oracle(
    cedar_baseline: CedarBaseline, cedar_dataset: CedarDataset
) -> None:
    """Reconcile persisted award arithmetic against the independent oracle."""
    assert cedar_baseline is cedar_dataset
    assert len(cedar_dataset.users_by_username) == 12
    service = ExpertsService()
    for person in cedar_dataset.oracle["people"]:
        projection = service.project_user(cedar_dataset.user_ids[person["username"]])
        assert projection.total_points == person["total_karma"]
        assert dict(projection.category_points) == {
            label.lower(): points
            for label, points in person["karma_by_category"].items()
        }
        assert dict(projection.source_points) == person["karma_by_source"]
        assert projection.primary_category == (
            person["primary_category"].lower() if person["primary_category"] else None
        )
    assert not KarmaAward.objects.filter(
        recipient_id=cedar_dataset.user_ids["nberg"]
    ).exists()


def test_load_cedar_baseline_with_second_load_preserves_awards(
    cedar_baseline: CedarBaseline,
) -> None:
    """Preserve award payloads, IDs and unrelated objects through repeated loads."""
    unrelated = User.objects.create_user(username="unrelated")
    before = list(KarmaAward.objects.order_by("pk").values())
    again = load_cedar_baseline()
    assert len(before) > 470
    assert again.user_ids == cedar_baseline.user_ids
    assert list(KarmaAward.objects.order_by("pk").values()) == before
    assert User.objects.filter(pk=unrelated.pk, username="unrelated").exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("count", -1),
        ("count", True),
        ("points", 3),
        ("points_each", 3),
        ("event", "invented"),
        ("category", "invented"),
    ],
)
def test_load_cedar_baseline_with_invalid_ledger_rejects_before_writes(
    tmp_path: Path, field: str, value: object
) -> None:
    """Reject malformed source data without even attempting database mutations."""
    document = json.loads(SOURCE.read_text(encoding="utf-8"))
    document["people"][0]["ledger"][0][field] = value
    fixture_path = tmp_path / SOURCE.name
    fixture_path.write_text(json.dumps(document), encoding="utf-8")
    with CaptureQueriesContext(connection) as queries, pytest.raises(ValueError):
        load_cedar_baseline(fixture_path)
    assert not any(
        query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for query in queries
    )


def test_load_cedar_baseline_with_release_rows_uses_canonical_playbook_identity(
    cedar_baseline: CedarDataset,
) -> None:
    """Bind each declared release to the real current playbook."""
    released = {
        book.pk: book.author_id
        for book in cedar_baseline.playbooks_by_pk.values()
        if book.status == "released"
    }
    awards = KarmaAward.objects.filter(
        source_kind=KarmaAward.SourceKind.RELEASE,
        playbook_id_snapshot__isnull=False,
    )
    assert len(released) == 11
    assert {
        award.playbook_id_snapshot: (award.recipient_id, award.event_identity)
        for award in awards
    } == {
        book_pk: (author_id, f"first_release:{book_pk}")
        for book_pk, author_id in released.items()
    }
    assert awards.count() == len(released)


def test_load_cedar_baseline_with_released_books_imports_version_history(
    cedar_baseline: CedarDataset,
) -> None:
    """Reconcile current rows and version receipts with real accepted change records."""
    maria = cedar_baseline.playbooks_by_pk[6101]
    assert list(maria.versions.values_list("version_number", "source")) == [
        (Decimal("1.0"), VersionSource.RELEASE)
    ]
    workflow = maria.workflows.get()
    assert workflow.name == "Lead an Accessibility Review"
    assert list(
        workflow.activities.order_by("order").values_list("name", flat=True)
    ) == [
        "Trace Keyboard Focus",
        "Review Form Feedback",
        "Document Recovery Paths",
    ]
    for book_pk, historical_key, expected_points in (
        (6106, "HIST-MARIA-DESIGN-01", [500, 100]),
        (6201, "HIST-MARIA-DEV-01", [500, 500]),
    ):
        book = cedar_baseline.playbooks_by_pk[book_pk]
        published, release = book.versions.all()
        pip = cedar_baseline.pips_by_key[historical_key]
        assert book.version == published.version_number == Decimal("2.0")
        assert (
            published.source == VersionSource.PIP_SOURCE and published.pip_id == pip.pk
        )
        assert pip.status == ProcessImprovementProposal.STATUS_ACCEPTED
        assert pip.created_by_id == cedar_baseline.user_ids["mrodriguez"]
        assert (
            release.source == VersionSource.RELEASE
            and release.version_number == Decimal("1.0")
        )
        assert release.pip_id is None and not release.snapshot_data.get("workflows")
        changes = list(pip.changes.order_by("order"))
        assert len(changes) == len(expected_points)
        assert published.snapshot_data["accepted_change_ids"] == [
            change.pk for change in changes
        ]
        for change, points in zip(changes, expected_points, strict=True):
            assert change.admin_decision == PipChange.ADMIN_ACCEPT
            assert change.target_id and change.parent_workflow.playbook_id == book_pk
            assert change.parent_workflow.name == book.name
            award = KarmaAward.objects.get(change_id_snapshot=change.pk)
            assert award.playbook_id_snapshot == book_pk and award.points == points
            assert award.entity_id_snapshot == change.target_id
            assert award.entity_type_snapshot == change.entity_type
            assert award.category == book.category
            assert award.event_identity == f"accepted_change:{change.pk}"
            assert award.event_channel == EventChannel.ACCEPTED_CHANGE
            assert award.occurred_at == pip.decided_at


def test_load_cedar_baseline_with_second_load_preserves_release_history(
    cedar_baseline: CedarDataset,
) -> None:
    """Keep receipts and accepted changes identical on repeat import."""
    versions = list(
        PlaybookVersion.objects.filter(
            playbook_id__in=cedar_baseline.playbook_ids.values()
        )
        .order_by("pk")
        .values()
    )
    changes = list(PipChange.objects.order_by("pk").values())
    assert versions and len(changes) == 4
    again = load_cedar_baseline()
    assert again.playbook_ids == cedar_baseline.playbook_ids
    assert (
        list(
            PlaybookVersion.objects.filter(playbook_id__in=again.playbook_ids.values())
            .order_by("pk")
            .values()
        )
        == versions
    )
    assert list(PipChange.objects.order_by("pk").values()) == changes


def test_load_cedar_baseline_with_gui_subset_preserves_47_of_470(
    cedar_baseline: CedarDataset,
) -> None:
    """Separate explicit GUI author rows from the larger historical cohort."""
    mike = cedar_baseline.users_by_username["mchen"]
    awards = KarmaAward.objects.filter(
        recipient=mike, source_kind=KarmaAward.SourceKind.CONSUMPTION
    )
    assert awards.count() == 470
    assert awards.filter(event_channel=EventChannel.GUI_COPY).count() == 47
    assert awards.filter(event_channel=EventChannel.HISTORICAL).count() == 423
    assert ExpertProfile.objects.get(user=mike).contribution_summary == ""
    projection = ExpertsService().project_user(mike.pk)
    assert (
        format_numeric_fallback(
            projection.released_public_playbook_count,
            projection.successful_gui_copy_count,
        )
        == "2 released playbooks · 47 copies"
    )


def test_load_cedar_baseline_with_unknown_history_does_not_invent_public_books(
    cedar_baseline: CedarDataset,
) -> None:
    """Keep unknown references nullable and preserve only declared public releases."""
    for person in cedar_baseline.oracle["people"]:
        assert set(
            Playbook.objects.filter(
                author_id=cedar_baseline.user_ids[person["username"]],
                status="released",
                visibility="public",
            ).values_list("pk", flat=True)
        ) == {book["pk"] for book in person["public_playbooks"]}
    residual = KarmaAward.objects.filter(
        recipient_id=cedar_baseline.user_ids["sreed"],
        source_kind=KarmaAward.SourceKind.MAJOR,
    )
    assert residual.count() == 6
    assert not residual.exclude(
        playbook_id_snapshot=None,
        change_id_snapshot=None,
        entity_type_snapshot=None,
        entity_id_snapshot=None,
    ).exists()
    assert cedar_baseline.activities_by_pk[6203].workflow_id == 6202
    assert cedar_baseline.workflows_by_pk[6202].playbook_id == 6201
    assert not User.objects.filter(username__in=("bcarter", "nibrahim")).exists()


@pytest.mark.parametrize("filename", ["mimir.db", "mimir.dev.db", "idle.db", "prod.db"])
def test_load_cedar_baseline_with_ambient_database_rejects_before_writes(
    tmp_path: Path, filename: str
) -> None:
    """Reject a file-backed effective configuration even with an explicit test claim."""
    ambient_path = tmp_path / filename
    scope = CedarDatabaseScope("test", str(ambient_path))
    original_name = connection.settings_dict["NAME"]
    with CaptureQueriesContext(connection) as queries:
        connection.settings_dict["NAME"] = ambient_path
        try:
            with pytest.raises(ValueError, match="database"):
                load_cedar_baseline(scope=scope)
        finally:
            connection.settings_dict["NAME"] = original_name
    assert len(queries) == 0
    assert not ambient_path.exists()


def test_load_cedar_baseline_with_verified_accounts_supports_real_login(
    client: Client,
    cedar_baseline: CedarDataset,
) -> None:
    """Use the real verification state and existing login form."""
    elena = cedar_baseline.users_by_username["esvensson"]
    assert UserEmailVerification.objects.get(user=elena).is_verified
    response = client.post(
        "/auth/user/login/", {"username": elena.username, "password": CEDAR_PASSWORD}
    )
    assert response.status_code == 302
    assert client.session[SESSION_KEY] == str(elena.pk)


def test_load_cedar_baseline_with_existing_playbook_conflict_rolls_back() -> None:
    """Protect a preexisting book and roll back new accounts on a late identity conflict."""
    owner = User.objects.create_user(username="unrelated")
    Playbook.objects.create(
        pk=6101, author=owner, name="Unrelated Book", category="design"
    )
    with pytest.raises(ValueError, match="conflict"):
        load_cedar_baseline()
    assert Playbook.objects.get(pk=6101).author_id == owner.pk
    assert not User.objects.filter(username="esvensson").exists()
    assert not KarmaAward.objects.exists()


@pytest.mark.parametrize(
    ("target_name", "target_host", "worker", "expected"),
    [
        ("test_mimir_test", "localhost", None, True),
        ("test_mimir_test_gw3", "localhost", "gw3", True),
        ("mimir_test", "localhost", None, False),
        ("test_other", "localhost", None, False),
        ("test_mimir_test", "other-host", None, False),
        ("test_mimir_test", "remote-host", None, False),
        ("test_mimir_test_gw4", "localhost", "gw3", False),
    ],
)
def test_cedar_postgres_settings_with_runner_identity_verifies_ownership(
    target_name: str,
    target_host: str,
    worker: str | None,
    expected: bool,
) -> None:
    """Recognize only the local test database that Django derives for its runner."""
    configured_host = target_host if target_host == "remote-host" else "localhost"
    configured = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "mimir_test",
        "HOST": configured_host,
        "PORT": 5432,
        "USER": "ci",
    }
    actual = {**configured, "NAME": target_name, "HOST": target_host, "PORT": "5432"}
    assert (
        experts_data._postgres_test_settings_match(actual, configured, worker)
        is expected
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("model_name", "consumed"),
    [("Activity", 6202), ("Activity", 9000), ("Workflow", 6201), ("Playbook", 6100)],
)
def test_load_cedar_baseline_with_postgres_reserved_boundary_preserves_sequence(
    model_name: str, consumed: int
) -> None:
    """Reserve fixed oracle IDs without reusing previously consumed sequence values."""
    if connection.vendor != "postgresql":
        pytest.skip("Requires the actual owned PostgreSQL runner.")
    model = getattr(experts_data, model_name)
    sequence = _set_owned_test_sequence(model, consumed)
    data = load_cedar_baseline()
    assert data.activities_by_pk[6203].pk == 6203
    before = list(KarmaAward.objects.order_by("pk").values())
    again = load_cedar_baseline()
    assert again.user_ids == data.user_ids
    assert list(KarmaAward.objects.order_by("pk").values()) == before
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval(%s::regclass)", [sequence])
        assert cursor.fetchone()[0] > consumed


@pytest.mark.django_db(transaction=True)
def test_load_cedar_baseline_with_postgres_pathological_gap_rejects_before_rows(
    tmp_path: Path,
) -> None:
    """A valid-looking huge reserved ID cannot create unbounded sequence work."""
    if connection.vendor != "postgresql":
        pytest.skip("Requires the actual owned PostgreSQL runner.")
    document = json.loads(SOURCE.read_text())
    person = next(row for row in document["people"] if row["username"] == "mchen")
    person["public_playbooks"][0]["workflow_pk"] = 10**12
    source = tmp_path / SOURCE.name
    source.write_text(json.dumps(document))
    with (
        CaptureQueriesContext(connection) as queries,
        pytest.raises(ValueError, match="sequence reservation"),
    ):
        load_cedar_baseline(source)
    assert not any(
        query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for query in queries
    )


@pytest.mark.django_db(transaction=True)
def test_load_cedar_baseline_with_postgres_conflicting_reserved_row_preserves_row() -> (
    None
):
    """Sequence preparation cannot overwrite an unexpected preexisting Cedar row."""
    if connection.vendor != "postgresql":
        pytest.skip("Requires the actual owned PostgreSQL runner.")
    owner = User.objects.create_user(username="existing-owner")
    book = Playbook.objects.create(
        pk=6201, author=owner, name="Existing private work", visibility="private"
    )
    _set_owned_test_sequence(Playbook, 9000)
    users_before = User.objects.count()
    with pytest.raises(ValueError, match="conflict"):
        load_cedar_baseline()
    book.refresh_from_db()
    assert book.name == "Existing private work" and book.author_id == owner.pk
    assert User.objects.count() == users_before and KarmaAward.objects.count() == 0


def _set_owned_test_sequence(model: type, consumed: int) -> str:
    """Create a real counterexample only inside the actual test-owned PG runner.

    :param model: Declared mixed-ID model. Example: Activity.
    :param consumed: Controlled consumed fixture value. Example:6202.
    :return: Actual model sequence name. Example: methodology_activity_id_seq.
    :raises AssertionError: The connection does not identify its owned test DB.
    """
    assert connection.vendor == "postgresql"
    assert connection.settings_dict["NAME"].startswith("test_")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_get_serial_sequence(%s,%s)",
            [model._meta.db_table, model._meta.pk.column],
        )
        sequence = cursor.fetchone()[0]
        cursor.execute("SELECT setval(%s::regclass,%s,true)", [sequence, consumed])
    return sequence
