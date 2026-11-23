from __future__ import annotations

"""Unique S04 Django-client acceptance bindings."""
from behave import then
from behave.runner import Context


@then('card "{card_id}" shows rank {rank:d} and "{display_name}"')
def card_identity(context: Context, card_id: str, rank: int, display_name: str) -> None:
    """Retain the requested real HTTP article and assert identity.

    :param context: Shared Cedar AT context. Example: context.cedar_dataset.
    :param card_id: Stable article hook. Example: "experts-card-mrodriguez".
    :param rank: Expected position. Example: 2.
    :param display_name: Expected visible name. Example: "Maria Rodriguez".
    :return: None. Example: scoped card retained for subsequent Then steps.
    :raises AssertionError: If article, rank or identity is incorrect.
    """
    raise NotImplementedError()


@then(
    'it shows total "{total}", category "{category}", and an accessibility contribution hint'
)
def card_signals(context: Context, total: str, category: str) -> None:
    """Assert the actual scoped card values against Cedar's stored public prose.

    :param context: Context retaining Maria's article. Example: Design response.
    :param total: Formatted overall total. Example: "8,200".
    :param category: Display category. Example: "Design".
    :return: None. Example: total/category/accessibility evidence verified.
    :raises AssertionError: If values or public hint differ.
    """
    raise NotImplementedError()


@then("it has an avatar or initials plus View profile and Reach out controls")
def card_actions(context: Context) -> None:
    """Assert initials and actual S17/S14 controls from rendered HTML.

    :param context: Context retaining Maria's article. Example: rank-two card.
    :return: None. Example: MR, View profile and Reach out verified.
    :raises AssertionError: If identity fallback or either action is absent.
    """
    raise NotImplementedError()


@then("it makes no availability or suitability assertion")
def card_claims(context: Context) -> None:
    """Reject added inferred claims while preserving the approved caveat.

    :param context: Scoped card and Cedar oracle. Example: Maria's public prose.
    :return: None. Example: exact prose and no recommendation fields.
    :raises AssertionError: If additional assertions appear.
    """
    raise NotImplementedError()
