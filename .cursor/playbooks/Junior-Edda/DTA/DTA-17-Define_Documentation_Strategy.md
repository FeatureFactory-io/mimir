# Activity: Define Documentation Strategy

**Activity ID**: 58
**Order**: 17
**Phase**: Inception
**Dependencies**: Predecessor: Activity 57 (Define Developer Experience)

## Description

Define Documentation Strategy

## Guidance

# Define Documentation Strategy

## Objective

Define Architecture Decision Record (ADR) process, API documentation approach, living documentation standards, runbook format, and knowledge base structure.

---

## Decisions to Make

### 1. Architecture Decision Records (ADRs)

- **Template**: Standard ADR format (Title, Status, Context, Decision, Consequences)
- **Storage location**: `docs/architecture/decisions/` or `docs/adr/`
- **Numbering**: Sequential (ADR-001, ADR-002, ...)
- **Review process**: PR-based? Team discussion? Informal?
- **When to write**: Any significant architecture or technology choice

### 2. API Documentation

- **Approach**: OpenAPI/Swagger spec generation
- **Generation**: Contract-first (write spec, generate code) or code-first (generate spec from code)
- **Publishing**: Auto-published on build? Swagger UI endpoint?
- **MCP tool documentation**: How are MCP tools documented?
- **Versioning**: Spec versioned with API version

### 3. Living Documentation

- **Code comments policy**: When to comment (non-obvious logic), when NOT to comment (obvious code)
- **Docstring standards**: Sphinx format with `:param:`, `:return:`, `:raises:` and examples
- **Type hints**: Required on all public methods and functions
- **README hierarchy**: Root README → app-level READMEs → module docs

### 4. Runbook Standards

- **Format**: Markdown with structured sections (Trigger, Impact, Steps, Verification)
- **Storage**: `docs/runbooks/` or alongside infrastructure code
- **Update cadence**: After every incident that reveals a gap
- **Review**: Quarterly runbook review for staleness

### 5. Knowledge Base

- **Wiki**: GitHub Wiki, Confluence, Notion, or docs/ in repo
- **Onboarding guides**: For new developers, new operators
- **FAQ**: Common questions and troubleshooting
- **Search**: How is documentation discoverable?

### 6. Scan Skills

Query Playbook Skills where `capability_domain` in:
- `DOCS_ADR`
- `DOCS_API`
- `DOCS_RUNBOOK`

Report coverage and gaps.

---

## Deliverables

- ✅ **ADR process** established with template and storage location
- ✅ **API documentation** approach chosen
- ✅ **Living documentation** standards defined (comments, docstrings, type hints)
- ✅ **Runbook standards** set
- ✅ **Knowledge base** structure defined
- ✅ **Skill coverage** assessed for this domain
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

None

## Artifacts Produced

None

## Artifacts Consumed

None

## Notes

No additional notes.
