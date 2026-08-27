# Implementation Plan: ADE-Aware Rule Export (Plan B)

**Feature:** EXPORT-ADE-RULES  
**GitHub Issue:** [#176](https://github.com/FeatureFactory-io/mimir/issues/176) (enhancement)  
**Reconciliation:** [EXPORT-ADE-RULES_CHANGE_RECONCILIATION.md](./EXPORT-ADE-RULES_CHANGE_RECONCILIATION.md)  
**Spec:** `docs/features/act-3-workflows/workflows-export-import.feature` (FOB-WORKFLOWS-EXPORT_IMPORT-30..34)  
**Related:** [#165](https://github.com/FeatureFactory-io/mimir/issues/165) playbook export; [#175](https://github.com/FeatureFactory-io/mimir/issues/175) deferred

---

## Problem Statement

Playbook rules export to the playbook tree with stored `alwaysApply`, but ADEs (Cursor, Devin) only inject rules from `.cursor/rules/` and `.windsurf/rules/`. Most Edda rules are `always_apply=false`, so even optional `sync_root_rules` skips them. DSP-05 never calls export with force-apply. Agents skip mandatory process rules.

---

## Section A — Context Map

| File | Lines | Note |
|------|-------|------|
| `methodology/services/playbook_export_service.py` | 24–90, 101–180, 233–243 | `export_playbook_to_local`, bundle generation, `_sync_root_rules` |
| `methodology/services/workflow_export_service.py` | 397–402 | `_format_rule_mdc` — extract ADE formatters from here |
| `mcp_integration/tools.py` | 1164–1209 | MCP stdio `export_playbook_to_local` — add params |
| `mcp_integration/facade/tools_http.py` | 409–500 | HTTP facade write + client-side sync — unify with service |
| `methodology/api/viewsets.py` | 339–381 | `POST export-local` — pass ADE params in request body |
| `tests/unit/test_playbook_export_service.py` | — | Unit patterns for export |
| `tests/integration/test_playbook_export_local_api.py` | — | API export-local tests |
| `docs/plans/EXPORT-ADE-RULES_CHANGE_RECONCILIATION.md` | — | Approved target state + Edda PIP outline |

---

## Section B — Do-Not-Do List

- Do NOT add `apply_mode` to Rule model ([#175](https://github.com/FeatureFactory-io/mimir/issues/175)).
- Do NOT mass-update Edda `Rule.always_apply` rows.
- Do NOT change JSON `export_playbook` / `import_playbook`.
- Do NOT overwrite entire `CLAUDE.md` / copilot-instructions — inline section only (DSP-05 PIP).
- Do NOT copy apply-on rules to **both** `.cursor` and `.windsurf` when `ade_target` is set — single ADE only.
- Do NOT break default export when `ade_target` is omitted (backward compatible).
- Do NOT submit/apply Edda PIP without human review (draft only in N4).
- Do NOT put filesystem logic only in HTTP facade — service owns formatting and placement for stdio + HTTP.

---

## Section C — SAO.md Sections That Apply

- **Shared Services Layer** — ADE formatting in export service, not MCP-only.
- **Hybrid MCP Access** — read-only export on released playbooks unchanged.
- **FastMCP as API Wrapper** — extend existing `export_playbook_to_local` tool signature.
- **Domain Model — Rule** — canonical tree vs ADE-root copies (reconciled in SAO).

---

## Section D — Tests to Create

| Test | Asserts |
|------|---------|
| `test_format_rule_for_ade_cursor_force_apply` | `always_apply=false` → `alwaysApply: true` when `force_apply=True` |
| `test_format_rule_for_ade_devin_extension` | Devin target → `.md` body without Cursor-only frontmatter where appropriate |
| `test_build_inline_rules_markdown` | Claude/Copilot bundle field lists all rule bodies when `force_apply=True` |
| `test_sync_ade_rules_cursor_only` | `ade_target=cursor` writes `.cursor/rules/` not `.windsurf/rules/` |
| `test_sync_ade_rules_devin_only` | `ade_target=devin` writes `.windsurf/rules/` only |
| `test_canonical_tree_preserves_stored_always_apply` | `{export_root}/rules/*.mdc` unchanged stored flag |
| `test_export_requires_ade_target_when_force_apply` | ValueError when `force_apply` without `ade_target` |
| `test_export_requires_ade_target_when_sync_root_rules` | ValueError when `sync_root_rules` without `ade_target` |
| `test_mcp_export_playbook_to_local_ade_t1` | MCP tool accepts new params; returns `inline_rules_markdown` for claude |
| `test_mcp_export_playbook_to_local_ade_t2` | Direct service + tmp_path: force_apply file on disk |
| `test_export_local_api_ade_params` | POST body `ade_target`, `force_apply` reflected in bundle |
| `test_playbook_export_ade_log_story_happy` | caplog: `ade_target=`, `force_apply=`, `ade_files=` |
| `test_playbook_export_ade_log_story_reject` | caplog: validation error when `ade_target` missing |

**Gherkin alignment:** scenarios EXPORT_IMPORT-30..34 (already in feature file).

---

## Section E — Log Story Script

| Where | Beat | Trigger | Must include |
|-------|------|---------|--------------|
| `PlaybookExportService.export_playbook_to_local` | entry | export start | `ade_target=`, `force_apply=`, `sync_root_rules=` |
| `PlaybookExportService._format_ade_rule_files` | processing | per rule | `slug=`, `ade_target=` |
| `PlaybookExportService._sync_ade_root_rules` | processing | ADE copy write | `path=`, `slug=`, `force_apply=` |
| `PlaybookExportService._build_inline_rules_markdown` | processing | claude/copilot | `rule_count=` |
| `PlaybookExportService.export_playbook_to_local` | exit | complete | `ade_files=`, `inline=` (bool) |
| `PlaybookExportService.export_playbook_to_local` | error | missing ade_target | `ade_target required` |

---

## Section F — MCP Tools to Expose

| Tool name | Service method | Write? | HITL? | Auth injection |
|-----------|---------------|--------|-------|----------------|
| `export_playbook_to_local` | `PlaybookExportService.export_playbook_to_local` | No (filesystem) | No | server-side user |

**Extended signature (proposed):**

```python
async def export_playbook_to_local(
    playbook_id: int,
    target_directory: str = ".cursor/playbooks",
    folder_name: str | None = None,
    additional_targets: list[str] | None = None,
    sync_root_rules: bool = False,
    ade_target: Literal["cursor", "devin", "claude", "copilot"] | None = None,
    force_apply: bool = False,
) -> dict
```

**Return shape additions:**

```python
{
  ...
  "ade_rule_files": [{"filename": "...", "content": "...", "path": ".cursor/rules/..."}],
  "inline_rules_markdown": "## Playbook Rules\n\n..."  # claude/copilot; empty str otherwise
}
```

No new MCP tool. T1 + T2 required; T3 if stdio subprocess tested elsewhere.

---

## Section G — Implementation Steps

### Slice 1 — ADE formatter + bundle (BPE-02)

1. Add `methodology/services/rule_export_formatters.py` (or helpers on `WorkflowExportService`):
   - `format_rule_for_ade(rule, ade_target, *, force_apply=False) -> str`
   - `build_inline_rules_markdown(rules, *, force_apply=False) -> str`
2. Extend `generate_playbook_export_bundle` to accept `ade_target`, `force_apply`; populate `ade_rule_files`, `inline_rules_markdown`.
3. Replace `_sync_root_rules` with `_sync_ade_root_rules(bundle, target_directory, ade_target, force_apply)` — single ADE path.
4. Unit tests + log-story tests (red → green).

### Slice 2 — MCP + API passthrough (BPE-02)

1. `export_playbook_to_local` in `tools.py` — new params.
2. `export_local` viewset — read `ade_target`, `force_apply`, `sync_root_rules` from POST body; pass to service when writing bundle (or return ADE fields in JSON for facade).
3. `tools_http.py` — use service-returned `ade_rule_files` / write ADE paths; remove dual-IDE client loop.
4. Integration tests T1/T2 + API test.

### Slice 3 — Acceptance alignment (BPE-04)

1. Verify Gherkin scenarios 30–34 mappable to integration tests (may remain partially documented until green).
2. Run full export test module.

### Slice 4 — Edda PIP draft (BPE-02, human gate)

1. `create_pip` on playbook 3 with ALTERs from reconciliation doc (DSP-04, DSP-05, artifact 20).
2. **Do not submit/apply** until human review.

### Slice 5 — DoD (BPE-06)

1. All gates green; update #176 with implementation status; close when shipped.

---

## Section H — Mockup Graduation Plan

Not applicable — no frontend screens.

---

## Feature Execution Graph

See [EXPORT-ADE-RULES-feature-execution-graph.yaml](./EXPORT-ADE-RULES-feature-execution-graph.yaml).

---

## Lessons Learned

- #176 was filed as a bug but is a **process + export contract** gap; BPE-08 reclassification avoided Autofix noise.
- Edda source of truth is released playbook v71 — FOB repo copies under `.cursor/playbooks/Edda/` are export artifacts, not authoritative for PIP ALTERs.
- Prior #165 `sync_root_rules` dual-wrote both IDEs; Plan B requires explicit `ade_target` to prevent wrong-IDE pollution.
- Deferring #175 keeps this CR shippable: `force_apply` on ADE copy is sufficient for the Yggdrasil failure mode.
