"""Real pure-policy counterexamples; never contact cloud or a database."""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from uuid import uuid4

import pytest

_ROOT = Path(__file__).resolve().parents[2] / "scripts/experts-staging"
_PRIOR_PATH = sys.path[:]
_PRIOR_CONTRACT = sys.modules.get("contract")
try:
    sys.path.insert(0, str(_ROOT))
    _SPEC = importlib.util.spec_from_file_location(
        "experts_saga_contract", _ROOT / "saga_contract.py"
    )
    assert _SPEC is not None and _SPEC.loader is not None
    contract = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(contract)
finally:
    sys.path[:] = _PRIOR_PATH
    if _PRIOR_CONTRACT is None:
        sys.modules.pop("contract", None)
    else:
        sys.modules["contract"] = _PRIOR_CONTRACT
_ORIGIN = "https://cedar-web:8443"


@pytest.mark.parametrize("case", contract.CASES)
def test_validate_case_with_implemented_lane_preserves_value(case: str) -> None:
    """Validate case with implemented lane preserves value.

    :param case: Explicit implemented or deliberately invalid lane.
    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    assert contract.validate_case(case) == case


@pytest.mark.parametrize("case", [None, "", "summary", "../nomination", 1, True])
def test_validate_case_with_invalid_lane_rejects(case: object) -> None:
    """Validate case with invalid lane rejects.

    :param case: Explicit implemented or deliberately invalid lane.
    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    with pytest.raises(ValueError):
        contract.validate_case(case)


@pytest.mark.parametrize("case", contract.CASES)
def test_allow_saga_request_with_real_reads_and_external_assets_allows(
    case: str,
) -> None:
    """Allow saga request with real reads and external assets allows.

    :param case: Explicit implemented or deliberately invalid lane.
    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    assert contract.allow_saga_request(case, _ORIGIN + "/experts/", "GET")
    assert contract.allow_saga_request(case, "https://fonts.gstatic.com/a.woff2", "GET")


@pytest.mark.parametrize("case", ["nomination", "copy-maria", "copy-self"])
def test_allow_saga_request_with_native_login_allows_only_auth_cases(case: str) -> None:
    """Allow saga request with native login allows only auth cases.

    :param case: Explicit implemented or deliberately invalid lane.
    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    assert contract.allow_saga_request(case, _ORIGIN + "/auth/user/login/", "POST")


@pytest.mark.parametrize("case", ["copy-maria", "copy-self"])
def test_allow_saga_request_with_exact_copy_receipt_allows(case: str) -> None:
    """Allow saga request with exact copy receipt allows.

    :param case: Explicit implemented or deliberately invalid lane.
    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    assert contract.allow_saga_request(case, _ORIGIN + "/karma/copy-receipts/", "POST")


@pytest.mark.parametrize("case", contract.CASES)
@pytest.mark.parametrize(
    "path",
    [
        "/api/playbooks/1/",
        "/karma/copy-receipts/?x=1",
        "/auth/user/login/?next=bad",
        "/auth/user/logout/",
    ],
)
def test_allow_saga_request_with_undeclared_writes_blocks(case: str, path: str) -> None:
    """Allow saga request with undeclared writes blocks.

    :param case: Explicit implemented or deliberately invalid lane.
    :param path: Actual local path used by the boundary.
    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    assert not contract.allow_saga_request(case, _ORIGIN + path, "POST")


@pytest.mark.parametrize(
    "url",
    [
        "https://cedar-web.evil:8443/auth/user/login/",
        "http://cedar-web:8443/auth/user/login/",
        "https://u:p@cedar-web:8443/auth/user/login/",
        "https://cedar-web/auth/user/login/",
        "mailto:maria.rodriguez@example.com",
    ],
)
def test_allow_saga_request_with_wrong_origin_or_mail_blocks(url: str) -> None:
    """Allow saga request with wrong origin or mail blocks.

    :param url: Actual candidate request URL used by the boundary.
    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    assert not contract.allow_saga_request("nomination", url, "POST")


def _attempt() -> dict[str, object]:
    """Build one exact valid copy request with a newly allocated UUID.

    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    return {
        "method": "POST",
        "path": "/karma/copy-receipts/",
        "csrf": True,
        "payload": {
            "entity_type": "activity",
            "entity_id": 6203,
            "event_identity": str(uuid4()),
        },
    }


