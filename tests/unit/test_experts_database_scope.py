"""Proofs of the Cedar importer's file-backed SQLite ownership boundary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from contextvars import Context, copy_context
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir
from uuid import uuid4

import pytest
from django.conf import settings
from django.db.backends.sqlite3.base import DatabaseWrapper

from tests.support import experts_data
from tests.support.experts_data import CedarDatabaseScope

_COUNTERFEIT_SQLITE_RUNTIME = """
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir
from uuid import uuid4

import django

django.setup()
from django.db import connections
from tests.support.experts_data import CedarDatabaseScope, load_cedar_baseline

if sys.argv[1] == "import-pytest":
    import pytest
else:
    assert "pytest" not in sys.modules
assert "pytest_django" not in sys.modules
os.environ["PYTEST_CURRENT_TEST"] = "tests/unit/test_claim.py::test_claim (call)"
sqlite = connections["default"]
assert sqlite.vendor == "sqlite" and sqlite.connection is None
with TemporaryDirectory(dir=Path(gettempdir()).resolve()) as directory:
    database = Path(directory) / "test.sqlite3"
    database.touch(mode=0o600)
    marker = database.with_name("owner.json")
    marker.touch(mode=0o600)
    owner = uuid4().hex
    marker.write_text(
        json.dumps({"database": str(database), "owner_id": owner, "pid": os.getpid()}),
        encoding="utf-8",
    )
    sqlite.settings_dict["NAME"] = str(database)
    sqlite.settings_dict["TEST"]["NAME"] = str(database)
    scope = CedarDatabaseScope("test", str(database), marker, owner)
    try:
        load_cedar_baseline(database.with_name("must-not-read.json"), scope=scope)
    except ValueError as error:
        assert "runner-owned" in str(error), error
    else:
        raise AssertionError("Counterfeit pytest environment was accepted.")
    assert sqlite.connection is None
    assert database.read_bytes() == b""
"""


@pytest.fixture
def sqlite_test_file(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[CedarDatabaseScope, DatabaseWrapper]]:
    """Declare a private real SQLite file while keeping the test runner's DB intact."""
    with TemporaryDirectory(dir=Path(gettempdir()).resolve()) as directory:
        database = Path(directory) / "test.sqlite3"
        database.touch(mode=0o600)
        marker = database.with_name("owner.json")
        owner = uuid4().hex
        marker.touch(mode=0o600)
        _write_marker(marker, database, owner, os.getpid())
        actual = deepcopy(experts_data.connection.settings_dict)
        actual.update(ENGINE="django.db.backends.sqlite3", NAME=str(database))
        actual["TEST"]["NAME"] = str(database)
        declared = settings.DATABASES["default"]["TEST"]
        monkeypatch.setitem(declared, "NAME", str(database))
        sqlite = DatabaseWrapper(actual, alias="default")
        scope = CedarDatabaseScope("test", str(database), marker, owner)
        monkeypatch.setattr(experts_data, "connection", sqlite)
        try:
            yield scope, sqlite
        finally:
            sqlite.close()


@pytest.fixture
def owned_sqlite(
    sqlite_test_file: tuple[CedarDatabaseScope, DatabaseWrapper],
    request: pytest.FixtureRequest,
) -> Iterator[tuple[CedarDatabaseScope, DatabaseWrapper]]:
    """Register the real Django wrapper's claim from the active pytest fixture."""
    scope, _sqlite = sqlite_test_file
    with experts_data._register_sqlite_test_scope(scope, request):
        yield sqlite_test_file


@pytest.fixture(params=("unregistered", "expired"))
def unregistered_sqlite(
    sqlite_test_file: tuple[CedarDatabaseScope, DatabaseWrapper],
    request: pytest.FixtureRequest,
) -> tuple[CedarDatabaseScope, DatabaseWrapper]:
    """Provide an owned file with no live registration during the test call."""
    if request.param == "expired":
        scope, sqlite = sqlite_test_file
        with experts_data._register_sqlite_test_scope(scope, request):
            assert sqlite.connection is None
    return sqlite_test_file


@pytest.fixture
def expired_sqlite_context(
    sqlite_test_file: tuple[CedarDatabaseScope, DatabaseWrapper],
    request: pytest.FixtureRequest,
) -> Context:
    """Capture active fixture authority, then end the registration during setup.

    :param sqlite_test_file: Real private SQLite file and wrapper.
    :param request: Active test runner fixture request.
    :return: A snapshot copied before registration ended.
    """
    scope, _sqlite = sqlite_test_file
    with experts_data._register_sqlite_test_scope(scope, request):
        snapshot = copy_context()
        snapshot.run(experts_data._require_registered_sqlite_scope, scope)
    return snapshot


