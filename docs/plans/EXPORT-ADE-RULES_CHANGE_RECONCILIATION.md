# Change Reconciliation: ADE-Aware Rule Export (Plan B)

**Feature ref:** EXPORT-ADE-RULES  
**Trigger:** [GitHub #176](https://github.com/FeatureFactory-io/mimir/issues/176) — enhancement / change request (not a product bug)  
**BPE activity:** BPE-08 Process Change Request  
**Approved:** 2026-08-27 (user execution of BPE-08 plan)  
**Related:** [#175](https://github.com/FeatureFactory-io/mimir/issues/175) closed — `apply_mode` enum **not planned**; Plan B (this CR) is the approved alternate

---

## Trigger summary

When teams run **DSP-05** (Generate AI IDE Configuration) and export an Edda playbook, mandatory process rules **appear on disk but never enter the agent context**.

**Root causes (as-built):**

1. Rules land under the playbook tree (`.cursor/playbooks/{name}/rules/`), not ADE load paths (`.cursor/rules/`, `.windsurf/rules/`).
2. Export maps Mimir `always_apply` 1:1 to Cursor `alwaysApply`. Most Edda process rules are `always_apply=false` → `alwaysApply: false` with no globs/description → Cursor never injects.
3. `sync_root_rules` copies only rules already marked `alwaysApply: true`, writes to **both** `.cursor` and `.windsurf`, defaults **off**, and is never required by DSP-05.
4. DSP-05 generates only `_ai-context`; DSP-04 says rules "will NOT be overwritten"; artifact 20 claims rules are "Always active (auto-loaded)".

**Observed impact:** Yggdrasil Act 10 agents skipped test-first, mockup graduation, and BPE-06.

---

## Agreed solution (Plan B)

Two coordinated slices — **minimal FOB export changes** + **Edda PIP** (DSP-04, DSP-05, artifact 20):

| Slice | Owner | Change |
|-------|-------|--------|
| Edda rule data | FOB playbook 3 (draft → MCP → re-release) | Set `always_apply=true` on all process rules currently `false` (~25 on prod). Team decision: craft rules are always-on in ADE; activity M2M still scopes *activity* attachment. **No local `mimir.db` changes.** |
| FOB export | `export_playbook_to_local` + MCP/API passthrough | Add `ade_target` + optional `force_apply`; format for chosen ADE; with `sync_root_rules=true`, write apply-on copies to ADE load paths. Canonical tree keeps stored `always_apply` (now `true` for Edda). |
| Edda process | PIP on released playbook | ALTER DSP-04 (record `ade_target`), DSP-05 (call export; verify / splice Claude-Copilot), artifact 20 (truthful apply-on wording). |

Export **formats and places**; DSP-05 **orchestrates** (does not hand-edit dozens of rule files).

---

## Reconciliation matrix

**Affected Screen IDs:** none (MCP + export contract). Scenario IDs: `FOB-WORKFLOWS-EXPORT_IMPORT-*`, `MCP-RULE-*`.

| Layer | Source | Current state | Drift? | Notes |
|-------|--------|---------------|--------|-------|
| User journey | `docs/features/user_journey.md` Act 10 | JSON/MPA GUI export only | **Y** | Local ADE markdown sync via MCP not documented |
| Scenarios | `workflows-export-import.feature` | `.mdc` with stored `alwaysApply`; optional dual-IDE `sync_root_rules` | **Y** | Missing `ade_target`, `force_apply`, single-ADE placement, Claude/Copilot inline |
| Mockups | — | Not present | **N/A** | No UI |
| Screen flow | — | Not present | **N/A** | No UI |
| IA guidelines | `docs/ux/IA_guidelines.md` | No export UI | **N/A** | No UI |
| Prior plan | `PLAYBOOK-EXPORT-TO-LOCAL_IMPLEMENTATION_PLAN.md` | #165 shipped tree + optional sync | **Y** | Sync insufficient for Plan B; plan remains historical |
| Architecture | `docs/architecture/SAO.md` | Rules → `rules/*.mdc` under playbook folder | **Y** | Missing canonical vs ADE-root copy distinction |
| As-built | `playbook_export_service.py`, `workflow_export_service.py`, `tools_http.py` | Cursor-only `.mdc`; sync skips `alwaysApply: false`; dual-IDE copy | **Y** | Matches Yggdrasil failure mode |
| Edda DSP-04/05 / artifact 20 | Released playbook id=3 v71 | Summary-only config; misleading "always active" | **Y** | PIP ALTERs (below); not editable in-repo as source of truth |
| MCP rules CRUD | `interact-with-rules-via-mcp.feature` | `always_apply` on model | **N** | Unchanged |

**Fast path:** not applicable (multi-layer drift).

---

## Proposed spec diffs (applied in BPE-08 Step 3)

### 1. `docs/features/act-3-workflows/workflows-export-import.feature`

Add scenarios **FOB-WORKFLOWS-EXPORT_IMPORT-30..34** (see applied file):

- **30** — `ade_target=cursor` + `sync_root_rules` + `force_apply` → `.cursor/rules/{slug}.mdc` with `alwaysApply: true` even when DB `always_apply=false`
- **31** — `ade_target=devin` → `.windsurf/rules/{slug}.md` only (not `.cursor/rules/`)
- **32** — `ade_target=claude` or `copilot` → bundle includes `inline_rules_markdown`; no ADE-root rule files
- **33** — Canonical `{export_root}/rules/*.mdc` retains **stored** `always_apply` (round-trip)
- **34** — `sync_root_rules` or `force_apply` without `ade_target` → validation error

### 2. `docs/architecture/SAO.md`

Extend Domain Model **Rule** bullet: two export surfaces — canonical playbook tree vs ADE-root apply-on copies (see applied edit).

### 3. Unchanged

- `docs/features/act-13-mcp/interact-with-rules-via-mcp.feature`
- JSON `export_playbook` / `import_playbook`
- `Rule.always_apply` model field

### 4. User journey (deferred note)

Act 10 remains JSON/MPA-focused. Optional follow-up CR: add MCP local-tree export narrative — **not in this CR**.

---

## Proposed Edda PIP outline (text only — apply via PIP after FOB ships)

**Playbook:** Edda (id=3, released v71)  
**PIP title (suggested):** ADE-aware rule export in DSP-05 (Plan B)

### ALTER Activity 63 — Choose Target AI IDE

- Replace **Windsurf** row label with **Devin** (path remains `.windsurf/rules/*.md`; Devin is Windsurf-compatible per README).
- In "Record Choice", add field: `ade_target: cursor | devin | claude | copilot` (one per selected primary target).
- Replace "Existing rules will NOT be overwritten" with: canonical playbook export tree is unchanged; DSP-05 writes **ADE apply-on copies** (frontmatter/placement) so the target IDE injects rules; rule **bodies** in Mimir are not ALTERed.

### ALTER Activity 64 — Generate AI IDE Configuration

Add step after **§3 Customize for Target Format**:

**§3b Enable playbook rules for target ADE**

1. Call `export_playbook_to_local(playbook_id=<Edda>, target_directory=".cursor/playbooks", folder_name="<slug>", ade_target=<from DSP-04>, sync_root_rules=true, force_apply=true)`.
2. **Cursor / Devin:** Verify ADE load folder contains one file per playbook rule with apply-on frontmatter (`alwaysApply: true` or Devin `.md` equivalent).
3. **Claude / Copilot:** Splice `inline_rules_markdown` from export response into `## Playbook Rules` section of `CLAUDE.md` or `.github/copilot-instructions.md` (do not replace entire file).
4. Present rule inventory table to user before commit (existing Step 4).

Update deliverables: include ADE rule sync verification.

### ALTER Artifact 20 — Windsurf/Cursor Rules Template

- Documentation map row: change "Always active (auto-loaded)" → "Apply-on copies written by DSP-05 to ADE load path".
- Section "Existing Rules (auto-loaded)" → "Playbook rules (ADE apply-on)"; note Cursor requires `.cursor/rules/` with `alwaysApply: true`; list comes from export, not assumption.
- Add placeholder `{AdeRuleInventory}` optional one-line per slug.

---

## Explicit non-goals

- [#175](https://github.com/FeatureFactory-io/mimir/issues/175) `apply_mode` enum on Rule model (closed **not planned** — see issue resolution comment)
- JSON `export_playbook` behavior changes
- Product code in BPE-08 (this document + spec edits only)
- Edda PIP create/submit/apply in BPE-08 (deferred to BPE-01 → BPE-02 implementation phase)

## Explicit goals (added)

- Mass-update Edda `Rule.always_apply` → `true` on **hosted FOB** via MCP `update_rule` while draft (~25 rules); re-release after review — not via local seed

---

## Open questions — resolved

| Question | Decision |
|----------|----------|
| Relabel #176? | Edit in place: remove `bug`/`copilot`; add `enhancement`; link this recon doc |
| Edda PIP in recon vs BPE-01? | Full ALTER outline in this doc; PIP drafting in BPE-01 implementation plan |

---

## Next step

**BPE-01 Plan Feature** → `docs/plans/EXPORT-ADE-RULES_IMPLEMENTATION_PLAN.md` + feature execution graph (no product code until BPE-02+).
