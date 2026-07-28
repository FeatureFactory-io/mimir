# Activity: Build CI Pipeline

**Activity ID**: 84
**Order**: 4
**Phase**: Elaboration
**Dependencies**: Predecessor: Activity 83 (Add Container & Deploy Make Targets)

## Description

Build CI Pipeline

## Guidance

APPEND TO GUIDANCE:

---

## Release-Gated CI (Huginn Model)

For EB / release-gated projects, CI runs on **published GitHub Releases** (and `workflow_dispatch`), not every push:

```yaml
on:
  release:
    types: [published]
  workflow_dispatch:

# Push to main → no CI run (intentional — human controls ship via gh release create)
```

**Why:** Prevents concurrent deploy races (`UpdateEnvironment: Must be Ready`) and gives explicit semver control.

### Dual Registry Build

| Image | Registry | Deployed to EB? |
|-------|----------|-----------------|
| Web app | ECR (private) | Yes |
| MCP facade / CLI tool | Docker Hub (public) | No — client-side only |

### Auth Options

| Method | When |
|--------|------|
| OIDC `role-to-assume` | Preferred for org repos |
| IAM access keys in secrets | Acceptable for single-team projects |

Do not treat access keys as always wrong — document trade-off in `CICD_REQUIREMENTS.md`.

## Agent

None

## Skill

**Title**: GitHub Actions Patterns
**Capability Domain**: CI_CD
**Technology Stack**: GitHub Actions

## Rules

None

## Artifacts Produced

- **CI Pipeline (GitHub Actions)** (Code) - Required

## Artifacts Consumed

None

## Notes

No additional notes.
