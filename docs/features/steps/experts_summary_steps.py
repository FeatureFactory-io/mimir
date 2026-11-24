from __future__ import annotations

import json
import re
from contextlib import ExitStack
from decimal import Decimal
from pathlib import Path

from behave import given, then, when
from behave.runner import Context
from django.test import override_settings
from django.urls import reverse

from methodology.llm.base import LLMResponse
from methodology.models import (
    Activity,
    AgentInteraction,
    ExpertProfile,
    KarmaAward,
    PipChange,
    Playbook,
    ProcessImprovementProposal,
)
from methodology.services.contribution_summary_boundary import (
    PublicContributionSummaryBoundary,
)
from methodology.services.galdr_prompts import HOLISTIC_SYSTEM_PROMPT
from methodology.services.public_contribution_evidence import (
    PublicContributionEvidenceService,
)
from tests.support.experts_data import seed_s27_summary_privacy_variant
from tests.support.experts_summary_data import (
    SUMMARY_PIP_BODY,
    SUMMARY_SCRIPTS,
    load_summary_script,
    prepare_summary_submission,
    summary_processing_scope,
)
from tests.support.scripted_llm import ScriptedLLM

_S27_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "tests/fixtures/llm_scripts/PRF-EXPERTS-03/happy.json"
)
_S27_COUNT_SENTINEL = "117 copies"
_S27_SCORE_VALUES = re.compile(r"\b(?:8,?200|7,?200|1,?000)\b")
_S27_FACT_FIELDS = frozenset(
    {
        "playbook_id",
        "playbook_name",
        "category",
        "kind",
        "entity_type",
        "operation",
        "title",
        "text",
    }
)
_S27_AUTHORED_PLAYBOOK = "Accessibility Audit Playbook"
_S27_AUTHORED_TITLES = frozenset(
    {
        _S27_AUTHORED_PLAYBOOK,
        "Lead an Accessibility Review",
        "Trace Keyboard Focus",
        "Review Form Feedback",
        "Document Recovery Paths",
    }
)
_S27_PUBLISHED_CHANGES = frozenset(
    {
        ("Accessible Forms Review", "ADD", "Keyboard Navigation Audit"),
        ("Accessible Forms Review", "ALTER", "Error Message Review"),
        ("React Frontend Development", "ADD", "Accessible component fixture"),
        ("React Frontend Development", "ADD", "Focus regression checklist"),
    }
)


@when("a contribution-summary request is assembled for Maria")
def assemble_maria_public_summary_request(context: Context) -> None:
    """Capture one actual request with only the model transport scripted.

    :param context: Actual Cedar AT context. Example: Maria's baseline rows.
    :return: None. Retain the captured model request and its decoded evidence.
    :raises AssertionError: If the call count, request envelope or subject differs.
    """
    case = seed_s27_summary_privacy_variant()
    subject_id = context.cedar_dataset.user_ids["mrodriguez"]
    assert case["subject_id"] == subject_id
    focus = Activity.objects.get(
        workflow__playbook_id=context.cedar_dataset.playbook_ids[6101],
        name="Trace Keyboard Focus",
    )
    focus.guidance += f"\n{_S27_COUNT_SENTINEL}."
    focus.save(update_fields=["guidance"])
    llm = _s27_scripted_model()
    PublicContributionSummaryBoundary(PublicContributionEvidenceService()).complete(
        subject_id, llm=llm, correlation_id="galdr-summary-05-at"
    )
    (call,) = llm.calls
    (message,) = call.messages
    assert message.role == "user" and call.max_tokens == 1024
    begin, payload, end = message.content.splitlines()
    assert (begin, end) == ("BEGIN PUBLIC EVIDENCE JSON", "END PUBLIC EVIDENCE JSON")
    context.s27_evidence = json.loads(payload)
    assert context.s27_evidence["subject_id"] == subject_id
    context.s27_system_prompt = call.system
    context.s27_request_text = f"{call.system}\n{message.content}"
    context.s27_privacy_case = case


def _s27_scripted_model() -> ScriptedLLM:
    """Load the one-turn PRF-EXPERTS-03 script for the request inspection.

    :return: Finite ScriptedLLM queue. Example: Maria's valid public paragraph.
    :raises AssertionError: If the turn is not a successful scripted response.
    """
    (turn,) = json.loads(_S27_SCRIPT.read_text(encoding="utf-8"))["responses"]
    assert turn["kind"] == "response"
    response = LLMResponse(
        content=turn["content"],
        model=turn["model"],
        usage=turn["usage"],
        stop_reason=turn["stop_reason"],
    )
    return ScriptedLLM((response,))


