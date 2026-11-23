from __future__ import annotations

import pytest
from django.test import Client


@pytest.mark.django_db
def test_profile_sources_with_cedar_ledger_reconcile(client: Client) -> None:
    """Prove baseline ORM source arithmetic matches actual profile HTTP.

    :param client: Real Django test client. Example: authenticated Maria.
    :return: None. Example: 5000 + 1600 + 1200 + 400 equals rendered 8200.
    :raises AssertionError: If ORM, production HTML or source ordering differs.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_profile_sources_with_new_learning_award_refresh_values(client: Client) -> None:
    """Prove numeric presentation reads current ledger without GET awards.

    :param client: Real Django test client. Example: Maria after a test learning award.
    :return: None. Example: Learning 405 and total 8205 without prose changes.
    :raises AssertionError: If values are cached, summary changes or GET writes awards.
    """
    raise NotImplementedError()
