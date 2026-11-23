from __future__ import annotations

from behave import given, then, when

from behave import then, when
from behave.runner import Context


@when("a contribution-summary request is assembled for Maria")
def assemble_maria_public_summary_request(context: Context) -> None:
    """Assemble the real public snapshot and prompt without calling a provider.

    :param context: Actual Cedar AT context. Example: Maria's baseline rows.
    :return: None; retain actual evidence and request for subsequent assertions.
    :raises ValueError: If real request assembly fails.
    """
    raise NotImplementedError()


@then(
    "it includes only released public playbook evidence and changes already published by acceptance"
)
def assert_summary_evidence_is_published_public(context: Context) -> None:
    """Assert actual assembled data against real publication/current-visibility rows.

    :param context: Actual assembled request. Example: Maria's prompt.
    :return: None when eligible facts survive and ineligible rows are absent.
    :raises AssertionError: If evidence selection is incorrect.
    """
    raise NotImplementedError()


@then("it excludes private playbooks, private PIPs, API tokens and email addresses")
def assert_summary_excludes_private_material(context: Context) -> None:
    """Check actual serialized request against Cedar's distinct private sentinels.

    :param context: Request and real Cedar rows. Example: Maria's privacy case.
    :return: None when private material is absent.
    :raises AssertionError: If any protected byte enters the assembled request.
    """
    raise NotImplementedError()


@then("it instructs the generator to omit Karma totals and category point subtotals")
def assert_summary_prompt_excludes_scores(context: Context) -> None:
    """Assert actual safety instructions and absence of numeric score data.

    :param context: Actual layered request. Example: Maria's prompt.
    :return: None when instructions and data satisfy the score exclusion.
    :raises AssertionError: If score instructions/data are wrong.
    """
    raise NotImplementedError()


@then("submitting a PIP does not make its unpublished title or content public")
def assert_submission_is_not_publication(context: Context) -> None:
    """Assert unpublished proposal content is absent and publication state unchanged.

    :param context: Real proposal plus assembled request. Example: Screen Reader PIP.
    :return: None when submission grants no publication.
    :raises AssertionError: If unpublished title/content enters public evidence.
    """
    raise NotImplementedError()


@given("Maria's PIP has reached Reviewed")
def s25_maria_pip_reached_reviewed(context: Context) -> None:
    """Reach Reviewed through genuine initial submission and finite model turns.

    :param context: Real AT context. Example: context.cedar_dataset from S03.
    :return: None. Example: context retains PIP, script and first interaction.
    :raises AssertionError: If real initial processing does not reach Reviewed.
    """
    raise NotImplementedError()


@when("she withdraws it and resubmits through the normal allowed lifecycle")
def s25_withdraw_and_resubmit(context: Context) -> None:
    """POST existing revert and submit routes with Maria's real session.

    :param context: Reviewed run context. Example: first summary persisted.
    :return: None. Example: context retains real responses and refreshed PIP.
    :raises AssertionError: For incorrect transitions or failed HTTP requests.
    """
    raise NotImplementedError()


@then("summary refresh is requested again before an administrator decision")
def s25_assert_second_refresh_before_decision(context: Context) -> None:
    """Assert second request, interaction and valid stored prose before decision.

    :param context: Completed resubmission context. Example: four consumed calls.
    :return: None. Example: None after real interaction/decision assertions.
    :raises AssertionError: For missing refresh, publication or administrator action.
    """
    raise NotImplementedError()
