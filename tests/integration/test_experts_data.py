"""Real database import and independent-oracle reconciliation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from tests.support import experts_data
from tests.support.experts_data import (
    CedarBaseline,
    CedarDatabaseScope,
    CedarDataset,
    load_cedar_baseline,
)

pytestmark = pytest.mark.django_db
SOURCE = Path(__file__).resolve().parents[2] / "test-data/experts/cedar-rfp-01.json"


def test_load_cedar_baseline_with_historical_rows_reconciles_oracle(
    cedar_baseline: CedarBaseline,
) -> None:
    """Prove actual awards reconcile all supplied totals and boundaries.

    :param cedar_baseline: Real imported baseline. Example: CedarBaseline({}, {}, {}).
    :return: None. Example: None.
    :raises AssertionError: For any persisted/oracle mismatch.
    """
    raise NotImplementedError()


def test_load_cedar_baseline_with_second_load_preserves_awards(
    cedar_baseline: CedarBaseline,
) -> None:
    """Prove repeat import does not duplicate history.

    :param cedar_baseline: First import. Example: CedarBaseline({}, {}, {}).
    :return: None. Example: None.
    :raises AssertionError: If repeat import changes totals or award counts.
    """
    raise NotImplementedError()


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
    """Prove baseline release awards use the live canonical identity.

    :param cedar_baseline: Real imported objects. Example: dataset.
    :return: None. Example: None.
    :raises AssertionError: If any release identity differs from first_release:<pk>.
    """
    raise NotImplementedError()


def test_load_cedar_baseline_with_released_books_imports_version_history(
    cedar_baseline: CedarDataset,
) -> None:
    """Prove imported released books have actual persisted version evidence.

    :param cedar_baseline: Real imported objects. Example: dataset.
    :return: None. Example: None.
    :raises AssertionError: If history is missing, duplicated or misclassified.
    """
    raise NotImplementedError()


def test_load_cedar_baseline_with_second_load_preserves_release_history(
    cedar_baseline: CedarDataset,
) -> None:
    """Prove repeated import leaves release awards and version history unchanged.

    :param cedar_baseline: First imported dataset. Example: dataset.
    :return: None. Example: None.
    :raises AssertionError: If history or first-release totals grow.
    """
    raise NotImplementedError()


def test_load_cedar_baseline_with_gui_subset_preserves_47_of_470() -> None:
    """Reconcile Mike 47 GUI author-copy events separately from 470 total author consumption events.

    :return: None on the asserted contract. Example: None.
    :raises AssertionError: The described boundary or actual evidence differs.
    """
    raise NotImplementedError()


def test_load_cedar_baseline_with_unknown_history_does_not_invent_public_books() -> (
    None
):
    """Preserve nullable unknown content and exact declared current public-book counts.

    :return: None on the asserted contract. Example: None.
    :raises AssertionError: The described boundary or actual evidence differs.
    """
    raise NotImplementedError()


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


def test_load_cedar_baseline_with_verified_accounts_supports_real_login() -> None:
    """Import actual existing email-verification state for the real login lifecycle.

    :return: None on the asserted contract. Example: None.
    :raises AssertionError: The described boundary or actual evidence differs.
    """
    raise NotImplementedError()


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
