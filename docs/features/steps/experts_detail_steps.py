from __future__ import annotations

from behave import then
from behave.runner import Context


@then(
    '"expert-contribution-summary" contains the complete stored nine-sentence paragraph'
)
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
