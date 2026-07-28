# Activity: Review SAO & Define CICD Requirements

**Activity ID**: 81
**Order**: 1
**Phase**: Elaboration
**Dependencies**: None

## Description

Review SAO & Define CICD Requirements

## Guidance

# Review SAO & Define CICD Requirements

## Objective

Read `docs/architecture/SAO.md` and DCI output. Define pipeline stages, map to `make` targets, produce `CICD_REQUIREMENTS.md`. **Pipeline shape depends on deployment style.**

---

## Process

### 1. Read SAO.md

Extract § Deployment Strategy, § Test Strategy, § CI/CD Pipeline.

### 2. Review DCI Output

| Style | Confirm available |
|-------|-------------------|
| **EKS** | Cluster name, ECR URI, Route53 domain, `make traffic-switch` |
| **Elastic Beanstalk** | EB app/env names, ECR URI, `deploy-idle.sh`, `make swap`, S3 backup bucket |

### 3. Choose Trigger Model

| Model | When | Trigger |
|-------|------|---------|
| **Continuous** | Fast iteration, trunk-based | Push to `main` → test + build |
| **Release-gated (Huginn)** | Production control, semver releases | `gh release create vX.Y.Z` → test + build + deploy-idle |

Document choice in `CICD_REQUIREMENTS.md`.

### 4. Map Pipeline Stages → Make Targets

#### EKS Path

| Stage | Target | Gate |
|-------|--------|------|
| Test | `make test` | All pass |
| Build | `make containers` | ECR push |
| Deploy idle | `make deploy ENV=idle` | Pods healthy |
| Smoke | `make smoke-test ENV=idle` | Pass |
| Switch | `make switch` → infra `traffic-switch` | Manual approval |
| Verify prod | `make smoke-test ENV=prod` | Pass |

#### Elastic Beanstalk Path

| Stage | Target | Gate |
|-------|--------|------|
| Test | `make test` | All pass |
| Build | CI: ECR push (+ optional Docker Hub for client tools) | Images pushed |
| Backup | `deploy-idle.sh` step 2 (SSM) | S3 keys exist |
| Deploy idle | `deploy-idle.sh` | EB Ready, Health ≠ Red |
| Smoke | `/health/` revision on idle CNAME | Match `GIT_REVISION` |
| Promote | `make swap` or `promote.yml` | Manual approval |
| Verify prod | `/health/` on HTTPS custom domain | Revision match |

### 5. Document CICD Requirements

Create `docs/architecture/CICD_REQUIREMENTS.md` — see artifact template **CICD Requirements (EB Reference)**.

---

## Deliverables

- ✅ SAO.md reviewed
- ✅ DCI output confirmed for chosen style
- ✅ Trigger model documented (continuous vs release-gated)
- ✅ Pipeline stages mapped to make targets
- ✅ `CICD_REQUIREMENTS.md` created

## Agent

None

## Skill

**Title**: GitHub Actions Patterns
**Capability Domain**: CI_CD
**Technology Stack**: GitHub Actions

## Rules

None

## Artifacts Produced

- **CICD Requirements (Release-Gated EB Reference)** (Document) - Required

## Artifacts Consumed

- **System Architecture Overview Template** (Document) - Required

## Notes

No additional notes.
