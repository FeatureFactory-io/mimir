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

Build functional prototypes with mocked data to validate UX before full implementation.

## Layout

Mockups live in a dedicated `mockups/` package at the repo root — separate from production code.

```
mockups/
  __init__.py          # package marker; demo/design reference only
  urls.py              # URL patterns for all mockup screens
  views.py             # views with hardcoded MOCK_* data fixtures
templates/mockups/
  {entity}/
    {operation}.html   # e.g. templates/mockups/pips/list.html
```

`mockups` is **not** in `INSTALLED_APPS` — it is a plain module included from `mimir/urls.py`.

---

## Gating — DEBUG only

Mockup routes are mounted only when `settings.DEBUG` is `True`.
In all other environments (test, production) they return 404.

```python
# mimir/urls.py
if settings.DEBUG:
    urlpatterns.append(path("mockups/", include("mockups.urls")))
```

This means mockups are automatically available with `runserver` (dev settings set `DEBUG=True`) and automatically disabled under pytest and production.

---

## Process

### 1. Add URL patterns

Register each screen in `mockups/urls.py`. URL names follow `mockup_{entity}_{operation}`:

```python
from django.urls import path
from . import views

urlpatterns = [
    path("{entity}/",          views.{entity}_list,   name="mockup_{entity}_list"),
    path("{entity}/create/",   views.{entity}_create, name="mockup_{entity}_create"),
    path("{entity}/<int:id>/", views.{entity}_detail, name="mockup_{entity}_detail"),
]
```

### 2. Create views with mock data

All mock data lives as module-level constants (`MOCK_*`). Views have no DB access and no auth checks.

```python
import logging
from django.shortcuts import render

logger = logging.getLogger(__name__)

MOCK_ITEMS = [...]  # hardcoded list of dicts

def {entity}_list(request):
    """FOB-{ENTITY}-LIST+FIND-1: description."""
    logger.info("Mockup: {entity}_list | user=%s", getattr(request.user, "username", "anonymous"))
    context = {"items": MOCK_ITEMS, "item_count": len(MOCK_ITEMS)}
    return render(request, "mockups/{entity}/list.html", context)
```

### 3. Create templates

**File location**: `templates/mockups/{entity}/{operation}.html`

Required elements in every mockup template:

```html
{% extends "base.html" %}
{% load static %}

{% block title %}{Entity} — Mockup{% endblock %}

{% block content %}
<div class="container mt-4" data-testid="{entity}-{operation}-page">

    <!-- ... screen content ... -->

    <!-- Mockup nav — cross-links to related screens -->
    <div class="alert alert-light border mt-4 small">
        <strong>Mockup screens:</strong>
        <a href="{% url 'mockup_{entity}_list' %}">List</a> ·
        <a href="{% url 'mockup_{entity}_create' %}">Create</a> ·
        <a href="{% url 'mockup_{entity}_detail' id=1 %}">Detail</a>
    </div>

</div>

<script>
// Client-side flow simulation — log decisions, actions, results
document.addEventListener('DOMContentLoaded', function () {
    console.log('[mockup:{entity}-{operation}] page loaded');
    // Log user interactions inline, e.g.:
    // console.log('[mockup:{entity}-{operation}] submit clicked, field=' + value);
});
</script>
{% endblock %}
```

Additional conventions:
- Bootstrap 5.3+ components throughout
- Font Awesome Pro icons on all buttons
- Bootstrap tooltips on all interactive elements
- `data-testid` attributes on all interactive elements
- Represent all UI states: loading, empty, error, success
- Semantic HTML (`nav`, `main`, `section`), ARIA labels, keyboard navigation

### 4. Add accessibility

- Semantic HTML structure
- ARIA labels and roles on interactive elements
- Keyboard navigation support
- Focus management for modals and alerts

---

## Deliverables

- ✅ `mockups/urls.py` — URL patterns for all CRUDLF screens, names as `mockup_{entity}_{operation}`
- ✅ `mockups/views.py` — mock data constants + view functions with INFO-level logging
- ✅ Templates at `templates/mockups/{entity}/{operation}.html`
- ✅ Each template has `data-testid="{entity}-{operation}-page"` on the root container
- ✅ Each template has a **Mockup nav** block with cross-links to all related mockup screens
- ✅ Each template has `console.log('[mockup:{entity}-{operation}]')` calls at key interaction points
- ✅ All UI states represented (empty, loaded, error, success)
- ✅ Accessibility attributes (ARIA, semantic HTML, keyboard nav)
- ✅ Mockups accessible at `/mockups/{entity}/` when `DEBUG=True`; return 404 otherwise

---

## Inputs

Read these before starting this activity. They are produced earlier in the playbook and are authoritative — raise a drift event instead of deviating.

- **User Journey** (Document, Required) — produced by Define User Journey (#36).
- **IA Guidelines** (Document, Required) — produced by Define Information Architecture (#37).
- **Screen Flow / Dialogue Map** (Diagram, Required) — produced by Create Dialogue Maps (#38).

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
