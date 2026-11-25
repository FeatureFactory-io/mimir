"""Closed row and traffic policies for the literal C01–C05 companion only."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from contract import allow_browser_request

CASE = "summary-acceptance"


def allow_summary_request(url: str, method: str, pip_id: int) -> bool:
    """Check only real reads and the exact normal login/submit/review POSTs.

    :param url: Actual browser URL.
    :param method: Actual request method.
    :param pip_id: Prepared actual positive proposal identity.
    :return: Whether this original request may proceed.
    :raises ValueError: The proposal identity is invalid.
    """
    if type(pip_id) is not int or pip_id <= 0:
        raise ValueError("An actual positive prepared proposal is required.")
    if allow_browser_request(url, method):
        return True
    try:
        parsed = urlsplit(url)
        owned = (parsed.scheme, parsed.hostname, parsed.port) == (
            "https",
            "cedar-web",
            8443,
        )
    except (ValueError, TypeError):
        return False
    paths = {
        "/auth/user/login/",
        f"/pips/{pip_id}/submit/",
        f"/pips/{pip_id}/admin-review/",
    }
    return (
        owned
        and method == "POST"
        and parsed.path in paths
        and not any((parsed.username, parsed.password, parsed.query, parsed.fragment))
    )


def assert_closed_rows(
    before: dict[str, Any],
    after: dict[str, Any],
    changes: dict[str, dict[str, frozenset[str]]],
    additions: dict[str, int],
) -> None:
    """Preserve all models, unrelated rows and all unlisted fields exactly.

    :param before: Full private original model/PK/field snapshot.
    :param after: Actual full precise snapshot.
    :param changes: Explicit model/PK/field allowances validated separately.
    :param additions: Exact required insertion count by model.
    :return: None when the closed delta matches.
    :raises AssertionError: Any unlisted field, model, deletion or insertion differs.
    """
    assert before and before.keys() == after.keys(), "Model set changed."
    assert changes.keys() <= before.keys() and additions.keys() <= before.keys()
    for model, rows in before.items():
        current = after[model]
        assert rows.keys() <= current.keys(), "Existing row deleted."
        assert len(current.keys() - rows.keys()) == additions.get(model, 0), model
        for pk, row in rows.items():
            fields = changes.get(model, {}).get(pk, frozenset())
            assert fields <= row["fields"].keys()
            expected = {
                **row,
                "fields": {
                    **row["fields"],
                    **{field: current[pk]["fields"][field] for field in fields},
                },
            }
            assert (
                current[pk] == expected
            ), f"Unexpected existing row delta: {model}/{pk}"
