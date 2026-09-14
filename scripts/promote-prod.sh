#!/usr/bin/env bash
# promote-prod.sh — swap idle ↔ prod EB CNAMEs, then smoke-test the prod URL.
# Run only after reviewing the idle deployment (deploy-idle.sh output).
#
# Revision guard:
#   • If EXPECTED_REVISION is set: must match idle /health/ revision (release tag,
#     e.g. v0.0.47) OR idle EB VersionLabel exactly (e.g. v-v0.0.47-abc-r238).
#   • If unset: promotes whatever is currently on idle (safe for local "make swap").
#
# Required env vars:
#   EB_APP      e.g. mimir
#   EB_ENV_A    e.g. mimir-prod
#   EB_ENV_B    e.g. mimir-idle
#
# Optional:
#   EXPECTED_REVISION   release tag (v0.0.41) or EB VersionLabel — must match idle staging
#   MIMIR_PROD_URL      default https://mimir.featurefactory.io

set -euo pipefail

: "${EB_APP:?EB_APP not set}"
: "${EB_ENV_A:?EB_ENV_A not set}"
: "${EB_ENV_B:?EB_ENV_B not set}"

# ── 1. Resolve live / idle ────────────────────────────────────────────────────
CNAME_A=$(aws elasticbeanstalk describe-environments \
  --application-name "$EB_APP" \
  --environment-names "$EB_ENV_A" \
  --query 'Environments[0].CNAME' --output text)

if echo "$CNAME_A" | grep -q "mimir-prod"; then
  LIVE_ENV="$EB_ENV_A"
  IDLE_ENV="$EB_ENV_B"
else
  LIVE_ENV="$EB_ENV_B"
  IDLE_ENV="$EB_ENV_A"
fi

echo "Live env:  $LIVE_ENV  (traffic is here — will become idle after swap)"
echo "Idle env:  $IDLE_ENV  (staged revision — will become prod after swap)"

# ── 2. Read idle's current version label ─────────────────────────────────────
IDLE_LABEL=$(aws elasticbeanstalk describe-environments \
  --application-name "$EB_APP" \
  --environment-names "$IDLE_ENV" \
  --query 'Environments[0].VersionLabel' --output text)

if [ -z "$IDLE_LABEL" ] || [ "$IDLE_LABEL" = "None" ] || [ "$IDLE_LABEL" = "null" ]; then
  echo "ERROR: could not read VersionLabel on idle env $IDLE_ENV — is a deployment staged?"
  exit 1
fi
echo "Idle VersionLabel: $IDLE_LABEL"

# ── 3. Read idle /health/ revision (MIMIR_GIT_REVISION — same as prod smoke) ─
IDLE_CNAME=$(aws elasticbeanstalk describe-environments \
  --application-name "$EB_APP" \
  --environment-names "$IDLE_ENV" \
  --query 'Environments[0].CNAME' --output text)
echo "Reading idle health: http://${IDLE_CNAME}/health/ ..."
IDLE_HEALTH=$(curl -s --max-time 15 "http://${IDLE_CNAME}/health/")
IDLE_REVISION=$(python3 -c "import json,sys; print(json.loads(sys.argv[1]).get('revision','unknown'))" "$IDLE_HEALTH")
echo "Idle /health/ revision: $IDLE_REVISION"

# ── 4. Optional revision guard ────────────────────────────────────────────────
if [ -n "${EXPECTED_REVISION:-}" ]; then
  if [ "$EXPECTED_REVISION" = "$IDLE_REVISION" ] || [ "$EXPECTED_REVISION" = "$IDLE_LABEL" ]; then
    echo "Revision guard passed: $EXPECTED_REVISION matches idle."
  else
    echo "ERROR: EXPECTED_REVISION=$EXPECTED_REVISION does not match idle revision ($IDLE_REVISION) or VersionLabel ($IDLE_LABEL)."
    echo "Deploy that revision to idle first, or unset EXPECTED_REVISION to promote whatever is staged."
    exit 1
  fi
fi

SMOKE_REVISION="$IDLE_REVISION"
echo "Prod smoke will verify revision: $SMOKE_REVISION"

# ── 5. Swap CNAMEs ────────────────────────────────────────────────────────────
echo "Swapping $IDLE_ENV (idle) ↔ $LIVE_ENV (live) ..."
aws elasticbeanstalk swap-environment-cnames \
  --source-environment-name "$IDLE_ENV" \
  --destination-environment-name "$LIVE_ENV"
echo "Swap requested — waiting 90s for DNS TTL propagation (Route53 TTL=60s)..."
sleep 90

# ── 6. Smoke-test prod URL — poll until revision matches (up to 3 min) ────────
PROD_URL="${MIMIR_PROD_URL:-https://mimir.featurefactory.io}"
echo "Polling ${PROD_URL}/health/ for revision=$SMOKE_REVISION ..."
for i in $(seq 1 18); do
  PROD_STATUS=$(curl -o /tmp/prod-health.json -s -w "%{http_code}" \
    --max-time 15 "${PROD_URL}/health/" || echo "000")
  PROD_REVISION=$(python3 -c 'import json; print(json.load(open("/tmp/prod-health.json")).get("revision","unknown"))' 2>/dev/null || echo "unknown")
  echo "  [${i}/18] HTTP=${PROD_STATUS}  revision=${PROD_REVISION}"
  if [ "$PROD_STATUS" = "200" ] && [ "$PROD_REVISION" = "$SMOKE_REVISION" ]; then
    break
  fi
  sleep 10
done

if [ "$PROD_STATUS" != "200" ]; then
  echo "Prod smoke test FAILED — HTTP $PROD_STATUS"
  cat /tmp/prod-health.json || true
  exit 1
fi

PROD_REVISION=$(python3 -c 'import json; print(json.load(open("/tmp/prod-health.json")).get("revision","unknown"))')
echo "Prod /health/ revision: $PROD_REVISION  (expected: $SMOKE_REVISION)"

if [ "$PROD_REVISION" != "$SMOKE_REVISION" ]; then
  echo "Prod smoke test FAILED — revision mismatch. CNAME may still be propagating."
  exit 1
fi

echo ""
echo "PROMOTE SUCCESS: ${PROD_URL}/health/ → 200, revision=${PROD_REVISION}."

echo "Stopping the env that is now idle (former prod) to save compute..."
PROD_CNAME_SUBSTRING="mimir-prod" \
  bash "$(dirname "$0")/eb_idle_power.sh" stop