@then(
    "it includes only released public playbook evidence and changes already published by acceptance"
)
def assert_summary_evidence_is_published_public(context: Context) -> None:
    """Assert actual assembled data against real publication/current-visibility rows.

    :param context: Actual assembled request. Example: Maria's prompt.
    :return: None when eligible facts survive and ineligible rows are absent.
    :raises AssertionError: If evidence selection is incorrect.
    """
    facts = context.s27_evidence["facts"]
    book_ids = {fact["playbook_id"] for fact in facts}
    public_books = dict(
        Playbook.objects.filter(
            pk__in=book_ids, visibility="public", status="released"
        ).values_list("pk", "name")
    )
    assert all(
        public_books.get(fact["playbook_id"]) == fact["playbook_name"] for fact in facts
    )
    assert {
        (fact["playbook_name"], fact["title"])
        for fact in facts
        if fact["kind"] == "authored"
    } == {(_S27_AUTHORED_PLAYBOOK, title) for title in _S27_AUTHORED_TITLES}
    assert {
        (fact["playbook_name"], fact["operation"], fact["title"])
        for fact in facts
        if fact["kind"] == "published_change"
    } == _S27_PUBLISHED_CHANGES
    assert len(facts) == len(_S27_AUTHORED_TITLES) + len(_S27_PUBLISHED_CHANGES)
    assert any(
        fact["title"] == "Error Message Review"
        and fact["text"] == "Use the real published activity guidance."
        for fact in facts
    )


@then("it excludes private playbooks, private PIPs, API tokens and email addresses")
def assert_summary_excludes_private_material(context: Context) -> None:
    """Check actual serialized request against Cedar's distinct private sentinels.

    :param context: Request and real Cedar rows. Example: Maria's privacy case.
    :return: None when private material is absent.
    :raises AssertionError: If any protected byte enters the assembled request.
    """
    assert all(
        sentinel not in context.s27_request_text
        for sentinel in context.s27_privacy_case["sentinels"]
    ), "The captured request contains protected Cedar data."
    assert "Check the focus order." in context.s27_request_text


@then("it instructs the generator to omit Karma totals and category point subtotals")
def assert_summary_prompt_excludes_scores(context: Context) -> None:
    """Assert actual safety instructions and absence of numeric score data.

    :param context: Actual layered request. Example: Maria's prompt.
    :return: None when instructions and data satisfy the score exclusion.
    :raises AssertionError: If score instructions/data are wrong.
    """
    foundation, identity = context.s27_system_prompt.split("\n\n", maxsplit=1)
    assert foundation.startswith("Foundation policy:") and "quoted data" in foundation
    assert "Omit private or unpublished material" in foundation
    assert (
        "Karma totals, category point subtotals, ranks and aggregate counts"
        in foundation
    )
    assert identity.startswith("Identity: You are the public contribution summarizer.")
    assert set(context.s27_evidence) == {"subject_id", "facts"}
    assert all(set(fact) == _S27_FACT_FIELDS for fact in context.s27_evidence["facts"])
    assert not _S27_SCORE_VALUES.search(context.s27_request_text)
    assert _S27_COUNT_SENTINEL not in context.s27_request_text


@then("submitting a PIP does not make its unpublished title or content public")
def assert_submission_is_not_publication(context: Context) -> None:
    """Assert unpublished proposal content is absent and publication state unchanged.

    :param context: Real proposal plus assembled request. Example: Screen Reader PIP.
    :return: None when submission grants no publication.
    :raises AssertionError: If unpublished title/content enters public evidence.
    """
    pip = context.s27_privacy_case["submitted_pip"]
    pip.refresh_from_db()
    assert pip.status == ProcessImprovementProposal.STATUS_SUBMITTED
    assert (pip.playbook.visibility, pip.playbook.status) == ("public", "released")
    change = pip.changes.get()
    assert change.admin_decision == PipChange.ADMIN_UNSET
    assert not pip.playbook_versions.exists()
    assert all(
        value and value not in context.s27_request_text
        for value in (pip.title, pip.summary, change.content)
    ), "The captured request contains unpublished proposal content."


