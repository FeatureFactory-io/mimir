"""Real test-runner ownership propagation into the existing stdio client."""

from __future__ import annotations

from collections.abc import Iterator
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir

import pytest
from django.db import connections
from rest_framework.authtoken.models import Token

from tests.integration.karma_event.conftest import (
    _activate_race_sqlite,
    _declare_sqlite_test_file,
)
from tests.support.experts_data import (
    CedarDatabaseScope,
    CedarDataset,
    _register_sqlite_test_scope,
    load_cedar_baseline,
)
from tests.support.karma_mcp import MCPDataset, StdioMCPClient


@pytest.fixture(params=("active", "expired"))
def guarded_stdio_database(
    request: pytest.FixtureRequest,
    transactional_db: None,
) -> Iterator[tuple[CedarDatabaseScope, MCPDataset, str]]:
    """Activate a genuine private runner SQLite DB and vary registration lifetime.

    :param request: Actual fixture request used for live scope registration.
    :param transactional_db: Original runner lifecycle outside the owned alias.
    :return: Scope and real imported dataset with active/expired ownership.
    """
    with TemporaryDirectory(
        prefix="mimir-stdio-scope-", dir=Path(gettempdir()).resolve()
    ) as directory:
        scope = _declare_sqlite_test_file(Path(directory))
        runner = deepcopy(connections.databases["default"])
        runner.update(
            ENGINE="django.db.backends.sqlite3",
            NAME=scope.database_name,
            OPTIONS={"timeout": 20},
            USER="",
            PASSWORD="",
            HOST="",
            PORT="",
            CONN_MAX_AGE=0,
            CONN_HEALTH_CHECKS=False,
        )
        runner["TEST"]["NAME"] = scope.database_name
        with _activate_race_sqlite(runner) as sqlite:
            with _register_sqlite_test_scope(scope, request):
                sqlite.creation.create_test_db(
                    verbosity=0, autoclobber=True, keepdb=True
                )
                dataset = MCPDataset(load_cedar_baseline(scope=scope), {}, {})
                if request.param == "active":
                    yield scope, dataset, "active"
                    return
            yield scope, dataset, "expired"


def _client(dataset: MCPDataset, root: Path, **kwargs: object) -> StdioMCPClient:
    """Construct the existing real facade protocol support client.

    :param dataset: Real ORM fixture references.
    :param root: Actual test-owned process directory.
    :param kwargs: Explicit ownership options, e.g. database_scope.
    :return: Unopened existing StdioMCPClient; no replacement executor.
    """
    return StdioMCPClient(
        entrypoint="facade",
        actor_username="mrodriguez",
        dataset=dataset,
        server_url="http://localhost:12345",
        root=root,
        **kwargs,
    )


def test_stdio_backend_with_default_runner_scope_preserves_legacy_caller(
    cedar_dataset: CedarDataset,
    tmp_path: Path,
) -> None:
    """Keep the original no-scope facade caller on the real normal runner.

    :param cedar_dataset: Actual runner-owned Cedar fixture.
    :param tmp_path: Owned subprocess directory.
    :return: None; backend resolves a real persisted actor token.
    """
    dataset = MCPDataset(cedar_dataset, {}, {})
    client = _client(dataset, tmp_path)
    client._prepare_backend()
    actor = cedar_dataset.users_by_username["mrodriguez"]
    assert Token.objects.filter(user=actor, key=client._token).exists()
    assert client._database is None
    client.__exit__(None, None, None)


def test_stdio_backend_with_explicit_scope_obeys_actual_registration_lifetime(
    guarded_stdio_database: tuple[CedarDatabaseScope, MCPDataset, str],
    tmp_path: Path,
) -> None:
    """Honor live explicit ownership and reject the unchanged claim after exit.

    :param guarded_stdio_database: Real file runner with live/expired fixture proof.
    :param tmp_path: Actual child process directory.
    :return: None; only live registration may resolve backend actor credentials.
    """
    scope, dataset, lifetime = guarded_stdio_database
    client = _client(dataset, tmp_path, database_scope=scope)
    before = Token.objects.count()
    if lifetime == "expired":
        with pytest.raises(ValueError, match="runner-owned"):
            client._prepare_backend()
        assert Token.objects.count() == before and client._token == ""
    else:
        client._prepare_backend()
        assert Token.objects.filter(key=client._token).exists()
    client.__exit__(None, None, None)


def test_stdio_backend_with_file_scope_omitted_does_not_infer_ownership(
    guarded_stdio_database: tuple[CedarDatabaseScope, MCPDataset, str],
    tmp_path: Path,
) -> None:
    """Keep file-backed ownership explicit even during an active registration.

    :param guarded_stdio_database: Real file and real declaration/registration.
    :param tmp_path: Owned child process directory.
    :return: None; absent constructor proof rejects before token lookup.
    """
    _scope, dataset, _lifetime = guarded_stdio_database
    client = _client(dataset, tmp_path)
    before = Token.objects.count()
    with pytest.raises(ValueError, match="explicit run ownership"):
        client._prepare_backend()
    assert Token.objects.count() == before and client._token == ""
    client.__exit__(None, None, None)


def test_stdio_backend_with_counterfeit_owner_rejects_before_token_lookup(
    guarded_stdio_database: tuple[CedarDatabaseScope, MCPDataset, str],
    tmp_path: Path,
) -> None:
    """Passing a scope does not bypass the original exact owner-file validation.

    :param guarded_stdio_database: Real file with actual owner record.
    :param tmp_path: Owned child directory, e.g. pytest tmp_path.
    :return: None; forged constructor proof never creates or resolves a token.
    """
    scope, dataset, _lifetime = guarded_stdio_database
    forged = replace(scope, owner_id="0" * 32)
    client = _client(dataset, tmp_path, database_scope=forged)
    before = Token.objects.count()
    with pytest.raises(ValueError, match="ownership does not match"):
        client._prepare_backend()
    assert Token.objects.count() == before and client._token == ""
    client.__exit__(None, None, None)
