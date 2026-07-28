# Activity: Publish

**Activity ID**: 150
**Order**: 4
**Phase**: Construction
**Dependencies**: Predecessor: Activity 142 (Contract)

## Description

Publish

## Guidance

## Purpose
Create the Milestone and Issues from the execution manifest, on GitHub or GitLab. Ask user before creating. The Milestone becomes MIN's operational ground truth — it must contain the full YAML manifest inline.

## Prerequisites
- Execution manifest YAML from PIN-03 (`ITER-*.yaml`)
- All skeleton commits on iteration branch
- GitHub CLI (`gh`) or GitLab CLI (`glab`) authenticated

## Step 0 — Platform Detection
```bash
REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
if echo "$REMOTE" | grep -q "github.com"; then
  PLATFORM=github
  gh auth status || { echo "Run: gh auth login"; exit 1; }
elif echo "$REMOTE" | grep -q "gitlab"; then
  PLATFORM=gitlab
  glab auth status || { echo "Run: glab auth login"; exit 1; }
else
  echo "Cannot detect platform from git remote. Set PLATFORM=github or PLATFORM=gitlab manually."
  exit 1
fi
echo "Platform: $PLATFORM"
```

## Step 1 — User Gate
Ask: "Platform detected: **{github|gitlab}**. Create milestone and issues from the manifest? (yes/no)"

- **No** → write manifest to `docs/plans/iterations/` only. Stop. Inform user: "Manifest saved. Invoke MIN manually when ready."
- **Yes** → continue.

## Step 2 — Bootstrap Labels

**GitHub:** See *GitHub Issue Operations* skill — Bootstrap Labels section.

**GitLab:** See *GitLab Issue Operations* skill — Bootstrap Labels section.

## Step 3 — Create Milestone

**GitHub:**
```bash
gh api repos/{owner}/{repo}/milestones   --method POST   --field title="ITER-YYYYMMDD | {iteration_goal}"   --field description="$(cat <<EOF
<!-- MANIFEST -->
$(cat ITER-*.yaml)
<!-- /MANIFEST -->

## Iteration Goal
{iteration_goal}

## Scenarios
{list}
EOF)"
# Record returned milestone number
```

**GitLab:**
```bash
PROJECT=$(glab api projects/:fullpath --jq '.id')
glab api "projects/$PROJECT/milestones"   --method POST   --field title="ITER-YYYYMMDD | {iteration_goal}"   --field description="<!-- MANIFEST -->$(cat ITER-*.yaml)<!-- /MANIFEST -->"
# Record returned milestone id
```

## Step 4 — Create Issues (one per scenario)

For each scenario in manifest order:

**GitHub:** See *GitHub Issue Operations* skill — Pattern 2.
**GitLab:** See *GitLab Issue Operations* skill — Pattern 2.

Issue body must include inline:
- `<!-- SCENARIO -->` YAML block
- Context Map table
- Do Not Do list
- SAO.md Sections
- Implementation Plan (full text from BPE-01)
- Acceptance Criteria checklist

Labels: `status-queued, parallel-group-{X}`
Dependency issues reference each other in body.

## Step 5 — Update Manifest with Issue Numbers
Add `github_issue` or `gitlab_issue` field per scenario. Commit:
```bash
git add docs/plans/iterations/
git commit -m "chore(pin): add issue numbers to manifest ITER-YYYYMMDD"
```

## Step 6 — Verify

**GitHub:**
```bash
gh milestone view {N}
gh issue list --milestone {N}
```

**GitLab:**
```bash
glab api "projects/:fullpath/milestones" --jq '.[] | select(.title | contains("ITER"))'
glab issue list --milestone "{milestone_title}" --label "status-queued"
```

## Success Criteria
- Milestone created with full `<!-- MANIFEST -->` YAML block
- One Issue per scenario with inline `<!-- SCENARIO -->` YAML + context map + do-not-do + implementation plan
- All issues labelled `status-queued` + `parallel-group-{X}`
- Local manifest updated with issue numbers and committed

## Skills
- *GitHub Issue Operations* (gh CLI) — see skill for all patterns
- *GitLab Issue Operations* (glab CLI) — see skill for all patterns

## Agent

None

## Skill

**Title**: GitHub Issue Operations
**Capability Domain**: GITHUB_ISSUE
**Technology Stack**: GitHub CLI

## Rules

None

## Artifacts Produced

None

## Artifacts Consumed

None

## Notes

No additional notes.
