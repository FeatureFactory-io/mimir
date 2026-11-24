"""Explicit real PostgreSQL service proof; absent opt-in is a reported skip."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from uuid import uuid4

import dj_database_url
import psycopg
import pytest
from django.conf import settings
from django.db import connection
from psycopg import sql

pytestmark = pytest.mark.skipif(
    os.environ.get("EXPERTS_OWNED_PG_TESTS") != "1",
    reason="Real owned PostgreSQL proof requires EXPERTS_OWNED_PG_TESTS=1 and its isolated CI service.",
)

_SETTINGS = """
import os
from pathlib import Path
from mimir.settings.test import *
MIMIR_ENV = "experts_staging"
EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = str(Path(os.environ["EXPERTS_STAGING_SCOPE_ROOT"]) / "mail")
EXPERTS_STAGING_SCOPE_ROOT = Path(os.environ["EXPERTS_STAGING_SCOPE_ROOT"])
"""
_PROBE = """
import json, os
from pathlib import Path
import django
django.setup()
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.contrib.auth.models import User
from methodology.models import ExpertProfile, KarmaAward
from tests.support.experts_data import CedarDatabaseScope, load_cedar_baseline, _resolve_database_scope
root = Path(os.environ["EXPERTS_STAGING_SCOPE_ROOT"])
record = json.loads((root / "owner.json").read_text())
scope = CedarDatabaseScope("owned_staging", os.environ["STAGING_PROBE_DATABASE"], root / "owner.json", os.environ["STAGING_PROBE_OWNER"])
mode = os.environ["STAGING_PROBE_MODE"]
assert "PYTEST_CURRENT_TEST" not in os.environ
assert connection.connection is None
if mode == "wrong_module":
    os.environ["DJANGO_SETTINGS_MODULE"] = "mimir.settings.prod"
if mode == "wrong_mail":
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
if mode == "happy":
    _resolve_database_scope(scope)
    call_command("migrate", interactive=False, verbosity=0)
    data = load_cedar_baseline(scope=scope)
    before = list(KarmaAward.objects.order_by("pk").values())
    load_cedar_baseline(scope=scope)
    assert list(KarmaAward.objects.order_by("pk").values()) == before
    assert User.objects.count() == 12 and KarmaAward.objects.count() == 2129
    assert ExpertProfile.objects.count() == 11
    print(json.dumps({"users":12,"awards":2129,"profiles":11,"real_postgres":connection.vendor == "postgresql","reimport_unchanged":True}))
else:
    try:
        load_cedar_baseline(root / "must-not-read.json", scope=scope)
    except (ValueError, OSError) as error:
        assert not isinstance(error, FileNotFoundError), "Unsafe guard reached fixture read"
        print(json.dumps({"rejected":True,"mode":mode,"connected":connection.connection is not None}))
    else:
        raise AssertionError("Unsafe staging claim was accepted")
