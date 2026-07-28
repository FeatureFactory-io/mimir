# Skill: Bootstrap 5-based Design System for Django & HTMX

**Capability Domain**: FRONTEND_FRAMEWORK  
**Technology Stack**: Bootstrap 5.3+ · Django 5 · HTMX

## Overview

Reference implementation for ESM-03 "Define Information Architecture" when the stack is Bootstrap 5 + Django + HTMX. Covers all 9 sections of the IA outline — the original 4 (tokens, layouts, navigation, components) and the 5 added by this PIP (page header, CRUDLF templates, button placement, feedback system, component states).

Use this skill as a starting point. Copy the patterns that fit your project and adjust tokens, column splits, and colour semantics to match your design decisions.

---

## 1. Design Tokens (Bootstrap 5 Extension Pattern)

Extend Bootstrap's CSS variables rather than overriding them. Prefix Mimir/project-specific tokens with `--{project}-`.

```css
/* base.css */
:root {
  /* Project palette — extend Bootstrap, never shadow it */
  --project-bg-body:    #f5f5f5;
  --project-bg-surface: #ffffff;

  /* Card chrome */
  --project-card-shadow:       0 2px 4px rgba(0,0,0,.08);
  --project-card-shadow-hover: 0 4px 12px rgba(0,0,0,.15);
  --project-card-radius:       0.5rem;

  /* Stat-card accent colours */
  --project-purple: #5856d6;
  --project-blue:   #38a9f0;
  --project-orange: #ffa726;
  --project-red:    #ef5350;
}

[data-bs-theme="dark"] {
  --project-bg-body:    #1a1a1a;
  --project-bg-surface: #2d2d2d;
  --project-purple: #7c7aec;
  --project-blue:   #64c3ff;
  --project-orange: #ffb74d;
  --project-red:    #f77673;
}
```

**Naming rule**: `--{namespace}-{element}-{property}[-{modifier}]`. Use semantic names (`--project-bg-surface`) not literal values (`--project-white`).

---

## 2. Layout Patterns

### 2-Column (main + metadata sidebar)
```html
<div class="container-fluid">
  <div class="row">
    <main class="col-lg-9"><!-- primary content --></main>
    <aside class="col-lg-3 bg-light p-3"><!-- metadata only — never navigation --></aside>
  </div>
</div>
```

### 3-Column (filters + content + metadata)
```html
<div class="container-fluid">
  <div class="row">
    <aside class="col-lg-2"><!-- filters / quick actions --></aside>
    <main class="col-lg-8"><!-- content --></main>
    <aside class="col-lg-2"><!-- metadata / related info --></aside>
  </div>
</div>
```

### Grid (dashboard cards)
```html
<div class="row g-3 mb-4">
  <div class="col-12 col-sm-6 col-lg-3"><!-- stat card --></div>
  <!-- repeat 4 times -->
</div>
```

---

## 3. Navigation Design

```html
<nav class="navbar navbar-expand-lg bg-white shadow-sm sticky-top">
  <div class="container-fluid">
    <a class="navbar-brand" href="/">Brand</a>
    <div class="collapse navbar-collapse">
      <ul class="navbar-nav me-auto">
        <li class="nav-item">
          {# active state: exact match for single-page sections #}
          <a class="nav-link {% if request.path == '/dashboard/' %}active{% endif %}"
             href="/dashboard/"
             {% if request.path == '/dashboard/' %}aria-current="page"{% endif %}
             data-bs-toggle="tooltip" title="Dashboard">
            <i class="fa-solid fa-gauge"></i> Dashboard
          </a>
        </li>
        <li class="nav-item">
          {# active state: contains check for multi-page sections #}
          <a class="nav-link {% if '/playbooks/' in request.path %}active{% endif %}"
             href="/playbooks/"
             {% if '/playbooks/' in request.path %}aria-current="page"{% endif %}
             data-bs-toggle="tooltip" title="Playbooks">
            <i class="fa-solid fa-book-sparkles"></i> Playbooks
          </a>
        </li>
      </ul>
      <ul class="navbar-nav ms-auto">
        <!-- dark-mode toggle, notification badges, user dropdown -->
      </ul>
    </div>
  </div>
</nav>
```

**Breadcrumbs**:
```html
<nav aria-label="breadcrumb">
  <ol class="breadcrumb">
    <li class="breadcrumb-item"><a href="/">Home</a></li>
    <li class="breadcrumb-item"><a href="/playbooks/">Playbooks</a></li>
    <li class="breadcrumb-item active" aria-current="page">React Frontend</li>
  </ol>
</nav>
```

---

## 4. Component Patterns (Atomic Design)

