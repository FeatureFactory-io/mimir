"""Real Cedar ORM history import for isolated test or ownership-verified demo DBs."""

from __future__ import annotations

import json
import os
import re
import stat
import sys
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from tempfile import gettempdir
from typing import TYPE_CHECKING, Any, Literal

import dj_database_url
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, connection, models, transaction
from django.db.backends.base.creation import TEST_DATABASE_PREFIX
from django.db.models import Prefetch, Q, prefetch_related_objects
from django.utils import timezone
from rest_framework.authtoken.models import Token

from accounts.models import get_or_create_email_verification, mark_email_verified
from methodology.models import (
    Activity,
    EventChannel,
    ExpertProfile,
    KarmaAward,
    PipChange,
    Playbook,
    PlaybookVersion,
    ProcessImprovementProposal,
    VersionSource,
    Workflow,
)
from methodology.models.karma_award import first_release_identity
from methodology.services.experts_service import (
    SOURCE_BUCKET_BY_KIND,
    SOURCE_BUCKETS,
    AwardTotals,
    ExpertsService,
    LiveContributionCounts,
    resolve_primary_category,
)
from methodology.services.pip_admin_service import PIPAdminService
from methodology.services.pip_service import PIPService

if TYPE_CHECKING:
    from pytest import FixtureRequest

CEDAR_PASSWORD = "Cedar-fictional-tests-only-2026"
CEDAR_BASELINE_TIME_ISO = "2026-11-22T00:00:00+00:00"
_CEDAR_SOURCE = (
    Path(__file__).resolve().parents[2] / "test-data/experts/cedar-rfp-01.json"
)
_CATEGORY_BY_LABEL = {label: slug for slug, label in Playbook.CATEGORY_CHOICES}
_AWARD_UNITS = {
    KarmaAward.SourceKind.RELEASE: 5000,
    KarmaAward.SourceKind.MAJOR: 500,
    KarmaAward.SourceKind.MINOR: 100,
    KarmaAward.SourceKind.CONSUMPTION: 5,
    KarmaAward.SourceKind.LEARNING: 5,
}
_TEST_SETTINGS = {"mimir.settings", "mimir.settings.test", "mimir.settings.e2e"}
_TEST_OWNER_ID = re.compile(r"[0-9a-f]{32}")
_UNREGISTERED_SQLITE_SCOPE = (
    "Cedar requires a runner-owned SQLite file registered by an active pytest fixture."
)
_LOCAL_POSTGRES_HOSTS = {"", "localhost", "127.0.0.1", "::1"}
_DEMO_OWNER_IDS = {"mimir-experts-demo", "mimir-experts-demo-host"}
_STAGING_FORMAT = "mimir-experts-owned-postgres-v1"
_STAGING_HOSTS = {"cedar-db", "localhost", "127.0.0.1", "::1"}
_STAGING_MANIFEST_LIMIT = 4096
_STAGING_IDENTITY_SQL = """
SELECT current_database(), current_user, session_user,
       pg_get_userbyid(d.datdba), shobj_description(d.oid, 'pg_database'),
       r.rolsuper, r.rolcreatedb, r.rolcreaterole, r.rolbypassrls,
       r.rolreplication, r.rolcanlogin
FROM pg_database AS d
JOIN pg_roles AS r ON r.rolname = current_user
WHERE d.datname = current_database()
"""
_INITIAL_RELEASE = "1.0"
_VERSION = re.compile(r"(?:0|[1-9][0-9]{0,3})\.[0-9]")
_Record = dict[str, Any]


@dataclass(frozen=True)
class CedarDatabaseScope:
    """Expected database identity and explicit ownership evidence for local files."""

    kind: Literal["test", "owned_demo", "owned_staging"]
    database_name: str
    ownership_manifest: Path | None = None
    owner_id: str | None = None


@dataclass(slots=True)
class _SQLiteTestRegistration:
    """Lifetime of one fixture's SQLite claim, shared by any context copies."""

    scope: CedarDatabaseScope
    request: FixtureRequest
    pid: int
    active: bool = True


_SQLITE_TEST_REGISTRATION: ContextVar[_SQLiteTestRegistration | None] = ContextVar(
    "cedar_sqlite_test_registration", default=None
)


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
        return {
            username: _positive_int(user.pk, "saved Cedar user PK")
            for username, user in self.users_by_username.items()
        }

    @property
    def playbook_ids(self) -> Mapping[int, int]:
        """Expose oracle-book-PK to actual-book-PK compatibility mapping.

        :return: Book identity mapping. Example: {6101: 6101}.
        :raises ValueError: If an imported book is unsaved.
        """
        return {
            oracle_id: _positive_int(book.pk, "saved Cedar playbook PK")
            for oracle_id, book in self.playbooks_by_pk.items()
        }


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
    _resolve_database_scope(scope)
    document = _read_cedar_document(fixture_path)
    _validate_cedar_document(document)
    try:
        with transaction.atomic():
            users = _create_cedar_users(document)
            books = _create_cedar_playbooks(document, users)
            dataset = CedarDataset(users, books, document)
            workflows, activities = _create_cedar_public_content(dataset)
            dataset = replace(
                dataset, workflows_by_pk=workflows, activities_by_pk=activities
            )
            _create_cedar_private_boundaries(dataset)
            pips = _create_cedar_historical_pips(dataset)
            dataset = replace(dataset, pips_by_key=pips)
            _publish_cedar_historical_changes(dataset)
            _import_cedar_versions(dataset)
            _import_cedar_profiles(dataset)
            _persist_cedar_awards(_normalize_cedar_awards(dataset))
            _verify_cedar_projection(dataset)
    except (IntegrityError, MultipleObjectsReturned, ValidationError) as error:
        raise ValueError(
            "Cedar import encountered invalid data or a database conflict."
        ) from error
    return dataset


def _resolve_database_scope(scope: CedarDatabaseScope | None) -> CedarDatabaseScope:
    """Accept verified runner isolation or explicitly evidenced demo ownership.

    :param scope: Optional caller ownership evidence. Example: None.
    :return: Checked effective scope. Example: an in-memory test scope.
    :raises ValueError: If no safe database ownership can be established.
    """
    if scope is None:
        scope = CedarDatabaseScope("test", str(connection.settings_dict["NAME"]))
    if not isinstance(scope, CedarDatabaseScope):
        raise ValueError("Explicit Cedar database scope required.")  # noqa: TRY004
    _validate_database_scope(scope)
    return scope


def _validate_database_scope(scope: CedarDatabaseScope) -> None:
    """Match actual connection/settings/path against the claimed owned database.

    :param scope: Resolved ownership claim. Example: a runner-owned test scope.
    :return: None. Example: None.
    :raises ValueError: For ambient dev, tracked seed, idle or production databases.
    """
    effective_name = str(connection.settings_dict["NAME"])
    if scope.database_name != effective_name:
        raise ValueError("Cedar database claim does not match the effective database.")
    if scope.kind == "owned_demo" and connection.vendor == "sqlite":
        _validate_owned_demo(scope)
        _verify_sqlite_target(str(Path(effective_name).resolve()))
        return
    if scope.kind == "owned_staging" and connection.vendor == "postgresql":
        _validate_owned_postgres_staging(scope)
        return
    if scope.kind != "test":
        raise ValueError("Unrecognized or unsafe Cedar database scope.")

    module = os.environ.get("DJANGO_SETTINGS_MODULE")
    pytest_running = (
        module in _TEST_SETTINGS
        and settings.MIMIR_ENV in {"test", "e2e"}
        and bool(os.environ.get("PYTEST_CURRENT_TEST"))
    )
    if connection.vendor == "postgresql" and pytest_running:
        _validate_postgres_test_scope(effective_name)
        return
    runner_memory = f"file:memorydb_{connection.alias}?mode=memory&cache=shared"
    if (
        connection.vendor == "sqlite"
        and pytest_running
        and effective_name != runner_memory
    ):
        _validate_sqlite_test_scope(scope)
        _verify_sqlite_target(effective_name)
        return
    acceptance = module == "mimir.settings.acceptance"
    if (
        connection.vendor != "sqlite"
        or effective_name != runner_memory
        or not (pytest_running or acceptance)
    ):
        raise ValueError("Cedar requires the runner-owned test database.")
    _verify_sqlite_target("")


def _validate_sqlite_test_scope(scope: CedarDatabaseScope) -> None:
    """Verify the runner declaration, private temp files and current-process owner.

    :param scope: The explicit fixture claim for the file-backed test database.
    :return: None once the runner settings and owner record agree.
    :raises ValueError: The declaration, path or ownership record is unsafe.
    """
    database = Path(scope.database_name)
    runner = settings.DATABASES["default"]["TEST"].get("NAME")
    if (
        connection.alias != "default"
        or str(runner) != scope.database_name
        or str(connection.settings_dict["TEST"].get("NAME")) != scope.database_name
    ):
        raise ValueError("Cedar file database does not match the runner declaration.")
    marker = scope.ownership_manifest
    owner = scope.owner_id
    if (
        marker is None
        or marker != database.with_name("owner.json")
        or not isinstance(owner, str)
        or not _TEST_OWNER_ID.fullmatch(owner)
    ):
        raise ValueError("Cedar file database requires explicit run ownership.")
    _validate_private_test_paths(database, marker)
    try:
        recorded = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(
            "Cedar file database ownership record is unreadable."
        ) from error
    if recorded != {"database": str(database), "owner_id": owner, "pid": os.getpid()}:
        raise ValueError("Cedar file database ownership does not match this process.")
    _require_registered_sqlite_scope(scope)


