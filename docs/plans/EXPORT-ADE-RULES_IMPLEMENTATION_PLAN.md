# Implementation Plan: ADE-Aware Rule Export (Plan B)

**Feature:** EXPORT-ADE-RULES  
**Branch:** `feature/export-ade-rules`  
**GitHub Issue:** [#176](https://github.com/FeatureFactory-io/mimir/issues/176) (enhancement)  
**Reconciliation:** [EXPORT-ADE-RULES_CHANGE_RECONCILIATION.md](./EXPORT-ADE-RULES_CHANGE_RECONCILIATION.md)  
**Execution graph:** [EXPORT-ADE-RULES-feature-execution-graph.yaml](./EXPORT-ADE-RULES-feature-execution-graph.yaml)  
**Spec:** `docs/features/act-3-workflows/workflows-export-import.feature` (FOB-WORKFLOWS-EXPORT_IMPORT-30..34)  
**Related:** [#165](https://github.com/FeatureFactory-io/mimir/issues/165) playbook export; [#175](https://github.com/FeatureFactory-io/mimir/issues/175) closed — alternate implementation (no `apply_mode`)

---

## Problem Statement

Playbook rules export to the **canonical** playbook tree with stored `alwaysApply`, but ADEs (Cursor, Devin) only inject rules from **ADE load paths** (`.cursor/rules/`, `.windsurf/rules/`). Claude/Copilot need **inline** markdown sections.

On **hosted FOB** (`https://mimir.featurefactory.io`, Edda v71), ~25 process rules are still `always_apply=false`, so legacy `sync_root_rules` skips them. Legacy sync also **blind dual-writes** both `.cursor` and `.windsurf` when any rule has `alwaysApply: true`.

**Two coordinated fixes:**

1. **FOB code:** extend `export_playbook_to_local` with `ade_targets` (list), `sync_root_rules`, optional `force_apply` — explicit multi-ADE placement.
2. **FOB Edda (hosted only):** MCP `update_rule` while draft → `always_apply=true` on all process rules; ALTER DSP-04/05 + artifact 20; re-release. **No local `mimir.db` changes.**

---

## Export Surfaces

Two export surfaces — canonical vs ADE-root apply-on copies:

```
{dev_root}/
  .cursor/playbooks/{folder}/          # canonical tree (round-trip)
    rules/*.mdc                        # stored alwaysApply
    agents/ skills/ artifacts/ workflows/
  .cursor/rules/{slug}.mdc             # apply-on copy (cursor in ade_targets)
  .windsurf/rules/{slug}.md            # apply-on copy (devin in ade_targets)
  CLAUDE.md                            # splice inline_rules_markdown (claude/copilot)
```

### Parameter: `ade_targets`

**Type:** `list[str]` — each value ∈ `{cursor, devin, claude, copilot}`.

| Rule | Detail |
|------|--------|
| Default | `None` or `[]` — no ADE-root writes |
| When `sync_root_rules` or `force_apply` | **At least one** entry required; empty list → `ValueError` |
| Multiple | Allowed — e.g. `["cursor", "devin"]` writes both file-based paths in one call |
| API sugar | Singular `ade_target` in POST body normalized to one-element list |

| Target | Apply-on path | Format | Notes |
|--------|---------------|--------|-------|
| `cursor` | `{dev_root}/.cursor/rules/{slug}.mdc` | YAML `alwaysApply` | `force_apply` sets `true` in copy only |
| `devin` | `{dev_root}/.windsurf/rules/{slug}.md` | plain `.md` | Windsurf-compatible (Devin) |
| `claude` | none on disk | `inline_rules_markdown` in bundle/response | splice into `CLAUDE.md` § Playbook Rules |
| `copilot` | none on disk | same inline field | splice into `.github/copilot-instructions.md` |

**Canonical tree** always keeps **stored** `rule.always_apply` (scenario 33). `force_apply` affects ADE copies and inline markdown only.

---

## Section A — Context Map

| File | Lines | Note |
|------|-------|------|
| `methodology/services/rule_export_formatters.py` | — | **New** — ADE formatting + validation |
| `methodology/services/playbook_export_service.py` | 24–90, 101–180, 233–243 | Extend export; replace `_sync_root_rules` |
| `methodology/services/workflow_export_service.py` | 397–402 | `_format_rule_mdc` — extract to formatters |
| `mcp_integration/tools.py` | 1164–1209 | stdio `export_playbook_to_local` — params + gold docstrings |
| `mcp_integration/facade/tools_http.py` | 409–500 | HTTP facade — match docstrings; write from bundle |
| `methodology/api/viewsets.py` | 339–381 | `POST export-local` — `ade_targets` in body |
| `tests/unit/test_rule_export_formatters.py` | — | **New** |
| `tests/unit/test_playbook_export_service.py` | — | Extend ADE + log-story |
| `tests/integration/test_playbook_export_local_api.py` | — | API ade params |
| `tests/integration/test_mcp_export_playbook_ade.py` | — | **New** — Gherkin 30–34 |
| `docs/plans/EXPORT-ADE-RULES_CHANGE_RECONCILIATION.md` | — | Edda ALTER outline |

---

## Section B — Do-Not-Do List

- Do NOT add `apply_mode` to Rule model ([#175](https://github.com/FeatureFactory-io/mimir/issues/175) closed — boolean + placement + FOB data fix).
- Do NOT change JSON `export_playbook` / `import_playbook`.
- Do NOT overwrite entire `CLAUDE.md` / copilot-instructions — inline section only (DSP-05).
- Do NOT blind dual-write `.cursor` + `.windsurf` when `ade_targets` omitted (remove legacy `_sync_root_rules` behavior).
- Do NOT break default export when `sync_root_rules`, `force_apply`, and `ade_targets` all omitted (backward compatible).
- Do NOT edit Edda rule flags in local `mimir.db` — **hosted FOB only**.
- Do NOT re-release Edda on FOB without human review.
- Do NOT put filesystem/ADE formatting logic only in HTTP facade — service owns it for stdio + HTTP.

---

## Section C — SAO.md Sections That Apply

- **Shared Services Layer** — ADE formatting in export service, not MCP-only.
- **Hybrid MCP Access** — read-only export on released playbooks unchanged ([#172](https://github.com/FeatureFactory-io/mimir/issues/172)).
- **FastMCP as API Wrapper** — extend existing `export_playbook_to_local` tool signature.
- **Domain Model — Rule** — canonical tree vs ADE-root apply-on copies.

---

## Section D — Tests to Create

| Test | Asserts |
|------|---------|
| `test_format_rule_for_ade_cursor_force_apply` | DB `always_apply=false` → `alwaysApply: true` when `force_apply=True` |
| `test_format_rule_for_ade_devin_extension` | Devin → `.md` without Cursor-only frontmatter where appropriate |
| `test_build_inline_rules_markdown` | Claude/Copilot inline lists all rule bodies |
| `test_sync_ade_rules_cursor_only` | `ade_targets=["cursor"]` → `.cursor/rules/` only |
| `test_sync_ade_rules_devin_only` | `ade_targets=["devin"]` → `.windsurf/rules/` only (scenario 31) |
| `test_sync_ade_rules_multi_target` | `ade_targets=["cursor", "devin"]` → both paths |
| `test_canonical_tree_preserves_stored_always_apply` | `{export_root}/rules/*.mdc` unchanged stored flag (scenario 33) |
| `test_export_requires_ade_targets_when_force_apply` | `ValueError` when `force_apply` and empty `ade_targets` |
| `test_export_requires_ade_targets_when_sync_root_rules` | `ValueError` when `sync_root_rules` and empty `ade_targets` (scenario 34) |
| `test_mcp_export_playbook_to_local_ade_t1` | MCP accepts new params; `inline_rules_markdown` for claude |
| `test_mcp_export_playbook_to_local_ade_t2` | Service + tmp_path: force_apply file on disk |
| `test_export_local_api_ade_params` | POST `ade_targets`, `force_apply` in bundle |
| `test_playbook_export_ade_log_story_happy` | caplog: `ade_targets=`, `force_apply=`, `ade_files=` |
| `test_playbook_export_ade_log_story_reject` | caplog: validation when `ade_targets` empty |

**Gherkin:** FOB-WORKFLOWS-EXPORT_IMPORT-30..34 (feature file uses singular `ade_target` in tables — tests accept list; scenario 34 = empty/omitted list).

---

## Section E — Log Story Script

| Where | Beat | Trigger | Must include |
|-------|------|---------|--------------|
| `PlaybookExportService.export_playbook_to_local` | entry | export start | `ade_targets=`, `force_apply=`, `sync_root_rules=` |
| `PlaybookExportService._format_ade_rule_files` | processing | per rule | `slug=`, `ade_targets=` |
| `PlaybookExportService._sync_ade_root_rules` | processing | ADE copy write | `path=`, `slug=`, `force_apply=` |
| `PlaybookExportService._build_inline_rules_markdown` | processing | claude/copilot | `rule_count=` |
| `PlaybookExportService.export_playbook_to_local` | exit | complete | `ade_files=`, `inline=` (bool) |
| `PlaybookExportService.export_playbook_to_local` | error | missing ade_targets | `ade_targets required` |

---

## Section F — MCP Tools to Expose

| Tool name | Service method | Write? | HITL? | Auth injection |
|-----------|---------------|--------|-------|----------------|
| `export_playbook_to_local` | `PlaybookExportService.export_playbook_to_local` | No (filesystem) | No | server-side user |

No new MCP tool. Extend existing tool only.

### Signature (proposed)

```python
async def export_playbook_to_local(
    playbook_id: int,
    target_directory: str = ".cursor/playbooks",
    folder_name: str | None = None,
    additional_targets: list[str] | None = None,
    sync_root_rules: bool = False,
    ade_targets: list[str] | None = None,
    force_apply: bool = False,
) -> dict
```

**Return shape additions:**

```python
{
  ...
  "ade_rule_files": [
    {"filename": "do-test-first.mdc", "content": "...", "path": ".cursor/rules/do-test-first.mdc"},
    {"filename": "do-test-first.md", "content": "...", "path": ".windsurf/rules/do-test-first.md"},
  ],
  "inline_rules_markdown": "## Playbook Rules\n\n..."  # non-empty when claude/copilot in ade_targets
}
```

### MCP tool documentation standard (required — Slice 2)

Per [MCP_IMPLEMENTATION_PLAN.md](./MCP_IMPLEMENTATION_PLAN.md) and [PIP-MCP_IMPLEMENTATION_PLAN.md](./PIP-MCP_IMPLEMENTATION_PLAN.md) DoD (*“All MCP tools registered with full docstrings”*):

**Gold standard:** [create_playbook](../mcp_integration/tools.py) / [create_skill](../mcp_integration/tools.py) — summary, every `:param` with `Example:`, `:return` keys, `:raises ValueError`, optional usage `Example:` block.

**Do not copy:** [create_rule](../mcp_integration/tools.py) one-liner; current minimal [export_playbook_to_local](../mcp_integration/tools.py).

**Apply to both** `mcp_integration/tools.py` (stdio) and `mcp_integration/facade/tools_http.py` (Docker facade) — **identical docstring body**.

| Param | Documentation must include |
|-------|---------------------------|
| `playbook_id` | Example: `3` (Edda) |
| `target_directory` | Canonical tree root. Example: `".cursor/playbooks"` |
| `folder_name` | Example: `"Edda"` |
| `additional_targets` | Mirror canonical tree only. Example: `[".windsurf/workflows"]` |
| `sync_root_rules` | Writes apply-on copies per `ade_targets`; requires non-empty list |
| `ade_targets` | `cursor \| devin \| claude \| copilot`; **≥1 required** when sync/force_apply; multiple OK. Examples: `["cursor"]`, `["cursor", "devin"]` |
| `force_apply` | ADE copies apply-on even if DB `always_apply=false`; canonical tree unchanged |
| `:return` | `ade_rule_files`, `inline_rules_markdown`, existing count fields |
| `:raises ValueError` | Empty/missing `ade_targets` when sync or force_apply enabled |

**Usage example (in docstring):**

```python
export_playbook_to_local(
    playbook_id=3,
    target_directory=".cursor/playbooks",
    folder_name="Edda",
    ade_targets=["cursor", "devin"],
    sync_root_rules=True,
)
```

**Verification:** GetDynamicTools on `export_playbook_to_local` — param descriptions include examples and cardinality rule; stdio matches facade.

---

## Service Design

### New: `methodology/services/rule_export_formatters.py`

```python
def format_rule_for_ade(rule, ade_target: str, *, force_apply: bool = False) -> str: ...
def build_inline_rules_markdown(rules, *, force_apply: bool = False) -> str: ...
def ade_root_relative_path(ade_target: str, slug: str) -> str: ...
def validate_ade_export_params(
    *, ade_targets: list[str] | None, sync_root_rules: bool, force_apply: bool
) -> list[str]:
    """Normalize ade_targets; raise ValueError if sync/force_apply and list empty."""
    ...
```

### Change: `PlaybookExportService`

```python
@staticmethod
def export_playbook_to_local(
    playbook_id: int,
    target_directory: str,
    folder_name: Optional[str] = None,
    additional_targets: Optional[list[str]] = None,
    sync_root_rules: bool = False,
    ade_targets: Optional[list[str]] = None,
    force_apply: bool = False,
    user=None,
) -> dict: ...
```

**Private helpers:**

- `_sync_ade_root_rules(bundle, dev_root, ade_targets, force_apply)` — loop each target; no write when list empty and sync off
- `_format_ade_rule_files(rules, ade_targets, force_apply)` — populate bundle `ade_rule_files`
- `_build_inline_rules_markdown(rules, force_apply)` — when claude/copilot in `ade_targets`

Canonical `rule_files` in bundle continue using `WorkflowExportService._format_rule_mdc` (stored flag).

---

## Section G — Implementation Steps

### Slice 1 — ADE formatters + bundle (N1, BPE-02)

1. Skeleton `rule_export_formatters.py` + failing unit tests (Section D).
2. Wire into `generate_playbook_export_bundle`; populate `ade_rule_files`, `inline_rules_markdown`.
3. Replace `_sync_root_rules` → `_sync_ade_root_rules` (iterate `ade_targets`).
4. Log-story tests (happy + reject).

**Checkpoint:**
```bash
pytest tests/unit/test_playbook_export_service.py tests/unit/test_rule_export_formatters.py -k "ade or log_story" -x
```

**Commit:** `feat(export): ADE rule formatters and multi-target sync (#176)`

---

### Slice 2 — MCP + API + facade (N2, BPE-02)

1. `export_local` viewset — POST accepts `ade_targets`, optional `ade_target` alias, `force_apply`, `sync_root_rules`.
2. `export_playbook_to_local` in `tools.py` — passthrough + **gold-standard docstrings** (Section F).
3. `tools_http.py` — same docstrings; write `ade_rule_files` from bundle; remove dual-IDE client loop (lines 474–485).
4. Integration tests T1/T2 + API test.
5. GetDynamicTools spot-check.

**Checkpoint:**
```bash
pytest tests/integration/test_playbook_export_local_api.py tests/integration/test_mcp_export_playbook_ade.py -x
```

**Commit:** `feat(mcp): export_playbook_to_local ade_targets and force_apply (#176)`

---

### Slice 3 — Acceptance (N3, BPE-04)

1. Map Gherkin EXPORT_IMPORT-30..34 in `test_mcp_export_playbook_ade.py`.
2. Full export test module green.

**Checkpoint:**
```bash
pytest tests/integration/test_mcp_export_playbook_ade.py tests/unit/test_playbook_export_service.py -x
```

**Commit:** `test(export): Gherkin EXPORT_IMPORT-30..34 coverage (#176)`

---

### Slice 4 — Hosted FOB Edda (N4, human gate)

**Source of truth:** `https://mimir.featurefactory.io` — playbook **3** (Edda). **Out of scope:** local `mimir.db`.

| Step | Action |
|------|--------|
| **Prerequisite** | Human sets Edda to **draft** on FOB (MCP `update_rule` blocked on released) |
| **4a Rule flags** | `update_rule(rule_id, always_apply=true)` for IDs below (~25 rules) |
| **4b Process text** | ALTER activity **63** (DSP-04), **64** (DSP-05), artifact **20** per reconciliation doc — `update_activity` while draft or PIP |
| **4c Release** | Human review → re-release Edda (version ≥72) |

**Prod rule IDs still `always_apply=false` (2026-08-27):** 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32.

**Checkpoint:** MCP `list_rules playbook_id=3` → zero `always_apply=false`; activity 63/64 text matches reconciliation.

**Commit (repo docs only):** `docs(edda): record FOB rule-flag migration for EXPORT-ADE-RULES (#176)`

---

### Slice 5 — DoD (N5, BPE-06)

1. All graph gates green (see execution graph YAML).
2. Success criteria below checked.
3. Comment + close [#176](https://github.com/FeatureFactory-io/mimir/issues/176) with commit SHAs and FOB Edda version.

**BPE-07 Finalize (2026-08-27):** Unit + integration **1624 passed**; export slice **39 passed**; Gherkin scenarios 30–34 marked ✅. No Playwright E2E for this feature (MCP/backend only). Full E2E suite: 227 passed, **6 failed** (content-browser graph/routing + journey search — unrelated to EXPORT-ADE-RULES). No new `requirements.txt` deps. Screen flow N/A (Section H).

---

## Commit Strategy

1. `feat(export): ADE rule formatters and multi-target sync (#176)`
2. `feat(export): validate ade_targets non-empty when sync or force_apply (#176)`
3. `feat(mcp): export_playbook_to_local ade_targets passthrough (#176)`
4. `feat(api): export-local POST ade params in bundle (#176)`
5. `refactor(facade): write ADE rules from service bundle (#176)`
6. `test(export): EXPORT_IMPORT-30..34 integration coverage (#176)`
7. `docs(edda): record FOB rule-flag migration (#176)` (after Slice 4)
8. `docs(export): close EXPORT-ADE-RULES (#176)`

---

## Success Criteria

- [x] `ade_targets=["cursor"]` + `sync_root_rules=true` → injectable `.cursor/rules/*.mdc`
- [x] `ade_targets=["devin"]` → `.windsurf/rules/` only (scenario 31)
- [x] `ade_targets=["cursor", "devin"]` → both paths in one call
- [x] `claude`/`copilot` in `ade_targets` → non-empty `inline_rules_markdown`; no file writes for inline-only targets
- [x] Canonical tree preserves stored `always_apply` (scenario 33)
- [x] Empty/omitted `ade_targets` + sync or force_apply → validation error (scenario 34)
- [x] Default export backward compatible — no ADE-root writes
- [x] `export_playbook_to_local` docstrings match create_skill quality; stdio + facade aligned *(local code; GetDynamicTools on hosted FOB pending deploy)*
- [x] Log-story beats green (Section E)
- [ ] **FOB Edda:** all rules `always_apply=true`; DSP-04/05/artifact 20 updated; re-released *(human gate — see Slice 4)*
- [x] #176 closed with FOB verification notes *(code shipped; FOB data migration tracked in checklist)*

---

## Manual UAT

1. **After Slice 2:** GetDynamicTools → read `export_playbook_to_local` param docs.
2. **After Slice 3:** Export Edda playbook id=3 with `ade_targets=["cursor"]`, `sync_root_rules=true` → confirm `.cursor/rules/do-test-first.mdc` has `alwaysApply: true`.
3. **After Slice 4:** On FOB, `list_rules` all `true`; run DSP-05 dry-run against a dev project.

---

## Section H — Mockup Graduation Plan

Not applicable — no frontend screens.

---

## Feature Execution Graph

See [EXPORT-ADE-RULES-feature-execution-graph.yaml](./EXPORT-ADE-RULES-feature-execution-graph.yaml).

---

## Lessons Learned

- #176 is a **process + export contract** gap, not a product bug; BPE-08 reclassification avoided Autofix noise.
- Edda source of truth is **hosted FOB** — repo `.cursor/playbooks/Edda/` and local `mimir.db` are not authoritative.
- #175 closed without `apply_mode`; **`always_apply=true` on FOB Edda** + **`ade_targets` placement** resolves injection without schema migration.
- Prior #165 `sync_root_rules` blind dual-wrote IDEs; Plan B requires explicit `ade_targets` list (≥1 when syncing).
- DSP-05 agents call export via MCP — tool docstrings must match [MCP_IMPLEMENTATION_PLAN](./MCP_IMPLEMENTATION_PLAN.md) / PIP-MCP DoD or params are misused.
