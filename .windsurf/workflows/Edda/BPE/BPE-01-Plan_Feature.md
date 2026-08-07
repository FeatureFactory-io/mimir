# Activity: Plan Feature

**Activity ID**: 96
**Order**: 1
**Phase**: Construction
**Dependencies**: None

## Description

Plan Feature

## Guidance

## Purpose
Plan a new feature implementation by analyzing requirements, assessing codebase state, creating detailed implementation plan, and preparing for execution.

## Prerequisites
- Feature specification or idea for what needs to be built
- Access to codebase and documentation

## Steps

### Step 0: Reset and Prepare
Reset your task plan. If there was work in progress on another task, create a TODO.md file documenting what was being worked on, what was completed, what remains to be done, and any blockers or notes.

### Step 1: Understand Architecture
Read `docs/architecture/SAO.md` (if exists) to identify architectural patterns and principles relevant to this implementation. **Note which section headings govern this feature — you will need these in Step 6.**

### Step 2: Understand User Journey
Check `docs/features/user_journey.md` (if exists) to understand what you're building and how it integrates with other parts of the system.

### Step 3: Analyze Feature Specification
Read the feature specification thoroughly. If none exists, propose creating one first.

Follow BDD/Gherkin format: one scenario = one user goal; 5–10 steps max; GIVEN-WHEN-THEN structure; independently executable. Step phrases must reuse patterns from `docs/features/CATALOG.md` or explicitly add a new catalogued step via TFK-07.

### Step 4: Assess Codebase State

a) **Identify reusable components:** list components/services/models that can be reused; verify they're not stubs.

b) **Check test coverage:** for any reusable components without tests, add test creation to the plan.

c) **Build context map:** identify 3–5 `file:line_range` locations an implementor must read. Format:
```
| file | lines | one-line note |
```
If you cannot identify 3 meaningful references, the codebase assessment in step (a) is incomplete.

d) **Detect MCP / Agent surface:**
   - Check SAO §18 — is MCP in scope for this feature?
     If yes: locate `mcp/server.py` (or equivalent). Verify `initialize_mcp()` exists and is called on startup. If missing: add initialization to the plan before any tool registration step.
   - Check SAO §17 — does this feature add or extend agent capabilities?
     If yes: locate `ToolExecutor` (artifact 56 §4.3). Verify it is instantiated and injected into the agent loop. If missing: add ToolExecutor initialization to the plan before service wiring.
   - Record findings as additional one-liners in the Context Map:
     `mcp/server.py | <line> | FastMCP singleton — register new tools here`
     `llm/executor.py | <line> | ToolExecutor — wire service callables here`
     Skip a row if that surface is not in scope.

e) **Mockup inventory and graduation plan** (when the feature has UI screens):

Canonical mockup locations (ESM-06):

- `templates/mockups/{entity}/` — HTML prototype templates
- `mockups/urls.py`, `mockups/views.py` — DEBUG-only routes at `/mockups/...` (404 when `DEBUG=False`)

```bash
# Entity slug from feature spec / screen ID (e.g. pips, teams, search)
ls templates/mockups/{entity}/ 2>/dev/null
rg "mockup_{entity}" mockups/urls.py 2>/dev/null || true
```

For **each screen** in scope (list, create, detail, …), decide graduate strategy and record in **Section H** (Step 6):

| Screen | Mockup source | Production target | Strategy |
|--------|---------------|-------------------|----------|
| list | `templates/mockups/{entity}/list.html` | `templates/methodology/{entity}/list.html` | rewire |

**Strategies:**

- **rewire** — mockup exists: BPE-03 **ports** markup/structure/testids to production templates and real views; **do not delete** mockup files or `/mockups/...` routes (keep as design reference per existing plan convention)
- **greenfield** — no mockup: build from feature file + `docs/ux/IA_guidelines.md`
- **partial** — mockup covers part of the screen: rewire what exists, extend in production

When strategy is **rewire** or **partial**, add mockup template path(s) to the Context Map (Step 4c). Each **BPE-03** graph node (Step 6G) must list `mockup_source` and `production_template` when applicable.

If the feature has **no UI** (API-only, MCP-only): Section H = `Not applicable — no frontend screens.`

If UI is in scope but **no mockups exist**, ask: create per ESM-06 first, or proceed **greenfield**?

### Step 5: Clarification Questions
Ask clarification questions scenario-by-scenario. If >5 questions total, create `FEAT_X.Y.Z_Clarifications.md` for batch answers.

### Step 6: Create Implementation Plan