@contextmanager
def _register_sqlite_test_scope(
    scope: CedarDatabaseScope, request: FixtureRequest
) -> Iterator[None]:
    """Bind a file claim to the pytest fixture that activates its Django alias.

    :param scope: Exact claim for the owned temporary file.
    :param request: The activating fixture's runner-supplied request.
    :return: Registration valid while the fixture and its triggering test are active.
    :raises ValueError: If the request is outside actual pytest fixture setup.
    """
    if _active_fixture_phase(request) != "setup":
        raise ValueError(_UNREGISTERED_SQLITE_SCOPE)
    registration = _SQLiteTestRegistration(scope, request, os.getpid())
    token = _SQLITE_TEST_REGISTRATION.set(registration)
    try:
        yield
    finally:
        # Reset restores the local binding only. Copies still hold this registration.
        registration.active = False
        _SQLITE_TEST_REGISTRATION.reset(token)


def _active_fixture_phase(request: FixtureRequest) -> Literal["setup", "call"] | None:
    """Match a fixture request to the real runner's current collected test.

    :param request: The actual pytest fixture request, including a session fixture.
    :return: The test phase held by that request, or None for inactive claims.
    """
    # The data importer is also used by standalone demo and Behave runtimes.
    pytest_module = sys.modules.get("pytest")
    if (
        pytest_module is None
        or not isinstance(request, pytest_module.FixtureRequest)
        or request.fixturename is None
    ):
        return None
    # A session-scoped request's .node is the session, so use the triggering item.
    item = request._pyfuncitem
    session = request.session
    stack = session._setupstate.stack
    if (
        item.session is not session
        or item is not next(reversed(stack), None)
        or stack[item][1] is not None
        or not any(collected is item for collected in session.items)
    ):
        return None
    marker = os.environ.get("PYTEST_CURRENT_TEST")
    node_id = item.nodeid.replace("\x00", "(null)")
    for phase in ("setup", "call"):
        if marker == f"{node_id} ({phase})":
            return phase
    return None


def _require_registered_sqlite_scope(scope: CedarDatabaseScope) -> None:
    """Require live authority in the current pytest item before opening SQLite.

    :param scope: Exact private file claim registered by the fixture.
    :return: None if the registration and its pytest item are still active.
    :raises ValueError: If the current context has no matching live registration.
    """
    registration = _SQLITE_TEST_REGISTRATION.get()
    if (
        registration is None
        or not registration.active
        or registration.scope is not scope
        or registration.pid != os.getpid()
        or _active_fixture_phase(registration.request) is None
    ):
        raise ValueError(_UNREGISTERED_SQLITE_SCOPE)


def _validate_private_test_paths(database: Path, marker: Path) -> None:
    """Require canonical owned private files directly within a temporary directory."""
    root = Path(gettempdir()).resolve()
    checkout = Path(settings.BASE_DIR).resolve()
    directory = database.parent
    if (
        directory.parent != root
        or database.is_relative_to(checkout)
        or database.is_relative_to(checkout.with_name("mimir"))
        or database != database.resolve()
        or marker != marker.resolve()
    ):
        raise ValueError(
            "Cedar file database requires a canonical private temporary path."
        )
    try:
        parent = directory.lstat()
        files = (database.lstat(), marker.lstat())
    except OSError as error:
        raise ValueError(
            "Cedar file database or ownership record is missing."
        ) from error
    if (
        not stat.S_ISDIR(parent.st_mode)
        or parent.st_uid != os.getuid()
        or parent.st_mode & 0o077
        or any(
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
            or info.st_mode & 0o077
            for info in files
        )
    ):
        raise ValueError(
            "Cedar file database and ownership record must be private files."
        )


def _verify_sqlite_target(expected_path: str) -> None:
    """Confirm the main database actually opened by SQLite is the intended target."""
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA database_list")
        opened = {alias: filename for _sequence, alias, filename in cursor.fetchall()}
    if opened.get("main") != expected_path:
        raise ValueError("Cedar database claim does not match the open database.")


def _validate_postgres_test_scope(effective_name: str) -> None:
    """Require Django's local runner-derived database and verify the live connection."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("Cedar requires an independent PostgreSQL base configuration.")
    configured = dj_database_url.parse(database_url)
    if not _postgres_test_settings_match(
        connection.settings_dict,
        configured,
        os.environ.get("PYTEST_XDIST_WORKER"),
    ):
        raise ValueError(
            "Cedar requires the runner-owned local PostgreSQL test database."
        )
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database()")
        match = cursor.fetchone() == (effective_name,)
    if not match:
        raise ValueError("Cedar database claim does not match the open database.")


def _postgres_test_settings_match(
    actual: Mapping[str, object],
    configured: Mapping[str, object],
    worker: str | None,
) -> bool:
    """Match the actual PostgreSQL connection against Django's local runner identity."""
    base = configured.get("NAME")
    engine = "django.db.backends.postgresql"
    if (
        not isinstance(base, str)
        or not base
        or configured.get("ENGINE") != engine
        or actual.get("ENGINE") != engine
        or configured.get("HOST") not in _LOCAL_POSTGRES_HOSTS
        or (worker is not None and not re.fullmatch(r"gw[0-9]+", worker))
    ):
        return False
    suffix = f"_{worker}" if worker else ""
    return (
        actual.get("NAME") == f"{TEST_DATABASE_PREFIX}{base}{suffix}"
        and actual.get("HOST") == configured.get("HOST")
        and str(actual.get("PORT") or "") == str(configured.get("PORT") or "")
        and actual.get("USER") == configured.get("USER")
    )


def _read_cedar_document(fixture_path: Path | None) -> dict[str, object]:
    """Read the domain contract without treating it as a loaddata fixture.

    :param fixture_path: Optional explicit source. Example: Path("cedar.json").
    :return: Parsed document. Example: {"people": []}.
    :raises ValueError: For malformed JSON/document structure.
    :raises OSError: If the file cannot be read.
    """
    source = fixture_path if fixture_path is not None else _CEDAR_SOURCE
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Malformed Cedar JSON document.") from error
    if (
        not isinstance(document, dict)
        or document.get("format") != "experts-story-fixture-v2"
    ):
        raise ValueError("Expected the Cedar domain fixture format.")
    return document


def _validate_cedar_document(document: Mapping[str, object]) -> None:
    """Validate identities, categories, counts, unit arithmetic and oracle totals.

    :param document: Independent source document. Example: {"people": []}.
    :return: None. Example: None.
    :raises ValueError: For invalid values or inconsistent totals/history.
    """
    people = _rows(document, "people")
    pips = _rows(document, "historical_pips")
    if not people:
        raise ValueError("Cedar requires its declared contributors.")
    accounts = [*people, *_authenticated_actors(document)]
    for account in accounts:
        _validate_account(account)
    _require_unique([account["username"] for account in accounts], "Cedar usernames")
    _require_unique(
        [account["email"].casefold() for account in accounts], "Cedar email addresses"
    )
    books = {book["pk"]: book for _, book in _book_declarations(people)}
    for person in people:
        _validate_person_ledger(person)
    _validate_pip_history(pips, people, books)
    copy_policy = document.get("copy_count_policy")
    if not isinstance(copy_policy, dict):
        raise ValueError("Cedar GUI-copy policy is required.")  # noqa: TRY004
    mike = next((person for person in people if person["username"] == "mchen"), {})
    copy_count = _nonnegative_int(copy_policy.get("baseline_mchen"), "Mike GUI copies")
    consumption_count = _nonnegative_int(
        copy_policy.get("baseline_mchen_all_author_consumption_events"),
        "Mike author consumption",
    )
    if copy_count != mike.get("copy_count") or consumption_count != sum(
        row["count"]
        for row in mike.get("ledger", [])
        if row["event"] == KarmaAward.SourceKind.CONSUMPTION
    ):
        raise ValueError("Cedar Mike GUI-copy subset does not reconcile.")


def _baseline_time() -> datetime:
    """Return the deterministic aware historical fixture timestamp.

    :return: Original import event time. Example: 2026-11-22T00:00:00+00:00.
    :raises ValueError: If the configured fixture timestamp is invalid.
    """
    return datetime.fromisoformat(CEDAR_BASELINE_TIME_ISO)


