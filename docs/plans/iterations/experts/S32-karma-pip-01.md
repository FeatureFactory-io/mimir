# S32: KARMA-PIP-01 Award an accepted major ADD

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S32
acceptance_id: KARMA-PIP-01
feature_file_path: docs/features/act-18-experts/karma-accrual.feature
feature_line: 20
primary_execution_layer: at
expanded_case_count: 3
dependencies:
- S30
- S23
- S10
- S11
- S12
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 0a62bea571ea2ea1421cfb19edcaa3cd29dd7bbc27c2a61308735e542a5e9410
```

### A — Context map


| Verified source | Relevant behavior |
|---|---|
| `docs/features/act-18-experts/karma-accrual.feature:20–30` | Three independent Examples: ADD Activity, Skill, Artifact; Maria 8,700/Design 7,700; target 3.0; local notification. |
| `methodology/services/pip_admin_service.py:24–114` | Existing atomic finalization validates staff/reviewed state, applies accepted changes, bumps once, sets terminal status, and registers decision email with `on_commit`. |
| `methodology/services/pip_apply_changes_service.py:757–801` | Existing version owner creates one major PIP history row; Karma must not bump again. Actual ADD bodies require Activity parent workflow and Artifact producer reference. |
| `methodology/services/pip_notification_service.py:47–83` | Real notification addresses `pip.created_by`, renders existing template, uses `EmailService.send_text_email`, and catches mail failure. |
| `test-data/experts/cedar-rfp-01.json:971–995` | Historical Maria Design PIP already explains Hana’s 1.0→2.0 baseline and Maria’s existing 600 Design PIP points. New acceptance must not replay it. |

Additional verification: `pip_views.py:610–685` already exposes staff-only real finalization POST; `PIPService.get_pip_with_changes` retains owner/staff access. Existing email tests assert actual locmem recipients/body; existing PIP CRUD tests exercise actual Activity/Skill/Artifact application. Existing `page` and `live_server_url` fixtures are in `tests/e2e/conftest.py:112–166`.

### B — Do not do


- Do not award Hana or the administrator: accepted-change recipient is Maria, `pip.created_by`.
- Do not count ADD as “major” because the playbook version increments. Exactly ADD Activity/Skill/Artifact earns 500; other supported accepted changes earn 100.
- Do not call first-release awarding from finalization or introduce another version bump.
- Do not award before changes and terminal decision have succeeded.
- Do not move awards into the email callback: decision/content/version/awards share the database transaction; email retains existing postcommit behavior.
- Do not add ledger FKs that prevent deleting content.
- Do not bypass PIP authorization, introduce MCP tools, call a provider, or generate a summary for this acceptance.
- Do not import historical Cedar data through live event hooks.

### C — Governing architecture


Read and apply:

- **Experts & Karma delivery architecture — planned delta**
- **Awards, projections and transaction boundaries**
- **Web delivery and notification reuse**
- **Test strategy for this delta**
- **Version Management**
- **Email Architecture / PIP Decision Email Content / Testing Strategy**

The shared S03/S30 contract supplies immutable integer `playbook_id_snapshot` and `change_id_snapshot`, `event_identity`, explicit `event_channel`, `occurred_at`, and atomic validated `persist_awards(tuple[AwardSpec, ...], *, correlation_id)`.

S32 adds the accepted-change policy and wires it after `_apply_terminal_status`, before email registration, within existing `finalize_pip` atomic scope. Preserve its working body and return contract.

Pseudocode:

1. Reload and lock persisted PIP; never trust caller-mutated status/recipient/category.
2. Return no awards for nonterminal/nonaccepted proposals, missing submitter, or absent successful PIP publication history.
3. Read only persisted ACCEPT changes in stable order.
4. Reuse an existing accepted-change event’s immutable payload on retry.
5. Otherwise classify supported operation/entity/relationship; make one spec per eligible change.
6. Persist the complete immutable tuple through S30.
7. Return outcomes; leave versioning and notification ownership unchanged.

Identity: `accepted_change:<actual_change_pk>`. Channel: `accepted_change`. Timestamp: persisted `pip.decided_at`. Source kind: `major` or `minor`; category: target playbook’s category at decision time. Retry reuses recorded timestamp/category instead of recomputing from later edits.

### D — Tests and gates


| Test | Required assertions |
|---|---|
| `test_finalize_pip_with_major_add_awards_submitter_and_publishes_once` | Parameterize **Activity, Skill, Artifact**, independently restore Cedar; real admin POST; actual new entity exists; Maria 8,700/Design 7,700; Hana/admin unchanged; exactly one new 500 `major` award with correct snapshots/channel; 2.0→3.0; exactly one new PIP version row; no new first-release award; one normal local email to Maria mentioning accepted change and 3.0. |
| `test_award_accepted_changes_with_retry_preserves_original_event` | Repeated service recording returns existing award, no duplicate or increased totals; same ID/time/category; later target-category edit does not rewrite historical attribution. |
| `test_finalize_pip_with_outer_rollback_restores_content_version_decision_and_awards` | Real outer transaction deliberately rolls back after successful finalization; new content, history, terminal decision and awards all roll back; postcommit email does not send. No service mocks. |
| `test_finalize_pip_with_invalid_apply_creates_no_award_or_email` | Invalid real producer/reference makes apply fail; no committed content/version/award/notification. |
| `test_accepted_change_policy_with_unsupported_change_returns_no_award` | Unknown entity/operation/relationship never defaults to 100. |
| `test_award_accepted_changes_with_ineligible_context_returns_no_awards` | Boundary-level safe behavior for nonterminal/no accepted changes/null creator/no publication; S35 later proves complete lifecycle matrix. |
| `test_accepted_change_log_story_happy` | `caplog` + `assert_log_story` prove entry, classification, persistence and exit with safe identifiers. |
| `test_accepted_change_log_story_reject` | Prove skipped eligibility/unsupported input reason; no payload/email/token logging. |
| `test_admin_browser_with_major_add_finalization_awards_maria` | Real browser login as existing staff Mike; existing selectors `admin-decision-1`, `finalize-btn`, `confirm-finalize-btn`; actual submission produces 3.0 and expected persisted award, no repeat on revisiting decided proposal. |

Checkpoint:

```text
make test-experts-s32
```

Required log gate:

```text
pytest tests/integration/test_experts_karma_pip.py -k log_story -x
```

Exact scoped living AT target, implemented after GO:

```makefile
.PHONY: test-at-experts-s32
test-at-experts-s32:
	DJANGO_SETTINGS_MODULE=mimir.settings.acceptance $(PYTHON) manage.py behave --simple --tags=@experts --name='^KARMA-PIP-01 Award an accepted major ADD' docs/features/act-18-experts/karma-accrual.feature
