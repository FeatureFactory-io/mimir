"""Pure namespace and real filesystem proofs for explicit staging ownership."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from django.conf import settings
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

from tests.support import experts_data
from tests.support.experts_data import CedarDatabaseScope

NONCE = "ab" * 16
NAME = f"experts_cedar_{NONCE}"


def _scope(marker: Path | None = None) -> CedarDatabaseScope:
    """Build one explicit nonsecret staging claim.

    :param marker: Optional private marker. Example: Path("/scope/owner.json").
    :return: Nonce-specific claim. Example: a CedarDatabaseScope.
    """
    return CedarDatabaseScope("owned_staging", NAME, marker, NONCE)


def _connection_settings() -> dict[str, object]:
    """Describe the dedicated endpoint without opening a connection.

    :return: Nonsecret configured identity. Example: {"HOST": "cedar-db"}.
    """
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": NAME,
        "USER": NAME,
        "HOST": "cedar-db",
        "PORT": "5432",
    }


def _manifest() -> dict[str, str]:
    """Return the exact independently expected ownership document.

    :return: Public marker fields. Example: {"fixture": "CEDAR-RFP-01"}.
    """
    return {
        "format": "mimir-experts-owned-postgres-v1",
        "fixture": "CEDAR-RFP-01",
        "owner_id": NONCE,
        "database": NAME,
        "role": NAME,
        "host": "cedar-db",
        "port": "5432",
    }


@pytest.mark.parametrize("host", ["cedar-db", "localhost", "127.0.0.1", "::1"])
def test_staging_manifest_with_dedicated_identity_matches_exact_endpoint(
    host: str,
) -> None:
    """Accept each explicitly supported private-network/loopback endpoint.

    :param host: Configured permitted host. Example: "cedar-db".
    :return: None after assertion. Example: None.
    """
    actual = _connection_settings()
    actual["HOST"] = host
    assert experts_data._staging_expected_manifest(_scope(), actual) == {
        **_manifest(),
        "host": host,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ENGINE", "django.db.backends.sqlite3"),
        ("NAME", "mimir"),
        ("USER", "postgres"),
        ("HOST", "mimir-prod.example.com"),
        ("HOST", ["cedar-db"]),
        ("PORT", "0"),
        ("PORT", "65536"),
        ("PORT", True),
        ("PORT", "5432;DROP"),
    ],
)
def test_staging_manifest_with_unsafe_connection_rejects_before_sql(
    field: str, value: object
) -> None:
    """Reject ambient namespaces and malformed endpoints using only values.

    :param field: Setting to corrupt. Example: "USER".
    :param value: Unsafe value. Example: "postgres".
    :return: None after the rejection. Example: None.
    """
    actual = _connection_settings()
    actual[field] = value
    with pytest.raises(ValueError):
        experts_data._staging_expected_manifest(_scope(), actual)


@pytest.mark.parametrize("nonce", [None, "", "a" * 31, "A" * 32, "../" * 11])
def test_staging_manifest_with_invalid_nonce_rejects_before_sql(
    nonce: str | None,
) -> None:
    """Require exactly32 lower-case hex digits for the dedicated namespace.

    :param nonce: Invalid owner. Example: "".
    :return: None after rejection. Example: None.
    """
    with pytest.raises(ValueError):
        experts_data._staging_expected_manifest(
            replace(_scope(), owner_id=nonce), _connection_settings()
        )


@pytest.fixture
def private_marker(tmp_path: Path) -> Iterator[Path]:
    """Create a real current-user private marker outside the checkout.

    :param tmp_path: Runner-owned temporary directory. Example: Path("/tmp/case").
    :return: Real private marker path. Example: tmp_path / "owner.json".
    """
    root = tmp_path.resolve()
    root.chmod(0o700)
    marker = root / "owner.json"
    marker.touch(mode=0o600)
    marker.write_text(json.dumps(_manifest()), encoding="utf-8")
    with override_settings(EXPERTS_STAGING_SCOPE_ROOT=root):
        yield marker


def test_staging_marker_with_private_real_file_reads_exact_record(
    private_marker: Path,
) -> None:
    """Read the current user's real private file with no connection activity.

    :param private_marker: Real file. Example: Path("/tmp/case/owner.json").
    :return: None after assertions. Example: None.
    """
    assert experts_data._staging_manifest_path(_scope(private_marker)) == private_marker
    assert experts_data._read_private_staging_manifest(private_marker) == _manifest()


@pytest.mark.parametrize(
    "fault", ["public_parent", "wrong_name", "missing_claim", "symlink_root"]
)
def test_staging_marker_with_unsafe_path_rejects_before_sql(
    private_marker: Path, fault: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject unsafe directory/path claims before any database connection.

    :param private_marker: Original real file. Example: Path("/tmp/case/owner.json").
    :param fault: Concrete path defect. Example: "public_parent".
    :param monkeypatch: Runtime setting scope. Example: pytest's fixture.
    :return: None after rejection. Example: None.
    """
    marker = private_marker
    if fault == "public_parent":
        marker.parent.chmod(0o755)
    elif fault == "wrong_name":
        marker = marker.with_name("different.json")
    elif fault == "missing_claim":
        marker = None
    else:
        link = private_marker.parent.with_name(private_marker.parent.name + "-link")
        link.symlink_to(private_marker.parent, target_is_directory=True)
        monkeypatch.setattr(settings, "EXPERTS_STAGING_SCOPE_ROOT", link)
        marker = link / "owner.json"
    with pytest.raises(ValueError):
        experts_data._staging_manifest_path(_scope(marker))


