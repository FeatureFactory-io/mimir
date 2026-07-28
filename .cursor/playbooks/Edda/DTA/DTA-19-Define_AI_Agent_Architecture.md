# Activity: Define AI Agent Architecture

**Activity ID**: 200
**Order**: 19
**Phase**: Inception
**Dependencies**: Predecessor: Activity 58 (Define Documentation Strategy)
Successor: Activity 201 (Define MCP Architecture)

## Description

Define AI Agent Architecture

## Guidance

# Define AI Agent Architecture

**Condition:** Run only if the system has in-app LLM agents (agentic loops, plan/worker execution, or LLM calls inside the application). Skip and write "Not applicable" in SAO §17 if none of: in-app agentic loop, LLM calls initiated by the app, plan/worker execution.

**Reference:** Playbook artifact **AI Agent Reference Architecture** (latest released Edda version).

## Objective

Confirm components (Part 1), pick design patterns and scenarios (Part 2), choose serving mode (Part 3), select capabilities (`CAP-xxx`), choose an assembly template, and record decisions in SAO §17.

## Process

1. **Fetch** the latest **AI Agent Reference Architecture** from the playbook.
2. Read **How to use this document** and **Part 1 — Components**; complete infra, model, vector (if needed), framework, memory, and observability checklist in SAO §17.
3. Pick **Part 2 — Design patterns** and primary **SC-xx** scenario(s); use **Part 5 — Quick reference** for secondary CAP additions.
4. Choose **Part 3 — Serving mode** (real-time, batch/queue, or both).
5. Copy required + chosen optional **CAP-IDs** into SAO §17 from **Part 4.1 Capability table**.
6. Confirm dependencies in **Part 4.3 Module wiring**.
7. Note starting assembly template from **Part 4.4** (T-01, T-02, T-03, or T-00 custom).
8. Name integration proof test IDs (`PRF-SCxx-xx`, `PRF-OBS-01`) from **Part 4.5** as DoD gate.
9. If **both** SC-02 and SC-05 are selected, read **Pattern 5 · SC-02 × SC-05 · Full rescan invariants** and record checklist in SAO §17.
10. If Pattern 4 / SC-01 with large domain state, decide dual execution path (CAP-037, CAP-038, CAP-039) and memory tiers (Component 5 / CAP-091–094).
11. Record Pattern 4 anti-pattern checklist (mechanical step execution; worker failure bridge) when CAP-060 selected.
12. Record decisions for SAO §17 via Write SAO.md (Activity 59).

## Decisions to Make

### 1. Infra layer (Component 1)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM provider | anthropic / openai / ollama / … | |
| Ollama readiness probe at startup | Yes / No / N/A | |
| Broker + result backend (CAP-060) | Configured / N/A | |
| Secrets server-side only | Yes | |

### 2. Vector tier (Component 3)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Vector store needed | Yes / No | |
| Backend | pgvector / dedicated / in-process | |
| CAP-090 / CAP-094 selected | Yes / No | |

### 3. Design pattern & scenario selection

Read **Part 2** pattern sections before ticking. Record primary scenario(s) and rationale.

| SC-ID | Pattern | Name | Selected? | Rationale |
|-------|---------|------|-----------|-----------|
| SC-01 | 4 | Conversational planner | | |
| SC-02 | 2 | Field extractor / batch ingest | | |
| SC-03 | 7 | Compiled pipeline | | |
| SC-04 | 3 | Event-driven nudge | | |
| SC-05 | 5 | Governed mutations | | |

### 4. Serving mode (Part 3)

| Mode | Selected? | CAP-IDs |
|------|-----------|---------|
| Real-time (3.1) | | CAP-040, CAP-003, CAP-100 |
| Batch / queue (3.2) | | CAP-060–066 |
| Observability for serving (3.3) | | CAP-101, CAP-100 |

### 5. Dual execution path (Pattern 4 / SC-01 with large state)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Context snapshot in chat (CAP-037) | Yes / No | |
| Snapshot invalidation on writes (CAP-038) | Yes / No | |
| Mutation-only tools in conversation (CAP-039) | Yes / No | |
| Full tool registry in plan worker only | Yes / No | |

### 6. Memory tiers (Component 5)

| Tier | CAP-IDs | Selected? | Rationale |
|------|---------|-----------|-----------|
| 1 Hot snapshot | 037, 038, 039 | | |
| 2 Semantic search | 091 | | |
| 3 AI profile | 092 | | |
| 4 Reference library | 094, 090 | | |
| 5 Entity notes | 093 | | |

### 7. Capability checklist

From **Part 4.1** — tick every CAP your project implements:

