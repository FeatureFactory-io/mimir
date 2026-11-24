"""S30 domain bindings using the real Django-client acceptance context."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from behave import given, then, when
from behave.runner import Context
from django.test import Client
from django.test.html import Element
from django.urls import reverse

from methodology.models import KarmaAward, PlaybookVersion, VersionSource
from methodology.services.experts_service import ExpertsService
from tests.support.experts_html import element_text, find_by_test_id
from tests.support.experts_release import NoraReleaseCase, build_nora_release_case

_PLAYBOOK_ID = 6302
_PLAYBOOK_NAME = "Accessible Workshop Starter"
_PRODUCT = "product"
_FIRST_RELEASE_VERSION = Decimal("1.0")
_FIRST_RELEASE_POINTS = 5000
_FIRST_RELEASE_IDENTITY = f"first_release:{_PLAYBOOK_ID}"
_RELEASE_NOTES = "Publish the workshop guide"
_FIRST_RELEASE_MESSAGE = (
    "You earned 5,000 Karma for releasing Accessible Workshop Starter"
)
_PRODUCT_RANKING = [("experts-card-apatel", "5,400"), ("experts-card-nberg", "5,000")]


@given("Nora owns draft Accessible Workshop Starter in Product")
def nora_owns_product_draft(context: Context) -> None:
    """Verify the restored baseline and normal release prerequisites.

    :param context: Real isolated AT context. Example: Cedar baseline context.
    :return: None after retaining Nora and playbook 6302 for the action.
    :raises AssertionError: If ownership, draft status or baseline points differ.
    """
    case = build_nora_release_case()
    assert case.author == context.cedar_dataset.users_by_username["nberg"]
    assert case.playbook == context.cedar_dataset.playbooks_by_pk[_PLAYBOOK_ID]
    assert case.playbook.name == _PLAYBOOK_NAME
    assert ExpertsService().project_user(case.author.pk).total_points == 0

    client = Client(enforce_csrf_checks=True)
    client.force_login(case.author)
    context.release_case = replace(case, client=client)


@when("she first releases it as version 1.0")
def nora_first_releases_playbook(context: Context) -> None:
    """POST the actual authenticated release route with required notes.

    :param context: Context containing Nora's target/client. Example: playbook 6302.
    :return: None after retaining the followed real release response.
    :raises AssertionError: If the normal publication path does not reach v1.0.
    """
    case: NoraReleaseCase = context.release_case
    target = {"pk": case.playbook.pk}
    detail_url = reverse("playbook_detail", kwargs=target)
    detail = case.client.get(detail_url)
    assert detail.status_code == 200
    csrf_token = str(detail.context["csrf_token"])
    response = case.client.post(
        reverse("playbook_release", kwargs=target),
        {"release_description": _RELEASE_NOTES, "csrfmiddlewaretoken": csrf_token},
        follow=True,
    )
    assert response.redirect_chain == [(detail_url, 302)]
    assert response.status_code == 200
    case.playbook.refresh_from_db()
    assert (case.playbook.status, case.playbook.version) == (
        "released",
        _FIRST_RELEASE_VERSION,
    )
    assert PlaybookVersion.objects.filter(
        playbook=case.playbook,
        source=VersionSource.RELEASE,
        version_number=_FIRST_RELEASE_VERSION,
    ).exists()
    context.release_response = response


@then("Nora's total changes from 0 to 5000 in Product")
def nora_receives_first_release_points(context: Context) -> None:
    """Read the actual persisted award and live ledger projection.

    :param context: Completed real release context. Example: Nora's v1.0 release.
    :return: None when total, category, source and one-row award agree.
    :raises AssertionError: If points or attribution differ.
    """
    case: NoraReleaseCase = context.release_case
    rows = KarmaAward.objects.filter(recipient=case.author).values_list(
        "event_identity", "playbook_id_snapshot", "source_kind", "category", "points"
    )
    assert list(rows) == [
        (
            _FIRST_RELEASE_IDENTITY,
            case.playbook.pk,
            KarmaAward.SourceKind.RELEASE,
            _PRODUCT,
            _FIRST_RELEASE_POINTS,
        )
    ]
    projection = ExpertsService().project_user(case.author.pk)
    assert projection.total_points == _FIRST_RELEASE_POINTS
    assert projection.category_points == ((_PRODUCT, _FIRST_RELEASE_POINTS),)


@then("the Product ranking is Alex 5400 followed by Nora 5000")
def product_ranking_after_nora_release(context: Context) -> None:
    """GET the production Product list and assert its actual ordered cards.

    :param context: Real client context. Example: Nora after successful release.
    :return: None when apatel precedes nberg at the exact displayed totals.
    :raises AssertionError: If ordering or scores differ.
    """
    case: NoraReleaseCase = context.release_case
    response = case.client.get(reverse("experts_list"), {"category": _PRODUCT})
    assert response.status_code == 200
    tab = find_by_test_id(response.content, "experts-category-product")
    assert dict(tab.attributes)["aria-current"] == "page"
    leaderboard = find_by_test_id(response.content, "experts-leaderboard")
    ranked_cards = [
        (
            dict(card.attributes)["data-testid"],
            element_text(find_by_test_id(str(card), "expert-card-karma")),
        )
        for card in leaderboard.children
        if isinstance(card, Element) and card.name == "article"
    ]
    assert ranked_cards == _PRODUCT_RANKING


@then('she sees "You earned 5,000 Karma for releasing Accessible Workshop Starter"')
def nora_sees_first_release_award(context: Context) -> None:
    """Inspect the real success message in the followed release response.

    :param context: Context retaining the actual release HTTP response.
    :return: None when the exact earned message appears in the standard alert.
    :raises AssertionError: If the visible message is absent or inaccurate.
    """
    alert = find_by_test_id(context.release_response.content, "alert-message")
    attributes = dict(alert.attributes)
    assert attributes["role"] == "alert"
    assert "alert-success" in attributes["class"].split()
    assert element_text(alert) == _FIRST_RELEASE_MESSAGE
