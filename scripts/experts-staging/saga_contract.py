"""Fail-closed contracts for explicit, independently owned staged Saga cases."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from typing import Any, NamedTuple
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
_MAX_CASE_SECONDS = 720
_MAX_LOGIN_SECONDS = 30
NORMAL_LOGIN_EXPIRY_SECONDS = 14 * 24 * 60 * 60
_LOGIN_MODELS = frozenset({"auth.user", "authtoken.token", "sessions.session"})
_LOGIN_METADATA_FIELDS = frozenset(
    {
        "actor",
        "method",
        "path",
        "status",
        "started_at",
        "completed_at",
        "session_key_sha256",
    }
)


class LoginInterval(NamedTuple):
    """Immutable safe bounds from the actual native login POST/302 observation."""

    actor: str
    started_at: datetime
    completed_at: datetime
    session_key_sha256: str


def utc_timestamp(value: object) -> datetime:
    """Read a precise aware UTC evidence timestamp without rounding its value.

    :param value: Full microsecond ISO timestamp from a real evidence producer.
    :return: Exact aware UTC instant.
    :raises AssertionError: The value is malformed, naive or lacks full precision.
    """
    assert isinstance(value, str) and re.fullmatch(
        r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}(?:Z|\+00:00)", value
    ), "Precise aware UTC timestamp required."
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise AssertionError("Precise aware UTC timestamp required.") from None


def validate_login_observation(
    case: str, observed: dict[str, Any] | None, prepared_at: str, verified_at: str
) -> LoginInterval | None:
    """Bind one actual actor login interval inside the private case observation window.

    :param case: Implemented explicit actor lane.
    :param observed: Actual safe native POST/302 metadata, or None for anonymous.
    :param prepared_at: Private baseline completion timestamp.
    :param verified_at: Actual companion verification timestamp.
    :return: Precise immutable login bounds; None only for the anonymous lane.
    :raises AssertionError: Actor, request, UTC bounds or session identity differ.
    """
    actor = ACTORS[validate_case(case)]
    window = (utc_timestamp(prepared_at), utc_timestamp(verified_at))
    assert 0 <= (window[1] - window[0]).total_seconds() <= _MAX_CASE_SECONDS
    if actor is None:
        assert observed is None, "Anonymous case cannot acquire login exceptions."
        return None
    return checked_login_interval(actor, observed, window)


def checked_login_interval(
    actor: str, observed: dict[str, Any] | None, window: tuple[datetime, datetime]
) -> LoginInterval:
    """Validate exact native request metadata without enlarging its time interval.

    :param actor: Exact case actor.
    :param observed: Actual safe POST/302 response observation.
    :param window: Private baseline and verification UTC bounds.
    :return: Exact observed interval and safe session identity digest.
    :raises AssertionError: Shape, request, actor, timestamp or digest differs.
    """
    assert isinstance(observed, dict) and observed.keys() == _LOGIN_METADATA_FIELDS
    assert observed["actor"] == actor and observed["method"] == "POST"
    assert observed["path"] == "/auth/user/login/"
    assert type(observed["status"]) is int and observed["status"] == 302
    start = utc_timestamp(observed["started_at"])
    end = utc_timestamp(observed["completed_at"])
    assert window[0] <= start <= end <= window[1]
    assert (end - start).total_seconds() <= _MAX_LOGIN_SECONDS
    digest = observed["session_key_sha256"]
    assert isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest)
    return LoginInterval(actor, start, end, digest)


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
    case: str,
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
    login: LoginInterval | None = None,
) -> list[str]:
    """Require every existing domain row unchanged and only the allowed additions.

    :param case: Implemented case, e.g. copy-maria.
    :param before: Complete private model/PK/row snapshot before browser work.
    :param after: Complete private snapshot after browser work.
    :param login: Precisely validated native login interval, otherwise no exceptions.
    :return: The newly inserted award IDs, never private row bodies.
    :raises AssertionError: A row, model set or allowed insertion count differs.
    :raises ValueError: The case is unimplemented.
    """
    validate_case(case)
    assert before and before.keys() == after.keys(), "Domain model set changed."
    assert_account_rows(case, before, after, login)
    additions: list[str] = []
    for model, rows in before.items():
        if model in _LOGIN_MODELS:
            continue
        additions.extend(assert_immutable_model(case, model, rows, after[model]))
    assert len(additions) == (2 if case == "copy-maria" else 0)
    return additions


def assert_immutable_model(
    case: str, label: str, before: dict[str, Any], after: dict[str, Any]
) -> list[str]:
    """Preserve every original row and allow only the already specified award pair.

    :param case: Explicit case.
    :param label: Actual concrete model label.
    :param before: Complete original model rows.
    :param after: Actual current model rows.
    :return: New award IDs, otherwise an empty list.
    :raises AssertionError: An original row or allowed insertion count differs.
    """
    unchanged = all(after.get(pk) == row for pk, row in before.items())
    assert unchanged, "Existing model rows changed."
    added = sorted(after.keys() - before.keys())
    expected = 2 if case == "copy-maria" and label == "methodology.karmaaward" else 0
    assert len(added) == expected, "Unexpected model row insertion."
    return added


def assert_account_rows(
    case: str,
    before: dict[str, Any],
    after: dict[str, Any],
    login: LoginInterval | None,
) -> None:
    """Check only source-supported login writes; every other model stays strict.

    :param case: Actual lane.
    :param before: Complete private original model snapshots.
    :param after: Actual private current model snapshots.
    :param login: Exact observed interval, or None for no permitted login effects.
    :return: None after the three narrowly supported auth models reconcile.
    :raises AssertionError: A user, token or session effect differs.
    """
    users = before.get("auth.user", {})
    if "auth.user" in before:
        assert_user_rows(case, users, after["auth.user"], login)
    if "authtoken.token" in before:
        assert_auth_tokens(
            case, users, before["authtoken.token"], after["authtoken.token"], login
        )
    if "sessions.session" in before:
        assert_session_rows(
            before["sessions.session"], after["sessions.session"], login
        )


def assert_user_rows(
    case: str,
    before: dict[str, Any],
    after: dict[str, Any],
    login: LoginInterval | None,
) -> None:
    """Permit only the exact actor's native-login timestamp, with every other value exact.

    :param case: Actual actor lane.
    :param before: Full original user rows including last_login at full precision.
    :param after: Full actual current user rows.
    :param login: Exact native interval; None permits no user change at all.
    :return: None after timestamps and all unrelated fields are preserved.
    :raises AssertionError: Any user effect is outside the exact supported event.
    """
    if login is None:
        assert before == after, "User state changed without a native login."
        return
    assert ACTORS[case] is not None and login.actor == ACTORS[case]
    assert before.keys() == after.keys()
    assert sum(row["fields"]["username"] == login.actor for row in before.values()) == 1
    for pk, row in before.items():
        if row["fields"]["username"] == login.actor:
            assert_login_user(row, after[pk], login)
        else:
            assert row == after[pk], "Unrelated account changed."


def assert_login_user(
    before: dict[str, Any], after: dict[str, Any], login: LoginInterval
) -> None:
    """Compare all actor fields exactly except its one precisely bounded last_login.

    :param before: Complete original actor serialization.
    :param after: Actual current actor serialization.
    :param login: Actual POST/302 interval.
    :return: None when only the source-supported timestamp changed.
    :raises AssertionError: Field shape/value or full-precision timestamp differs.
    """
    stamp = after["fields"]["last_login"]
    assert after == {**before, "fields": {**before["fields"], "last_login": stamp}}
    assert stamp != before["fields"]["last_login"]
    assert login.started_at <= utc_timestamp(stamp) <= login.completed_at


def assert_auth_tokens(
    case: str,
    users: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
    login: LoginInterval | None = None,
) -> None:
    """Allow only the existing login flow's one token creation for its exact actor.

    :param case: Implemented actor lane.
    :param users: Original serialized user rows with their actual PKs.
    :param before: Private pre-login token rows.
    :param after: Private post-browser token rows, never exported.
    :param login: Exact native interval required for any permitted new token.
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
        assert login is not None and login.actor == actor
        assert_new_auth_token(pk, after[pk], user, login)


