from __future__ import annotations

"""Real Django-client contracts for the existing own-profile summary."""
import pytest
from django.test import Client
from tests.support.experts_data import CedarDataset

pytestmark = pytest.mark.django_db


def test_profile_summary_contract_with_seeded_maria_returns_complete_stored_paragraph(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove complete stored text reaches the authenticated production response.

    :param client: Real Django client. Example: Client().
    :param cedar_dataset: Isolated ORM baseline. Example: Maria under "mrodriguez".
    :return: None. Example: all nine sentences match the stored paragraph.
    :raises AssertionError: If status, full text or persisted text differs.
    :raises NotImplementedError: Until the approved proof is implemented.
    """
    raise NotImplementedError()


def test_profile_summary_markup_with_long_paragraph_links_button_to_region(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove initial semantics without claiming browser execution.

    :param client: Real Django client. Example: Client().
    :param cedar_dataset: Isolated ORM baseline. Example: Maria's long summary.
    :return: None. Example: one native toggle controls the unique summary region.
    :raises AssertionError: If ARIA, native type, uniqueness or account hooks differ.
    :raises NotImplementedError: Until the approved proof is implemented.
    """
    raise NotImplementedError()
