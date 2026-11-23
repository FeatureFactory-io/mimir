from __future__ import annotations

from behave import then, when

from behave import given
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


@when('Elena selects the "{category}" playbook category')
def select_playbook_category(context: Context, category: str) -> None:
    """Follow an actual rendered category href using the real Django client.

    :param context: AT context. Example: context.cedar_dataset and client.
    :param category: Visible category label. Example: "Design".
    :return: None. Example: context.response is the Design list response.
    :raises AssertionError: If the category anchor or successful response is absent.
    :raises NotImplementedError: Until BPE implements this binding.
    """
    raise NotImplementedError


@then("category links show Product, Development, Research, Design and Other")
def category_links_show_all_categories(context: Context) -> None:
    """Assert the complete ordered category navigation from rendered HTML.

    :param context: AT context with response. Example: Design list response.
    :return: None. Example: all five labels and hrefs asserted.
    :raises AssertionError: If links differ in count, order, label or destination.
    :raises NotImplementedError: Until BPE implements this binding.
    """
    raise NotImplementedError


@then('the Design link has aria-current "{value}"')
def design_link_has_current_state(context: Context, value: str) -> None:
    """Assert Design alone exposes the requested current-page state.

    :param context: AT context with response. Example: Design list response.
    :param value: Required aria-current value. Example: "page".
    :return: None. Example: Design is the only current anchor.
    :raises AssertionError: If current state is absent, wrong or duplicated.
    :raises NotImplementedError: Until BPE implements this binding.
    """
    raise NotImplementedError


@when("she refreshes the page")
def refresh_current_category_page(context: Context) -> None:
    """Request the last response URL again without changing its query.

    :param context: AT context with real response. Example: ?category=design.
    :return: None. Example: response replaced by the repeated GET response.
    :raises AssertionError: If there is no successful category response to refresh.
    :raises NotImplementedError: Until BPE implements this binding.
    """
    raise NotImplementedError


@then("Design remains current")
def design_remains_current(context: Context) -> None:
    """Assert the refreshed URL and uniquely current Design anchor agree.

    :param context: AT context after refresh. Example: Design response.
    :return: None. Example: unchanged Design query and current state asserted.
    :raises AssertionError: If refresh changes the query or current category.
    :raises NotImplementedError: Until BPE implements this binding.
    """
    raise NotImplementedError