def _validate_owned_demo(scope: CedarDatabaseScope) -> None:
    """Verify the local owner's manifest and immutable database path before SQL."""
    if (
        os.environ.get("DJANGO_SETTINGS_MODULE") != "experts_demo_settings"
        or settings.EMAIL_BACKEND != "django.core.mail.backends.filebased.EmailBackend"
        or scope.owner_id not in _DEMO_OWNER_IDS
        or scope.ownership_manifest is None
    ):
        raise ValueError("Cedar demo database requires verified local ownership.")
    expected = Path(settings.DEMO_DATA_ROOT).resolve() / "mimir.db"
    database = Path(scope.database_name)
    manifest = scope.ownership_manifest
    checkout = Path(settings.BASE_DIR).resolve()
    if (
        database != expected
        or manifest != expected.with_name("owner.json")
        or not database.is_file()
        or not manifest.is_file()
        or database.is_symlink()
        or manifest.is_symlink()
        or database.is_relative_to(checkout)
        or database.is_relative_to(checkout.with_name("mimir"))
        or database.stat().st_nlink != 1
        or database.stat().st_uid != os.getuid()
        or manifest.stat().st_uid != os.getuid()
    ):
        raise ValueError(
            "Cedar demo database or ownership manifest is outside its local scope."
        )
    record = json.loads(manifest.read_text(encoding="utf-8"))
    if record != {
        "demo_id": scope.owner_id,
        "fixture": "CEDAR-RFP-01",
        "database": str(expected),
    }:
        raise ValueError("Cedar demo ownership manifest does not match the database.")


def _validate_owned_postgres_staging(scope: CedarDatabaseScope) -> None:
    """Verify private runtime, local ownership and actual PostgreSQL identity.

    :param scope: Explicit staging claim. Example: CedarDatabaseScope("owned_staging", name).
    :return: None after all guards pass. Example: None.
    :raises ValueError: If any ownership/runtime/database evidence differs.
    """
    if (
        os.environ.get("DJANGO_SETTINGS_MODULE") != "experts_staging_settings"
        or settings.MIMIR_ENV != "experts_staging"
        or settings.EMAIL_BACKEND != "django.core.mail.backends.filebased.EmailBackend"
    ):
        raise ValueError("Cedar staging requires its isolated runtime and file mail.")
    expected = _staging_expected_manifest(scope, connection.settings_dict)
    marker = _staging_manifest_path(scope)
    if _read_private_staging_manifest(marker) != expected:
        raise ValueError("Cedar staging ownership manifest does not match its claim.")
    with connection.cursor() as cursor:
        cursor.execute(_STAGING_IDENTITY_SQL)
        actual = cursor.fetchone()
    if not _staging_identity_matches(expected, actual):
        raise ValueError("Cedar staging live database ownership does not match.")


def _staging_expected_manifest(
    scope: CedarDatabaseScope, actual: Mapping[str, object]
) -> dict[str, str]:
    """Validate the closed staging namespace and configured endpoint without SQL.

    :param scope: Explicit nonce claim. Example: a staging scope with a 32-hex owner.
    :param actual: Effective connection settings. Example: {"HOST": "cedar-db"}.
    :return: Exact expected public ownership record. Example: {"fixture": "CEDAR-RFP-01"}.
    :raises ValueError: If namespace, role, endpoint or nonce is unsafe.
    """
    owner = scope.owner_id
    if (
        scope.kind != "owned_staging"
        or not isinstance(owner, str)
        or not _TEST_OWNER_ID.fullmatch(owner)
    ):
        raise ValueError("Cedar staging requires a 32-hex ownership nonce.")
    name, host, port = f"experts_cedar_{owner}", actual.get("HOST"), actual.get("PORT")
    if (
        actual.get("ENGINE") != "django.db.backends.postgresql"
        or scope.database_name != name
        or actual.get("NAME") != name
        or actual.get("USER") != name
        or not isinstance(host, str)
        or host not in _STAGING_HOSTS
        or isinstance(port, bool)
        or not str(port).isdecimal()
        or not 1 <= int(str(port)) <= 65535
    ):
        raise ValueError("Cedar staging requires its dedicated database and role.")
    return {
        "format": _STAGING_FORMAT,
        "fixture": "CEDAR-RFP-01",
        "owner_id": owner,
        "database": name,
        "role": name,
        "host": str(host),
        "port": str(port),
    }


def _staging_manifest_path(scope: CedarDatabaseScope) -> Path:
    """Require a private owner directory outside both application checkouts.

    :param scope: Claim holding the marker path. Example: /experts-scope/owner.json.
    :return: Checked marker path. Example: Path("/experts-scope/owner.json").
    :raises ValueError: If the path, parent permissions or ownership is unsafe.
    """
    root = Path(getattr(settings, "EXPERTS_STAGING_SCOPE_ROOT", ""))
    marker, checkout = scope.ownership_manifest, Path(settings.BASE_DIR).resolve()
    if (
        not root.is_absolute()
        or root != root.resolve()
        or any(parent.is_symlink() for parent in (root, *root.parents))
        or root.is_relative_to(checkout)
        or root.is_relative_to(checkout.with_name("mimir"))
        or not root.is_dir()
        or root.stat().st_uid != os.getuid()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
        or marker != root / "owner.json"
    ):
        raise ValueError("Cedar staging requires a private ownership directory.")
    return marker


def _read_private_staging_manifest(path: Path) -> object:
    """Open a bounded private manifest without following a final symlink.

    :param path: Prechecked marker path. Example: Path("/experts-scope/owner.json").
    :return: Decoded JSON value. Example: {"format": "mimir-experts-owned-postgres-v1"}.
    :raises ValueError: If the file is unsafe, oversized or malformed.
    :raises OSError: If the claimed file cannot be opened.
    """
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open(path, flags), "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_size > _STAGING_MANIFEST_LIMIT
        ):
            raise ValueError("Cedar staging requires a private regular marker file.")
        content = stream.read(_STAGING_MANIFEST_LIMIT + 1)
    if len(content) > _STAGING_MANIFEST_LIMIT:
        raise ValueError("Cedar staging ownership manifest is too large.")
    try:
        return json.loads(content)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Cedar staging ownership manifest is malformed.") from error


def _staging_identity_matches(
    expected: Mapping[str, str], actual: Sequence[object] | None
) -> bool:
    """Match actual server ownership and nonprivileged LOGIN role capabilities.

    :param expected: Exact marker record. Example: {"owner_id": "0" * 32}.
    :param actual: Real SQL row. Example: (database, role, role, role, marker, False).
    :return: Whether every identity and capability matches. Example: True.
    """
    role = expected["role"]
    required = (
        expected["database"],
        role,
        role,
        role,
        f"{_STAGING_FORMAT}:{expected['owner_id']}",
        False,
        False,
        False,
        False,
        False,
        True,
    )
    return (
        actual is not None
        and len(actual) == len(required)
        and all(type(value) is bool for value in actual[5:])
        and tuple(actual) == required
    )


def _rows(record: Mapping[str, object], field_name: str) -> list[_Record]:
    """Require a JSON list of object records."""
    value = record.get(field_name)
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError(f"Cedar {field_name} must be a list of objects.")
    return value


def _text(value: object, field_name: str, max_length: int | None = None) -> str:
    """Require nonblank text that fits a bounded model field when applicable."""
    if (
        not isinstance(value, str)
        or not value.strip()
        or (max_length is not None and len(value) > max_length)
    ):
        raise ValueError(f"Cedar {field_name} contains invalid text.")
    return value


def _nonnegative_int(value: object, field_name: str) -> int:
    """Disallow booleans and implicit numeric conversion in fixture arithmetic."""
    if type(value) is not int or value < 0:
        raise ValueError(f"Cedar {field_name} must be a nonnegative integer.")
    return value


def _positive_int(value: object, field_name: str) -> int:
    """Require a positive integer that fits an integer reference field."""
    result = _nonnegative_int(value, field_name)
    if not 0 < result <= 2**63 - 1:
        raise ValueError(
            f"Cedar {field_name} must be a positive persisted identifier or count."
        )
    return result


def _category(value: object) -> str:
    """Normalize one known category label to its model slug."""
    label = _text(value, "category")
    if label not in _CATEGORY_BY_LABEL:
        raise ValueError("Unrecognized Cedar category.")
    return _CATEGORY_BY_LABEL[label]


def _require_unique(values: Sequence[str | int], description: str) -> None:
    """Reject duplicate fixture keys before database state can change."""
    if len(set(values)) != len(values):
        raise ValueError(f"Duplicate {description}.")


def _authenticated_actors(document: Mapping[str, object]) -> list[_Record]:
    """Read only the actors the source declares as authenticated accounts."""
    actors = _rows(document, "actors")
    if any(type(actor.get("authenticated", False)) is not bool for actor in actors):
        raise ValueError("Cedar actor authentication state must be boolean.")
    return [actor for actor in actors if actor.get("authenticated", False)]