connection.close()
"""


@dataclass(frozen=True, repr=False)
class StagingProbe:
    """Fresh dedicated server objects and a credential-private child environment."""

    admin: psycopg.Connection
    name: str
    root: Path
    environment: Mapping[str, str]


def _ci_admin_configuration() -> dict[str, object]:
    """Require the explicitly opted-in existing isolated PostgreSQL service.

    :return: Guarded service settings kept private. Example: {"HOST": "localhost"}.
    :raises ValueError: If the URL identifies any other database or host.
    """
    configured = dj_database_url.parse(os.environ.get("DATABASE_URL", ""))
    if (
        configured.get("ENGINE") != "django.db.backends.postgresql"
        or configured.get("HOST") not in {"localhost", "127.0.0.1", "::1"}
        or configured.get("NAME") != "mimir_test"
        or configured.get("USER") != "huginn"
    ):
        raise ValueError(
            "Owned staging proof requires the isolated huginn/mimir_test CI service."
        )
    return configured


def _create_probe_database(
    admin: psycopg.Connection, name: str, password: str, nonce: str
) -> None:
    """Provision only the random names this fixture just allocated.

    :param admin: Real isolated service connection. Example: an autocommit connection.
    :param name: Nonce-prefixed role/database. Example: experts_cedar_<32hex>.
    :param password: Fresh ephemeral credential. Example: uuid4().hex.
    :param nonce: Public ownership nonce. Example: uuid4().hex.
    :return: None after role/database/comment creation. Example: None.
    """
    admin.execute(
        sql.SQL(
            "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOREPLICATION"
        ).format(sql.Identifier(name), sql.Literal(password))
    )
    admin.execute(
        sql.SQL("CREATE DATABASE {} OWNER {}").format(
            sql.Identifier(name), sql.Identifier(name)
        )
    )
    admin.execute(
        sql.SQL("COMMENT ON DATABASE {} IS {}").format(
            sql.Identifier(name),
            sql.Literal(f"mimir-experts-owned-postgres-v1:{nonce}"),
        )
    )


def _probe_environment(
    root: Path, name: str, password: str, nonce: str, configured: Mapping[str, object]
) -> Mapping[str, str]:
    """Allowlist the isolated child environment without host/provider credentials.

    :param root: Private owner directory. Example: Path("/tmp/probe").
    :param name: Dedicated identity. Example: experts_cedar_<nonce>.
    :param password: Fresh service-local credential. Example: uuid4().hex.
    :param nonce: Public ownership nonce. Example: uuid4().hex.
    :param configured: Guarded CI endpoint. Example: {"HOST": "localhost", "PORT": 5432}.
    :return: Read-only environment mapping. Example: {"DJANGO_SETTINGS_MODULE": "experts_staging_settings"}.
    """
    host = str(configured["HOST"])
    host = f"[{host}]" if ":" in host else host
    return MappingProxyType(
        {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": os.pathsep.join((str(root), str(settings.BASE_DIR))),
            "DJANGO_SETTINGS_MODULE": "experts_staging_settings",
            "MIMIR_ENV": "experts_staging",
            "DATABASE_URL": f"postgresql://{name}:{password}@{host}:{configured.get('PORT') or 5432}/{name}",
            "EXPERTS_STAGING_SCOPE_ROOT": str(root),
            "STAGING_PROBE_DATABASE": name,
            "STAGING_PROBE_OWNER": nonce,
        }
    )


def _write_probe_owner(
    root: Path, name: str, nonce: str, configured: Mapping[str, object]
) -> None:
    """Create the exact private file/runtime contract using no database password.

    :param root: Private real directory. Example: Path("/tmp/probe").
    :param name: Dedicated identity. Example: experts_cedar_<nonce>.
    :param nonce: Public owner nonce. Example: uuid4().hex.
    :param configured: Guarded endpoint. Example: {"HOST": "localhost", "PORT": 5432}.
    :return: None after private files exist. Example: None.
    """
    record = {
        "format": "mimir-experts-owned-postgres-v1",
        "fixture": "CEDAR-RFP-01",
        "owner_id": nonce,
        "database": name,
        "role": name,
        "host": str(configured["HOST"]),
        "port": str(configured.get("PORT") or 5432),
    }
    for filename, content in (
        ("owner.json", json.dumps(record)),
        ("experts_staging_settings.py", _SETTINGS),
    ):
        target = root / filename
        target.touch(mode=0o600)
        target.write_text(content, encoding="utf-8")


@pytest.fixture
def staging_probe(tmp_path: Path) -> Iterator[StagingProbe]:
    """Create/drop one actual fresh nonprivileged role/database per test.

    :param tmp_path: Real private fixture directory. Example: Path("/tmp/probe").
    :return: Real service-owned isolated probe. Example: StagingProbe(...).
    """
    configured, nonce, password = _ci_admin_configuration(), uuid4().hex, uuid4().hex
    name, root = f"experts_cedar_{nonce}", tmp_path.resolve()
    root.chmod(0o700)
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user")
        original_runner = cursor.fetchone()
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as admin:
        try:
            _create_probe_database(admin, name, password, nonce)
            _write_probe_owner(root, name, nonce, configured)
            yield StagingProbe(
                admin,
                name,
                root,
                _probe_environment(root, name, password, nonce, configured),
            )
        finally:
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                    sql.Identifier(name)
                )
            )
            admin.execute(
                sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(name))
            )
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database(), current_user")
                assert cursor.fetchone() == original_runner


def _run_probe(probe: StagingProbe, mode: str) -> dict[str, object]:
    """Run the real Django importer outside pytest using only dedicated credentials.

    :param probe: Actual isolated service objects. Example: StagingProbe(...).
    :param mode: Positive/negative lane. Example: "happy".
    :return: Last child JSON record. Example: {"rejected": True}.
    """
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=settings.BASE_DIR,
        env={**probe.environment, "STAGING_PROBE_MODE": mode},
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    return json.loads(result.stdout.splitlines()[-1])


def test_owned_postgres_scope_with_real_fresh_database_imports_exact_cedar(
    staging_probe: StagingProbe,
) -> None:
    """Prove live ownership, migrations and full import with no pytest-scope claim.

    :param staging_probe: Actual freshly owned PostgreSQL database. Example: StagingProbe(...).
    :return: None after positive proof. Example: None.
    """
    assert _run_probe(staging_probe, "happy") == {
        "users": 12,
        "awards": 2129,
        "profiles": 11,
        "real_postgres": True,
        "reimport_unchanged": True,
    }


def _alter_real_claim(probe: StagingProbe, fault: str) -> None:
    """Mutate genuine owner files/database metadata for negative controls.

    :param probe: Actual isolated database. Example: StagingProbe(...).
    :param fault: Specific independent defect. Example: "wrong_comment".
    :return: None after the real mutation. Example: None.
    """
    marker = probe.root / "owner.json"
    if fault == "wrong_comment":
        probe.admin.execute(
            sql.SQL("COMMENT ON DATABASE {} IS 'wrong-owner'").format(
                sql.Identifier(probe.name)
            )
        )
    elif fault == "wrong_owner":
        probe.admin.execute(
            sql.SQL("ALTER DATABASE {} OWNER TO huginn").format(
                sql.Identifier(probe.name)
            )
        )
    elif fault == "elevated_role":
        probe.admin.execute(
            sql.SQL("ALTER ROLE {} CREATEDB").format(sql.Identifier(probe.name))
        )
    elif fault == "wrong_manifest":
        record = json.loads(marker.read_text())
        marker.write_text(json.dumps({**record, "fixture": "wrong"}))
    elif fault == "public_file":
        marker.chmod(0o644)
    elif fault == "public_parent":
        probe.root.chmod(0o755)


@pytest.mark.parametrize(
    "fault",
    [
        "wrong_comment",
        "wrong_owner",
        "elevated_role",
        "wrong_manifest",
        "public_file",
        "public_parent",
        "wrong_module",
        "wrong_mail",
    ],
)
def test_owned_postgres_scope_with_actual_unsafe_claim_rejects_before_fixture_read(
    staging_probe: StagingProbe, fault: str
) -> None:
    """Reject real unsafe claims before migration or a nonexistent fixture read.

    :param staging_probe: Actual fresh database. Example: StagingProbe(...).
    :param fault: Concrete file/runtime/server fault. Example: "elevated_role".
    :return: None after unchanged-schema rejection. Example: None.
    """
    _alter_real_claim(staging_probe, fault)
    result = _run_probe(staging_probe, fault)
    assert result["rejected"] is True and result["mode"] == fault
    with psycopg.connect(staging_probe.environment["DATABASE_URL"]) as owned:
        assert owned.execute(
            "SELECT count(*) FROM pg_tables WHERE schemaname='public'"
        ).fetchone() == (0,)
