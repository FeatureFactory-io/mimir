from __future__ import annotations

from pathlib import Path
from collections.abc import Iterator
import pytest
from django.db import connections

@pytest.fixture(scope='session')
def django_db_modify_db_settings(django_db_modify_db_settings: None, tmp_path_factory: pytest.TempPathFactory) -> None:
    """Select a unique file-backed test NAME for SQLite before DB creation.

    :param django_db_modify_db_settings: Parent configuration. Example: None.
    :param tmp_path_factory: Pytest temp factory. Example: isolated event DB dir.
    :return: None; engine and production settings remain unchanged.
    :raises RuntimeError: Configuration happens after test DB initialization.
    """
    raise NotImplementedError()

@pytest.fixture
def separate_connections() -> Iterator[None]:
    """Provide real transaction-thread connection cleanup around race tests.

    :return: Iterator yielding None. Example: threads close all owned connections.
    :raises AssertionError: Worker leaks connection, thread or transaction.
    """
    raise NotImplementedError()