_S25_SCRIPT = SUMMARY_SCRIPTS / "PRF-EXPERTS-01/resubmission_happy.json"
_S25_INITIAL_RUN = "cedar-summary-initial-at"
_S25_SECOND_RUN = "cedar-summary-resubmission-at"
_S25_REVISED_BODY = (
    "Unpublished revision clarifying the screen reader recovery rationale."
)


@given("Maria's PIP has reached Reviewed")
def s25_maria_pip_reached_reviewed(context: Context) -> None:
    """Reach Reviewed through genuine initial submission and finite model turns.

    :param context: Real AT context. Example: context.cedar_dataset from S03.
    :return: None. Example: context retains PIP, script and first interaction.
    :raises AssertionError: If real initial processing does not reach Reviewed.
    """
    pip = prepare_summary_submission(context.cedar_dataset)
    context.s25_pip = pip
    context.s25_script = load_summary_script(_S25_SCRIPT, pip.changes.get().pk)
    context.s25_versions = tuple(pip.playbook.versions.order_by("pk").values_list())
    # The shared exact-step binding compares the live projection and full ledger.
    context.s23_pip = pip
    context.s23_awards_before = tuple(KarmaAward.objects.order_by("pk").values_list())
    context.client.force_login(pip.created_by)
    scope = ExitStack()
    context.add_cleanup(scope.close)
    scope.enter_context(override_settings(GALDR_USE_TARGET_STATE=True))
    context.s25_llm = scope.enter_context(summary_processing_scope(context.s25_script))
    first_summary, first_assessment, _, _ = context.s25_script
    context.s25_first = _s25_submit(
        context, _S25_INITIAL_RUN, first_summary, first_assessment
    )
    assert len(context.s25_llm.calls) == 2


@when("she withdraws it and resubmits through the normal allowed lifecycle")
def s25_withdraw_and_resubmit(context: Context) -> None:
    """POST existing revert, edit and submit routes with Maria's real session.

    :param context: Reviewed run context. Example: first summary persisted.
    :return: None. Example: context retains the refreshed PIP.
    :raises AssertionError: For incorrect transitions or failed HTTP requests.
    """
    pip = context.s25_pip
    first_profile, first_interaction = context.s25_first
    first_calls = context.s25_llm.calls
    _s25_post(context, "pip_revert_to_draft", "pip_detail")
    pip.refresh_from_db()
    change = pip.changes.get()
    assert pip.status == pip.STATUS_DRAFT
    assert pip.galdr_holistic_assessment == ""
    assert change.galdr_recommendation == change.galdr_reasoning == ""
    _s25_post(
        context,
        "pip_edit",
        "pip_edit",
        data={
            "action": "save_header",
            "title": pip.title,
            "summary": _S25_REVISED_BODY,
        },
    )
    pip.refresh_from_db()
    assert pip.status == pip.STATUS_DRAFT and pip.summary == _S25_REVISED_BODY
    assert context.s25_llm.calls == first_calls
    assert list(AgentInteraction.objects.filter(pip=pip)) == [first_interaction]
    current = ExpertProfile.objects.get(pk=first_profile.pk)
    assert current.contribution_summary == first_profile.contribution_summary
    assert current.summary_updated_at == first_profile.summary_updated_at
    _, _, second_summary, second_assessment = context.s25_script
    context.s25_second = _s25_submit(
        context, _S25_SECOND_RUN, second_summary, second_assessment
    )


@then("summary refresh is requested again before an administrator decision")
def s25_assert_second_refresh_before_decision(context: Context) -> None:
    """Assert independent refreshes, public inputs and unchanged publication.

    :param context: Completed resubmission context. Example: four consumed calls.
    :return: None. Example: None after real interaction/decision assertions.
    :raises AssertionError: For missing refresh, publication or administrator action.
    """
    pip = context.s25_pip
    first_profile, first = context.s25_first
    second_profile, second = context.s25_second
    assert tuple(AgentInteraction.objects.filter(pip=pip).order_by("pk")) == (
        first,
        second,
    )
    assert first.call_id and second.call_id and first.call_id != second.call_id
    assert second_profile.summary_updated_at > first_profile.summary_updated_at
    _assert_s25_call_separation(context)
    pip.playbook.refresh_from_db()
    change = pip.changes.get()
    assert pip.decided_at is None
    assert (change.admin_decision, change.admin_note) == (PipChange.ADMIN_UNSET, "")
    assert pip.playbook.version == Decimal("2.0")
    assert (
        tuple(pip.playbook.versions.order_by("pk").values_list())
        == context.s25_versions
    )
    assert not pip.playbook_versions.exists()
    assert not Activity.objects.filter(
        workflow__playbook_id=pip.playbook_id, name=change.name
    ).exists()


