# Activity: Wire CICD Integration

**Activity ID**: 191
**Order**: 5
**Phase**: Elaboration
**Dependencies**: Predecessor: Activity 190 (Build Fixture Library)
Successor: Activity 192 (Establish E2E Infrastructure)

## Description

Wire CICD Integration

## Guidance

# Wire CICD Integration

## Objective

Configure the CI/CD pipeline to run tests at appropriate stages: unit+integration+AT on CI (every push), E2E on staging (before release swap). Define pass/fail gates at each stage.

---

## Process

### 1. CI Pipeline Test Stages

Modify `.github/workflows/ci.yml` (DCD-04 artifact) to add acceptance test stage:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: make provision
      - name: Lint
        run: make lint
      - name: Unit tests
        run: make test-unit
      - name: Integration tests
        run: make test-integration
      - name: Acceptance tests          # NEW — TAF addition
        run: make test-at
```

**Gate:** All three test levels must pass before container build proceeds.

### 2. CD Pipeline E2E Stage

Modify `.github/workflows/cd.yml` (DCD-05 artifact) to add E2E stage on staging:

```yaml
  e2e-staging:
    needs: deploy-idle
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Playwright browsers
        run: playwright install chromium
      - name: Run E2E against staging
        run: make test-e2e BASE_URL=${{ vars.STAGING_URL }} DB_URI=${{ vars.STAGING_DB_URI }}
      - name: Upload screenshots
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-screenshots
          path: tests/e2e/screenshots/
```

**Gate:** E2E must pass on staging → create release → swap with prod.

### 3. Screenshot Archival

- E2E tests capture a screenshot after every step
- Screenshots uploaded as GitHub Actions artifacts for human review

## Agent

None

## Skill

None

## Rules

None

## Artifacts Produced

None

## Artifacts Consumed

- **SAO.md § Test Strategy** (Document) - Required
- **Step Library Catalog** (Document) - Required
- **Fixture Library Catalog** (Document) - Required

## Notes

No additional notes.
