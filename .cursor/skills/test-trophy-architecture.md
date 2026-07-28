# Skill: Test Trophy Architecture

**Capability Domain**: TEST_STRATEGY
**Technology Stack**: pytest+behave

## Overview

Integration-first testing philosophy replacing the traditional test pyramid. The "trophy" shape reflects where we invest most: thick integration tests in the middle, thin unit tests at the base, acceptance tests above, and selective E2E at the top.

## The Test Trophy Model

```
        ╱╲          E2E (selective, slow, staging only)
       ╱────╲        Acceptance Tests (behave, BDD .features)
      ╱════════╲     INTEGRATION TESTS (main bet, no mocking)
     ╱──────────╲    Unit Tests (thin, only where isolation helps)
    ════════════════  Static Analysis (linting, type checks)
```

## Why Not the Pyramid?

1. **Unit tests have limited value**: Testing `model.save()` returns OK tells us nothing about whether data persisted.
2. **Acceptance tests are expensive**: Real browser, slow, flaky.
3. **Integration tests are the sweet spot**: Real objects, real connections, real data. Fast enough for CI, thorough enough to catch real bugs.

## When Unit Tests ARE Valuable

- Custom QuerySet methods with complex filtering logic
- Pure utility/helper functions with interesting edge cases
- Business logic methods that do computation (not just DB operations)

## When Unit Tests ARE NOT Valuable

- Default Model CRUD
- Auto-generated admin views
- Framework behavior
- Anything that requires mocking to test in isolation
