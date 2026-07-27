# Implementation Plan: PIP Activity Predecessor & Order (#168)

**Feature**: FOB-PIP-PRED — Structural activity sequencing via PIP apply  
**GitHub Issue**: [#168](https://github.com/phainestai/mimir/issues/168)  
**Branch**: `feature/pip-activity-predecessor-order`  
**Spec**: Extend `docs/features/act-9-pips/pips-link-changes.feature` (new scenarios FOB-PIP-LINK-16..20)  
**UAT**: Manual — accept sequencing PIP on released Edda; verify graph in UI + MCP `get_activity`

---

## Problem Statement

Accepted PIPs cannot mutate `Activity.predecessor` or display `order`. Authors fixing broken chains (e.g. MIN 178→183, DTA 58→200→201→59) can only ALTER guidance text. MCP `set_predecessor` is blocked on released playbooks, so PIP is the only path — but PIP apply has no predecessor/order mutations.

---

## Section A — Context Map

| File | Lines | Note |
|------|-------|------|
| `methodology/models/pip_change.py` | 26–37 | `RELATIONSHIP_TYPE_CHOICES` — add `activity_predecessor` |
| `methodology/services/pip_link_service.py` | 29–35, 159–188 | Endpoint map + `relationship_exists` — wire predecessor |
| `methodology/services/pip_apply_changes_service.py` | 356–427, 453–465 | `_apply_link_or_unlink` + `_apply_alter` Activity branch |
| `methodology/services/activity_service.py` | 366–398 | `set_predecessor` — reuse; add `clear_predecessor`, `set_activity_order` |
| `mcp_integration/tools.py` | 2892–2930 | `add_pip_change` docstring + `relationship_type` enum |
| `mcp_integration/facade/tools_http.py` | ~1174+ | Mirror `add_pip_change` params if HTTP facade exposes them |
| `methodology/api/viewsets_resources.py` | PIP viewset | REST `add_pip_change` payload validation |
| `tests/integration/test_pip_link_changes.py` | — | Pattern for LINK apply integration tests |

---

## Section B — Do-Not-Do List

- Do NOT bypass `ActivityService.set_predecessor` cycle checks — PIP apply must call the same service method as MCP/UI.
- Do NOT add MCP-specific logic inside services — shared `ActivityService` / `PipApplyChangesService` only.
- Do NOT allow direct `predecessor_id` writes on released playbooks outside PIP finalize path.
- Do NOT repurpose `PipChange.order` (PIP row sequence) as activity display order — add `display_order` field instead.
- Do NOT delete existing LINK relationship types or change their semantics.
- Do NOT mock DB in integration tests for apply path.
- Do NOT defer logging to a final slice — beats in Section E ship with behavior.

---

## Section C — SAO.md Sections That Apply

- **Structured PIPs** — typed LINK/UNLINK per relationship; apply routes to existing services.
- **Hybrid MCP Access** — released playbooks: structural fixes only via PIP accept, not `set_predecessor`.
- **Shared Services Layer** — `PipApplyChangesService` → `ActivityService`; no MCP logic in services.
- **Galdr AI Review** — new relationship type must appear in change rows Galdr already assesses (no Galdr code change unless prompt omits unknown rel types).

---

## Section D — Tests to Create

| Test | Asserts |
|------|---------|
| `test_add_pip_change_link_activity_predecessor_stored` | Draft PIP accepts LINK `activity_predecessor` source=pred target=act |
| `test_add_pip_change_link_predecessor_duplicate_rejected` | Second LINK same pair → ValidationError |
| `test_add_pip_change_unlink_predecessor_requires_link` | UNLINK when no predecessor → rejected at draft persist |
| `test_pip_apply_link_activity_predecessor_sets_fk` | Admin accept + finalize → `act.predecessor_id == pred.pk` and `pred.successor_id == act.pk` |
| `test_pip_apply_unlink_activity_predecessor_clears_fk` | UNLINK clears predecessor + successor sync |
| `test_pip_apply_link_predecessor_cycle_rejected` | LINK creating cycle → ValidationError at apply, playbook unchanged |
| `test_add_pip_change_alter_activity_display_order` | ALTER Activity with `display_order` persists on change row |
| `test_pip_apply_alter_activity_display_order_renormalizes` | Accept ALTER order → activities in workflow have contiguous 1..N orders |
| `test_mcp_add_pip_change_activity_predecessor_in_doc` | MCP tool accepts `relationship_type=activity_predecessor` (T1-style via direct tool call) |
| `test_pip_apply_predecessor_log_story_happy` | caplog: apply LINK logs predecessor ids + pip id |
| `test_pip_apply_predecessor_cycle_log_story_reject` | caplog: cycle branch logged before ValidationError |

**Feature file** (add to `pips-link-changes.feature`):

- FOB-PIP-LINK-16: LINK activity_predecessor stored in draft  
- FOB-PIP-LINK-17: Admin finalize sets predecessor FK  
- FOB-PIP-LINK-18: UNLINK clears predecessor  
- FOB-PIP-LINK-19: Cycle rejected at apply  
- FOB-PIP-LINK-20: ALTER display_order reorders within workflow  

---

## Section E — Log Story Script

| Where | Beat | Trigger | Must include |
|-------|------|---------|--------------|
| `PIPService.add_change` | entry | LINK activity_predecessor | pip_id=, relationship_type=activity_predecessor |
| `pip_link_service.validate_link_change_for_persist` | validation | endpoint refs resolved | source_ref=, target_ref=, playbook_id= |
| `PipApplyChangesService._apply_link_or_unlink` | processing | LINK predecessor | pip=, activity_id=, predecessor_id= |
| `ActivityService.set_predecessor` | exit | success | activity id=, predecessor id=, successor synced |
| `ActivityService.clear_predecessor` | exit | UNLINK | activity id=, cleared predecessor id= |
| `PipApplyChangesService._apply_alter` | processing | ALTER display_order | activity_id=, old_order=, new_order= |
| `ActivityService.set_activity_order` | exit | renormalize | workflow_id=, activity_id=, final_order= |
| `PipApplyChangesService._apply_link_or_unlink` | error | cycle detected | pip=, cycle, ValidationError |

---

## Section F — MCP Tools to Expose

| Tool name | Service method | Write? | HITL? | Auth injection |
|-----------|---------------|--------|-------|----------------|
| `add_pip_change` (extend) | `PIPService.add_change` | Yes (draft PIP) | No | server-side user via `get_current_user` |
| `preview_pip_diff` (unchanged) | — | No | No | — |

No new MCP tool. Extend `add_pip_change` schema:

- `relationship_type`: add `activity_predecessor` (source = predecessor Activity, target = successor Activity)
- `display_order`: optional int on ALTER Activity rows (new PipChange field)

---

## Design Decisions

### 1. Predecessor via LINK/UNLINK (primary)

```
LINK  relationship_type=activity_predecessor
      source_entity_ref=<predecessor_activity_pk|#ref>
      target_entity_ref=<successor_activity_pk|#ref>

UNLINK same pair — clears target.predecessor (and syncs successor pointers)
```

Semantics match issue #168 and existing LINK dispatch pattern.

### 2. Display order via ALTER (secondary)

Add nullable `PipChange.display_order` (`PositiveSmallIntegerField`, null=True) used only when `entity_type=Activity` and `change_type=ALTER`. Apply calls new `ActivityService.set_activity_order(activity, display_order)` which reorders within workflow (reuse `_renormalize_activity_orders` logic extracted to ActivityService).

### 3. clear_predecessor helper

```python
ActivityService.clear_predecessor(activity)  # clears FK, fixes stale successor on old pred
```

---

## Implementation Steps (small slices)

### Slice 0 — Branch

```bash
git checkout -b feature/pip-activity-predecessor-order
```

### Slice 1 — Model + migration (RED)

1. Add `REL_ACTIVITY_PREDECESSOR = "activity_predecessor"` to `PipChange`.
2. Add `display_order` nullable field on `PipChange`.
3. Migration `001X_pipchange_predecessor_display_order.py`.
4. Write failing tests for LINK persist (no apply yet).

### Slice 2 — Link validation (GREEN persist)

1. Extend `_RELATIONSHIP_ENDPOINTS`: `(Activity, Activity)` — source=predecessor, target=successor.
2. `relationship_exists`: `target.predecessor_id == source_id`.
3. Update `PIPService.add_change` / serializers to accept new rel + display_order.
4. Green persist tests.

### Slice 3 — Apply LINK/UNLINK predecessor (GREEN apply)

1. `ActivityService.clear_predecessor`.
2. `_apply_link_or_unlink` branch → `set_predecessor` / `clear_predecessor`.
3. Integration tests FOB-PIP-LINK-16..18 + log-story happy.

### Slice 4 — Cycle guard + log-story reject (GREEN)

1. Ensure cycle raises at apply (existing `activity.clean()`).
2. `test_pip_apply_predecessor_cycle_*` + log-story reject.

### Slice 5 — ALTER display_order (GREEN)

1. `ActivityService.set_activity_order`.
2. `_apply_alter` Activity branch reads `change.display_order`.
3. Tests FOB-PIP-LINK-20.

### Slice 6 — MCP + docs

1. Update `add_pip_change` docstring in `tools.py` + facade.
2. Extend `pips-link-changes.feature`.
3. Update SAO PIP LINK dispatch bullet.

### Slice 7 — Full pytest + UAT note

```bash
.venv/bin/python -m pytest tests/integration/test_pip_link_changes.py tests/integration/test_pip_entity_crud.py -x
.venv/bin/python -m pytest tests/
```

---

## Commit Strategy

- `feat(pip): add activity_predecessor LINK relationship type` (#168)
- `feat(pip): apply predecessor LINK/UNLINK via ActivityService` (#168)
- `feat(pip): ALTER Activity display_order on PIP accept` (#168)
- `test(pip): predecessor link apply and log-story coverage` (#168)
- `docs(pip): extend pips-link-changes feature for predecessor` (#168)

---

## Success Criteria (BPE-06)

- [ ] Feature scenarios FOB-PIP-LINK-16..20 in Gherkin
- [ ] All Section D tests green
- [ ] Log-story tests prove Section E beats
- [ ] Edda-style chain PIP can be expressed and applied without admin manual graph edits
- [ ] Plan approved by user
