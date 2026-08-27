# Manage Iteration

**Playbook**: Edda v64.0 (Released)
**Workflow ID**: 17
**Description**: Feature-driven, team-lead-driven sprint execution. TL (advanced model) dispatches dr-dobbs workers (cheap-fast model) node-by-node per issue. After all nodes pass, TL integrates and gates each feature with BPE-06 + BPE-07 before handing to Saga (UAT Agent) for Playwright acceptance. Fix loop resolves UAT blockers before close.
**Phase Organization**: No phase organization
**Total Activities**: 7
**Export Date**: 2026-08-27

## Activity Flow

```
MIN-01  Activate Iteration          → verify PIN artifacts, milestone, issues, clean slate
MIN-02  Load Context & Sequence     → restore PIN context, sequence execution queue
MIN-03  Build                       → TL dispatches dr-dobbs workers per graph node (issue-by-issue)
MIN-04  Integrate & Gate            → TL: BPE-06 DoD + BPE-07 Finalize per feature; close issues
MIN-05  UAT Agent                   → Saga runs tests/uat/ Playwright journeys; files IF DIFFER as bugs
MIN-06  Fix & Reintegrate           → TL + dr-dobbs fix UAT blockers; regression UAT; loop until clean
MIN-07  Close Iteration             → TAF health gate + lessons learned + GitHub Release + milestone close
```

## Model Tiers

| Activity | Model |
|----------|-------|
| MIN-01, MIN-02 | TL inline (advanced model) |
| MIN-03 TL role | Advanced reasoning model (orchestrator — no code) |
| MIN-03 dr-dobbs workers | Cheap-fast model (e.g. composer-2.5-fast) |
| MIN-04, MIN-07 | TL inline (advanced model) |
| MIN-05, MIN-06 Saga | Medium model |
| MIN-06 dr-dobbs fix workers | Cheap-fast model |

## Activities

See individual activity files in this directory.

## Editing Instructions

- **Add activity**: Create new file with pattern PREFIX-XX-Name.md
- **Remove activity**: Delete the .md file
- **Reorder**: Rename files to change order numbers
- **Edit content**: Modify description, guidance, dependencies
- **Change phase**: Update the Phase field

After editing, use import_workflow_from_local MCP tool to import changes.
