# S29: GALDR-SUMMARY-07 Preserve last good summary on provider failure

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S29
acceptance_id: GALDR-SUMMARY-07
feature_file_path: docs/features/act-18-experts/galdr-contribution-summary.feature
feature_line: 43
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S23
- S04
- S10
- S17
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- ca4594a546e58a4fb91b231e35f786262003de922039b445e8c5f5760abe2fc8
```

## A — Context map


Paths below are relative to `/Users/denispetelin/GitHub/mimir-experts-replay`.

| Verified source | Lines | Relevant contract |
|---|---:|---|
| `docs/features/act-18-experts/galdr-contribution-summary.feature` | 49–54 | Retain Maria’s last successful paragraph, preserve existing PIP failure/recovery, award nothing. |
| `methodology/services/pip_service.py` | 750–793 | Normal submission validates, changes status and dispatches existing eager/post-commit processing. |
| `methodology/services/galdr_engine.py` | 65–113, 184–223 | Existing assessment failure returns Processing to Submitted for retry; successful assessment continues to persistence. |
| `test-data/experts/cedar-rfp-01.json` | 114–119, 1040–1056 | Maria’s exact nine-sentence fixture and stable-prose policy. |
| `docs/architecture/SAO.md` | 3964–3977, 3979–4019 | Typed boundary failures, single delegation, privacy, retention, usage/cost and mandatory PRF gates. |

Also read replay `AGENTS.md`, `CLAUDE.md`, the three `/tmp/experts-pin-*` guidance/ownership files, orient S29 mapping, actual CAP-001/CAP-004 helpers, log/agent assertion helpers, acceptance settings/catalog, and delivered S23/S27 raw reports.

Delivered S23 report describes earlier independent orchestration helpers; current SAO and parent convergence take precedence: consume `PublicContributionSummaryBoundary.complete()` once and preserve its authentic partial trace. Likewise, use S27’s canonical `ScriptedLLM.calls`, never the older S23 `requests` proposal.

## B — Do-not-do list


- Do not clear or replace `contribution_summary` before a valid replacement exists.
- Do not update `summary_updated_at` on failure; it records the last successful refresh.
- Do not turn failure into successful canned prose or an empty paragraph.
- Do not let summary failure skip, accept, reject or otherwise decide the PIP.
- Do not introduce automatic retries; exercise the existing explicit Submitted retry lifecycle.
- Do not award Karma, alter accepted changes or publish the submitted ADD.
- Do not create a new provider/factory/scheduler, queue, registry, ToolExecutor or agent loop.
- Do not substitute `StubGaldrClient`, a domain mock or fabricated passing trace.
- Do not record provider exception bodies, model bodies, email or credentials in failure metadata.
- Do not report missing tokens/rates as measured zero usage/cost.
- Do not invent a new UI error panel. Existing summary rendering and S26 fallback remain authoritative.
- Do not claim missing, skipped, zero-selected or PIN raising tests prove delivery.

## C — Governing architecture and ownership


Applicable sections: **Experts & Karma delivery architecture — planned delta**, **Awards, projections and transaction boundaries**, **Test strategy for this delta**, and SAO §17 **Components, pattern and serving decisions**, **Capability selection and dependency wiring**, **Privacy, bounds and failure policy**, **Observability and proof gates**.

Required prerequisite interfaces:

- S03 supplies `CedarDataset`, real historical ledger/projections and `ExpertProfile` fields:
  `contribution_summary`, `summary_updated_at`, `summary_status`,
  `summary_error_code`, `last_summary_correlation_id`.
- S27 supplies immutable `SummaryBoundaryResult`, typed `SummaryBoundaryError(code, trace, response)`, `PublicContributionSummaryBoundary.complete`, `trace_as_agent_story`, and immutable request capture through `.calls`.
- S23 supplies normal PIP provider injection, composition, refresh persistence, `AgentInteraction`, shared script loading and real draft/ADD preparation.

S23’s failure persistence must update failure metadata and write a failed interaction while preserving both last-good fields. This is a prerequisite acceptance condition for the owning implementation, not a new S29 production implementation.

Failure metadata has `summary_status="failure"` and a safe allowlisted error code. Use S27’s canonical codes once reconciled; tests compare exact agreed codes, not raw exception messages. Preserve the actual normalized response when validation fails so supplied usage remains observable without storing its body.

## D — Tests to create


| Exact proposed test | Assertions |
|---|---|
| `tests/integration/test_experts_summary_failure.py::test_s29_submission_with_summary_failure_retains_last_good` | Parameterized provider error, empty prose, 15 sentences, unexpected markup and token-limit truncation. Real Cedar, real draft/ADD and normal eager submission. Exact paragraph and successful timestamp unchanged; failure status/code recorded; one failed summary interaction; Maria stays 8,200; ledger rows unchanged; Hana v2.0 and activities unchanged. |
| `…::test_s29_submission_with_summary_failure_continues_existing_assessment` | Run both existing assessment modes. Queue contains summary failure followed by valid assessment. Two actual `.calls`; first is bounded summary, second is existing assessment; PIP reaches Reviewed and no change is applied/awarded. |
| `…::test_s29_submission_with_assessment_failure_uses_existing_retry` | Queue: summary error, assessment error, valid summary, valid assessment. First submission returns to Submitted under existing policy. Explicit normal retry reaches Reviewed; no new retry mechanism, four calls total, two summary attempts, no award. |
| `…::test_s29_submission_with_missing_last_good_preserves_empty_state` | Empty summary and null successful timestamp remain empty/null; failure metadata recorded. No generated fallback paragraph; numeric projection remains available. S26 owns rendered numeric fallback. |
| `…::test_s29_summary_log_story_reject` | Actual caplog records prove E below; exact safe reason/correlation and retention decision; no provider/body/private sentinel leakage. |
| `tests/integration/test_experts_summary_proofs.py::test_s29_summary_agent_story_reject` | `@agent_proof`; parameterized provider/invalid-output cases through real submission. Assert persisted authentic trace, failed interaction, no successful `domain_write`, no awards and bounded actual summary request. |
| `…::test_s29_summary_interaction_with_failure_preserves_usage_agent_story_reject` | Provider failure: unknown tokens/cost are null. Invalid response with supplied tokens and configured rates: tokens retained and cost calculated despite validation failure. Missing usage/rates: null cost. Nonnegative measured latency and shared correlation. |
| `…::test_s29_summary_with_exhausted_script_fails_loudly` | Exercise real boundary with finite ScriptedLLM exhausted after a preceding real boundary call. Explicit typed failure caused by exhaustion, no successful result/default prose and no boundary DB writes. Do not let lifecycle exception handling disguise a malformed test script as a passing normal-submission proof. |

The failure parameter matrix asserts exact reason codes after parent reconciliation. Fifteen sentences are genuinely fifteen complete sentences, not repeated punctuation. Boundary 14-sentence validation remains S27’s ownership.

For normal-submission adverse cases every fixture provides **two** ordered items: summary failure/invalid response, then valid existing assessment JSON containing the actual change ID. This prevents accidental assessment queue exhaustion from passing as the intended failure.

Backend gates:

```bash
pytest tests/integration/test_experts_summary_failure.py tests/integration/test_experts_summary_proofs.py -k s29 -x
pytest tests/integration/test_experts_summary_failure.py -k s29_summary_log_story_reject -x
pytest tests/integration/test_experts_summary_proofs.py -m agent_proof -k s29 -x
```

The log fixture must explicitly enable affected loggers and propagation, capture INFO, and restore original logger state. `mimir/settings/test.py:86–98` disables existing loggers; `caplog.set_level()` alone is insufficient.

Exact AT gate, overriding inherited feature `@wip` selection deliberately:

```bash
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance python manage.py behave --simple --tags=@experts --name='^GALDR-SUMMARY-07 Preserve last good summary on provider failure$' docs/features/act-18-experts/galdr-contribution-summary.feature
```

Required aggregate gates after all contracts are implemented:

```bash
make test-at-experts
make test-agent-experts
pytest tests/integration/test_pip_lifecycle.py::test_galdr_eager_moves_to_reviewed -x
```

Acceptance requires one actual S29 scenario executed, no undefined/skipped steps. Aggregate Experts AT remains incomplete while other contracts remain WIP.

## E — Log story


These are S23/S27 production beats consumed by S29, not a separate logger implementation.

| Where | Beat | Trigger | Required fragments |
|---|---|---|---|
| `ContributionSummaryService.refresh_for_submission` | entry | Normal processing | `pip_id=`, `subject_id=`, `correlation_id=` |
| `PublicContributionSummaryBoundary.complete` | processing | Model invocation | `model=`, `tools=none`, `correlation_id=` |
| `PublicContributionSummaryBoundary.complete` | error | Provider/output failure | `outcome=failure`, `reason_code=`, `correlation_id=` |
| `ContributionSummaryService.refresh_for_submission` | branch | Retain prior paragraph | `last_good_retained=true`, `karma_awarded=0`, `correlation_id=` |
| Same | exit | Failed attempt persisted | `summary_updated=false`, `outcome=failure`, `interaction_id=`, `pip_lifecycle=unchanged` |

For the no-last-good case assert `last_good_retained=false` and no fabricated prose. Include literal beat fragments in `assert_log_story` requirements: its mapping keys alone do not enforce beat identity.

## F — MCP tools


Not applicable. No new/modified MCP schema, registration, client or transport. Existing submission services retain permissions and normal lifecycle.

## G — Agent proofs


| PRF | Scripts | Assertions |
|---|---|---|
| PRF-EXPERTS-02 | `PRF-EXPERTS-02/s29_provider.json`, `s29_empty.json`, `s29_overlong.json`, `s29_markup.json`, `s29_truncated.json` | Real submission → `entry`, `public_evidence`, `llm_call`, `failure`, `exit`; retained paragraph/timestamp, exact safe reason, no successful `domain_write`, no award. |
| PRF-EXPERTS-02 | `PRF-EXPERTS-02/s29_retry.json` | Existing assessment error returns Submitted; explicit retry succeeds through the same injected queue and normal lifecycle. |
| PRF-EXPERTS-02 | `PRF-EXPERTS-02/s29_exhaustion.json` | One response, then actual boundary exhaustion raises explicitly; never default prose. |
| PRF-OBS-01 | `PRF-OBS-01/s29_invalid_usage.json`, `s29_unknown_usage.json`, `s29_unknown_rates.json` | Persisted failure outcome, real partial trace/correlation, measured latency, supplied tokens and configured-rate estimate or null when unknown. |

ScriptedLLM is the sole model seam. `.calls[0]` captures the summary request; later private assessment requests must not be confused with public summary input. Authenticate traces from production boundary/store; never construct test traces that merely satisfy `assert_agent_story`.

A successful control is covered by S23; S29’s explicit retry also demonstrates recovery to successful storage. Live-provider quality/cost remains separate post-GO rehearsal evidence.

## H — Mockup graduation


Not applicable. No template, interaction or new error presentation is introduced. Last-good rendering belongs to existing S10/S17/S24 contracts; absent prose uses S26’s live numeric fallback.

No S29 browser lifecycle is necessary. Any later owning UI certification must reuse the existing function-scoped browser configuration separately from backend log capture.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/galdr-contribution-summary.feature:43`; 1 expanded case(s), primary layer `at`. Dependencies: S23, S04, S10, S17. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: GALDR-SUMMARY-07
  nodes:
  - id: S29-N1-retention
    title: Certify real submission failure retention and recovery
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/fixtures/llm_scripts/PRF-EXPERTS-02/s29_empty.json
    - tests/fixtures/llm_scripts/PRF-EXPERTS-02/s29_exhaustion.json
    - tests/fixtures/llm_scripts/PRF-EXPERTS-02/s29_markup.json
    - tests/fixtures/llm_scripts/PRF-EXPERTS-02/s29_overlong.json
    - tests/fixtures/llm_scripts/PRF-EXPERTS-02/s29_provider.json
    - tests/fixtures/llm_scripts/PRF-EXPERTS-02/s29_retry.json
    - tests/fixtures/llm_scripts/PRF-EXPERTS-02/s29_truncated.json
    - tests/integration/test_experts_summary_failure.py
    - tests/integration/test_experts_summary_proofs.py
    - tests/support/experts_summary_failure_data.py
    gate:
      command: pytest tests/integration/test_experts_summary_failure.py tests/integration/test_experts_summary_proofs.py
        -k 's29 and not interaction' -x
      log_story_command: pytest tests/integration/test_experts_summary_failure.py -k s29_summary_log_story_reject
        -x
      agent_proof_command: pytest tests/integration/test_experts_summary_proofs.py -m agent_proof -k 's29 and not
        interaction' -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-assert-agent-story
    tests:
    - test_s29_submission_with_summary_failure_retains_last_good
    - test_s29_submission_with_summary_failure_continues_existing_assessment
    - test_s29_submission_with_assessment_failure_uses_existing_retry
    - test_s29_submission_with_missing_last_good_preserves_empty_state
    - test_s29_summary_log_story_reject
    - test_s29_summary_agent_story_reject
    - test_s29_summary_interaction_with_failure_preserves_usage_agent_story_reject
    - test_s29_summary_with_exhausted_script_fails_loudly
  - id: S29-N2-failure-observability
    title: Certify failed interaction usage and unknown cost
    bpe: BPE-02
    depends_on:
    - S29-N1-retention
    footprint:
    - tests/fixtures/llm_scripts/PRF-OBS-01/s29_invalid_usage.json
    - tests/fixtures/llm_scripts/PRF-OBS-01/s29_unknown_rates.json
    - tests/fixtures/llm_scripts/PRF-OBS-01/s29_unknown_usage.json
    - tests/integration/test_experts_summary_proofs.py
    gate:
      command: pytest tests/integration/test_experts_summary_proofs.py -k s29_summary_interaction -x
      agent_proof_command: pytest tests/integration/test_experts_summary_proofs.py -m agent_proof -k s29_summary_interaction
        -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-agent-story
    tests:
    - test_s29_summary_agent_story_reject
    - test_s29_summary_interaction_with_failure_preserves_usage_agent_story_reject
    - test_s29_summary_with_exhausted_script_fails_loudly
  - id: S29-N3-acceptance
    title: Execute the exact living failure contract
    bpe: BPE-04
    depends_on:
    - S29-N2-failure-observability
    footprint:
    - docs/features/steps/experts_summary_steps.py
    gate:
      command: make test-experts-s29-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: S29-N4-dod
    title: Verify retention, lifecycle, logs and agent gates together
    bpe: BPE-06
    depends_on:
    - S29-N3-acceptance
    footprint: []
    gate:
      command: make test-experts-s29
      log_story_command: pytest tests/integration/test_experts_summary_failure.py -k s29_summary_log_story_reject
        -x
      agent_proof_command: pytest tests/integration/test_experts_summary_proofs.py -m agent_proof -k s29 -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-assert-log-story
      - do-assert-agent-story
      - do-github-issues
    notes: Run exact AT and existing lifecycle regression; aggregate make gates require all implemented contracts.
  scenario_dependencies:
  - S23
  - S04
  - S10
  - S17
```

## Lessons Learned

1. Summary failure and assessment failure are separate outcomes. An adverse summary proof needs a valid assessment response to establish that distinction.
2. Retention includes the successful timestamp; checking text alone misses false freshness.
3. Invalid model output may still incur observable usage/cost. Provider transport failure usually leaves these unknown.
4. Disabled Django test loggers require explicit restoration-aware capture.
5. Real partial traces and captured `.calls` prevent orchestration proofs from passing through bypassed collaborators.
6. PIN placeholders and zero-selected WIP runs are structural evidence only; delivery requires actual executed contracts.

## Structural application evidence

`docs/experts-replay/pin-evidence/S29.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.
