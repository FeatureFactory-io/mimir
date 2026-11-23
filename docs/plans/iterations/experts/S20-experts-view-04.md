# S20: EXPERTS-VIEW-04 Keep private data out of the public response

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S20
acceptance_id: EXPERTS-VIEW-04
feature_file_path: docs/features/act-18-experts/experts-view.feature
feature_line: 28
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
- S17
- S14
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- bf47ae52b0f3d7601abb23348e8a07bf3fde0c22705440ab31c2938dc28759d1
```

## A — Context map


| Verified source | Meaning |
|---|---|
| `docs/features/act-18-experts/experts-view.feature:28-33` | Anonymous detail must omit the three exact sentinels and token field. |
| `methodology/models/playbook.py:84-125` | `can_view` also permits owners/team/group members and authenticated public active/disabled access; it cannot define public expert evidence. |
| `accounts/views.py:285-317` | Existing own-profile response deliberately includes email, token and private collections; public detail must not reuse its context. |
| `docs/architecture/SAO.md:3883-3905` | Public detail exposes approved totals, stored public summary and currently public released evidence through Django templates. |
| `test-data/experts/cedar-rfp-01.json:114-138` | Maria's public identity, legitimate contact email, released playbook 6101 and exact private sentinels. |

Additional inspected implementation: `mockups/experts_views.py:38-58` copies the entire fictional person dictionary. This is prototype behavior, unsuitable for production projection reuse. `tests/e2e/conftest.py:101-117,141-168` supplies existing isolated browser/page and function-selectable real live server.

## B — Do not do


- Do not add runtime behavior, routes, permission policies, summary generation or model changes in S20. S17 owns the public detail allowlist and explicit `visibility="public", status="released"` query.
- Do not serialize or recursively inspect the entire Django context: `request.user` may legitimately contain account data. Inspect only S17's designated public DTO, separately inspecting S14's authorized contact context.
- Do not remove Elena's legitimate authenticated `mailto:maria.rodriguez@example.com` behavior.
- Do not modify staff flags, grant permissions, share private playbooks with Elena, or broaden PIP access to make tests pass.
- Do not load fictional private fixture JSON into production views or templates.
- Do not mistake absent seeded private records, skipped tests or zero selected scenarios for privacy evidence.

## C — Applicable architecture


- **Experts & Karma delivery architecture — Awards, projections and transaction boundaries**.
- **Web delivery and notification reuse**.
- **Test strategy for this delta**.
- **FOB Authorization — Guest read security**.
- **E2E Testing with Playwright**.
- IA §11, especially `docs/ux/IA_guidelines.md:1179-1192`.

SAO §17 generation proofs belong to S23/S27. This scenario certifies the stored public presentation boundary.

## D — Tests and exact assertions


All DB/HTTP tests use real objects and the real Django client; no mocks.

| Test | Assertions |
|---|---|
| `test_public_detail_with_anonymous_viewer_excludes_private_data` | Seed and verify real private playbook, private PIP and Maria token first. GET `/experts/mrodriguez/` is 200; identity and public evidence 6101 remain. Full HTML, including hidden markup/attributes/scripts, omits all three sentinels, Maria email and `mailto:`. Own-profile controls are absent. Inspect only public DTO for allowlisted scalar/nested fields. |
| `test_public_detail_with_authenticated_elena_preserves_public_boundary` | `force_login(esvensson)` without role changes; 200; no private titles/body/token/account controls; legitimate Maria contact link present. Public DTO remains email-free; separately authorized S14 contact data may contain email. |
| `test_public_detail_with_unpublished_evidence_excludes_each_status` | Parameterize public `draft`, `active`, `disabled` evidence plus private released evidence. Their unique names/body markers/links never appear for Bob or Elena, while released public 6101 remains. Confirm these variants really exist in DB. |
| `test_public_detail_with_private_fixture_has_allowlisted_projection` | Obtain only S17 DTO from actual response; require exact approved DTO schema and nested evidence schema, no ORM/User/PIP/Token objects or forbidden keys; every evidence PK resolves to a public released row. |
| `test_public_detail_with_guest_browser_omits_private_markup` | Existing real browser/page/live-server fixtures; production detail returns 200, Maria/public link visible, whole `page.content()` excludes sentinels/email/mailto and profile control hooks. |
| Exact named Behave contract | Bind the original VIEW-04 phrases to real HTTP/parser assertions; run all five steps plus baseline, with no undefined/skipped steps. |

Private controls to exclude include the actual hooks `profile-token-field`, `profile-token-toggle`, `profile-token-copy`, `profile-token-regenerate-form`, `profile-edit-btn`, `profile-pips-table`, `profile-teams-section`, and `profile-playbooks-table`. Do not prohibit ordinary site navigation to the viewer's own profile.

Fixture proof must inspect persisted `Playbook.name/description`, `ProcessImprovementProposal.title/summary` and `Token.key`; negative HTML checks alone are insufficient.

S03 owns `load_cedar_baseline()`, `CedarDataset`, baseline binding and shared `find_by_test_id`. Reuse them. S20 owns only its distinct anonymous-open, omission and absent-test-id phrases. Reconcile the designated DTO context key with S17 before applying skeletons; below, `expert` is the proposed key.

## E — Log story


Not applicable: this is certification-only work with no new service/controller action or runtime logging. S17 retains its behavior/log-story gate; S20 does not replace it. No new log-story test or command is claimed. Test failures must describe field names/categories without dumping secrets or the whole context.

## F — MCP tools


Not applicable: no MCP change, facade registration, REST write or export receipt.

## G — Agent proofs


Not applicable: no provider call, prompt, orchestration or generated-summary mutation. No ScriptedLLM fixture, ToolExecutor or new PRF is needed.

## H — Graduation and delivery


S17 owns graduation of `templates/mockups/experts/detail.html` into `templates/experts/detail.html`; S14 owns the shared contact partial. S20 certifies their production outputs and proposes no duplicate templates/CSS.

Proposed footprint:



No migration, tracked seed or production file belongs in this footprint.

Execution requires PIN-04 issue with this full contract and docs handoff commit, then PIN-05 GO. Later slices: backend certification, AT bindings, browser certification, terminal DoD. Each slice follows `Refs #N` plus required issue update; final slice alone uses `Closes #N`.



