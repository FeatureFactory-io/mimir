# Infrastructure Verification

**Project**: {project}
**Deployment Style**: Elastic Beanstalk
**Verified**: {date}
**Verified By**: {name}

## CDK Stacks
| Stack | Status | Notes |
|-------|--------|-------|
| Network (VPC, SG) | ☐ | |
| App (EB, ECR ref, CI IAM) | ☐ | Both envs Ready |
| Backups (S3, SSM) | ☐ | Bucket + lifecycle 90d |
| SES | ☐ | Optional |
| DNS (Route53 CNAME) | ☐ | Points to `{project}-prod.eba-…`, not ALB ARN |

## Platform Snapshot
| Check | Status | Notes |
|-------|--------|-------|
| `export_eb_live_settings.py` run | ☐ | |
| `diff_eb_live_vs_cdk.py` → 0 diffs | ☐ | Secrets excluded |

## EB Environments
| Env | Status | Health | CNAME | VersionLabel |
|-----|--------|--------|-------|--------------|
| `{project}-prod` | ☐ | ☐ | ☐ | ☐ |
| `{project}-idle` | ☐ | ☐ | ☐ | ☐ |

## ECR
| Check | Status | Notes |
|-------|--------|-------|
| Push test image | ☐ | |
| Pull from EB instance role | ☐ | |

## DNS & TLS
| Check | Status | Notes |
|-------|--------|-------|
| `dig app.example.com` → prod EB label | ☐ | |
| HTTPS /health/ on prod domain | ☐ | ACM on ALB :443 |
| HTTP /health/ on idle CNAME | ☐ | Used for CI smoke |

## Backup & SSM
| Check | Status | Notes |
|-------|--------|-------|
| SSM managed instances | ☐ | Both EB envs |
| Manual `make backup` → S3 | ☐ | |
| CI backup in deploy-idle.sh | ☐ | Fail-closed |

## End-to-End Blue/Green
| Step | Status | Notes |
|------|--------|-------|
| `gh release create` → deploy-idle | ☐ | |
| Idle smoke revision match | ☐ | |
| `make swap` → prod smoke | ☐ | Wait ≥90s after swap |
| Rollback (second swap) tested | ☐ | Old version still on other env |

## GitHub Actions
| Workflow | Status | Notes |
|----------|--------|-------|
| build-and-deploy on release | ☐ | |
| promote.yml manual + approval | ☐ | |
| infra.yml on infra/ changes | ☐ | Optional |