@pytest.fixture(params=("normal", "exception"))
def expired_nested_sqlite_context(
    owned_sqlite: tuple[CedarDatabaseScope, DatabaseWrapper],
    request: pytest.FixtureRequest,
) -> Context:
    """Capture inner authority while the outer registration remains active.

    :param owned_sqlite: File backed by the outer registration.
    :param request: Active fixture request with the inner exit kind.
    :return: A snapshot of the closed inner registration.
    """
    scope, _sqlite = owned_sqlite
    exceptional_exit = request.param == "exception"
    message = "fixture body failed"
    exit_check = (
        pytest.raises(RuntimeError, match=message)
        if exceptional_exit
        else nullcontext()
    )
    with exit_check, experts_data._register_sqlite_test_scope(scope, request):
        snapshot = copy_context()
        snapshot.run(experts_data._require_registered_sqlite_scope, scope)
        if exceptional_exit:
            raise RuntimeError(message)
    return snapshot


def _write_marker(marker: Path, database: Path, owner_id: str, pid: int) -> None:
    """Write the exact local test-run owner proof consumed by the guard."""
    marker.write_text(
        json.dumps({"database": str(database), "owner_id": owner_id, "pid": pid}),
        encoding="utf-8",
    )


def test_check_file_scope_with_runner_owned_database_uses_live_pragma(
    owned_sqlite: tuple[CedarDatabaseScope, DatabaseWrapper],
) -> None:
    """Require real pytest runtime, explicit evidence and a real SQLite connection."""
    scope, sqlite = owned_sqlite
    assert os.environ["PYTEST_CURRENT_TEST"].endswith("(call)")
    assert sqlite.connection is None
    experts_data._validate_database_scope(scope)
    assert sqlite.connection is not None


def test_check_file_scope_with_copied_live_registration_uses_live_pragma(
    owned_sqlite: tuple[CedarDatabaseScope, DatabaseWrapper],
) -> None:
    """Copied context shares live authority while an empty thread has none.

    :param owned_sqlite: An active real SQLite registration for this pytest item.
    """
    scope, sqlite = owned_sqlite
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            Context().run, experts_data._validate_database_scope, scope
        )
        with pytest.raises(ValueError, match="registered by an active pytest fixture"):
            future.result()
    assert sqlite.connection is None
    copy_context().run(experts_data._validate_database_scope, scope)
    assert sqlite.connection is not None


def test_check_file_scope_with_copied_expired_registration_rejects_before_opening(
    sqlite_test_file: tuple[CedarDatabaseScope, DatabaseWrapper],
    expired_sqlite_context: Context,
    request: pytest.FixtureRequest,
) -> None:
    """Reject copied setup authority during the same active pytest item's call.

    :param sqlite_test_file: An otherwise valid private file and unopened wrapper.
    :param expired_sqlite_context: The active setup context retained after expiry.
    :param request: The same test runner item that activated the fixture.
    """
    scope, sqlite = sqlite_test_file
    assert os.environ["PYTEST_CURRENT_TEST"] == f"{request.node.nodeid} (call)"
    assert sqlite.connection is None
    with pytest.raises(ValueError, match="registered by an active pytest fixture"):
        expired_sqlite_context.run(experts_data._validate_database_scope, scope)
    assert sqlite.connection is None
    assert Path(scope.database_name).read_bytes() == b""


def test_check_file_scope_with_closed_nested_registration_restores_live_outer(
    owned_sqlite: tuple[CedarDatabaseScope, DatabaseWrapper],
    expired_nested_sqlite_context: Context,
) -> None:
    """Revoke the copied inner registration without disturbing the live outer one.

    :param owned_sqlite: The still-live outer registration for the same scope.
    :param expired_nested_sqlite_context: Snapshot of the exited inner registration.
    """
    scope, sqlite = owned_sqlite
    with pytest.raises(ValueError, match="registered by an active pytest fixture"):
        expired_nested_sqlite_context.run(experts_data._validate_database_scope, scope)
    assert sqlite.connection is None
    experts_data._validate_database_scope(scope)
    assert sqlite.connection is not None


def test_check_file_scope_with_active_unregistered_pytest_rejects_before_opening(
    unregistered_sqlite: tuple[CedarDatabaseScope, DatabaseWrapper],
) -> None:
    """A real running pytest process must have registered the specific file."""
    scope, sqlite = unregistered_sqlite
    assert os.environ["PYTEST_CURRENT_TEST"].endswith("(call)")
    with pytest.raises(ValueError, match="runner-owned"):
        experts_data._validate_database_scope(scope)
    assert sqlite.connection is None


