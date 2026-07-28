# Activity: Implement Switch & Rollback

**Activity ID**: 86
**Order**: 6
**Phase**: Elaboration
**Dependencies**: Predecessor: Activity 85 (Build CD Pipeline)

## Description

Implement Switch & Rollback

## Guidance

# Implement Switch & Rollback

## Objective

Ensure traffic switch and rollback work reliably end-to-end. **Mechanism depends on deployment style.**

---

## Path Selection

| Style | Switch | Rollback |
|-------|--------|----------|
| **EKS** | `make switch` → infra `traffic-switch` (Route53 weights) | `make rollback` → infra `traffic-rollback` |
| **Elastic Beanstalk** | `make swap` → `promote-prod.sh` (CNAME swap) | **Another CNAME swap** — previous version still running on other env |

---

## EKS Path

Verify `make switch` and `make rollback` delegate to infra repo. Create `.github/workflows/rollback.yml` with confirmation gate calling `make rollback`.

---

## Elastic Beanstalk Path

**Skill**: AWS EB Blue/Green Deployment

### 1. Verify `make swap`

```makefile
swap: ## Promote idle → prod
	bash scripts/promote-prod.sh
```

Test: deploy to idle → `make swap` → prod `/health/` revision matches.

### 2. EB Rollback = Second Swap

No Helm rollback or Route53 weight change. The previously-live env still runs the old image:

```bash
# If prod is bad after swap:
make swap   # swaps back — old env becomes prod again
```

Document: rollback time ≈ CNAME swap + 90s DNS + smoke poll (~3 min max).

### 3. Create `promote.yml` (GitHub)

```yaml
name: Promote to Production
on:
  workflow_dispatch:
    inputs:
      expected_revision:
        description: 'Release tag or EB VersionLabel (optional)'
        required: false
jobs:
  promote:
    environment: production   # approval gate
    steps:
      - run: bash scripts/promote-prod.sh
        env:
          EB_APP: {project}
          EB_ENV_A: {project}-prod
          EB_ENV_B: {project}-idle
          EXPECTED_REVISION: ${{ inputs.expected_revision }}
          MIMIR_PROD_URL: https://app.example.com
```

### 4. Optional Emergency Rollback Workflow

`.github/workflows/rollback.yml` — same as promote (another swap), with confirmation input `type "rollback"`.

### 5. Runbook

Document in README:
- **Promote:** review idle URL → `gh workflow run promote.yml` or `make swap`
- **Rollback:** `make swap` again (no redeploy needed)
- **When:** smoke fails after promote, user reports, monitoring alerts

---

## Deliverables

- ✅ Switch verified for chosen style
- ✅ EB: rollback documented as second CNAME swap
- ✅ `promote.yml` with production approval gate
- ✅ Optional `rollback.yml` with confirmation
- ✅ Runbook documented
- ✅ Rollback time measured (< 3 min for EB)

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

None

## Artifacts Consumed

- **Helm Chart Template** (Template) - Required
- **CI Pipeline (GitHub Actions)** (Code) - Required
- **CD Pipeline (GitHub Actions)** (Code) - Required

## Notes

No additional notes.
