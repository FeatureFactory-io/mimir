from __future__ import annotations
from behave import then, when

"S46 server-contract bindings; clipboard proof remains Playwright."
from behave.runner import Context


@when("a private read is denied or a clipboard write or export fails")
def fail_or_deny_consumption(context: Context) -> None:
    """Run actual private-read denial and filesystem-service failure cases.

    :param context: Real AT client and independently restored Cedar baseline.
    :return: None. Example: failures and complete ledger snapshots retained.
    :raises AssertionError: Operation unexpectedly succeeds or lacks evidence.
    """
    raise NotImplementedError()


@then("no consumption award is created for either party")
def assert_no_consumption_awards(context: Context) -> None:
    """Assert every captured server failure preserved the complete ledger.

    :param context: Real server failure results and original snapshots.
    :return: None. Example: no recipient has a new or mutated award.
    :raises AssertionError: Any global ledger field differs.
    """
    raise NotImplementedError()