### Button atom
```html
<!-- icon before text (default) -->
<button class="btn btn-primary" data-bs-toggle="tooltip" title="Save changes">
  <i class="fa-solid fa-save me-2"></i>Save
</button>

<!-- icon-only (must have tooltip) -->
<button class="btn btn-outline-secondary" data-bs-toggle="tooltip" title="Edit">
  <i class="fa-solid fa-pen-to-square"></i>
</button>
```

### Empty state
```html
<div class="text-center py-5">
  <i class="fa-light fa-inbox fa-4x text-muted mb-3"></i>
  <h5>No items yet</h5>
  <p class="text-muted">Get started by creating your first item.</p>
  <button class="btn btn-primary mt-2">
    <i class="fa-solid fa-plus me-2"></i>Create
  </button>
</div>
```

---

## 5. Page Header Pattern

Every non-dashboard page uses a consistent two-row header immediately after the breadcrumb.

```html
{# Row 1: breadcrumb (see section 3) #}

{# Row 2: title + action cluster #}
<div class="d-flex justify-content-between align-items-center mb-4">
  <div>
    <h1 class="h3 mb-0">{{ page_title }}</h1>
    {# Detail pages only: metadata sub-row #}
    <div class="text-muted small mt-1">v{{ object.version }} &middot; Updated {{ object.updated_at|timesince }} ago</div>
  </div>
  {# Action cluster — see Section 7 for placement rules #}
  <div class="d-flex gap-2 flex-wrap">
    {% block page_actions %}{% endblock %}
  </div>
</div>
```

**Rules**:
- List and View pages: action cluster in `{% block page_actions %}`
- The sub-row (version / timestamp) is only shown on View and Edit pages
- On mobile, action cluster wraps below the title (`flex-wrap`)

---

## 6. Baseline CRUDLF Page Templates

### List+Find (FOB-{ENTITY}-LIST+FIND)
```html
{% extends "base.html" %}
{% block content %}
<div class="container-fluid p-4">
  {# breadcrumb #}
  {# page header with "Create" primary action #}
  <div class="d-flex justify-content-between align-items-center mb-4">
    <h1 class="h3 mb-0">{{ entity_plural }}</h1>
    <a href="{% url 'entity-create' %}" class="btn btn-primary">
      <i class="fa-solid fa-plus me-2"></i>Create
    </a>
  </div>

  {# search / filter bar #}
  <div class="d-flex gap-2 mb-3">
    <div class="input-group" style="max-width:360px;">
      <span class="input-group-text"><i class="fa-solid fa-magnifying-glass"></i></span>
      <input type="text" class="form-control" placeholder="Search..." name="q" value="{{ request.GET.q }}">
    </div>
  </div>

  {# table or empty state #}
  {% if object_list %}
  <div class="table-responsive">
    <table class="table table-hover align-middle">
      <thead>
        <tr>
          <th>Name</th>
          <th>Status</th>
          <th>Last Updated</th>
          <th class="text-end">Actions</th>
        </tr>
      </thead>
      <tbody>
        {% for item in object_list %}
        <tr>
          <td><a href="{{ item.get_absolute_url }}">{{ item.name }}</a></td>
          <td><span class="badge bg-success">{{ item.status }}</span></td>
          <td>{{ item.updated_at|timesince }} ago</td>
          <td class="text-end">
            <a href="{% url 'entity-edit' item.pk %}" class="btn btn-sm btn-outline-primary"
               data-bs-toggle="tooltip" title="Edit">
              <i class="fa-solid fa-pen-to-square"></i>
            </a>
            <button class="btn btn-sm btn-outline-danger" data-bs-toggle="modal"
                    data-bs-target="#deleteModal" data-id="{{ item.pk }}"
                    data-bs-toggle2="tooltip" title="Delete">
              <i class="fa-solid fa-trash"></i>
            </button>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% else %}
  {# empty state — see Section 4 #}
  {% endif %}
</div>
{% endblock %}
```

### View (FOB-{ENTITY}-VIEW)
```html
<div class="container-fluid p-4">
  <div class="row">
    <main class="col-lg-9">
      {# breadcrumb #}
      {# page header with Edit + Back actions #}
      <div class="tab-content">{# tabs for content sections #}</div>
    </main>
    <aside class="col-lg-3 bg-light p-3">
      <h6 class="text-uppercase text-muted small mb-3">Details</h6>
      {# version, author, timestamps, tags — metadata only #}
    </aside>
  </div>
</div>
```

