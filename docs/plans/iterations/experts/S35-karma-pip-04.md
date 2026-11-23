# S35: KARMA-PIP-04 Do not award draft, submitted or rejected-only proposals

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S35
acceptance_id: KARMA-PIP-04
feature_file_path: docs/features/act-18-experts/karma-accrual.feature
feature_line: 64
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S32
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 95f7481c3f865db3b86bdca9801e972c1ba9d1cbfdd5a00351f350ce8e321328
```

### A — Context map


| Verified source | Implementation implication |
|---|---|
| `methodology/models/process_improvement_proposal.py:17–33` | Five relevant stored statuses are `draft`, `submitted`, **`processing_galdr`**, `reviewed`, `rejected`. |
| `methodology/services/pip_admin_service.py:24–114,132–147` | Finalization requires staff and reviewed status; content/version application is conditional on accepted changes; all-reject sets rejected and retains postcommit notification. |
| `methodology/services/pip_service.py:599–625,749–793` | Normal creation produces draft; submission moves directly to processing and schedules Galdr. Submitted is a retry state, not an intermediate state to invent. |
| `tests/integration/test_pip_admin_review_view.py:254–274` | Existing real administrator POST proves all-reject status and unchanged version; lacks Karma and complete content/ledger assertions. |
| `test-data/experts/cedar-rfp-01.json:183–193,316–319,990–1013` | Maria starts at 8,200, Design 7,200, Development 1,000; target 6106 starts at 2.0; historical accepted points must remain intact. |

Also inspected replay AGENTS, CLAUDE, orient roster, current SAO delta, live guidance/rules, ownership notes and S32 report. Existing Karma modules are planned interfaces, not verified runtime behavior.

### B — Do not do


- No production edits, new award writer, migration, provider adapter, lifecycle expansion or permission changes.
- Do not assert the ledger is empty: Cedar contains historical awards.
- Do not manufacture `processing`; use `STATUS_PROCESSING_GALDR`.
- Do not confuse Galdr recommendations or saved administrator choices with completed eligible acceptance.
- Do not suppress normal rejection status/timestamp/decision email while checking absence of award/content/version effects.
- Do not reproduce S23 submission/summary-generation proofs or claim Galdr orchestration from ORM fixtures.
- Do not recreate S32 total/category bindings, S03 background, Cedar importer or logging implementation.
- Do not add a browser task: this contract certifies domain eligibility and existing HTTP finalization.

### C — Applicable architecture


SAO headings:

- **Experts & Karma delivery architecture — planned delta**
- **Awards, projections and transaction boundaries**
- **Web delivery and notification reuse**
- **Test strategy for this delta**
- **Version Management**

SAO `3836–3861` explicitly makes rejection/submission worth zero and preserves the existing version owner. S03 supplies historical ledger/projections; S32 supplies terminal eligibility and finalization wiring.

### D — Tests and assertions


New suite: `tests/integration/test_experts_karma_nonaccepted.py`.

| Test | Exact proof |
|---|---|
| `test_nonaccepted_pip_log_story_reject[status]` — five cases | Independently restore Cedar; create a real draft/change, then establish the explicitly documented status boundary fixture. Invoke S32 `KarmaService.award_accepted_changes`. Assert returned `()`, unchanged complete ledger fingerprint, Maria 8,200/Design 7,200/Development 1,000, unchanged target content/version/history, and safe eligibility-skip logs. |
| `test_finalize_pip_with_rejected_only_preserves_karma_content_and_version` | Start from explicit reviewed fixture. Authenticated existing staff Mike POSTs `action=finalize` with each `decision_<pk>=REJECT`; assert 302, persisted rejected status and decision timestamp, every decision REJECT, unchanged content/version 2.0/history and complete ledger fingerprint, Maria 8,200 and all other recipients unchanged. Execute existing on-commit callback and assert one normal rejection email to Maria through locmem. |
| `test_rejected_finalization_log_story_reject` | Same real rejection path; assert S32 eligibility-skip entry/branch/exit logs and zero outcomes through `assert_log_story`; no proposal body, email address or credentials in records. |

**Expected positive count:** seven pytest cases, including five independently parameterized status cases. One named Behave scenario executes all five independently restored status cases and the real rejection finalization. Zero/skipped/undefined selected cases do not pass.

Fixture boundary:

- Draft/change creation uses existing `PIPService` methods with real Cedar workflow references.
- Submitted, processing and reviewed rows are **explicit ORM eligibility fixtures**, with consistent timestamps.
- Reviewed may have Galdr ACCEPT plus a saved ADMIN_ACCEPT choice: terminal eligibility must still block awarding before finalization.
- Rejected is produced by real reviewed→all-reject finalization; never assign rejected directly to claim that path.
- This does not claim submission/Galdr lifecycle proof. If that scope changes, depend on S23 and use its ScriptedLLM seam; legacy FakeLLM is prohibited.

Checkpoint: `make test-experts-s35`.

Required log gate:
`pytest tests/integration/test_experts_karma_nonaccepted.py -k log_story -x`.

### E — Log story


S32 owns all production emission. S35 adds assertions only.

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `KarmaService.award_accepted_changes` | entry | Each direct call or rejected-finalization hook | `entry`, `pip_id=`, `correlation_id=` |
| `KarmaService.award_accepted_changes` | branch | Persisted proposal is ineligible | `branch`, `pip_id=`, `reason=` identifying nonterminal/rejected eligibility |
| `KarmaService.award_accepted_changes` | exit | Ineligible return | `exit`, `pip_id=`, `created_count=0`, `existing_count=0` |

Use `tests/support/log_story.py:9–37`. No new logging framework or invented committed-transaction message. Reconcile reason vocabulary with S32 before application.

### F — MCP tools


Not applicable: no tools, facade changes, authorization forwarding or registration changes. Existing staff finalization/service boundaries only.

### G — Agent proofs


Not applicable: explicit persisted-state fixtures and administrator rejection exercise deterministic domain policy. No SAO §17 PRF is added or changed. S23 retains real submission/assessment orchestration ownership.

### H — Mockup graduation


Not applicable: no UI/template/CSS changes. Django-client POST certifies existing administrator finalization; BPE-03 and BPE-05 are omitted.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/karma-accrual.feature:64`; 1 expanded case(s), primary layer `at`. Dependencies: S32. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-PIP-04
  nodes:
  - id: N1-state-eligibility
    title: Certify all five persisted nonaccepted states
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_karma_nonaccepted.py
    - tests/support/experts_data.py
    tests:
    - test_nonaccepted_pip_log_story_reject
    log_story_rows:
    - KarmaService.award_accepted_changes:entry
    - KarmaService.award_accepted_changes:branch
    - KarmaService.award_accepted_changes:exit
    gate:
      command: pytest tests/integration/test_experts_karma_nonaccepted.py -k nonaccepted_pip -x
      log_story_command: pytest tests/integration/test_experts_karma_nonaccepted.py -k nonaccepted_pip_log_story
        -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-docstring-format
  - id: N2-rejected-finalization
    title: Certify actual rejection without content or award effects
    bpe: BPE-02
    depends_on:
    - N1-state-eligibility
    footprint:
    - tests/integration/test_experts_karma_nonaccepted.py
    tests:
    - test_finalize_pip_with_rejected_only_preserves_karma_content_and_version
    - test_rejected_finalization_log_story_reject
    log_story_rows:
    - KarmaService.award_accepted_changes:entry
    - KarmaService.award_accepted_changes:branch
    - KarmaService.award_accepted_changes:exit
    gate:
      command: pytest tests/integration/test_experts_karma_nonaccepted.py -x
      log_story_command: pytest tests/integration/test_experts_karma_nonaccepted.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-small-increments
  - id: N3-living-at
    title: Bind the exact nonaccepted contract
    bpe: BPE-04
    depends_on:
    - N2-rejected-finalization
    footprint:
    - docs/features/steps/experts_karma_pip_steps.py
    gate:
      command: make test-experts-s35-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-docstring-format
  - id: N4-definition-of-done
    title: Require behavior logs and named AT together
    bpe: BPE-06
    depends_on:
    - N3-living-at
    footprint: []
    gate:
      command: make test-experts-s35
      log_story_command: pytest tests/integration/test_experts_karma_nonaccepted.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-github-issues
  scenario_dependencies:
  - S32
