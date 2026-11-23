from __future__ import annotations

from behave import given, when, then
from behave.runner import Context


@given("the isolated {variant} data")
def isolated_category_data(context: Context, variant: str) -> None:
    """Build real isolated variant, preserving shared baseline references.
    :param context: Transactional Behave context.
    :param variant: TIE01 or TIE02.
    :return: None.
    :raises ValueError: Unknown variant.
    """
    raise NotImplementedError()


@when("the user's primary playbook category is projected")
def project_primary_category(context: Context) -> None:
    """Call S03 canonical projection and capture before/after ledger.
    :param context: Context containing CategoryTieDataset.
    :return: None.
    :raises RuntimeError: Variant was not prepared.
    """
    raise NotImplementedError()


@then("the result is {category}")
def category_result(context: Context, category: str) -> None:
    """Assert actual canonical result, 10,000 total and unchanged awards.
    :param context: Context containing actual projection.
    :param category: Expected display category; example: "Design".
    :return: None.
    :raises AssertionError: Category, arithmetic or snapshot differs.
    """
    raise NotImplementedError()
