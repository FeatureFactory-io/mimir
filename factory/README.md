# Dark factory (`factory/`)

Mechanical scaffold for the **dark-factory** sprint factory on Mimir: milestone-driven LE + specialist workers via filesystem queue (`tasks/pending` → `claimed` → `done`), tmux + `fswatch`, and Cursor CLI.

## Canonical docs

| Topic | Location |
|--------|-----------|
| Process contract (phases 0–6) | [`.cursor/skills/dark-factory/SKILL.md`](../.cursor/skills/dark-factory/SKILL.md) |
| Worker prompts | [`prompts/`](../prompts/) (used by `scripts/factory.sh`) |
| LE watch loop | [`references/worker-protocol.md`](../references/worker-protocol.md) |
| CI/CD, staging vs prod | [`docs/architecture/SAO.md`](../docs/architecture/SAO.md) |
| Iteration protocol (PIT/MIN) | [`.cursor/rules/iteration-protocol.mdc`](../.cursor/rules/iteration-protocol.mdc) |

Mimir uses **GitHub** (`gh`) for milestones/issues/PRs — not GitLab (`glab`).

## Prerequisites

Installed by **`make provision`** (single command with Python app + factory CLIs).

Re-check anytime:

```bash
make factory-check   # strict — includes gh auth + cursor-agent + model list
make test-factory    # contract tests + shell syntax checks
```

**Manual steps after first `make provision`** (cannot be automated):

- `gh auth login` — if GitHub CLI is new
- `cursor-agent` on PATH — install/update via [Cursor CLI](https://cursor.com/docs/cli)

On macOS, if `flock` is missing from PATH after provision, add:

```bash
export PATH="$(brew --prefix util-linux)/bin:$PATH"
```

Mockups for ingestion: `templates/mockups/` and `docs/ux/`.

## Commands (from repo root)

```bash
# Phase 0 — validate milestone, issues, tooling, feature refs
./scripts/preflight.sh 'Your Milestone Title'

# Phase 3 — tmux factory (after LE has filled pending tasks)
./scripts/factory.sh 'Your-Milestone-Slug' [mgmt-branch]
# Attach: tmux a -t mimir-Your-Milestone-Slug

# Merge code task PRs (LE)
./scripts/integrate.sh merge T-001

# Validate manual-tester tasks (no PR)
./scripts/integrate.sh validate T-M01

# Cut release after all tasks terminal (triggers CI → idle EB)
./scripts/release.sh 1.2.3 [--dry-run] [--target-sha <sha>]

# Post-sprint archive
./scripts/archive.sh 'your-sprint-slug'
```

### Preflight flags

| Flag | Purpose |
|------|---------|
| `--allow-dirty` | Waive clean working tree (local-only) |
| `--allow-missing-featurefile-ref` | Waive missing `docs/features/*.feature` in issues (infra sprints only — document why) |
| `--skip-staging-check` | Skip staging URL reachability probe |

Set `STAGING_URL` or rely on `make eb-status` idle CNAME when checking staging.

**Production promote** (manual, after staging review): `make swap` (see Makefile).

## Task queue lanes

| Directory | Meaning |
|-----------|---------|
| `tasks/pending/` | Waiting to be claimed |
| `tasks/claimed/` | In progress |
| `tasks/done/` | Awaiting LE review + integrate |
| `tasks/blocked/` | Max attempts or verify-result failure |
| `tasks/rejected/<id>/` | Archived rejection snapshots |

## Result kinds and terminal statuses

| Role / kind | `# Result` contract | Terminal status for release |
|-------------|---------------------|----------------------------|
| **code** (feature-builder, step-def-writer) | `branch`, `mr`, `commit_sha` required | `integrated` |
| **manual-tester** | `branch: none`, `mr: 0`, `commit_sha: none`, `## Evidence` required | `validated` (via `integrate.sh validate`) |
| **monitoring** (release-engineer pipeline watch) | `status: monitoring`, `mr: 0` | `integrated` or `monitoring` |

**Dependencies:** `claim.sh` and `integrate.sh` require dependencies in `done/` with terminal status (`integrated`, `validated`, or `monitoring`; manual `passed` counts for manual-tester deps only).

## Management branch

Factory state (`factory/tasks/`, `factory/blackboard.md`) lives on the sprint **management branch** (default: current branch, e.g. `features/<milestone>`). Workers use git worktrees under `.worktrees/<role>/` and branch from `origin/main` after dependencies are integrated.

Serialized git updates use `scripts/factory-git.sh` under `factory/.git.lock`.

## Maintainer verification

```bash
make test-factory
make factory-check
bash -n scripts/factory.sh scripts/preflight.sh scripts/claim.sh scripts/done.sh \
         scripts/reject.sh scripts/status.sh scripts/bb-append.sh \
         scripts/verify-result.sh scripts/integrate.sh scripts/release.sh \
         scripts/archive.sh scripts/rescue-result.sh scripts/factory-git.sh
```
