# Implementation Plan: Playbook Export to Local IDE Workspace (#165)

**Feature**: FOB-MCP-PEXP — One-shot markdown export of full playbook to `.cursor` / `.windsurf`  
**GitHub Issue**: [#165](https://github.com/phainestai/mimir/issues/165)  
**Branch**: `feature/export-playbook-to-local`  
**Spec**: New scenarios in `docs/features/act-3-workflows/workflows-export-import.feature` (FOB-WORKFLOWS-EXPORT_IMPORT-22..25)  
**Related**: DSP-05 Generate AI IDE Configuration; distinct from JSON `export_playbook` (FOB-WORKFLOWS-EXPORT_IMPORT-20)

---

## Problem Statement

`export_workflow_to_local` exports one workflow at a time and only activity-linked rules. Full IDE sync (Edda → `.cursor/playbooks/Edda` + `.windsurf/workflows/Edda`) requires ~50+ MCP calls. Need `export_playbook_to_local` looping workflows, all rules, agents, skills, artifacts, and `playbook.md`.

---

## Section A — Context Map

| File | Lines | Note |
|------|-------|------|
| `methodology/services/workflow_export_service.py` | 1–110, 330–366 | Per-workflow export + partial rules — reuse, add `skip_rules` flag |
| `methodology/services/playbook_service.py` | — | `get_playbook` metadata for `playbook.md` |
| `methodology/api/viewsets.py` | 700–718 | `WorkflowViewSet.export` — pattern for playbook export action |
| `mcp_integration/tools.py` | 1126–1159 | `export_workflow_to_local` — sibling tool registration |
| `mcp_integration/facade/tools_http.py` | 335+ | HTTP facade writes files from JSON response |
| `docs/features/act-3-workflows/workflows-export-import.feature` | 219+ | JSON export scenarios — add local tree scenarios separately |
| `tests/unit/test_workflow_export_service.py` | — | Export unit patterns |
| `tests/integration/test_mcp_e2e_all_tools.py` | 688+ | `test_48_export_workflow_to_local` |

---

## Section B — Do-Not-Do List

- Do NOT conflate with JSON `export_playbook` / `import_playbook` (cross-instance migration) — separate tool and service.
- Do NOT put filesystem I/O in MCP tool layer — service writes files; MCP/DRF call service (match `WorkflowExportService` pattern).
- Do NOT duplicate workflow markdown generation — delegate to `WorkflowExportService.export_workflow_to_markdown(..., skip_rules=True)`.
- Do NOT export draft-only secrets or user emails in `playbook.md`.
- Do NOT require export when `MIMIR_DEV_ROOT` unset on Docker facade — same guard as existing export tools.
- Do NOT break existing `export_workflow_to_local` behavior (default `skip_rules=False`).

---

## Section C — SAO.md Sections That Apply

- **FastMCP as API Wrapper** — new POST `/api/playbooks/{id}/export-local/` → MCP tool.
- **Hybrid MCP Access** — read-only export allowed on released playbooks.
- **Shared Services Layer** — new `PlaybookExportService` orchestrates existing exporters.
- **Rule export** — playbook-scoped `rules/*.mdc` under playbook folder, not sibling orphan `rules/`.

---

## Section D — Tests to Create

| Test | Asserts |
|------|---------|
| `test_playbook_export_service_writes_playbook_md` | `playbook.md` with name, version, workflow index |
| `test_playbook_export_service_exports_all_rules` | Rules with `activity_count=0` included under `{root}/rules/` |
| `test_playbook_export_service_exports_agents_skills_artifacts` | `agents/`, `skills/`, `artifacts/` folders populated |
| `test_playbook_export_service_loops_all_workflows` | N workflows → N subfolders with `_workflow.md` |
| `test_playbook_export_service_multi_target` | Two targets both receive identical tree |
| `test_playbook_export_sync_root_rules_optional` | `sync_root_rules=True` copies always-apply rules to `.cursor/rules/` |
| `test_mcp_export_playbook_to_local_t1` | MCP tool returns counts summary dict |
| `test_mcp_export_playbook_to_local_t2` | Direct service call with real DB + tmp_path |
| `test_mcp_export_playbook_to_local_t3` | Subprocess JSON-RPC no stdout noise (if stdio transport tested) |
| `test_playbook_export_log_story_happy` | caplog: playbook_id=, workflows=, rules=, files_created= |
| `test_playbook_export_log_story_reject` | caplog: permission denied / playbook not found |

**Feature scenarios** (add to `workflows-export-import.feature`):

- FOB-WORKFLOWS-EXPORT_IMPORT-22: Single call exports full playbook tree  
- FOB-WORKFLOWS-EXPORT_IMPORT-23: All playbook rules exported (including unlinked)  
- FOB-WORKFLOWS-EXPORT_IMPORT-24: Optional dual targets `.cursor` + `.windsurf`  
- FOB-WORKFLOWS-EXPORT_IMPORT-25: Summary counts match list_* totals  

---

## Section E — Log Story Script

| Where | Beat | Trigger | Must include |
|-------|------|---------|--------------|
| `PlaybookExportService.export_playbook_to_local` | entry | export start | playbook_id=, targets= |
| `PlaybookExportService._export_playbook_metadata` | processing | playbook.md written | path=, version= |
| `PlaybookExportService._export_all_rules` | processing | rules loop | playbook_id=, rule_count= |
| `PlaybookExportService._export_entity_folder` | processing | agents/skills/artifacts | entity_type=, count= |
| `WorkflowExportService.export_workflow_to_markdown` | processing | per workflow | workflow_id=, folder= |
| `PlaybookExportService.export_playbook_to_local` | exit | complete | workflows=, activities=, rules=, files_created len= |
| `PlaybookExportService.export_playbook_to_local` | error | permission/playbook missing | playbook_id=, error |

---

## Section F — MCP Tools to Expose

| Tool name | Service method | Write? | HITL? | Auth injection |
|-----------|---------------|--------|-------|----------------|
| `export_playbook_to_local` | `PlaybookExportService.export_playbook_to_local` | No (filesystem) | No | server-side user; read playbook permission |
| `export_workflow_to_local` | unchanged | No | No | unchanged |

**Tool signature (proposed):**

```python
async def export_playbook_to_local(
    playbook_id: int,
    target_directory: str = ".cursor/playbooks",
    folder_name: str | None = None,
    additional_targets: list[str] | None = None,
    sync_root_rules: bool = False,
) -> dict
```

**Return shape:**

```python
{
  "status": "exported",
  "playbook_id": 3,
  "playbook_name": "Edda",
  "export_paths": ["..."],
  "workflows": 10,
  "activities": 87,
  "rules": 32,
  "skills": 19,
  "agents": 2,
  "artifacts": 28,
  "files_created": ["playbook.md", "ESM/_workflow.md", ...],
}
```

---

## Target Directory Layout

```
{target_directory}/{folder_name}/          # e.g. .cursor/playbooks/Edda/
  playbook.md                              # metadata + workflow index
  rules/                                   # ALL playbook rules (list_rules)
  agents/                                  # one .md per agent
  skills/                                  # one .md per skill
  artifacts/                               # one .md per artifact
  ESM/                                     # workflow export (existing format)
  DTA/
  ...
```

When `additional_targets` provided (e.g. `.windsurf/workflows/Edda`), repeat tree write to each root.

When `sync_root_rules=True`, copy rules with `always_apply=True` to:

- `{dev_root}/.cursor/rules/{slug}.mdc`
- `{dev_root}/.windsurf/rules/{slug}.md`

---

## Service Design

### New file: `methodology/services/playbook_export_service.py`

```python
class PlaybookExportService:
    @staticmethod
    def export_playbook_to_local(
        playbook_id: int,
        target_directory: str,
        folder_name: str | None = None,
        additional_targets: list[str] | None = None,
        sync_root_rules: bool = False,
        user=None,
    ) -> dict:
        ...
```

**Private helpers** (concise public method):

- `_resolve_playbook(playbook_id, user)`
- `_write_playbook_md(playbook, export_root, workflows)`
- `_export_rules(playbook, export_root/rules/)`
- `_export_agents`, `_export_skills`, `_export_artifacts` — one markdown file each
- `_export_workflows(playbook, export_root)` — loop `WorkflowExportService.export_workflow_to_markdown(..., skip_rules=True)`
- `_sync_root_rules(playbook, dev_root)` — optional
- `_mirror_to_additional_targets(primary_result, additional_targets)`

### WorkflowExportService change

Add parameter `skip_rules: bool = False` to `export_workflow_to_markdown`. When True, skip `_export_rules_for_workflow` (playbook export owns rules once).

Add `_generate_agent_md`, `_generate_skill_md`, `_generate_artifact_md` formatters (front matter + body from model fields).

---

## Implementation Steps (vertical slices)

### Slice 1 — Service skeleton + playbook.md (RED → GREEN)

1. `PlaybookExportService` stub + `playbook.md` generation.
2. Unit test with tmp_path.

### Slice 2 — Workflow loop

1. Integrate workflow export with `skip_rules=True`.
2. Integration test: 2 workflows → 2 folders.

### Slice 3 — Full entity folders

1. Rules (all), agents, skills, artifacts exporters.
2. Tests assert unlinked rules included (#165 repro).

### Slice 4 — DRF + MCP + facade

1. `PlaybookViewSet.export_local` POST action.
2. `export_playbook_to_local` in `tools.py` + `tools_http.py` + `server.py` registration.
3. T1/T2 MCP tests.

### Slice 5 — Multi-target + sync_root_rules

1. `additional_targets` mirror copy.
2. Optional root rules sync.
3. Feature scenarios 24–25.

### Slice 6 — Docs + UAT

1. Gherkin scenarios 22–25.
2. Update `docs/DOCKER_QUICK_START.md` tool table.
3. Manual: export Edda playbook id=3 to `.cursor/playbooks/Edda`.

---

## Commit Strategy

- `feat(export): add PlaybookExportService with playbook.md` (#165)
- `feat(export): export all rules agents skills artifacts in playbook tree` (#165)
- `feat(mcp): add export_playbook_to_local tool` (#165)
- `feat(export): optional multi-target and sync_root_rules` (#165)
- `test(export): playbook local export integration and log-story` (#165)
- `docs(workflows): add playbook local export scenarios` (#165)

---

## Success Criteria

- [ ] One MCP call replaces ~50 manual calls for Edda IDE sync
- [ ] Playbook-wide rules (activity_count=0) appear in export
- [ ] Existing `export_workflow_to_local` unchanged for single-workflow use
- [ ] Section D tests green + log-story coverage
- [ ] Plan approved by user
