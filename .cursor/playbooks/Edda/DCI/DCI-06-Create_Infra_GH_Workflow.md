# Activity: Create Infra GH Workflow

**Activity ID**: 79
**Order**: 6
**Phase**: Elaboration
**Dependencies**: Predecessor: Activity 78 (Build Route53 & DNS Stack)

## Description

Create Infra GH Workflow

## Guidance

# Create Infra GitHub Actions Workflow

## Objective

Create a GitHub Actions workflow that automates **CDK infrastructure deployment**. Traffic switching is **not** in this workflow for EB — it lives in the app repo (`make swap` / `promote.yml`).

---

## Path Selection

| Style | Infra workflow scope | Traffic switch location |
|-------|---------------------|------------------------|
| **EKS** | `cdk deploy` + optional `traffic-switch` job | Infra repo `make traffic-switch` |
| **Elastic Beanstalk** | `cdk deploy` only | App repo `promote.yml` or `make swap` |

---

## Shared Pattern: Thin Wrapper Around Make

```yaml
name: Infrastructure

on:
  push:
    branches: [main]
    paths:
      - 'infra/**'      # monorepo layout
      # OR 'stacks/**'  # separate infra repo
      - 'cdk.json'
  workflow_dispatch:
    inputs:
      action:
        type: choice
        options: [deploy, status]

permissions:
  id-token: write
  contents: read

jobs:
  infra:
    runs-on: ubuntu-latest
    environment: infrastructure
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: make provision
      - run: make deploy   # or: cd infra && cdk deploy --all
```

> **Auth:** Prefer OIDC (`role-to-assume`). IAM access keys acceptable for single-team projects — see GitHub Actions Patterns skill § Release-Triggered Deploy.

---

## EKS Path Additions

Add manual `traffic-switch` and `traffic-rollback` jobs with `environment: production` approval gate:

```yaml
  traffic-switch:
    if: github.event.inputs.action == 'traffic-switch'
    environment: production
    steps:
      - run: make traffic-switch
```

---

## Elastic Beanstalk Path

**Do not** add traffic-switch to infra workflow. Document in README:

```markdown
## Infra vs App deploy

- **Infra** (this workflow): `cdk deploy --all` — VPC, EB envs, DNS CNAME, backups bucket
- **App** (build-and-deploy.yml): test → ECR push → deploy-idle.sh → smoke
- **Promote** (promote.yml or `make swap`): CNAME swap after human review
```

Refresh platform snapshot after console EB changes:

```bash
python infra/scripts/export_eb_live_settings.py
python infra/scripts/diff_eb_live_vs_cdk.py  # expect 0 diffs before deploy
```

---

## GitHub Environments

| Environment | Reviewers | Used for |
|-------------|-----------|----------|
| `infrastructure` | 0–1 | CDK deploy |
| `production` | 1–2 | EKS traffic-switch **or** app promote.yml |

---

## Deliverables

- ✅ `.github/workflows/infra.yml` (or in `infra/.github/…` for separate repo)
- ✅ CDK deploy on infra path changes
- ✅ EB: no traffic-switch in infra workflow
- ✅ EKS: optional traffic-switch with production approval
- ✅ Workflow tested

## Agent

None

## Skill

**Title**: GitHub Actions Patterns
**Capability Domain**: CI_CD
**Technology Stack**: GitHub Actions

## Rules

None

## Artifacts Produced

- **Infra GH Actions Workflow** (Code) - Required

## Artifacts Consumed

- **Infra Repo Scaffold** (Template) - Required
- **CDK Stack Templates** (Code) - Required

## Notes

No additional notes.
