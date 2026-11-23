from __future__ import annotations

"""Real failure fixtures and complete-ledger invariants for S46."""
from contextlib import contextmanager
from typing import Iterator
from django.contrib.auth.models import User
from tests.support.experts_data import CedarDataset

LedgerSnapshot = tuple[tuple[object, ...], ...]


def snapshot_global_ledger() -> LedgerSnapshot:
    """Read every concrete KarmaAward field ordered by primary key.

    :return: Immutable complete rows. Example: ((1, 42, ...),).
    :raises RuntimeError: Canonical award schema is unavailable.
    """
    raise NotImplementedError()


def assert_global_ledger_unchanged(before: LedgerSnapshot) -> None:
    """Compare every global award field, not only totals or row count.

    :param before: Earlier complete snapshot. Example: baseline rows.
    :return: None. Example: exact equality holds.
    :raises AssertionError: Any award was inserted, deleted or modified.
    """
    raise NotImplementedError()


def prepare_denied_target(
    dataset: CedarDataset, entity_type: str, failure: str
) -> tuple[User, int]:
    """Prepare a real private-denied or absent target with a nonstaff reader.

    :param dataset: Independently restored Cedar objects. Example: CEDAR-RFP-01.
    :param entity_type: Contract entity kind. Example: "activity".
    :param failure: Supported failure. Example: "private" or "missing".
    :return: Real actor and target PK. Example: (Elena, private_activity.pk).
    :raises ValueError: Unsupported kind or failure.
    """
    raise NotImplementedError()


@contextmanager
def revoke_token_on_next_request_finish(actor_id: int) -> Iterator[None]:
    """Revoke actual credentials after the dedicated real bundle response.

    Connect a bounded request_finished receiver; disconnect in finally.
    No service or HTTP response is replaced.

    :param actor_id: Token owner PK. Example: Maria's actual PK.
    :return: Context spanning one isolated export. Example: with helper(...).
    :raises AssertionError: No intended bundle request finished.
    """
    raise NotImplementedError()


def revoke_finished_request_token(
    *, actor_id: int, sender: object, **kwargs: object
) -> None:
    """Delete the real DRF token when the dedicated request finishes.

    :param actor_id: Token owner PK. Example: Maria's actual PK.
    :param sender: Django signal sender. Example: handler class.
    :param kwargs: Actual signal metadata. Example: signal object.
    :return: None. Example: later receipt authenticates unsuccessfully.
    :raises RuntimeError: Database revocation cannot complete.
    """
    raise NotImplementedError()
