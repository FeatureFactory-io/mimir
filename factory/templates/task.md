---
id: T-NNN
role: feature-builder   # step-def-writer | feature-builder | release-engineer | manual-tester
attempt: 1
depends_on: []          # ids must be in done/ with terminal status before claim
github_issue: 0         # GitHub issue number this task closes (0 if none)
branch: factory/T-NNN-short-slug
expected_capabilities:  # advisory — workers run with full tool access (--yolo)
  - git
  - gh
  - .venv/bin/pytest
files_in_scope:
  - path/to/file.py
---

## Goal

One paragraph describing what success looks like from the user's perspective.

## Blueprint

See [`factory/blueprints/T-NNN.md`](../blueprints/T-NNN.md) for design details, files
touched, interfaces changed, and risks.

## Acceptance criteria

Copy the relevant Gherkin scenario(s) verbatim from `docs/features/**/*.feature`:

```gherkin
Scenario: <title>
  Given ...
  When ...
  Then ...
```

## Checkpoint command

```bash
.venv/bin/pytest tests/integration/test_activity_list.py::TestActivityList::test_act_list_06_search_by_name -x
```

Run this from the worktree root (`.worktrees/<role>/`) before marking the task done.

## Files in scope

Repeat the `files_in_scope` list here as prose if additional context helps the worker:

- `path/to/file.py` — <what changes and why>

## Do not touch

- List any files/areas explicitly out of scope to prevent drift.

---

# Result

status:
branch:
mr:
commit_sha:

<!-- Result kinds:
     code task   — status: passed|failed; branch + mr + commit_sha required
     manual task — status: passed|failed; branch: none; mr: 0; commit_sha: none; ## Evidence required
     monitoring  — status: monitoring; mr: 0 (release-engineer pipeline watch)

     Scope enforcement is post-run via git diff vs files_in_scope — not tool allowlists.
     Leaving required fields blank routes this task to factory/tasks/blocked/. -->