@pytest.mark.parametrize(
    "fault", ["public_file", "hardlink", "symlink", "fifo", "oversize", "malformed"]
)
def test_staging_marker_with_unsafe_file_rejects_without_following_target(
    private_marker: Path, fault: str
) -> None:
    """Exercise actual file modes, links, bounded reads and JSON decoding.

    :param private_marker: Original real file. Example: Path("/tmp/case/owner.json").
    :param fault: Concrete file defect. Example: "symlink".
    :return: None after rejection. Example: None.
    """
    marker = private_marker
    if fault == "public_file":
        marker.chmod(0o644)
    elif fault == "hardlink":
        os.link(marker, marker.with_name("hardlink.json"))
    elif fault == "symlink":
        marker = marker.with_name("link.json")
        marker.symlink_to(private_marker)
    elif fault == "fifo":
        marker = marker.with_name("pipe.json")
        os.mkfifo(marker, 0o600)
    elif fault == "oversize":
        marker.write_text(" " * 4097, encoding="utf-8")
    else:
        marker.write_text("{", encoding="utf-8")
    with pytest.raises((ValueError, OSError)):
        experts_data._read_private_staging_manifest(marker)


def _identity_row() -> tuple[object, ...]:
    """Describe the real PostgreSQL row expected from the dedicated LOGIN role.

    :return: Complete identity/capability row. Example: (NAME, NAME, NAME, NAME, marker, ...).
    """
    return (
        NAME,
        NAME,
        NAME,
        NAME,
        f"mimir-experts-owned-postgres-v1:{NONCE}",
        False,
        False,
        False,
        False,
        False,
        True,
    )


def test_staging_identity_with_all_owned_fields_matches() -> None:
    """Accept only a complete server identity with no elevated role capability.

    :return: None after assertion. Example: None.
    """
    assert experts_data._staging_identity_matches(_manifest(), _identity_row())


@pytest.mark.parametrize("index", range(11))
def test_staging_identity_with_each_wrong_field_rejects(index: int) -> None:
    """Protect every actual server field, including unchanged database counts.

    :param index: Actual server column to alter. Example: 5 for SUPERUSER.
    :return: None after assertion. Example: None.
    """
    row = list(_identity_row())
    row[index] = not row[index] if isinstance(row[index], bool) else "wrong"
    assert not experts_data._staging_identity_matches(_manifest(), row)


@pytest.mark.parametrize("row", [None, (), (NAME,), _identity_row()[:-1]])
def test_staging_identity_with_missing_row_rejects(
    row: tuple[object, ...] | None,
) -> None:
    """Reject missing or truncated results without accepting partial evidence.

    :param row: Incomplete SQL result. Example: None.
    :return: None after assertion. Example: None.
    """
    assert not experts_data._staging_identity_matches(_manifest(), row)


@pytest.mark.parametrize("fault", ["module", "environment", "mail"])
def test_staging_runtime_with_wrong_configuration_rejects_before_sql(
    fault: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject inherited application runtime/mail before any ownership query.

    :param fault: Runtime condition to alter. Example: "mail".
    :param monkeypatch: Scoped environment setter. Example: pytest's fixture.
    :return: None after rejection and zero SQL. Example: None.
    """
    module = "mimir.settings.prod" if fault == "module" else "experts_staging_settings"
    environment = "prod" if fault == "environment" else "experts_staging"
    mail = (
        "smtp"
        if fault == "mail"
        else "django.core.mail.backends.filebased.EmailBackend"
    )
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", module)
    with (
        override_settings(MIMIR_ENV=environment, EMAIL_BACKEND=mail),
        CaptureQueriesContext(connection) as queries,
        pytest.raises(ValueError, match="isolated runtime"),
    ):
        experts_data._validate_owned_postgres_staging(_scope())
    assert len(queries) == 0


def test_staging_marker_with_directory_inside_checkout_rejects(
    private_marker: Path,
) -> None:
    """Reject even a private correctly named marker inside application source.

    :param private_marker: Real marker. Example: Path("/tmp/case/owner.json").
    :return: None after rejection. Example: None.
    """
    with (
        override_settings(BASE_DIR=private_marker.parent.parent),
        pytest.raises(ValueError),
    ):
        experts_data._staging_manifest_path(_scope(private_marker))


@pytest.mark.parametrize("index", range(5, 11))
def test_staging_identity_with_numeric_capability_rejects(index: int) -> None:
    """Require genuine PostgreSQL booleans rather than equal numeric values.

    :param index: Capability column. Example: 5 for SUPERUSER.
    :return: None after assertion. Example: None.
    """
    row = list(_identity_row())
    row[index] = int(row[index])
    assert not experts_data._staging_identity_matches(_manifest(), row)
