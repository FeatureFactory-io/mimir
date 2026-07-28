# Activity: Deploy & Verify Cloud Environment

**Activity ID**: 80
**Order**: 7
**Phase**: Elaboration
**Dependencies**: Predecessor: Activity 79 (Create Infra GH Workflow)

## Description

Deploy & Verify Cloud Environment

## Guidance

# Deploy & Verify Cloud Environment

## Objective

Run full infrastructure deployment, verify AWS resources, and confirm blue/green switching end-to-end. **Acceptance gate for DCI workflow.** Follow the path matching your deployment style.

---

## Path Selection

Refer to `INFRA_REQUIREMENTS.md` § Deployment Style.

---

## EKS Path

### 1. Full Deployment

```bash
cd {project}-infra && make deploy
```

Expected: ~20–25 min (EKS cluster dominates).

### 2. Verify VPC, EKS, ECR, DNS

```bash
kubectl get nodes          # 2 Ready
kubectl get ns             # blue, green
aws ecr describe-repositories
dig prod.{domain} && dig idle.{domain}
make traffic-switch && make traffic-rollback
```

### 3. Document in `docs/architecture/INFRA_VERIFICATION.md`

Use EKS checklist (VPC, subnets, NAT, EKS nodes, namespaces, ECR, Route53 weights, GH Actions deploy).

---

## Elastic Beanstalk Path

### 1. Full Deployment

```bash
cd infra && cdk deploy --all --require-approval never
```

Expected: ~10–15 min (no EKS).

### 2. Verify Platform Snapshot

```bash
python scripts/export_eb_live_settings.py
python scripts/diff_eb_live_vs_cdk.py
# Expect 0 platform diffs (secrets excluded)
```

### 3. Verify EB Environments

```bash
aws elasticbeanstalk describe-environments \
  --application-name {project} \
  --query 'Environments[].{Name:EnvironmentName,Status:Status,Health:Health,CNAME:CNAME,Version:VersionLabel}' \
  --output table
```

Both `{project}-prod` and `{project}-idle` should be `Ready`.

### 4. Verify ECR, DNS, Backups

```bash
# ECR push test
aws ecr get-login-password | docker login ...
docker push {account}.dkr.ecr.{region}.amazonaws.com/{project}:verify-test

# DNS: public domain → prod EB label
dig +short app.example.com

# S3 backup bucket exists
aws s3 ls s3://{project}-db-backups-{account}/

# SSM: EB instances managed
aws ssm describe-instance-information --filters Key=tag:elasticbeanstalk:environment-name,Values={project}-idle
```

### 5. End-to-End Blue/Green (with app pipeline)

Full acceptance requires app deploy — coordinate with DCD:

```bash
gh release create v0.0.1-test   # CI: deploy-idle.sh → idle smoke
curl http://{idle-cname}/health/  # revision matches
make swap                       # CNAME swap + prod smoke
curl https://app.example.com/health/
```

### 6. Document in `docs/architecture/INFRA_VERIFICATION.md`

| Check | Status | Details |
|-------|--------|---------|
| VPC / SG | ✅ | … |
| EB app + 2 envs | ✅ | Ready, Green/Yellow |
| Platform snapshot diff | ✅ | 0 diffs |
| ECR push/pull | ✅ | … |
| Route53 CNAME → prod label | ✅ | not ALB-alias |
| S3 backup bucket | ✅ | lifecycle 90d |
| SSM on EB instances | ✅ | SendCommand works |
| Idle deploy + smoke | ✅ | revision match |
| CNAME swap + prod smoke | ✅ | HTTPS revision match |

---

## Deliverables

- ✅ All CDK stacks deployed for chosen style
- ✅ Blue/green mechanism verified (Route53 weights **or** EB CNAME swap)
- ✅ **`docs/architecture/INFRA_VERIFICATION.md`** documented
- ✅ GH Actions infra deploy passing

## Agent

None

## Skill

**Title**: AWS Elastic Beanstalk Blue/Green Deployment

**Title**: K8s in EKS Deployment Patterns
**Capability Domain**: CONTAINER_ORCHESTRATION
**Technology Stack**: Kubernetes + AWS EKS

## Rules

None

## Artifacts Produced

- **INFRA Verification Checklist (EB Reference)** (Document) - Required

## Artifacts Consumed

- **Infra Repo Scaffold** (Template) - Required
- **CDK Stack Templates** (Code) - Required
- **Infra GH Actions Workflow** (Code) - Required

## Notes

No additional notes.
