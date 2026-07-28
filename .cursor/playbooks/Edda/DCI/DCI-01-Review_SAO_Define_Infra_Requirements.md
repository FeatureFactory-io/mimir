# Activity: Review SAO & Define Infra Requirements

**Activity ID**: 74
**Order**: 1
**Phase**: Elaboration
**Dependencies**: None

## Description

Review SAO & Define Infra Requirements

## Guidance

# Review SAO & Define Infra Requirements

## Objective

Read `docs/architecture/SAO.md`, identify the AWS services needed for the application, and produce a concise infrastructure requirements document that drives all subsequent CDK stack decisions.

---

## Process

### 1. Read SAO.md

Extract from SAO.md:

- **Technology Stack Table** — runtime versions, databases, caches, queues
- **§ Deployment Strategy** (DTA-14) — blue/green, canary, rolling
- **§ Infrastructure** (DTA-15) — cloud provider, region, compute platform
- **§ Observability** (DTA-13) — logging, metrics, tracing services

### 2. Map Application Needs → AWS Services

| Application Need | EKS Path | EB Path | CDK Stack |
|-----------------|----------|---------|----------|
| Container orchestration | EKS | Elastic Beanstalk | EKS Stack / EB Stack |
| Container registry | ECR | ECR | EKS Stack / EB Stack |
| Networking (VPC, subnets) | VPC | VPC | VPC Stack |
| DNS for blue/green | Route53 | Route53 (via CNAME swap) | DNS Stack / EB handles internally |
| NAT for private subnets | NAT Gateway | NAT Gateway | VPC Stack |
| TLS termination | ALB + ACM | EB managed ALB | EKS Stack (ingress) / EB handles |
| Secrets | AWS Secrets Manager or K8s Secrets | Secrets Manager or EB env properties | EKS Stack / EB Stack |
| Logging | CloudWatch Logs | CloudWatch Logs | EKS Stack (add-ons) / EB handles |

### 3. Choose Deployment Style

Read the infrastructure skills available in this playbook. Pick one based on SAO.md § Deployment Strategy and § Infrastructure decisions:

| Style | When to choose | Skill |
|---|---|---|
| Kubernetes / EKS | Multi-service, needs orchestration, team familiar with K8s | K8s in EKS Deployment Patterns (#23) |
| Elastic Beanstalk | Single-service Django/web app, small team, want managed infra | AWS EB Blue/Green Deployment |

Record the choice in `INFRA_REQUIREMENTS.md` under a new **"Deployment Style"** heading:

```markdown
## Deployment Style

**Chosen**: [EKS / Elastic Beanstalk]

**Rationale**: [Why this style fits the project — team size, service count, K8s familiarity, etc.]

**Skill Reference**: [Skill name and ID]
```

All subsequent DCI and DCD activities must be executed using the patterns from the chosen skill.

### 4. Document Infra Requirements

Create `docs/architecture/INFRA_REQUIREMENTS.md`. Tailor the content to your chosen deployment style:

#### EKS Path

```markdown
# Infrastructure Requirements

## AWS Region
{region from SAO.md, e.g., us-east-1}

## Deployment Style
**Chosen**: Kubernetes / EKS
**Rationale**: Multi-service architecture with microservices orchestration needs
**Skill Reference**: K8s in EKS Deployment Patterns (#23)

## Services Required
| Service | Purpose | Configuration |
|---------|---------|---------------|
| VPC | Network isolation | 2 public + 2 private subnets, NAT GW |
| EKS | Container orchestration | Managed node group, 2-3 nodes |
| ECR | Container registry | 1 repo per service |
| Route53 | DNS + blue/green switching | Hosted zone, prod/idle weighted records |

## Blue/Green Strategy
- Two namespaces: `blue`, `green`
- Route53 weighted records: `prod.{domain}` → active, `idle.{domain}` → standby
- Switch = swap DNS weights (0/100 ↔ 100/0)

## Cost Estimate
{Rough monthly cost for EKS + NAT + Route53}

## Security Requirements
- Private subnets for EKS nodes
- Security groups: EKS ↔ database, ALB ↔ EKS
- IAM roles: EKS node role, CDK deploy role
```

#### EB Path

```markdown
# Infrastructure Requirements

## AWS Region
{region from SAO.md, e.g., us-east-1}

## Deployment Style
**Chosen**: Elastic Beanstalk
**Rationale**: Single Django application, small team, prefer managed infrastructure
**Skill Reference**: AWS EB Blue/Green Deployment

## Services Required
| Service | Purpose | Configuration |
|---------|---------|---------------|
| VPC | Network isolation | 2 public + 2 private subnets, NAT GW |
| Elastic Beanstalk | Managed Docker platform | 2 environments: {project}-prod, {project}-idle |
| ECR | Container registry | 1 repo for web image |
| S3 | Deployment bundles | elasticbeanstalk-{region}-{account} |

## Blue/Green Strategy
- Two EB environments: `{project}-prod` (physical A), `{project}-idle` (physical B)
- CNAME swap: `swap-environment-cnames` flips prod ↔ idle roles
- Prod is whichever env currently holds the `{project}-prod` CNAME

## Environment Variables
- `EB_APP`: {project}
- `EB_ENV_A`: {project}-prod
- `EB_ENV_B`: {project}-idle
- `EB_BUCKET`: elasticbeanstalk-{region}-{account}

## Cost Estimate
{Rough monthly cost for 2 EB environments + NAT + S3}

## Security Requirements
- Private subnets for EB instances
- Security groups: EB ALB ↔ instances
- IAM roles: EB service role, instance profile
```

### 5. Validate with SAO.md

Cross-check: every service in INFRA_REQUIREMENTS.md must trace back to a decision in SAO.md. If SAO.md doesn't cover infra decisions, flag it and update DTA first.

---

## Deliverables

- ✅ **SAO.md reviewed** — infra-relevant sections extracted
- ✅ **Deployment style chosen** — EKS or EB, documented with rationale
- ✅ **AWS service mapping** — application needs → AWS services (both paths shown)
- ✅ **`docs/architecture/INFRA_REQUIREMENTS.md`** created (tailored to chosen style)
- ✅ **Blue/green strategy** documented (style-specific)
- ✅ **Cost estimate** included

## Inputs

Read these before starting this activity. They are produced earlier in the playbook and are authoritative — raise a drift event instead of deviating.

- **System Architecture Overview Template** (Template, Required) — produced by Write SAO.md (#59).

## Agent

None

## Skill

**Title**: AWS CDK with Python
**Capability Domain**: INFRASTRUCTURE_AS_CODE
**Technology Stack**: AWS CDK + Python

## Rules

None

## Artifacts Produced

- **INFRA Requirements (EB Reference)** (Document) - Required

## Artifacts Consumed

- **System Architecture Overview Template** (Document) - Required

## Notes

No additional notes.
