# Fixture and proof-support catalog

| Asset | Kind and scope | State |
| --- | --- | --- |
| `e2e_seed.json` | Existing real Django users/entities; loaded by `tests/conftest.py` and E2E setup | Existing; retain |
| `journey_seed.json`, `playbooks_seed.json` | Existing scenario data; inspect each test's explicit loading | Existing; retain |
| `test-data/experts/cedar-rfp-01.json` | Fictional domain oracle: people, public/private records, exact awards, event resets and viewports | Contract only; no ORM adapter yet |
| `tests/support/scripted_llm.py:ScriptedLLM` | CAP-004 finite model-response queue for real orchestrator integration | Implemented; 17 support checks cover it and agent-story helper |
| `tests/support/agent_story.py:assert_agent_story` | Control-plane trace identity/beats, non-vacuous fragment requirements | Implemented helper; feature proof pending |
| `tests/support/log_story.py:assert_log_story` | Existing log-record assertions, distinct from control-plane trace assertions | Existing; retain |
| `tests/e2e/e2e_helpers.py:login` | Actual browser authentication | Existing; reuse |

Pytest fixtures are discovered through the existing `tests/conftest.py`; E2E adds
its scoped `conftest.py`. Support utilities are explicit imports, not automatic
fixtures. Behave has its own lifecycle in `docs/features/environment.py`; it
does not automatically discover pytest fixtures.

The Cedar adapter must create real objects in the runner-owned test DB or the
ownership-checked local demonstration DB. It must not write to the tracked seed,
an idle environment, or production. Import historical awards with stable event
identities rather than replaying historical user actions through live hooks.
Each independent EV case resets the oracle; baseline 8,200 must not silently
include the previous case's +5. Public/private sentinels and zero/tie/sixth-rank
people are mandatory. Catalog the adapter and reset command when implemented.

Agent proofs must exercise real orchestration, prompt building, public-evidence
queries, persistence and trace emission with ScriptedLLM as the sole substituted
model. A canned paragraph rendered by a prototype is not an agent proof or a
live-provider result. No feature proof is marked passed by the helper tests.

## Experts replay planning registration

Status: planned, unimplemented. No green acceptance or fixture import is claimed.

