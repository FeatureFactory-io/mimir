# Activity: Check Definition of Done

**Activity ID**: 101
**Order**: 6
**Phase**: Construction
**Dependencies**: Predecessor: Activity 100 (Implement Journey Certification Tests)

## Description

Check Definition of Done

## Guidance

## Purpose
Validate that feature/story implementation complies with all project rules and standards by examining current state and outputs.

## Core Development Rules Checklist

### Test-First Development
- [ ] Every function/method has corresponding test(s)
- [ ] Feature files in `docs/features/` exist and comply with scenarios
- [ ] Tests use pytest framework
- [ ] Mocking is minimal

### Continuous Testing
- [ ] All tests are runnable via `pytest tests/`
- [ ] Tests are pytest compatible with proper fixtures
- [ ] `tests.log` file exists and contains test output

### Concise Methods
- [ ] Top-level (public) methods are 20-30 lines maximum
- [ ] Supporting logic is in well-named private methods
- [ ] Helper methods have single, focused responsibilities
- [ ] Method names are descriptive and clear

## Code Quality Rules Checklist

### Import Management
- [ ] All imports are at module level
- [ ] No imports inside functions/methods
- [ ] Dependencies are properly declared

### Log Story Verification
- [ ] Implementation plan / issue contains a **Log Story Script** (Where / Beat / Trigger / Must include)
- [ ] Every script row is proven by a passing `*_log_story_*` caplog test (or `checkpoint.log_story_command` from the iteration manifest)
- [ ] Happy **and** reject paths covered when the scenario has both
- [ ] Log levels are appropriate (DEBUG, INFO, WARNING, ERROR)
- [ ] No secrets/tokens/passwords appear at INFO in asserted lines
- [ ] No deferred logging slice remains in the plan

Grep of `logs/app.log` is an **audit aid**, not the DoD gate. Caplog (or `log_story_command`) is the gate.

## Testing and Quality Assurance Checklist

### Integration Test Standards
- [ ] Integration tests in `tests/integration/` exist
- [ ] Integration tests avoid mocking
- [ ] Real dependencies are used in integration scenarios

### Commit Conventions
- [ ] Recent commit messages follow Angular conventional format
- [ ] Commits are atomic and focused
- [ ] Breaking changes are documented in commit messages

## UI and Frontend Rules Checklist

### Django Views + HTMX
- [ ] No DRF views exist for new web UI features
- [ ] Django views return HTML templates
- [ ] HTMX attributes used for dynamic interactions
- [ ] Services layer is shared between MCP and Web UI

### Semantic Naming
- [ ] All interactive elements have `data-testid` attributes
- [ ] Naming follows kebab-case convention
- [ ] Form inputs have proper name and id attributes

## Documentation Checklist

### Scenario Writing
- [ ] BDD scenarios exist for features
- [ ] Feature files are well-structured
- [ ] Scenarios cover edge cases and error conditions
- [ ] Review GUI - do scenarios match behavior, fields, URLs, design rules? Report inconsistencies to user

### TODO Management
- [ ] TODO comments exist for incomplete implementations
- [ ] TODO items have clear descriptions
- [ ] TODOs in dependencies can be ignored

### Document Updates
- [ ] Review code: new packages, patterns, approaches worth documenting?
- [ ] Review conversation: need to update feature files/corrections?
- [ ] Review modus operandi against workflows and rules - can we improve?

## Final Validation Checklist

### Overall Quality Check
- [ ] Feature meets acceptance criteria
- [ ] Code is production-ready
- [ ] Documentation exists and is accurate

### Integration Validation
- [ ] Feature integrates with existing system
- [ ] No breaking changes introduced
- [ ] Dependencies properly declared in requirements.txt

### Deployment Readiness
- [ ] Database migrations exist if needed
- [ ] Environment variables are documented
- [ ] Configuration changes are documented

### Cleanup
- [ ] Remove temporary files like debug_*.py
- [ ] Scan file structure for stray misplaced files
- [ ] Remove *.log files from repository


## Rules

Before validating DoD, **read** each Rule below in this playbook (by slug), then **apply** it as the acceptance criterion for the matching checklist items. Do not rely on memory of the rule text.

Required:
- `do-test-first`
- `do-continuous-testing`
- `do-write-concise-methods`
- `do-import-on-module-level`
- `do-informative-logging`
- `do-assert-log-story`
- `do-not-mock-in-integration-tests`
- `do-follow-commit-convention`
- `do-semantic-versioning-on-ui-elements`
- `do-write-scenarios`
- `do-add-todos-for-incomplete-items`
- `pytest`

Activity-specific (not a substitute for the rules above):
- Observability DoD is **Log Story Verification** (caplog / `log_story_command`), not “logging statements exist”.

## Actions
All checkboxes must be completed before considering the story "Done". Any deviations must be presented to user. If user says "collect for cleanup but defer" - create a Backlog item in GitHub as Issue with "deferred" tag. Otherwise resolve deviations as directed by user, commit following Angular convention, and send Pull Request.

## Success Criteria
- All checklist items verified
- No deviations or all approved by user
- Code production-ready
- Ready for PR

## Inputs

Read these before starting this activity. They are produced earlier in the playbook and are authoritative — raise a drift event instead of deviating.

- **Feature Files** (Document, Required) — produced by Write Feature Files (#39).
- **Implementation Plan Template** (Template, Required) — produced by Plan Feature (#96).

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

- **Fix Tests** (`do-fix-tests`)
- **Informative Logging** (`do-informative-logging`)
- **Update Tests After Bugfixing** (`do-update-tests-after-bugfixing`)

## Artifacts Produced

None

## Artifacts Consumed

- **Feature Files** (Document) - Required
- **Definition of Done Checklist Template** (Template) - Required
- **Implementation Plan Template** (Template) - Required

## Notes

No additional notes.
