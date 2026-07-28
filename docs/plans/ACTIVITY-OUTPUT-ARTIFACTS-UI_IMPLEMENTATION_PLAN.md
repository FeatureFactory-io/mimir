# Implementation Plan: Activity Detail Output Artifacts UI (#167)

**Feature**: FOB-ART-OUT — Symmetric input/output artifact cards on activity detail  
**GitHub Issue**: [#167](https://github.com/FeatureFactory-io/mimir/issues/167)  
**Branch**: `feature/activity-output-artifacts-ui`  
**Spec**: `docs/features/act-6-artifacts/artifacts-flow.feature` — ART-FLOW-16, ART-FLOW-19  
**UAT**: Browse activity with outputs on local server; verify badge count + links

---

## Problem Statement

Activity detail page shows **Input Artifacts** but not **Output Artifacts**. View already loads `artifact_outputs` into context; `_embed.html` renders outputs; main `detail.html` does not. Spec ART-FLOW-16 requires the section.

---

## Section A — Context Map

| File | Lines | Note |
|------|-------|------|
| `methodology/activity_views.py` | 381–417 | Already passes `artifact_outputs` — no view change required |
| `templates/activities/detail.html` | 262–304 | Input Artifacts card — mirror for Output |
| `templates/activities/_embed.html` | 56–68 | Reference markup for output list |
| `methodology/services/artifact_service.py` | ~240 | `get_artifacts_for_activity` — producer side |
| `docs/features/act-6-artifacts/artifacts-flow.feature` | 166–197 | ART-FLOW-16/19 acceptance criteria |
| `tests/integration/test_activity_view.py` | — | Extend with output artifacts assertions |

---

## Section B — Do-Not-Do List

- Do NOT add new service methods — reuse `ArtifactService.get_artifacts_for_activity`.
- Do NOT change MCP `get_activity` — already returns `output_artifacts`.
- Do NOT duplicate query logic in the template — use context `artifact_outputs` only.
- Do NOT add React/SPA — Django template + Bootstrap card matching Input Artifacts.
- Do NOT skip `data-testid` attributes (Playwright/E2E readiness).
- Do NOT defer logging — view already logs input/output counts at INFO.

---

## Section C — SAO.md Sections That Apply

- **UI**: Django templates + Bootstrap 5.3; semantic versioning via `data-testid`.
- **Shared Services Layer** — view calls `ArtifactService`; template is thin.
- **Artifact model** — `produced_by` FK defines outputs; symmetric to `ArtifactInput` for inputs.

---

## Section D — Tests to Create

| Test | Asserts |
|------|---------|
| `test_activity_detail_shows_output_artifacts_section` | 200 + `data-testid="output-artifacts-card"` when outputs exist |
| `test_activity_detail_output_artifact_links_and_badges` | Each output: name link, type badge, required badge when `is_required` |
| `test_activity_detail_no_outputs_shows_empty_state` | Empty state `data-testid="no-output-artifacts"` |
| `test_activity_detail_output_artifact_navigates_to_detail` | Link href to `artifact_detail` (ART-FLOW-19) |
| `test_activity_detail_output_artifacts_log_story_happy` | caplog: view logs input and output counts |

Map to **ART-FLOW-16** and **ART-FLOW-19**.

---

## Section E — Log Story Script

| Where | Beat | Trigger | Must include |
|-------|------|---------|--------------|
| `activity_views.activity_detail` | entry | GET detail | user=, activity_pk= |
| `activity_views.activity_detail` | processing | inputs/outputs loaded | artifact input count=, output count= |
| `activity_views.activity_detail` | exit | render | activity=, can_edit= |

*(Existing log line at 384–386 already covers output count — extend assertion only.)*

---

## Section F — MCP Tools to Expose

**Not applicable** — UI-only fix; MCP `get_activity` already exposes `output_artifacts`.

---

## UI Design

Add card **below Input Artifacts** (before closing sidebar column):

```html
<!-- Output Artifacts Card -->
<div class="card" data-testid="output-artifacts-card">
  <div class="card-header">
    <h5><i class="fa-solid fa-box-open"></i> Output Artifacts
      {% if artifact_outputs %}<span class="badge">…</span>{% endif %}
    </h5>
  </div>
  <div class="card-body">
    {% for artifact in artifact_outputs %}
      <!-- link to artifact_detail, type badge, required badge -->
    {% endfor %}
    {% empty %} … no-output-artifacts … {% endfor %}
  </div>
</div>
```

Mirror Input Artifacts styling from lines 262–304 of `detail.html`. Use `fa-box-open` (consistent with `_embed.html`).

---

## Implementation Steps

### Slice 1 — RED: integration test

Add tests to `tests/integration/test_activity_view.py` (or new `test_activity_detail_artifacts.py`):

- Fixture: activity with 2 outputs via `Artifact.objects.create(produced_by=activity, …)`
- Assert section present before template exists → fail

### Slice 2 — GREEN: template

1. Add Output Artifacts card to `templates/activities/detail.html`.
2. Green behavior tests.

### Slice 3 — Log-story test

1. `test_activity_detail_output_artifacts_log_story_happy` with caplog.
2. Full pytest slice.

### Slice 4 — Docs

No feature file change needed (ART-FLOW-16 already written). Optional: note in `_implementation_notes` if act-6 has one.

---

## Commit Strategy

- `test(activities): assert output artifacts on activity detail` (#167)
- `feat(activities): add Output Artifacts card on activity detail` (#167)

---

## Success Criteria

- [ ] ART-FLOW-16 scenarios pass via pytest mapping
- [ ] Symmetry with Input Artifacts card (header, badge, list, empty state)
- [ ] Guest browse path unchanged (read-only, no edit button unless `can_edit`)
- [ ] Plan approved by user
