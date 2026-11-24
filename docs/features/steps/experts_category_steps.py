from __future__ import annotations

from http import HTTPStatus
from urllib.parse import urljoin

from behave import given, then, when
from behave.runner import Context

from methodology.models import KarmaAward, Playbook
from methodology.services.experts_service import ExpertProjection, ExpertsService
from tests.support.experts_category_html import category_anchors
from tests.support.experts_category_ties import CategoryTieDataset, load_category_tie

_TIED_CATEGORY_POINTS = {"development": 5_000, "design": 5_000}
_TIED_TOTAL = 10_000
_CATEGORY_LABELS = dict(Playbook.CATEGORY_CHOICES)
_EXPERTS_LIST_PATH = "/experts/"
_DESIGN_URL = "/experts/?category=design"
_PAGE_CURRENT = "page"
_EXPECTED_CATEGORIES = (
    ("Product", "product"),
    ("Development", "development"),
    ("Research", "research"),
    ("Design", "design"),
    ("Other", "other"),
)


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
    :raises AssertionError: If the category, destination or successful response differs.
    """
    slug = dict(_EXPECTED_CATEGORIES).get(category)
    assert slug is not None, f"Unknown category label {category!r}."
    context.execute_steps(
        f'Given Elena is authenticated\nWhen Elena opens "{_EXPERTS_LIST_PATH}"'
    )
    response = context.response
    assert response.status_code == HTTPStatus.OK, "The Experts list did not load."
    links = category_anchors(response.content.decode(response.charset))
    matches = [anchor for anchor in links if anchor.label == category]
    assert len(matches) == 1, f"Expected one link for {category!r}, got {matches!r}."
    path = urljoin(response.wsgi_request.get_full_path(), matches[0].href)
    assert path == f"{_EXPERTS_LIST_PATH}?category={slug}", path
    context.execute_steps(f'When Elena opens "{path}"')
    assert context.response.status_code == HTTPStatus.OK, f"Could not open {path!r}."


@then("category links show Product, Development, Research, Design and Other")
def category_links_show_all_categories(context: Context) -> None:
    """Assert the complete ordered category navigation from rendered HTML.

    :param context: AT context with response. Example: Design list response.
    :return: None. Example: all five labels and hrefs asserted.
    :raises AssertionError: If links differ in count, order, label, destination or hook.
    """
    response = context.response
    path = response.wsgi_request.get_full_path()
    links = category_anchors(response.content.decode(response.charset))
    actual = [(link.label, urljoin(path, link.href), link.test_id) for link in links]
    expected = [
        (label, f"{_EXPERTS_LIST_PATH}?category={slug}", f"experts-category-{slug}")
        for label, slug in _EXPECTED_CATEGORIES
    ]
    assert actual == expected, f"Expected category links {expected!r}, got {actual!r}."


@then('the Design link has aria-current "{value}"')
def design_link_has_current_state(context: Context, value: str) -> None:
    """Assert Design alone exposes the requested current-page state.

    :param context: AT context with response. Example: Design list response.
    :param value: Required aria-current value. Example: "page".
    :return: None. Example: Design is the only current anchor.
    :raises AssertionError: If current state is absent, wrong or duplicated.
    """
    response = context.response
    links = category_anchors(response.content.decode(response.charset))
    current = [
        (link.label, link.aria_current)
        for link in links
        if link.aria_current is not None
    ]
    assert current == [("Design", value)], (
        f"Unexpected category current state {current!r}."
    )


@when("she refreshes the page")
def refresh_current_category_page(context: Context) -> None:
    """Request the last response URL again without changing its query.

    :param context: AT context with real response. Example: ?category=design.
    :return: None. Example: response replaced by the repeated GET response.
    :raises AssertionError: If the Design response is missing or the repeated GET fails.
    """
    response = getattr(context, "response", None)
    assert response is not None and response.status_code == HTTPStatus.OK, (
        "The category page must load successfully before refresh."
    )
    path = response.wsgi_request.get_full_path()
    assert path == _DESIGN_URL, f"Expected the Design URL before refresh, got {path!r}."
    context.execute_steps(f'When Elena opens "{path}"')
    assert context.response.status_code == HTTPStatus.OK, f"Could not refresh {path!r}."


@then("Design remains current")
def design_remains_current(context: Context) -> None:
    """Assert the refreshed URL and uniquely current Design anchor agree.

    :param context: AT context after refresh. Example: Design response.
    :return: None. Example: unchanged Design query and current state asserted.
    :raises AssertionError: If refresh changes the query or current category.
    """
    context.execute_steps(f'Then the URL is "{_DESIGN_URL}"')
    design_link_has_current_state(context, _PAGE_CURRENT)
