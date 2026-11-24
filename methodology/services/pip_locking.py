"""Shared parent-row locking for PIP mutations."""

from __future__ import annotations

from django.db import connections
from django.db.models import F, QuerySet
from django.db.transaction import TransactionManagementError

from methodology.models import ProcessImprovementProposal


def lock_proposal_queryset(
    proposals: QuerySet[ProcessImprovementProposal],
) -> QuerySet[ProcessImprovementProposal]:
    """Prepare current proposal rows for a locking read in the caller's transaction.

    :param proposals: Parent rows to lock. Example: proposals filtered by ID.
    :return: Locking queryset in primary-key order. Evaluate it before writing.
    :raises TypeError: If given something other than a proposal queryset.
    :raises TransactionManagementError: If the caller does not own an atomic block.
    """
    if (
        not isinstance(proposals, QuerySet)
        or proposals.model is not ProcessImprovementProposal
    ):
        raise TypeError("PIP review locks require a proposal queryset.")
    locked = proposals.select_for_update(of=("self",)).order_by("pk")
    connection = connections[locked.db]
    if not connection.in_atomic_block:
        raise TransactionManagementError("PIP review locks require a transaction.")
    if connection.vendor == "sqlite":
        # SQLite ignores SELECT FOR UPDATE. Acquire its write lock before any
        # proposal read in this transaction can establish an older snapshot.
        locked.update(status=F("status"))
    return locked
