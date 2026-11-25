"""Real pure-policy counterexamples; never contact cloud or a database."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import sys
from datetime import datetime, timedelta
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
        "fields": {"user": user, "created": _STARTED},
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
    contract.assert_auth_tokens(
        case, users, {}, {"a" * 40: _token()}, _interval(username)
    )


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
            "copy-self",
            {"3": {"fields": {"username": "mchen"}}},
            {},
            {"a" * 40: token},
            _interval("mchen"),
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


_PREPARED = "2026-11-25T00:00:00.000000+00:00"
_STARTED = "2026-11-25T00:00:01.123400+00:00"
_COMPLETED = "2026-11-25T00:00:02.654321+00:00"
_VERIFIED = "2026-11-25T00:00:10.000000+00:00"


def _login_observation(actor: str = "esvensson") -> dict[str, object]:
    """Build safe synthetic metadata for one real-shaped native login observation.

    :param actor: Exact fictional actor used by the lane.
    :return: Fresh nonsecret POST/302 metadata with precise UTC bounds.
    """
    return {
        "actor": actor,
        "method": "POST",
        "path": "/auth/user/login/",
        "status": 302,
        "started_at": _STARTED,
        "completed_at": _COMPLETED,
        "session_key_sha256": "a" * 64,
    }


def _interval(actor: str = "esvensson") -> contract.LoginInterval:
    """Build a precise immutable synthetic interval for isolated policy checks.

    :param actor: Exact fictional actor.
    :return: Full microsecond UTC bounds with the test session's actual digest.
    """
    return contract.LoginInterval(
        actor,
        datetime.fromisoformat(_STARTED),
        datetime.fromisoformat(_COMPLETED),
        hashlib.sha256(("s" * 32).encode()).hexdigest(),
    )


def _users() -> dict[str, object]:
    """Build exact-shaped private user rows with distinguishable original values.

    :return: Fresh synthetic original rows, never a database substitute.
    """
    return {
        str(pk): {
            "model": "auth.user",
            "pk": pk,
            "fields": {
                "username": name,
                "last_login": None,
                "email": "fictional@example.com",
                "is_staff": False,
            },
        }
        for pk, name in ((3, "mrodriguez"), (4, "esvensson"), (5, "mchen"))
    }


def _logged_in_users(actor: str) -> tuple[dict[str, object], dict[str, object]]:
    """Apply only one exact actor timestamp inside the synthetic native interval.

    :param actor: Declared case actor.
    :return: Independent before/after dictionaries for exact comparison tests.
    """
    before = _users()
    after = copy.deepcopy(before)
    row = next(row for row in after.values() if row["fields"]["username"] == actor)
    row["fields"]["last_login"] = _STARTED
    return before, after


@pytest.mark.parametrize(
    "case,actor",
    [("nomination", "esvensson"), ("copy-maria", "mrodriguez"), ("copy-self", "mchen")],
)
def test_assert_user_rows_with_only_exact_actor_login_timestamp_passes(
    case: str, actor: str
) -> None:
    """Permit only the observed actor and preserve every unrelated account field.

    :param case: Signed-in lane.
    :param actor: Its exact actor.
    :return: None after the sole supported event is accepted.
    """
    before, after = _logged_in_users(actor)
    contract.assert_user_rows(case, before, after, _interval(actor))


@pytest.mark.parametrize(
    "stamp",
    [
        "2026-11-25T00:00:01.123399Z",
        "2026-11-25T00:00:02.654322Z",
        None,
        "2026-11-25T00:00:01.123400",
    ],
)
def test_assert_user_rows_with_actor_timestamp_outside_precise_interval_rejects(
    stamp: object,
) -> None:
    """Refuse one-microsecond excursions, absent values and naive timestamps.

    :param stamp: Deliberately invalid actor timestamp.
    :return: None after the exact event boundary rejects it.
    """
    before, after = _logged_in_users("esvensson")
    after["4"]["fields"]["last_login"] = stamp
    with pytest.raises(AssertionError):
        contract.assert_user_rows("nomination", before, after, _interval())


@pytest.mark.parametrize(
    "field,value",
    [("last_login", _STARTED), ("email", "changed@example.com"), ("is_staff", True)],
)
def test_assert_user_rows_with_unrelated_account_change_rejects(
    field: str, value: object
) -> None:
    """Do not grant the login exception to another account or another field.

    :param field: Unrelated account field being changed.
    :param value: Deliberately unexpected value.
    :return: None after the strict comparison rejects the effect.
    """
    before, after = _logged_in_users("esvensson")
    after["3"]["fields"][field] = value
    with pytest.raises(AssertionError):
        contract.assert_user_rows("nomination", before, after, _interval())


@pytest.mark.parametrize("case", contract.CASES)
def test_assert_user_rows_without_login_observation_rejects_any_timestamp_change(
    case: str,
) -> None:
    """Missing evidence permits zero timestamp exceptions for every lane.

    :param case: Implemented lane.
    :return: None after a changed timestamp is rejected.
    """
    before, after = _logged_in_users("mrodriguez")
    with pytest.raises(AssertionError):
        contract.assert_user_rows(case, before, after, None)


@pytest.mark.parametrize(
    "label", ["accounts.useronboardingstate", "accounts.useremailverification"]
)
@pytest.mark.parametrize("operation", ["insert", "change", "delete"])
def test_assert_row_delta_with_account_state_mutation_rejects(
    label: str, operation: str
) -> None:
    """Keep all account models under ordinary immutable-row comparisons.

    :param label: Actual omitted account model label from the independent review.
    :param operation: Unauthorized insertion, update or deletion.
    :return: None after every mutation fails closed.
    """
    before, after = _rows(), _rows()
    before[label] = {} if operation == "insert" else {"1": {"state": "original"}}
    after[label] = {} if operation == "delete" else {"1": {"state": "changed"}}
    with pytest.raises(AssertionError):
        contract.assert_row_delta("copy-guest", before, after)


@pytest.mark.parametrize(
    "stamp",
    [
        "2026-11-25T00:00:01.123399Z",
        "2026-11-25T00:00:02.654322Z",
        "2026-11-24T00:00:00.000000Z",
        None,
    ],
)
def test_assert_auth_tokens_with_new_token_time_outside_login_rejects(
    stamp: object,
) -> None:
    """Bind a normal new credential to the same exact observed POST interval.

    :param stamp: Forged or missing new token creation timestamp.
    :return: None after the invalid insertion fails closed.
    """
    token = _token(4)
    token["fields"]["created"] = stamp
    with pytest.raises(AssertionError):
        contract.assert_auth_tokens(
            "nomination", _users(), {}, {"a" * 40: token}, _interval()
        )


def _session() -> dict[str, object]:
    """Build a real-shaped synthetic session row for pure identity/expiry checks.

    :return: One new private session example tied to the interval's cookie hash.
    """
    expiry = datetime.fromisoformat(_STARTED) + timedelta(
        seconds=contract.NORMAL_LOGIN_EXPIRY_SECONDS
    )
    return {
        "model": "sessions.session",
        "pk": "s" * 32,
        "fields": {
            "session_data": "synthetic-signed-session",
            "expire_date": expiry.isoformat(timespec="microseconds"),
        },
    }


def test_assert_session_rows_with_exact_cookie_and_normal_bounded_expiry_passes() -> (
    None
):
    """Permit only one exact observed session addition and preserve older rows.

    :return: None after the known supported session event passes.
    """
    old = {"old": {"unchanged": True}}
    contract.assert_session_rows(old, {**old, "s" * 32: _session()}, _interval())


@pytest.mark.parametrize(
    "change", ["anonymous", "wrong-cookie", "changed-old", "wrong-expiry", "two-new"]
)
def test_assert_session_rows_with_unobserved_or_unrelated_session_effect_rejects(
    change: str,
) -> None:
    """Reject extra or changed sessions and mismatched identity/expiry metadata.

    :param change: Specific unauthorized session effect.
    :return: None after strict session policy rejects it.
    """
    before, after, login = (
        {"old": {"unchanged": True}},
        {"old": {"unchanged": True}, "s" * 32: _session()},
        _interval(),
    )
    if change == "anonymous":
        login = None
    elif change == "wrong-cookie":
        login = login._replace(session_key_sha256="b" * 64)
    elif change == "changed-old":
        after["old"] = {"unchanged": False}
    elif change == "wrong-expiry":
        after["s" * 32]["fields"]["expire_date"] = _COMPLETED
    else:
        after["t" * 32] = _session()
    with pytest.raises(AssertionError):
        contract.assert_session_rows(before, after, login)


def test_utc_timestamp_with_one_microsecond_difference_preserves_exact_instants() -> (
    None
):
    """Preserve the real precision that Django's default evidence encoder truncates.

    :return: None after the one-microsecond difference remains observable.
    """
    first = contract.utc_timestamp(_STARTED)
    second = contract.utc_timestamp("2026-11-25T00:00:01.123401Z")
    assert second - first == timedelta(microseconds=1)
    assert first.tzinfo is not None and first.utcoffset() == timedelta(0)


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        1,
        "",
        "2026-11-25",
        "2026-11-25T00:00:00",
        "2026-11-25T00:00:00Z",
        "2026-11-25T00:00:00.000000+01:00",
        "2026-99-25T00:00:00.000000Z",
    ],
)
def test_utc_timestamp_with_unprecise_or_non_utc_input_rejects(value: object) -> None:
    """Refuse implicit timezone or precision tolerances in private time comparisons.

    :param value: Deliberately invalid evidence timestamp.
    :return: None after the invalid boundary input is rejected.
    """
    with pytest.raises(AssertionError):
        contract.utc_timestamp(value)


@pytest.mark.parametrize(
    "case,actor",
    [("nomination", "esvensson"), ("copy-maria", "mrodriguez"), ("copy-self", "mchen")],
)
def test_validate_login_observation_with_exact_actor_and_bounded_post_returns_interval(
    case: str, actor: str
) -> None:
    """Accept only actual-shaped actor metadata inside its private case window.

    :param case: Signed-in lane.
    :param actor: Its exact declared actor.
    :return: None after every returned bound matches without expansion.
    """
    actual = contract.validate_login_observation(
        case, _login_observation(actor), _PREPARED, _VERIFIED
    )
    assert actual.actor == actor
    assert actual.started_at == datetime.fromisoformat(_STARTED)
    assert actual.completed_at == datetime.fromisoformat(_COMPLETED)


def test_validate_login_observation_with_anonymous_case_requires_no_login() -> None:
    """Anonymous browsing cannot acquire a timestamp or session-writing exception.

    :return: None after absent metadata passes and a forged login is rejected.
    """
    assert (
        contract.validate_login_observation("copy-guest", None, _PREPARED, _VERIFIED)
        is None
    )
    with pytest.raises(AssertionError):
        contract.validate_login_observation(
            "copy-guest", _login_observation(), _PREPARED, _VERIFIED
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("actor", "mchen"),
        ("method", "GET"),
        ("path", "/auth/user/profile/"),
        ("status", 200),
        ("status", 302.0),
        ("session_key_sha256", "not-a-digest"),
        ("started_at", "2026-11-24T23:59:59.999999Z"),
        ("completed_at", "2026-11-25T00:00:10.000001Z"),
        ("completed_at", "2026-11-25T00:00:01.123399Z"),
    ],
)
def test_validate_login_observation_with_wrong_actor_request_or_bounds_rejects(
    field: str, value: object
) -> None:
    """Reject attribution errors and even one-microsecond interval excursions.

    :param field: Observation field being corrupted.
    :param value: Deliberately invalid value.
    :return: None after the inconsistent observation fails closed.
    """
    observed = _login_observation()
    observed[field] = value
    with pytest.raises(AssertionError):
        contract.validate_login_observation(
            "nomination", observed, _PREPARED, _VERIFIED
        )


def test_validate_login_observation_with_missing_metadata_or_unbounded_case_rejects() -> (
    None
):
    """Do not turn missing login evidence or an old baseline into a broad exception.

    :return: None after both invalid observation windows are rejected.
    """
    with pytest.raises(AssertionError):
        contract.validate_login_observation("nomination", None, _PREPARED, _VERIFIED)
    with pytest.raises(AssertionError):
        contract.validate_login_observation(
            "nomination", _login_observation(), "2026-11-24T00:00:00.000000Z", _VERIFIED
        )
