# Activity: Create Mockups

**Activity ID**: 40
**Order**: 6
**Phase**: Inception
**Dependencies**: Predecessor: Activity 39 (Write Feature Files)

## Description

Create Mockups

## Guidance

# Create Mockups (Prototyped Screens)

## Objective

Build functional prototypes with representative mock data to validate UX before full implementation. Mockups are design reference — not connected to live data or production runtime.

## Layout

Mockups live in a dedicated `mockups/` package at the repo root, separate from production apps.

```
mockups/
  urls.py              # URL patterns for all mockup screens (canonical inventory)
  views.py             # views with hardcoded fixture data
  templates/mockups/
    base.html          # shared shell — banner and screen inventory
```

The package is included from the project URLconf. It is not a production feature surface.

## Gating — DEBUG only

Mockup routes are mounted only when `settings.DEBUG` is true. In test and production they are not mounted and return 404.

```python
if settings.DEBUG:
    urlpatterns.append(path("mockups/", include("mockups.urls")))
```

`runserver` with development settings (`DEBUG=True`) serves them at `/mockups/`. Pytest and production settings (`DEBUG=False`) do not.

## Mockup chrome (required on every screen)

Every mockup inherits a single shared shell. Do not duplicate mockup chrome inside individual screens.

Two signals are always present (except the full-bleed exception below):

### 1. Persistent mockup banner

A fixed banner at the top of the viewport states that the screen is design reference only and is not connected to live data.

- Defined once in the shared shell.
- Never removed or hidden on individual mockup screens.
- Production chrome (nav, page header) sits below it.

### 2. Shared screen inventory

A single footer (or equivalent persistent index) lists every registered mockup screen. This is the canonical cross-link index for designers, reviewers, and agents jumping between prototypes.

Rules:

| Rule | Detail |
|---|---|
| **Single source** | Maintain inventory links in the shared shell only — never add a second per-page inventory block. |
| **Keep in sync** | When you add a mockup screen, add its inventory link in the same change. |
| **Page-specific hints** | Optional suffix text (reset notes, store keys, and similar) attaches to the shared inventory. Do not fork the inventory. |
| **Test hook** | The inventory root has a stable test id so agents and AT can find it. |

Representative detail/edit screens that are reachable from list rows do not need inventory links unless they are primary entry points.

**Full-bleed exception:** A screen whose layout needs the full viewport height may hide the inventory. The banner stays visible.

## Process

### 1. Register every screen

Every prototype in the Screen Flow is a registered mockup under `mockups/urls.py`, served at `/mockups/`. The inventory in the shared shell is the canonical list — keep it in lockstep with registrations.

### 2. Use representative mock data

Mock data is hardcoded fixtures. Mockup screens have no live datastore access and no production auth checks. Cover the states the IA requires: loading, empty, error, success.

### 3. Build screens from the shared shell

Each screen extends the shared mockup shell (inherits banner + inventory).

- Follow the IA Guidelines for layout, page headers, components, and test-id naming.
- Visible title and subtitle use production copy — no Screen IDs and no “mockup” or storage jargon in the page header.
- Screen traceability lives in metadata (screen-id slot → comment in the shell; test ids on containers and controls).
- Mockup signaling is **only** the banner and the shared inventory. Interactive prototypes may append reset hints on the inventory, never in the page header.
- Represent UI states; use semantic HTML, ARIA labels, and keyboard navigation.

### 4. Accessibility

- Semantic structure (`nav`, `main`, `section`)
- ARIA labels and roles on interactive elements
- Keyboard navigation
- Focus management for modals and alerts

## Deliverables

- ✅ Shared mockup shell with persistent banner and single screen inventory
- ✅ Every Screen Flow prototype registered and linked from that inventory (no per-page duplicate inventories)
- ✅ Representative mock data; no live datastore; no production auth
- ✅ Production-real page headers; Screen IDs only in metadata / test ids
- ✅ All required UI states (empty, loaded, error, success)
- ✅ Accessibility (ARIA, semantic HTML, keyboard nav)
- ✅ Mockups accessible at `/mockups/` when `DEBUG=True`; not mounted and 404 otherwise

## Inputs

Read these before starting this activity. They are produced earlier in the playbook and are authoritative — raise a drift event instead of deviating.

- **User Journey** (Document, Required) — produced by Define User Journey (#36).
- **IA Guidelines** (Document, Required) — produced by Define Information Architecture (#37).
- **Screen Flow / Dialogue Map** (Diagram, Required) — produced by Create Dialogue Maps (#38).

---

## Responsive Visual Validation

The Responsive Coverage Contract in `docs/ux/IA_guidelines.md` is authoritative.

Render and visually inspect every registered mockup at every required target viewport. Use the same CSS-pixel profile names and dimensions defined by the IA. A single responsive mockup may satisfy multiple profiles; separate mockup implementations are not required.

For each Screen ID and viewport, verify:

- page shell, navigation, breadcrumbs, title, metadata, and action clusters follow the mapped recipe;
- columns stack in the documented order and reading/focus order stays coherent;
- text, controls, menus, tooltips, modals, feedback, tables, rails, canvases, and split panes do not clip or overlap;
- no unintended page-level horizontal scrollbar appears; intentional table/component overflow remains local;
- primary navigation and primary actions remain reachable;
- low-height profiles preserve deliberate scrolling or the documented full-viewport fit;
- content remains readable without browser zoom and interactive targets remain usable by touch and keyboard.

Record a responsive evidence index containing Screen ID, recipe, viewport profile, result, screenshot/reference, reviewer, and any approved exception. Fix failures before completing ESM-06. An exception is valid only when it is documented in the IA and represented by a focused feature scenario.

## Agent

None

## Skill

**Title**: Django + HTMX Frontend Implementation Patterns
**Capability Domain**: FRONTEND_FRAMEWORK
**Technology Stack**: Django+HTMX+Graphviz

## Rules

- **Diagrams Element By Element** (`do-diagrams-element-by-element`)
- **Look Via Human Eye** (`do-look-via-human-eye`)
- **View Drawio Diagrams** (`do-view-drawio-diagrams`)

## Artifacts Produced

- **HTML Mockups** (Code) - Required
- **HTML Mockups Template** (Template) - Optional

## Artifacts Consumed

- **User Journey** (Document) - Required
- **IA Guidelines** (Document) - Required
- **Screen Flow / Dialogue Map** (Diagram) - Required

## Notes

No additional notes.