**Mandatory Section A — Context Map** (from Step 4c)
**Mandatory Section B — Do-Not-Do List** (derived from SAO.md sections)
**Mandatory Section C — SAO.md Sections That Apply**
**Mandatory Section D — Tests to Create** (each row must state what it asserts). When Section E has rows, also list `test_*_log_story_happy` and/or `test_*_log_story_reject` (pytest + caplog; integration or view level).
**Mandatory Section E — Log Story Script** (formerly Logs to Emit). Each row is a beat the implementor must emit and prove with caplog. Never defer logging to a final slice.
```
## Log Story Script
| Where | Beat | Trigger | Must include |
|-------|------|---------|--------------|
| `LoginView.post` | entry | method called | email= (never password) |
| `LoginView.post` | branch | bad credentials | authentication failed |
| `LoginView.post` | exit | success | login success, user_pk= |
```
Beats vocabulary: `entry | config | validation | processing | branch | exit | error`.
Do not cite dropped rule `add-logging`.

**Mandatory Section F — MCP Tools to Expose** (skip with "Not applicable" if MCP not in scope):
```
## MCP Tools to Expose
| Tool name | Service method | Write? | HITL? | Auth injection |
|-----------|---------------|--------|-------|----------------|
| `create_foo` | `FooService.create` | Yes | No | server-side user_id |
```
Rules: artifact 57 §3.2 (tool schema), §3.3 (auth injection — never accept user_id from args), §3.4 (write-tool policy)

**Mandatory Section H — Mockup Graduation Plan** (from Step 4e; use `Not applicable — no frontend screens` when no UI):

```
## Mockup Graduation Plan
| Screen | Mockup source | Production target | Strategy | BPE-03 node id |
|--------|---------------|-------------------|----------|----------------|
| list | templates/mockups/{entity}/list.html | templates/methodology/{entity}/list.html | rewire | N2-frontend-list |
```

Strategy values: `rewire | greenfield | partial`. When `rewire`/`partial`, production templates must match mockup UX unless feature file explicitly diverges (note divergence in Do-Not-Do or clarifications).

**Implementation Steps:**

1. **Backend Implementation:** models, admin, services, views, URLs. Follow the Rules section below.

6. **MCP Tool Registration (if SAO §18 in scope):**
   - Declare the tool in `mcp/tools/` wrapping the service method; apply server-side auth injection.
   - Register with `initialize_mcp()`.
   - Apply stdout hygiene if stdio transport (artifact 57 §6).
   - Reference: artifact 57 §3–§4

7. **ToolExecutor Wiring (if SAO §17 in scope):**
   - Register the service callable in `ToolExecutor` under the tool name expected by the agent loop.
   - Ensure the return envelope matches the stable format.
   - Mark as HITL if destructive.
   - Reference: artifact 56 §4.3

2. **Frontend Implementation:** Django templates, HTMX, partials, `data-testid` attributes.

3. **Testing — prove what's working:** behavior tests red → green → refactor. Unit, integration (no mocks), view tests. Then **log-story tests red → green** in the same slice (caplog / `assert_log_story`).
   **MCP tools** (if Section F populated): Tests to Create table must include T1 + T2 per new tool; T3 required if stdio:
   - T1 (FastMCP Client): `async with Client(transport=mcp) as c: await c.call_tool(...)` — proves schema, registration
   - T2 (Direct service): call service with real DB — proves service/ORM wiring
   - T3 (subprocess JSON-RPC): proves entrypoint cleanliness (no stdout noise)
   - Full recipes: artifact 57 §7

4. **Observability:** emit INFO at decision points matching the Log Story Script (who/what/when/why, never raw secrets). Prove with caplog tests — ban deferred "informative logging pass" slices.

5. **Commit Strategy:** Angular convention after every principal step. Behavior + log-story green in the same commit when Section E is populated.

Each narrative implementation step above maps to one or more **`feature_execution_graph` nodes** tagged with `bpe: BPE-02`…`BPE-06` in Step 6G — the graph is the executable plan; Sections A–F remain the human-readable contract.

### Step 6G — Build Feature Execution Graph (Plan mode)

After Sections A–F are complete:

1. Switch to **Plan mode**. Present a Mermaid dependency graph of execution nodes (typical order: backend slices → frontend → AT → E2E → DoD). Prefer **4–8 nodes** per feature.
2. For each node, assign `bpe: BPE-0N` using [BPE-02](BPE-02-Implement_Backend.md)…[BPE-06](BPE-06-Check_Definition_of_Done.md) as templates: slice `footprint`, `tests`, `log_story_rows`, and **pytest/`make` gates** only (no custom gate scripts). See artifact **Feature Execution Graph** (`artifacts/feature-execution-graph-schema.md`).
   - **BPE-03 nodes:** when Section H strategy is `rewire` or `partial`, set optional fields `mockup_source`, `production_template`, `graduate_strategy: rewire` on the node (schema documents these).