def _validate_account(record: _Record) -> None:
    """Validate identifiers and bounded fields of a declared user."""
    try:
        UnicodeUsernameValidator()(_text(record.get("username"), "username", 150))
        validate_email(_text(record.get("email"), "email address", 254))
    except ValidationError as error:
        raise ValueError("Invalid Cedar account identity.") from error
    name = _text(record.get("name"), "display name")
    first, _, last = name.partition(" ")
    if (
        len(first) > 150
        or len(last) > 150
        or type(record.get("is_staff", False)) is not bool
    ):
        raise ValueError("Invalid Cedar account display name or staff flag.")


def _book_declarations(people: Sequence[_Record]) -> list[tuple[_Record, _Record]]:
    """Get and validate the explicit public and draft book declarations."""
    declared: list[tuple[_Record, _Record]] = []
    workflow_ids: list[int] = []
    activity_ids: list[int] = []
    for person in people:
        if person.get("summary") is not None and not isinstance(person["summary"], str):
            raise ValueError("Cedar profile summary must be text or null.")
        _validate_private_declarations(person)
        for book in _rows(person, "public_playbooks"):
            _validate_book(book, released=True)
            _validate_book_content(book, workflow_ids, activity_ids)
            declared.append((person, book))
        if "draft_playbook" in person:
            book = person["draft_playbook"]
            if not isinstance(book, dict):
                raise ValueError("Invalid Cedar draft playbook.")
            _validate_book(book, released=False)
            declared.append((person, book))
    _require_unique([book["pk"] for _, book in declared], "Cedar book PKs")
    _require_unique(workflow_ids, "Cedar workflow PKs")
    _require_unique(activity_ids, "Cedar activity PKs")
    return declared


def _validate_book(book: _Record, *, released: bool) -> None:
    """Validate identity, version line and category of a declared book."""
    _positive_int(book.get("pk"), "book PK")
    _text(book.get("title"), "book title", 100)
    _category(book.get("category"))
    version = _text(book.get("version"), "book version")
    if (
        not _VERSION.fullmatch(version)
        or (Decimal(version) >= 1) != released
        or version == "0.0"
    ):
        raise ValueError("Invalid Cedar book version.")


def _validate_book_content(
    book: _Record, workflow_ids: list[int], activity_ids: list[int]
) -> None:
    """Validate the explicitly named and identified current content."""
    if "workflow" in book:
        _text(book["workflow"], "workflow name", 100)
    if "workflow_pk" in book:
        workflow_ids.append(_positive_int(book["workflow_pk"], "workflow PK"))
    if "activity_pk" in book:
        activity_ids.append(_positive_int(book["activity_pk"], "activity PK"))
        _text(book.get("activity"), "activity name", 200)
    elif "activity" in book:
        raise ValueError("Cedar singleton activity requires its declared PK.")
    activities = book.get("activities", [])
    if not isinstance(activities, list):
        raise ValueError("Cedar workflow activities must be a list.")  # noqa: TRY004
    names = [_text(name, "activity name", 200) for name in activities]
    if "activity" in book:
        names.append(book["activity"])
    _require_unique(names, "Cedar activity names within a workflow")
    if names and not ("workflow" in book or "workflow_pk" in book):
        raise ValueError("Cedar activities require a declared parent workflow.")


def _validate_private_declarations(person: _Record) -> None:
    """Check that reserved private sentinels fit their actual model fields."""
    titles = person.get("private_playbooks", [])
    if not isinstance(titles, list):
        raise ValueError("Cedar private playbooks must be a list.")  # noqa: TRY004
    _require_unique(
        [_text(title, "private title", 100) for title in titles], "Cedar private titles"
    )
    if "private_pip" in person:
        _text(person["private_pip"], "private proposal title", 200)
        if not _rows(person, "public_playbooks"):
            raise ValueError("Cedar unpublished proposal requires a declared release.")
    if "private_token" in person:
        _text(person["private_token"], "private token", 40)


def _validate_person_ledger(person: _Record) -> None:
    """Check counts, unit values and all independent numeric oracle fields."""
    amounts_by_category: Counter[str] = Counter()
    amounts_by_source = dict.fromkeys(SOURCE_BUCKETS, 0)
    counts = _ledger_counts(person)
    for (category, source), count in counts.items():
        points = count * _AWARD_UNITS[source]
        amounts_by_category[category] += points
        amounts_by_source[SOURCE_BUCKET_BY_KIND[source]] += points
    category_totals = _oracle_points(person, "karma_by_category")
    source_totals = _oracle_points(person, "karma_by_source")
    category = person.get("primary_category")
    nonzero = bool(amounts_by_category)
    if (
        dict(amounts_by_category) != category_totals
        or amounts_by_source != source_totals
        or sum(category_totals.values())
        != _nonnegative_int(person.get("total_karma"), "total Karma")
        or (category is not None) != nonzero
        or (
            nonzero
            and category_totals.get(_text(category, "primary category"))
            != max(category_totals.values())
        )
    ):
        raise ValueError(
            "Cedar ledger arithmetic does not match the independent oracle."
        )
    charged_buckets = [
        count
        for (_category_label, source), count in counts.items()
        if source == KarmaAward.SourceKind.CONSUMPTION
    ]
    copies = _nonnegative_int(person.get("copy_count", 0), "GUI copy count")
    if copies and (len(charged_buckets) != 1 or copies > charged_buckets[0]):
        raise ValueError("Cedar GUI copies require a known author-consumption subset.")


def _ledger_counts(person: _Record) -> dict[tuple[str, str], int]:
    """Validate and index unique category/source aggregate rows."""
    counts: dict[tuple[str, str], int] = {}
    for row in _rows(person, "ledger"):
        category = _text(row.get("category"), "ledger category")
        _category(category)
        event = _text(row.get("event"), "award source")
        count = _positive_int(row.get("count"), "award count")
        unit = _positive_int(row.get("points_each"), "award points")
        points = _positive_int(row.get("points"), "row points")
        key = (category, event)
        if key in counts or _AWARD_UNITS.get(event) != unit or count * unit != points:
            raise ValueError(
                "Cedar ledger rows must have unique keys and consistent award arithmetic."
            )
        counts[key] = count
    return counts


def _oracle_points(person: _Record, field_name: str) -> dict[str, int]:
    """Keep declared oracle numbers separate from event arithmetic."""
    amounts = person.get(field_name)
    if not isinstance(amounts, dict):
        raise ValueError(f"Cedar {field_name} must be a points object.")  # noqa: TRY004
    return {
        name: _nonnegative_int(value, field_name) for name, value in amounts.items()
    }


def _validate_pip_history(
    pips: Sequence[_Record], people: Sequence[_Record], books: Mapping[int, _Record]
) -> None:
    """Verify exactly declared published PIPs and known receipt capacity."""
    counts_by_user: dict[str, Counter[tuple[str, str]]] = {
        person["username"]: Counter(
            (book["category"], KarmaAward.SourceKind.RELEASE)
            for book in _rows(person, "public_playbooks")
        )
        for person in people
    }
    public_ids = {
        book["pk"] for person in people for book in _rows(person, "public_playbooks")
    }
    revised_by: dict[int, str] = {}
    _require_unique(
        [_text(pip.get("id"), "historical PIP ID", 200) for pip in pips],
        "Cedar PIP IDs",
    )
    for pip in pips:
        author = _text(pip.get("submitter"), "historical PIP submitter")
        book_id = _positive_int(pip.get("playbook_pk"), "historical PIP book PK")
        if (
            author not in counts_by_user
            or book_id not in public_ids
            or book_id in revised_by
        ):
            raise ValueError(
                "Cedar historical PIP requires a known author and unique public target."
            )
        book = books[book_id]
        for source in _validate_published_changes(pip, book):
            counts_by_user[author][(pip["category"], source)] += 1
        revised_by[book_id] = pip["version_after"]
    for book_id in public_ids:
        if books[book_id]["version"] != revised_by.get(book_id, _INITIAL_RELEASE):
            raise ValueError(
                "Cedar released book lacks its declared publication history."
            )
    for person in people:
        ledger = _ledger_counts(person)
        if any(
            ledger.get(key, 0) < count
            for key, count in counts_by_user[person["username"]].items()
        ):
            raise ValueError("Cedar known content receipts exceed ledger counts.")


def _validate_published_changes(pip: _Record, book: _Record) -> tuple[str, ...]:
    """Check that canonical Activity changes and publication version match their book."""
    version = _text(pip.get("version_after"), "published PIP version")
    if (
        pip.get("version_before") != _INITIAL_RELEASE
        or not _VERSION.fullmatch(version)
        or Decimal(version) <= Decimal(_INITIAL_RELEASE)
        or version != book["version"]
        or pip.get("playbook_title") != book["title"]
        or pip.get("category") != book["category"]
    ):
        raise ValueError(
            "Cedar historical PIP does not match its declared book and versions."
        )
    changes = _rows(pip, "accepted_changes")
    sources: list[str] = []
    names: list[str] = []
    for change in changes:
        names.append(_text(change.get("name"), "published activity name", 200))
        operation = change.get("operation")
        if change.get("entity") != PipChange.ENTITY_ACTIVITY or operation not in (
            PipChange.CHANGE_ADD,
            PipChange.CHANGE_ALTER,
        ):
            raise ValueError("Unsupported Cedar historical change.")
        source = (
            KarmaAward.SourceKind.MAJOR
            if operation == PipChange.CHANGE_ADD
            else KarmaAward.SourceKind.MINOR
        )
        if (
            _positive_int(change.get("karma"), "accepted change award")
            != _AWARD_UNITS[source]
        ):
            raise ValueError("Invalid Cedar historical change award.")
        sources.append(source)
    _require_unique(names, "Cedar published activity names")
    if not changes or sum(_AWARD_UNITS[source] for source in sources) != _positive_int(
        pip.get("total_award"), "historical PIP total"
    ):
        raise ValueError("Cedar PIP awards do not sum to its declared total.")
    return tuple(sources)


