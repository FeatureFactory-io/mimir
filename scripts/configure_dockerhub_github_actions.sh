#!/usr/bin/env bash
#
# Create Docker Hub repo featurefactory/mimir-mcp (if missing) and set GitHub Actions secrets.
#
# Prerequisites:
#   - jq, curl
#   - gh auth login (scopes include repo/workflow enough for Actions secrets)
#   - Docker Hub: either `docker login` (credential helper holds PAT/password) OR
#     export DOCKERHUB_USERNAME + DOCKERHUB_TOKEN
#
# Usage:
#   ./scripts/configure_dockerhub_github_actions.sh
#
# Optional:
#   export GITHUB_REPOSITORY="FeatureFactory-io/mimir"
#   export DOCKER_CREDENTIAL_HELPER_URL="https://index.docker.io/v1/"
#
set -euo pipefail

HUB_API_URL="${DOCKER_CREDENTIAL_HELPER_URL:-https://index.docker.io/v1/}"

load_docker_hub_creds_if_missing() {
  if [[ -n "${DOCKERHUB_USERNAME:-}" && -n "${DOCKERHUB_TOKEN:-}" ]]; then
    return 0
  fi
  local helper CRED_JSON USER_NAME SECRET
  for helper in docker-credential-desktop docker-credential-osxkeychain docker-credential-pass; do
    command -v "$helper" >/dev/null 2>&1 || continue
    CRED_JSON="$(printf '%s\n' "${HUB_API_URL}" | "$helper" get 2>/dev/null)" || CRED_JSON=""
    [[ -z "${CRED_JSON}" ]] && continue
    USER_NAME="$(echo "${CRED_JSON}" | jq -r .Username)"
    SECRET="$(echo "${CRED_JSON}" | jq -r .Secret)"
    if [[ -n "${USER_NAME}" && "${USER_NAME}" != "null" && -n "${SECRET}" && "${SECRET}" != "null" ]]; then
      export DOCKERHUB_USERNAME="${USER_NAME}"
      export DOCKERHUB_TOKEN="${SECRET}"
      echo "Using Docker credential helper (${helper}); Hub user: ${DOCKERHUB_USERNAME}"
      return 0
    fi
  done
  echo "Missing DOCKERHUB_USERNAME / DOCKERHUB_TOKEN and no usable docker credential helper for ${HUB_API_URL}." >&2
  echo "Run docker login docker.io (or Hub), or export both variables explicitly." >&2
  exit 1
}

load_docker_hub_creds_if_missing

if [[ -n "${GITHUB_REPOSITORY:-}" ]]; then
  REPO_SPEC="${GITHUB_REPOSITORY}"
else
  ROOT="$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel 2>/dev/null || true)"
  if [[ -n "$ROOT" ]]; then
    REMOTE="$(git -C "$ROOT" remote get-url origin 2>/dev/null || true)"
    REMOTE="${REMOTE%.git}"
    if [[ "${REMOTE}" =~ ^git@[^:]+:(.+)$ ]]; then
      REPO_SPEC="${BASH_REMATCH[1]}"
    elif [[ "${REMOTE}" =~ ^https?://[^/]+/(.+)$ ]]; then
      REPO_SPEC="${BASH_REMATCH[1]}"
    else
      REPO_SPEC="FeatureFactory-io/mimir"
    fi
  else
    REPO_SPEC="${REPO_OVERRIDE:-FeatureFactory-io/mimir}"
  fi
fi

LOGIN_JSON="$(curl -fsS -H "Content-Type: application/json" \
  -X POST \
  -d "{\"username\": \"${DOCKERHUB_USERNAME}\", \"password\": \"${DOCKERHUB_TOKEN}\"}" \
  https://hub.docker.com/v2/users/login/)"

JWT="$(echo "${LOGIN_JSON}" | jq -r .token)"
if [[ -z "${JWT}" || "${JWT}" == "null" ]]; then
  echo "Docker Hub API login failed; response:"
  echo "${LOGIN_JSON}" | jq .
  exit 1
fi

BODY_FILE="$(mktemp)"
trap 'rm -f "${BODY_FILE}"' EXIT

HTTP_CODE="$(curl -sS -o "${BODY_FILE}" -w "%{http_code}" \
  -X POST "https://hub.docker.com/v2/repositories/" \
  -H "Authorization: JWT ${JWT}" \
  -H "Content-Type: application/json" \
  -d '{
        "namespace": "featurefactory",
        "name": "mimir-mcp",
        "description": "Mimir MCP facade — stdio/SSE bridge to FOB REST API",
        "full_description": "",
        "is_private": false
      }')"

if [[ "${HTTP_CODE}" == "201" ]]; then
  echo "Docker Hub: created featurefactory/mimir-mcp"
elif [[ "${HTTP_CODE}" == "409" ]] || grep -qi 'already exists\|taken\|in use\|duplicate' "${BODY_FILE}" 2>/dev/null; then
  echo "Docker Hub: featurefactory/mimir-mcp already exists (ok)"
else
  EXISTS_CODE="$(curl -sS -o /dev/null -w "%{http_code}" "https://hub.docker.com/v2/repositories/featurefactory/mimir-mcp/")"
  if [[ "${EXISTS_CODE}" == "200" ]]; then
    echo "Docker Hub: featurefactory/mimir-mcp exists (HTTP ${HTTP_CODE} on duplicate create)"
  else
    cat "${BODY_FILE}" >&2
    echo "Docker Hub repo create failed (HTTP ${HTTP_CODE}); GET repo returned ${EXISTS_CODE}" >&2
    exit 1
  fi
fi

printf '%s\n' "${DOCKERHUB_USERNAME}" | gh secret set DOCKERHUB_USERNAME -R "${REPO_SPEC}"
printf '%s\n' "${DOCKERHUB_TOKEN}"     | gh secret set DOCKERHUB_TOKEN -R "${REPO_SPEC}"
echo "GitHub Actions secrets DOCKERHUB_USERNAME / DOCKERHUB_TOKEN set on ${REPO_SPEC}"