```

This explicitly selects the named contract despite its feature-level `@wip`; require **three executed Examples, zero undefined/failed/skipped selected cases**. Keep aggregate `make test-at-experts` separate and report its actual remaining coverage.

Rollup target after GO:

```makefile
.PHONY: test-experts-s32
test-experts-s32:
	$(PYTEST) tests/integration/test_experts_karma_pip.py -x
	$(MAKE) test-at-experts-s32
	$(PYTEST) -o addopts= tests/e2e/test_experts_karma_pip.py -x
```

PIN may reserve these target names as comments; do not fill working recipes or assertions during skeleton apply.

### E — Log story


| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `KarmaService.award_accepted_changes` | entry | Hook/service called | `entry`, `pip_id=`, `correlation_id=` |
| `KarmaService._accepted_change_policy` | processing | Recognized accepted change | `processing`, `change_id=`, `operation=ADD`, `entity=`, `source_kind=major`, `points=500` |
| `KarmaService.award_accepted_changes` | branch | Ineligible proposal/change | `branch`, `pip_id=`, `reason=` |
| `KarmaService.award_accepted_changes` | exit | Tuple persisted/replayed | `exit`, `pip_id=`, `created_count=`, `existing_count=` |
| `PIPAdminService._award_finalized_pip` | exit | Successful transaction-local hook | `exit`, `pip_id=`, `actor_id=`, `recipient_id=` |

S30 persistence’s existing/replay/error beats remain independently covered by its own tests. Logs must not claim the surrounding transaction committed before it actually commits.

### F — MCP tools


Not applicable. Existing administrator UI/service path only. No facade registration or tool changes.

### G — Agent proofs


Not applicable. This scenario starts with a real **reviewed** PIP fixture and exercises administrator finalization. It does not test Galdr assessment or contribution-summary orchestration. No FakeLLM, ScriptedLLM, provider, tool registry or agent factory is needed here.

If implementation chooses to invoke submission/assessment instead, that expands the proof surface and must use the existing S23 CAP-004 seam with its assessment proof; prefer the independent reviewed fixture.

### H — Mockup graduation


No new production UI or template graduation. Reuse the existing administrator review page, decision controls, confirmation modal, messages and decision email template. BPE-03 is omitted. Browser certification verifies existing UI reaches the newly wired domain behavior.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/karma-accrual.feature:20`; 3 expanded case(s), primary layer `at`. Dependencies: S30, S23, S10, S11, S12. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-PIP-01
  nodes:
  - id: N1-accepted-change-policy
    title: Accepted-change policy and immutable award specifications
    bpe: BPE-02
    depends_on: []
    footprint:
    - methodology/services/karma_service.py
    - tests/integration/test_experts_karma_pip.py
    - tests/support/experts_data.py
    tests:
    - test_accepted_change_policy_with_unsupported_change_returns_no_award
    - test_award_accepted_changes_with_ineligible_context_returns_no_awards
    - test_award_accepted_changes_with_retry_preserves_original_event
    - test_accepted_change_log_story_happy
    - test_accepted_change_log_story_reject
    log_story_rows:
    - KarmaService.award_accepted_changes:entry
    - KarmaService._accepted_change_policy:processing
    - KarmaService.award_accepted_changes:branch
    - KarmaService.award_accepted_changes:exit
    gate:
      command: pytest tests/integration/test_experts_karma_pip.py -k 'policy or ineligible or retry or log_story'
        -x
      log_story_command: pytest tests/integration/test_experts_karma_pip.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-write-concise-methods
  - id: N2-finalization-hook
    title: Atomic finalization hook with existing publication and email
    bpe: BPE-02
    depends_on:
    - N1-accepted-change-policy
    footprint:
    - methodology/services/pip_admin_service.py
    - tests/integration/test_experts_karma_pip.py
    tests:
    - test_finalize_pip_with_major_add_awards_submitter_and_publishes_once
    - test_finalize_pip_with_outer_rollback_restores_content_version_decision_and_awards
    - test_finalize_pip_with_invalid_apply_creates_no_award_or_email
    - test_accepted_change_log_story_happy
    log_story_rows:
    - PIPAdminService._award_finalized_pip:exit
    gate:
      command: pytest tests/integration/test_experts_karma_pip.py -x
      log_story_command: pytest tests/integration/test_experts_karma_pip.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
  - id: N3-living-at
    title: Execute all three named outline Examples against real finalization
    bpe: BPE-04
    depends_on:
    - N2-finalization-hook
    footprint:
    - docs/features/steps/experts_karma_pip_steps.py
    gate:
      command: make test-experts-s32-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: N4-browser-finalization
    title: Certify administrator finalization in the existing browser UI
    bpe: BPE-05
    depends_on:
    - N3-living-at
    footprint:
    - tests/e2e/test_experts_karma_pip.py
    gate:
      command: make test-experts-s32-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
  - id: N5-definition-of-done
    title: Roll up behavior, log, three-example AT and browser evidence
    bpe: BPE-06
    depends_on:
    - N4-browser-finalization
    footprint: []
    gate:
      command: make test-experts-s32
      log_story_command: pytest tests/integration/test_experts_karma_pip.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-github-issues
  scenario_dependencies:
  - S30
  - S23
  - S10
  - S11
  - S12
```

## Lessons Learned

After PIN-04 issue creation and PIN-05 human GO:

1. Plan/docs handoff commit with `Refs #N`.
2. Accepted-change policy/specifications and corresponding behavior/log tests.
3. Existing atomic finalization hook and transaction/mail proofs.
4. Three-example living AT and browser certification; final passing slice `Closes #N`.

Each implementation slice requires its commit and issue update before the next slice.

Lessons learned:

- “Major ADD” describes the award category; existing administrator finalization also publishes a major version for minor edits. These policies must remain separate.
- Historical Cedar 2.0 must contain actual PIP/version/ledger records. Replaying its accepted changes would corrupt the starting totals.
- Existing EmailService is already real Django mail despite older SAO paragraphs describing a pending migration.
- Feature-level `@wip` would silently exclude this exact contract without an explicit scoped selection. Zero selected cases cannot certify it.

No files were changed, no tests were run, and no mutations were performed.

## Structural application evidence

`docs/experts-replay/pin-evidence/S32.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.