def _create_cedar_users(document: Mapping[str, object]) -> dict[str, User]:
    """Create real named accounts, preserving declared staff flags and identities.

    :param document: Validated oracle. Example: {"people": []}.
    :return: Actual users keyed by username. Example: {"mchen": a User}.
    :raises ValueError: For conflicting unrelated account ownership.
    """
    users: dict[str, User] = {}
    records = [*_rows(document, "people"), *_authenticated_actors(document)]
    for record in records:
        first_name, _, last_name = record["name"].partition(" ")
        username = record["username"]
        email = record["email"]
        matched = User.objects.filter(username=username).first()
        if User.objects.filter(email__iexact=email).exclude(username=username).exists():
            raise ValueError("Cedar account email conflicts with a different account.")
        values = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "is_staff": record.get("is_staff", False),
            "is_active": True,
            "is_superuser": False,
        }
        if matched is None:
            matched = User.objects.create_user(
                username=username, password=CEDAR_PASSWORD, **values
            )
        elif not _matches(matched, values) or not matched.check_password(
            CEDAR_PASSWORD
        ):
            raise ValueError("Cedar username conflicts with an existing account.")
        _verify_cedar_user_email(matched)
        users[username] = matched
    return users


def _verify_cedar_user_email(user: User) -> None:
    """Use existing real verification state so browser login is functional.

    :param user: Imported account. Example: User(username="esvensson").
    :return: None. Example: None.
    :raises ValueError: If the user is unsaved or not fixture-owned.
    """
    if not user.pk or not user.check_password(CEDAR_PASSWORD):
        raise ValueError("Email verification requires a saved Cedar account.")
    state = get_or_create_email_verification(user)
    if (
        not state.is_verified
        or state.verification_token
        or state.token_created_at is not None
    ):
        mark_email_verified(user)


def _create_cedar_playbooks(
    document: Mapping[str, object], users: Mapping[str, User]
) -> dict[int, Playbook]:
    """Create only declared current books with actual category/status/visibility.

    :param document: Validated current-book oracle. Example: {"people": []}.
    :param users: Actual imported authors. Example: {"mchen": a User}.
    :return: Oracle-PK keyed real books. Example: {6201: a Playbook}.
    :raises ValueError: For conflicting identities or missing authors.
    """
    people = _rows(document, "people")
    books: dict[int, Playbook] = {}
    for person, book in _book_declarations(people):
        released = book is not person.get("draft_playbook")
        stored = _match_or_create(
            Playbook,
            {"pk": book["pk"]},
            {
                "author_id": users[person["username"]].pk,
                "name": book["title"],
                "category": _category(book["category"]),
                "version": Decimal(book["version"]),
                "visibility": "public" if released else "private",
                "status": "released" if released else "draft",
                "description": "",
                "source": "owned",
            },
        )
        books[book["pk"]] = stored
    for person in people:
        for title in person.get("private_playbooks", []):
            stored = _match_or_create(
                Playbook,
                {
                    "author_id": users[person["username"]].pk,
                    "name": title,
                },
                {
                    "category": "other",
                    "version": Decimal("0.1"),
                    "visibility": "private",
                    "status": "draft",
                    "description": "",
                    "source": "owned",
                },
            )
            books[stored.pk] = stored
    return books


def _create_cedar_public_content(
    dataset: CedarDataset,
) -> tuple[dict[int, Workflow], dict[int, Activity]]:
    """Create the explicitly declared public workflows/activities from the contract.

    A current published Activity needs a parent. If the oracle gives only a
    workflow PK (Mike) or the published Activity names (Hana), use the declared
    book title as the minimal current workflow label. No v1 content is inferred.

    :param dataset: Imported users/books and oracle. Example: a CedarDataset.
    :return: Actual workflow/activity maps. Example: ({6202: workflow}, {6203: activity}).
    :raises ValueError: For missing parents or conflicting content identities.
    """
    workflows: dict[int, Workflow] = {}
    activities: dict[int, Activity] = {}
    revisions = {
        pip["playbook_pk"]: _rows(pip, "accepted_changes")
        for pip in _rows(dataset.oracle, "historical_pips")
    }
    public_books = [
        book
        for person in _rows(dataset.oracle, "people")
        for book in _rows(person, "public_playbooks")
    ]
    # Reserve declared IDs before any auto-generated parents or activities.
    public_books.sort(key=lambda book: "workflow_pk" not in book)
    for book in public_books:
        changes = revisions.get(book["pk"], [])
        if not changes and not ("workflow" in book or "workflow_pk" in book):
            continue
        workflow = _store_cedar_workflow(book)
        workflows[workflow.pk] = workflow
        named_activities = dict.fromkeys(book.get("activities", []))
        if "activity_pk" in book:
            named_activities[book["activity"]] = book["activity_pk"]
        for change in changes:
            named_activities.setdefault(change["name"], None)
        for order, (name, activity_id) in enumerate(named_activities.items(), start=1):
            activity = _store_cedar_activity(workflow.pk, name, order, activity_id)
            activities[activity.pk] = activity
    return workflows, activities


def _create_cedar_private_boundaries(dataset: CedarDataset) -> None:
    """Persist specified private book/PIP/token sentinels without public exposure.

    :param dataset: Fixture-owned accounts/books and oracle. Example: a CedarDataset.
    :return: None. Example: None.
    :raises ValueError: For conflicting sentinel ownership or missing parents.
    """
    for person in _rows(dataset.oracle, "people"):
        user = dataset.users_by_username[person["username"]]
        if "private_pip" in person:
            book = dataset.playbooks_by_pk[person["public_playbooks"][0]["pk"]]
            _match_or_create(
                ProcessImprovementProposal,
                {"title": person["private_pip"]},
                {
                    "playbook_id": book.pk,
                    "created_by_id": user.pk,
                    "status": ProcessImprovementProposal.STATUS_DRAFT,
                    "summary": "",
                },
            )
        if "private_token" in person:
            _match_or_create(
                Token, {"user_id": user.pk}, {"key": person["private_token"]}
            )


def _create_cedar_historical_pips(
    dataset: CedarDataset,
) -> dict[str, ProcessImprovementProposal]:
    """Create real accepted historical PIPs/changes without decision hooks.

    :param dataset: Imported parents and historical contract. Example: a CedarDataset.
    :return: PIPs keyed by historical ID. Example: {"HIST-MARIA-DESIGN-01": a PIP}.
    :raises ValueError: For mismatched authors, changes or published version facts.
    """
    pips: dict[str, ProcessImprovementProposal] = {}
    timestamp = _baseline_time()
    for record in _rows(dataset.oracle, "historical_pips"):
        key = record["id"]
        pips[key] = _match_or_create(
            ProcessImprovementProposal,
            {"title": key},
            {
                "playbook_id": dataset.playbooks_by_pk[record["playbook_pk"]].pk,
                "created_by_id": dataset.user_ids[record["submitter"]],
                "status": ProcessImprovementProposal.STATUS_ACCEPTED,
                "summary": "",
                "decided_at": timestamp,
                "status_changed_at": timestamp,
            },
        )
    return pips


def _publish_cedar_historical_changes(dataset: CedarDataset) -> None:
    """Materialize declared accepted changes in their specified current books.

    :param dataset: Real historical PIPs and public parent content. Example: dataset.
    :return: None. Example: None.
    :raises ValueError: For inconsistent accepted/publication relationships.
    """
    workflows = {
        workflow.playbook_id: workflow for workflow in dataset.workflows_by_pk.values()
    }
    activities = {
        (activity.workflow_id, activity.name): activity
        for activity in dataset.activities_by_pk.values()
    }
    for record in _rows(dataset.oracle, "historical_pips"):
        pip = dataset.pips_by_key[record["id"]]
        workflow = workflows[pip.playbook_id]
        for order, fact in enumerate(_rows(record, "accepted_changes"), start=1):
            activity = activities[(workflow.pk, fact["name"])]
            _match_or_create(
                PipChange,
                {"pip_id": pip.pk, "order": order},
                {
                    "name": activity.name,
                    "parent_workflow_id": workflow.pk,
                    "target_id": activity.pk,
                    "target_name_snapshot": activity.name,
                    "change_type": fact["operation"],
                    "entity_type": fact["entity"],
                    "admin_decision": PipChange.ADMIN_ACCEPT,
                    "content": "",
                },
            )
    prefetch_related_objects(
        tuple(dataset.pips_by_key.values()),
        Prefetch("changes", queryset=PipChange.objects.order_by("order")),
    )


