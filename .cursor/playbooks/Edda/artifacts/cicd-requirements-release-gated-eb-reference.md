# CI/CD Requirements

## Trigger Model
**Chosen**: Release-gated (Huginn model)
**Rationale**: Explicit semver control, avoids concurrent EB deploy races

```bash
gh release create vX.Y.Z  # sole production deploy trigger
```

Push to `main` does **not** run deploy jobs.

## Pipeline Architecture

```
gh release create vX.Y.Z
  → test (pytest)
  → build (ECR web + Docker Hub client image)
  → deploy-idle (SSM backup → EB deploy → idle smoke)
  → human review idle URL
  → make swap / promote.yml (production approval)
  → prod smoke (HTTPS /health/ revision)
```

## Make Targets
| Target | Description | Added By |
|--------|-------------|----------|
| `make test` | All tests | BSP |
| `make lint` | Linting | BSP |
| `make swap` | EB CNAME promote | DCD |
| `make eb-status` | Show both EB envs | DCD |
| `make backup` | Manual pre-migrate backup | DCD |

## GitHub Workflows
| File | Trigger | Purpose |
|------|---------|---------|
| `build-and-deploy.yml` | release, workflow_dispatch | test + build + deploy-idle |
| `promote.yml` | workflow_dispatch | CNAME swap + prod smoke |
| `infra.yml` (optional) | push to `infra/**` | CDK deploy only |

## Environments
| Name | URL | Purpose |
|------|-----|---------|
| idle (dynamic) | `http://{idle-cname}.elasticbeanstalk.com` | Staging after deploy |
| prod | `https://app.example.com` | Live traffic |

## Image Tagging
- Tag: `{branch-slug}-{short-sha}` (e.g. `v0.0.41-abc1234`)
- EB VersionLabel: `v-{branch}-{sha}-r{run_number}`
- Release revision: tag name (e.g. `v0.0.41`) stored as `{PROJECT}_GIT_REVISION`

## Quality Gates
| Gate | Criteria |
|------|----------|
| Test | All pytest pass |
| Backup | S3 keys under `pre-migrate/{revision}/` |
| Idle smoke | HTTP 200, revision match |
| Prod smoke | HTTPS 200, revision match after swap |

## Secrets
| Secret | Purpose |
|--------|---------|
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | EB/ECR/S3/SSM (or OIDC) |
| `GH_BUG_REPORT_TOKEN` | Mapped to `GITHUB_TOKEN` on EB at deploy |
| `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` | Client MCP image |
