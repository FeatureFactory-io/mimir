# Activity: Define MCP Architecture

**Activity ID**: 201
**Order**: 18
**Phase**: Inception
**Dependencies**: Predecessor: Activity 200 (Define AI Agent Architecture)
Successor: Activity 59 (Write SAO.md)

## Description

Define MCP Architecture

## Guidance

# Define MCP Architecture

**Condition:** Run only if the system exposes tools or resources via the Model Context Protocol. Skip and write "Not applicable" in SAO §18 if MCP is not in scope. Depends on DTA-03 (API style chosen).

**Reference:** Playbook artifact **MCP FastMCP Reference Architecture** (latest released Edda version).

## Objective

Decide the MCP integration case (A / B / hybrid), transport topology, tool inventory, and authentication pattern; document all decisions in SAO §18.

## Process

1. **Fetch the latest MCP FastMCP Reference Architecture** from the playbook and read the Purpose & Mission Assessment sections before answering any question below.
2. Answer mission questions — determine integration case and transport.
3. Inventory tools — decide which service callables become MCP tools.
4. Design auth pattern — process user, PAT per call, or both.
5. Handle stdout hygiene if stdio transport is selected.
6. Record decisions for SAO §18.

## Decisions to Make

### 1. Mission Assessment (Q1–Q7)

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| Q1 | Who are the MCP clients? (AI IDE, Claude Desktop, custom script, cloud AI) | | Transport and auth |
| Q2 | Embed business logic or delegate to HTTP API? | | Case A vs B vs hybrid |
| Q3 | How is user identity established per tool call? | | Auth pattern |
| Q4 | Are any tools destructive? (write, delete, deploy) | | HITL and write-tool policy |
| Q5 | Low-latency local IDE integration required? | | stdio transport |
| Q6 | Multi-tenant or remote-client access required? | | HTTP+SSE transport |
| Q7 | Stdout logging interference needs prevention? | | Log routing for stdio |

### 2. Integration Case

- [ ] **Case A — Service Bridge**: MCP calls internal service layer directly. Best for single-deployment systems.
- [ ] **Case B — API Facade**: MCP calls the public HTTP API. Best for multi-tenant / remote clients.
- [ ] **Hybrid**: Mix of A and B.

Rationale: _____

### 3. Transport Topology

| Target | Transport | Port / Path | Notes |
|--------|-----------|-------------|-------|
| Local IDE (Cursor, Claude Desktop) | stdio | n/a | Requires stdout hygiene |
| Remote AI clients | HTTP+SSE | :8001/mcp | Auth header required |

Topology decision: stdio only / HTTP+SSE only / Both (dual server)

### 4. Tool Inventory

| Tool name | Service method | Write? | HITL? | Case |
|-----------|----------------|--------|-------|------|
| | | | | |

**Write-tool policy**: Require explicit confirmation param / HITL prompt before execute / Audit log only

### 5. Authentication Pattern

Selected pattern(s): Process user / PAT per call / Session cookie / Mixed

PAT injection point: Tool argument (explicit) / HTTP header (Bearer — avoids prompt injection)

### 6. Stdout Hygiene (if stdio)

- Redirect all logging to stderr or file
- Suppress third-party libraries that print to stdout
- Add T3 test verifying no stdout noise on server boot

### 7. Case B: API Readiness Contract (if Case B or hybrid)

| Tool | HTTP endpoint | Method | Auth header |
|------|---------------|--------|-------------|
| | | | |

### 8. Scan Skills

Query Skills where `capability_domain` in: MCP, API_INTEGRATION, AUTH. Report gaps.

## Deliverables

- Mission questions answered (Q1–Q7)
- Integration case chosen (A / B / hybrid) with rationale
- Transport topology defined
- Tool inventory table (tool → service method → write? → HITL?)
- Auth pattern defined with injection point
- Stdout hygiene addressed (if stdio)
- API readiness contract defined (if Case B)
- Skill coverage assessed
- Decision recorded for SAO §18 (DTA-18)

## Agent

None

## Skill

None

## Rules

None

## Artifacts Produced

- **MCP FastMCP Reference Architecture** (Document) - Optional

## Artifacts Consumed

None

## Notes

No additional notes.
