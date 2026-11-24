"""Private race databases must not leak into later asynchronous ORM calls."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from asgiref.sync import SyncToAsync, sync_to_async
from django.core.exceptions import ImproperlyConfigured
from django.db import connections

from tests.integration.karma_event.conftest import _activate_race_sqlite

_EXECUTOR_WAIT_SECONDS = 30


@pytest.mark.django_db(transaction=True)
def test_private_sqlite_with_invalid_backend_restores_runner_before_yield() -> None:
    """Preserve both existing wrappers when real backend creation fails.

    :return: None; invalid setup cannot alter the next ordinary ORM operation.
    :raises AssertionError: The original aliases or worker connection are lost.
    """
    before = asyncio.run(sync_to_async(_connection_snapshot)())
    main = connections["default"]
    declared = connections.databases["default"]
    executor = SyncToAsync.single_thread_executor
    worker = executor.submit(connections.__getitem__, "default").result(
        timeout=_EXECUTOR_WAIT_SECONDS
    )
    invalid = deepcopy(declared)
    invalid["ENGINE"] = "mimir.unavailable_test_backend"
    try:
        with pytest.raises(ImproperlyConfigured), _activate_race_sqlite(invalid):
            pytest.fail("Invalid backend unexpectedly opened")
        assert connections.databases["default"] is declared
        assert connections["default"] is main
        assert asyncio.run(sync_to_async(_connection_snapshot)()) == before
    finally:
        connections.databases["default"] = declared
        connections["default"] = main
        executor.submit(connections.__setitem__, "default", worker).result(
            timeout=_EXECUTOR_WAIT_SECONDS
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("body_fails", (False, True))
def test_private_sqlite_with_async_orm_restores_original_thread_connection(
    tmp_path: Path, body_fails: bool
) -> None:
    """Keep actual thread-local connection identity across normal/error teardown.

    :param tmp_path: Test-owned directory for a real temporary SQLite file.
    :param body_fails: Whether the private database scope raises during its body.
    :return: None; the original asynchronous runner connection remains usable.
    :raises AssertionError: A private connection escapes its owning scope.
    """
    before = asyncio.run(sync_to_async(_connection_snapshot)())
    private = _private_sqlite_settings(tmp_path)
    try:
        with _activate_race_sqlite(private):
            during = asyncio.run(sync_to_async(_connection_snapshot)())
            assert during[1] == private["NAME"]
            assert during[0] != before[0]
            if body_fails:
                raise RuntimeError("deliberate fixture body failure")
    except RuntimeError as error:
        assert body_fails and str(error) == "deliberate fixture body failure"
    assert asyncio.run(sync_to_async(_connection_snapshot)()) == before


def _private_sqlite_settings(directory: Path) -> dict[str, Any]:
    """Declare a test-owned SQLite lane independently of the primary backend.

    :param directory: Actual pytest temporary directory for this test.
    :return: Private SQLite settings, even when the main CI runner is PostgreSQL.
    :raises KeyError: The runner has no default database configuration.
    """
    private = deepcopy(connections.databases["default"])
    private.update(
        ENGINE="django.db.backends.sqlite3",
        NAME=str(directory / "private.sqlite3"),
        OPTIONS={"timeout": 20},
        USER="",
        PASSWORD="",
        HOST="",
        PORT="",
        CONN_MAX_AGE=0,
        CONN_HEALTH_CHECKS=False,
    )
    private["TEST"]["NAME"] = private["NAME"]
    return private


def _connection_snapshot() -> tuple[int, str, int]:
    """Read identity and a real SQL result on the asynchronous ORM worker.

    :return: Actual wrapper identity, database name and scalar SELECT result.
    :raises DatabaseError: The currently active test database cannot be queried.
    """
    database = connections["default"]
    with database.cursor() as cursor:
        cursor.execute("SELECT 1")
        return id(database), str(database.settings_dict["NAME"]), cursor.fetchone()[0]
