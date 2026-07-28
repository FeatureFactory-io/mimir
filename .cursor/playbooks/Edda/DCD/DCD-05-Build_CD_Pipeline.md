# Activity: Build CD Pipeline

**Activity ID**: 85
**Order**: 5
**Phase**: Elaboration
**Dependencies**: Predecessor: Activity 84 (Build CI Pipeline)

## Description

Build CD Pipeline

## Guidance

APPEND TO GUIDANCE:

---

## TAF Integration: E2E Staging Gate in CD

Add an E2E test stage in the CD pipeline that runs after deploying to the idle/staging environment and before the release/swap:

```yaml
  e2e-staging:
    needs: smoke-test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
      - name: Install dependencies
        run: make provision
      - name: Install Playwright
        run: playwright install chromium
      - name: Run E2E against staging
        run: make test-e2e BASE_URL=${{ vars.STAGING_URL }} DB_URI=${{ vars.STAGING_DB_URI }}
      - name: Upload E2E screenshots
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-screenshots-${{ github.sha }}
          path: tests/e2e/screenshots/
          retention-days: 14

  release:
    needs: e2e-staging
```

### Pipeline Flow (updated)

```
CI: lint → test-unit → test-integration → test-at → build container → push to ECR
CD: deploy-idle → smoke → E2E on staging (screenshots) → release → approve → switch → verify-prod
```

E2E fail → pipeline stops → no release → no swap. Screenshots are always archived for debugging.

## Agent

None

## Skill

**Title**: AWS Elastic Beanstalk Blue/Green Deployment

**Title**: GitHub Actions Patterns
**Capability Domain**: CI_CD
**Technology Stack**: GitHub Actions

## Rules

None

## Artifacts Produced

- **CD Pipeline (GitHub Actions)** (Code) - Required

## Artifacts Consumed

- **CICD Requirements (Release-Gated EB Reference)** (Document) - Required
- **Helm Chart Template** (Template) - Required

## Notes

No additional notes.
