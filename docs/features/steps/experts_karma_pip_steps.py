from __future__ import annotations

from behave import given, then, when
from behave.runner import Context


@given("Maria's new PIP targets Hana's Accessible Forms Review version 2.0")
def prepare_maria_major_add_target(context: Context) -> None:
    """Retain the independently restored real target before the Example selects type.

    :param context: Isolated AT context. Example: context.cedar_dataset from S03.
    :return: None. Example: real target 6106 is retained at version 2.0.
    :raises AssertionError: If baseline authorship or version differs.
    """
    raise NotImplementedError()


@when("an Administrator accepts its eligible ADD {entity} change")
def accept_maria_major_add(context: Context, entity: str) -> None:
    """Create a reviewed real change and finalize through the administrator POST.

    :param context: AT context with a real Django client. Example: context.client.
    :param entity: Exact outline row. Example: "Artifact".
    :return: None. Example: actual finalization response and change are retained.
    :raises AssertionError: If authorization, application or finalization fails.
    """
    raise NotImplementedError()


@then("Maria's total becomes 8700 and Design subtotal becomes 7700")
def assert_maria_major_add_totals(context: Context) -> None:
    """Assert live ledger projections and the submitter-only change award.

    :param context: Context containing the real finalized change. Example: PIP 42.
    :return: None. Example: Maria 8700/7700, Hana and administrator unchanged.
    :raises AssertionError: If totals, recipient or immutable attribution differs.
    """
    raise NotImplementedError()


@then("the target playbook is version 3.0")
def assert_major_add_target_version(context: Context) -> None:
    """Assert one actual major publication and no repeated first-release credit.

    :param context: Context with the finalized target. Example: playbook 6106.
    :return: None. Example: one new PIP version at 3.0 and no release award.
    :raises AssertionError: If publication or first-release invariants differ.
    """
    raise NotImplementedError()


@then("the normal decision notification is captured locally")
def assert_major_add_local_notification(context: Context) -> None:
    """Assert the existing postcommit email in local-memory capture.

    :param context: Real isolated AT context. Example: finalized ADD Skill case.
    :return: None. Example: one accepted decision email to Maria includes 3.0.
    :raises AssertionError: If recipient, body, count or delivery timing differs.
    """
    raise NotImplementedError()
