# Activity: Write SAO.md

**Activity ID**: 59
**Order**: 20
**Phase**: Inception
**Dependencies**: Predecessor: Activity 58 (Define Documentation Strategy)

## Description

Write SAO.md

## Guidance

**Position in workflow:** Terminal activity of Define Architecture (DTA) — order **20 of 20**. Run only after all prior DTA domain activities are complete (DTA-02 through DTA-17, and when applicable Activity 200 Define AI Agent Architecture and Activity 201 Define MCP Architecture).

# Write SAO.md (System Architecture Overview)

## Objective

Compile all architectural decisions from DTA-02 through DTA-17 (and optionally Activities 200 and 201, if applicable) into a single, authoritative document: `docs/architecture/SAO.md`.

Since Activity 42 now dispatches the domain decision workers in parallel (see that activity's Step 6), this activity is the **first point** at which all 16-18 domain decisions are seen together. Serial execution used to give an agent incidental cross-domain awareness just by having read every earlier decision in order before reaching this activity; parallel dispatch does not provide that awareness, so Step 0 below makes the check explicit instead of assuming it happened.

## Process

### 0. Cross-Domain Consistency Check (run before compiling)

Before writing anything into SAO.md, check each collected domain decision against the others for contradictions. At minimum, check these known collision points:

| Pair | What can conflict |
|---|---|
| Security (decision from the Define Security domain activity) ↔ Data Architecture (Define Data Architecture) | Authentication model and encryption-at-rest expectations must match the chosen database engine's actual support (e.g. field-level encryption availability, session storage backing) |
| Infrastructure (Define Infrastructure) ↔ CI/CD Pipeline (Define CI/CD Pipeline) | The chosen compute model (Kubernetes, container service, serverless, VMs, PaaS, desktop-only) constrains which deploy targets and promotion mechanisms are even possible |
| Infrastructure (Define Infrastructure) ↔ Release & Rollback (Define Release & Rollback) | The blue/green or rollback mechanism chosen must match the compute model — e.g. a Kubernetes/EKS choice implies namespace or Route53-weight based switching; an Elastic Beanstalk choice implies environment-swap based switching. A Release & Rollback decision written independently of the Infrastructure decision may assume a mechanism the chosen compute platform doesn't support. |

For each pair above (and any other conflict a reviewer notices while compiling): if the two decisions are compatible, note nothing extra. If they conflict, **do not silently pick one** — surface it to the user as a named contradiction between the two domains and get an explicit resolution before writing either section into SAO.md.

Record the outcome of this check (clean, or list of resolved contradictions) as a short note at the top of SAO.md's changelog/history, so a future reader can see the check happened.

### 1. Gather All Decisions

Collect recorded decisions from each domain activity:
- DTA-02: Application Blocks
- DTA-03: Integration & API Design
- DTA-04: Code Organization
- DTA-05: Data Architecture
- DTA-06: Test Strategy
- DTA-07: Performance & Scalability
- DTA-08: Error Handling & Resilience
- DTA-09: Infrastructure
- DTA-10: CI/CD Pipeline
- DTA-11: Release & Rollback
- DTA-12: Observability
- DTA-13: Config & Secrets
- DTA-14: Security
- DTA-15: Backup & Recovery
- DTA-16: Developer Experience
- DTA-17: Documentation Strategy
- Activity 200: AI Agent Architecture (if applicable)
- Activity 201: MCP Architecture (if applicable)

### 2. Write SAO.md

Structure — add sections 17 and 18 after section 16:

```
## 16. Documentation Strategy
[Decision from DTA-17]

## 17. AI Agent Architecture
[Decision from Activity 200 — skip section if no in-app agent]

## 18. MCP Architecture
[Decision from Activity 201 — skip section if no MCP interface]
```

### 3. Skill Gap Analysis

Compile coverage reports from all domain activities into a single matrix:

```
Domain                   | Covered Skills     | Gaps
Application Blocks       | [list]             | [list]
...
AI Agent Architecture    | [list]             | [list]
MCP Architecture         | [list]             | [list]
```

### 4. Review with User

Present SAO.md for review, including the Step 0 consistency-check outcome. Get explicit approval before proceeding to Bootstrap Project.

### 5. Post-Implementation Updates

The SAO is a living document. During and after implementation, update it with critical discoveries, retrospective corrections, and recurring patterns. Each update should reference the original DTA decision.

## Deliverables

- Cross-domain consistency check performed and recorded (Step 0), any contradictions resolved with the user before compilation
- SAO.md written at `docs/architecture/SAO.md`
- All domain decisions (16 core + up to 2 optional: AI Agent, MCP) compiled
- Skill coverage report included
- Key decisions summary with rationale
- User approval obtained
- Ready to proceed to **Define Software Process (DSP)**. DSP requires SAO.md to generate the AI IDE configuration — run DSP before BSP.

When ESM, DTA, DSP, and BSP are all complete, proceed to BSP-08 for the Construction Handoff and mode selection.

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

None

## Rules

- **Fan Out Independent Work** (`fan-out-independent-work`)

## Artifacts Produced

- **System Architecture Overview Template** (Document) - Optional

## Artifacts Consumed

None

## Notes

No additional notes.
