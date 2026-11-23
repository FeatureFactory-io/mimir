# S24: GALDR-SUMMARY-02 Present one stored summary consistently

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S24
acceptance_id: GALDR-SUMMARY-02
feature_file_path: tests/e2e/experts-interactions.feature
feature_line: 30
primary_execution_layer: e2e
expanded_case_count: 1
dependencies:
- S23
- S04
- S10
- S11
- S17
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- bf87fd12ac9fbab82cc0c3dd72a307a621dbea4a53a77a209db0cfe921a53ba8
```

## A — Context map


| Verified source | Lines | Relevance |
|---|---:|---|
| `docs/features/act-18-experts/galdr-contribution-summary.feature` | 17–21 | One refreshed stored paragraph supplies own profile, leaderboard hint and full public detail. |
| `test-data/experts/cedar-rfp-01.json` | 114–119, 1040–1056 | Maria’s actual nine-sentence paragraph; refreshed prose may retain identical public facts. |
| `docs/architecture/SAO.md` | 3883–3905, 3912–3928 | Stored public prose, existing routes/templates, separate Django-client and browser certification. |
| `docs/architecture/SAO.md` | 3937–3977, 3988–4019 | S23 owns bounded generation/persistence; rendering must introduce no competing provider path. |
| `docs/ux/IA_guidelines.md` | 1167–1204 | Two-line hints, four-line own preview, full public paragraph and seven exact viewports. |

Actual fixture implementation details were also inspected: `tests/e2e/conftest.py:101–117,141–168` exposes existing function-scoped `page` and selectable function-scoped `live_server_url`. `accounts/views.py:285–317` is the existing authenticated profile controller; current code has no Experts contribution behavior.

Orient confirms S24 and all 49 contracts remain in scope. The older readiness file’s pending scope statement is superseded by `docs/plans/iterations/pin-orient-20261123.md`.

## B — Do not do


- Do not regenerate, summarize, slice or shorten stored prose on a GET.
- Do not add a provider stub, generation endpoint, queue, ToolExecutor or second summary service.
- Do not copy mockup JSON projection into production.
- Do not simulate clamp geometry, expansion clicks or browser layout in Django-client AT.
- Do not change account permissions, expose own-profile account fields publicly or award Karma.
- Do not replace S03/S04/S10/S17/S23 implementations with raising stubs.
- Do not remove feature-level `@wip` and claim the remaining unimplemented contracts pass.
- No worker writes, tests, commits, live-provider calls or GitHub actions.

## C — Applicable architecture and ownership


Governing headings: **Awards, projections and transaction boundaries**, **Web delivery and notification reuse**, **Test strategy for this delta**, and §17 **Components, pattern and serving decisions**, **Privacy, bounds and failure policy**, **Observability and proof gates**.

S03 supplies real `ExpertProfile`, Cedar adapter, projection and shared HTML parser. S04 supplies card presentation. S10 supplies existing-own-profile integration and its overflow-aware expansion handler. S17 supplies public detail. S23 establishes a successful refresh and owns generation/persistence.

S24 is a certification slice consuming those interfaces. Its baseline fixture represents an already successful stored refresh; it does not claim that loading a fixture proves generation. S23’s lifecycle proof separately proves the transition into that state.

Use `load_cedar_baseline()->CedarDataset`, `users_by_username`, and the stored `ExpertProfile` paragraph. Reuse S03’s `find_by_test_id`/`element_text`; reuse S03’s baseline and Hana setup, S10’s Maria authentication/profile-opening phrases, and existing actor/path bindings. No duplicate parser, generic navigation steps or Cedar loader.

Proposed implementation footprint:



No production or schema changes are expected. Any discovered production defect belongs in the owning prerequisite’s reconciled footprint before implementation.

## D — Exact tests and assertions


| Test | Required assertions |
|---|---|
| `test_stored_summary_with_three_surface_reads_preserves_identical_full_text` | Real Cedar DB. Maria’s stored paragraph equals the nine-sentence oracle. Authenticated Maria own-profile, Elena’s Design leaderboard and anonymous public detail return 200. All three prose nodes contain the complete stored paragraph, including its final sentence. |
| `test_stored_summary_with_repeated_reads_preserves_refresh_state` | Repeat actual GETs; stored text, refresh metadata and summary interaction count remain unchanged. Read-path inspection confirms these views consume persisted projection only; unchanged interaction count alone is not claimed to prove absence of provider traffic. |
| `test_stored_summary_with_target_viewport_preserves_visual_contract` | Seven actual Chromium cases. All three nodes retain identical complete `text_content`. Card visibly clamps at two lines, own preview at four, public paragraph has no clamp and no clipped overflow. Real Show more/Show less restores the same paragraph and correct ARIA state. No page-level horizontal overflow. |

For the browser test, inspect computed line height, rendered height, `scrollHeight`, `clientHeight`, overflow and line-clamp; allow ≤1 CSS pixel rounding tolerance. Long Maria prose must actually overflow each collapsed preview. Public detail must show its complete height. Do not infer visual truncation from a class name alone.

Existing card hook is `experts-card-mrodriguez`; agree with S04 on a scoped `expert-card-hint` prose hook. Existing own/public hooks are `profile-contribution-summary` and `expert-contribution-summary`. Selector agreement is prerequisite convergence, not a new S24 production behavior.

AT owns precisely these four new phrases:

1. `Maria's contribution summary has refreshed`
2. `her own profile and public expert detail show that stored text`
3. `her leaderboard hint is a visually truncated excerpt of it`
4. `the public detail retains the complete paragraph`

