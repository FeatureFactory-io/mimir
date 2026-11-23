# S31: KARMA-RELEASE-02 Do not repeat the first-release award on later versions

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S31
acceptance_id: KARMA-RELEASE-02
feature_file_path: docs/features/act-18-experts/karma-accrual.feature
feature_line: 15
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S30
- S32
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 76b67b72b598a26f46c1a68900b6b6ba792822d422d89ac67b991dfae4570821
```

## A — Context map


| Verified source | Lines | Finding |
|---|---:|---|
| `docs/features/act-18-experts/karma-accrual.feature` | 15–18 | Exact contract: accepted PIP publishes next major without another first-release award. |
| `methodology/services/playbook_service.py` | 488–621 | Existing release returns `Playbook`; owner-only publication increments major. Existing staff-only revert preserves numeric version. |
| `methodology/services/pip_admin_service.py` | 24–114 | Real staff finalization applies accepted changes, invokes existing major bump and queues decision mail after commit. |
| `methodology/services/pip_apply_changes_service.py` | 757–801 | Existing PIP version owner creates exactly one `PIP_SOURCE` major history row. |
| `test-data/experts/cedar-rfp-01.json` | 634–655, 775–790 | Nora starts at zero; real first release earns 5,000; later v2.0 must not repeat it. |

Also inspected complete orient roster, replay AGENTS/CLAUDE, guidance/rules/ownership snapshots, IA, S30 and S45 reports, and actual test bodies. Existing assertions: `test_playbook_release.py:110–121` proves next major; `test_admin_revert.py:29–53` proves retained numeric version; `:56–96` proves edit-after-revert then release; `test_pip_admin_review_view.py:196–221` proves real administrator POST applies changes and publishes v2.0.

Working reuse: Django client, `PlaybookVersion`, `PIPAdminService.finalize_pip`, existing release modal/messages, `tests/support/log_story.py:9–37`, existing browser `page` and `live_server_url` fixtures. Experts ledger/query/Cedar bindings remain planned prerequisites, not implemented APIs.

## B — Do-not-do list


- No second award writer, release endpoint, release outcome type, version bump, model signal or production helper in S31.
- Preserve `release_playbook(...) -> Playbook`; S30 alone owns its outcome-based delegation and UI message wiring.
- Do not award on historical import or infer eligibility merely from absent ledger rows.
- Do not encode version, category, author or recipient into `first_release:<actual_playbook_pk>`.
- No manual version/status rewrites presented as lifecycle actions; exercise normal release, real PIP finalization and existing staff revert.
- Do not invent an undo/revert API. `revert_released_playbook_to_draft` requires staff and a nonempty reason; its existing UI is the Django admin action (`methodology/admin.py:35–50`).
- Do not grant Nora staff privileges. Cedar Mike already supplies the staff actor.
- Do not require summary generation, provider calls, queues, MCP changes or broadened PIP permissions.
- Do not duplicate S45 race, constraint or receipt-conflict tests; retain S31 lifecycle-specific ownership/historical proofs.
- Never replace existing working bodies with raising stubs.

## C — Applicable SAO sections and design


Governing sections: **Design Principles → Hybrid MCP Access**, **Version Management**, **Experts & Karma delivery architecture → Awards, projections and transaction boundaries**, **Web delivery and notification reuse**, **Test strategy for this delta**. SAO §17 supplies an exclusion: summaries cannot award points; this certification does not invoke summaries.

S03 owns schema/import/projection. S30 owns the sole `KarmaService.persist_awards`, publication eligibility/history detection, transaction hook and award message. First-release uniqueness must additionally cover the immutable playbook snapshot independently of recipient and channel. Imported historical first-release markers participate in discovery and uniqueness.

S31 certifies those interfaces after S03/S30. No dependency on S32: accepted-change award amounts are outside this contract. Its PIP proof inspects Nora’s release subtotal and immutable release row, permitting independently valid submitter awards.

Lifecycle:
1. Restore Cedar; use S30’s real `build_nora_release_case`.
2. Publish Nora’s actual draft normally: v1.0, one `first_release:6302`, Product 5,000.
3. Prepare an isolated reviewed PIP targeting that released playbook; Maria submits an ADD Activity under its real workflow.
4. Use the real administrator-finalization POST as Mike; require accepted state, new activity and v2.0 `PIP_SOURCE` history.
5. Assert Nora’s release award remains exactly the original row and 5,000.
6. Independently certify ordinary re-release and staff revert/release, imported markers, changed ownership and denied operations.

Reviewed-state construction is explicitly test setup: create draft/change through real builder services, then persist valid reviewed/Galdr metadata needed by finalization. It does not claim submission/Galdr behavior and does not call a provider. Numeric versions are always advanced by domain actions.

## D — Tests and exact assertions


| New test | Assertions |
|---|---|
| `test_later_major_with_accepted_pip_preserves_first_release_award` | Real Nora 0→5,000/v1.0, real admin POST → accepted/v2.0/new Activity/PIP_SOURCE row; original release row’s ID, amount, recipient, category, identity, channel and time unchanged; release sum 5,000/count one. |
| `test_later_major_with_normal_releases_preserves_single_award` | Real v1.0→2.0→3.0 through owner release POSTs; one release row; Nora remains 5,000; later responses omit earned-5,000 message while retaining normal success. |
| `test_later_major_with_staff_revert_and_release_preserves_single_award` | Mike’s real revert changes released→draft while holding version; normal draft edit advances minor under existing behavior; Nora release publishes next major; no deleted or repeated award. |
| `test_later_major_with_imported_release_marker_preserves_history` | S03-imported Mike/6201 canonical historical marker is discoverable; normal later release preserves marker fields, original timestamp and Mike’s 12,450 total; no fresh release event. |
| `test_later_major_with_changed_author_preserves_original_recipient` | After actual Nora first release, adversarial ORM setup reassigns author to Maria; normal release by Maria creates no second first award. Nora retains original 5,000; Maria gains no release points. |
| `test_later_major_with_denied_operations_preserves_version_and_award` | Wrong owner release and nonstaff revert raise/reject appropriately; blank revert reason rejects; persisted version/status and award snapshot unchanged. |
| `test_karma_later_release_log_story_happy` | Capture S30’s existing later-publication branch and message outcome; zero additional release points agrees with DB. |
| `test_karma_later_release_log_story_reject` | Capture S30’s wrong-owner rejection; no award-success beat or new history/award. |
| `test_later_major_with_browser_release_omits_second_award_message` | Actual first and second release modal interactions reach v1.0/v2.0; initial earned message present, later earned message absent; fresh Product page shows Nora 5,000; ledger count remains one. |

All database tests use real objects/services; no patched domain service, provider double or mocked ORM. Shared assertions must compare persisted fields, not fixture oracle totals alone.

Backend gate:
```bash
pytest tests/integration/test_experts_release_later_versions.py tests/integration/test_experts_release_later_log_story.py tests/integration/test_playbook_release.py tests/integration/test_admin_revert.py tests/integration/test_pip_admin_review_view.py -x
```
Log gate:
```bash
pytest tests/integration/test_experts_release_later_log_story.py -x
```
Browser gate, kept separate from backend/log capture:
```bash
E2E_LIVE_SERVER_SCOPE=function pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_release_later_versions.py -x
```
Living-spec gates:
```bash
make test-at-harness
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance .venv/bin/python manage.py behave --simple --tags=@experts --name='^KARMA-RELEASE-02 Do not repeat the first-release award on later versions$' docs/features/act-18-experts/karma-accrual.feature
```
Require one executed/passed scenario and four executed/passed steps including Background, zero undefined/skipped. Explicit `@experts` selection includes this named contract despite feature-level `@wip`. After parent-controlled tag reconciliation, `make test-at-experts` is the aggregate iteration gate; require S31 actually included. Never use broad legacy feature scans or zero selection as evidence.

## E — Log story script


S31 consumes S30-owned logs; it adds no production logging surface.

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `PlaybookService.release_playbook_with_award` | entry | Later owner publication | `actor_id=`, `playbook_id=`, `correlation_id=` |
| Same | branch | Previously published playbook | `reason=previously_released`, `award_points=0` |
| `_release_with_karma_message` | exit | Later release response | `earned_message=false`, `playbook_id=`, `correlation_id=` |
| `PlaybookService.release_playbook_with_award` | error | Wrong owner attempts later release | safe `reason=`, `playbook_id=`, `correlation_id=` |

Use `assert_log_story` and INFO-or-higher `caplog`, clearing the initial award capture before checking later-operation absence of success. Do not assert fabricated `persist_awards` calls for ineligible publication. Existing PIP finalize/version logs are supplementary evidence, not newly promised structured beats. No raw notes, email, prompts, credentials or private content.

## F — MCP tools


Not applicable: existing web/domain release and PIP administration only. No modified facade/client registration, second MCP server or tool proof required.

## G — Agent proofs


Not applicable: deterministic ledger/lifecycle certification; no LLM, agent orchestration or SAO §17 PRF capability changes. Reviewed fixture construction avoids live Galdr entirely.

## H — Mockup graduation


Reuse existing production release controls and message renderer without template changes. S03 owns Product leaderboard graduation; S30 owns earned-message wiring. Browser selectors already exist: `open-release-modal`, `open-release-modal-released`, `release-description-input`, `release-confirm`, `alert-message`. No S31 mockup or BPE-03 implementation is required.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/karma-accrual.feature:15`; 1 expanded case(s), primary layer `at`. Dependencies: S30, S32. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-RELEASE-02
  nodes:
  - id: N1-lifecycle-certification
    title: Certify existing publication and ledger boundaries
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_release_later_log_story.py
    - tests/integration/test_experts_release_later_versions.py
    - tests/support/experts_release.py
    gate:
      command: pytest tests/integration/test_experts_release_later_versions.py tests/integration/test_experts_release_later_log_story.py
        -x
      log_story_command: pytest tests/integration/test_experts_release_later_log_story.py -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-docstring-format
      - pytest
    tests:
    - test_later_major_with_accepted_pip_preserves_first_release_award
    - test_later_major_with_normal_releases_preserves_single_award
    - test_later_major_with_staff_revert_and_release_preserves_single_award
    - test_later_major_with_imported_release_marker_preserves_history
    - test_later_major_with_changed_author_preserves_original_recipient
    - test_later_major_with_denied_operations_preserves_version_and_award
    - test_karma_later_release_log_story_happy
    - test_karma_later_release_log_story_reject
  - id: N2-living-spec
    title: Bind the exact next-major acceptance contract
    bpe: BPE-04
    depends_on:
    - N1-lifecycle-certification
    footprint:
    - docs/features/steps/experts_karma_release_later_steps.py
    gate:
      command: make test-experts-s31-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
  - id: N3-browser
    title: Certify later publication without a repeated earned message
    bpe: BPE-05
    depends_on:
    - N2-living-spec
    footprint:
    - tests/e2e/test_experts_release_later_versions.py
    gate:
      command: make test-experts-s31-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
      - pytest
  - id: N4-dod
    title: Verify certification and existing release regressions
    bpe: BPE-06
    depends_on:
    - N3-browser
    footprint: []
    gate:
      command: make test-experts-s31
      log_story_command: pytest tests/integration/test_experts_release_later_log_story.py -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-assert-log-story
      - do-github-issues
      - pytest
  scenario_dependencies:
  - S30
  - S32