### Edit (FOB-{ENTITY}-EDIT)
```html
<form method="post">
  {% csrf_token %}
  <div class="row">
    <div class="col-md-8">
      {# primary fields #}
    </div>
    <div class="col-md-4">
      <div class="card">
        <div class="card-header">Settings</div>
        <div class="card-body">{# visibility, flags, secondary fields #}</div>
      </div>
    </div>
  </div>
  {# form footer — see Section 7 for button order #}
  <div class="d-flex justify-content-end gap-2 mt-4">
    <a href="{{ cancel_url }}" class="btn btn-outline-secondary">Cancel</a>
    <button type="submit" class="btn btn-primary">
      <i class="fa-solid fa-save me-2"></i>Save
    </button>
  </div>
</form>
```

### Delete — confirmation modal (no dedicated page)
```html
<div class="modal fade" id="deleteModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Delete {{ entity_name }}?</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <p>Are you sure you want to delete <strong id="deleteItemName"></strong>?</p>
        <div class="alert alert-warning">
          <i class="fa-solid fa-triangle-exclamation me-2"></i>This action cannot be undone.
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
        <form id="deleteForm" method="post">
          {% csrf_token %}
          <button type="submit" class="btn btn-danger">
            <i class="fa-solid fa-trash me-2"></i>Delete
          </button>
        </form>
      </div>
    </div>
  </div>
</div>
```

---

## 7. Button Placement Rules

**Universal rules**:
- Primary action is always **rightmost** in its cluster.
- Destructive action (Delete) is always **leftmost** in its cluster — never adjacent to the primary.
- Use `d-flex justify-content-end gap-2 flex-wrap` for all action clusters.

| Context | Corner | Left → Right order |
|---|---|---|
| List / View page header | Top-right | Secondary actions … Primary |
| Create / Edit form footer | Bottom-right | Cancel → Save draft → Submit |
| Detail page with destructive action | Top-right | Delete … Secondary … Back |
| Modal footer | Bottom-right | Cancel → Confirm |

```html
{# List / View header #}
<div class="d-flex justify-content-end gap-2 flex-wrap">
  <button class="btn btn-outline-secondary">Export</button>
  <a href="{% url 'entity-create' %}" class="btn btn-primary">
    <i class="fa-solid fa-plus me-2"></i>Create
  </a>
</div>

{# Form footer #}
<div class="d-flex justify-content-end gap-2 flex-wrap mt-4">
  <a href="{{ cancel_url }}" class="btn btn-outline-secondary">Cancel</a>
  <button type="submit" name="action" value="draft" class="btn btn-outline-primary">Save draft</button>
  <button type="submit" class="btn btn-primary">Submit</button>
</div>

{# Detail page with Delete #}
<div class="d-flex justify-content-end gap-2 flex-wrap">
  <button class="btn btn-outline-danger" data-bs-toggle="modal" data-bs-target="#deleteModal">Delete</button>
  <a href="{% url 'entity-edit' object.pk %}" class="btn btn-outline-primary">Edit</a>
  <a href="{{ back_url }}" class="btn btn-secondary">Back</a>
</div>
```

---

## 8. Feedback / Notification System

### Toast container (in base.html)
```html
<div class="toast-container position-fixed top-0 end-0 p-3" style="z-index:1090;">
  {# toasts injected here by showToast() or Django message rendering #}
</div>
```

### Toast variants
```html
{# success — auto-dismiss 5 s #}
<div class="toast align-items-center text-bg-success border-0" role="alert">
  <div class="d-flex">
    <div class="toast-body"><i class="fa-solid fa-circle-check me-2"></i>{{ message }}</div>
    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
  </div>
</div>

{# error — manual dismiss only #}
<div class="toast align-items-center text-bg-danger border-0" role="alert">
  <div class="d-flex">
    <div class="toast-body"><i class="fa-solid fa-circle-exclamation me-2"></i>{{ message }}</div>
    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
  </div>
</div>
```

Same pattern for `text-bg-warning` (info icon) and `text-bg-info` (info icon), both auto-dismiss 5 s.

**Dismissal rules**:
- `success` + `info` + `warning`: `autohide: true, delay: 5000`
- `error` / `danger`: `autohide: false` — user must dismiss manually

### showToast() JS helper
```javascript
function showToast(message, type = 'success') {
  const container = document.querySelector('.toast-container');
  const icons = { success: 'fa-circle-check', error: 'fa-circle-exclamation',
                  warning: 'fa-triangle-exclamation', info: 'fa-circle-info' };
  const bg    = { success: 'text-bg-success', error: 'text-bg-danger',
                  warning: 'text-bg-warning', info: 'text-bg-info' };
  const autohide = type !== 'error';

  container.insertAdjacentHTML('beforeend', `
    <div class="toast align-items-center ${bg[type]} border-0" role="alert">
      <div class="d-flex">
        <div class="toast-body"><i class="fa-solid ${icons[type]} me-2"></i>${message}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    </div>`);

  const el = container.lastElementChild;
  const t  = new bootstrap.Toast(el, { autohide, delay: 5000 });
  t.show();
  el.addEventListener('hidden.bs.toast', () => el.remove());
}
```