@pytest.mark.parametrize("case", ["copy-maria", "copy-self"])
def test_validate_copy_attempts_with_exact_action_returns_actual_uuid(
    case: str,
) -> None:
    """Validate copy attempts with exact action returns actual uuid.

    :param case: Explicit implemented or deliberately invalid lane.
    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    attempt = _attempt()
    assert (
        contract.validate_copy_attempts(case, [attempt])
        == attempt["payload"]["event_identity"]
    )


def test_validate_copy_attempts_with_guest_traffic_rejects() -> None:
    """Validate copy attempts with guest traffic rejects.

    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    assert contract.validate_copy_attempts("copy-guest", []) is None
    with pytest.raises(AssertionError):
        contract.validate_copy_attempts("copy-guest", [_attempt()])


@pytest.mark.parametrize(
    "field,value",
    [("csrf", False), ("method", "GET"), ("path", "/api/consumption-receipts/")],
)
def test_validate_copy_attempts_with_invalid_envelope_rejects(
    field: str, value: object
) -> None:
    """Validate copy attempts with invalid envelope rejects.

    :param field: Envelope or payload field to corrupt.
    :param value: Deliberately invalid value.
    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    attempt = _attempt()
    attempt[field] = value
    with pytest.raises(AssertionError):
        contract.validate_copy_attempts("copy-maria", [attempt])


@pytest.mark.parametrize(
    "field,value",
    [
        ("entity_id", 6101),
        ("entity_type", "playbook"),
        ("event_identity", "not-a-uuid"),
        ("actor", 1),
        ("points", 5),
    ],
)
def test_validate_copy_attempts_with_untrusted_attribution_rejects(
    field: str, value: object
) -> None:
    """Validate copy attempts with untrusted attribution rejects.

    :param field: Envelope or payload field to corrupt.
    :param value: Deliberately invalid value.
    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    attempt = _attempt()
    attempt["payload"][field] = value
    with pytest.raises((AssertionError, ValueError)):
        contract.validate_copy_attempts("copy-maria", [attempt])


def test_validate_copy_attempts_with_duplicate_or_missing_attempt_rejects() -> None:
    """Validate copy attempts with duplicate or missing attempt rejects.

    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    attempt = _attempt()
    for attempts in ([], [attempt, attempt]):
        with pytest.raises(AssertionError):
            contract.validate_copy_attempts("copy-maria", attempts)


def _rows() -> dict[str, dict[str, object]]:
    """Build independent private row examples for mutation counterexamples.

    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    return {
        "methodology.karmaaward": {"1": {"points": 5000}},
        "methodology.expertprofile": {"2": {"summary": "Original public text."}},
        "auth.user": {"3": {"username": "mrodriguez"}},
    }


@pytest.mark.parametrize("case", ["nomination", "copy-guest", "copy-self"])
def test_assert_row_delta_with_unchanged_noaward_lane_passes(case: str) -> None:
    """Assert row delta with unchanged noaward lane passes.

    :param case: Explicit implemented or deliberately invalid lane.
    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    before = _rows()
    assert contract.assert_row_delta(case, before, copy.deepcopy(before)) == []


def test_assert_row_delta_with_exact_pair_preserves_every_original_row() -> None:
    """Assert row delta with exact pair preserves every original row.

    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    before = _rows()
    after = copy.deepcopy(before)
    after["methodology.karmaaward"].update({"4": {"points": 5}, "5": {"points": 5}})
    assert contract.assert_row_delta("copy-maria", before, after) == ["4", "5"]
    assert before == _rows()