3. User approves the graph in Plan mode.
4. **Compile** the approved graph to YAML with root key `feature_execution_graph`, wrapped in `<!-- FEATURE_EXECUTION_GRAPH -->` … `<!-- /FEATURE_EXECUTION_GRAPH -->`.
5. **Standalone feature** (no PIN): also write `docs/plans/{FEAT}-feature-execution-graph.yaml`.
6. **Under PIN-03**: embed the graph at `scenarios.{SN}.feature_execution_graph` in the iteration execution manifest; skip BPE-01 Steps 9–10 (issue creation happens in PIN-04).

**Solo orchestration (no MIN):** parent agent walks ready nodes, launches a **fresh subagent per node** with skill *Assemble Guidance Bundle*, collects `NODE_PASS` comments, runs BPE-07 when all nodes green.

### Steps 7–10: Rule Confirmation, No Time Estimates, Submit for Approval, GitHub Issue

Issue body must contain all mandatory sections inline: **A–H** (H may be N/A), **`FEATURE_EXECUTION_GRAPH`**, and **Lessons Learned**. Each section must be self-sufficient for a cold-start implementor. When used under PIN, note that `checkpoint.log_story_command` must pass alongside the behavior checkpoint; terminal scenario checkpoint should match the **BPE-06** node's `gate.command`.

### Step 7: Write Lessons Learned

Before creating the GitHub issue, add a `## Lessons Learned` section to the issue body.

**The question is open-ended:** *Completing this story — what difficulties did you encounter? How could the task definition, tools, and artifacts you received have been improved to make accomplishing this task easier, without creating extra duplicates or contradictions elsewhere?*

