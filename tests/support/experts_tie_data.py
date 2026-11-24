"""Isolated real-ORM TIE03 normalization; no production event hooks."""

from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from methodology.models import EventChannel, KarmaAward
from tests.support.experts_data import (
    CedarDataset,
    HistoricalAward,
    _baseline_time,
    _persist_cedar_awards,
    _resolve_database_scope,
    _verify_cedar_projection,
)

_ALINA_USERNAME = "apark"
_SOFIA_USERNAME = "sreed"
_DESIGN = "design"
# TIE03 in the independent Cedar oracle declares counted awards without source refs.
_TIE03_AWARD_GROUPS = (
    (KarmaAward.SourceKind.MAJOR, 30, 500),
    (KarmaAward.SourceKind.MINOR, 4, 100),
)


def apply_cedar_tie03(dataset: CedarDataset) -> CedarDataset:
    """Add Alina's historical equal-total case atomically.

    :param dataset: Loaded baseline. Example: load_cedar_baseline().
    :return: New dataset containing Alina. Example: users_by_username["apark"].
    :raises ValueError: For unsafe DB ownership, an invalid baseline or invalid awards.
    """
    if not isinstance(dataset, CedarDataset):
        raise ValueError("TIE03 requires a loaded Cedar baseline.")  # noqa: TRY004
    _resolve_database_scope(None)
    try:
        with transaction.atomic():
            _validate_tie03_baseline(dataset)
            alina = _create_tie03_user()
            _create_tie03_historical_awards(alina)
            return _dataset_with_tie03_user(dataset, alina)
    except (IntegrityError, ValidationError) as error:
        raise ValueError("TIE03 could not import Alina's historical awards.") from error


def _validate_tie03_baseline(dataset: CedarDataset) -> User:
    """Validate the untouched baseline before starting variant writes.

    :param dataset: Baseline dataset. Example: load_cedar_baseline().
    :return: Persisted Sofia. Example: User(username="sreed").
    :raises ValueError: If mapping/DB state or Sofia's ledger is inconsistent.
    """
    mapped_sofia = dataset.users_by_username.get(_SOFIA_USERNAME)
    sofia = User.objects.filter(username=_SOFIA_USERNAME).first()
    if (
        mapped_sofia is None
        or mapped_sofia._state.adding
        or sofia is None
        or mapped_sofia.pk != sofia.pk
        or mapped_sofia.username != sofia.username
    ):
        raise ValueError("TIE03 requires Sofia's persisted Cedar baseline account.")
    if (
        _ALINA_USERNAME in dataset.users_by_username
        or User.objects.filter(username=_ALINA_USERNAME).exists()
    ):
        raise ValueError("TIE03 requires a baseline without an existing Alina account.")
    try:
        _verify_cedar_projection(
            replace(dataset, users_by_username={sofia.username: sofia})
        )
    except ValueError as error:
        raise ValueError(
            "TIE03 requires Sofia's original Cedar contribution history."
        ) from error
    return sofia


def _create_tie03_user() -> User:
    """Create Alina after the baseline contributors.

    :return: Persisted contributor. Example: User(username="apark").
    :raises IntegrityError: If the reserved variant username already exists.
    """
    return User.objects.create_user(
        username=_ALINA_USERNAME, first_name="Alina", last_name="Park"
    )


def _create_tie03_historical_awards(recipient: User) -> None:
    """Import approved Design award normalization without live award hooks.

    :param recipient: Persisted Alina. Example: User(username="apark").
    :return: None. Example: None after historical rows total 15400.
    :raises ValueError: If recipient or normalized event payload is invalid.
    """
    if (
        not recipient.pk
        or recipient._state.adding
        or recipient.username != _ALINA_USERNAME
    ):
        raise ValueError("TIE03 awards require a persisted Alina account.")
    occurred_at = _baseline_time()
    _persist_cedar_awards(
        tuple(
            HistoricalAward(
                recipient_id=recipient.pk,
                event_identity=f"cedar:tie03:{recipient.username}:{source}:{index}",
                source_kind=source,
                event_channel=EventChannel.HISTORICAL,
                points=points_each,
                category=_DESIGN,
                playbook_id_snapshot=None,
                change_id_snapshot=None,
                entity_type_snapshot=None,
                entity_id_snapshot=None,
                occurred_at=occurred_at,
            )
            for source, count, points_each in _TIE03_AWARD_GROUPS
            for index in range(count)
        )
    )


def _dataset_with_tie03_user(dataset: CedarDataset, contributor: User) -> CedarDataset:
    """Extend the user mapping without mutating the baseline contract.

    :param dataset: Original baseline. Example: load_cedar_baseline().
    :param contributor: Persisted Alina. Example: User(username="apark").
    :return: New immutable mapping container. Example: CedarDataset with "apark".
    :raises ValueError: If the contributor is not the expected persisted user.
    """
    if (
        not contributor.pk
        or contributor._state.adding
        or contributor.username != _ALINA_USERNAME
    ):
        raise ValueError("TIE03 requires a persisted Alina account.")
    users = {**dataset.users_by_username, _ALINA_USERNAME: contributor}
    return replace(dataset, users_by_username=MappingProxyType(users))
