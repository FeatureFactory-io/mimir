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
