# Activity: Define Infrastructure

**Activity ID**: 50
**Order**: 9
**Phase**: Inception
**Dependencies**: Predecessor: Activity 49 (Define Error Handling & Resilience)

## Description

Define Infrastructure

## Guidance

# Define Infrastructure

## Objective

Define the local development environment, cloud provider and compute model, networking setup, and Infrastructure as Code tooling.

---

## Decisions to Make

### 1. Local Development Environment

- **Containerization**: Docker, Podman, or native?
- **Dev/prod parity**: How close is local to production?
- **Makefile targets**: `make provision` (install all deps), `make run` (start everything)
- **Required tools**: Which CLI tools, SDKs, runtimes must be installed?
- **Environment variables**: How are they managed locally? (.env file, direnv)

### 2. Cloud Provider & Compute Model

Choose compute model:
- **Kubernetes (EKS/GKE/AKS)** — Container orchestration. Best for: complex deployments, auto-scaling.
- **Container service (ECS/Cloud Run)** — Managed containers. Best for: simpler container deployments.
- **Serverless (Lambda/Cloud Functions)** — Event-driven functions. Best for: sporadic workloads.
- **VMs (EC2/Compute Engine)** — Traditional. Best for: legacy apps, specific OS needs.
- **PaaS (Heroku/Railway/Render)** — Managed platform. Best for: fast start, less ops overhead.
- **Desktop only** — No cloud. Best for: single-user desktop applications.

### 3. Networking

- **VPC**: Network isolation, subnets (public/private)
- **DNS**: Domain management, Route53/Cloudflare
- **Load balancing**: ALB/NLB, health checks, SSL termination
- **CDN**: Static asset distribution, edge caching

### 4. Infrastructure as Code

Choose one:
- **AWS CDK** — TypeScript/Python, AWS-native. Best for: AWS-only, programmatic infra.
- **Terraform** — HCL, multi-cloud. Best for: cloud-agnostic, declarative.
- **Pulumi** — General-purpose languages. Best for: developers who prefer Python/TS.
- **CloudFormation** — YAML/JSON, AWS-native. Best for: simple AWS setups.
- **None** — Manual/console setup. Best for: prototypes, desktop apps.

### 5. Scan Skills

Query Playbook Skills where `capability_domain` in:
- `INFRA_LOCAL`
- `INFRA_CLOUD`
- `INFRA_K8S`

Report coverage and gaps.

---

## Deliverables

- ✅ **Local dev environment** defined with provisioning instructions
- ✅ **Cloud provider & compute model** chosen with rationale
- ✅ **Networking** architecture defined
- ✅ **IaC tool** selected
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
