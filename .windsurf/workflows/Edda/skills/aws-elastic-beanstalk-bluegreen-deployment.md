# Skill: AWS Elastic Beanstalk Blue/Green Deployment

**Capability Domain**: CI_CD
**Technology Stack**: AWS Elastic Beanstalk + ECR + GitHub Actions

## Overview

Reference patterns for deploying applications to AWS Elastic Beanstalk using a two-environment CNAME-swap blue/green model. One environment always holds the `prod` CNAME (live traffic); the other is `idle` (staging). Deployments always go to idle first, are smoke-tested, then promoted by swapping CNAMEs. Roles flip on every swap — no environment is permanently "prod" or "idle".

## Mental Model

```
  EB_ENV_A ({project}-prod)   ↔   EB_ENV_B ({project}-idle)
       ↑                              ↑
  CNAME: {project}-prod.*       CNAME: {project}-idle.*

Live = whichever env currently owns the {project}-prod CNAME.
Idle = the other one.
After swap-environment-cnames: roles are reversed.
```

- **Never hard-code** which physical env is prod — resolve at runtime by CNAME inspection.
- Both envs run the same Docker image (from ECR); only the CNAME differs.
- The EB application version is tracked by `VersionLabel` (e.g. `v-v0.0.41-abc1234-r42`).

## Pattern 1: Idle-First Deploy (`deploy-idle.sh`)

### 1a. Resolve live/idle dynamically

```bash
CNAME_A=$(aws elasticbeanstalk describe-environments \
  --application-name "$EB_APP" \
  --environment-names "$EB_ENV_A" \
  --query 'Environments[0].CNAME' --output text)

if echo "$CNAME_A" | grep -q "{project}-prod"; then
  LIVE_ENV="$EB_ENV_A"; IDLE_ENV="$EB_ENV_B"
else
  LIVE_ENV="$EB_ENV_B"; IDLE_ENV="$EB_ENV_A"
fi
echo "Deploying to idle: $IDLE_ENV"
```

**Critical**: grep pattern must match the exact prod subdomain prefix. A mismatch silently deploys to the wrong environment.

### 1b. Pre-deploy DB backup (fail-closed)

Before uploading bundle or calling `update-environment`:

```bash
bash scripts/run-eb-backup.sh   # SSM SendCommand on idle EC2
aws s3 ls "s3://${S3_BACKUP_BUCKET}/pre-migrate/${GIT_REVISION}/" --recursive | head -5
# Abort deploy if backup missing
```

Uses SSM to run `pre_deploy_backup` on idle host: `pg_dump` + `dumpdata` → S3. Requires `AmazonSSMManagedInstanceCore` on EB instance role.

### 1c. Upload bundle and create application version

```bash
S3_KEY="${EB_APP}/${VERSION_LABEL}/deploy-bundle.zip"
aws s3 cp "$DEPLOY_BUNDLE_PATH" "s3://${EB_BUCKET}/${S3_KEY}" --quiet

EXISTS=$(aws elasticbeanstalk describe-application-versions \
  --application-name "$EB_APP" \
  --version-labels "$VERSION_LABEL" \
  --query "length(ApplicationVersions)" --output text)
[ "${EXISTS}" = "0" ] && aws elasticbeanstalk create-application-version \
  --application-name "$EB_APP" \
  --version-label "$VERSION_LABEL" \
  --source-bundle "S3Bucket=${EB_BUCKET},S3Key=${S3_KEY}" \
  --no-auto-create-application --output text > /dev/null
```

### 1d. Deploy and poll until Ready

```bash
OPTION_SETTINGS="Namespace=aws:elasticbeanstalk:application:environment,OptionName={PROJECT}_GIT_REVISION,Value=${GIT_REVISION}"
# Optional: propagate GH_BUG_REPORT_TOKEN → GITHUB_TOKEN on EB env
if [ -n "${GH_BUG_REPORT_TOKEN:-}" ]; then
  OPTION_SETTINGS="${OPTION_SETTINGS} Namespace=aws:elasticbeanstalk:application:environment,OptionName=GITHUB_TOKEN,Value=${GH_BUG_REPORT_TOKEN}"
fi

aws elasticbeanstalk update-environment \
  --application-name "$EB_APP" \
  --environment-name "$IDLE_ENV" \
  --version-label "$VERSION_LABEL" \
  --option-settings ${OPTION_SETTINGS} \
  --output text > /dev/null

for i in $(seq 1 40); do
  STATUS=$(aws elasticbeanstalk describe-environments ... --query "Environments[0].Status" --output text)
  HEALTH=$(aws elasticbeanstalk describe-environments ... --query "Environments[0].Health" --output text)
  [ "${STATUS}" = "Ready" ] && { [ "${HEALTH}" = "Red" ] && exit 1 || break; }
  sleep 15
done
```

> Use `{PROJECT}_GIT_REVISION` env var (e.g. `MIMIR_GIT_REVISION`) — set by CI, read by `/health/`.