```

## Lessons Learned

- Existing staff playbook revert differs from PIP withdrawal; confusing them would invent unsupported operations and permissions.
- Normal repeated release is intentional publication, whereas S45 receipt replay is retry handling; both must retain first-release uniqueness.
- Real first-release setup is essential: a fabricated “already awarded” row would miss S30 integration failures.
- Reviewed-state fixture setup isolates finalization certification without introducing provider, summary or S32 dependencies.
- Root pytest excludes E2E; browser certification requires its own configuration and function-scoped live server.
- Read-only planning only: no files written, tests executed, commits made, issues posted or implementation success claimed.

## Structural application evidence

`docs/experts-replay/pin-evidence/S31.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.

## Actual structural footprint

`docs/experts-replay/pin-evidence/S31.json`, `docs/features/steps/experts_karma_release_later_steps.py`, `docs/plans/iterations/experts/S31-karma-release-02.md`, `tests/e2e/test_experts_release_later_versions.py`, `tests/integration/test_experts_release_later_log_story.py`, `tests/integration/test_experts_release_later_versions.py`, `tests/support/experts_release.py`

Skeleton: `72a9002019b629159e666c2fac9033b2e285222b`; shared reconciliation: `39d598328d438d09723b6eb14574fbf92fab71c9`. Semantic and physical-file dependencies are recorded separately in the iteration manifest. Context-map line ranges record the workers’ inspection baseline; headers and the final scaffold remain authoritative.
