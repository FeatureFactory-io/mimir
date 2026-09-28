# Activity: Build Route53 & DNS Stack

**Activity ID**: 78
**Order**: 5
**Phase**: Elaboration
**Dependencies**: Predecessor: Activity 77 (Build Compute & Container Registry Stack)

## Description

Build Route53 & DNS Stack

## Guidance

# Build Route53 & DNS Stack

## Objective

Implement DNS for blue/green traffic routing. **Implementation differs by deployment style** — do not mix patterns.

---

## Path Selection

Refer to `INFRA_REQUIREMENTS.md` § Deployment Style.

| Style | DNS model | Switch mechanism |
|-------|-----------|------------------|
| **EKS** | Weighted records: `prod.{domain}`, `idle.{domain}` | `traffic_switch.py` swaps weights |
| **Elastic Beanstalk** | Single CNAME: `{domain}` → `{project}-prod.eba-…` | EB `swap-environment-cnames` (no Route53 edit on promote) |

---

## EKS Path

**Skill**: AWS CDK with Python § Route53 Hosted Zone

### 1. Implement `stacks/dns_stack.py`

Create hosted zone. Weighted prod/idle records managed by `scripts/traffic_switch.py` (not CDK) to avoid drift.

### 2. Create `scripts/traffic_switch.py`

Actions: `switch`, `rollback`, `status` — swap Route53 weighted record targets.

### 3. Infra Makefile targets

```makefile
traffic-switch:  ## Swap prod/idle DNS weights
	python scripts/traffic_switch.py --action switch
traffic-rollback: ## Restore previous weights
	python scripts/traffic_switch.py --action rollback
```

### 4. Verify

```bash
dig prod.{domain}
dig idle.{domain}
make traffic-switch && dig prod.{domain}  # target changed
```

---

## Elastic Beanstalk Path

**Skill**: AWS EB Blue/Green Deployment § Pattern 7: Route53 for EB

### 1. DNS Mental Model

```
Public:  https://app.example.com
           ↓ Route53 CNAME (TTL 60s)
         app-prod.eba-xxxxx.elasticbeanstalk.com   ← fixed label name
           ↓ EB swap-environment-cnames
         whichever physical env currently owns that label
```

**Critical:** Route53 must point at the **EB environment CNAME label** (`{project}-prod.eba-…`), **not** the ALB ARN directly. ALB-alias breaks CNAME swap — live traffic won't follow promotion.

### 2. Implement `stacks/dns_stack.py`

Use an **idempotent Lambda custom resource** to UPSERT the CNAME (avoids `ConflictingResourceExists` on re-deploy):

```python
# Route53 CNAME: app.example.com → {project}-prod.eba-xxxxx.elasticbeanstalk.com
# Lambda handler: ListResourceRecordSets + ChangeResourceRecordSets (UPSERT)
```

HTTPS terminates at the EB-managed ALB (ACM cert on :443 listener). No CloudFront required for basic setup.

### 3. No traffic_switch.py for EB

Promotion is **only** `aws elasticbeanstalk swap-environment-cnames` (see EB skill Pattern 2). Route53 record stays fixed; EB rotates which env owns the `{project}-prod` label.

### 4. Verify

```bash
dig +short app.example.com
# Must resolve to whichever env currently holds app-prod.eba-… label

make swap   # in app repo
sleep 90    # Route53 TTL + resolver cache
dig +short app.example.com  # same CNAME label, different backend env
```

---

## Deliverables

- ✅ **EKS**: hosted zone + `traffic_switch.py` + make targets
- ✅ **EB**: CNAME to prod EB label via idempotent Lambda UPSERT
- ✅ **EB**: documented why ALB-alias Route53 breaks swap
- ✅ CDK tests passing
- ✅ DNS resolving correctly for chosen style

## Agent

None

## Skill

**Title**: AWS CDK with Python
**Capability Domain**: INFRASTRUCTURE_AS_CODE
**Technology Stack**: AWS CDK + Python

## Rules

None

## Artifacts Produced

None

## Artifacts Consumed

- **Infra Repo Scaffold** (Template) - Required
- **CDK Stack Templates** (Code) - Required

## Notes

No additional notes.