The hint AT binding checks the full source text in the real rendered hint and its production clamp class. Its catalog entry explicitly maps **visual** proof to the seven browser cases. It never pretends that Django’s HTML parser lays out CSS.

Commands, to run only after GO:

```bash
.venv/bin/pytest tests/integration/test_experts_stored_summary.py -x
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance .venv/bin/python manage.py behave --simple --tags=@experts --name='^GALDR-SUMMARY-02 Present one stored summary consistently$' docs/features/act-18-experts/galdr-contribution-summary.feature
E2E_LIVE_SERVER_SCOPE=function .venv/bin/pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_stored_summary.py -x
make test-at-harness
make test-at-experts
make test-agent-experts
```

Expected S24 counts: **2 integration tests, 1 AT scenario/6 steps including background, 7 browser cases**; none skipped. Exact `--tags=@experts` overrides configured WIP exclusion only for the named contract. Aggregate Experts certification remains incomplete until every contracted scenario actually runs.

## E — Log story


Not applicable to new S24 behavior: this slice adds certification only and introduces no production controller/service decisions or mutations. Existing render logs and S23’s refresh log story remain owned and tested upstream. Do not manufacture test-only production logs or duplicate their logging methods.



No `checkpoint.log_story_command` is declared.

## F — MCP tools


Not applicable. S24 changes no MCP tool, REST endpoint, facade registration or authorization forwarding. MCP T1/T2/T3 registration proofs would test an unrelated surface.

## G — Agent proofs


No new or modified agent capability, so S24 declares no separate PRF or scripted fixture. Reuse S23’s required real lifecycle proofs through `make test-agent-experts`; deterministic stored-display tests do not substantiate live model quality.

If convergence requires a lifecycle-to-display proof, extend S23’s existing real submission proof with the same finite `ScriptedLLM` and `PRF-EXPERTS-03/submission_happy.json`; assert its captured calls do not increase during subsequent GETs. Do not create another provider seam or use `StubGaldrClient`. This extension is unnecessary for the stated already-refreshed display precondition.

## H — Mockup graduation and local execution graph


Reference `templates/mockups/experts/list.html:13–18`, `detail.html:6`, `own_profile.html:6–13`, and `base.html:9–12`. These establish full DOM prose with two/four-line CSS treatment. S04/S10/S17 graduate those recipes; S24 certifies their production routes. Preserve the existing profile account features. Screenshots must show production routes, not `/mockups/`.



All four nodes serialize locally. PIN-04 owns issue/handoff publication; PIN-05 owns GO. Thereafter each node receives its own `Refs #N` commit and approved issue update; final DoD uses `Closes #N`.

## Parent convergence

Authoritative acceptance source: `tests/e2e/experts-interactions.feature:30`; 1 expanded case(s), primary layer `e2e`. Dependencies: S23, S04, S10, S11, S17. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.
This entire acceptance contract is browser-certified. Server checks are complementary initial-HTML/receipt contracts; no clipboard/hover/expansion Behave substitution is allowed.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: GALDR-SUMMARY-02
  scenario_id: S24
  external_dependencies:
  - S03
  - S04
  - S10
  - S17
  - S23
  nodes:
  - id: S24-N1-stored-read-contract
    title: Certify shared stored source through real views
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_stored_summary.py
    tests:
    - test_stored_summary_with_three_surface_reads_preserves_identical_full_text
    - test_stored_summary_with_repeated_reads_preserves_refresh_state
    gate:
      command: pytest tests/integration/test_experts_stored_summary.py -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
  - id: S24-N2-acceptance
    title: Bind the exact stored-summary acceptance contract
    bpe: BPE-04
    depends_on:
    - S24-N1-stored-read-contract
    footprint:
    - docs/features/steps/experts_stored_summary_steps.py
    gate:
      command: make test-experts-s24-server
      expected_scenarios: 1
      expected_steps: 6
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
  - id: S24-N3-browser
    title: Certify real clamp geometry at seven IA viewports
    bpe: BPE-05
    depends_on:
    - S24-N2-acceptance
    footprint:
    - tests/e2e/test_experts_stored_summary.py
    gate:
      command: make test-experts-s24-browser
      expected_tests: 7
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
      - pytest
  - id: S24-N4-dod
    title: Record actual production-screen evidence and inherited gates
    bpe: BPE-06
    depends_on:
    - S24-N3-browser
    footprint:
    - docs/ux/experts-responsive-evidence.json
    gate:
      command: make test-experts-s24
      additional_commands:
      - make test-at-harness
      - make test-agent-experts
      requirement: S24 exact gates and nonempty aggregate gates pass; skipped/zero is not completion.
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-follow-commit-convention
      - do-github-issues
      - pytest
  scenario_dependencies:
  - S23
  - S04
  - S10
  - S11
  - S17
```

## Lessons Learned

- Already-refreshed display and generation are separate contracts; repeating S23’s generation machinery would create competing ownership.
- Full DOM equality does not establish visual visibility. Geometry requires the actual browser and correct E2E configuration.
- Maria’s real nine-sentence fixture supplies long text naturally; synthetic filler and simulated clamps would weaken the proof.
- Shared parser, actor/path steps and established browser lifecycle prevent duplicate infrastructure.
- Planned gates were not executed; no passing behavior is claimed.

## Structural application evidence

`docs/experts-replay/pin-evidence/S24.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.
