# Activity: Acceptance, Bug Reports & Deploy Fixes

**Activity ID**: 183
**Order**: 6
**Phase**: None
**Dependencies**: None

## Description

Acceptance, Bug Reports & Deploy Fixes

## Guidance

## Purpose
User acceptance loop: demo the delivered iteration to the user guided by feature files, collect bugs, file them, fix them, and deploy a patch release.

## Steps

### Step 1: Confirm MIN-05 Artifacts Are in Place
- DoD check passed
- PR opened (not necessarily merged)
- GitHub Release tagged

If any artifact is missing: return to MIN-05 before proceeding.

### Step 2: Open App Locally
```bash
make run
# or if no Makefile target:
python manage.py runserver 8000
```
Confirm the server starts without errors. Monitor `logs/app.log` in a separate terminal:
```bash
tail -f logs/app.log
```

### Step 3: Build Demo Path from Manifest Feature Files
Load `feature_file_paths[]` from the ITER-*.yaml manifest for each scenario shipped in this iteration. Read those `.feature` files and extract the `Scenario:` titles.

Do NOT search `docs/features/act-*/` blindly — use only the paths declared in the manifest.

Build the guided walkthrough:
```
=== ACCEPTANCE DEMO PATH ===
Milestone: #{N} | {goal}

Suggested walkthrough (from feature files in manifest):
1. {Scenario title} — {brief what to click/do}
   Feature file: {feature_file_path}
2. {Scenario title} — {brief what to click/do}
...

Open: http://localhost:8000
Browser console: open DevTools → Console tab
Logs: tail -f logs/app.log
============================
```

Present this to the user. Wait for them to browse and report issues.

### Step 4: Collect Bug Reports
While the user browses, monitor in parallel:
- `logs/app.log` for ERROR/WARNING entries
- Browser console (ask user to share any red errors)
- User verbal feedback

For each defect reported or observed:
- Capture: title, steps to reproduce, expected vs actual, severity (blocker/major/minor)
- Include relevant log excerpts

### Step 5: File Bug Reports
For each defect, file via `report_bug` MCP tool:
```
report_bug(
  description="{title}\n\nSteps: {steps}\nExpected: {expected}\nActual: {actual}\nSeverity: {severity}\n\nLog excerpt:\n{log lines}",
  page_context="MIN-06 acceptance session — milestone #{N} — {timestamp}"
)
```
Link each filed issue to the current milestone:
```bash
gh issue edit {bug_issue_number} --milestone {N}
```

### Step 6: Triage and Fix
For each bug:

**Blocker** (prevents core feature from working):
- Fix immediately in the iteration branch
- Re-run relevant BPE-04/BPE-05 checkpoints for the affected scenario
- Commit:
```bash
git add -A
git commit -m "fix({scope}): {bug title}"
```

**Major / Minor** (degraded experience, not blocking):
- File the issue (Step 5) — defer to next iteration
- Do not hold the release

### Step 7: Deploy Patch Release
After all blockers are fixed:
```bash
gh release create "{ITER-slug}-patch.{N}" \
  --title "Patch: {iteration_goal}" \
  --notes "$(cat <<'EOF'
## Bug Fixes from Acceptance Testing

{list of fixed bugs with issue links}

## Still Open (deferred)
{list of non-blocker issues, or "none"}
EOF
)"
```
Post patch summary on the milestone:
```bash
gh issue comment {first_issue} --body "<!-- PATCH_RELEASE -->\nPatch: {tag}\nFixed: {N} blockers\nDeferred: {N} non-blockers\n<!-- /PATCH_RELEASE -->"
```

## Success Criteria
- App running locally; demo path derived from `feature_file_paths[]` in manifest (not from blind directory search)
- All user-reported and log-observed defects captured
- Each defect filed via `report_bug` MCP and linked to milestone
- All blockers fixed, checkpoints re-run and passing
- Patch release created (if any blockers were fixed)
- Non-blocker issues deferred to next iteration backlog

## Agent

None

## Skill

None

## Rules

None

## Artifacts Produced

None

## Artifacts Consumed

None

## Notes

No additional notes.
