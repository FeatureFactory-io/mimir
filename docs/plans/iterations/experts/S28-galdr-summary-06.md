# S28: GALDR-SUMMARY-06 Preserve stable prose when points change

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S28
acceptance_id: GALDR-SUMMARY-06
feature_file_path: docs/features/act-18-experts/galdr-contribution-summary.feature
feature_line: 36
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S23
- S10
- S11
- S12
- S36
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- 122e4260d174417f539fd3149571a51c8072f0d9ad61418675070a11a9ce1730
```

## A — Context map


References are relative to `/Users/denispetelin/GitHub/mimir-experts-replay`.

| Verified file:lines | Implementation relevance |
|---|---|
| `test-data/experts/cedar-rfp-01.json:114-192,686-701,1040-1056` | Exact nine-sentence paragraph; Maria 8200→8205, Mike 12450→12455; Development copy event; live numeric values are independent of prose. |
| `static/js/copy_prompt.js:79-98` | Actual clipboard promise-success boundary. S36 adds its receipt here; S28 exercises that completed wiring. |
| `methodology/services/pip_service.py:750-793` | Real submission validation, processing transition and eager/on-commit scheduling; S23 supplies the optional sole model-port injection. |
| `tests/support/scripted_llm.py:11-59` | Real finite queue explicitly fails on exhaustion. S27’s planned `calls` capture must record attempts before consuming the queue. |
| `docs/architecture/SAO.md:3939-4017` | T-00 assembly, submission-only trigger, stable public facts, live numeric projections and separate trace/log proof obligations. |

Additional inspected implementations: authorized activity loading at `activity_service.py:937-975`; existing profile view at `accounts/views.py:285-318`; real rendered-copy checks at `test_copy_prompt.py:43-65`; browser lifecycle at `tests/e2e/conftest.py:141-168`; existing `assert_agent_story`, `assert_log_story`, pytest configurations and Makefile gates.

## B — Do not do


- Do not implement awards or clipboard receipts again. Consume S36’s real authenticated, CSRF-protected boundary and S30’s atomic ledger writer.
- Do not call the generator to update a numeric score or rebuild unchanged prose.
- Do not prove “no model call” solely from unchanged interaction-row counts: an attempted provider call could fail before persistence.
- Do not replace ScriptedLLM with a fake provider, monkeypatch domain services, fabricate trace beats, stub the clipboard, or suppress queue exhaustion.
- Do not directly insert the tested consumption awards or change totals with ORM updates.
- Do not infer category/source from cached prose or fixture totals. Read actual projections after the event.
- Do not assume an eligible learner becomes a Development leaderboard member: Maria remains primarily Design.
- Do not modify summary text, status, timestamp, error code or last correlation merely because Karma changed.
- Do not claim a receipt POST proves a browser clipboard changed.
- Do not replace existing methods with raising stubs, run migrations, alter seed data, call a live provider or execute tests during PIN.

## C — Applicable architecture


- **Experts & Karma delivery architecture — Awards, projections and transaction boundaries**
- **Web delivery and notification reuse**
- **Test strategy for this delta**
- **17. AI Agent Architecture — Experts contribution summary**
  - Components, pattern and serving decisions
  - Capability selection and dependency wiring
  - Privacy, bounds and failure policy
  - Observability and proof gates
- **IA §11 — Experts replay recipe and responsive coverage contract**
- **User journey — Cross-cutting: FOB-GALDR-CONTRIBUTION-SUMMARY-1**

S03 owns schema, imported historical events, Cedar bindings and live projection. S04 owns cards; S10 owns authenticated profile; S17 owns public detail. S23 owns generation/store/interaction and provider composition. S36 owns actual successful-copy receipts. All must precede S28 certification.

## D — Tests to create


All bodies remain raising stubs during PIN.

| Exact test | Future assertions |
|---|---|
| `tests/integration/test_experts_summary_stability.py::test_s28_copy_receipt_with_stored_summary_updates_only_live_numbers` | Real Cedar baseline, Maria authenticated, real rendered activity 6203 and CSRF-valid S36 receipt. Exactly two awards appear: Maria learning +5, Mike author-consumption +5; Development attribution; totals 8205/12455. Maria’s complete paragraph and refresh metadata remain identical; global and subject interaction snapshots remain identical. |
| `…::test_s28_display_with_completed_copy_reads_live_totals_and_stored_prose` | Real post-event GETs of own profile, Design list and public detail show `8,205`; Development list shows Mike `12,455`. Maria remains Design; category totals are Design 7200/Development 1005; source totals are Released 5000/PIP 1600/Consumption 1200/Learning 405. Stored paragraph is complete in detail/own-profile DOM and retained by the visually clamped card hint. Repeated GETs create no additional awards or interactions. |
| `…::test_s28_copy_log_story_happy` | Capture only the receipt/display window; shared helper proves S36 entry/validation/pair-persistence/exit and S10’s stored-summary projection branch. No contribution-summary generation entry/processing beat appears in that window; logs expose no paragraph or credential bodies. |
| `tests/integration/test_experts_summary_proofs.py::test_s28_points_change_agent_story_happy` | Perform an actual S23 normal submission first using one finite ScriptedLLM as the sole model port for both summary and existing assessment. Assert real successful summary trace using `assert_agent_story`, exact nine-sentence stored paragraph and expected two captured calls. Then exercise S36’s real receipt and all display GETs under the same scoped provider composition. `calls` remains exactly equal, including after an exhausted queue would have recorded an attempted extra call; interaction snapshot and refresh metadata unchanged; totals 8205/12455. |
| `tests/e2e/test_experts_summary_stability.py::test_s28_browser_with_successful_copy_updates_score_and_preserves_paragraph` | Real Maria login, actual activity-6203 Copy Prompt click, real browser `clipboard.readText()` equals the entire `CopyPromptService.build_activity_prompt` result, successful receipt response awaited. Reload own profile/list/detail; numbers update, paragraph remains byte-for-byte, no extra awards or interactions. |

The proof constructs the finite ScriptedLLM from the actual Cedar oracle paragraph plus S23’s real assessment-script response. It reuses S23’s script loader and normal draft setup; no alternative provider implementation or competing fixture loader.

Before the event, record all summary fields, subject/global interaction identities and provider calls. Capture again after the receipt **and after the display GETs**. Finish eager processing before opening this observation window; do not use arbitrary sleeps.

**Backend checkpoint**

```bash
pytest tests/integration/test_experts_summary_stability.py -x
```

**Log checkpoint**

```bash
pytest tests/integration/test_experts_summary_stability.py::test_s28_copy_log_story_happy -x
```

**Agent checkpoint**

```bash
pytest tests/integration/test_experts_summary_proofs.py::test_s28_points_change_agent_story_happy -m agent_proof -x
```

**Exact living-spec checkpoint**

```bash
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance python manage.py behave --simple --tags=@experts --name='^GALDR-SUMMARY-06 Preserve stable prose when points change$' docs/features/act-18-experts/galdr-contribution-summary.feature
```

Explicit `@experts` selection overrides configured WIP exclusion for this named contract. Require one executed/passed scenario, all steps passed, zero undefined/skipped steps.

**Separate browser checkpoint**

```bash
E2E_LIVE_SERVER_SCOPE=function pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_summary_stability.py -x
```

Use existing `page`, `context`, `live_server_url`, `login` and `CEDAR_PASSWORD`. Grant actual clipboard permissions for the live-server origin. Prepare ORM data and expected prompt before browser operations. Backend logging checks remain under normal backend settings.

Aggregate completion additionally requires `make test-at-harness`, `make test-agent-experts` and `make test-at-experts`; the latter cannot certify S28 while WIP exclusion still omits it. Missing, zero-collected or skipped checks are not completion evidence.

## E — Log story


S28 adds certification of existing owner logs, not production logging methods.

| Where | Beat | Trigger | Required fragments |
|---|---|---|---|
| `copy_success_receipt` | entry | Real authenticated receipt | request ID, actor ID, `gui_copy` |
| `copy_success_receipt` | validation | Authorized allowlisted payload | entity `activity`, ID `6203`, action UUID |
| `KarmaService.award_successful_consumption` | processing | Real atomic pair | same event identity, both recipient IDs, points `5`, applied outcome |
| `copy_success_receipt` | exit | Receipt completed | same identity, applied outcome |
| `accounts.views._profile_contribution_context` | branch | Post-event GET | `summary_state=stored`, Maria subject ID |
| Same | exit | Fresh projection | `total_points=8205`, `primary_category=Design` |

`test_s28_copy_log_story_happy` asserts where, literal beat and required fragments using `assert_log_story`. After clearing baseline-generation logs, assert no new summary entry/completion beat. This absence supplements captured-port proof; it cannot replace it. S36 owns rejected receipt log paths; S28 introduces no new rejection branch.

## F — MCP


Not applicable. No MCP tool, facade registration, client forwarding or API schema changes. S28 operates through existing Django lifecycle, GUI receipt and HTML surfaces.

## G — Agent proofs


| Proof | Script/provider | Required assertions |
|---|---|---|
| PRF-EXPERTS-01 stability extension | Real CAP-004 ScriptedLLM; Cedar paragraph plus S23 assessment script loaded through S23 support | Actual baseline `contribution_summary` trace: entry, public_evidence, llm_call, validation, domain_write, exit. Then unchanged captured calls, persisted interactions and refresh metadata across receipt/display; numeric totals change. |

Selected CAPs are reused, not expanded. No ToolExecutor, tool registry, broker, blackboard or new PRF identity.

The test keeps S23’s scoped `resolve_processing_llm` test hook installed through both baseline generation and subsequent HTTP actions. That ensures an accidental refresh uses the same captured provider seam. Verify the completed S23 wiring, rather than inventing the setting name before reconciliation. `ScriptedLLM.calls` must capture every validated attempt, including exhausted calls. No new adverse agent capability is introduced; provider/privacy failure proofs remain S23/S27/S29.

## H — Mockup graduation


Strategy: **certify existing graduation**. S04/S10/S17 already own production templates based on the Experts prototypes. S36 owns clipboard wiring.

Use their stable selectors: `experts-card-mrodriguez`, nested `expert-card-karma`, `profile-karma-total`, `profile-contribution-summary`, `expert-karma-total`, `expert-contribution-summary`, and the actual copy button. The browser test verifies the existing visual truncation preserves stored DOM text; S11/S04 retain geometric viewport certification. No duplicate CSS, template or JavaScript implementation is needed.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/galdr-contribution-summary.feature:36`; 1 expanded case(s), primary layer `at`. Dependencies: S23, S10, S11, S12, S36. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: GALDR-SUMMARY-06
  nodes:
  - id: N1-stability
    title: Certify receipt, live projections and no regeneration
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_summary_proofs.py
    - tests/integration/test_experts_summary_stability.py
    - tests/support/experts_summary_stability.py
    tests:
    - test_s28_copy_receipt_with_stored_summary_updates_only_live_numbers
    - test_s28_display_with_completed_copy_reads_live_totals_and_stored_prose
    - test_s28_copy_log_story_happy
    - test_s28_points_change_agent_story_happy
    log_story_rows:
    - copy_success_receipt:entry
    - copy_success_receipt:validation
    - KarmaService.award_successful_consumption:processing
    - copy_success_receipt:exit
    - accounts.views._profile_contribution_context:branch
    - accounts.views._profile_contribution_context:exit
    gate:
      command: pytest tests/integration/test_experts_summary_stability.py -x
      log_story_command: pytest tests/integration/test_experts_summary_stability.py::test_s28_copy_log_story_happy
        -x
      agent_proof_command: pytest tests/integration/test_experts_summary_proofs.py::test_s28_points_change_agent_story_happy
        -m agent_proof -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-assert-agent-story
      - do-docstring-format
  - id: N2-acceptance
    title: Bind exact stable-prose living specification
    bpe: BPE-04
    depends_on:
    - N1-stability
    footprint:
    - docs/features/steps/experts_summary_stability_steps.py
    gate:
      command: make test-experts-s28-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: N3-browser
    title: Certify actual clipboard and refreshed displays
    bpe: BPE-05
    depends_on:
    - N2-acceptance
    footprint:
    - tests/e2e/test_experts_summary_stability.py
    tests:
    - test_s28_browser_with_successful_copy_updates_score_and_preserves_paragraph
    gate:
      command: make test-experts-s28-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
  - id: N4-dod
    title: Review exact contract and aggregate evidence
    bpe: BPE-06
    depends_on:
    - N3-browser
    footprint: []
    gate:
      command: make test-experts-s28
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-assert-agent-story
      - do-github-issues
    notes: Require N1/N2/N3 checkpoint evidence as well; aggregate exclusion cannot substitute.
  scenario_dependencies:
  - S23
  - S10
  - S11
  - S12
  - S36
```

## Lessons Learned

Unchanged stored interactions alone cannot establish absence of provider calls. A real generated baseline, captured sole model port and attempt capture before exhaustion provide stronger falsification.

The same public paragraph can remain valid while Development learning points and overall totals change. Primary category and four source totals must therefore be tested independently.

Existing clipboard and lifecycle code provide the required boundaries; this scenario needs focused cross-boundary certification rather than new production machinery.

After PIN-04 issue publication and PIN-05 GO: N1 behavior/log/agent proofs ship together, then N2 acceptance and N3 browser certification, then N4 evidence review. Use `Refs #N` on each slice and `Closes #N` only on the final successful slice, with required commit-linked issue updates. No writes, tests or commits were performed by this worker.
