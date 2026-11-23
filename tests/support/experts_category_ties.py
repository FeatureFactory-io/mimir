from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from django.contrib.auth.models import User
from methodology.models import Playbook
from tests.support.experts_data import CedarDataset

TieVariant = Literal["TIE01", "TIE02"]


@dataclass(frozen=True)
class CategoryTieDataset:
    baseline: CedarDataset
    variant: TieVariant
    user: User
    playbook_ids: tuple[int, ...]


def load_category_tie(variant: str) -> CategoryTieDataset:
    """Extend a fresh real Cedar baseline with one isolated variant.
    :param variant: TIE01 or TIE02; example: "TIE01".
    :return: Real ORM fixture references; example: arao plus one Development release.
    :raises ValueError: Unknown variant, before database writes.
    """
    raise NotImplementedError()


def _create_tie_playbook(user: User, category: str, ordinal: int) -> Playbook:
    """Create one authored released playbook and truthful history directly.
    :param user: Persisted variant author.
    :param category: Canonical category; example: "development".
    :param ordinal: Positive sequence for collision-free fictional names.
    :return: Released ORM playbook with one initial version.
    :raises ValueError: Invalid category, user or ordinal.
    """
    raise NotImplementedError()


def _create_tie_awards(user: User, variant: TieVariant) -> None:
    """Persist two stable historical category awards using S03 ledger schema.
    :param user: Persisted recipient.
    :param variant: Identity namespace; example: "TIE02".
    :return: None; two 5,000-point snapshots, total 10,000.
    :raises ValueError: Invalid persisted recipient or variant.
    """
    raise NotImplementedError()
