"""S30 real Django-client acceptance contract."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.http import HttpResponse
from django.test.html import Element
from django.urls import reverse

from methodology.models import KarmaAward, PlaybookVersion, VersionSource
from methodology.services.experts_service import ExpertsService
from tests.support.experts_html import element_text, find_by_test_id
from tests.support.experts_release import NoraReleaseCase, build_nora_release_case

_EARNED_MESSAGE = "You earned 5,000 Karma for releasing Accessible Workshop Starter"
_RELEASE_NOTES = "Publish the workshop guide"


@pytest.mark.django_db
def test_karma_release_01_with_baseline_displays_award_and_product_ranking() -> None:
    """Execute Nora's normal release POST and query the live Product list.

    Assert baseline Nora=0, target version=1.0, Nora=5000 Product points, exact
    earned message, and rendered Product order apatel=5400 then nberg=5000.
    Read the real ledger/projection and HTTP responses; do not hard-code scores
    into rendered fixtures or replace domain services with mocks.

    :return: None when every KARMA-RELEASE-01 observable matches the contract.
    :raises AssertionError: If any amount, version, message or rank differs.
    """
    case = build_nora_release_case()
    assert ExpertsService().project_user(case.author.pk).total_points == 0

    response = _post_release(case)
    _assert_alert(response, _EARNED_MESSAGE, style="success")
    case.playbook.refresh_from_db()
    assert case.playbook.status == "released"
    assert case.playbook.version == Decimal("1.0")
    award = KarmaAward.objects.get(recipient=case.author)
    assert (award.points, award.category) == (5000, "product")
    assert award.source_kind == KarmaAward.SourceKind.RELEASE

    projection = ExpertsService().project_user(case.author.pk)
    assert projection.total_points == 5000
    assert projection.category_points == (("product", 5000),)
    product = case.client.get(reverse("experts_list"), {"category": "product"})
    assert _rendered_product_scores(product) == [
        ("experts-card-apatel", "5,400"),
        ("experts-card-nberg", "5,000"),
    ]


@pytest.mark.django_db
def test_release_with_nonfirst_outcome_omits_earned_message() -> None:
    """Keep normal release success without claiming another first award.

    :return: None when later publication succeeds without an earned-5000 message.
    :raises AssertionError: If the message announces unearned points.
    """
    case = build_nora_release_case()
    _assert_alert(_post_release(case), _EARNED_MESSAGE, style="success")

    later = _post_release(case)

    _assert_alert(later, "Playbook released.", style="success")
    case.playbook.refresh_from_db()
    assert case.playbook.version == Decimal("2.0")
    assert list(
        KarmaAward.objects.filter(recipient=case.author).values_list(
            "points", flat=True
        )
    ) == [5000]


@pytest.mark.django_db
@pytest.mark.parametrize("category", ["", "retired"], ids=["blank", "retired"])
def test_release_with_invalid_first_category_displays_validation_error(
    category: str,
) -> None:
    """Show the domain validation in the existing alert without publishing.

    :param category: Legacy draft category. Example: "retired".
    :return: None when the error renders and the draft remains intact.
    :raises AssertionError: If the view misreports or publishes the invalid draft.
    """
    case = build_nora_release_case()
    original_version = case.playbook.version
    case.playbook.category = category
    case.playbook.save(update_fields=["category"])

    response = _post_release(case)

    _assert_alert(
        response, "Choose a valid playbook category before releasing.", style="danger"
    )
    case.playbook.refresh_from_db()
    assert case.playbook.status == "draft"
    assert case.playbook.version == original_version
    assert not PlaybookVersion.objects.filter(
        playbook=case.playbook, source=VersionSource.RELEASE
    ).exists()
    assert not KarmaAward.objects.filter(recipient=case.author).exists()


def _post_release(case: NoraReleaseCase) -> HttpResponse:
    """Submit the existing owner release form and follow its normal redirect.

    :param case: Restored case. Example: Nora with Cedar draft 6302.
    :return: Final HTTP response. Example: playbook detail with a success alert.
    :raises AssertionError: If publication does not redirect to the same playbook.
    """
    url = reverse("playbook_release", kwargs={"pk": case.playbook.pk})
    response = case.client.post(
        url, {"release_description": _RELEASE_NOTES}, follow=True
    )
    assert response.redirect_chain == [
        (reverse("playbook_detail", kwargs={"pk": case.playbook.pk}), 302)
    ]
    return response


def _assert_alert(response: HttpResponse, expected: str, *, style: str) -> None:
    """Verify exact feedback and the existing alert semantics on detail.

    :param response: Redirected response. Example: rendered playbook detail.
    :param expected: Complete alert text. Example: "Playbook released.".
    :param style: Bootstrap alert variant. Example: "success".
    :return: None when the existing alert matches text and severity.
    :raises AssertionError: If feedback is absent, misplaced or differs.
    """
    assert response.status_code == 200
    alert = find_by_test_id(response.content, "alert-message")
    attributes = dict(alert.attributes)
    assert attributes["role"] == "alert"
    assert f"alert-{style}" in attributes["class"].split()
    assert element_text(alert) == expected


def _rendered_product_scores(response: HttpResponse) -> list[tuple[str, str]]:
    """Read actual Product card identities and scores in document order.

    :param response: Leaderboard response. Example: GET /experts/?category=product.
    :return: Ordered card IDs and visible scores. Example: [("experts-card-apatel", "5,400")].
    :raises AssertionError: If Product or the expected semantic elements are missing.
    """
    assert response.status_code == 200
    tab = find_by_test_id(response.content, "experts-category-product")
    assert dict(tab.attributes)["aria-current"] == "page"
    leaderboard = find_by_test_id(response.content, "experts-leaderboard")
    return [
        (
            dict(card.attributes)["data-testid"],
            element_text(find_by_test_id(str(card), "expert-card-karma")),
        )
        for card in leaderboard.children
        if isinstance(card, Element) and card.name == "article"
    ]
