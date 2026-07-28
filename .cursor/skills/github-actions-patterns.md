# Skill: GitHub Actions Patterns

**Capability Domain**: CI_CD
**Technology Stack**: GitHub Actions

## Overview

Reference patterns for CI/CD with GitHub Actions. Covers triggers, AWS auth (OIDC and access keys), environment protection, Makefile-first architecture, and **release-gated deploy (Huginn model)**.

---

## Existing Patterns 1–10

*(Unchanged: OIDC federation, ECR auth, environment protection rules, workflow triggers, Makefile-first, conditional jobs, job outputs, caching, badges, emergency rollback workflow.)*

---

## Pattern 11: Release-Gated Deploy (Huginn Model)

Pipeline runs **only on published GitHub Releases** (or manual dispatch). Pushes to `main` do not deploy.

```yaml
name: Build and Deploy

on:
  release:
    types: [published]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: make test

  build-and-push:
    needs: test
    steps:
      - run: # build ECR image + optional Docker Hub client image

  deploy-idle:
    needs: build-and-push
    if: vars.AWS_ACCOUNT_ID != ''
    steps:
      - run: bash scripts/deploy-idle.sh

# Promote is SEPARATE workflow — workflow_dispatch + production environment
```

**Release process:**

```bash
gh release create vX.Y.Z --title "..." --notes "..."
# CI: test → build → deploy-idle → idle smoke
# Human reviews idle URL
make swap   # or: gh workflow run promote.yml
```

**Why release-gated:**
- Explicit semver control
- Avoids concurrent EB deploy races
- Matches Huginn/GitLab promote-after-staging model

**When to use continuous (push) instead:** Fast-moving dev/staging, no EB concurrency concerns, feature branches need CI on every push.

---

## Pattern 12: Dual Registry Build

```yaml
# Web app → private ECR (deployed to EB/EKS)
- uses: docker/build-push-action@v5
  with:
    tags: ${{ steps.ecr.outputs.registry }}/myapp:${{ steps.tag.outputs.suffix }}

# Client tool (MCP facade) → public Docker Hub (NOT deployed to cloud)
- uses: docker/build-push-action@v5
  with:
    file: Dockerfile.mcp
    tags: myorg/myapp-mcp:${{ steps.tag.outputs.suffix }}
```

---

## Pattern 13: Auth — OIDC vs Access Keys

| Method | Setup | Best for |
|--------|-------|----------|
| **OIDC** | IAM role + `role-to-assume` | Org repos, no long-lived secrets |
| **Access keys** | `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` secrets | Single-team, simpler bootstrap |

Both are valid. Document choice in `CICD_REQUIREMENTS.md`. EB skill Pattern 3 uses access keys as the simpler default; upgrade to OIDC when ready.

---

## Pattern 14: Separate Promote Workflow

```yaml
# .github/workflows/promote.yml
on:
  workflow_dispatch:
    inputs:
      expected_revision:
        required: false

jobs:
  promote:
    environment: production
    steps:
      - run: bash scripts/promote-prod.sh
```

Never auto-promote to production after idle deploy — always require human review or environment approval.

---

## GitHub Environment Configuration

| Environment | Reviewers | Purpose |
|-------------|-----------|---------|
| `infrastructure` | 0–1 | CDK deploy |
| `staging` | None | Auto-deploy to idle (optional) |
| `production` | 1–2 | CNAME swap / traffic switch |

---

## Common Pitfalls

1. **Storing AWS keys when OIDC available** — prefer OIDC for org scale
2. **Business logic in YAML** — use Makefile
3. **Auto-promote to prod** — always gate
4. **Push + release both triggering deploy** — pick one trigger model
5. **workflow_run gotcha** — uses default branch workflow file
