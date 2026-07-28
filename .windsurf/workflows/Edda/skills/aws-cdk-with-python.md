# Skill: AWS CDK with Python

**Capability Domain**: INFRASTRUCTURE_AS_CODE
**Technology Stack**: AWS CDK + Python

## Overview

Reference patterns for building AWS infrastructure using CDK with Python. Covers **EKS** and **Elastic Beanstalk** deployment styles. All patterns follow CDK best practices: typed constructs, explicit dependencies, proper tagging.

Choose path per `INFRA_REQUIREMENTS.md` § Deployment Style.

---

## EKS Patterns (Patterns 1–8)

*(Existing patterns unchanged: VPC, EKS cluster, ECR, Route53 hosted zone, security groups, OIDC for GitHub Actions, CDK context, CDK testing, cost reference ~$160/mo baseline.)*

See playbook v39+ for full EKS pattern code blocks.

---

## Elastic Beanstalk Patterns

### Pattern 9: EB Application + Twin Environments

```python
from aws_cdk import Stack, aws_elasticbeanstalk as eb, aws_ecr as ecr, aws_iam as iam
from constructs import Construct

EB_SOLUTION_STACK = "64bit Amazon Linux 2023 v4.x running Docker"

class AppStack(Stack):
    def __init__(self, scope, id, *, vpc, eb_sg, acm_cert_arn, **kwargs):
        super().__init__(scope, id, **kwargs)
        # Reference existing ECR repo — do not recreate if CI already created it
        self.web_repo = ecr.Repository.from_repository_name(self, "EcrRepo", "{project}")
        self.app = eb.CfnApplication(self, "App", application_name="{project}")
        # Import pre-existing EB service/instance roles when migrating
        # Create env_a ({project}-prod) and env_b ({project}-idle) with option_settings
```

**Key decisions:**
- `from_repository_name` when ECR pre-exists — avoids "already exists" deploy failures
- Import existing IAM roles (`aws-elasticbeanstalk-ec2-role`) during brownfield migration
- Platform settings loaded from exported JSON snapshot (Pattern 11)

### Pattern 10: Route53 CNAME via Lambda UPSERT

Public domain CNAME → `{project}-prod.eba-xxxxx.elasticbeanstalk.com`.

Use Lambda custom resource (not raw `CnameRecord`) for idempotent UPSERT on re-deploy.

**Never** point Route53 at ALB ARN — breaks EB CNAME swap on promotion.

### Pattern 11: EB Platform Settings Export

Two sources of truth:

| What | Where |
|------|--------|
| Platform settings | `eb_live_platform_settings.json` (exported, committed) |
| Secrets | `infra/.env` at synth/deploy (gitignored) |

```python
# stacks/eb_env.py
EB_SECRET_KEYS = frozenset({"DATABASE_URL", "DJANGO_SECRET_KEY", ...})

def secret_env_values() -> dict[str, str]:
    load_dotenv("infra/.env")
    return {k: os.environ[k] for k in EB_SECRET_KEYS if os.environ.get(k)}
```

Refresh after console changes:

```bash
python infra/scripts/export_eb_live_settings.py
python infra/scripts/diff_eb_live_vs_cdk.py  # 0 diffs before deploy
```

### Pattern 12: Pre-Migrate Backup Stack

```python
class BackupsStack(Stack):
    # S3 bucket: {project}-db-backups-{account}
    # Lifecycle: expire pre-migrate/ prefix after 90 days
    # IAM: MimirDbBackup policy on aws-elasticbeanstalk-ec2-role
    # Attach AmazonSSMManagedInstanceCore for SSM SendCommand backup
```

Backup runs in **deploy-idle.sh** before `update-environment`, not in container entrypoint.

### Pattern 13: CI Deploy IAM User

Create `mimir-ci`-style user with scoped policy:
- `ecr:*` push to app repo
- `elasticbeanstalk:*` deploy
- `s3:PutObject` on EB bundle bucket + backup bucket list/verify
- `ssm:SendCommand` on EB instances for pre-deploy backup

Prefer OIDC over long-lived keys when feasible.

### EB Cost Reference

| Resource | Approximate Monthly Cost |
|----------|-------------------------|
| 2× EB t3.small Docker envs | ~$30–60 |
| NAT Gateway (1) | ~$30 + transfer |
| Route53 hosted zone | ~$0.50 |
| S3 backups | ~$1–5 |
| **Total (baseline)** | **~$65–95/month** |

---

## Common Pitfalls (Both Paths)

1. **EKS creation time** — ~15 min; don't abort early
2. **CDK drift** — don't modify CDK-managed resources in console without re-export
3. **EB: recreating ECR** — use `from_repository_name` for brownfield
4. **EB: ALB-alias Route53** — breaks CNAME swap; use EB label CNAME
5. **Removal policies** — `RETAIN` for ECR, S3 backups, databases
