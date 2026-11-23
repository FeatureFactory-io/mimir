# S25: GALDR-SUMMARY-03 Refresh on normal withdrawal and resubmission

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S25
acceptance_id: GALDR-SUMMARY-03
feature_file_path: docs/features/act-18-experts/galdr-contribution-summary.feature
feature_line: 17
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S23
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 86730a150c5aad93dad96b87d805c68f47c9ddd0a520451f9b3207adc5a2b47e
```

## A — Context Map


| File | Verified lines | Meaning |
|---|---:|---|
| `docs/features/act-18-experts/galdr-contribution-summary.feature` | 23–27 | Exact Reviewed → withdrawal → normal resubmission contract; Maria remains 8200. |
| `methodology/services/pip_service.py` | 536–595, 750–793 | `withdraw_pip` cancels; `revert_to_draft` permits Reviewed and clears assessments; normal submission schedules Galdr. |
| `methodology/pip_views.py` | 568–606 | Existing authenticated POST submit/revert endpoints reach the real shared services. |
| `templates/pips/detail.html` | 30–43, 222–240 | User-facing **Withdraw to Draft** calls `pip_revert_to_draft`; **Cancel PIP** is a distinct action. |
| `docs/architecture/SAO.md` | 3943–3977, 3979–4018 | Existing scheduler, sole ScriptedLLM seam, public-only evidence, last-good preservation, production trace and PRF gates. |

Also inspected Cedar JSON, Galdr runner/client, port and proof helpers, EmailService, existing lifecycle/revert/browser test bodies, Makefile, Behave environment/catalog, orient roster and delivered S23/S27 reports.

**Critical verified distinction:** the scenario’s normal withdrawal is `PIPService.revert_to_draft`, exposed as **Withdraw to Draft**. `withdraw_pip` transitions to terminal `withdrawn`, corresponding to **Cancel PIP**. No new lifecycle transition or status permission is needed.

The existing `test_full_galdr_feedback_loop_revert_and_resubmit` (`tests/integration/test_pip_revert_to_draft.py:341–371`) manually assigns Reviewed. It remains a regression test; it cannot certify S25’s full normal lifecycle.

## B — Do-Not-Do List


- Do not assign PIP status manually to prepare Reviewed or Draft.
- Do not submit a Reviewed PIP directly; return it to Draft through the existing allowed service/view.
- Do not reinterpret cancellation as resumable withdrawal.
- Do not award points for withdrawal, submission, resubmission or generation.
- Do not invoke administrator finalization to demonstrate refresh.
- Do not publish the new proposal or include its title/body in summary evidence.
- Do not invent new public facts, changed counts or a “recently accepted” claim.
- Do not demand different prose as the definition of a refresh; the same paragraph can be a valid new result.
- Do not replace domain services, scheduler, query, prompt, validator, store or assessment parser with mocks.
- Do not use `StubGaldrClient` in the new lifecycle proof.
- Do not add another queue, provider factory, model method, migration or seed mutation.
- Do not replace existing working implementation with raising skeletons.

## C — Governing SAO Sections and Design


Applicable headings:

- **Awards, projections and transaction boundaries**
- **Web delivery and notification reuse**
- **Test strategy for this delta**
- **17. AI Agent Architecture — Experts contribution summary**
- **Components, pattern and serving decisions**
- **Capability selection and dependency wiring**
- **Privacy, bounds and failure policy**
- **Observability and proof gates**

S25 certifies S23/S27 composition without expected runtime changes:

1. Load S03’s real `CedarDataset`; use `users_by_username["mrodriguez"]` and actual Hana target bindings.
2. Reuse S23 `prepare_summary_submission`, reconciled to accept `CedarDataset`, to create **Screen Reader Error Recovery** with one valid ADD Activity through real services.
3. Inject one finite `ScriptedLLM` through S23’s optional port bridge. Initial normal submission must actually reach Reviewed.
4. Snapshot stored paragraph, interaction IDs, complete ledger rows, Maria’s projected total, target version/content and decision fields.
5. Call real `revert_to_draft`. Verify Draft, cleared per-change/holistic assessment, unchanged paragraph and zero additional provider calls/interactions/awards.
6. Submit the same PIP normally with a new correlation ID. Verify a second actual summary request and assessment, stored validated response and a second successful summary interaction before any administrator decision.
7. Assert Maria remains exactly 8200, ledger unchanged, no published ADD, Hana remains v2.0 and no decision mail.

Use both existing assessment modes for service proofs. Each successful cycle requires **summary + assessment**, so the full loop consumes **four** responses. The private assessment request may contain proposal content; privacy assertions inspect summary requests at positions 0 and 2, never mislabel the private assessment as public evidence.

Use S27’s immutable boundary result and authentic trace; S23 appends/persists `domain_write`. Do not fabricate passing trace dictionaries.

For deterministic replacement proof, the first and second summary responses may be distinct valid paraphrases of the **same approved public facts**. No output marker, synthetic fact, changed count or new publication is needed. An identical-text variant verifies that a second interaction/request still establishes refresh.

S03 owns schema/Cedar; S27 owns `.calls`, evidence/prompt/validator/boundary; S23 owns adapter/composition/scheduling/storage and optional assessment bridge. S25 consumes these contracts.

## D — Tests to Create


| Test | Required assertions |
|---|---|
| `test_s25_resubmit_with_reviewed_pip_refreshes_without_award` | Parametrize target-state/per-change modes. Real initial submit reaches Reviewed; real revert clears assessments with zero calls; normal resubmit reaches Reviewed. Exactly four `.calls`, two successful summary interactions, stored second response, distinct correlations, total 8200 and complete ledger unchanged. |
| `test_s25_resubmit_with_identical_valid_summary_records_new_refresh` | Same valid summary text in both cycles; second request/interaction exists even though stored paragraph is equal. No fabricated changed facts/counts. |
| `test_s25_submit_with_reviewed_or_foreign_actor_rejects_before_refresh` | From genuinely reached Reviewed, direct resubmit rejects. Nonowner revert rejects. Neither changes status, text, ledger or interactions; provider call count remains two. |
| `test_s25_http_withdraw_and_resubmit_uses_existing_post_routes` | Authenticated real Django-client POSTs to initial submit, revert and resubmit; normal redirects; same PIP survives; Draft assessment fields clear; Reviewed final state; refreshed stored text; no administrator decision/mail/award. |
| `test_s25_resubmission_log_story_happy` | Existing real revert log beats and S23/S27 refresh beats for both correlations; no sensitive bodies. |
| `test_s25_resubmission_log_story_reject` | Normal initial submit → real revert → explicit second-summary provider error → valid assessment. Failure/retention beats; last good paragraph; no summary-domain write for rejected run. |
| `test_s25_resubmission_agent_story_happy` | PRF-EXPERTS-01/03 and PRF-OBS-01: two genuine persisted traces, actual summary calls public-only, real domain effects, four model turns and no award. |
| `test_s25_resubmission_agent_story_reject` | PRF-EXPERTS-02: second summary failure retains first text, failure interaction has safe partial trace, no successful summary write; remaining assessment response is consumed and existing lifecycle recovery policy retained. |
| `test_s25_browser_withdraw_and_resubmit_refreshes_before_decision` | Real login and clicks on existing controls/modal; Reviewed → Draft → Reviewed; model-only injection; second persisted interaction/text; no decision and 8200 unchanged. |

All tests initially remain documented raising skeletons. No test was executed during planning.

Commands, from the replay repository:

```sh
pytest tests/integration/test_experts_summary_resubmission.py tests/integration/test_experts_summary_proofs.py -k s25 -x
pytest tests/integration/test_experts_summary_resubmission.py -k 's25 and log_story' -x
pytest tests/integration/test_experts_summary_proofs.py -m agent_proof -k s25 -x
```

Exact living-spec gate explicitly overrides inherited WIP filtering:

```sh
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance python manage.py behave --simple --tags=@experts --name '^GALDR-SUMMARY-03 Refresh on normal withdrawal and resubmission$' docs/features/act-18-experts/galdr-contribution-summary.feature
```

Require **one selected scenario passed, zero undefined/failed steps**. Other scenarios may be unselected; zero selected/passed is never completion. Preserve feature-level WIP until its other contracts also qualify.

Browser gate:

```sh
E2E_LIVE_SERVER_SCOPE=function pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_summary_resubmission.py::test_s25_browser_withdraw_and_resubmit_refreshes_before_decision -x
```

Regression and aggregate delivery gates:

```sh
pytest tests/integration/test_pip_revert_to_draft.py tests/integration/test_pip_lifecycle.py tests/integration/test_galdr_target_state.py -x
make test-at-harness
make test-agent-experts
make test-at-experts
make lint
```

Aggregate Experts AT is final-feature evidence only when all intended contracts actually execute; its WIP exclusion can otherwise produce incomplete coverage.

## E — Log Story Script


Assert existing revert logs and S23/S27-owned refresh logs; no S25 runtime logging addition is expected.

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `PIPService.revert_to_draft` | entry | Maria withdraws Reviewed PIP | `pip=`, `actor=`, `status=reviewed` |
| Same | validation | Allowed owner/state | `validation allowed`, `status=reviewed`, `pip=` |
| Same | processing | Assessment cleared | `changes_cleared=1`, `pip=` |
| Same | exit | Draft persisted | `status=draft`, `pip=` |
| `ContributionSummaryService` | entry | Both normal processing runs | `pip_id=`, `subject_id=`, matching `correlation_id=` |
| S27 boundary | processing | Each summary completion | Matching correlation, `tools=none`, bounded model call |
| S23 summary service | exit | Successful refresh | Matching correlation, success and zero-award outcome |
| S23 summary service | error/branch | Second-summary provider failure | Safe `reason_code=provider_failed`, last-good retention |
| Existing Galdr | exit | Assessment persisted | `pip id=`, `reviewed` |

Use `assert_log_story` and scope assertions by each correlation for refresh records. Existing revert records lack correlation, so match actual pip/actor/status rather than invent a field. Enable named loggers for capture; `mimir.settings.test` disables existing loggers.

Assert absence of private Cedar title/PIP/token/email sentinels, new proposal title/body, and summary response bodies from captured logs/production traces.

## F — MCP Tools


Not applicable. No MCP registration, facade, schema or transport modification. This scenario uses existing HTTP/domain lifecycle routes.

## G — Agent Proofs


| PRF | Script | Genuine proof |
|---|---|---|
| PRF-EXPERTS-01 | `tests/fixtures/llm_scripts/PRF-EXPERTS-01/resubmission_happy.json` | Both cycles: `entry → public_evidence → llm_call → validation → domain_write → exit`; same PIP/subject, distinct correlations, no tools/awards. |
| PRF-EXPERTS-03 | Same | `.calls[0]` and `.calls[2]` retain approved public facts and exclude private/unpublished proposal/account/score data before model invocation. |
| PRF-OBS-01 | Same | Two persisted summary interactions have supplied usage, nonnegative measured latency, configured/unknown cost semantics and correct run identity. |
| PRF-EXPERTS-02 | `tests/fixtures/llm_scripts/PRF-EXPERTS-02/resubmission_reject_provider.json` | Second cycle has authentic failure/exit trace and no successful summary write; previous paragraph retained; assessment executes. |

Happy script order: valid public summary A; valid existing assessment for actual change ID; valid public summary B; valid existing assessment for the same change ID. Rejection script replaces item 3 with explicit `LLMError`. Same-text test derives its queue through the shared loader, using A for item 3.

Script files support the two existing assessment formats using S23’s loader conventions; interpolate only actual change-ID fields. Preserve loud exhaustion. No live provider, custom fake, StubGaldrClient or service patch.

## H — Mockup Graduation and Browser Certification


No new template or styling is required. Reuse production controls:

- `pip-detail-revert-open`
- `pip-revert-modal`
- `pip-detail-revert-confirm`
- `pip-detail-submit`
- `pip-status-badge`

Use `get_by_test_id`, accessible modal name **Return PIP to Draft?**, and existing login selectors/helpers. Reuse `page` and `live_server_url`; the inspected fixtures are at `tests/e2e/conftest.py:113–116,141–168`.

Do not reuse old `reviewed_pip_for_e2e`, which assigns Reviewed manually. Prepare the new browser PIP through genuine initial processing. Configure only S23’s existing test provider injection so live-server requests consume the same finite queue; no second factory/settings mechanism.

The Django-client AT step proves HTTP/domain behavior; Playwright independently proves actual modal activation and submission clicks. No simulated clicks inside AT.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/galdr-contribution-summary.feature:17`; 1 expanded case(s), primary layer `at`. Dependencies: S23. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: GALDR-SUMMARY-03
  nodes:
  - id: S25-N1-lifecycle
    title: Certify real Reviewed withdrawal and repeat processing
    bpe: BPE-02
    depends_on: []
    external_dependencies:
    - S03
    - S23
    - S27
    footprint:
    - tests/fixtures/llm_scripts/PRF-EXPERTS-01/resubmission_happy.json
    - tests/fixtures/llm_scripts/PRF-EXPERTS-02/resubmission_reject_provider.json
    - tests/integration/test_experts_summary_proofs.py
    - tests/integration/test_experts_summary_resubmission.py
    tests:
    - test_s25_resubmit_with_reviewed_pip_refreshes_without_award
    - test_s25_resubmit_with_identical_valid_summary_records_new_refresh
    - test_s25_submit_with_reviewed_or_foreign_actor_rejects_before_refresh
    - test_s25_resubmission_log_story_happy
    - test_s25_resubmission_log_story_reject
    - test_s25_resubmission_agent_story_happy
    - test_s25_resubmission_agent_story_reject
    gate:
      command: pytest tests/integration/test_experts_summary_resubmission.py tests/integration/test_experts_summary_proofs.py
        -k s25 -x
      log_story_command: pytest tests/integration/test_experts_summary_resubmission.py -k 's25 and log_story' -x
      agent_proof_command: pytest tests/integration/test_experts_summary_proofs.py -m agent_proof -k s25 -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-assert-agent-story
      - pytest
  - id: S25-N2-http-at
    title: Bind exact lifecycle contract through Django HTTP
    bpe: BPE-04
    depends_on:
    - S25-N1-lifecycle
    footprint:
    - docs/features/steps/experts_summary_steps.py
    - tests/integration/test_experts_summary_resubmission.py
    tests:
    - test_s25_http_withdraw_and_resubmit_uses_existing_post_routes
    gate:
      command: make test-experts-s25-at
      acceptance_command: DJANGO_SETTINGS_MODULE=mimir.settings.acceptance python manage.py behave --simple --tags=@experts
        --name '^GALDR-SUMMARY-03 Refresh on normal withdrawal and resubmission$' docs/features/act-18-experts/galdr-contribution-summary.feature
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
  - id: S25-N3-browser
    title: Certify existing Withdraw to Draft modal and resubmit controls
    bpe: BPE-05
    depends_on:
    - S25-N2-http-at
    footprint:
    - tests/e2e/test_experts_summary_resubmission.py
    tests:
    - test_s25_browser_withdraw_and_resubmit_refreshes_before_decision
    gate:
      command: make test-experts-s25-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
      - pytest
  - id: S25-N4-dod
    title: Verify lifecycle privacy zero awards and all evidence gates
    bpe: BPE-06
    depends_on:
    - S25-N3-browser
    footprint: []
    gate:
      command: make test-experts-s25
      log_story_command: pytest tests/integration/test_experts_summary_resubmission.py -k 's25 and log_story' -x
      agent_proof_command: pytest tests/integration/test_experts_summary_proofs.py -m agent_proof -k s25 -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-assert-log-story
      - do-assert-agent-story
      - do-github-issues
      - pytest
    additional_gates:
    - make test-at-harness
    - make test-agent-experts
    - make lint
  scenario_dependencies:
  - S23
```

## Lessons Learned

The misleadingly named `withdraw_pip` is cancellation; the existing UI and Act9 contracts establish that resumable withdrawal means `revert_to_draft`. Reading the bodies prevents unnecessary lifecycle changes.

Legacy lifecycle/browser fixtures manually set Reviewed and cannot prove this scenario’s initial submission. S25 needs genuine first processing before withdrawal.

A refresh is evidenced by a new actual request and persisted interaction. Changed prose or counts are neither required nor sufficient. Public facts remain stable across an unpublished resubmission.

S23/S27 reports contain older shared-interface proposals (`requests`, mapping-based Cedar input and competing fixture names). Apply parent convergence: `.calls`, `CedarDataset`, S27 single-call `PRF-EXPERTS-03/happy.json`, and S23 separate two-call submission script. S25 adds only its own four-turn scripts.

No repository writes, mutations, tests, provider requests, commits or GitHub actions were performed.

## Structural application evidence

`docs/experts-replay/pin-evidence/S25.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.