```

## Lessons Learned

After PIN-04 handoff and PIN-05 GO: docs-only handoff `Refs #N`; N1 certification plus log proofs; N2 real rejection plus log proof; N3 AT; N4 conjunctive final verification `Closes #N`. Each slice requires its commit-linked issue update before the next begins.

Lessons Learned:

- “Processing” in prose maps to `processing_galdr`; submission does not normally stop at submitted.
- Explicit ORM fixtures validly isolate eligibility, but cannot establish Galdr lifecycle correctness.
- Rejection legitimately changes proposal state and sends its existing notification while preserving content, version and awards.
- S32 owns runtime fixes. A failing certification requiring production changes must be reconciled with S32 rather than silently expanding S35.

No files changed, tests run, commits made or external mutations performed.

## Structural application evidence

`docs/experts-replay/pin-evidence/S35.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.

## Actual structural footprint

`docs/experts-replay/pin-evidence/S35.json`, `docs/features/steps/experts_karma_pip_steps.py`, `docs/plans/iterations/experts/S35-karma-pip-04.md`, `tests/integration/test_experts_karma_nonaccepted.py`, `tests/support/experts_data.py`

Skeleton: `05299659ecb8f04625ca7a9a09ef16a7d0e25693`; shared reconciliation: `39d598328d438d09723b6eb14574fbf92fab71c9`. Semantic and physical-file dependencies are recorded separately in the iteration manifest. Context-map line ranges record the workers’ inspection baseline; headers and the final scaffold remain authoritative.
