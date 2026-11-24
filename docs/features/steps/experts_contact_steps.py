from __future__ import annotations

from behave import then
from behave.runner import Context
from django.core import mail
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from tests.support.experts_guest_contact import (
    GUEST_CONTACT_EXPLANATION,
    assert_guest_contact_markup,
)
from tests.support.experts_guest_detail import assert_guest_detail_evidence_readable

_WRITE_PREFIXES = ("INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "ALTER", "DROP")


@then("Reach out is disabled and has no mailto destination")
def guest_detail_reach_out_is_restricted(context: Context) -> None:
    """Check native disabled guest contact in the actual initial response.

    :param context: Real AT response and Cedar dataset. Example: S16 context.
    :return: None. Example: None after shared guest markup assertion.
    :raises AssertionError: If contact is enabled or any contact email leaks.
    """
    emails = tuple(
        user.email for user in context.cedar_dataset.users_by_username.values()
    )
    assert_guest_contact_markup(context.response, None, emails)


@then('its focusable wrapper explains "{explanation}"')
def guest_contact_wrapper_explains(context: Context, explanation: str) -> None:
    """Check wrapper focusability and explanation association in initial HTML.

    :param context: Real AT response. Example: S16 public detail response.
    :param explanation: Exact required description. Example: GUEST_CONTACT_EXPLANATION.
    :return: None. Example: None after matching text and aria-describedby.
    :raises ValueError: If the requested explanation differs from the contract.
    :raises AssertionError: If explanation, target ID or focusable markup differs.
    """
    if explanation != GUEST_CONTACT_EXPLANATION:
        raise ValueError(
            "Guest contact requires the canonical accessibility explanation."
        )
    guest_detail_reach_out_is_restricted(context)


@then("public contribution and released-playbook evidence remain readable")
def guest_detail_public_evidence_is_readable(context: Context) -> None:
    """Check public prose and real anonymous evidence HTTP access.

    :param context: AT client, response and cedar_dataset. Example: S16 context.
    :return: None. Example: None after shared server evidence assertion.
    :raises AssertionError: If full prose or public released evidence is unavailable.
    """
    _assert_read_only_public_navigation(context)


def _assert_read_only_public_navigation(context: Context) -> None:
    """Read real public evidence and repeat detail GET without changing any table.

    :param context: Existing anonymous AT client and baseline, e.g. Bob and Maria.
    :return: None after actual detail/playbook/workflow requests preserve state.
    :raises AssertionError: If a read writes SQL, changes mail or schedules a callback.
    """
    before, prior_mail = _database_rows(), tuple(getattr(mail, "outbox", ()))
    with (
        TestCase.captureOnCommitCallbacks() as callbacks,
        CaptureQueriesContext(connection) as queries,
    ):
        assert_guest_detail_evidence_readable(
            context.client, context.response, context.cedar_dataset
        )
        repeated = context.client.get(context.response.wsgi_request.path, follow=False)
        assert_guest_detail_evidence_readable(
            context.client, repeated, context.cedar_dataset
        )
    if _database_rows() != before or tuple(getattr(mail, "outbox", ())) != prior_mail:
        raise AssertionError("Anonymous evidence reads changed database or mail state.")
    if callbacks or any(
        row["sql"].lstrip().upper().startswith(_WRITE_PREFIXES) for row in queries
    ):
        raise AssertionError(
            "Anonymous evidence reads wrote SQL or scheduled a callback."
        )


def _database_rows() -> tuple[tuple[str, tuple[tuple[object, ...], ...]], ...]:
    """Keep a deterministic snapshot of every table privately in memory.

    :return: Complete table rows, e.g. account, token, profile and ledger state.
    :raises RuntimeError: If the isolated acceptance database is unavailable.
    """
    snapshots = []
    with connection.cursor() as cursor:
        for table in sorted(connection.introspection.table_names(cursor)):
            cursor.execute(f"SELECT * FROM {connection.ops.quote_name(table)}")
            snapshots.append((table, tuple(sorted(cursor.fetchall(), key=repr))))
    return tuple(snapshots)
