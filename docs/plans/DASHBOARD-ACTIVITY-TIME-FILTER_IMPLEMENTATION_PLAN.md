# Implementation Plan: Dashboard Recently Used Time-Window Filter (BPE-01)

**Feature**: FOB-DASHBOARD-09..13 — Recently Used time filter + window badge  
**Spec**: [`docs/features/act-0-auth/navigation.feature`](../features/act-0-auth/navigation.feature)  
**Confirmed**: Rename UI to **Recently Used**; badge shows count **in selected window**

---

## Section A — Context Map

| File | Change |
|------|--------|
| [`methodology/services/activity_service.py`](../../methodology/services/activity_service.py) | `get_recent_activities(user, limit, hours)` + `count_recent_activities_in_window` |
| [`methodology/views.py`](../../methodology/views.py) | Pass `hours` from dashboard + HTMX; `_parse_activity_feed_hours` |
| [`templates/methodology/partials/recent_activity_section.html`](../../templates/methodology/partials/recent_activity_section.html) | Title Recently Used, window badge |
| [`templates/methodology/partials/activity_feed_refresh.html`](../../templates/methodology/partials/activity_feed_refresh.html) | HTMX panel, dynamic label, refresh preserves hours |
| [`tests/unit/test_activity_service.py`](../../tests/unit/test_activity_service.py) | Hours filter + log story |
| [`tests/integration/test_dashboard_activity_feed.py`](../../tests/integration/test_dashboard_activity_feed.py) | HTMX + badge integration |

---

## Section B — Do-Not-Do

- No FOB-DASHBOARD-02 usage-count table in this slice
- No Playbook/Workflow feed rows
- No MCP / new models

---

## Section C — SAO

Activity Access Tracking; templates + HTMX + `data-testid`

---

## Section D — Tests

See cursor plan `dashboard_activity_time_filter_7687ce17.plan.md` Section D.

---

## Section E — Log Story

- `ActivityService.get_recent_activities`: entry (user_id, limit, hours), processing (cutoff, result_count)
- `dashboard_activities`: entry (user, hours)
- `dashboard`: processing (hours=24, activity_count_in_window)

---

## Section F — MCP

Not applicable.

---

## Commit slices

1. docs(features): scenarios + user journey + this plan  
2. test(dashboard): service hours filter RED  
3. feat(dashboard): service GREEN  
4. test(dashboard): integration RED  
5. feat(dashboard): views GREEN  
6. feat(ui): templates Recently Used + HTMX  
7. verify pytest green
