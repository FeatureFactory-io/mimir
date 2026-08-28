# Manage Iteration

**Playbook**: Edda v73.0 (Released)
**Workflow ID**: 17
**Description**: Feature-driven, team-lead-driven sprint execution. Advanced-model TL orchestrates the full build→integrate→test→fix→close cycle, one issue at a time. TL dispatches cheap-fast dr-dobbs workers (one per graph node), verifies each feature’s DoD gate (already run as a BPE-06 node), then hands to Saga (UAT Agent) for project-agnostic acceptance testing scoped to the iteration manifest. A test-first fix loop (BPE-09) resolves UAT blockers before a PR is opened for human review and the iteration is rel
**Phase Organization**: No phase organization
**Total Activities**: 7
**Export Date**: 2026-08-28 15:19 UTC

## Activities

See individual activity files in this directory.

## Editing Instructions

- **Add activity**: Create new file with pattern PREFIX-XX-Name.md
- **Remove activity**: Delete the .md file
- **Reorder**: Rename files to change order numbers
- **Edit content**: Modify description, guidance, dependencies
- **Change phase**: Update the Phase field

After editing, use import_workflow_from_local MCP tool to import changes.