Graph dependencies are local; scenario dependencies apply before N1. Exact `--tags=@experts` deliberately overrides inherited WIP exclusion for this named certification. Require one executed scenario and no skipped/undefined steps. `make test-at-experts` remains the aggregate iteration gate after all contracts are ready; zero coverage never completes it. Run browser and backend gates separately with their respective settings.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-view.feature:28`; 1 expanded case(s), primary layer `at`. Dependencies: S03, S17, S14. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-VIEW-04
  nodes:
  - id: S20-N1-boundary-proof
    title: Real DB public projection certification
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_public_privacy.py
    - tests/support/experts_privacy.py
    gate:
      command: pytest tests/integration/test_experts_public_privacy.py -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
    tests:
    - test_public_detail_with_anonymous_viewer_excludes_private_data
    - test_public_detail_with_authenticated_elena_preserves_public_boundary
    - test_public_detail_with_unpublished_evidence_excludes_each_status
    - test_public_detail_with_private_fixture_has_allowlisted_projection
  - id: S20-N2-acceptance
    title: Execute exact privacy acceptance contract
    bpe: BPE-04
    depends_on:
    - S20-N1-boundary-proof
    footprint:
    - docs/features/steps/experts_privacy_steps.py
    gate:
      command: make test-experts-s20-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
  - id: S20-N3-browser
    title: Certify actual guest DOM
    bpe: BPE-05
    depends_on:
    - S20-N2-acceptance
    footprint:
    - tests/e2e/test_experts_public_privacy.py
    gate:
      command: make test-experts-s20-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
      - pytest
  - id: S20-N4-dod
    title: Verify complete privacy evidence
    bpe: BPE-06
    depends_on:
    - S20-N3-browser
    footprint: []
    gate:
      command: make test-experts-s20
      additional_commands:
      - make test-at-harness
      - make lint
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-github-issues
      - pytest
  scenario_dependencies:
  - S03
  - S17
  - S14
```

## Lessons Learned

The prototype copies all fictional person fields, so visual resemblance cannot establish a safe production projection. Existing `can_view` intentionally grants broader authenticated access than public expert evidence permits. Privacy tests must prove sensitive records exist, inspect the designated DTO, and distinguish guest email exclusion from legitimate authenticated contact.

No files changed, tests executed, commits made or external actions taken.

## Structural application evidence

`docs/experts-replay/pin-evidence/S20.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.

## Actual structural footprint

`docs/experts-replay/pin-evidence/S20.json`, `docs/features/steps/experts_privacy_steps.py`, `docs/plans/iterations/experts/S20-experts-view-04.md`, `tests/e2e/test_experts_public_privacy.py`, `tests/integration/test_experts_public_privacy.py`, `tests/support/experts_privacy.py`

Skeleton: `f76bbf0c3d1cd8c337e26648fc6ddc60b7acf345`; shared reconciliation: `39d598328d438d09723b6eb14574fbf92fab71c9`. Semantic and physical-file dependencies are recorded separately in the iteration manifest. Context-map line ranges record the workers’ inspection baseline; headers and the final scaffold remain authoritative.