def _import_cedar_versions(dataset: CedarDataset) -> None:
    """Persist known release and published-PIP history without award hooks.

    :param dataset: Actual books, PIPs and oracle. Example: a CedarDataset.
    :return: None. Example: None.
    :raises ValueError: For conflicting version source, number or PIP linkage.
    """
    historical = {
        record["playbook_pk"]: record
        for record in _rows(dataset.oracle, "historical_pips")
    }
    for book in dataset.playbooks_by_pk.values():
        if book.status != "released":
            continue
        revision = historical.get(book.pk)
        baseline = _version_snapshot(book, include_current_content=revision is None)
        _store_cedar_version(
            book, _INITIAL_RELEASE, VersionSource.RELEASE, None, baseline
        )
        if revision is not None:
            pip = dataset.pips_by_key[revision["id"]]
            snapshot = _version_snapshot(book, include_current_content=True)
            snapshot.update(
                {
                    "pip_id": pip.pk,
                    "version_before": revision["version_before"],
                    "version_after": revision["version_after"],
                    "accepted_change_ids": [change.pk for change in pip.changes.all()],
                }
            )
            _store_cedar_version(
                book, revision["version_after"], VersionSource.PIP_SOURCE, pip, snapshot
            )


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
    if not playbook.pk:
        raise ValueError("Cedar version snapshots require a persisted book.")
    if not include_current_content:
        return {"version": _INITIAL_RELEASE}
    workflows = playbook.workflows.order_by("order", "pk").prefetch_related(
        Prefetch("activities", queryset=Activity.objects.order_by("order", "pk"))
    )
    return {
        "name": playbook.name,
        "category": playbook.category,
        "status": playbook.status,
        "version": str(playbook.version),
        "workflows": [
            {
                "id": workflow.pk,
                "name": workflow.name,
                "order": workflow.order,
                "abbreviation": workflow.abbreviation,
                "activities": [
                    {"id": activity.pk, "name": activity.name, "order": activity.order}
                    for activity in workflow.activities.all()
                ],
            }
            for workflow in workflows
        ],
    }


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
    if (
        source not in (VersionSource.RELEASE, VersionSource.PIP_SOURCE)
        or ((source == VersionSource.PIP_SOURCE) != (pip is not None))
        or (pip is not None and pip.playbook_id != playbook.pk)
    ):
        raise ValueError("Cedar version source and publication relationship conflict.")
    lookup = {"playbook_id": playbook.pk, "version_number": Decimal(version_number)}
    fields = {
        "source": source,
        "pip_id": pip.pk if pip is not None else None,
        "snapshot_data": dict(snapshot),
        "is_major": True,
        "created_by_id": playbook.author_id if pip is None else None,
    }
    version, created = PlaybookVersion.objects.get_or_create(**lookup, defaults=fields)
    timestamp = _baseline_time()
    if created:
        PlaybookVersion.objects.filter(pk=version.pk).update(created_at=timestamp)
        version.created_at = timestamp
    elif not _matches(version, fields) or version.created_at != timestamp:
        raise ValueError("Cedar playbook version conflicts with an existing receipt.")
    return version


def _import_cedar_profiles(dataset: CedarDataset) -> None:
    """Store supplied public prose, normalizing JSON null to empty text.

    :param dataset: Actual fixture accounts and oracle. Example: a CedarDataset.
    :return: None. Example: None.
    :raises ValueError: For conflicting profile ownership or malformed prose.
    """
    for person in _rows(dataset.oracle, "people"):
        user = dataset.users_by_username[person["username"]]
        _match_or_create(
            ExpertProfile,
            {"user_id": user.pk},
            {
                "contribution_summary": person.get("summary") or "",
                "summary_status": ExpertProfile.SummaryStatus.NEVER,
                "summary_updated_at": None,
                "summary_error_code": "",
                "last_summary_correlation_id": "",
            },
        )


def _normalize_cedar_awards(dataset: CedarDataset) -> tuple[HistoricalAward, ...]:
    """Expand count/unit rows and bind only known content/change references.

    :param dataset: Imported identities, history and independent oracle. Example: dataset.
    :return: Deterministic direct-import awards. Example: ().
    :raises ValueError: For inconsistent totals, channels or known references.
    """
    awards: list[HistoricalAward] = []
    for person in _rows(dataset.oracle, "people"):
        for index, row in enumerate(_rows(person, "ledger")):
            normalize = (
                _historical_release_rows
                if row["event"] == KarmaAward.SourceKind.RELEASE
                else _historical_nonrelease_rows
            )
            awards.extend(normalize(dataset, person["username"], row, index))
    _require_unique(
        [award.event_identity for award in awards], "Cedar award identities"
    )
    return tuple(awards)


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
    category = _category(ledger_row["category"])
    recipient_id = dataset.users_by_username[username].pk
    books = sorted(
        book.pk
        for book in dataset.playbooks_by_pk.values()
        if book.author_id == recipient_id
        and book.category == category
        and book.status == "released"
    )
    if len(books) > ledger_row["count"]:
        raise ValueError("Cedar ledger does not cover its known release receipts.")
    timestamp = _baseline_time()
    return tuple(
        HistoricalAward(
            recipient_id=recipient_id,
            event_identity=(
                first_release_identity(books[index])
                if index < len(books)
                else _historical_event_id(username, row_index, index)
            ),
            source_kind=KarmaAward.SourceKind.RELEASE,
            event_channel=EventChannel.HISTORICAL,
            points=ledger_row["points_each"],
            category=category,
            playbook_id_snapshot=books[index] if index < len(books) else None,
            change_id_snapshot=None,
            entity_type_snapshot=None,
            entity_id_snapshot=None,
            occurred_at=timestamp,
        )
        for index in range(ledger_row["count"])
    )


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
    source = ledger_row["event"]
    category = _category(ledger_row["category"])
    recipient_id = dataset.users_by_username[username].pk
    changes = _cedar_change_receipts(dataset, recipient_id, category, source)
    copies = 0
    if source == KarmaAward.SourceKind.CONSUMPTION:
        person = next(
            person
            for person in _rows(dataset.oracle, "people")
            if person["username"] == username
        )
        copies = person.get("copy_count", 0)
    if max(copies, len(changes)) > ledger_row["count"]:
        raise ValueError("Known Cedar history exceeds the aggregate ledger count.")
    timestamp = _baseline_time()
    return tuple(
        (
            HistoricalAward(
                recipient_id=recipient_id,
                event_identity=_historical_event_id(username, row_index, ordinal),
                source_kind=source,
                event_channel=(
                    EventChannel.GUI_COPY
                    if ordinal < copies
                    else EventChannel.HISTORICAL
                ),
                points=ledger_row["points_each"],
                category=category,
                playbook_id_snapshot=None,
                change_id_snapshot=None,
                entity_type_snapshot=None,
                entity_id_snapshot=None,
                occurred_at=timestamp,
            )
            if ordinal >= len(changes)
            else changes[ordinal]
        )
        for ordinal in range(ledger_row["count"])
    )


def _historical_event_id(username: str, row_index: int, ordinal: int) -> str:
    """Build stable identities for historical events without known release keys.

    :param username: Oracle recipient. Example: "mrodriguez".
    :param row_index: Zero-based source row. Example: 1.
    :param ordinal: Zero-based item within aggregate row. Example: 0.
    :return: Stable identity. Example: "cedar:baseline:mrodriguez:1:0".
    :raises ValueError: For invalid username or negative indices.
    """
    _text(username, "historical award recipient", 150)
    _nonnegative_int(row_index, "historical row index")
    _nonnegative_int(ordinal, "historical item index")
    return f"cedar:baseline:{username}:{row_index}:{ordinal}"


def _persist_cedar_awards(awards: Sequence[HistoricalAward]) -> None:
    """Directly insert or verify immutable history without live service hooks.

    :param awards: Validated deterministic historical rows. Example: ().
    :return: None. Example: None.
    :raises ValueError: For conflicting existing logical rows or timestamps.
    """
    expected = {award.event_identity: asdict(award) for award in awards}
    release_ids = {
        award.playbook_id_snapshot
        for award in awards
        if award.source_kind == KarmaAward.SourceKind.RELEASE
        and award.playbook_id_snapshot is not None
    }
    change_ids = {
        award.change_id_snapshot
        for award in awards
        if award.change_id_snapshot is not None
    }
    candidates = KarmaAward.objects.filter(
        Q(recipient_id__in={award.recipient_id for award in awards})
        | Q(
            source_kind=KarmaAward.SourceKind.RELEASE,
            playbook_id_snapshot__in=release_ids,
        )
        | Q(change_id_snapshot__in=change_ids)
    )
    history = set()
    for existing in candidates.values(*HistoricalAward.__dataclass_fields__):
        identity = existing["event_identity"]
        if identity in expected:
            if existing != expected[identity]:
                raise ValueError(
                    "Cedar award conflicts with an existing event snapshot."
                )
            history.add(identity)
        elif existing["change_id_snapshot"] in change_ids or (
            existing["source_kind"] == KarmaAward.SourceKind.RELEASE
            and existing["playbook_id_snapshot"] in release_ids
        ):
            raise ValueError(
                "Cedar receipt conflicts with a different existing event identity."
            )
    pending = [
        KarmaAward(**payload) for key, payload in expected.items() if key not in history
    ]
    for award in pending:
        award.clean()
    KarmaAward.objects.bulk_create(pending)