def _s25_post(
    context: Context,
    route: str,
    destination: str,
    *,
    data: dict[str, str] | None = None,
    correlation: str = "",
) -> None:
    """Check redirects and run only the callbacks registered by the real POST.

    :param context: Authenticated Django acceptance client and PIP.
    :param route: Existing POST route. Example: pip_revert_to_draft.
    :param destination: Expected redirect route. Example: pip_detail.
    :param data: Optional draft edit parameters.
    :param correlation: Optional submission request ID. Example: cedar-summary-initial-at.
    :return: None when the HTTP response and registered callback count match.
    :raises AssertionError: If the redirect, acting user or callback count differs.
    """
    pip = context.s25_pip
    ids = {"pk": pip.pk}
    headers = {"X-Request-ID": correlation} if correlation else {}
    # Behave's TestCase rolls back its outer transaction at scenario teardown.
    with context.test.captureOnCommitCallbacks(execute=True) as callbacks:
        response = context.client.post(
            reverse(route, kwargs=ids), data=data, headers=headers
        )
    assert response.status_code == 302 and response.url == reverse(
        destination, kwargs=ids
    )
    assert response.wsgi_request.user == pip.created_by
    expected_callbacks = 1 if correlation else 0
    assert len(callbacks) == expected_callbacks


def _s25_submit(
    context: Context, correlation: str, summary: LLMResponse, assessment: LLMResponse
) -> tuple[ExpertProfile, AgentInteraction]:
    """Verify the real submission, resulting assessment and stored summary.

    :param context: Authenticated acceptance client with a prepared draft.
    :param correlation: Current submission request ID.
    :param summary: Expected public model response.
    :param assessment: Expected private Galdr model response.
    :return: Persisted profile and matching refresh interaction.
    :raises AssertionError: If the real callback did not persist both results.
    """
    assert isinstance(summary, LLMResponse) and isinstance(assessment, LLMResponse)
    _s25_post(context, "pip_submit_review", "pip_detail", correlation=correlation)
    pip = context.s25_pip
    pip.refresh_from_db()
    change = pip.changes.get()
    (verdict,) = json.loads(assessment.content)["change_assessments"]
    assert pip.status == pip.STATUS_REVIEWED and pip.galdr_holistic_assessment
    assert (change.pk, change.galdr_recommendation, change.galdr_reasoning) == (
        verdict["change_id"],
        verdict["recommendation"],
        verdict["reasoning"],
    )
    profile = ExpertProfile.objects.get(user_id=pip.created_by_id)
    interaction = AgentInteraction.objects.get(pip=pip, correlation_id=correlation)
    assert profile.contribution_summary == summary.content
    assert profile.summary_status == ExpertProfile.SummaryStatus.SUCCESS
    assert profile.last_summary_correlation_id == correlation
    assert interaction.subject_id == pip.created_by_id
    assert interaction.workflow_id == "contribution_summary"
    assert interaction.outcome == AgentInteraction.Outcome.SUCCESS
    assert pip.submitted_at <= interaction.created_at <= pip.reviewed_at
    return profile, interaction


def _assert_s25_call_separation(context: Context) -> None:
    """Check public evidence and the private assessment of each draft revision.

    :param context: Completed lifecycle with four requests and two saved profiles.
    :return: None when both public streams exclude unpublished proposal content.
    :raises AssertionError: If a request is missing, misclassified or leaks private prose.
    """
    first_public, first_assessment, second_public, second_assessment = (
        context.s25_llm.calls
    )
    first_profile, _ = context.s25_first
    second_profile, _ = context.s25_second
    pip = context.s25_pip
    unpublished = (pip.title, SUMMARY_PIP_BODY, pip.summary, pip.changes.get().content)
    for call, profile in (
        (first_public, first_profile),
        (second_public, second_profile),
    ):
        (message,) = call.messages
        assert "Identity: You are the public contribution summarizer." in call.system
        assert "Keyboard Navigation Audit" in message.content
        public_text = (
            f"{call.system}\n{message.content}\n{profile.contribution_summary}"
        )
        assert all(value and value not in public_text for value in unpublished)
    for private_call, body in (
        (first_assessment, SUMMARY_PIP_BODY),
        (second_assessment, _S25_REVISED_BODY),
    ):
        assert private_call.system == HOLISTIC_SYSTEM_PROMPT
        assert pip.title in private_call.messages[0].content
        assert body in private_call.messages[0].content


