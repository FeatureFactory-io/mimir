# S23: GALDR-SUMMARY-01 Refresh on submission without awarding acceptance points

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S23
acceptance_id: GALDR-SUMMARY-01
feature_file_path: docs/features/act-18-experts/galdr-contribution-summary.feature
feature_line: 8
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
- S27
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- a90598a10c13c88296b27963b83a43890227977734f811ef9de14513a4adfca2
- fcbb7fe459e18074b28e076c910d4473cd6cf1e2ab21ea669857f837f3e2fd12
```

## A — Context map


All paths are relative to `/Users/denispetelin/GitHub/mimir-experts-replay`.

| File | Verified lines | Why read it |
|---|---:|---|
| `methodology/services/pip_service.py` | 750–793 | Existing submitter/status/structural checks, processing transition, eager execution and post-commit scheduling. Preserve them. |
| `methodology/services/galdr_engine.py` | 100–145 | Existing assessment-mode selection and real per-change assessment path. The summary collaborator must remain separate. |
| `methodology/llm/base.py` | 8–53 | Existing immutable messages/responses and `BaseLLM.complete` protocol; production adapter must implement this boundary. |
| `tests/support/scripted_llm.py` | 11–59 | Existing finite, ordered provider seam raises on exhaustion. It currently does not expose requests. |
| `docs/architecture/SAO.md` | 3916–3989 | Governing T-00 assembly, selected CAPs, public-data boundaries, bounds, trace and PRF contracts. |

Additional inspected real implementations: Galdr holistic parsing/persistence and retry handlers; `PIPService` permission guards and lifecycle; `Playbook.visibility/status`; `PlaybookVersion.pip`; `assert_agent_story`; `assert_log_story`; existing Galdr and PIP lifecycle integration-test bodies.

The existing `get_galdr_client()` selects `StubGaldrClient` when Anthropic is disabled (`galdr_client.py:188–198`). That legacy stub can support existing regression tests, but cannot establish the new “ScriptedLLM is the sole provider seam” proof. For the new integration proofs, explicitly inject one `ScriptedLLM` through normal submission, Galdr assessment and the summary collaborator. Keep all existing parsers, validators, services and persistence real.

## B — Do not do


- Do not add a queue, broker, ToolExecutor, planner, tool registry, blackboard, vector store or conversation loop. SAO selects one no-tools T-00 completion.
- Do not replace working Galdr methods with raising stubs during PIN. Append uncalled helpers; wire them only after GO.
- Do not alter PIP read, submitter, staff or decision permissions.
- Do not pass the submitted PIP title, summary, changes or Galdr assessment prompt into the public summary prompt.
- Do not reuse `build_playbook_context_summary()` indiscriminately: the summary needs S27’s restricted public evidence.
- Do not award Karma on submission, summary success, summary failure or retry; do not call decision/acceptance services.
- Do not alter playbook versions or publish the proposed ADD.
- Do not call the provider under a transaction/row lock.
- Do not clear the previous summary before generating or validating a replacement.
- Do not write an empty/default paragraph on provider failure.
- Do not log or persist prompt/response bodies, unpublished titles, email, credentials or tokens in interaction metadata.
- Do not represent missing usage/rates as zero cost.
- Do not let summary failure bypass existing Galdr assessment or change its recovery policy.
- Do not use mocks for domain services or test providers other than ScriptedLLM in the new integration proofs.
- Do not call a live provider, seed/reset a database, implement tests or execute migrations during this planning activity.

## C — Applicable SAO sections


- **Design Principles → Hybrid MCP Access: Draft CRUD + Released PIP Workflow**
- **Design Principles → Version Management**
- **Experts & Karma delivery architecture — planned delta**
  - **Awards, projections and transaction boundaries**
  - **Web delivery and notification reuse**
  - **Test strategy for this delta**
- **17. AI Agent Architecture — Experts contribution summary**
  - **Components, pattern and serving decisions**
  - **Capability selection and dependency wiring**
  - **Privacy, bounds and failure policy**
  - **Observability and proof gates**

The complete Experts delta and §17 were read. The current Act 18 journey and Cedar EV04/summary policy agree: submit 8,200 → 8,200; acceptance is a later independent action.

## D — Tests to create


Every test below is a documented raising stub during PIN. The assertions described here are the future green contract.

| Exact test | Future assertions |
|---|---|
| `tests/integration/test_experts_summary_submission.py::test_s23_submit_for_review_with_add_activity_refreshes_without_acceptance_award` | Restore real Cedar ORM baseline. Create Maria’s draft and ADD through real `PIPService`; submit normally with eager processing and explicit ScriptedLLM. Summary completion occurs once; exact validated response is stored on Maria’s profile; sentence count ≤14; total remains 8,200; ledger unchanged; ADD not applied; Hana v2.0 unchanged; PIP reviewed with existing assessment semantics. Parametrize both existing Galdr assessment modes. |
| `…::test_s23_submit_for_review_with_invalid_actor_requests_no_summary` | Another non-staff actor cannot submit Maria’s draft; no model request, summary change or award. Existing permission exception remains. |
| `…::test_s23_submit_for_review_with_rollback_does_not_dispatch_processing` | With eager mode off, roll back an outer transaction: on-commit processing never runs; no interaction, summary or ledger change. |
| `…::test_s23_http_submission_with_request_id_uses_normal_lifecycle` | Real authenticated Django-client POST to `reverse("pip_submit_review", kwargs={"pk": pip.pk})`, configured provider seam only. Assert normal redirect, same processing result and request correlation in the persisted interaction. No patched service/view. |
| `…::test_s23_summary_log_story_happy` | `caplog` + `assert_log_story` prove all happy rows in E, with actual IDs/correlation and no body/sentinel leakage. |
| `…::test_s23_summary_log_story_reject` | Explicit provider error; last good summary retained; failure and retained-summary branch logged; assessment still runs; no award. |
| `tests/integration/test_experts_summary_proofs.py::test_s23_submission_agent_story_happy` | `@agent_proof`; real submission, evidence, prompt, validator, profile and trace store. `assert_agent_story` proves PRF-EXPERTS-01; actual ScriptedLLM requests prove the summary request is bounded and uses the real layered prompt. |
| `…::test_s23_submission_agent_story_reject` | `@agent_proof`; explicit ScriptedLLM provider failure preserves last good text; trace contains failure/exit and no domain_write; remaining scripted assessment executes normally. Supports essential PRF-EXPERTS-02 behavior; S29 extends malformed/overlong/exhaustion coverage. |
| `…::test_s23_submission_with_private_sentinels_agent_story_happy` | `@agent_proof`; real private playbook/PIP/token/email/unpublished ADD sentinels. Inspect the actual summary request recorded by ScriptedLLM: all excluded; real public facts retained; no totals/category subtotals/counts. Existing private assessment request may contain the proposal—it is a separate request and must never be treated as public evidence. PRF-EXPERTS-03. |
| `…::test_s23_summary_interaction_agent_story_happy` | `@agent_proof`; persisted trace shares correlation, workflow and subject IDs; normalized supplied input/output usage; nonnegative measured latency; configured-rate cost calculation; missing usage/rates yield null cost. No prompt or response body in trace. PRF-OBS-01. |
| `tests/unit/test_contribution_summary_adapter.py::test_s23_normalize_response_with_text_and_usage_returns_port_response` | Real adapter normalization preserves joined text, configured/returned model, stop reason and optional input/output token counts. |
| `…::test_s23_adapter_with_invalid_request_rejects_before_provider` | Invalid message collection, token bound or temperature raises before SDK call. No live request. |

Behavior checkpoint:

```bash
pytest tests/unit/test_contribution_summary_adapter.py tests/integration/test_experts_summary_submission.py tests/integration/test_experts_summary_proofs.py -k s23 -x
```

Log checkpoint:

```bash
pytest tests/integration/test_experts_summary_submission.py -k 's23 and log_story' -x
```

Agent checkpoint:

```bash
pytest tests/integration/test_experts_summary_proofs.py -m agent_proof -k s23 -x
```

Existing regression gate, in addition to the S23 checkpoint:

```bash
pytest tests/integration/test_pip_lifecycle.py::test_galdr_eager_moves_to_reviewed tests/integration/test_galdr_target_state.py::test_galdr_holistic_accepts_interdependent_changes tests/integration/test_pip_revert_to_draft.py::test_full_galdr_feedback_loop_revert_and_resubmit -x
```

At iteration completion, the existing `make test-agent-experts` runs the full proof file. Missing, skipped or zero-collected proofs are not delivery passes.

## E — Log story script


Default level INFO; use sanitized IDs and reason codes, never exception bodies from the provider.

| ID | Where | Beat | Trigger | Must include |
|---|---|---|---|---|
| E1 | `PIPService._schedule_processing` | entry | Valid committed submission | `pip_id=`, `actor_id=`, `correlation_id=`, `reason=submission` |
| E2 | `ContributionSummaryService.refresh_for_submission` | entry | Processing invokes summary | `subject_id=`, `pip_id=`, `correlation_id=` |
| E3 | Same | config | Assembly selected | `workflow=contribution_summary`, `model=`, `max_tokens=1024`, `tools=none` |
| E4 | Same | validation | Subject and public evidence validated | `visibility=public_released`, `evidence_chars=`, `correlation_id=` |
| E5 | Same | processing | Bounded completion requested | `operation=complete`, `correlation_id=` |
| E6 | Same | validation | Output accepted | `sentence_count=`, `limit=14`, `correlation_id=` |
| E7 | Same | exit | Profile and interaction persisted | `outcome=success`, `summary_updated=true`, `interaction_id=`, `karma_awarded=0` |
| E8 | Same | error | Provider or validation failure | `outcome=failure`, `reason_code=`, `correlation_id=` |
| E9 | Same | branch | Failure recovery | `last_good_retained=true`, `karma_awarded=0`, `correlation_id=` |
| E10 | Same | exit | Failed attempt completes | `summary_updated=false`, `pip_lifecycle=unchanged`, `correlation_id=` |

`test_s23_summary_log_story_happy` covers E1–E7; reject covers E1–E5 and E8–E10. Assertions must include the beat text as well as the fragments: the existing `assert_log_story` helper does not independently enforce its dictionary key.

## F — MCP tools


Not applicable. S23 adds no MCP tool/schema/registration. Existing submit tools reach the same shared lifecycle. No second MCP server or facade business logic is added.

## G — Agent proofs


| PRF ID | Workflow | Script paths | Required trace beats | Adverse |
|---|---|---|---|---|
| PRF-EXPERTS-01 | `contribution_summary` | `tests/fixtures/llm_scripts/PRF-EXPERTS-01/happy.json`, `happy_per_change.json` | `entry` subject/pip/correlation; `public_evidence` public IDs and bounded size; `llm_call` configured model/tools=none/max_tokens=1024; `validation` valid/sentences; `domain_write` profile ID/summary_updated; `exit` success/karma_awarded=0 | No |
| PRF-EXPERTS-02 | Same | `tests/fixtures/llm_scripts/PRF-EXPERTS-02/reject_provider.json` | `entry`, `public_evidence`, `llm_call`, `failure` provider_failed/last_good_retained; `exit` failure/karma_awarded=0; no `domain_write` | Yes |
| PRF-EXPERTS-03 | Same | `tests/fixtures/llm_scripts/PRF-EXPERTS-03/submission_happy.json` | `public_evidence` authorized-only; `llm_call` bounded; `validation`; `domain_write`; also inspect the actual summary request for absent sentinels | Privacy |
| PRF-OBS-01 | Same | `tests/fixtures/llm_scripts/PRF-OBS-01/happy.json`, `unknown_rates.json` | Persisted interaction’s correlation/outcome/usage/latency/cost and ordinary workflow beats | Missing usage/rates |

Script files describe ordered `LLMResponse` or `LLMError` items. For the holistic happy path the queue is:

1. A short valid public paragraph, for example: “Maria Rodriguez maintains Accessibility Audit Playbook. Its published examples cover keyboard focus and form feedback.”
2. Existing holistic-assessment JSON with a complete verdict for the newly created change. The loader resolves the explicitly named `$CHANGE_ID` integer field from the real draft, without template evaluation.

For per-change assessment, item 2 is the existing single-change verdict JSON. For provider rejection, item 1 is `LLMError("scripted_provider_failure")`, followed by a valid real assessment response. Thus only the provider is substituted, and the test distinguishes one summary call from the additional pre-existing assessment call.

No golden task fixture or live-provider rehearsal is introduced by this scenario. Model quality and actual provider cost remain separate post-GO rehearsal evidence.

## H — Mockup graduation


Not applicable: this is processing and storage behavior. No production template or mockup is graduated here. S10/S24 and the public presentation scenarios consume the stored paragraph separately. Browser/manual UAT obligations remain with their owning UI graphs.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/galdr-contribution-summary.feature:8`; 1 expanded case(s), primary layer `at`. Dependencies: S03, S27. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: GALDR-SUMMARY-01
  nodes:
  - id: N1-summary-adapter-trace
    title: Provider port composition and real interaction schema
    bpe: BPE-02
    depends_on: []
    footprint:
    - .env.example
    - methodology/llm/anthropic_adapter.py
    - methodology/migrations/0028_agent_interaction.py
    - methodology/models/__init__.py
    - methodology/models/agent_interaction.py
    - methodology/services/contribution_summary_factory.py
    - mimir.db
    - mimir/settings/base.py
    - tests/unit/test_contribution_summary_adapter.py
    tests:
    - test_s23_normalize_response_with_text_and_usage_returns_port_response
    - test_s23_adapter_with_invalid_request_rejects_before_provider
    gate:
      command: pytest tests/unit/test_contribution_summary_adapter.py -k s23 -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-write-concise-methods
      - do-docstring-format
  - id: N2-summary-lifecycle
    title: Delegate once and preserve normal submission and assessment
    bpe: BPE-02
    depends_on:
    - N1-summary-adapter-trace
    footprint:
    - methodology/pip_views.py
    - methodology/services/contribution_summary_service.py
    - methodology/services/galdr_client.py
    - methodology/services/galdr_engine.py
    - methodology/services/pip_service.py
    - tests/fixtures/llm_scripts/PRF-EXPERTS-01/happy.json
    - tests/fixtures/llm_scripts/PRF-EXPERTS-01/happy_per_change.json
    - tests/fixtures/llm_scripts/PRF-EXPERTS-02/reject_provider.json
    - tests/fixtures/llm_scripts/PRF-EXPERTS-03/submission_happy.json
    - tests/fixtures/llm_scripts/PRF-OBS-01/happy.json
    - tests/fixtures/llm_scripts/PRF-OBS-01/unknown_rates.json
    - tests/integration/test_experts_summary_proofs.py
    - tests/integration/test_experts_summary_submission.py
    - tests/support/experts_summary_data.py
    tests:
    - test_s23_submit_for_review_with_add_activity_refreshes_without_acceptance_award
    - test_s23_submit_for_review_with_invalid_actor_requests_no_summary
    - test_s23_submit_for_review_with_rollback_does_not_dispatch_processing
    - test_s23_summary_log_story_happy
    - test_s23_summary_log_story_reject
    - test_s23_submission_agent_story_happy
    - test_s23_submission_agent_story_reject
    - test_s23_submission_with_private_sentinels_agent_story_happy
    - test_s23_summary_interaction_agent_story_happy
    log_story_rows:
    - E1
    - E2
    - E3
    - E4
    - E5
    - E6
    - E7
    - E8
    - E9
    - E10
    gate:
      command: pytest tests/integration/test_experts_summary_submission.py tests/integration/test_experts_summary_proofs.py
        -k s23 -x
      log_story_command: pytest tests/integration/test_experts_summary_submission.py -k 's23 and log_story' -x
      agent_proof_command: pytest tests/integration/test_experts_summary_proofs.py -m agent_proof -k s23 -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-informative-logging
      - do-assert-log-story
      - do-assert-agent-story
  - id: N3-submission-acceptance
    title: Exact server contract and actual authenticated HTTP submission
    bpe: BPE-04
    depends_on:
    - N2-summary-lifecycle
    footprint:
    - tests/integration/test_experts_summary_submission.py
    tests:
    - test_s23_http_submission_with_request_id_uses_normal_lifecycle
    gate:
      command: make test-experts-s23-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: N4-definition-of-done
    title: Conjunctive behavior, exact AT, regression, log and agent gate
    bpe: BPE-06
    depends_on:
    - N3-submission-acceptance
    footprint: []
    log_story_rows:
    - E1
    - E2
    - E3
    - E4
    - E5
    - E6
    - E7
    - E8
    - E9
    - E10
    gate:
      command: make test-experts-s23
      log_story_command: pytest tests/integration/test_experts_summary_submission.py -k 's23 and log_story' -x
      agent_proof_command: pytest tests/integration/test_experts_summary_proofs.py -m agent_proof -k s23 -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-assert-agent-story
      - do-follow-commit-convention
  scenario_dependencies:
  - S03
  - S27
```

## Lessons Learned

The baseline already has real Galdr lifecycle machinery, while the newer SAO correctly calls its Experts collaborator planned. Treating “Galdr exists” as proof that public summary generation exists would conceal the missing query, privacy and trace work.

The legacy deterministic Galdr stub cannot satisfy the new sole-ScriptedLLM orchestration gate. A small explicit port bridge is necessary; replacing assessment logic would be unnecessary scope expansion.

The shared ScriptedLLM currently cannot prove what was actually sent to the provider. Immutable request capture is a narrowly scoped test-support extension, preferable to patching prompt/domain services.

S03 foundation → S27 public-evidence/prompt/validation → S23 orchestration avoids a dependency cycle with S10’s display behavior. These ownership decisions and the reserved migration filename must be reconciled before skeleton application.

Suggested delivery commits after the separate plan/docs handoff: adapter/schema foundation; lifecycle+behavior+log+agent proofs together; real HTTP acceptance. Use `Refs #N` until the final scenario slice, then `Closes #N`, with corresponding issue updates. PIN-04/05 owns publication and the combined human GO.

## Structural application evidence

`docs/experts-replay/pin-evidence/S23.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.