def _verify_cedar_projection(dataset: CedarDataset) -> None:
    """Independently reconcile actual persisted contribution totals and counts.

    :param dataset: Complete actual baseline and independent oracle. Example: dataset.
    :return: None. Example: None.
    :raises ValueError: For any persisted/oracle mismatch.
    """
    service = ExpertsService()
    ids = dataset.user_ids
    totals = service._load_award_totals(tuple(ids.values()))
    live = service._load_live_counts(tuple(ids.values()))
    released = service._load_released_counts(tuple(ids.values()))
    from_oracle = {
        person["username"]: person for person in _rows(dataset.oracle, "people")
    }
    for name, user_id in ids.items():
        person = from_oracle.get(name)
        if person is None:
            if user_id in totals:
                raise ValueError("Cedar actor has conflicting award history.")
            continue
        _reconcile_cedar_person(
            person, totals.get(user_id), live[user_id], released.get(user_id, {})
        )


def _matches(row: models.Model, fields: Mapping[str, object]) -> bool:
    """Compare declared database fields without overwriting a preexisting row."""
    return all(getattr(row, name) == expected for name, expected in fields.items())


def _match_or_create[Model: models.Model](
    model: type[Model], key: dict[str, Any], fields: dict[str, Any]
) -> Model:
    """Persist deterministic fixture data or verify the full declared payload."""
    row, created = model._default_manager.get_or_create(**key, defaults=fields)
    if not created and not _matches(row, fields):
        raise ValueError(
            f"Cedar {model.__name__} import conflicts with an existing row."
        )
    return row


def _store_cedar_workflow(book: _Record) -> Workflow:
    """Persist a declared workflow or the minimum parent for published activities."""
    parent = {
        "playbook_id": book["pk"],
        "name": book.get("workflow", book["title"]),
    }
    key = {"pk": book["workflow_pk"]} if "workflow_pk" in book else parent
    return _match_or_create(Workflow, key, {**parent, "order": 1, "description": ""})


def _store_cedar_activity(
    workflow_id: int, name: str, order: int, activity_id: int | None
) -> Activity:
    """Persist only a declared current Activity and its known order."""
    identity = {"workflow_id": workflow_id, "name": name}
    lookup = {"pk": activity_id} if activity_id is not None else identity
    return _match_or_create(
        Activity, lookup, {**identity, "order": order, "guidance": ""}
    )


def _cedar_change_receipts(
    dataset: CedarDataset, recipient_id: int, category: str, source: str
) -> tuple[HistoricalAward, ...]:
    """Bind known PIP awards to the actual published change and entity identities."""
    if source not in (KarmaAward.SourceKind.MAJOR, KarmaAward.SourceKind.MINOR):
        return ()
    receipts: list[HistoricalAward] = []
    operation = (
        PipChange.CHANGE_ADD
        if source == KarmaAward.SourceKind.MAJOR
        else PipChange.CHANGE_ALTER
    )
    for pip in dataset.pips_by_key.values():
        book = dataset.playbooks_by_pk[pip.playbook_id]
        if pip.created_by_id != recipient_id or book.category != category:
            continue
        for change in pip.changes.all():
            if change.change_type != operation:
                continue
            receipts.append(
                HistoricalAward(
                    recipient_id=recipient_id,
                    event_identity=f"accepted_change:{change.pk}",
                    source_kind=source,
                    event_channel=EventChannel.ACCEPTED_CHANGE,
                    points=_AWARD_UNITS[source],
                    category=category,
                    playbook_id_snapshot=book.pk,
                    change_id_snapshot=change.pk,
                    entity_type_snapshot=change.entity_type,
                    entity_id_snapshot=change.target_id,
                    occurred_at=pip.decided_at,
                )
            )
    return tuple(receipts)


def _reconcile_cedar_person(
    person: _Record,
    awarded: AwardTotals | None,
    live: LiveContributionCounts,
    released: Mapping[str, int],
) -> None:
    """Verify source/category totals and visible counts against the independent oracle."""
    categories = dict(awarded.category_points) if awarded else {}
    sources = (
        dict(awarded.source_points) if awarded else dict.fromkeys(SOURCE_BUCKETS, 0)
    )
    primary = person.get("primary_category")
    total = awarded.total_points if awarded else 0
    if (
        total != person["total_karma"]
        or categories
        != {
            _category(label): points
            for label, points in person["karma_by_category"].items()
        }
        or sources != person["karma_by_source"]
        or resolve_primary_category(categories, released)
        != (_category(primary) if primary else None)
        or live.released_public_playbook_count != len(person["public_playbooks"])
        or live.successful_gui_copy_count != person.get("copy_count", 0)
    ):
        raise ValueError(
            "Persisted Cedar contribution projection conflicts with its independent oracle."
        )


def seed_s27_summary_privacy_variant() -> Mapping[str, Any]:
    """Extend the real Cedar baseline with independent privacy/publication cases.

    :return: Real ORM rows and expected sentinels. Example: Maria plus draft PIPs.
    :raises ValueError: If baseline/publication receipt invariants do not reconcile.
    """
    with transaction.atomic():
        dataset = load_cedar_baseline()
        maria = dataset.users_by_username["mrodriguez"]
        person = next(
            row
            for row in _rows(dataset.oracle, "people")
            if row["username"] == maria.username
        )
        receipt = PlaybookVersion.objects.get(
            pip=dataset.pips_by_key["HIST-MARIA-DESIGN-01"]
        )
        title, body = (
            "S27 Unpublished Keyboard Recovery",
            "S27 private recovery rationale",
        )
        change_body = "S27 private change guidance"
        audit_body = "S27 private version audit narrative"
        credential = "fixture-credential-for-privacy-testing"
        score = f"Karma total: {person['total_karma']}"
        submitted = ProcessImprovementProposal.objects.create(
            playbook_id=receipt.playbook_id,
            created_by=maria,
            title=title,
            summary=body,
            status=ProcessImprovementProposal.STATUS_SUBMITTED,
        )
        PipChange.objects.create(
            pip=submitted,
            change_type=PipChange.CHANGE_ADD,
            entity_type=PipChange.ENTITY_ACTIVITY,
            content=change_body,
        )
        PlaybookVersion.objects.filter(pk=receipt.pk).update(description=audit_body)
        Activity.objects.filter(
            workflow__playbook_id=6101, name="Trace Keyboard Focus"
        ).update(
            guidance=f"Check the focus order. Email {maria.email}. API key: {credential}\n{score}"
        )
        Activity.objects.filter(
            workflow__playbook_id=receipt.playbook_id, name="Error Message Review"
        ).update(guidance="Use the real published activity guidance.")
    return {
        "dataset": dataset,
        "subject_id": maria.pk,
        "submitted_pip": submitted,
        "sentinels": (
            *person["private_playbooks"],
            person["private_pip"],
            person["private_token"],
            maria.email,
            title,
            body,
            change_body,
            audit_body,
            credential,
            score,
        ),
    }


def create_reviewed_major_add_pip(
    dataset: CedarDataset, entity_type: str
) -> ProcessImprovementProposal:
    """Create an independent real reviewed Maria proposal targeting Hana's v2.0.

    :param dataset: Independently restored Cedar data. Example: load_cedar_baseline().
    :param entity_type: Major ADD entity. Example: "Artifact".
    :return: Real reviewed proposal with one undecided change. Example: ADD Artifact PIP.
    :raises ValueError: For unsupported entity or missing target structure.
    """
    payload = _major_add_change_payload(dataset, entity_type)
    book = dataset.playbooks_by_pk[6106]
    if book.version != Decimal("2.0") or book.category != "design":
        raise ValueError(
            "The Cedar major ADD case requires Hana's Design playbook v2.0."
        )
    maria = dataset.users_by_username["mrodriguez"]
    pip = PIPService.create_draft_for_playbook(
        actor=maria,
        playbook_id=book.pk,
        title=f"Add an accessibility {entity_type}",
        summary="Strengthen the form review for assistive technology.",
    )
    change = PIPService.add_change(actor=maria, pip=pip, **payload)
    # The reviewed boundary is a real ORM fixture. This case does not run Galdr.
    now = timezone.now()
    pip.status = ProcessImprovementProposal.STATUS_REVIEWED
    pip.submitted_at = now
    pip.reviewed_at = now
    pip.save(update_fields=["status", "submitted_at", "reviewed_at", "updated_at"])
    change.galdr_recommendation = PipChange.GALDR_ACCEPT
    change.save(update_fields=["galdr_recommendation", "updated_at"])
    return pip


