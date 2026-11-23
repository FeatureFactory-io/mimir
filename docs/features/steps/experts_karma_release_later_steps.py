from __future__ import annotations

from behave import given, then, when
from behave.runner import Context


@given("a playbook has already earned its first-release award")
def playbook_has_first_release_award(context: Context) -> None:
    """Use existing Cedar context and normally publish Nora's real draft.

    :param context: Real AT context. Example: context.cedar_dataset and client.
    :return: None. Example: retained Nora/6302, v1.0 and original 5000-row snapshot.
    :raises AssertionError: If baseline zero or actual first release differs.
    """
    raise NotImplementedError()


@when("an accepted PIP publishes its next major version")
def accepted_pip_publishes_next_major(context: Context) -> None:
    """Prepare reviewed fixture then POST real admin finalization as Cedar Mike.

    :param context: Completed first-release context. Example: Nora/6302 at v1.0.
    :return: None. Example: accepted ADD Activity, v2.0/PIP_SOURCE response retained.
    :raises AssertionError: If acceptance, inserted activity or next major fails.
    """
    raise NotImplementedError()


@then("its author receives no additional 5000 first-release points")
def author_receives_no_repeated_first_release_points(context: Context) -> None:
    """Read actual immutable release row and Nora's release subtotal.

    :param context: Actual finalized-PIP context. Example: Nora/6302 at v2.0.
    :return: None. Example: same first_release:6302 row and Product release sum 5000.
    :raises AssertionError: If any release-award field/count/amount changes.
    """
    raise NotImplementedError()
