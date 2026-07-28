# {Project Name}: System Architecture Overview

## Executive Summary
- System purpose (1-2 sentences)
- Key architectural decisions (bullet list of the most impactful choices)

## 1. Application Blocks
<!-- Decision from DTA-02 -->
### Bounded Contexts / Domain Packages
- List domain packages with responsibilities

### Module Dependency Rules
- Dependency direction diagram or rules

### Foundational Architectural Pattern
- **Chosen**: {pattern}
- **Rationale**: Why this pattern over alternatives

### UI Architecture Patterns (if applicable)
- **Rendering model**: {server-rendered | SPA | hybrid} — rationale
- **Layout pattern**: {single-panel | multi-panel | wizard} — rationale
- **Component interaction model**: {full reload | partial updates | client-side state} — rationale
- **Visualization approach**: {server-generated | client-rendered | hybrid} — rationale

## 2. Integration & API Design
<!-- Decision from DTA-03 -->
### API Style
- **Chosen**: {style}
- **Rationale**: Why this style

### Versioning Strategy
- **Chosen**: {strategy}

### Contract Approach
- **Chosen**: {approach}

### External Integrations
- List 3rd party APIs, webhook patterns, retry policies

### Inter-Service Communication
- **Chosen**: {model}
- **Rationale**: Why this model

### Implementation Patterns
<!-- Populated during/after implementation -->
- Service-to-transport mapping:
- Sync/async boundary:
- Protocol-specific constraints:
- Shared service layer:
- Error propagation:

## 3. Code Organization
<!-- Decision from DTA-04 -->

## 4. Data Architecture
<!-- Decision from DTA-05 -->

## 5. Test Strategy
<!-- Decision from DTA-06 -->

## 6. Performance & Scalability
<!-- Decision from DTA-07 -->

## 7. Error Handling & Resilience
<!-- Decision from DTA-08 -->

## 8. Infrastructure
<!-- Decision from DTA-09 -->

## 9. CI/CD Pipeline
<!-- Decision from DTA-10 -->

## 10. Release & Rollback
<!-- Decision from DTA-11 -->

## 11. Observability
<!-- Decision from DTA-12 -->

## 12. Config & Secrets
<!-- Decision from DTA-13 -->

## 13. Security
<!-- Decision from DTA-14 -->

## 14. Backup & Recovery
<!-- Decision from DTA-15 -->

## 15. Developer Experience
<!-- Decision from DTA-16 -->

## 16. Documentation Strategy
<!-- Decision from DTA-17 -->

## 17. AI Agent Architecture
<!-- Decision from DTA-19 — omit this section if no in-app agent -->
<!--
Skip condition: write "Not applicable — no in-app LLM agent." and remove the subsections below
if DTA-19 was not run.
Reference: Playbook artifact AI Agent Reference Architecture — Parts 1–5 and Part 4 capability appendix
-->

### Infra layer (Part 1 · Component 1)

| Setting | Value |
|---------|-------|
| LLM provider | |
| Ollama host / model (if applicable) | |
| API key storage | server env / secret manager |
| Celery broker URL (if CAP-060) | |
| Celery result backend | |
| LLM readiness health check | Yes / No |

### Vector tier (Part 1 · Component 3)

| Decision | Value |
|----------|-------|
| Vector store used | Yes / No |
| Backend | pgvector / dedicated / in-process |
| Embedding model | |
| CAP-090 search_knowledge | Yes / No |
| CAP-094 reference library | Yes / No |

### Design pattern & scenario selection

<!-- Read Part 2 patterns in the AI Agent Reference Architecture before ticking -->

| SC-ID | Pattern | Name | Selected? | Rationale |
|-------|---------|------|-----------|-----------|
| SC-01 | 4 | Conversational planner | | |
| SC-02 | 2 | Field extractor / batch ingest | | |
| SC-03 | 7 | Compiled pipeline | | |
| SC-04 | 3 | Event-driven nudge | | |
| SC-05 | 5 | Governed mutations | | |

### Serving mode (Part 3)

| Mode | Selected? | Notes |
|------|-----------|-------|
| Real-time (3.1) — sync chat, streaming | | CAP-040, CAP-003, CAP-100 |
| Batch / queue (3.2) — worker, CI ingest | | CAP-060–066 |
| Observability for serving (3.3) | | CAP-101, CAP-100 events |

### Dual execution path (Pattern 4 / SC-01)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Context snapshot in chat (CAP-037) | | |
| Snapshot invalidation (CAP-038) | | |
| Mutation-only conversation tools (CAP-039) | | |
| Full tools in worker only | | |

### Memory tiers (Part 1 · Component 5)

| Tier | CAP-IDs | Selected? | Rationale |
|------|---------|-----------|-----------|
| 1 Hot snapshot | 037–039 | | |
| 2 Semantic search | 091 | | |
| 3 AI profile | 092 | | |
| 4 Reference library | 094, 090 | | |
| 5 Entity notes | 093 | | |

### Capability checklist

<!-- Copy CAP rows from Part 4.1 for every CAP implemented -->

| CAP-ID | Name | Implement? | Project module path |
|--------|------|--------------|---------------------|
| CAP-001 | LLM Port protocol | | |
| CAP-004 | ScriptedLLM | | |
| CAP-037 | Context snapshot hydration | | |
| CAP-038 | Snapshot invalidation hooks | | |
| CAP-039 | Dual tool exposure | | |
| CAP-091 | Semantic context search | | |
| CAP-101 | Agent interaction trace | | |
| | | | |

### Assembly template

- **Template**: {T-01 Planner | T-02 Field | T-03 Pipeline | T-00 Custom}
- **Custom CAP list** (if T-00): CAP-___ , CAP-___ , …