@pytest.mark.parametrize("pytest_import", ("without-pytest", "import-pytest"))
def test_check_file_scope_with_counterfeit_standalone_runner_rejects_before_import(
    pytest_import: str,
) -> None:
    """Django outside pytest rejects an otherwise matching proof before SQL or seed I/O."""
    environment = {
        **os.environ,
        "DATABASE_URL": "",
        "DJANGO_SETTINGS_MODULE": "mimir.settings.test",
        "MIMIR_ENV": "test",
    }
    result = subprocess.run(
        [sys.executable, "-c", _COUNTERFEIT_SQLITE_RUNTIME, pytest_import],
        env=environment,
        cwd=Path(settings.BASE_DIR),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "case", ("wrong-module", "wrong-environment", "no-pytest", "wrong-node", "teardown")
)
def test_check_file_scope_with_invalid_runtime_rejects_before_opening(
    owned_sqlite: tuple[CedarDatabaseScope, DatabaseWrapper],
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    """A legitimate temporary file and owner marker cannot authorize a wrong runtime."""
    scope, sqlite = owned_sqlite
    if case == "wrong-module":
        monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "mimir.settings.prod")
    elif case == "wrong-environment":
        monkeypatch.setattr(settings, "MIMIR_ENV", "prod")
    elif case == "no-pytest":
        monkeypatch.delenv("PYTEST_CURRENT_TEST")
    elif case == "wrong-node":
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "other.py::test_node (call)")
    else:
        marker = os.environ["PYTEST_CURRENT_TEST"].removesuffix(" (call)")
        monkeypatch.setenv("PYTEST_CURRENT_TEST", f"{marker} (teardown)")
    with pytest.raises(ValueError, match="runner-owned"):
        experts_data._validate_database_scope(scope)
    assert sqlite.connection is None


@pytest.mark.parametrize(
    "case",
    (
        "missing-owner",
        "wrong-run",
        "wrong-pid",
        "public-marker",
        "public-file",
        "hardlink",
    ),
)
def test_check_file_scope_with_invalid_owner_rejects_before_opening(
    owned_sqlite: tuple[CedarDatabaseScope, DatabaseWrapper], case: str
) -> None:
    """Require current run ownership and private single-link regular files."""
    scope, sqlite = owned_sqlite
    database = Path(scope.database_name)
    marker = scope.ownership_manifest
    assert marker is not None and scope.owner_id is not None
    if case == "missing-owner":
        scope = replace(scope, ownership_manifest=None, owner_id=None)
    elif case == "wrong-run":
        _write_marker(marker, database, uuid4().hex, os.getpid())
    elif case == "wrong-pid":
        _write_marker(marker, database, scope.owner_id, os.getpid() + 1)
    elif case == "public-marker":
        marker.chmod(0o644)
    elif case == "public-file":
        database.chmod(0o644)
    else:
        database.with_name("another-link.sqlite3").hardlink_to(database)
    with pytest.raises(ValueError, match="ownership|private"):
        experts_data._validate_database_scope(scope)
    assert sqlite.connection is None


@pytest.mark.parametrize("case", ("runner-name", "ambient", "seed", "symlink"))
def test_check_file_scope_with_unsafe_path_rejects_before_opening(
    owned_sqlite: tuple[CedarDatabaseScope, DatabaseWrapper],
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    """Reject mismatched declarations, non-private paths, tracked seed and symlinks."""
    scope, sqlite = owned_sqlite
    database = Path(scope.database_name)
    test_settings = settings.DATABASES["default"]["TEST"]
    if case == "runner-name":
        monkeypatch.setitem(test_settings, "NAME", str(database.with_suffix(".other")))
    elif case == "ambient":
        database.parent.chmod(0o755)
    else:
        if case == "seed":
            target = Path(settings.BASE_DIR).resolve() / "mimir.db"
        else:
            target = database.with_name("linked.sqlite3")
            target.symlink_to(database)
        scope = replace(
            scope,
            database_name=str(target),
            ownership_manifest=target.with_name("owner.json"),
        )
        sqlite.settings_dict.update(NAME=str(target), TEST={"NAME": str(target)})
        monkeypatch.setitem(test_settings, "NAME", str(target))
    with pytest.raises(ValueError, match="runner|private"):
        experts_data._validate_database_scope(scope)
    assert sqlite.connection is None


def test_check_file_scope_with_wrong_open_database_rejects_live_pragma(
    owned_sqlite: tuple[CedarDatabaseScope, DatabaseWrapper],
) -> None:
    """An already-open connection must agree with the declaration and marker."""
    scope, sqlite = owned_sqlite
    declared = sqlite.settings_dict["NAME"]
    sqlite.settings_dict["NAME"] = str(Path(declared).with_name("separate.sqlite3"))
    with sqlite.cursor() as cursor:
        cursor.execute("SELECT 1")
        assert cursor.fetchone() == (1,)
    sqlite.settings_dict["NAME"] = declared
    with pytest.raises(ValueError, match="open database"):
        experts_data._validate_database_scope(scope)