| PIN | Contract | Authoritative source | Primary layer | Cases | Gate |
|---|---|---|---|---:|---|
| S01 | EXPERTS-LIST-01 | `docs/features/act-18-experts/experts-list.feature:9` | at | 1 | `make test-experts-s01` |
| S02 | EXPERTS-LIST-02 | `docs/features/act-18-experts/experts-list.feature:17` | at | 1 | `make test-experts-s02` |
| S03 | EXPERTS-LIST-03 | `docs/features/act-18-experts/experts-list.feature:25` | at | 1 | `make test-experts-s03` |
| S04 | EXPERTS-LIST-04 | `docs/features/act-18-experts/experts-list.feature:41` | at | 1 | `make test-experts-s04` |
| S05 | EXPERTS-LIST-05 | `docs/features/act-18-experts/experts-list.feature:48` | at | 1 | `make test-experts-s05` |
| S06 | EXPERTS-LIST-06 | `docs/features/act-18-experts/experts-list.feature:54` | at | 1 | `make test-experts-s06` |
| S07 | EXPERTS-LIST-07 | `docs/features/act-18-experts/experts-list.feature:59` | at | 1 | `make test-experts-s07` |
| S08 | EXPERTS-LIST-08 | `docs/features/act-18-experts/experts-list.feature:66` | at | 1 | `make test-experts-s08` |
| S09 | EXPERTS-LIST-09 | `docs/features/act-18-experts/experts-list.feature:71` | at | 1 | `make test-experts-s09` |
| S10 | EXPERTS-PROFILE-01 | `docs/features/act-18-experts/experts-profile.feature:7` | at | 1 | `make test-experts-s10` |
| S11 | EXPERTS-PROFILE-02 | `tests/e2e/experts-interactions.feature:9` | e2e | 1 | `make test-experts-s11` |
| S12 | EXPERTS-PROFILE-03 | `docs/features/act-18-experts/experts-profile.feature:15` | at | 1 | `make test-experts-s12` |
| S13 | EXPERTS-PROFILE-04 | `docs/features/act-18-experts/experts-profile.feature:21` | at | 1 | `make test-experts-s13` |
| S14 | EXPERTS-REACH-01 | `docs/features/act-18-experts/experts-reach-out.feature:8` | at | 1 | `make test-experts-s14` |
| S15 | EXPERTS-REACH-02 | `tests/e2e/experts-interactions.feature:21` | e2e | 1 | `make test-experts-s15` |
| S16 | EXPERTS-REACH-03 | `docs/features/act-18-experts/experts-reach-out.feature:14` | at | 1 | `make test-experts-s16` |
| S17 | EXPERTS-VIEW-01 | `docs/features/act-18-experts/experts-view.feature:8` | at | 1 | `make test-experts-s17` |
| S18 | EXPERTS-VIEW-02 | `docs/features/act-18-experts/experts-view.feature:16` | at | 1 | `make test-experts-s18` |
| S19 | EXPERTS-VIEW-03 | `docs/features/act-18-experts/experts-view.feature:22` | at | 1 | `make test-experts-s19` |
| S20 | EXPERTS-VIEW-04 | `docs/features/act-18-experts/experts-view.feature:28` | at | 1 | `make test-experts-s20` |
| S21 | EXPERTS-VIEW-05 | `docs/features/act-18-experts/experts-view.feature:35` | at | 2 | `make test-experts-s21` |
| S22 | EXPERTS-VIEW-06 | `docs/features/act-18-experts/experts-view.feature:43` | at | 1 | `make test-experts-s22` |
| S23 | GALDR-SUMMARY-01 | `docs/features/act-18-experts/galdr-contribution-summary.feature:8` | at | 1 | `make test-experts-s23` |
| S24 | GALDR-SUMMARY-02 | `tests/e2e/experts-interactions.feature:30` | e2e | 1 | `make test-experts-s24` |
| S25 | GALDR-SUMMARY-03 | `docs/features/act-18-experts/galdr-contribution-summary.feature:17` | at | 1 | `make test-experts-s25` |
| S26 | GALDR-SUMMARY-04 | `docs/features/act-18-experts/galdr-contribution-summary.feature:23` | at | 1 | `make test-experts-s26` |
| S27 | GALDR-SUMMARY-05 | `docs/features/act-18-experts/galdr-contribution-summary.feature:29` | at | 1 | `make test-experts-s27` |
| S28 | GALDR-SUMMARY-06 | `docs/features/act-18-experts/galdr-contribution-summary.feature:36` | at | 1 | `make test-experts-s28` |
| S29 | GALDR-SUMMARY-07 | `docs/features/act-18-experts/galdr-contribution-summary.feature:43` | at | 1 | `make test-experts-s29` |
| S30 | KARMA-RELEASE-01 | `docs/features/act-18-experts/karma-accrual.feature:8` | at | 1 | `make test-experts-s30` |
| S31 | KARMA-RELEASE-02 | `docs/features/act-18-experts/karma-accrual.feature:15` | at | 1 | `make test-experts-s31` |
| S32 | KARMA-PIP-01 | `docs/features/act-18-experts/karma-accrual.feature:20` | at | 3 | `make test-experts-s32` |
| S33 | KARMA-PIP-02 | `docs/features/act-18-experts/karma-accrual.feature:32` | at | 20 | `make test-experts-s33` |
| S34 | KARMA-PIP-03 | `docs/features/act-18-experts/karma-accrual.feature:59` | at | 1 | `make test-experts-s34` |
| S35 | KARMA-PIP-04 | `docs/features/act-18-experts/karma-accrual.feature:64` | at | 1 | `make test-experts-s35` |
| S36 | KARMA-COPY-01 | `tests/e2e/experts-interactions.feature:37` | e2e | 1 | `make test-experts-s36` |
| S37 | KARMA-COPY-02 | `tests/e2e/experts-interactions.feature:45` | e2e | 1 | `make test-experts-s37` |
| S38 | KARMA-COPY-03 | `tests/e2e/experts-interactions.feature:53` | e2e | 1 | `make test-experts-s38` |
| S39 | KARMA-MCP-01 | `docs/features/act-18-experts/karma-accrual.feature:68` | at | 9 | `make test-experts-s39` |
| S40 | KARMA-MCP-03 | `docs/features/act-18-experts/karma-accrual.feature:88` | at | 10 | `make test-experts-s40` |
| S41 | KARMA-MCP-02 | `docs/features/act-18-experts/karma-accrual.feature:108` | at | 1 | `make test-experts-s41` |
| S42 | KARMA-EXPORT-01 | `docs/features/act-18-experts/karma-accrual.feature:113` | at | 1 | `make test-experts-s42` |
| S43 | KARMA-EXPORT-02 | `docs/features/act-18-experts/karma-accrual.feature:120` | at | 1 | `make test-experts-s43` |
| S44 | KARMA-EXPORT-03 | `docs/features/act-18-experts/karma-accrual.feature:125` | at | 1 | `make test-experts-s44` |
| S45 | KARMA-EVENT-01 | `docs/features/act-18-experts/karma-accrual.feature:130` | at | 1 | `make test-experts-s45` |
| S46 | KARMA-EVENT-02 | `docs/features/act-18-experts/karma-accrual.feature:137` | at | 1 | `make test-experts-s46` |
| S47 | KARMA-CATEGORY-01 | `docs/features/act-18-experts/karma-accrual.feature:141` | at | 2 | `make test-experts-s47` |
| S48 | FOB-NAV-EXPERTS-01 | `docs/features/act-0-auth/experts-navigation.feature:8` | at | 1 | `make test-experts-s48` |
| S49 | FOB-NAV-EXPERTS-02 | `docs/features/act-0-auth/experts-navigation.feature:16` | at | 1 | `make test-experts-s49` |

Shared Cedar data: `test-data/experts/cedar-rfp-01.json`; adapter `tests/support/experts_data.py`, runner-owned or verified demo DB only. Five journey/viewport and four manual UAT contracts remain separately mapped in `docs/plans/iterations/pin-convergence-20261123-experts.md`.