def _major_add_change_payload(
    dataset: CedarDataset, entity_type: str
) -> dict[str, object]:
    """Supply real service fields, including parent and producer references.

    :param dataset: Restored Cedar relationships. Example: playbook 6106 and its workflow.
    :param entity_type: Eligible ADD entity. Example: "Activity".
    :return: Existing PIPService.add_change keyword payload. Example: parent_workflow_id.
    :raises ValueError: If a required workflow or producer cannot be resolved.
    """
    if entity_type not in (
        PipChange.ENTITY_ACTIVITY,
        PipChange.ENTITY_SKILL,
        PipChange.ENTITY_ARTIFACT,
    ):
        raise ValueError(
            "The Cedar major ADD case requires Activity, Skill or Artifact."
        )
    payload: dict[str, object] = {
        "change_type": PipChange.CHANGE_ADD,
        "entity_type": entity_type,
        "name": f"Assistive Technology Check {entity_type}",
        "content": "Use a screen reader to verify recovery after a form error.",
    }
    book = dataset.playbooks_by_pk[6106]
    if entity_type == PipChange.ENTITY_ACTIVITY:
        workflow = book.workflows.order_by("order", "pk").first()
        if workflow is None:
            raise ValueError("The Cedar major ADD Activity requires a parent workflow.")
        payload["parent_workflow_id"] = workflow.pk
    elif entity_type == PipChange.ENTITY_ARTIFACT:
        producer = (
            Activity.objects.filter(workflow__playbook=book).order_by("pk").first()
        )
        if producer is None:
            raise ValueError(
                "The Cedar major ADD Artifact requires a producer activity."
            )
        payload["produced_by_activity_ref"] = str(producer.pk)
    return payload


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
    states = (
        ProcessImprovementProposal.STATUS_DRAFT,
        ProcessImprovementProposal.STATUS_SUBMITTED,
        ProcessImprovementProposal.STATUS_PROCESSING_GALDR,
        ProcessImprovementProposal.STATUS_REVIEWED,
        ProcessImprovementProposal.STATUS_REJECTED,
    )
    if (
        not isinstance(dataset, CedarDataset)
        or not isinstance(status, str)
        or status not in states
    ):
        raise ValueError("Provide Cedar data and one of the five nonaccepted states.")
    with transaction.atomic():
        pip = _create_nonaccepted_draft(dataset)
        return _stage_nonaccepted_pip(dataset, pip, status)


def _create_nonaccepted_draft(dataset: CedarDataset) -> ProcessImprovementProposal:
    """Use normal draft/change builders for Hana's unchanged Design v2.0 target.

    :param dataset: Restored Cedar data. Example: Maria and Hana6106.
    :return: Actual draft with one unapplied ADD Activity. Example: draft PIP42.
    :raises ValueError: If the required released target is not the Cedar baseline.
    """
    book = dataset.playbooks_by_pk[6106]
    if (
        book.status != "released"
        or book.version != Decimal("2.0")
        or book.category != "design"
    ):
        raise ValueError("Nonaccepted Cedar cases require Hana's released Design v2.0.")
    pip = PIPService.create_draft_for_playbook(
        actor=dataset.users_by_username["mrodriguez"],
        playbook_id=book.pk,
        title="Check form recovery before accepting",
        summary="Unpublished recovery proposal for the Cedar fixture.",
    )
    PIPService.add_change(
        actor=dataset.users_by_username["mrodriguez"],
        pip=pip,
        **_major_add_change_payload(dataset, PipChange.ENTITY_ACTIVITY),
    )
    return pip


def _stage_nonaccepted_pip(
    dataset: CedarDataset, pip: ProcessImprovementProposal, status: str
) -> ProcessImprovementProposal:
    """Establish explicit ORM eligibility states; rejection uses actual staff finalization.

    :param dataset: Cedar users. Example: existing Mike staff reviewer.
    :param pip: Normal newly created draft. Example: draft ADD Activity42.
    :param status: Supported boundary. Example: "reviewed" with saved ACCEPT choice.
    :return: Persisted ineligible proposal. Example: genuinely rejected PIP42.
    :raises ValidationError: If real staff decision or finalization rejects the fixture.
    """
    if status == ProcessImprovementProposal.STATUS_DRAFT:
        return pip
    now = timezone.now()
    pip.status = pip.STATUS_REVIEWED if status == pip.STATUS_REJECTED else status
    pip.submitted_at = now
    pip.reviewed_at = now if pip.status == pip.STATUS_REVIEWED else None
    pip.save(update_fields=["status", "submitted_at", "reviewed_at", "updated_at"])
    if pip.status != pip.STATUS_REVIEWED:
        return pip
    change = pip.changes.get()
    change.galdr_recommendation = PipChange.GALDR_ACCEPT
    change.save(update_fields=["galdr_recommendation", "updated_at"])
    reviewer = dataset.users_by_username["mchen"]
    if status == pip.STATUS_REJECTED:
        return PIPAdminService.finalize_pip(
            pip,
            reviewer,
            decisions={
                change.pk: (PipChange.ADMIN_REJECT, "Rejected eligibility fixture")
            },
        )
    PIPAdminService.save_decisions(
        pip,
        reviewer,
        {change.pk: (PipChange.ADMIN_ACCEPT, "Saved choice, not finalization")},
    )
    return pip


def create_reviewed_partial_pip(dataset: CedarDataset) -> ProcessImprovementProposal:
    """Build a real two-change Maria fixture without assessment or awards.

    :param dataset: Restored Cedar data. Example: Hana6106 at version2.0.
    :return: Reviewed proposal with undecided ADD/ALTER. Example: new PIP42.
    :raises ValueError: Missing target workflow/activity or incompatible baseline.
    :raises ValidationError: If normal draft/change authorization rejects fixture inputs.
    """
    if not isinstance(dataset, CedarDataset) or 6106 not in dataset.playbooks_by_pk:
        raise ValueError("The partial decision fixture requires restored Cedar data.")
    book = dataset.playbooks_by_pk.get(6106)
    if book is None or (book.status, book.version, book.category) != (
        "released",
        Decimal("2.0"),
        "design",
    ):
        raise ValueError("Partial decisions require Hana's released Design v2.0.")
    target = Activity.objects.filter(workflow__playbook=book).order_by("pk").first()
    if target is None:
        raise ValueError("Partial decisions require an existing workflow Activity.")
    with transaction.atomic():
        pip = _create_partial_draft(dataset, target)
        return _stage_partial_review(pip)


def _create_partial_draft(
    dataset: CedarDataset, target: Activity
) -> ProcessImprovementProposal:
    """Build both unapplied changes through normal service authorization while draft.

    :param dataset: Restored original actors. Example: Maria as nonstaff submitter.
    :param target: Real existing Hana Activity. Example: one Activity of playbook6106.
    :return: Actual draft with ADD/ALTER in order. Example: two undecided changes.
    :raises ValidationError: If normal draft/change creation rejects the real inputs.
    """
    maria = dataset.users_by_username["mrodriguez"]
    pip = PIPService.create_draft_for_playbook(
        actor=maria,
        playbook_id=target.workflow.playbook_id,
        title="Add recovery coverage, retain the existing review",
        summary="Two independent staff choices in the Cedar partial decision case.",
    )
    PIPService.add_change(
        actor=maria,
        pip=pip,
        **_major_add_change_payload(dataset, PipChange.ENTITY_ACTIVITY),
    )
    PIPService.add_change(
        actor=maria,
        pip=pip,
        change_type=PipChange.CHANGE_ALTER,
        entity_type=PipChange.ENTITY_ACTIVITY,
        target_id=target.pk,
        name="S34 Rejected recovery rewrite",
        content="S34 rejected ALTER sentinel: replace the published recovery guidance.",
    )
    return pip


def _stage_partial_review(
    pip: ProcessImprovementProposal,
) -> ProcessImprovementProposal:
    """Establish an explicit reviewed ORM boundary without simulating assessment.

    :param pip: Actual two-change draft. Example: ADD then ALTER, both choices unset.
    :return: Persisted reviewed fixture. Example: submission/review timestamps, no decision.
    :raises ValueError: If normal draft construction did not produce the exact fixture.
    """
    changes = tuple(pip.changes.order_by("order", "pk"))
    if (
        pip.status != pip.STATUS_DRAFT
        or tuple(c.change_type for c in changes)
        != (PipChange.CHANGE_ADD, PipChange.CHANGE_ALTER)
        or any(c.admin_decision != PipChange.ADMIN_UNSET for c in changes)
    ):
        raise ValueError(
            "Stage only the two undecided draft changes for partial review."
        )
    pip.status = pip.STATUS_REVIEWED
    pip.submitted_at = pip.reviewed_at = timezone.now()
    pip.save(update_fields=["status", "submitted_at", "reviewed_at", "updated_at"])
    pip.changes.update(galdr_recommendation=PipChange.GALDR_ACCEPT)
    return pip
