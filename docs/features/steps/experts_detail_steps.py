from __future__ import annotations
from behave import then
from behave.runner import Context


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
    raise NotImplementedError()


@then("the paragraph has no line clamp or ellipsis truncation")
def public_paragraph_has_no_truncation_contract(context: Context) -> None:
    """Check the server-rendered summary has no truncation contract.

    :param context: Actual detail response. Example: expert-contribution-summary node.
    :return: None. Example: no clamp class, inline clamp or substituted ellipsis.
    :raises AssertionError: For server-authored truncation.
    """
    raise NotImplementedError()


@then('the title includes "{title}"')
def public_title_includes_identity(context: Context, title: str) -> None:
    """Assert the real response title contains the selected public identity, independently of page H1.

    :param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: Actual domain, response or recorded boundary differs.
    """
    raise NotImplementedError()


@then("the response status is {status:d}")
def public_response_has_expected_status(context: Context, status: int) -> None:
    """Assert the actual Django response status; missing and zero-score profiles share generic 404 content.

    :param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: Actual domain, response or recorded boundary differs.
    """
    raise NotImplementedError()
