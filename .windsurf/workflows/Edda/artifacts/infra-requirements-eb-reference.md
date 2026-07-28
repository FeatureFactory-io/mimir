# Infrastructure Requirements

## AWS Region
{region, e.g. us-east-1}

## Deployment Style
**Chosen**: Elastic Beanstalk
**Rationale**: Single web application, small team, prefer managed infrastructure over K8s ops
**Skill Reference**: AWS Elastic Beanstalk Blue/Green Deployment

## Repo Layout
- [ ] Separate `{project}-infra` repo
- [x] `infra/` in application monorepo

## Services Required
| Service | Purpose | Configuration |
|---------|---------|---------------|
| VPC | Network isolation | Lookup existing or 2 public + 2 private subnets, NAT GW |
| Elastic Beanstalk | Managed Docker platform | 2 envs: `{project}-prod`, `{project}-idle` |
| ECR | Container registry | 1 repo for web image (reference existing if brownfield) |
| S3 | Deployment bundles + DB backups | `elasticbeanstalk-{region}-{account}`, `{project}-db-backups-{account}` |
| Route53 | Public DNS | CNAME → `{project}-prod.eba-….elasticbeanstalk.com` |
| SES | Transactional email | Configuration set + verified domain (optional) |
| SSM | Pre-deploy backup | `AmazonSSMManagedInstanceCore` on EB instance role |

## Blue/Green Strategy
- Two EB environments: `{project}-prod` (physical A), `{project}-idle` (physical B)
- CNAME swap via `swap-environment-cnames` — prod is whichever env holds `{project}-prod` label
- Route53 public CNAME points at fixed EB label — **not** ALB ARN
- Deploy always to idle (resolved by CNAME inspection, not env name)

## Environment Variables (CI/CD)
| Var | Example |
|-----|---------|
| `EB_APP` | `{project}` |
| `EB_ENV_A` | `{project}-prod` |
| `EB_ENV_B` | `{project}-idle` |
| `EB_BUCKET` | `elasticbeanstalk-{region}-{account}` |
| `S3_BACKUP_BUCKET` | `{project}-db-backups-{account}` |

## Secrets Management
| Source | What |
|--------|------|
| `eb_live_platform_settings.json` | Platform settings (exported from live, no secrets) |
| `infra/.env` at `cdk deploy` | `DATABASE_URL`, `DJANGO_SECRET_KEY`, API keys |
| CI `deploy-idle.sh` | `{PROJECT}_GIT_REVISION`, optional `GITHUB_TOKEN` from `GH_BUG_REPORT_TOKEN` |

## Cost Estimate
~$65–95/month (2 EB envs + NAT + Route53 + S3)

## Security Requirements
- Private subnets for EB instances
- Security groups: ALB ↔ instances, EB ↔ RDS
- IAM: EB service role, instance profile (ECR read, SES send, S3 backup, SSM)
- CI IAM user scoped to ECR push, EB deploy, SSM SendCommand, S3 verify