@given("Mike has no stored contribution summary")
def mike_has_no_stored_contribution_summary(context: Context) -> None:
    """Verify the shared baseline normalized Mike's null prose to empty storage.

    :param context: Shared Cedar AT context. Example: context.cedar_dataset.
    :return: None. Example: None with persisted public_summary == "".
    :raises AssertionError: If Mike is absent or stored prose is nonempty.
    """
    raise NotImplementedError()


@when("Elena opens the Development leaderboard")
def elena_opens_development_leaderboard(context: Context) -> None:
    """Use common Elena authentication and a real production Django GET.

    :param context: Shared AT context. Example: context.client.
    :return: None. Example: None with response for /experts/?category=development.
    :raises AssertionError: If the request does not return the actual leaderboard.
    """
    raise NotImplementedError()


@then('Mike\'s hint is "{expected}" from live released-playbook and GUI-copy counts')
def mike_hint_matches_live_counts(context: Context, expected: str) -> None:
    """Compare the real card hint and independently persisted qualifying rows.

    :param context: AT response and shared Cedar context. Example: context.response.
    :param expected: Exact hint. Example: "2 released playbooks · 47 copies".
    :return: None. Example: None after exact rendered and row-count assertions.
    :raises AssertionError: If hint, qualifying counts or 47/470 distinction fails.
    """
    raise NotImplementedError()


@then("no public-summary paragraph is fabricated")
def no_public_summary_paragraph_is_fabricated(context: Context) -> None:
    """Inspect real public response and unchanged empty profile storage.

    :param context: Shared response context. Example: Mike's rendered card.
    :return: None. Example: None with no summary paragraph and empty storage.
    :raises AssertionError: If prose is rendered or persisted without a summary.
    """
    raise NotImplementedError()


@given("Maria has a stored successful contribution summary")
def s29_given_successful_summary(context: Context) -> None:
    """Prepare the real Cedar draft and exact nine-sentence successful record.

    :param context: Isolated acceptance context with shared CedarDataset.
    :return: None; retain original text/time/ledger identities in context.
    :raises ValueError: If baseline or normal draft preparation is invalid.
    """
    raise NotImplementedError()


@when("its next generation attempt fails")
def s29_when_generation_fails(context: Context) -> None:
    """Submit normally with summary error followed by valid assessment.

    :param context: Real draft and ScriptedLLM-only model seam.
    :return: None; retain actual submission result and interaction.
    :raises AssertionError: If normal submission does not execute two calls.
    """
    raise NotImplementedError()


@then("the last good paragraph is retained")
def s29_then_last_good_retained(context: Context) -> None:
    """Compare exact stored text/time and failed safe refresh metadata.

    :param context: Completed actual submission context.
    :return: None when text/timestamp persist and failure metadata is correct.
    :raises AssertionError: If paragraph, timestamp or metadata differs.
    """
    raise NotImplementedError()


@then("the PIP follows its existing failure/recovery behavior")
def s29_then_existing_lifecycle(context: Context) -> None:
    """Verify valid assessment continues to Reviewed without applying changes.

    :param context: Actual proposal, calls and failure interaction.
    :return: None when summary failure leaves assessment policy unchanged.
    :raises AssertionError: If processing skips assessment or changes decisions.
    """
    raise NotImplementedError()


@then("no Karma is awarded for summary generation")
def s29_then_no_summary_award(context: Context) -> None:
    """Verify Maria remains at 8200 and original ledger identities persist.

    :param context: Real Cedar projection and pre-attempt award snapshot.
    :return: None when no award, accepted change or publication was created.
    :raises AssertionError: If any numerical or publication effect occurs.
    """
    raise NotImplementedError()