### 1e. Smoke-test idle — verify revision

```bash
HTTP_STATUS=$(curl -o /tmp/idle-health.json -s -w "%{http_code}" \
  --max-time 30 --retry 15 --retry-delay 10 --retry-all-errors \
  "http://${IDLE_CNAME}/health/")
ACTUAL=$(python3 -c 'import json; print(json.load(open("/tmp/idle-health.json")).get("revision","unknown"))')
[ "$ACTUAL" != "$GIT_REVISION" ] && exit 1
echo "Idle smoke OK. Run 'make swap' to promote."
```

## Pattern 2: CNAME Swap & Prod Smoke (`promote-prod.sh`)

### 2a. Revision guard

Accept **release tag** (e.g. `v0.0.47`) **or** EB VersionLabel (e.g. `v-v0.0.47-abc-r42`):

```bash
IDLE_LABEL=$(aws elasticbeanstalk describe-environments ... --query 'Environments[0].VersionLabel' --output text)
IDLE_REVISION=$(curl -s "http://${IDLE_CNAME}/health/" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("revision",""))')

if [ -n "${EXPECTED_REVISION:-}" ]; then
  [ "$EXPECTED_REVISION" != "$IDLE_REVISION" ] && [ "$EXPECTED_REVISION" != "$IDLE_LABEL" ] && exit 1
fi
EXPECTED_REVISION="${EXPECTED_REVISION:-$IDLE_REVISION}"
```

### 2b. Swap CNAMEs

```bash
aws elasticbeanstalk swap-environment-cnames \
  --source-environment-name "$IDLE_ENV" \
  --destination-environment-name "$LIVE_ENV"
sleep 90   # Route53 TTL 60s + resolver cache — do not shorten
```

### 2c. Poll prod URL until revision matches

Poll `https://app.example.com/health/` up to 18×10s for HTTP 200 + revision match.

## Pattern 3: GitHub Actions Wiring

Release-triggered (Huginn model), not push-triggered:

```yaml
on:
  release:
    types: [published]
  workflow_dispatch:

jobs:
  test: { ... }
  build-and-push:
    needs: test
    # ECR: web image; Docker Hub: client-side MCP facade (not deployed to EB)
  deploy-idle:
    needs: build-and-push
    if: vars.AWS_ACCOUNT_ID != ''
    run: bash scripts/deploy-idle.sh

# Separate promote.yml — workflow_dispatch only
# environment: production (approval gate)
```

## Pattern 4: Required Secrets & Variables

| Name | Type | Description |
|------|------|-------------|
| `AWS_ACCESS_KEY_ID` | Secret | IAM key (or use OIDC) |
| `AWS_SECRET_ACCESS_KEY` | Secret | IAM secret |
| `DOCKERHUB_USERNAME` | Secret | For MCP facade image (optional) |
| `DOCKERHUB_TOKEN` | Secret | Docker Hub token |
| `GH_BUG_REPORT_TOKEN` | Secret | PAT → mapped to `GITHUB_TOKEN` on EB at deploy |
| `AWS_ACCOUNT_ID` | Variable | S3 bucket + ECR URI construction |
| `S3_BACKUP_BUCKET` | Variable | Pre-migrate backup bucket |

## Pattern 5: Smoke-Test Contract

`GET /health/` → `{"status":"ok","revision":"<GIT_REVISION>"}`. Idle uses HTTP on EB CNAME; prod uses HTTPS on custom domain.

## Pattern 6: Pre-Deploy Backup via SSM

Order: resolve idle → SSM backup → verify S3 → upload bundle → update-environment → migrate in entrypoint → smoke.

S3 layout: `s3://{bucket}/pre-migrate/{GIT_REVISION}/{timestamp}/mimir.sql.gz`

Manual: `make backup` (requires `DATABASE_URL`, `S3_BACKUP_BUCKET`).

## Pattern 7: Route53 for EB

Public domain CNAME → `{project}-prod.eba-….elasticbeanstalk.com` (fixed label).

Promotion = EB CNAME swap only. Route53 record unchanged.

**Anti-pattern:** Route53 A-alias to ALB ARN — swap has no effect on live traffic.

## Pattern 8: CDK Platform Snapshot

Export live EB settings (no secrets) → `eb_live_platform_settings.json`.
Diff before deploy: `diff_eb_live_vs_cdk.py` → 0 platform diffs.
Secrets via `infra/.env` at `cdk deploy`.

## Common Pitfalls

1. **Wrong CNAME grep pattern** — deploys to live env
2. **DNS sleep too short** — prod smoke hits old env
3. **Hardcoded idle env name** — after swap, `{project}-idle` may be live
4. **Skipping idle smoke** — bad image becomes prod after swap
5. **Health=Red on Ready** — always check Health after poll
6. **ALB-alias Route53** — CNAME swap ineffective
7. **ELB health 400** — add instance private IP to ALLOWED_HOSTS (IMDSv2)
8. **Concurrent deploys** — use release-only trigger, not push + release simultaneously