| CAP-ID | Name | Required for SC? | Implement? | Module path in project |
|--------|------|------------------|------------|------------------------|
| CAP-001 | LLM Port protocol | | | |
| CAP-037 | Context snapshot hydration | | | |
| CAP-038 | Snapshot invalidation hooks | | | |
| CAP-039 | Dual tool exposure | | | |
| CAP-091 | Semantic context search | | | |
| CAP-092 | AI-managed profile memory | | | |
| CAP-093 | Entity notes graph | | | |
| CAP-094 | Reference knowledge library | | | |
| CAP-101 | Agent interaction trace | | | |
| … | (copy remaining rows for each selected CAP) | | | |

Minimum: all **required** CAP-IDs from your selected SC-xx row in **Part 5 — Scenario index**.

### 8. Assembly template

- [ ] **T-01 Planner** (SC-01 / Pattern 4)
- [ ] **T-02 Field** (SC-02 / Pattern 2)
- [ ] **T-03 Pipeline** (SC-03)
- [ ] **T-00 Custom** — list CAP-IDs: _______________

### 9. Agent identities (CAP-121, CAP-122)

| Identity | Role | Model tier | Allowed tools |
|----------|------|------------|---------------|
| | | planning / execution / field | |

### 10. Agent Blackboard (if CAP-070 selected)

- Durability tier: A — in-process / B — run-persistent
- Schema keys: phase, hypothesis, current_plan, last_actions, next_intent
- Max board size (chars): ______

### 11. Worker anti-patterns (if CAP-060 selected)

- [ ] Worker uses LLM per step (CAP-054) — not mechanical tool script (Pattern 4 anti-patterns)
- [ ] Worker failure bridged to UI (CAP-100 plan_failed and/or chat context injection)
- [ ] PRF-SC01-06 mapped if hybrid worker is new

### 12. Observability (Component 6 / CAP-101)

- correlation_id header/name: ______
- Cost rate table location: ______
- PRF-OBS-01 test file: ______

### 13. Integration proof (DoD gate)

| PRF ID | Scenario | Test file | Selected? |
|--------|----------|-----------|-----------|
| PRF-SC02-01 | SC-02 thinking JSON | | |
| PRF-SC02-02 | SC-02 parse fail loud | | |
| PRF-SC02-03 | SC-02 domain D0 pre-filter | | |
| PRF-SC02-04 | SC-02 D1 parse fail loud | | |
| PRF-SC01-01 | SC-01 plan handoff | | |
| PRF-SC01-02 | SC-01 429 retry | | |
| PRF-SC01-03 | SC-01 blackboard retain | | |
| PRF-SC01-04 | SC-01 dual tool exposure | | |
| PRF-SC01-05 | SC-01 snapshot invalidation | | |
| PRF-SC01-06 | SC-01 no mechanical worker | | |
| PRF-SC01-07 | SC-01 worker failure bridge | | |
| PRF-SC05-01 | SC-05 HITL | | |
| PRF-SC05-02 | SC-02+05 full rescan invariants | | |
| PRF-OBS-01 | all | correlation + usage trace | | |

### 14. SC-02 × SC-05 full rescan (if both selected)

From **Pattern 5 · SC-02 × SC-05 · Full rescan invariants**:

- [ ] Rescan delete ops meet auto-apply confidence threshold (or rescan disables partial auto-apply)
- [ ] ChangeSet apply ordering: deletes → updates → adds when rescan flag is set
- [ ] PRF-SC05-02 mapped to integration test file

### 15. Scan Skills

Query Skills where `capability_domain` in: AI_AGENT, LLM_INTEGRATION, ASYNC_TASK, OBSERVABILITY. Report gaps.

## Deliverables

- Infra + vector tier decisions documented
- Primary pattern(s) and SC-xx scenario(s) chosen with rationale
- Serving mode (Part 3) selected
- Dual execution path + memory tier decisions (when Pattern 4 / SC-01)
- CAP-ID checklist complete for selected scenarios
- Assembly template (T-01 / T-02 / T-03 / T-00) named
- Agent identities + model tiers documented
- Worker anti-pattern checklist completed (when CAP-060)
- Observability trace documented (CAP-101)
- PRF test IDs mapped to project test files
- SC-02 × SC-05 rescan checklist completed (when both scenarios selected)
- Skill coverage assessed
- Decision recorded for SAO §17 via Write SAO.md (Activity 59)

## Agent

None

## Skill

None

## Rules

None

## Artifacts Produced

- **AI Agent Reference Architecture** (Document) - Optional

## Artifacts Consumed

None

## Notes

No additional notes.
