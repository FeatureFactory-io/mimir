# Activity: Define Application Blocks

**Activity ID**: 43
**Order**: 2
**Phase**: Inception
**Dependencies**: Predecessor: Activity 42 (Analyze ESM Artifacts)

## Description

Define Application Blocks

## Guidance

# Define Application Blocks

## Objective

Identify bounded contexts, domain packages, module boundaries, and dependency rules. Choose the foundational architectural pattern (MVC, event-driven, modular monolith, microservices, etc.).

---

## Internal Process

Every domain activity follows this structure:

1. **Identify needs** — what does ESM require for this domain?
2. **Scan Skills** — query Playbook Skills by `capability_domain` for this domain
3. **Propose options** — 2-3 approaches with Skill coverage, cost, risk
4. **Record decision** — user picks, rationale documented

---

## Decisions to Make

### 1. Bounded Contexts / Domain Packages

- Review ESM entities and their relationships
- Group entities into cohesive domain packages
- Define which entities belong together (high cohesion) vs. which are separate concerns (loose coupling)
- Example groupings:
  - `auth/` — User, Session, Permissions
  - `methodology/` — Playbook, Workflow, Activity, Skill
  - `planning/` — WorkPlan, Task, Estimation
  - `mcp/` — MCP protocol, tools, stdio interface

### 2. Module Boundaries & Dependency Rules

- Define what can import what (dependency direction)
- Identify shared kernel vs. independent modules
- Example rules:
  - `planning` → depends on `methodology` (reads playbook structure)
  - `mcp` → depends on `methodology` (exposes methodology as tools)
  - `auth` → independent (no methodology dependency)
  - No circular dependencies allowed

### 3. Foundational Architectural Pattern

Choose one:
- **MVC / MTV** — Model-Template-View (Django default). Best for: server-rendered web apps with moderate complexity.
- **Event-Driven** — Publish/subscribe, event sourcing. Best for: highly decoupled systems, real-time requirements.
- **Modular Monolith** — Single deployable unit with strict module boundaries. Best for: starting simple with clear growth path.
- **Microservices** — Independent deployable services. Best for: large teams, independent scaling needs.
- **Batch Processing** — Scheduled jobs processing data in bulk. Best for: data pipelines, ETL.
- **Hybrid** — Combine patterns (e.g., MVC for web + event-driven for async).

### 3a. UI Architecture Patterns (if system has a web/desktop UI)

Define the presentation layer architecture:

**Rendering model**:
- **Server-rendered** — HTML generated on server (Django templates, Jinja2). Best for: testability, SEO, minimal JS.
- **SPA** — Single Page Application (React, Vue, Svelte). Best for: rich interactivity, complex state.
- **Hybrid** — Server-rendered with progressive enhancement (HTMX, Alpine.js, Turbo). Best for: server-side simplicity with dynamic UX.

**Layout pattern**:
- **Single-panel** — One main content area. Best for: simple CRUD, mobile-first.
- **Multi-panel** — Split layout (navigation + content + detail). Best for: explorer-style UIs, dashboards.
- **Wizard/stepper** — Sequential steps. Best for: complex forms, onboarding.

**Component interaction model**:
- **Full page reload** — Traditional links/forms. Simplest, most testable.
- **Partial updates** — Server returns HTML fragments, client swaps them (HTMX, Turbo Frames). Testable with standard server-side tests.
- **Client-side state** — JS manages state, talks to API (React+Redux, Vue+Pinia). Requires browser-based testing.

**Visualization approach** (if applicable):
- **Server-generated** — Graphviz, matplotlib, SVG generation on server. Best for: static/semi-static diagrams.
- **Client-rendered** — D3.js, Cytoscape.js, Chart.js. Best for: interactive, real-time visualizations.
- **Hybrid** — Server generates data, client renders. Best for: large datasets with interactive exploration.

Document rationale for each choice, especially impact on **testability** and **build complexity**.

### 4. Scan Skills & Reference Implementations

Query Playbook Skills where `capability_domain` in:
- `APP_STRUCTURE`
- `DOMAIN_MODELING`
- `DEPENDENCY_INJECTION`

Report coverage:
```
Skill Coverage for Application Blocks:
  APP_STRUCTURE    | [Django App Architecture Skill] ✅
                   | Reference: Repository pattern, service layers, dependency rules
                   | Example: Mimir methodology/ app structure
  
  DOMAIN_MODELING  | [DDD Bounded Contexts Skill] ✅  
                   | Reference: Entity modeling, aggregate boundaries
                   | Example: Playbook → Workflow → Activity hierarchy
  
  DEPENDENCY_INJECTION | ❌ No Skill - will create custom patterns
                       | Estimated impact: +1 iteration for pattern definition
```

If reference implementations exist: "Following Django app patterns from [Django App Architecture Skill](#skill-456), recommend service layer approach with estimated 2-day implementation."

If gaps exist: "No Skill for Dependency Injection — will need to define patterns. Estimated impact: +1 iteration."

---

## Deliverables

- ✅ **Bounded contexts / domain packages** identified and documented
- ✅ **Module dependency rules** defined (what imports what)
- ✅ **Foundational pattern** chosen with rationale
- ✅ **UI architecture patterns** defined (if applicable): rendering model, layout, interaction model, visualization
- ✅ **Skill coverage** assessed for this domain with reference implementations
- ✅ **Decision recorded** for inclusion in SAO.md (DTA-18)

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

- **Skeletons First** (`do-skeletons-first`)

## Artifacts Produced

None

## Artifacts Consumed

None

## Notes

No additional notes.
