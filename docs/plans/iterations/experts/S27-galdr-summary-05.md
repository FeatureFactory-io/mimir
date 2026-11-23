# S27: GALDR-SUMMARY-05 Exclude private data and mutable scores from generated prose

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S27
acceptance_id: GALDR-SUMMARY-05
feature_file_path: docs/features/act-18-experts/galdr-contribution-summary.feature
feature_line: 29
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- b1ad7a2fc13d4e3cb131f796863978a0f950ae348218c0e500ab16def37bb415
```

## A — Context Map


| File | Verified lines | Why it governs |
|---|---:|---|
| `docs/features/act-18-experts/galdr-contribution-summary.feature` | 35–40 | Exact request-assembly privacy contract. |
| `docs/architecture/SAO.md` | 3916–3983 | T-00 completion, layered prompts, visibility, bounds, trace and PRF-EXPERTS-03. |
| `methodology/models/playbook.py` | 49–60 | Actual visibility/status/author fields; public evidence requires both `public` and `released`. |
| `methodology/services/pip_apply_changes_service.py` | 757–793 | Committed PIP publication creates a `PlaybookVersion` receipt linked to its PIP. |
| `test-data/experts/cedar-rfp-01.json` | 114–138 | Maria’s legitimate public facts and distinct private title/PIP/token/email sentinels. |

Also inspected actual `PIPAdminService.finalize_pip`, PIP/change/version models, Galdr scheduling/prompts, integration tests, port and proof-helper bodies, Act18 journey, full Cedar JSON, catalogs and replay instructions.

Existing working Galdr prompt builders are unsuitable for this boundary: they describe assessment context and may contain proposed changes. Preserve them.

## B — Do-Not-Do List


- Do not treat submission, Galdr recommendation, an administrator flag alone, or a public target as publication.
- Do not serialize `PIP.title`, `summary`, `content`, Galdr reasoning, administrator notes or version audit narratives.
- Do not use owner/staff access as the public-evidence filter.
- Do not include account emails, credentials, ledger values, mutable aggregate counts or category point subtotals.
- Do not query token tables or pass whole user/model dictionaries to the prompt.
- Do not add tools, ToolExecutor, planner, queue, broker, vector storage or another provider seam.
- Do not persist summaries, awards or AgentInteraction rows here.
- Do not replace existing working lifecycle/assessment bodies with skeletons.
- Do not claim deterministic ScriptedLLM proofs establish live-provider quality.

## C — Applicable SAO Sections and Design


Applicable headings:

1. **Experts & Karma delivery architecture — planned delta**
2. **Awards, projections and transaction boundaries**
3. **Test strategy for this delta**
4. **17. AI Agent Architecture — Experts contribution summary**
5. **Components, pattern and serving decisions**
6. **Capability selection and dependency wiring**
7. **Privacy, bounds and failure policy**
8. **Observability and proof gates**

S27 owns four collaborators:

- `PublicContributionEvidenceService.collect(subject_id)` produces an immutable, deterministic snapshot of public facts.
- `build_summary_prompt(evidence)` builds foundation safety, summarizer identity and explicitly delimited evidence.
- `validate_summary_response(response, evidence)` accepts bounded plain prose or raises a sanitized validation error.
- `PublicContributionSummaryBoundary.complete(...)` performs the real read-only collect → prompt → single injected model call → validation path and returns summary, normalized response and immutable body-free trace.

The narrow completion boundary is needed for an independently genuine PRF-EXPERTS-03. S23 delegates its completion to this collaborator and retains scheduling, provider composition, summary persistence, AgentInteraction and `domain_write`. There is no duplicate model path.

Evidence rules:

- Include authored playbooks only while currently public and released.
- Include contribution attribution only for accepted changes of terminal accepted/partially accepted PIPs with a matching PIP-source version receipt on the same currently public released playbook, at or below its current version.
- Include only the accepted rows of partial decisions.
- Read descriptive details from current public entity rows. Never use proposal payloads as public descriptions.
- Existing ADD application does not persist the created entity ID on `PipChange`. Resolve a unique matching current entity within the same playbook; omit ambiguous/unresolvable detail. A generic published operation/entity attribution can remain.
- DROP/LINK/UNLINK may contribute a safe generic published attribution; do not recover deleted names or serialize proposed relationship rationale.
- Serialize only explicit immutable fact fields. Scrub emails and recognizable credential material even when embedded in an otherwise public text field.
- Bound complete serialized evidence to 24,000 characters. Reject oversize input rather than silently slicing facts. No provider call follows a rejected snapshot.
- Request at most 1,024 output tokens. Reject empty, truncated, malformed, marked-up, over-14-sentence or sensitive/aggregate-score output.

S03 supplies the actual Cedar ORM baseline and historical publication receipts. The evidence query itself uses existing models; it has no ledger/schema dependency.

## D — Tests to Create


All listed tests begin as typed, documented raising stubs.

| Location / test | Required assertion after GO |
|---|---|
| `tests/integration/test_experts_public_evidence.py::test_collect_with_cedar_privacy_variant_returns_only_published_public_facts` | Real Cedar DB retains Accessibility Audit Playbook, Keyboard Navigation Audit and published Development contributions; excludes all private/unpublished sentinels and ledger/account fields. |
| `…::test_collect_with_partial_or_unpublished_decisions_excludes_ineligible_changes` | Reject rows, accepted flags without publication receipt, future receipts, private/draft/disabled targets and nonterminal proposals contribute nothing. |
| `…::test_collect_with_invalid_subject_rejects_before_model_call` | Reject bool/nonpositive/missing subject IDs without a provider turn. |
| `…::test_build_summary_prompt_with_public_evidence_preserves_layers_and_bounds` | Foundation/identity/data layers exist; evidence remains data; no scores/counts; serialized bounds 24,000/24,001 are exercised. |
| `…::test_validate_summary_response_with_boundary_or_unsafe_output_enforces_contract` | Fourteen sentences accepted; fifteen rejected; empty/markup/truncation/email/credential/score/count outputs rejected. |
| `…::test_public_evidence_log_story_happy` | `assert_log_story` proves happy beats and no sensitive bodies. |
| `…::test_public_evidence_log_story_reject` | Rejection has safe reason/correlation context and no private fields. |
| `tests/integration/test_experts_summary_proofs.py::test_s27_summary_agent_story_happy` | PRF-EXPERTS-03: real DB/services/boundary and ScriptedLLM; captured request excludes sentinels **before** the call, retains public facts, uses one call, returns valid prose and authentic production trace. |
| `…::test_s27_summary_agent_story_reject` | Unsafe scripted output produces typed boundary error with partial production trace; no successful result or domain write. |
| `…::test_s27_summary_with_exhausted_script_fails_loudly` | Exhaustion is an explicit failure, never fallback prose or successful trace. |

The PRF tests must also assert: unchanged database before/after the read-only boundary, no tools, no award, no profile write, no AgentInteraction write, safe trace content, and 1,024-token request limit.

Required pytest gates:

```sh
pytest tests/integration/test_experts_public_evidence.py tests/integration/test_experts_summary_proofs.py -k 'public_evidence or s27_summary' -x
```

```sh
pytest tests/integration/test_experts_public_evidence.py -k log_story -x
```

```sh
pytest tests/integration/test_experts_summary_proofs.py -m agent_proof -k s27_summary -x
```

Living-spec gate, after S03 baseline/background bindings exist:

```sh
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance python manage.py behave --simple docs/features/act-18-experts/galdr-contribution-summary.feature --name 'GALDR-SUMMARY-05'
```

Remove `@wip` only when that exact contract executes against real behavior. Zero collection/skips cannot certify delivery. PIN raising checkpoints establish structure only.

## E — Log Story Script


All rows are INFO, captured with `caplog` and proved with `assert_log_story`. Log identifiers, lengths and safe reason codes; never prompt/response bodies or raw provider exception messages.

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `PublicContributionSummaryBoundary.complete` | entry | Invocation | `subject_id=`, `correlation_id=` |
| `PublicContributionEvidenceService.collect` | validation | Subject accepted | `subject_id=`, `scope=public_released` |
| `PublicContributionEvidenceService.collect` | processing | Snapshot assembled | `subject_id=`, `fact_count=`, `evidence_chars=` |
| `build_summary_prompt` | config | Layers prepared | `layers=foundation,identity,evidence`, `max_tokens=1024` |
| `PublicContributionSummaryBoundary.complete` | processing | Before provider invocation | `correlation_id=`, `model=`, `tools=none` |
| `validate_summary_response` | validation | Output accepted | `sentence_count=`, `status=accepted` |
| `PublicContributionSummaryBoundary.complete` | exit | Valid completion | `correlation_id=`, `outcome=success` |
| `PublicContributionSummaryBoundary.complete` | error | Any rejected stage | `correlation_id=`, `reason_code=`, `outcome=failure` |

Tests must assert absence of Maria’s private sentinels, email, unpublished proposal title/content, prompt and response bodies from captured records.

## F — MCP Tools to Expose


Not applicable. S27 adds no MCP endpoint, registration or facade change.

## G — Agent Proofs


| PRF ID | Workflow | Script | Production trace asserted | Adverse |
|---|---|---|---|---|
| PRF-EXPERTS-03 | `contribution_summary` | `tests/fixtures/llm_scripts/PRF-EXPERTS-03/happy.json` | `entry`, `public_evidence`, `llm_call`, `validation`, `exit`; public facts present, excluded sentinels absent before model call, no tools/domain write | Yes: adversarial private/unpublished input rows |
| PRF-EXPERTS-03 | `contribution_summary` | `tests/fixtures/llm_scripts/PRF-EXPERTS-03/reject_unsafe.json` | `entry`, `public_evidence`, `llm_call`, `failure`, `exit`; sanitized validation rejection | Yes |

Use existing `ScriptedLLM` exclusively. Inspect the actual request through the boundary’s real `_complete_once` call using a permitted ScriptedLLM request-capture extension if needed; **do not introduce a hand-written fake client**. An alternative is a ScriptedLLM subclass that only records immutable request copies and calls `super().complete`; it must preserve validation, errors and exhaustion unchanged. Prefer extending the existing helper to expose immutable calls, with helper tests, if no capture interface exists at implementation time.

The current ScriptedLLM inspected here does **not** retain requests. Therefore request capture is a real proposed test-support change, explicitly in the footprint below.

Trace returned by the production boundary is converted through `trace_as_agent_story`, then checked with `assert_agent_story`. Tests must not fabricate their own passing trace. S23 adds persisted lifecycle/`domain_write` proofs; S27 does not claim those portions of PRF-EXPERTS-01/02 or PRF-OBS-01.

## H — Mockup Graduation


Not applicable: this scenario changes no template or browser interaction. Existing production summary presenters receive the same validated stored string through S23.

Public-response/browser privacy certification remains covered by S20 and the combined feature journey. Any relevant Playwright gate must clear global E2E exclusion:

```sh
pytest -o addopts= tests/e2e/<consolidated-experts-test-file>.py -k privacy -x
```

That path is intentionally not a fictitious S27 checkpoint; the owning browser worker supplies the actual collected test.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/galdr-contribution-summary.feature:29`; 1 expanded case(s), primary layer `at`. Dependencies: S03. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: GALDR-SUMMARY-05
  nodes:
  - id: S27-N1-public-evidence
    title: Query immutable published public facts
    bpe: BPE-02
    depends_on: []
    footprint:
    - methodology/services/public_contribution_evidence.py
    - tests/integration/test_experts_public_evidence.py
    - tests/support/experts_data.py
    tests:
    - test_collect_with_cedar_privacy_variant_returns_only_published_public_facts
    - test_collect_with_partial_or_unpublished_decisions_excludes_ineligible_changes
    - test_collect_with_invalid_subject_rejects_before_model_call
    - test_public_evidence_log_story_happy
    - test_public_evidence_log_story_reject
    log_story_rows:
    - PublicContributionEvidenceService.collect:validation
    - PublicContributionEvidenceService.collect:processing
    gate:
      command: pytest tests/integration/test_experts_public_evidence.py -k 'collect or log_story' -x
      log_story_command: pytest tests/integration/test_experts_public_evidence.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-write-concise-methods
  - id: S27-N2-prompt-validator
    title: Layered bounded prompt and output validation
    bpe: BPE-02
    depends_on:
    - S27-N1-public-evidence
    footprint:
    - methodology/services/contribution_summary_prompts.py
    - tests/integration/test_experts_public_evidence.py
    tests:
    - test_build_summary_prompt_with_public_evidence_preserves_layers_and_bounds
    - test_validate_summary_response_with_boundary_or_unsafe_output_enforces_contract
    log_story_rows:
    - build_summary_prompt:config
    - validate_summary_response:validation
    gate:
      command: pytest tests/integration/test_experts_public_evidence.py -k 'prompt or response' -x
      log_story_command: pytest tests/integration/test_experts_public_evidence.py tests/integration/test_experts_summary_proofs.py
        -k "s27 and log_story" -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-write-concise-methods
  - id: S27-N3-read-only-boundary
    title: Prove real completion boundary with ScriptedLLM
    bpe: BPE-02
    depends_on:
    - S27-N2-prompt-validator
    footprint:
    - methodology/services/contribution_summary_boundary.py
    - tests/fixtures/llm_scripts/PRF-EXPERTS-03/happy.json
    - tests/fixtures/llm_scripts/PRF-EXPERTS-03/reject_unsafe.json
    - tests/integration/test_experts_summary_proofs.py
    - tests/support/scripted_llm.py
    - tests/unit/test_agent_test_support.py
    tests:
    - test_scripted_llm_with_recorded_call_preserves_request_and_exhaustion
    - test_s27_summary_agent_story_happy
    - test_s27_summary_agent_story_reject
    - test_s27_summary_with_exhausted_script_fails_loudly
    log_story_rows:
    - PublicContributionSummaryBoundary.complete:entry
    - PublicContributionSummaryBoundary.complete:processing
    - PublicContributionSummaryBoundary.complete:exit
    - PublicContributionSummaryBoundary.complete:error
    gate:
      command: pytest tests/unit/test_agent_test_support.py tests/integration/test_experts_summary_proofs.py -k
        'recorded_call or s27_summary' -x
      agent_proof_command: pytest tests/integration/test_experts_summary_proofs.py -m agent_proof -k s27_summary
        -x
      log_story_command: pytest tests/integration/test_experts_public_evidence.py tests/integration/test_experts_summary_proofs.py
        -k "s27 and log_story" -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-agent-story
      - do-assert-log-story
  - id: S27-N4-acceptance
    title: Bind exact request-assembly privacy contract
    bpe: BPE-04
    depends_on:
    - S27-N3-read-only-boundary
    footprint:
    - docs/features/steps/experts_summary_steps.py
    gate:
      command: make test-experts-s27-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
    notes: 'Exact Behave scenario must also execute using acceptance settings. Reuse S03 Cedar/background bindings.
      No UI graduation belongs here.

      '
  - id: S27-N5-dod
    title: Certify privacy, log and agent gates together
    bpe: BPE-06
    depends_on:
    - S27-N4-acceptance
    footprint: []
    gate:
      command: make test-experts-s27
      log_story_command: pytest tests/integration/test_experts_public_evidence.py -k log_story -x
      agent_proof_command: pytest tests/integration/test_experts_summary_proofs.py -m agent_proof -k s27_summary
        -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-assert-log-story
      - do-assert-agent-story
  scenario_dependencies:
  - S03
```

## Lessons Learned

1. A public target does not make proposal text public; evidence must follow committed publication.
2. Existing publication receipts avoid adding a new schema, but the query must join the same playbook and honor partial decisions.
3. ADD rows lack a persistent created-entity reference. Current scoped resolution must fail closed on ambiguity.
4. ScriptedLLM currently lacks request capture. Privacy-before-call proof requires explicit capture while preserving its finite-queue semantics.
5. A production body-free boundary trace makes the independent PRF genuine; lifecycle persistence remains S23’s responsibility.
6. Cedar includes numerical language in its historical display fixture. The generated prompt must omit aggregate numerical contribution counts even when that canned display paragraph mentions them.
7. No implementation, test assertion, provider call, file write or commit was performed by this worker.
