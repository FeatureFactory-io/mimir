"""S23 normal submission steps; real Django domain and captured provider seam."""

from __future__ import annotations

from decimal import Decimal

from behave import given, then, when
from behave.runner import Context
from django.urls import reverse

from methodology.llm.base import LLMResponse
from methodology.models import (
    Activity,
    AgentInteraction,
    ExpertProfile,
    KarmaAward,
    PipChange,
    Playbook,
    PlaybookVersion,
    ProcessImprovementProposal,
    VersionSource,
)
from methodology.services.contribution_summary_prompts import (
    MAX_SUMMARY_TOKENS,
    _count_sentences,
)
from methodology.services.experts_service import ExpertsService
from methodology.services.galdr_prompts import HOLISTIC_SYSTEM_PROMPT
from tests.support.experts_summary_data import (
    SUMMARY_SCRIPTS,
    load_summary_script,
    prepare_summary_submission,
    summary_processing_scope,
)

_REQUEST_ID = "cedar-summary-submission-at"


@given("Hana owns Accessible Forms Review at version 2.0")
def hana_target_has_original_publication(context: Context) -> None:
    """Verify real Hana authorship, current v2.0 and historical accepted-change receipts.

    :param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: Actual domain, response or recorded boundary differs.
    """
    cedar = context.cedar_dataset
    hana = cedar.users_by_username["hkim"]
    target = Playbook.objects.get(pk=cedar.playbook_ids[6106])
    assert (target.author_id, target.name, target.version) == (
        hana.pk,
        "Accessible Forms Review",
        Decimal("2.0"),
    )
    assert (target.visibility, target.status) == ("public", "released")
    historical_pip = cedar.pips_by_key["HIST-MARIA-DESIGN-01"]
    receipt = target.versions.get(
        pip=historical_pip,
        source=VersionSource.PIP_SOURCE,
        version_number=target.version,
    )
    accepted = historical_pip.changes.filter(admin_decision=PipChange.ADMIN_ACCEPT)
    assert set(receipt.snapshot_data["accepted_change_ids"]) == {
        change.pk for change in accepted
    }
    assert receipt.snapshot_data["accepted_change_ids"]


@given("Maria drafts Screen Reader Error Recovery with one ADD Activity change")
def maria_drafts_error_recovery_activity(context: Context) -> None:
    """Create Maria's draft and one ADD through PIPService.

    :param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: Actual domain, response or recorded boundary differs.
    """
    cedar = context.cedar_dataset
    pip = prepare_summary_submission(cedar)
    change = pip.changes.get()
    assert pip.created_by_id == cedar.users_by_username["mrodriguez"].pk
    assert pip.status == ProcessImprovementProposal.STATUS_DRAFT
    assert (pip.title, change.name) == ("Screen Reader Error Recovery",) * 2
    assert change.change_type == PipChange.CHANGE_ADD
    assert change.entity_type == PipChange.ENTITY_ACTIVITY
    assert change.parent_workflow.playbook_id == pip.playbook_id
    context.s23_pip = pip


@when("Maria submits the PIP through its normal lifecycle")
def maria_submits_normal_summary_lifecycle(context: Context) -> None:
    """Submit through the authenticated Django client with a two-turn provider script.

    :param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: Actual domain, response or recorded boundary differs.
    """
    pip = context.s23_pip
    ids = {"pk": pip.pk}
    script = load_summary_script(
        SUMMARY_SCRIPTS / "PRF-EXPERTS-01/happy.json", pip.changes.get().pk
    )
    summary = script[0]
    assert isinstance(summary, LLMResponse)
    context.s23_expected_summary = summary.content
    context.s23_awards_before = tuple(KarmaAward.objects.order_by("pk").values_list())
    context.s23_versions_before = tuple(
        pip.playbook.versions.order_by("pk").values_list()
    )
    profile = ExpertProfile.objects.get(user_id=pip.created_by_id)
    context.s23_previous_update = profile.summary_updated_at
    context.client.force_login(pip.created_by)
    # The Behave TestCase rolls back its outer transaction. Run the callback it registered.
    with (
        summary_processing_scope(script) as llm,
        context.test.captureOnCommitCallbacks(execute=True),
    ):
        response = context.client.post(
            reverse("pip_submit_review", kwargs=ids),
            headers={"X-Request-ID": _REQUEST_ID},
        )
    assert response.status_code == 302
    assert response.url == reverse("pip_detail", kwargs=ids)
    assert response.wsgi_request.user == pip.created_by
    context.s23_calls = llm.calls


