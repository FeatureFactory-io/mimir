from __future__ import annotations

from behave import then, when
from behave.runner import Context


@when("she exports Mike's public released workflow 6202 into multiple local files")
def export_mikes_workflow(context: Context) -> None:
    """Call the real registered export tool and retain actual temp-file evidence.

    :param context: Isolated Cedar/token context. Example: context.cedar_dataset.
    :return: None with export result/event evidence stored. Example: None.
    :raises RuntimeError: If actual MCP export cannot complete.
    """
    raise NotImplementedError()


@then("the actual export files are written within the authorized export root")
def assert_confined_actual_export_files(context: Context) -> None:
    """Read actual produced files and verify each resolved authorized root.

    :param context: Context containing export result/root. Example: context.
    :return: None after actual filesystem assertions. Example: None.
    :raises AssertionError: If content is missing or any destination escapes.
    """
    raise NotImplementedError()


@then("the award is per successful call rather than per generated file")
def assert_one_export_award_pair(context: Context) -> None:
    """Verify exactly two five-point rows share one export event UUID.

    :param context: Baseline and actual completed export. Example: context.
    :return: None after pair/channel/count assertions. Example: None.
    :raises AssertionError: If files or nested content multiplied awards.
    """
    raise NotImplementedError()
