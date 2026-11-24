"""Acceptance assertions for the public expert detail response."""

from __future__ import annotations

import re

from behave import then
from behave.runner import Context
from django.http.response import HttpResponseBase
from django.test.html import Element, parse_html

from methodology.models import ExpertProfile
from tests.support.experts_html import element_text, find_by_test_id

_SUMMARY_TEST_ID = "expert-contribution-summary"
_MIN_HTTP_STATUS = 100
_MAX_HTTP_STATUS = 599
_TRUNCATION_CLASSES = frozenset(
    {"expert-hint", "expert-summary-collapsed", "text-truncate"}
)
_INLINE_TRUNCATION = re.compile(
    r"(?:^|;)\s*(?:(?:-webkit-)?line-clamp\s*:\s*\d|text-overflow\s*:\s*ellipsis\b)",
    re.IGNORECASE,
)


@then(
    '"expert-contribution-summary" contains the complete stored nine-sentence paragraph'
)
@then('"expert-contribution-summary" contains her full stored paragraph')
def complete_stored_contribution_paragraph(context: Context) -> None:
    """Compare rendered summary with Maria's real stored baseline.

    :param context: Real AT response and Cedar ORM state. Example: Maria detail response.
    :return: None. Example: exact complete paragraph, including final sentence.
    :raises AssertionError: For shortened or substituted text.
    """
    response = context.response
    assert response.status_code == 200
    maria_id = context.cedar_dataset.user_ids["mrodriguez"]
    stored_summary = ExpertProfile.objects.values_list(
        "contribution_summary", flat=True
    ).get(user_id=maria_id)
    assert stored_summary, "Cedar Maria must have a stored contribution summary."
    person = response.context["person"]
    assert person["subject_id"] == maria_id
    assert person["summary"] == stored_summary
    paragraph = find_by_test_id(response.content, _SUMMARY_TEST_ID)
    assert paragraph.name == "p"
    assert paragraph.children == [stored_summary], "The rendered paragraph differs."


@then("the paragraph has no line clamp or ellipsis truncation")
def public_paragraph_has_no_truncation_contract(context: Context) -> None:
    """Check the server-rendered summary has no truncation contract.

    :param context: Actual detail response. Example: expert-contribution-summary node.
    :return: None. Example: no clamp class, inline clamp or substituted ellipsis.
    :raises AssertionError: For server-authored truncation.
    """
    paragraph = find_by_test_id(context.response.content, _SUMMARY_TEST_ID)
    attributes = dict(paragraph.attributes)
    assert _TRUNCATION_CLASSES.isdisjoint(
        attributes.get("class", "").split()
    ), "The public summary uses a truncation class."
    assert not _INLINE_TRUNCATION.search(
        attributes.get("style", "")
    ), "The public summary declares inline truncation."


@then('the title includes "{title}"')
def public_title_includes_identity(context: Context, title: str) -> None:
    """Assert the real response title contains the selected public identity, independently of page H1.

    :param context: Actual Django-client acceptance state. Example: Maria's detail GET.
    :param title: Expected public identity title fragment. Example: Maria Rodriguez.
    :return: None when the rendered document title contains the identity.
    :raises AssertionError: If the response or document title differs.
    """
    response = context.response
    assert response.status_code == 200
    document = parse_html(response.content.decode(response.charset))
    titles = [
        child
        for head in document.children
        if isinstance(head, Element) and head.name == "head"
        for child in head.children
        if isinstance(child, Element) and child.name == "title"
    ]
    assert len(titles) == 1, "Expected one title in the document head."
    assert title in element_text(titles[0]), "Expected identity in the document title."


@then("the response status is {status:d}")
def public_response_has_expected_status(context: Context, status: int) -> None:
    """Compare the observed Django response with the specified HTTP status.

    :param context: Real acceptance state, e.g. context.response from a GET.
    :param status: Expected integer HTTP status, e.g. 404.
    :return: None when the actual response matches, e.g. HTTP 404 equals 404.
    :raises ValueError: Invalid status value, e.g. True or 600.
    :raises AssertionError: Missing response or mismatch, e.g. HTTP 200 versus 404.
    """
    if type(status) is not int or not _MIN_HTTP_STATUS <= status <= _MAX_HTTP_STATUS:
        raise ValueError("An integer HTTP status from 100 through 599 is required.")
    response = getattr(context, "response", None)
    assert isinstance(response, HttpResponseBase), "A Django HTTP response is required."
    assert (
        response.status_code == status
    ), f"Expected HTTP {status}, got HTTP {response.status_code}."
