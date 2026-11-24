"""Real HTTP regression contracts for the shared public status binding."""

from __future__ import annotations

from typing import cast

import pytest
from behave.configuration import Configuration
from behave.runner import Context, Runner
from django.http.response import HttpResponseBase
from django.test import Client

from docs.features.steps.experts_detail_steps import public_response_has_expected_status
from tests.support.experts_data import CedarDataset

pytestmark = pytest.mark.django_db
_PROFILE_CASES = (
    ("mrodriguez", 200),
    ("skim", 200),
    ("no-such-cedar-user", 404),
    ("nberg", 404),
)


@pytest.mark.parametrize(("username", "status"), _PROFILE_CASES)
def test_status_step_with_matching_real_response_accepts(
    client: Client, cedar_dataset: CedarDataset, username: str, status: int
) -> None:
    """Accept actual successful and missing/ineligible profile responses.

    :param client: Real anonymous Django client, e.g. Client().
    :param cedar_dataset: Actual Cedar fixture, e.g. Maria and zero-score Nora.
    :param username: Requested subject, e.g. "nberg".
    :param status: Contracted real result, e.g. 404.
    :return: None after the shared binding accepts the observation.
    :raises AssertionError: If the route or shared assertion differs.
    """
    assert cedar_dataset.user_ids["mrodriguez"]
    response = client.get(f"/experts/{username}/")
    assert response.status_code == status
    public_response_has_expected_status(_response_context(response), status)


@pytest.mark.parametrize(("username", "status"), _PROFILE_CASES)
def test_status_step_with_mismatched_real_response_rejects(
    client: Client, cedar_dataset: CedarDataset, username: str, status: int
) -> None:
    """Reject the opposite expectation using actual 200 and 404 responses.

    :param client: Real anonymous Django client, e.g. Client().
    :param cedar_dataset: Persisted Cedar history, e.g. Sam's positive profile.
    :param username: Actual route subject, e.g. "skim".
    :param status: Real expected route outcome, e.g. 200.
    :return: None when a wrong status expectation raises AssertionError.
    :raises AssertionError: If the binding accepts a false status claim.
    """
    assert cedar_dataset.user_ids["skim"]
    response = client.get(f"/experts/{username}/")
    assert response.status_code == status
    incorrect_status = 404 if status == 200 else 200
    with pytest.raises(AssertionError, match="Expected HTTP"):
        public_response_has_expected_status(
            _response_context(response), incorrect_status
        )


@pytest.mark.parametrize("invalid_status", (True, 99, 600, "404"))
def test_status_step_with_invalid_expected_status_rejects(
    client: Client, cedar_dataset: CedarDataset, invalid_status: object
) -> None:
    """Fail invalid expectations before comparing an actual response.

    :param client: Real Django client, e.g. an anonymous browser request.
    :param cedar_dataset: Actual Cedar records, e.g. Maria's public profile.
    :param invalid_status: Invalid contract value, e.g. True or "404".
    :return: None when the malformed expectation raises ValueError.
    :raises AssertionError: If invalid input silently reaches comparison.
    """
    assert cedar_dataset.user_ids["mrodriguez"]
    response = client.get("/experts/mrodriguez/")
    assert response.status_code == 200
    with pytest.raises(ValueError, match="integer HTTP status"):
        public_response_has_expected_status(
            _response_context(response), cast(int, invalid_status)
        )


def test_status_step_with_missing_response_rejects() -> None:
    """Reject an actual Behave context with no preceding HTTP request.

    :return: None when absent observation raises AssertionError.
    :raises AssertionError: If no HTTP result can satisfy the binding.
    """
    context = Context(Runner(Configuration([], load_config=False)))
    with pytest.raises(AssertionError, match="Django HTTP response"):
        public_response_has_expected_status(context, 404)


def _response_context(response: HttpResponseBase) -> Context:
    """Carry the real Django response in a genuine Behave context.

    :param response: Real client response, e.g. public profile HTTP200.
    :return: Context with the actual response, e.g. context.response.
    :raises TypeError: If Behave cannot construct its normal runner context.
    """
    context = Context(Runner(Configuration([], load_config=False)))
    context.response = response
    return context
