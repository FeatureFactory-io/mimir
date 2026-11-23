"""Shared real Cedar fixtures visible under both pytest configurations."""

from __future__ import annotations

import pytest

from tests.support.experts_data import CedarDataset, load_cedar_baseline


@pytest.fixture
def cedar_dataset(db: None) -> CedarDataset:
    """Load the real Cedar baseline once under the actual test lifecycle.

    :param db: Runner-owned database access. Example: None.
    :return: Real imported objects and independent oracle. Example: CedarDataset.
    :raises ValueError: Unsafe database ownership or invalid history.
    """
    return load_cedar_baseline()


@pytest.fixture
def cedar_baseline(cedar_dataset: CedarDataset) -> CedarDataset:
    """Expose the same dataset for planned compatibility consumers.

    :param cedar_dataset: Already-loaded real baseline. Example: CedarDataset.
    :return: The same dataset, without a second import. Example: cedar_dataset.
    :raises ValueError: Invalid baseline contract.
    """
    return cedar_dataset