### Agent identities (CAP-121 / CAP-122)

| Identity | Role | Model tier | Allowed tools |
|----------|------|------------|---------------|
| | | planning / execution / field | |

### Agent Blackboard (if CAP-070 selected)

| Key | Role | Durability |
|-----|------|-----------|
| | | |

- Durability tier: {A — in-process | B — run-persistent}
- Max board size (chars): ______

### Plan & Steps (if CAP-050 selected)

- States: `pending → running → completed | failed | waiting_retry`
- Hybrid step flags in use: {is_critical, is_planning, is_variable_assessment, data-only}
- Worker uses LLM per step (CAP-054) — not mechanical tool-only execution

### Worker failure bridge (if CAP-060 selected)

- [ ] CAP-100 plan_failed event and/or chat context injection on worker failure
- [ ] PRF-SC01-07 mapped to integration test file

### Observability (Part 1 · Component 6 / CAP-101)

| Field | Value |
|-------|-------|
| correlation_id header | |
| Cost rate table location | |
| PRF-OBS-01 test file | |

### Integration proof (DoD gate)

<!-- Map PRF-SCxx-xx test IDs from Part 4.5 -->

| PRF ID | Scenario | Test file |
|--------|----------|-----------|
| PRF-SC02-01 | SC-02 thinking JSON | |
| PRF-SC02-02 | SC-02 parse fail loud | |
| PRF-SC02-03 | SC-02 domain D0 pre-filter | |
| PRF-SC02-04 | SC-02 D1 parse fail loud | |
| PRF-SC01-01 | SC-01 plan handoff | |
| PRF-SC01-02 | SC-01 429 retry | |
| PRF-SC01-03 | SC-01 blackboard retain | |
| PRF-SC01-04 | SC-01 dual tool exposure | |
| PRF-SC01-05 | SC-01 snapshot invalidation | |
| PRF-SC01-06 | SC-01 no mechanical worker | |
| PRF-SC01-07 | SC-01 worker failure bridge | |
| PRF-OBS-01 | all — correlation + usage trace | |
| PRF-SC05-01 | SC-05 HITL | |
| PRF-SC05-02 | SC-02+05 full rescan invariants | |

### SC-02 × SC-05 full rescan (if batch ingest replaces snapshot)

Complete when **both** SC-02 and SC-05 are selected:

- [ ] Rescan delete ops meet auto-apply confidence threshold (or rescan disables partial auto-apply)
- [ ] ChangeSet apply ordering: deletes → updates → adds when rescan flag is set
- [ ] PRF-SC05-02 mapped to integration test file

## 18. MCP Architecture
<!-- Decision from DTA-20 — omit this section if no MCP interface -->
<!--
Skip condition: write "Not applicable — no MCP interface." and remove the subsections below
if DTA-20 was not run.
Reference: Playbook artifact MCP FastMCP Reference Architecture
-->

### Integration Case

- **Chosen**: {Case A — Service Bridge | Case B — API Facade | Hybrid}
- **Rationale**: _____

### Transport Topology

| Target | Transport | Port / Path | Notes |
|--------|-----------|------------|-------|
| Local IDE | stdio | n/a | |
| Remote AI clients | HTTP+SSE | | |

### Tool Inventory

| Tool name | Service method | Write? | HITL? | Case |
|-----------|---------------|--------|-------|------|
| | | | | |

- Write-tool policy: {Require explicit confirmation param | HITL prompt before execute | Audit log only}

### Auth Pattern

- **Selected**: {Process user | PAT per call | Session cookie | Mixed}
- **PAT injection point**: {Tool argument | HTTP header (Bearer)}
- **Rationale**: _____

### Stdout Hygiene (if stdio)

- Logging redirected to stderr / file: {Yes | N/A}
- Third-party stdout suppressed: {Yes | N/A}
- Boot noise test added: {Yes | N/A}

### API Readiness Contract (if Case B)

| Tool | HTTP endpoint | Method | Auth header |
|------|--------------|--------|-------------|
| | | | |

## Technology Stack Table

Machine-readable table consumed by Bootstrap Project (BSP) for automated provisioning.

| Layer | Tool | Version | Install Command (macOS) | Install Command (Linux) | Verify Command |
|-------|------|---------|-------------------------|-------------------------|----------------|
| ...   | ...  | ...     | ...                     | ...                     | ...            |

> **Note**: Each row must have install + verify commands so BSP can automate provisioning.

## Skill Coverage Report

| Domain | Covered Skills | Gaps |
|--------|---------------|------|
| Application Blocks | | |
| Integration & API | | |
| Code Organization | | |
| Data Architecture | | |
| Test Strategy | | |
| Performance & Scalability | | |
| Error Handling & Resilience | | |
| Infrastructure | | |
| CI/CD Pipeline | | |
| Release & Rollback | | |
| Observability | | |
| Config & Secrets | | |
| Security | | |
| Backup & Recovery | | |
| Developer Experience | | |
| Documentation Strategy | | |
| AI Agent Architecture | | |
| MCP Architecture | | |

## Key Decisions with Rationale

| # | Domain | Decision | Rationale |
|---|--------|----------|-----------|
| 1 | | | |

## Discovered Patterns & Lessons Learned
<!-- Reserved section — populated during and after implementation -->

### Critical Discoveries

<!-- For each significant discovery during implementation: -->
<!--
#### Discovery: {title}
- **Context**: What was being built/integrated
- **Problem**: What didn't work as expected
- **Solution**: The pattern/workaround adopted
- **Key Lessons**:
  1. ...
-->

### Retrospective Updates

<!-- Track SAO sections updated post-implementation: -->
<!--
| Section | Original Decision | What Changed | Updated Decision |
|---------|-------------------|--------------|------------------|
| | | | |
-->
