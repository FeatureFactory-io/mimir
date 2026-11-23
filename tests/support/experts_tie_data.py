from __future__ import annotations

"""Isolated real-ORM TIE03 normalization; no production event hooks."""
from django.contrib.auth.models import User
from tests.support.experts_data import CedarDataset


def apply_cedar_tie03(dataset: CedarDataset) -> CedarDataset:
    """Add Alina's historical equal-total case atomically.

    :param dataset: Loaded baseline. Example: load_cedar_baseline().
    :return: New dataset containing Alina. Example: users_by_username["apark"].
    :raises ValueError: If Sofia is missing, altered or Alina already exists.
    :raises NotImplementedError: Until the approved fixture contract is implemented.
    """
    raise NotImplementedError()


def _validate_tie03_baseline(dataset: CedarDataset) -> User:
    """Validate the untouched baseline before starting variant writes.

    :param dataset: Baseline dataset. Example: load_cedar_baseline().
    :return: Persisted Sofia. Example: User(username="sreed").
    :raises ValueError: If mapping/DB state or Sofia's ledger is inconsistent.
    :raises NotImplementedError: Until fixture validation is implemented.
    """
    raise NotImplementedError()


def _create_tie03_user() -> User:
    """Create Alina after the baseline contributors.

    :return: Persisted contributor. Example: User(username="apark").
    :raises ValueError: If the reserved variant username already exists.
    :raises NotImplementedError: Until isolated user creation is implemented.
    """
    raise NotImplementedError()


def _create_tie03_historical_awards(recipient: User) -> None:
    """Import approved Design award normalization without live award hooks.

    :param recipient: Persisted Alina. Example: User(username="apark").
    :return: None. Example: None after historical rows total 15400.
    :raises ValueError: If recipient or normalized event payload is invalid.
    :raises NotImplementedError: Until the reconciled ledger import is implemented.
    """
    raise NotImplementedError()


def _dataset_with_tie03_user(dataset: CedarDataset, contributor: User) -> CedarDataset:
    """Extend the user mapping without mutating the baseline contract.

    :param dataset: Original baseline. Example: load_cedar_baseline().
    :param contributor: Persisted Alina. Example: User(username="apark").
    :return: New immutable mapping container. Example: CedarDataset with "apark".
    :raises ValueError: If the contributor is not the expected persisted user.
    :raises NotImplementedError: Until immutable dataset extension is implemented.
    """
    raise NotImplementedError()