@pytest.mark.parametrize("case", contract.CASES)
@pytest.mark.parametrize(
    "change", ["award-value", "profile-text", "deleted-row", "new-user", "new-model"]
)
def test_assert_row_delta_with_unrelated_mutation_rejects(
    case: str, change: str
) -> None:
    """Assert row delta with unrelated mutation rejects.

    :param case: Explicit implemented or deliberately invalid lane.
    :param change: Specific unrelated domain mutation.
    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    before, after = _rows(), _rows()
    if change == "award-value":
        after["methodology.karmaaward"]["1"]["points"] = 1
    elif change == "profile-text":
        after["methodology.expertprofile"]["2"]["summary"] = "Changed text."
    elif change == "deleted-row":
        after["auth.user"].pop("3")
    elif change == "new-user":
        after["auth.user"]["4"] = {"username": "bob"}
    else:
        after["methodology.unexpected"] = {}
    with pytest.raises(AssertionError):
        contract.assert_row_delta(case, before, after)


@pytest.mark.parametrize("count", [0, 1, 3])
def test_assert_row_delta_with_wrong_pair_cardinality_rejects(count: int) -> None:
    """Assert row delta with wrong pair cardinality rejects.

    :param count: Deliberately invalid number of new awards.
    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    before, after = _rows(), _rows()
    after["methodology.karmaaward"].update(
        {str(index + 4): {"points": 5} for index in range(count)}
    )
    with pytest.raises(AssertionError):
        contract.assert_row_delta("copy-maria", before, after)


@pytest.mark.parametrize("case", ["nomination", "copy-guest", "copy-self"])
def test_assert_row_delta_with_unauthorized_new_awards_rejects(case: str) -> None:
    """Assert row delta with unauthorized new awards rejects.

    :param case: Explicit implemented or deliberately invalid lane.
    :return: None after assertions, or the fresh example data.
    :raises AssertionError: An expected boundary outcome differs.
    """
    before, after = _rows(), _rows()
    after["methodology.karmaaward"]["4"] = {"points": 5}
    with pytest.raises(AssertionError):
        contract.assert_row_delta(case, before, after)


def _token(user: int = 3) -> dict[str, object]:
    """Build synthetic private token metadata for one exact actor.

    :param user: Synthetic actual user PK.
    :return: A fresh serialized row example, never a service credential.
    """
    return {
        "model": "authtoken.token",
        "pk": "a" * 40,
        "fields": {"user": user, "created": "2026-11-25T00:00:00Z"},
    }


@pytest.mark.parametrize(
    "case,username",
    [("nomination", "esvensson"), ("copy-maria", "mrodriguez"), ("copy-self", "mchen")],
)
def test_assert_auth_tokens_with_exact_native_login_creation_passes(
    case: str, username: str
) -> None:
    """Permit only the known ordinary login bookkeeping addition.

    :param case: Implemented signed-in lane.
    :param username: Its exact actor.
    :return: None after the expected genuine-login shape is accepted.
    """
    users = {"3": {"fields": {"username": username}}}
    contract.assert_auth_tokens(case, users, {}, {"a" * 40: _token()})


def test_assert_auth_tokens_with_guest_creation_or_existing_change_rejects() -> None:
    """Reject anonymous token creation and mutation of any original credential.

    :return: None after both unauthorized effects fail closed.
    """
    with pytest.raises(AssertionError):
        contract.assert_auth_tokens("copy-guest", {}, {}, {"a" * 40: _token()})
    before, after = {"a" * 40: _token()}, {"a" * 40: _token(4)}
    with pytest.raises(AssertionError):
        contract.assert_auth_tokens(
            "copy-maria", {"3": {"fields": {"username": "mrodriguez"}}}, before, after
        )


@pytest.mark.parametrize(
    "field,value", [("user", 4), ("created", None), ("extra", "unexpected")]
)
def test_assert_auth_tokens_with_unrelated_or_malformed_token_rejects(
    field: str, value: object
) -> None:
    """Reject tokens with a different recipient or unexpected metadata.

    :param field: Field to corrupt.
    :param value: Deliberately invalid value.
    :return: None after the unsafe effect is rejected.
    """
    token = _token()
    token["fields"][field] = value
    with pytest.raises(AssertionError):
        contract.assert_auth_tokens(
            "copy-self", {"3": {"fields": {"username": "mchen"}}}, {}, {"a" * 40: token}
        )


def test_assert_auth_tokens_with_preexisting_actor_token_requires_no_new_row() -> None:
    """Retain the exact original token and reject duplicate login credentials.

    :return: None after the legitimate original is preserved without additions.
    """
    users = {"3": {"fields": {"username": "mrodriguez"}}}
    before = {"a" * 40: _token()}
    contract.assert_auth_tokens("copy-maria", users, before, copy.deepcopy(before))
    with pytest.raises(AssertionError):
        contract.assert_auth_tokens(
            "copy-maria", users, before, {**before, "b" * 40: _token()}
        )
