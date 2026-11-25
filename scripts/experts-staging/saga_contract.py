"""Fail-closed contracts for explicit, independently owned staged Saga cases."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from contract import allow_browser_request

CASES = ("nomination", "copy-maria", "copy-guest", "copy-self")
ACTORS = {
    "nomination": "esvensson",
    "copy-maria": "mrodriguez",
    "copy-guest": None,
    "copy-self": "mchen",
}


def validate_case(case: str) -> str:
    """Require an implemented case, without a permissive default.

    :param case: Explicit lane name, e.g. copy-maria.
    :return: The validated unchanged lane.
    :raises ValueError: The case is absent, malformed or unimplemented.
    """
    if type(case) is not str or case not in CASES:
        raise ValueError("An implemented explicit Saga case is required.")
    return case


def allow_saga_request(case: str, url: str, method: str) -> bool:
    """Permit only declared native browser destinations and lane-specific writes.

    :param case: Implemented lane, e.g. nomination.
    :param url: Actual request URL, e.g. the owned HTTPS login endpoint.
    :param method: Actual HTTP method.
    :return: Whether the original request may continue without replacement.
    :raises ValueError: The lane itself is invalid.
    """
    validate_case(case)
    if allow_browser_request(url, method):
        return True
    try:
        parsed = urlsplit(url)
        owned = (parsed.scheme, parsed.hostname, parsed.port) == (
            "https",
            "cedar-web",
            8443,
        )
    except (TypeError, ValueError):
        return False
    if not owned or any(
        (parsed.username, parsed.password, parsed.query, parsed.fragment)
    ):
        return False
    paths = {"/auth/user/login/"} if ACTORS[case] is not None else set()
    if case in {"copy-maria", "copy-self"}:
        paths.add("/karma/copy-receipts/")
    return method == "POST" and parsed.path in paths


def validate_copy_attempts(case: str, attempts: list[dict[str, Any]]) -> str | None:
    """Verify actual receipt payload, identity and CSRF presence without secrets.

    :param case: Explicit copy lane.
    :param attempts: Passive records containing method, path, payload and csrf.
    :return: Canonical UUID for signed-in cases, otherwise None.
    :raises AssertionError: Traffic differs from the one exact allowed action.
    :raises ValueError: The case is invalid or not a copy lane.
    """
    validate_case(case)
    if not case.startswith("copy-"):
        raise ValueError("A clipboard case is required.")
    if case == "copy-guest":
        assert attempts == [], "Guest copy attempted a receipt."
        return None
    assert len(attempts) == 1, "Signed-in copy must make one observed receipt."
    attempt = attempts[0]
    assert attempt["method"] == "POST" and attempt["path"] == "/karma/copy-receipts/"
    assert attempt["csrf"] is True
    payload = attempt["payload"]
    raw = payload["event_identity"]
    identity = UUID(raw)
    assert identity.version == 4 and str(identity) == raw
    assert payload == {
        "entity_type": "activity",
        "entity_id": 6203,
        "event_identity": raw,
    }
    return raw


def assert_row_delta(
    case: str, before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]
) -> list[str]:
    """Require every existing domain row unchanged and only the allowed additions.

    :param case: Implemented case, e.g. copy-maria.
    :param before: Complete private model/PK/row snapshot before browser work.
    :param after: Complete private snapshot after browser work.
    :return: The newly inserted award IDs, never private row bodies.
    :raises AssertionError: A row, model set or allowed insertion count differs.
    :raises ValueError: The case is unimplemented.
    """
    validate_case(case)
    assert before and before.keys() == after.keys(), "Domain model set changed."
    additions: list[str] = []
    for model, rows in before.items():
        current = after[model]
        unchanged = all(current.get(pk) == row for pk, row in rows.items())
        assert unchanged, "Existing domain rows changed."
        added = sorted(current.keys() - rows.keys())
        if model == "authtoken.token":
            assert_auth_tokens(case, before["auth.user"], rows, current)
            continue
        if case == "copy-maria" and model == "methodology.karmaaward":
            assert len(added) == 2, "Maria copy must add exactly two awards."
            additions.extend(added)
        else:
            assert not added, "Unexpected domain row insertion."
    assert len(additions) == (2 if case == "copy-maria" else 0)
    return additions


def assert_auth_tokens(
    case: str, users: dict[str, Any], before: dict[str, Any], after: dict[str, Any]
) -> None:
    """Allow only the existing login flow's one token creation for its exact actor.

    :param case: Implemented actor lane.
    :param users: Original serialized user rows with their actual PKs.
    :param before: Private pre-login token rows.
    :param after: Private post-browser token rows, never exported.
    :return: None once unchanged originals and the exact login addition agree.
    :raises AssertionError: A token belongs to another actor or has invalid shape.
    """
    actor = ACTORS[validate_case(case)]
    user = next(
        (int(pk) for pk, row in users.items() if row["fields"]["username"] == actor),
        None,
    )
    assert user is not None or actor is None
    existing = any(row["fields"]["user"] == user for row in before.values())
    added = after.keys() - before.keys()
    assert all(after.get(pk) == row for pk, row in before.items())
    assert len(added) == int(actor is not None and not existing)
    for pk in added:
        assert_new_auth_token(pk, after[pk], user)


def assert_new_auth_token(pk: str, row: dict[str, Any], user: int | None) -> None:
    """Check actual new login token structure privately without printing its value.

    :param pk: Private new token key, never exported.
    :param row: Actual serialized token row.
    :param user: Exact original authenticated actor ID.
    :return: None when every generated-token field matches the existing schema.
    :raises AssertionError: Token identity, actor or metadata shape differs.
    """
    assert re.fullmatch(r"[a-f0-9]{40}", pk)
    assert row["model"] == "authtoken.token" and row["pk"] == pk
    fields = row["fields"]
    assert fields.keys() == {"user", "created"} and fields["user"] == user
    assert isinstance(fields["created"], str) and fields["created"]
