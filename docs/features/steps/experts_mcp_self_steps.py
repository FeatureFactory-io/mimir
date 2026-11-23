from __future__ import annotations

"""Distinct S40 bindings; reuse undecorated support, never import step modules."""
from behave import given, then, when
from behave.runner import Context


@given("{consumer} has a valid MCP token and existing permission for {content}")
def given_self_fetch_permission(context: Context, consumer: str, content: str) -> None:
    """Resolve real Cedar content, token and pre-operation ledger state.

    :param context: Existing transactional AT context. Example: cedar_dataset.
    :param consumer: Literal actor. Example: "Mike".
    :param content: Exact outline content. Example: "Mike's Activity".
    :return: None. Example: genuine permission and snapshot established.
    :raises AssertionError: Fixture role, token or permission is wrong.
    """
    raise NotImplementedError()


@when("the consumer successfully uses {tool} on that content")
def when_self_fetch_succeeds(context: Context, tool: str) -> None:
    """Exercise real authorized detail GET and shared token receipt boundary.

    :param context: Prepared case/client. Example: Mike activity self-fetch.
    :param tool: Existing detail tool name. Example: "get_activity".
    :return: None. Example: actual content and successful zero-award receipt.
    :raises AssertionError: Wrong tool, denied read or failed receipt.
    """
    raise NotImplementedError()


@then("the consumer total remains {total:d} and no paired author award is created")
def then_self_fetch_preserves_karma(context: Context, total: int) -> None:
    """Assert full-ledger equality and all-user totals after the real request.

    :param context: Completed operation and snapshot. Example: Maria PIP.
    :param total: Literal expected total. Example: 8200.
    :return: None. Example: actor, target author and entire ledger unchanged.
    :raises AssertionError: Content was not successful or any award changed.
    """
    raise NotImplementedError()
