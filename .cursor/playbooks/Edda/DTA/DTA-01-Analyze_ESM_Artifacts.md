# Activity: Analyze ESM Artifacts

**Activity ID**: 42
**Order**: 1
**Phase**: Inception
**Dependencies**: None

## Description

Analyze ESM Artifacts

## Guidance

# Analyze ESM Artifacts

## Objective

Extract capability requirements per architectural domain from the ESM output artifacts (user journey, screen flows, .feature files, IA guidelines). This structured requirements list feeds all subsequent DTA activities (DTA-02 through DTA-17).

---

## Process

### 1. Read User Journey

- Extract **domain entities** (e.g., User, Playbook, Workflow, Activity, Skill)
- Identify **interaction patterns** (CRUD, search, import/export, real-time updates)
- Note **personas and roles** that imply auth/authorization requirements
- Flag **integration points** (external systems, APIs, data sources)

### 2. Read Screen Flows

- Identify **UI complexity** per screen type:
  - Simple: static content, read-only views
  - Moderate: forms, tables, filters, pagination
  - Complex: graphs, drag-and-drop, real-time, rich text editors
- Count screen types to estimate **frontend effort**
- Note **navigation patterns** (breadcrumbs, tabs, modals, wizards)

### 3. Read Feature Files (.feature)

- Extract **required capabilities** from scenario steps:
  - CRUD operations per entity
  - Search and filter requirements
  - Authentication and authorization scenarios
  - Error handling and edge cases
  - Data validation rules
- Map scenarios to **capability domains** (GUI_FORM, API_CRUD, AUTH_SESSION, etc.)

### 4. Read IA Guidelines

- Extract **design system requirements** (component library, theming)
- Note **accessibility requirements** (ARIA, keyboard navigation)
- Identify **responsive/multi-device** needs

### 5. Compile Requirements per Domain

Produce a structured list mapping ESM findings to the 16 architectural domains:

```
Domain: Application Blocks (DTA-02)
  - 5 bounded contexts identified: Auth, Methodology, Planning, MCP, Web UI
  - Dependency: Methodology → Planning (planning reads methodology)

Domain: Integration & API Design (DTA-03)
  - MCP stdio interface required (read-only)
  - Web UI HTTP interface required (full CRUD)
  - No external 3rd party integrations identified

Domain: Code Organization (DTA-04)
  - Monorepo structure implied (single Django project)
  - 3 layers visible: models, services, views

Domain: Data Architecture (DTA-05)
  - 6 entities with relationships (graph-like)
  - Version tracking required
  - Import/export functionality needed

... (continue for all 16 domains)
```

---

## Deliverables

- ✅ **Domain entities extracted** from user journey
- ✅ **UI complexity assessed** from screen flows
- ✅ **Capability domains mapped** from .feature files
- ✅ **Structured requirements list** produced for all 16 architectural domains
- ✅ **Ready to proceed** with DTA-02 through DTA-17

## Inputs

Read these before starting this activity. They are produced earlier in the playbook and are authoritative — raise a drift event instead of deviating.

- **User Journey** (Document, Required) — produced by Define User Journey (#36).
- **IA Guidelines** (Document, Required) — produced by Define Information Architecture (#37).

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

None

## Artifacts Produced

None

## Artifacts Consumed

- **User Journey** (Document) - Required
- **IA Guidelines** (Document) - Required

## Notes

No additional notes.
