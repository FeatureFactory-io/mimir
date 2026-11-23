from __future__ import annotations

"""Certification helpers; never imported by production modules."""
from collections.abc import Mapping
from django.http import HttpResponse
from tests.support.experts_data import CedarDataset


def load_privacy_case() -> CedarDataset:
    """Load real Cedar rows and independent unpublished variants.

    :return: Dataset, e.g. users_by_username["mrodriguez"].
    :raises AssertionError: If required private rows/token are absent.
    """
    raise NotImplementedError()


def assert_private_rows_exist(dataset: CedarDataset) -> None:
    """Prove sensitive fixtures exist before checking their exclusion.

    :param dataset: Cedar ORM dataset, e.g. Maria and playbook 6101.
    :return: None; successful validation.
    :raises AssertionError: If real private Playbook/PIP/Token data is missing.
    """
    raise NotImplementedError()


def assert_public_projection(dto: Mapping[str, object], dataset: CedarDataset) -> None:
    """Validate only the designated public DTO and its evidence.

    :param dto: S17 allowlisted projection, e.g. response.context["expert"].
    :param dataset: Real Cedar dataset, e.g. public playbook 6101.
    :return: None; schema and public-released evidence validated.
    :raises AssertionError: For extra fields, ORM objects or private evidence.
    """
    raise NotImplementedError()


def assert_public_response(
    response: HttpResponse, dataset: CedarDataset, authenticated: bool
) -> None:
    """Validate raw HTML and designated projection without inspecting request.user.

    :param response: Actual Django-client response, e.g. status 200.
    :param dataset: Real Cedar dataset, e.g. Maria's persisted fixtures.
    :param authenticated: Contact eligibility, e.g. False for Bob.
    :return: None; private data absent and legitimate content retained.
    :raises AssertionError: For a leak, wrong status or lost authorized contact.
    """
    raise NotImplementedError()