@then("a contribution-summary refresh is requested during processing")
def summary_refresh_occurs_during_processing(context: Context) -> None:
    """Prove one public summary request and the existing private Galdr assessment.

    :param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: Actual domain, response or recorded boundary differs.
    """
    pip = context.s23_pip
    pip.refresh_from_db()
    assert pip.status == ProcessImprovementProposal.STATUS_REVIEWED
    assert pip.submitted_at is not None and pip.reviewed_at is not None
    assert pip.galdr_holistic_assessment
    change = pip.changes.get()
    assert change.galdr_recommendation == PipChange.GALDR_ACCEPT
    assert change.galdr_reasoning == "The proposed activity fits the review workflow."
    public_call, assessment_call = context.s23_calls
    assert public_call.max_tokens == MAX_SUMMARY_TOKENS
    assert "Identity: You are the public contribution summarizer." in public_call.system
    assert assessment_call.system == HOLISTIC_SYSTEM_PROMPT
    assert pip.title in assessment_call.messages[0].content
    interaction = AgentInteraction.objects.get(pip=pip)
    assert interaction.subject_id == pip.created_by_id
    assert interaction.workflow_id == "contribution_summary"
    assert interaction.correlation_id == _REQUEST_ID
    assert pip.submitted_at <= interaction.created_at <= pip.reviewed_at
    context.s23_interaction = interaction


@then("Maria's total remains {total:d}")
def maria_summary_total_remains(context: Context, total: int) -> None:
    """Check the live total and unchanged award ledger after submission.

    :param context: Actual isolated Django-client acceptance state. Example: context.s23_pip.
    :param total: Expected actual ledger total. Example: 8200.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: The projection or ledger differs.
    """
    projection = ExpertsService().project_user(context.s23_pip.created_by_id)
    assert projection.total_points == total
    assert (
        tuple(KarmaAward.objects.order_by("pk").values_list())
        == context.s23_awards_before
    )


@then("the new proposal is not described as accepted")
def summary_excludes_unpublished_proposal(context: Context) -> None:
    """Check public input and stored prose exclude the proposal and no ADD was published.

    :param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: Actual domain, response or recorded boundary differs.
    """
    pip = context.s23_pip
    change = pip.changes.get()
    public_call = context.s23_calls[0]
    profile = ExpertProfile.objects.get(user_id=pip.created_by_id)
    public_text = "\n".join(
        (
            public_call.system,
            *(message.content for message in public_call.messages),
            profile.contribution_summary,
        )
    )
    for unpublished in (pip.title, pip.summary, change.content):
        assert unpublished and unpublished not in public_text
    assert "Keyboard Navigation Audit" in public_call.messages[0].content
    assert change.admin_decision == PipChange.ADMIN_UNSET
    assert pip.decided_at is None
    assert not Activity.objects.filter(
        workflow__playbook_id=pip.playbook_id, name=change.name
    ).exists()
    assert not PlaybookVersion.objects.filter(pip=pip).exists()
    assert pip.playbook.version == Decimal("2.0")
    assert (
        tuple(pip.playbook.versions.order_by("pk").values_list())
        == context.s23_versions_before
    )


@then("the successful public summary is stored on her profile")
def summary_success_persists_validated_prose(context: Context) -> None:
    """Compare the scripted response with the validated persisted profile and trace.

    :param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: Actual domain, response or recorded boundary differs.
    """
    profile = ExpertProfile.objects.get(user_id=context.s23_pip.created_by_id)
    assert profile.contribution_summary == context.s23_expected_summary
    assert profile.summary_updated_at is not None
    assert profile.summary_updated_at != context.s23_previous_update
    assert profile.summary_status == ExpertProfile.SummaryStatus.SUCCESS
    assert profile.last_summary_correlation_id == _REQUEST_ID
    interaction = context.s23_interaction
    assert interaction.outcome == AgentInteraction.Outcome.SUCCESS
    assert any(
        event["beat"] == "validation" and "status=accepted" in event["details"].split()
        for event in interaction.events
    )
    context.s23_stored_summary = profile.contribution_summary


@then("it contains at most {limit:d} sentences")
def summary_obeys_sentence_bound(context: Context, limit: int) -> None:
    """Count the sentences in the stored paragraph using the shared validator logic.

    :param context: Actual isolated Django-client acceptance state. Example: context.s23_stored_summary.
    :param limit: Maximum allowed stored sentence count. Example: 14.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: The stored summary is empty or exceeds the limit.
    """
    assert 0 < _count_sentences(context.s23_stored_summary) <= limit
