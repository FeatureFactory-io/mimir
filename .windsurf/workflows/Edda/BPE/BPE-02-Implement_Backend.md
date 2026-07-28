# Activity: Implement Backend

**Activity ID**: 97
**Order**: 2
**Phase**: Construction
**Dependencies**: Predecessor: Activity 96 (Plan Feature)

## Description

Implement Backend

## Guidance

## Purpose
Implement backend services, models, and views following test-first development and small increments approach.

## Steps

### 1. Create Skeletons
Create all class and method skeletons with full docstrings following your language's documentation conventions.

The core principle: the developer who has no knowledge of the system can implement methods/properties etc. following only documentation in the skeleton.

- Create class and method/function stubs and document them
- Include full docstrings, return types, and sample return values
- Use appropriate placeholder (e.g., `NotImplementedError`, `TODO`, `panic!`, etc.)
- Do not skip type hints or documentation
- Add comments inside the methods pointing attention to the logic flow, exception handling, logging etc.

### 2. Write Behavior Tests Before Logic
Write unit tests before writing method logic using your test framework. Use real dependencies in integration scenarios - no mocking.

### 3. Implement Incrementally (behavior green)
Work method-by-method. Each method/property should be: implemented → behavior-tested → then log-story tested (step 4) → committed.

### 4. Log Story — Caplog in the Same Slice
For each footprint method covered by the plan's **Log Story Script**:

1. Write `test_*_log_story_happy` and/or `test_*_log_story_reject` (red)
2. Emit INFO logs that satisfy story beats (`entry → config → validation → processing → branch → exit → error`) per `do-informative-logging`
3. Make log-story tests green using skill *Pytest Log Story Assertions* (`tests/support/log_story.py` → `assert_log_story`) once TFK-02 has bootstrapped the helper — per `do-assert-log-story`
4. Never defer logging to a later “informative logging pass” slice

### 5. Commit After Each Step
Write → run → test (behavior + log story) → evaluate → fix. Commit using Angular-style commit messages. Behavior and log-story green in the same commit.

### 6. Backend Architecture
- **Services Layer**: Business logic shared between different interfaces (API, Web UI, CLI, etc.)
- **Repository Pattern**: Data access abstraction (can be swapped)
- **Views/Controllers**: Return appropriate responses for your framework
- **API Endpoints**: Follow RESTful or your framework's conventions
- **Context/State**: Always validate and document

### 7. Route Registration
Register new routes/endpoints with descriptive names. Follow your framework's conventions for URL/route structure.

### 8. Testing Views/Controllers
Use your framework's test client. Test responses, validate context/state, check templates/views used, test dynamic endpoints. Include caplog assertions for Log Story Script rows on those views.

### 9. Scan Skills

Query Playbook Skills where `capability_domain` in:
- `BACKEND_FRAMEWORK` — Backend implementation patterns for your tech stack
- `TEST_FRAMEWORK` — Testing patterns and best practices
- `LOGGING_PATTERN` — Logging implementation for your language
- `LOG_STORY_TESTING` — Pytest Log Story Assertions / caplog helpers
- `DOCSTRING_FORMAT` — Documentation format for your language

Apply reference implementations and patterns from matched Skills.

## Rules

Before implementing, **read** each Rule below in this playbook (by slug), then **apply** it to every change in this activity's footprint. Do not rely on memory of the rule text; do not paraphrase the rule body into this activity.

Required:
- `do-skeletons-first`
- `do-test-first`
- `do-not-mock-in-integration-tests`
- `do-informative-logging`
- `do-assert-log-story`
- `do-import-on-module-level`
- `do-write-concise-methods`
- `do-docstring-format`
- `do-follow-commit-convention`
- `do-small-increments`
- `pytest`

Activity-specific (not a substitute for the rules above):
- Log-story tests (`*_log_story_*` / caplog) ship in the **same** red→green slice as behavior — no deferred logging pass.

## Success Criteria
- All skeletons created with full documentation
- Behavior tests written before implementation and passing
- Log Story Script rows proven by passing `*_log_story_*` caplog tests in the same commit as behavior
- No deferred logging slice in the plan
- Code committed with proper messages
- Routes/endpoints properly registered
- Services layer properly structured

## Inputs

Read these before starting this activity. They are produced earlier in the playbook and are authoritative — raise a drift event instead of deviating.

- **Feature Files** (Document, Required) — produced by Write Feature Files (#39).
- **System Architecture Overview Template** (Template, Required) — produced by Write SAO.md (#59).
- **Implementation Plan Template** (Template, Required) — produced by Plan Feature (#96).
- **Definition of Done Checklist Template** (Template, Required) — produced by Check Definition of Done (#101).

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

**Title**: Django Backend Implementation Patterns
**Capability Domain**: BACKEND_FRAMEWORK
**Technology Stack**: Django+Python+pytest

**Title**: Pytest Log Story Assertions

## Rules

- **Assert Log Story** (`assert-log-story`)
- **Check Previous Commits** (`do-check-previous-commits`)
- **Docstring Format** (`do-docstring-format`)
- **Fix Tests** (`do-fix-tests`)
- **Import On Module Level** (`do-import-on-module-level`)
- **Informative Logging** (`do-informative-logging`)
- **Not Go Into Debugging Loops** (`do-not-go-into-debugging-loops`)
- **Skeletons First** (`do-skeletons-first`)
- **Test First** (`do-test-first`)
- **Validate Api Contracts** (`do-validate-api-contracts`)
- **Keep Docstrings Consistent** (`keep-docstrings-consistent`)

## Artifacts Produced

None

## Artifacts Consumed

- **Feature Files** (Document) - Required
- **System Architecture Overview Template** (Document) - Required
- **Definition of Done Checklist Template** (Template) - Required
- **Implementation Plan Template** (Template) - Required

## Notes

No additional notes.
