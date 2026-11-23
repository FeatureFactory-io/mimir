# Experts architecture and test prerequisites

Parent authorization: execute the approved Experts replay through ESM, PIN and
BPE/MIN. This prerequisite plan supplies the test assets the selected checkout
lacks; it adds no product feature beyond the contracted Experts behavior.

## Ordered work and dependencies

1. Record the architecture delta in SAO: immutable award ledger/projections,
   public evidence boundary, successful-copy notification, and a bounded
   contribution-summary completion with a provider-neutral port.
2. Bootstrap TFK support: typed LLM port, CAP-004 ordered ScriptedLLM and shared
   agent trace assertion, with failing tests before implementations. Retain the
   existing log-story helper. No production summary/award behavior is filled.
3. Configure scoped living-spec AT execution and catalogs using the Django test
   client. Preserve existing pytest and Playwright runners and CI. A health
   smoke scenario proves the new harness; old narrative feature files are not
   silently declared executable. Experts' missing domain bindings stay pending.
4. Record actual prerequisite checks, then PIN-01/02 and parallel per-scenario
   planning. Apply only unimplemented structural skeletons sequentially.
5. Publish the concrete manifest/issues and obtain PIN-05 GO before feature
   behavior or implementation-test bodies are filled. Merge/release remain
   their own real human gates.

## Footprints and convergence

Architecture: `docs/architecture/SAO.md`. Test support:
`methodology/llm/base.py`, `tests/support/scripted_llm.py`,
`tests/support/agent_story.py`, focused support tests, `behave.ini`,
`docs/features/environment.py`, `docs/features/steps/`, `CATALOG.md`, fixture
catalog, a scoped harness smoke feature, requirements and Makefile targets.
No cloud, credentials, production datastore, general CI redesign, external
message, merge or release is part of these prerequisites.

Run support tests and one real Django-client AT health scenario; check existing
mockup gating and test configuration remain valid. Keep AT browser-free; keep
E2E separate. Only ScriptedLLM substitutes for the model in future integration
proofs. The feature adapter and scoring/summary/provider behavior remain PIN/BPE
deliverables. Catalog every implemented primitive and every pending binding.
