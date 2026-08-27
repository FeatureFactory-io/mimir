# FOB Edda migration checklist — EXPORT-ADE-RULES (Slice 4)

**Playbook:** Edda (id=3) on `https://mimir.featurefactory.io`  
**Status (2026-08-27):** `released` v71 — **MCP `update_rule` blocked until draft**

---

## Prerequisite (human)

1. FOB UI → Playbook **Edda** → set status to **draft**
2. Confirm via MCP: `get_playbook(playbook_id=3)` → `status: draft`

---

## 4a — Rule flags (`always_apply=true`)

Run for each rule currently `false` (MCP `list_rules playbook_id=3`):

| rule_id | slug |
|--------:|------|
| 8 | do-add-todos-for-incomplete-items |
| 9 | do-check-before-deleting |
| 10 | do-check-previous-commits |
| 11 | do-diagrams-element-by-element |
| 12 | do-docstring-format |
| 13 | do-fix-tests |
| 14 | do-github-issues |
| 15 | do-import-on-module-level |
| 16 | do-informative-logging |
| 17 | do-look-via-human-eye |
| 18 | do-not-go-into-debugging-loops |
| 19 | do-not-mock-in-integration-tests |
| 20 | do-plan-before-doing |
| 21 | do-pull-frequently |
| 22 | do-runner |
| 23 | do-semantic-versioning-on-ui-elements |
| 24 | do-skeletons-first |
| 25 | do-test-fixture-data-management |
| 26 | do-test-first |
| 27 | do-update-tests-after-bugfixing |
| 28 | do-validate-api-contracts |
| 29 | do-view-drawio-diagrams |
| 30 | do-write-scenarios |
| 31 | keep-docstrings-consistent |
| 32 | tooltips |

Example MCP call per row:

```
update_rule(rule_id=26, always_apply=true)
```

**Verify:** `list_rules(playbook_id=3)` → zero entries with `always_apply: false`

---

## 4b — Process text (while draft)

ALTER per [EXPORT-ADE-RULES_CHANGE_RECONCILIATION.md](./EXPORT-ADE-RULES_CHANGE_RECONCILIATION.md):

| Entity | Activity / artifact | Changes |
|--------|---------------------|---------|
| DSP-04 | Activity **63** | Devin label; record `ade_targets`; fix overwrite wording |
| DSP-05 | Activity **64** | §3b `export_playbook_to_local` with `ade_targets`, `sync_root_rules=true` |
| Artifact **20** | | Apply-on copy wording; not “always active (auto-loaded)” |

Use `update_activity` while draft or `create_pip` for audit trail.

---

## 4c — Re-release

Human review → release Edda (target version ≥72).

---

## FOB code dependency

FOB export changes ship in commits `d8b9d08`, `add42ed` (repo). Prod FOB must deploy these before DSP-05 §3b works end-to-end on hosted MCP.
