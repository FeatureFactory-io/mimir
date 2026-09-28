# Activity: Define Integration & API Design

**Activity ID**: 44
**Order**: 3
**Phase**: Inception
**Dependencies**: Predecessor: Activity 43 (Define Application Blocks)

## Description

Define Integration & API Design

## Guidance

# Define Integration & API Design

## Objective

Choose API style, versioning strategy, contract approach, external integration patterns, and inter-service communication model.

---

## Decisions to Make

### 1. API Style

Choose one or hybrid:
- **REST** — Resource-oriented, HTTP verbs, JSON. Best for: standard CRUD web apps.
- **GraphQL** — Query language, single endpoint. Best for: complex data fetching, mobile clients.
- **gRPC** — Binary protocol, protobuf. Best for: internal service-to-service, high throughput.
- **MCP (Model Context Protocol)** — stdio-based, tool-oriented. Best for: AI agent integration.
- **Hybrid** — e.g., REST for web UI + MCP for AI agents.

### 2. API Versioning Strategy

Choose one:
- **URL path** — `/api/v1/playbooks/` → simple, visible, easy to route
- **Header** — `Accept: application/vnd.mimir.v1+json` → clean URLs
- **Query param** — `/api/playbooks/?version=1` → easy to test
- **No versioning** — acceptable for internal-only APIs in early stages

### 3. Contract Approach

Choose one:
- **Contract-first** — Write OpenAPI/AsyncAPI spec first, generate code from it
- **Code-first** — Write code first, generate spec from annotations/decorators
- **No formal contract** — acceptable for internal APIs with single consumer

### 4. External Integrations

- Identify 3rd party APIs the system consumes (if any)
- Define webhook patterns (inbound/outbound)
- Define event bus usage (if applicable)
- Define retry and error handling for external calls

### 5. Inter-Service Communication

If multiple services/processes exist:
- **Sync (HTTP/gRPC)** — Request-response. Simple but creates coupling.
- **Async (Message Queue)** — Fire-and-forget. Decoupled but complex.
- **Shared Database** — Both processes read/write same DB. Simple but limits scaling.
- **File-based** — Export/import via files. Simple for batch scenarios.

### 6. Implementation Patterns (document during/after implementation)

For each chosen API style, document recurring implementation patterns as they emerge:

- **Service-to-transport mapping** — How business logic maps to API endpoints/tools. Example: thin controller/tool wrapping a service method.
- **Sync/async boundary** — If the API layer is async but business logic is sync (or vice versa), document the bridging pattern and any pitfalls discovered.
- **Protocol-specific constraints** — Transport-layer constraints that affect architecture. Examples: stdio pollution in MCP, CORS in REST, N+1 in GraphQL.
- **Shared service layer** — If multiple transports (e.g., web UI + API + MCP) share business logic, document how the service layer is structured to serve all consumers.
- **Error propagation** — How errors from the service layer translate to API responses per transport (HTTP status codes, MCP error objects, gRPC status codes).

> **Note**: This subsection starts as placeholder during DTA. Populate it during implementation and feed findings back into SAO.md via the "Discovered Patterns" section (DTA-18).

### 7. Scan Skills

Query Playbook Skills where `capability_domain` in:
- `API_REST`
- `API_GRAPHQL`
- `API_GRPC`
- `API_CONTRACT`

Report coverage and gaps.

---

## Deliverables

- ✅ **API style** chosen with rationale
- ✅ **Versioning strategy** defined
- ✅ **Contract approach** selected
- ✅ **External integrations** identified and patterns defined
- ✅ **Inter-service communication** model chosen (if applicable)
- ✅ **Implementation patterns** placeholder created (populated during/after implementation)
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

- **Validate Api Contracts** (`do-validate-api-contracts`)

## Artifacts Produced

None

## Artifacts Consumed

None

## Notes

No additional notes.