This is not a finite list of categories. Write freely. If something matters, write it down. Areas that often surface signal (use them if they apply, ignore if they don't):
- Missing or unclear artifacts (mockups, SAO sections, feature files, skills)
- Activity steps that contradicted each other, the feature spec, or `user_journey.md`
- Technical decisions made during planning not yet in `docs/architecture/SAO.md`
- Deviations from the written BDD scenarios (scope narrowed, step reworded, constraint added)

If nothing to note: `## Lessons Learned — None.`

One honest sentence beats four empty bullet points. The reader is MIN-05 closing the iteration and PIN-02 opening the next one.

## Rules

Before planning and writing the implementation plan, **read** each Rule below in this playbook (by slug), then **apply** it when filling Mandatory Sections D–E and the Implementation Steps. Do not rely on memory of the rule text.

Required:
- `do-plan-before-doing`
- `do-skeletons-first`
- `do-test-first`
- `do-not-mock-in-integration-tests`
- `do-informative-logging`
- `do-assert-log-story`
- `do-write-concise-methods`
- `do-docstring-format`
- `do-semantic-versioning-on-ui-elements`
- `do-follow-commit-convention`
- `do-small-increments`
- `pytest`

Activity-specific (not a substitute for the rules above):
- Mandatory Section E is a **Log Story Script** (Where / Beat / Trigger / Must include); Section D must name matching `*_log_story_*` tests when Section E is non-empty.
- Logging ships in the same green slice as behavior — ban deferred logging passes.
- Step 6G **Feature Execution Graph** is mandatory; every node has `gate.command`; at least one `BPE-02` and one terminal `BPE-06` node.

## Success Criteria
- Feature specification exists and is clear
- Codebase assessment complete with context map (3–5 file:line_range references)
- Plan contains all mandatory sections: Context Map, Do-Not-Do, SAO Sections, Tests to Create, Log Story Script, MCP Tools to Expose, Mockup Graduation Plan (Section H or N/A)
- **`feature_execution_graph` compiled** (Step 6G): every node has `gate.command`, BPE-06 terminal node, deps enforce layer order
- All tests explicitly listed with what they prove, including `*_log_story_*` when Section E has rows
- All log decision points listed with Beat + required context fields
- If MCP tools added: Tests to Create table contains T1+T2 rows per new tool (T3 if stdio)
- Plan reviewed and approved by user (including Plan mode graph approval)
- GitHub issue created/updated with Sections A–F, `FEATURE_EXECUTION_GRAPH`, and Lessons Learned inline
- `## Lessons Learned` section present in the issue body

## Agent

**Name**: Dr. Dobbs v2
**Description**: # Cautious Developer Agent Guide

**Motto**: "Code that's easy to prove correct is code that works"

## Core Principles

### 1. Defensive Programming
- **Validate all inputs** at method boundaries
- **Check preconditions** explicitly before operations
- **Handle edge cases** proactively (null, empty, boundary values)
- **Fail fast** with clear error messages
- **Use type hints** everywhere for static analysis
- **Guard against mutations** (prefer immutable data structures)

### 2. Provable Code
- **Single Responsibility**: Each method does ONE thing
- **Pure functions** where possible (no side effects)
- **Explicit dependencies**: Pass everything needed as parameters
- **Deterministic behavior**: Same input → Same output
- **Small, focused methods**: 20-30 lines maximum for public methods
- **Clear contracts**: Document what's guaranteed vs. what's not

### 3. Observable Code
- **Log at decision points**: Why did we take this branch?
- **Log state transitions**: What changed and why?
- **Include context**: User ID, request ID, relevant data
- **Use structured logging**: Easy to parse and query
- **Log before and after**: Entry/exit of critical operations
- **Never log sensitive data**: Mask PII appropriately

### 4. Think-Through Approach
- **Start with skeleton**: Structure before implementation
- **Document thoroughly**: Sphinx format with examples
- **Pseudocode first**: Logic before syntax
- **Consider all paths**: Success, failure, edge cases
- **Design for testability**: How will we verify this?

### 5. Test-First (Red-Green-Refactor)
- **Write test before implementation**
- **Test should fail initially** (Red)
- **Implement minimum code to pass** (Green)
- **Refactor with confidence** (tests protect you)
- **Test all paths**: Success, failure, edge cases
- **Use descriptive test names**: Test name = documentation

### 6. Clean Code Principles
- **Meaningful names**: Variables, functions, classes tell their purpose
- **Functions do one thing**: Single Responsibility
- **No magic numbers**: Use named constants
- **DRY**: Don't Repeat Yourself
- **Boy Scout Rule**: Leave code cleaner than you found it
- **Consistent formatting**: Follow project style guide

### 7. SOLID Principles
- Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion

### 8. Self-Documented Code
- **Code explains "what" and "how"**
- **Comments explain "why"**
- **Use type hints**: They're documentation
- **Descriptive variable names**: No abbreviations unless obvious
- **Examples in docstrings**: Show usage
- **Codebase as learning materials**: Add references for advanced concepts

## Workflow

1. **Understand Requirements** — Read spec, identify edge cases, list assumptions
2. **Design (Think-Through)** — Skeleton, docstrings, pseudocode, testable units
3. **Write Tests (Red)** — Happy path, errors, edge cases, boundary conditions
4. **Implement (Green)** — Minimum code to pass, defensive checks, logging
5. **Refactor** — Extract helpers, remove duplication, improve naming, SOLID
6. **Verify** — All tests pass, coverage adequate, logs informative, docs complete

## Checklist for Every Method

- [ ] Sphinx-formatted docstring with :param:, :return:, :raises:
- [ ] Type hints on all parameters and return
- [ ] Input validation with clear error messages
- [ ] Logging at entry, exit, and decision points
- [ ] Tests for success, failure, and edge cases
- [ ] Method is < 30 lines (extract helpers if needed)
- [ ] No magic numbers (use named constants)
- [ ] Follows single responsibility principle
- [ ] Self-documenting variable names
- [ ] Comments explain "why", not "what"

## Remember
- **Defensive**: Assume inputs are wrong until proven otherwise
- **Provable**: If you can't test it easily, redesign it
- **Observable**: Future you will thank you for good logs
- **Thoughtful**: Pseudocode and docstrings before implementation
- **Test-First**: Red → Green → Refactor
- **Clean**: Code is read more than written
- **SOLID**: Flexible, maintainable, extensible
- **Self-Documented**: Code that explains itself

---
*"Any fool can write code that a computer can understand. Good programmers write code that humans can understand."* — Martin Fowler

## Skill

**Title**: Pytest Log Story Assertions

## Rules

- **Github Issues** (`do-github-issues`)
- **Informative Logging** (`do-informative-logging`)
- **Plan Before Doing** (`do-plan-before-doing`)
- **Pull Frequently** (`do-pull-frequently`)

## Artifacts Produced

- **Implementation Plan Template** (Template) - Required
- **Feature Execution Graph** (Schema) - Required — see `artifacts/feature-execution-graph-schema.md`

## Artifacts Consumed

- **User Journey** (Document) - Required
- **Screen Flow / Dialogue Map** (Diagram) - Required
- **Feature Files** (Document) - Required
- **HTML Mockups** (Code) - Optional — inventory in Step 4e; graduation in Section H
- **System Architecture Overview Template** (Document) - Required

## Notes

No additional notes.