### Django view → HTMX integration
```python
# In Django view — set headers so HTMX can read them
response['X-Toast']      = 'Playbook saved successfully!'
response['X-Toast-Type'] = 'success'   # success | error | warning | info
```

```javascript
// In base.html — read headers after any HTMX request
document.addEventListener('htmx:afterRequest', function (evt) {
  const msg  = evt.detail.xhr.getResponseHeader('X-Toast');
  const type = evt.detail.xhr.getResponseHeader('X-Toast-Type') || 'success';
  if (msg) showToast(msg, type);
});
```

### Field validation — always inline, never a toast
```html
<div class="mb-3">
  <label for="name" class="form-label">Name <span class="text-danger">*</span></label>
  <input type="text" class="form-control is-invalid" id="name" value="{{ form_data.name }}">
  <div class="invalid-feedback">
    <i class="fa-solid fa-circle-exclamation me-1"></i>{{ errors.name }}
  </div>
</div>
```

---

## 9. Component State Catalogue

Document these 6 states for every interactive component. Minimum required: Button, Input, Card, Nav link.

### Button states
```css
.btn-primary              { /* default */ }
.btn-primary:hover        { transform: translateY(-1px); box-shadow: 0 4px 8px rgba(0,0,0,.15); }
.btn-primary:focus        { box-shadow: 0 0 0 .25rem rgba(13,110,253,.5); }
.btn-primary:active       { transform: translateY(0); }
.btn-primary:disabled,
.btn-primary[disabled]    { opacity: .65; cursor: not-allowed; pointer-events: none; }
/* Loading: replace label with spinner, keep disabled */
```
```html
{# Loading state #}
<button class="btn btn-primary" disabled>
  <span class="spinner-border spinner-border-sm me-2"></span>Saving...
</button>
```

### Input states
```css
.form-control             { /* default */ }
.form-control:focus       { border-color: var(--bs-primary); box-shadow: 0 0 0 .25rem rgba(13,110,253,.25); }
.form-control.is-valid    { border-color: var(--bs-success); }
.form-control.is-invalid  { border-color: var(--bs-danger); }
.form-control:disabled    { background: var(--bs-gray-200); cursor: not-allowed; }
```

### Card states
```css
.card                     { box-shadow: var(--project-card-shadow); transition: box-shadow .2s ease, transform .2s ease; }
.card:hover               { box-shadow: var(--project-card-shadow-hover); transform: translateY(-2px); }
.card:focus-within        { outline: 2px solid var(--bs-primary); outline-offset: 2px; }
.card.selected            { border: 2px solid var(--bs-primary); background: rgba(13,110,253,.04); }
/* Disabled: opacity .5, pointer-events none */
/* Loading: replace body content with skeleton shimmer */
```

### Skeleton shimmer (loading state for cards)
```css
.skeleton {
  background: linear-gradient(90deg, var(--bs-gray-200) 25%, var(--bs-gray-100) 50%, var(--bs-gray-200) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: .25rem;
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
.skeleton-title { height: 1.5rem; width: 40%; }
.skeleton-text  { height: 1rem;   width: 100%; }
```

### Nav link states
```css
.nav-link           { color: var(--bs-gray-700); transition: all .15s ease; }
.nav-link:hover     { color: var(--bs-primary); background: var(--bs-gray-100); border-radius: .375rem; }
.nav-link:focus     { outline: 2px solid var(--bs-primary); outline-offset: 2px; }
.nav-link.active    { color: var(--bs-primary); font-weight: 600; }
.nav-link.disabled  { color: var(--bs-gray-400); pointer-events: none; cursor: default; }
```

---

## Quick-Start Checklist

Before building any screen against this design system:

- [ ] Tokens defined and CSS variables declared in `base.css`
- [ ] Dark-mode overrides set under `[data-bs-theme="dark"]`
- [ ] `showToast()` helper and `htmx:afterRequest` listener in `base.html`
- [ ] Toast container `div` present in `base.html`
- [ ] Page header template block wired in base template
- [ ] CRUDLF skeletons available as Django template fragments
- [ ] All buttons have tooltips (`data-bs-toggle="tooltip"`)
- [ ] All interactive elements have `data-testid` attributes
- [ ] Component states verified in both light and dark mode
