from __future__ import annotations

from behave import given, then, when
from behave.runner import Context

from methodology.models import KarmaAward, Playbook
from methodology.services.experts_service import ExpertProjection, ExpertsService
from tests.support.experts_category_ties import CategoryTieDataset, load_category_tie

_TIED_CATEGORY_POINTS = {"development": 5_000, "design": 5_000}
_TIED_TOTAL = 10_000
_CATEGORY_LABELS = dict(Playbook.CATEGORY_CHOICES)


@given("the isolated {variant} data")
def isolated_category_data(context: Context, variant: str) -> None:
    """Build the historical variant in the scenario's isolated test database.

    :param context: Transactional Behave context with the baseline already loaded.
    :param variant: Historical tie fixture. Example: "TIE01".
    :return: None. Example: context.category_tie contains the Development tie case.
    :raises ValueError: For an unknown variant or a conflicting test fixture.
    :raises AssertionError: If the shared Cedar identities change.
    """
    tie = load_category_tie(variant)
    assert tie.baseline.user_ids == context.cedar_dataset.user_ids
    assert tie.baseline.playbook_ids == context.cedar_dataset.playbook_ids
    context.category_tie = tie


@when("the user's primary playbook category is projected")
def project_primary_category(context: Context) -> None:
    """Capture the real ledger and ask the canonical service for the projection.

    :param context: Behave context containing the loaded CategoryTieDataset.
    :return: None. Example: context.category_projection holds the actual total.
    :raises RuntimeError: If the variant was not prepared.
    :raises ValueError: If the persisted variant user cannot be projected.
    """
    tie: CategoryTieDataset | None = getattr(context, "category_tie", None)
    if tie is None:
        raise RuntimeError("Load the Cedar tie variant before projecting its category.")
    context.category_ledger_before = tuple(
        KarmaAward.objects.order_by("pk").values_list()
    )
    context.category_projection = ExpertsService().project_user(tie.user.pk)


@then("the result is {category}")
def category_result(context: Context, category: str) -> None:
    """Verify the real category decision, projected points and unchanged ledger.

    :param context: Behave context with the actual service projection and prior ledger.
    :param category: Expected Gherkin display category. Example: "Design".
    :return: None. Example: the Design tie still totals 10,000 after the query.
    :raises AssertionError: If the category, totals or complete ledger differ.
    """
    projection: ExpertProjection = context.category_projection
    assert projection.primary_category is not None, "No primary category was projected."
    assert _CATEGORY_LABELS.get(projection.primary_category) == category
    assert projection.total_points == _TIED_TOTAL
    assert dict(projection.category_points) == _TIED_CATEGORY_POINTS
    assert context.category_ledger_before == tuple(
        KarmaAward.objects.order_by("pk").values_list()
    )


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
