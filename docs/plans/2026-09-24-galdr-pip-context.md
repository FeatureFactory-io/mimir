# Bug #185: review the complete PIP target state

## Context and root cause
PIP 78's saved rejection for #rit-1 explicitly reviewed the row in isolation, despite its parent #wf-rit being a prior ADD. The EB compose template documents GALDR_USE_TARGET_STATE but omits it from the container environment; base settings default false while tests force true. Both prompt formats also omit structural ref fields; holistic change content is truncated at 500 characters.

## A. Context map
- deploy/docker-compose.tmpl.yml and docker-compose.prod.yml: container settings boundary.
- mimir/settings/base.py and methodology/services/galdr_engine.py: review mode and complete assessment persistence.
- methodology/services/galdr_prompts.py: all pending changes and parent/phase/producer refs.
- methodology/services/galdr_client.py: output budget for large batches.
- tests/integration/test_galdr_target_state.py: real DB and deterministic test client.

## B. Boundaries
No schema/seed change. No production PIP edits, resubmission, or automatic acceptance. Preserve human PIP finalization. No manual AWS changes. Do not promise deterministic semantic LLM judgments; deterministic structural validation and complete shared context address false missing-parent rejections.

## C. SAO and specifications
SAO Galdr AI Engine, Structured PIPs, Shared Services. Existing act-9 PIP review and act-13 MCP PIP lifecycle specifications apply.

## D. Tests
Reproduce missing flag in both compose manifests, missing ref/full-content context, incomplete/foreign/duplicate assessment acceptance. Exercise a 58-change real-DB PIP, repeated submission and pending parent dry-run rollback. Reject missing parents structurally before LLM review. Run focused Galdr/PIP tests then release regression suite.

## E. Log story
Log chosen review mode, PIP and batch size. Reject incomplete/duplicate/foreign assessments before any persistence. Add non-secret review mode to health JSON for deployment read-back.

## F. MCP
No new tools. Existing PIP submission uses shared review engine.

## G. Implementation
1. Pass holistic flag into both production compose manifests and default base mode to holistic.
2. Include complete pending changes and structural fields in both prompt paths; describe validated same-PIP parents and supported secondary workflow membership.
3. Raise holistic output budget for the reported 58-row batch, reject truncated responses, require exactly one assessment for every submitted row.
4. Verify runtime review mode through health after existing build/promote workflows.

## H. UI
No screens changed. No migration.

## Verification results
- Red: configuration, structural-reference prompt, completeness and truncation regressions failed before implementation.
- Focused PIP/Galdr/health regression: 138 passed, 1 skipped.
- Full release-workflow regression selection: 1624 passed, 3 skipped on local SQLite.
- Live claude-sonnet-4-5: two identical synthetic 58-change requests each returned 58 complete ACCEPT assessments and correctly resolved the pending parent. No production records were changed. Semantic LLM wording varied; deterministic editorial judgments are not claimed.
- Direct AWS inspection was unavailable due to expired local login. Deployment uses existing GitHub workflow credentials; runtime review mode is verified via non-secret health JSON after promotion.
