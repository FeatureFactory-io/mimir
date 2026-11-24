from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir
from typing import Any
from uuid import UUID, uuid4

import pytest
from django.core.management import call_command
from django.db import connection, connections
from django.db.backends.base.base import BaseDatabaseWrapper
from pytest_django.plugin import DjangoDbBlocker

from methodology.services.karma_service import AwardSpec, KarmaService
from tests.support.experts_data import (
    CedarDatabaseScope,
    CedarDataset,
    _register_sqlite_test_scope,
    _validate_database_scope,
    load_cedar_baseline,
)


@pytest.fixture(scope="session")
def owned_race_sqlite(
    django_db_blocker: DjangoDbBlocker, request: pytest.FixtureRequest
) -> Iterator[tuple[CedarDatabaseScope, dict[str, Any]] | None]:
    """Build a session-private SQLite lane with Django's real test DB creation.

    :param django_db_blocker: The real pytest-django database access guard.
    :param request: The pytest fixture request for the initial test setup.
    :return: SQLite ownership and runner settings, or None for PostgreSQL.
    :raises OSError: If the runner cannot create private local files.
    """
    if connection.vendor != "sqlite":
        yield None
        return
    with TemporaryDirectory(
        prefix="mimir-s45-", dir=Path(gettempdir()).resolve()
    ) as directory:
        scope = _declare_sqlite_test_file(Path(directory))
        runner_settings = deepcopy(connections.databases["default"])
        runner_settings["TEST"]["NAME"] = scope.database_name
        with (
            _register_sqlite_test_scope(scope, request),
            _activate_race_sqlite(runner_settings) as sqlite,
            django_db_blocker.unblock(),
        ):
            # The preallocated file is empty and private. Keep it so Django retains its mode.
            sqlite.creation.create_test_db(verbosity=0, autoclobber=True, keepdb=True)
            _validate_database_scope(scope)
            call_command("loaddata", "tests/fixtures/e2e_seed.json", verbosity=0)
        yield scope, runner_settings


@pytest.fixture
def django_db_setup(
    django_db_setup: None,
    owned_race_sqlite: tuple[CedarDatabaseScope, dict[str, Any]] | None,
    request: pytest.FixtureRequest,
) -> Iterator[CedarDatabaseScope | None]:
    """Use the private alias for the full S45 lifecycle, including pytest flush.

    :param django_db_setup: Existing pytest-django session setup, kept independent.
    :param owned_race_sqlite: Session-private file and its Django configuration.
    :param request: The pytest fixture request for this test's alias activation.
    :return: Explicit SQLite proof or None under standard PostgreSQL isolation.
    """
    if owned_race_sqlite is None:
        yield django_db_setup
        return
    scope, runner_settings = owned_race_sqlite
    with (
        _register_sqlite_test_scope(scope, request),
        _activate_race_sqlite(runner_settings),
    ):
        yield scope


@contextmanager
def _activate_race_sqlite(
    settings_dict: dict[str, Any],
) -> Iterator[BaseDatabaseWrapper]:
    """Install the runner declaration for ORM threads and preserve the normal alias."""
    original = connections["default"]
    declared = connections.databases
    previous = declared["default"]
    declared["default"] = settings_dict
    sqlite = connections.create_connection("default")
    connections["default"] = sqlite
    try:
        yield sqlite
    finally:
        try:
            sqlite.close()
        finally:
            connections["default"] = original
            declared["default"] = previous


def _declare_sqlite_test_file(directory: Path) -> CedarDatabaseScope:
    """Create the private runner's file and bind its marker to this process/run."""
    database = directory / "test.sqlite3"
    database.touch(mode=0o600, exist_ok=False)
    owner = uuid4().hex
    marker = directory / "owner.json"
    marker.touch(mode=0o600, exist_ok=False)
    record = {"database": str(database), "owner_id": owner, "pid": os.getpid()}
    marker.write_text(json.dumps(record), encoding="utf-8")
    return CedarDatabaseScope("test", str(database), marker, owner)


@pytest.fixture
def cedar_dataset(
    transactional_db: None, django_db_setup: CedarDatabaseScope | None
) -> CedarDataset:
    """Import Cedar into the actual runner database only after ownership is proven.

    :param transactional_db: Real committed fixture rows visible to worker connections.
    :param django_db_setup: Explicit runner proof for file-backed SQLite.
    :return: Real Cedar actors, history and content.
    :raises ValueError: The active database ownership proof failed.
    """
    return load_cedar_baseline(scope=django_db_setup)


@pytest.fixture
def consumption_specs(cedar_dataset: CedarDataset) -> tuple[AwardSpec, ...]:
    """Build one frozen pair from an actual authorized Cedar Activity.

    :param cedar_dataset: Real imported Cedar accounts and their playbooks.
    :return: Learning and consumption specs. Example: Maria and Mike, five each.
    :raises PermissionError: If the fixture actor loses access to the Activity.
    """
    actor = cedar_dataset.users_by_username["mrodriguez"]
    target = KarmaService._resolve_consumption_target(actor, "activity", 6203)
    channel = "gui_copy"
    identity = KarmaService._canonical_consumption_identity(
        actor.pk, UUID(int=45), channel
    )
    return KarmaService._build_consumption_specs(
        actor, target, identity, channel=channel
    )


@pytest.fixture
def separate_connections() -> Iterator[None]:
    """Provide real transaction-thread connection cleanup around race tests.

    :return: Iterator yielding None. Example: threads close all owned connections.
    :raises AssertionError: Worker leaks connection, thread or transaction.
    """
    assert connection.get_autocommit() and not connection.in_atomic_block
    try:
        yield
    finally:
        assert connection.get_autocommit() and not connection.in_atomic_block
