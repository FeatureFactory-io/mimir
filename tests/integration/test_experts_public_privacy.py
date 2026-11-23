from __future__ import annotations

import pytest
from django.test import Client
from tests.support.experts_privacy import load_privacy_case

pytestmark = pytest.mark.django_db


def test_public_detail_with_anonymous_viewer_excludes_private_data(
    client: Client,
) -> None:
    """Certify guest HTML against persisted sensitive data.

    :param client: Real Django client, e.g. anonymous session.
    :return: None; all guest privacy assertions pass.
    :raises AssertionError: If private data leaks or public evidence disappears.
    """
    raise NotImplementedError()


def test_public_detail_with_authenticated_elena_preserves_public_boundary(
    client: Client,
) -> None:
    """Preserve authorized contact while excluding private contribution data.

    :param client: Real Django client, e.g. force_login(esvensson).
    :return: None; public boundary and legitimate mailto both pass.
    :raises AssertionError: If privacy or authenticated contact regresses.
    """
    raise NotImplementedError()


@pytest.mark.parametrize("status", ["draft", "active", "disabled"])
@pytest.mark.parametrize("authenticated", [False, True])
def test_public_detail_with_unpublished_evidence_excludes_each_status(
    client: Client, status: str, authenticated: bool
) -> None:
    """Certify explicit public-released filtering for both viewer types.

    :param client: Real Django client, e.g. Bob's session.
    :param status: Persisted public variant status, e.g. "active".
    :param authenticated: Whether Elena signs in, e.g. True.
    :return: None; variant excluded and public released evidence retained.
    :raises AssertionError: If fixtures are absent or excluded evidence leaks.
    """
    raise NotImplementedError()


def test_public_detail_with_private_fixture_has_allowlisted_projection(
    client: Client,
) -> None:
    """Check only S17 DTO schema and real evidence eligibility.

    :param client: Real Django client, e.g. anonymous session.
    :return: None; no private fields or ORM objects enter the DTO.
    :raises AssertionError: If schema or public-released eligibility fails.
    """
    raise NotImplementedError()
