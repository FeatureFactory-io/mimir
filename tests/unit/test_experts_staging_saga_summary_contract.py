"""Counterexamples for the bounded summary companion policy."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/experts-staging"))
from saga_summary_contract import allow_summary_request, assert_closed_rows


def test_allow_summary_request_with_exact_prepared_routes_closes_writes() -> None:
    """Allow actual routes and reject foreign proposal writes."""
    origin = "https://cedar-web:8443"
    assert allow_summary_request(origin + "/experts/", "GET", 7301)
    assert allow_summary_request(origin + "/auth/user/login/", "POST", 7301)
    assert allow_summary_request(origin + "/pips/7301/submit/", "POST", 7301)
    assert not allow_summary_request(origin + "/pips/7302/submit/", "POST", 7301)
    assert not allow_summary_request(origin + "/karma/copy-receipts/", "POST", 7301)
    assert not allow_summary_request(origin + "/pips/7301/submit/?x=1", "POST", 7301)


def test_assert_closed_rows_with_one_known_field_preserves_rest() -> None:
    """Only the explicitly listed field of the explicitly listed row changes."""
    before = {"model": {"1": {"pk": 1, "fields": {"a": 1, "b": 2}}}}
    after = copy.deepcopy(before)
    after["model"]["1"]["fields"]["a"] = 3
    assert_closed_rows(before, after, {"model": {"1": frozenset({"a"})}}, {})
    after["model"]["1"]["fields"]["b"] = 4
    with pytest.raises(AssertionError):
        assert_closed_rows(before, after, {"model": {"1": frozenset({"a"})}}, {})


@pytest.mark.parametrize("mutation", ["new_model", "row_delete", "row_add"])
def test_assert_closed_rows_with_unlisted_mutation_rejects(mutation: str) -> None:
    """No generic allowance hides unrelated changes."""
    before = {"model": {"1": {"pk": 1, "fields": {"a": 1}}}}
    after = copy.deepcopy(before)
    if mutation == "new_model":
        after["other"] = {}
    elif mutation == "row_delete":
        after["model"].clear()
    else:
        after["model"]["2"] = {"pk": 2, "fields": {"a": 1}}
    with pytest.raises(AssertionError):
        assert_closed_rows(before, after, {}, {})


@pytest.mark.parametrize("pip_id", [None, 0, -1, True, "7301"])
def test_allow_summary_request_with_invalid_identity_rejects(pip_id: object) -> None:
    """No malformed identity can broaden the exact normal mutation routes."""
    with pytest.raises(ValueError):
        allow_summary_request("https://cedar-web:8443/experts/", "GET", pip_id)


@pytest.mark.parametrize(
    "url",
    [
        "http://cedar-web:8443/pips/7301/submit/",
        "https://cedar-web:8444/pips/7301/submit/",
        "https://other:8443/pips/7301/submit/",
        "https://user@cedar-web:8443/pips/7301/submit/",
        "https://cedar-web:8443/pips/7301/admin-review/#fragment",
        "https://cedar-web:8443/api/pips/7301/",
    ],
)
def test_allow_summary_request_with_undeclared_destination_blocks(url: str) -> None:
    """Only the prepared owned native browser forms may receive POSTs."""
    assert not allow_summary_request(url, "POST", 7301)