def assert_new_auth_token(
    pk: str, row: dict[str, Any], user: int | None, login: LoginInterval
) -> None:
    """Check actual new login token structure privately without printing its value.

    :param pk: Private new token key, never exported.
    :param row: Actual serialized token row.
    :param user: Exact original authenticated actor ID.
    :param login: Actual native POST/302 interval.
    :return: None when every generated-token field matches the existing schema.
    :raises AssertionError: Token identity, actor or metadata shape differs.
    """
    assert re.fullmatch(r"[a-f0-9]{40}", pk)
    assert row["model"] == "authtoken.token" and row["pk"] == pk
    fields = row["fields"]
    assert fields.keys() == {"user", "created"} and fields["user"] == user
    assert login.started_at <= utc_timestamp(fields["created"]) <= login.completed_at


def assert_session_rows(
    before: dict[str, Any], after: dict[str, Any], login: LoginInterval | None
) -> None:
    """Preserve existing sessions and bind one normal insertion to the actual cookie.

    :param before: Complete private original session rows.
    :param after: Complete actual session rows.
    :param login: Exact native event; None allows no session writes.
    :return: None after key identity and precise normal expiry are checked.
    :raises AssertionError: Existing state, insertion count, digest or expiry differs.
    """
    assert all(after.get(pk) == row for pk, row in before.items())
    added = after.keys() - before.keys()
    if login is None:
        assert not added
        return
    assert len(added) == 1
    key = next(iter(added))
    assert re.fullmatch(r"[a-z0-9]{32}", key)
    assert hashlib.sha256(key.encode()).hexdigest() == login.session_key_sha256
    row = after[key]
    assert row["pk"] == key and row["model"] == "sessions.session"
    assert row["fields"].keys() == {"session_data", "expire_date"}
    created = utc_timestamp(row["fields"]["expire_date"]) - timedelta(
        seconds=NORMAL_LOGIN_EXPIRY_SECONDS
    )
    assert login.started_at <= created <= login.completed_at
