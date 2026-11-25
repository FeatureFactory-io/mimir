"""Independent source-bound contracts for the two remaining S04 visual variants."""

from __future__ import annotations

import ast
import copy
import hashlib
import os
import stat
from pathlib import Path
from typing import Any

from saga_contract import (
    allow_saga_request,
    assert_row_delta,
    checked_login_interval,
    utc_timestamp,
)

CASES = ("long_identity_and_prose", "missing_summary")
SOURCE_SHA256 = "896285a8b9281e28cda5f66515c7e09a5c3bbcab96caa0d3f5e712046abac379"
SOURCE_BLOB = "5993562e018f62cff3d8973bc20c54756dbf5ba8"
FIXTURE_SHA256 = "ecac2f4494984eecd7216e94d3dcd3d75512359f8d50d06f712c4cd7d47dfbfb"
_LITERALS = frozenset(
    {
        "VIEWPORTS",
        "_LONG_FIRST",
        "_LONG_LAST",
        "_LONG_SUMMARY",
        "_MIKE_FALLBACK",
        "_CATEGORIES",
    }
)
_ORDERS = {
    "Design": ["sreed", "mrodriguez", "pnair", "dortiz", "hkim"],
    "Development": ["mchen", "jlee"],
}


def validate_output(output: Path) -> Path:
    """Require the caller's existing private acquisition root without ORM imports.

    :param output: Absolute freshly owned mode0700 evidence directory.
    :return: Unchanged validated path.
    :raises ValueError: A linked, foreign, public or nonexistent path is supplied.
    """
    if not isinstance(output, Path) or not output.is_absolute():
        raise ValueError("An absolute private acquisition directory is required.")
    if not output.is_dir() or output.resolve() != output or output.is_symlink():
        raise ValueError("Existing acquisition directory cannot contain links.")
    info = output.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("Owned mode0700 acquisition directory required.")
    return output


def source_constants(path: Path) -> dict[str, Any]:
    """Read checked literal constants without importing Django-coupled test code.

    :param path: Exact candidate04 S04 browser test source.
    :return: Declared immutable literal values and source identities.
    :raises ValueError: Candidate source bytes or constant declarations differ.
    """
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Exact candidate04 S04 source bytes required.")
    values = {}
    for node in ast.parse(raw).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in _LITERALS:
                values[target.id] = ast.literal_eval(node.value)
    if values.keys() != _LITERALS:
        raise ValueError("Exact literal S04 declarations required.")
    return {**values, "source_sha256": SOURCE_SHA256, "source_blob": SOURCE_BLOB}


def validate_case(case: str) -> str:
    """Require one independent visual case.

    :param case: Explicit long or missing variant.
    :return: Unchanged validated case.
    :raises ValueError: Any other case, including the normal/guest matrices.
    """
    if type(case) is not str or case not in CASES:
        raise ValueError("Explicit long/missing visual variant required.")
    return case


def expected_contributors(
    document: dict[str, Any], case: str, constants: dict[str, Any]
) -> tuple[str, list[dict[str, str]]]:
    """Derive display expectations from the independent Cedar fixture.

    :param document: Actual pristine Cedar JSON.
    :param case: One declared visual variant.
    :param constants: Checked candidate source constants.
    :return: Category and exact ranked contributors including the declared variant.
    :raises ValueError: Case or fixture oracle differs.
    """
    validate_case(case)
    category = "Development" if case == "missing_summary" else "Design"
    order = document["expected_" + category.lower() + "_order"]
    if order != _ORDERS[category]:
        raise ValueError("Independent Cedar category order differs.")
    people = {person["username"]: dict(person) for person in document["people"]}
    if case == "long_identity_and_prose":
        people["mrodriguez"].update(
            name=constants["_LONG_FIRST"] + " " + constants["_LONG_LAST"],
            summary=constants["_LONG_SUMMARY"],
        )
    rows = [
        {
            "username": name,
            "name": people[name]["name"],
            "total": f"{people[name]['total_karma']:,}",
            "email": people[name]["email"],
            "hint": people[name]["summary"]
            or f"{len(people[name]['public_playbooks'])} released playbooks · {people[name]['copy_count']} copies",
        }
        for name in order
    ]
    if case == "missing_summary":
        assert (
            rows[0]["total"] == "12,450"
            and rows[0]["hint"] == constants["_MIKE_FALLBACK"]
        )
    return category, rows


def assert_preparation_rows(
    before: dict[str, Any], after: dict[str, Any], case: str, constants: dict[str, Any]
) -> None:
    """Require precisely Maria's three declared fields, or no changes for missing.

    :param before: All installed concrete and automatic M2M baseline rows.
    :param after: Same complete projection after bounded ORM preparation.
    :param case: Exact variant.
    :param constants: Independently checked candidate source literals.
    :return: None only after exact row comparison.
    :raises AssertionError: Any other field, row or model differs.
    """
    validate_case(case)
    expected = copy.deepcopy(before)
    if case == "long_identity_and_prose":
        users = expected["auth.user"]
        maria = [
            pk for pk, row in users.items() if row["fields"]["username"] == "mrodriguez"
        ]
        assert len(maria) == 1
        user_id = maria[0]
        fields = users[user_id]["fields"]
        assert (
            fields["first_name"] != constants["_LONG_FIRST"]
            and fields["last_name"] != constants["_LONG_LAST"]
        )
        fields.update(
            first_name=constants["_LONG_FIRST"], last_name=constants["_LONG_LAST"]
        )
        profiles = [
            row
            for row in expected["methodology.expertprofile"].values()
            if str(row["fields"]["user"]) == user_id
        ]
        assert (
            len(profiles) == 1
            and profiles[0]["fields"]["contribution_summary"]
            != constants["_LONG_SUMMARY"]
        )
        profiles[0]["fields"]["contribution_summary"] = constants["_LONG_SUMMARY"]
    assert after == expected, "Only the exact three declared ORM fields may change."


def allow_visual_request(url: str, method: str) -> bool:
    """Allow original reads and only the ordinary native login write.

    :param url: Actual browser request URL.
    :param method: Actual HTTP method.
    :return: Whether the request is an explicitly allowed destination.
    """
    return allow_saga_request("nomination", url, method)


def assert_visual_effects(
    baseline: dict[str, Any],
    after: dict[str, Any],
    observation: dict[str, Any],
    verified_at: str,
    session_age: int,
) -> None:
    """Apply the reviewed exact Elena login exceptions to all39 model rows.

    :param baseline: Private prepared variant rows and timestamp.
    :param after: Complete real post-browser snapshot.
    :param observation: Actual native login envelope and cookie digest.
    :param verified_at: Precise actual verification timestamp.
    :param session_age: Actual configured normal session age.
    :return: None after strict whole-row comparison.
    :raises AssertionError: Any unrelated effect or malformed envelope occurs.
    """
    start, end = utc_timestamp(baseline["prepared_at"]), utc_timestamp(verified_at)
    assert 0 <= (end - start).total_seconds() <= 720
    assert session_age == 1209600
    login = checked_login_interval("esvensson", observation, (start, end), session_age)
    assert assert_row_delta("nomination", baseline["rows"], after, login) == []
