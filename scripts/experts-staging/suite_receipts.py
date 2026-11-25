"""Closed safe native auth/write envelopes retained in public derivatives."""

from __future__ import annotations

import re
from typing import Any

from saga_contract import checked_login_interval, utc_timestamp, validate_copy_attempts

_ACTORS = {
    "nomination": "esvensson",
    "copy-maria": "mrodriguez",
    "copy-guest": None,
    "copy-self": "mchen",
    "guest-public": None,
    "authenticated-matrix": "esvensson",
    "long_identity_and_prose": "esvensson",
    "missing_summary": "esvensson",
}


def protocol_fields(record: dict[str, Any], result: dict[str, Any]) -> None:
    """Retain only exact typed native account/write observations without credentials.

    :param record: Parsed original case report.
    :param result: Safe derivative under construction.
    :return: None after closed precise protocol fields validate.
    :raises AssertionError: Any native actor, request or timestamp differs.
    """
    case = record.get("case")
    if "login_observation" in record:
        actor = _ACTORS[case]
        login = record["login_observation"]
        assert (login is None) == (actor is None)
        if login is not None:
            checked_login(actor, login)
        result["login_observation"] = login
    if "login_observations" in record:
        assert case == "summary-acceptance"
        logins = record["login_observations"]
        assert isinstance(logins, list) and len(logins) == 3
        for actor, login in zip(("mrodriguez", "mchen", "mrodriguez"), logins):
            checked_login(actor, login)
        result["login_observations"] = logins
    if "receipt_attempts" in record:
        attempts = record["receipt_attempts"]
        if case == "nomination":
            assert attempts == []
        else:
            validate_copy_attempts(case, attempts)
        assert all(
            isinstance(row, dict) and set(row) == {"method", "path", "payload", "csrf"}
            for row in attempts
        )
        result["receipt_attempts"] = attempts
    _copy_response(record, result)
    _writes(record, result)


def _copy_response(record: dict[str, Any], result: dict[str, Any]) -> None:
    """Keep the real applied/skipped/self outcome with an exact closed body.

    :param record: Original browser receipt.
    :param result: Safe derivative.
    :return: None after actual receipt status validates.
    :raises AssertionError: Unknown fields or outcome differ.
    """
    if "receipt_response" not in record:
        return
    expected = {
        "copy-maria": {"status": "applied"},
        "copy-self": {"status": "skipped", "reason": "self_consumption"},
        "copy-guest": None,
    }
    assert (
        record.get("case") in expected
        and record["receipt_response"] == expected[record["case"]]
    )
    result["receipt_response"] = record["receipt_response"]


def checked_login(actor: str, login: dict[str, Any]) -> None:
    """Check the existing precise full-microsecond native POST/302 schema.

    :param actor: Exact closed role for this lane.
    :param login: Original safe native action-response envelope.
    :return: None after exact schema/timing/hash checks.
    :raises AssertionError: Actor, request, digest or duration differs.
    """
    start, end = utc_timestamp(login["started_at"]), utc_timestamp(
        login["completed_at"]
    )
    checked_login_interval(actor, login, (start, end), 1209600)


def _writes(record: dict[str, Any], result: dict[str, Any]) -> None:
    """Require exact case-specific POST ordering and bounded summary envelopes.

    :param record: Original report.
    :param result: Safe derivative.
    :return: None after every allowed nonread request validates.
    :raises AssertionError: Extra endpoint, method, fields or order is present.
    """
    case = record.get("case")
    if "nonread_requests" in record:
        observed = record["nonread_requests"]
        if case == "summary-acceptance":
            paths = [
                "/auth/user/login/",
                _summary_post(record["submission"], "submit"),
                "/auth/user/login/",
                _summary_post(record["finalization"], "admin-review"),
                "/auth/user/login/",
            ]
            result.update(
                submission=record["submission"], finalization=record["finalization"]
            )
        else:
            paths = ["/auth/user/login/"] if _ACTORS.get(case) is not None else []
            if case in {"copy-maria", "copy-self"}:
                paths.append("/karma/copy-receipts/")
        assert observed == [{"method": "POST", "path": path} for path in paths]
        result["nonread_requests"] = observed


def _summary_post(record: dict[str, Any], operation: str) -> str:
    """Validate only the literal native summary POST action/response schema.

    :param record: Actual safe submission or decision observation.
    :param operation: Fixed submit or admin-review suffix.
    :return: Exact safe native path.
    :raises AssertionError: Shape, status, route or full timestamp differs.
    """
    assert isinstance(record, dict) and set(record) == {
        "method",
        "path",
        "status",
        "started_at",
        "completed_at",
    }
    assert (
        record["method"] == "POST"
        and type(record["status"]) is int
        and record["status"] == 302
    )
    assert isinstance(record["path"], str) and re.fullmatch(
        r"/pips/[1-9][0-9]*/" + operation + "/", record["path"]
    )
    seconds = (
        utc_timestamp(record["completed_at"]) - utc_timestamp(record["started_at"])
    ).total_seconds()
    assert 0 <= seconds <= 30
    return record["path"]
