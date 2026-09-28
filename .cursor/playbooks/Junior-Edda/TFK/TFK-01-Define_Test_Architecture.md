# Activity: Define Test Architecture

**Activity ID**: 187
**Order**: 1
**Phase**: Inception
**Dependencies**: Successor: Activity 188 (Bootstrap Test Harness)

## Description

Define Test Architecture

## Guidance

# Define Test Architecture

## Objective

Consume DTA-06 "Define Test Strategy" decisions (already seeded into `docs/architecture/SAO.md` § Test Strategy) and **flesh out** that SAO section with the project's Test Trophy model, runner mapping, coverage policy, directory layout, and zero-bug / zero-length-feedback workflow.

**Authoritative output:** update `docs/architecture/SAO.md` § Test Strategy. Do **not** treat a separate Test Architecture Document as the source of truth. A thin local pointer file (e.g. `docs/architecture/test-architecture.md` linking to SAO §5) is allowed for navigation only.

**Handoff:** DTA-06 / DTA-18 write motivators and broad strokes. TFK-01 (run before BPE) completes directory layout, AT/E2E runner paths, and quality gates so construction can execute against a finished Test Strategy section.

---

## Decisions to Flesh Out in SAO.md

### 1. Test Trophy (not Pyramid)

Our model is the **Test Trophy** — integration tests are the main bet:

| Level | Weight | Runner | What it proves |
|-------|--------|--------|----------------|
| Unit | Thin | pytest | Custom queryset logic, pure utility functions, business logic methods — only where isolation adds value. Do NOT test default Model CRUD, auto-generated views, or framework behavior. |
| Integration | **Thick** | pytest | Feature works end-to-end with real DB, real services, real connections. **No mocking.** Think of them as acceptance tests minus the GUI. |
| Acceptance (AT) | Medium | behave-django | `.feature` scenarios in `docs/features/` executed against the app via Django test client. Steps from the TFK Step Library. BDD-grade executable requirements. |
| E2E | Selective | behave + Playwright | Full user journey in `tests/e2e/`. Sequential, slow, runs on staging before release. Screenshots for visual verification. |

### 2. Why Test Trophy over Pyramid

- Unit tests are limited: testing `model.save()` returns OK tells us nothing about whether data actually persisted
- Acceptance tests with a real browser are expensive: slow, flaky
- Integration tests hit the sweet spot: real thing, no GUI overhead, fast enough for CI
- AT tests are integration tests with BDD syntax — the `.feature` file IS the requirements document made executable

### 3. Runner Mapping

- **pytest**: everything up to and including integration tests
- **behave-django** (`make test-at`): acceptance tests — `docs/features/` (spec + runner; Django test client; `tags = ~@wip`)
- **behave + Playwright** (`make test-e2e`): E2E tests — `tests/e2e/` (LiveServer + browser; own `environment.py`)

### 4. Coverage Policy

- Coverage metrics are necessary but not sufficient
- **Coverage is meaningless without quality** — 90% coverage with useless tests is worse than 60% with real tests
- Quality gates: no mocking in integration tests, no testing framework behavior, no tests > 10 lines without extraction
- `@wip` scenarios excluded from CI; all other `docs/features/` scenarios must pass AT before merge

### 5. Zero-Bug and Zero-Length Feedback

Document in SAO: bug = failing integration/AT scenario; fix same day with a permanent regression test; continuous pytest feedback via `tests.log`.

### 6. Agent test lanes

When SAO §17 (AI Agent Architecture) applies — i.e. the project has agent workflows, tool registries, or LLM orchestration — extend the Test Strategy with a **four-lane agent eval model**. When SAO §17 is **N/A** (no agents), skip this subsection entirely; lanes 3–4 and agent Makefile targets are optional no-ops (see TFK-05).

**Four lanes:**

| Lane | Name | Runner | What it proves |
|------|------|--------|----------------|
| 1 | Control-plane proofs | pytest `@agent_proof` + CAP-004 ScriptedLLM | Orchestration: workflow id, tools offered/called, domain writes, plan/blackboard transitions — **not** model quality |
| 2 | Deterministic shell | pytest integration (no LLM) | D0 prefilter, JSON parse, validate-before-LLM, schema bounds — pure code paths |
| 3 | Live contract eval | pytest `@live_llm` (nightly / optional CD) | Provider contracts at temp=0: response shape, tool-call envelope, rate-limit handling |
| 4 | Task performance quality | pytest `@quality` (promotion band) | Frozen TASK-* golden tasks: structured oracle (recall, graph diff, schema bounds) |

**Gate matrix (CI stage vs lane):**

| Lane | PR merge (`ci.yml`) | Nightly (`agent-eval.yml`) | Promotion / release |
|------|---------------------|----------------------------|---------------------|
| 1 | ✅ when `AGENTS_ENABLED=true` — `make test-agent-proof` | — | — |
| 2 | ✅ normal integration job (`make test-integration`) | — | — |
| 3 | ❌ not a PR gate | ✅ scheduled / `workflow_dispatch` | Optional CD cert when `AGENT_EVAL_ENABLED=true` |
| 4 | ❌ not a PR gate | Optional regression run | ✅ vs last certified pass band before promote |

**PRF vs TASK (artifact 56):**

| Artifact row | Lane | Assert helper | Fixture root |
|--------------|------|---------------|--------------|
| **PRF-*** (integration proof) | 1 (+ lane 2 for non-LLM steps) | `assert_agent_story(trace, …)` | `tests/fixtures/llm_scripts/<prf-id>/` |
| **TASK-*** (golden task) | 4 | structured oracle + optional domain asserts | `tests/fixtures/agent_tasks/<task-id>/` |

PRF rows prove **control plane** under scripted LLM turns; TASK rows prove **outcome quality** under live (or promoted) models. Do not use lane 4 to prove 429 retry or HITL gates — those belong in PRF lane 1.

**Skip when SAO §17 N/A:** If the project has no agent architecture section, do not add lane Makefile targets to required CI, do not block BPE/MIN on `agent_proof_command`, and do not create empty `llm_scripts/` / `agent_tasks/` trees. Artifact 11–13 templates add capability, not mandate.

Document in SAO § Test Strategy: which PRF-* and TASK-* rows are in scope for this release, lane assignment, and `AGENTS_ENABLED` / `AGENT_EVAL_ENABLED` env conventions.

---

## Deliverables

- ✅ **SAO.md § Test Strategy** fleshed out (Trophy, runners, paths, coverage, zero-bug, zero-length feedback)
- ✅ **SAO.md § Test Strategy § Agent lanes** (when §17 applies): four-lane table, gate matrix, PRF vs TASK mapping, skip rules
- ✅ Ready for TFK-02 Bootstrap Test Harness and BPE

## Agent

None

## Skill

**Title**: Test Trophy Architecture
**Capability Domain**: Test Strategy & Design
**Technology Stack**: testing-trophy, integration-testing

## Rules

None

## Artifacts Produced

- **SAO.md § Test Strategy** (Document) - Optional

## Artifacts Consumed

None

## Notes

No additional notes.
