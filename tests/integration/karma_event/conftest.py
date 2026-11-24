from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

import pytest

from methodology.services.karma_service import AwardSpec, KarmaService
from tests.support.experts_data import CedarDataset


@pytest.fixture(scope="session")
def django_db_modify_db_settings(django_db_modify_db_settings: None) -> None:
    """Keep pytest-django's owned test database for the Cedar importer.

    :param django_db_modify_db_settings: Standard runner setup. Example: None.
    :return: None. Example: leave the owned SQLite shared-memory setup in place.
    """
    return django_db_modify_db_settings


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
    raise NotImplementedError()
