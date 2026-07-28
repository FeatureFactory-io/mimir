# {ProjectName} Information Architecture Guidelines

## Document Overview

This document defines the Information Architecture, Design System, and UI patterns for the {ProjectName} application. We rely heavily on **Bootstrap 5.3+** as our foundational framework, extending it with custom tokens and components where needed.

**Philosophy**: Leverage Bootstrap's conventions, utilities, and component patterns as the first choice. Customize only when necessary for brand identity or specific user experience requirements.

---

## Table of Contents

1. [Design System Foundation](#design-system-foundation)
2. [Skeleton & Layout](#skeleton--layout)
3. [Visual Design](#visual-design)
4. [Component Kit (Atomic Design)](#component-kit-atomic-design)
5. [Behavior & Interactions](#behavior--interactions)
6. [Flow & User Experience](#flow--user-experience)
7. [Data & State Patterns](#data--state-patterns)

---

## Design System Foundation

### 1. Design Tokens

We extend Bootstrap's native CSS variables with {ProjectName}-specific tokens. All tokens follow Bootstrap's naming convention for consistency.

#### Color Tokens

**Base Bootstrap Colors** (use as-is):
```css
/* Primary palette - Bootstrap defaults */
--bs-primary: {PrimaryColor};
--bs-secondary: {SecondaryColor};
--bs-success: #198754;
--bs-info: #0dcaf0;
--bs-warning: #ffc107;
--bs-danger: #dc3545;
--bs-light: #f8f9fa;
--bs-dark: #212529;

/* Grayscale */
--bs-gray-100: #f8f9fa;
--bs-gray-200: #e9ecef;
--bs-gray-300: #dee2e6;
--bs-gray-400: #ced4da;
--bs-gray-500: #adb5bd;
--bs-gray-600: #6c757d;
--bs-gray-700: #495057;
--bs-gray-800: #343a40;
--bs-gray-900: #212529;
```

**{ProjectName} Custom Colors**:
```css
/* Dashboard/feature-specific colors */
--{project}-color-1: {CustomColor1};
--{project}-color-2: {CustomColor2};
--{project}-color-3: {CustomColor3};

/* Background colors */
--{project}-bg-body: #f5f5f5;
--{project}-bg-surface: #ffffff;
--{project}-bg-elevated: #ffffff;
```

#### Spacing Tokens

**Use Bootstrap's spacing scale** (0.25rem increments):
```css
/* Bootstrap spacing multiplier: 1 = 0.25rem = 4px */
--bs-spacer: 1rem; /* 16px base */

/* Usage via utility classes */
.m-0  /* margin: 0 */
.m-1  /* margin: 0.25rem (4px) */
.m-2  /* margin: 0.5rem (8px) */
.m-3  /* margin: 1rem (16px) */
.m-4  /* margin: 1.5rem (24px) */
.m-5  /* margin: 3rem (48px) */
```

**{ProjectName} Custom Spacing**:
```css
/* Card spacing */
--{project}-card-padding: 1.25rem;
--{project}-card-gap: 1.5rem;

/* Section spacing */
--{project}-section-gap: 2rem;
--{project}-content-max-width: 1200px;
```

#### Typography Tokens

**Bootstrap Font Stack** (use as-is):
```css
--bs-font-sans-serif: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
--bs-font-monospace: SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace;

/* Font sizes - Bootstrap scale */
--bs-body-font-size: 1rem;
--bs-h1-font-size: 2.5rem;
--bs-h2-font-size: 2rem;
--bs-h3-font-size: 1.75rem;
--bs-h4-font-size: 1.5rem;
--bs-h5-font-size: 1.25rem;
--bs-h6-font-size: 1rem;
```

---

## Skeleton & Layout

### Navigation Structure

**Primary Navigation**:
- {NavigationItem1}
- {NavigationItem2}
- {NavigationItem3}
- {NavigationItem4}

**Navigation Pattern**: Bootstrap navbar with dropdown menus for entity groups.

```html
<nav class="navbar navbar-expand-lg navbar-dark bg-dark">
  <div class="container-fluid">
    <a class="navbar-brand" href="/">{ProjectName}</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navbarNav">
      <ul class="navbar-nav">
        <li class="nav-item"><a class="nav-link" href="/{entity1}/">{Entity1}</a></li>
        <li class="nav-item"><a class="nav-link" href="/{entity2}/">{Entity2}</a></li>
        <li class="nav-item"><a class="nav-link" href="/{entity3}/">{Entity3}</a></li>
      </ul>
    </div>
  </div>
</nav>
```

### Page Layout Pattern

**Standard Page Structure**:
```html
<div class="container-fluid">
  <!-- Page Header -->
  <div class="row mb-4">
    <div class="col">
      <h1>{PageTitle}</h1>
      <p class="text-muted">{PageDescription}</p>
    </div>
  </div>

  <!-- Main Content -->
  <div class="row">
    <div class="col-lg-12">
      {MainContent}
    </div>
  </div>
</div>
```

---

## Component Kit (Atomic Design)

### Atoms

#### Buttons

**Primary Actions**:
```html
<button class="btn btn-primary" data-bs-toggle="tooltip" title="{TooltipText}">
  <i class="fa-solid fa-{icon}"></i> {ButtonText}
</button>
```

**Secondary Actions**:
```html
<button class="btn btn-secondary" data-bs-toggle="tooltip" title="{TooltipText}">
  <i class="fa-solid fa-{icon}"></i> {ButtonText}
</button>
```

**Danger Actions**:
```html
<button class="btn btn-danger" data-bs-toggle="tooltip" title="{TooltipText}">
  <i class="fa-solid fa-{icon}"></i> {ButtonText}
</button>
```

#### Form Inputs

**Text Input**:
```html
<div class="mb-3">
  <label for="{fieldId}" class="form-label">{FieldLabel} <span class="text-danger">*</span></label>
  <input type="text" class="form-control" id="{fieldId}" name="{fieldName}" 
         placeholder="{PlaceholderText}" required data-testid="{entity}-{field}-input">
  <div class="invalid-feedback">{ErrorMessage}</div>
</div>
```

**Textarea**:
```html
<div class="mb-3">
  <label for="{fieldId}" class="form-label">{FieldLabel}</label>
  <textarea class="form-control" id="{fieldId}" name="{fieldName}" rows="4" 
            placeholder="{PlaceholderText}" data-testid="{entity}-{field}-textarea"></textarea>
</div>
```

**Select Dropdown**:
```html
<div class="mb-3">
  <label for="{fieldId}" class="form-label">{FieldLabel}</label>
  <select class="form-select" id="{fieldId}" name="{fieldName}" data-testid="{entity}-{field}-select">
    <option value="">{DefaultOption}</option>
    <option value="{value1}">{Option1}</option>
    <option value="{value2}">{Option2}</option>
  </select>
</div>
```

### Molecules

#### Card Component

```html
<div class="card shadow-sm" data-testid="{entity}-card">
  <div class="card-header">
    <h5 class="card-title mb-0">{CardTitle}</h5>
  </div>
  <div class="card-body">
    {CardContent}
  </div>
  <div class="card-footer">
    {CardActions}
  </div>
</div>
```

#### Table Component

```html
<div class="table-responsive">
  <table class="table table-hover" data-testid="{entity}-table">
    <thead>
      <tr>
        <th>{Column1}</th>
        <th>{Column2}</th>
        <th>{Column3}</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      <tr data-testid="{entity}-row">
        <td>{Value1}</td>
        <td>{Value2}</td>
        <td>{Value3}</td>
        <td>
          <div class="btn-group" role="group">
            <button class="btn btn-sm btn-outline-primary" data-testid="view-{entity}-button">
              <i class="fa-solid fa-eye"></i>
            </button>
            <button class="btn btn-sm btn-outline-secondary" data-testid="edit-{entity}-button">
              <i class="fa-solid fa-edit"></i>
            </button>
            <button class="btn btn-sm btn-outline-danger" data-testid="delete-{entity}-button">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

---

## Behavior & Interactions

### Toast Notifications

**Success**:
```html
<div class="toast align-items-center text-bg-success border-0" role="alert" data-testid="success-toast">
  <div class="d-flex">
    <div class="toast-body">
      <i class="fa-solid fa-check-circle me-2"></i> {SuccessMessage}
    </div>
    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
  </div>
</div>
```

**Error**:
```html
<div class="toast align-items-center text-bg-danger border-0" role="alert" data-testid="error-toast">
  <div class="d-flex">
    <div class="toast-body">
      <i class="fa-solid fa-exclamation-circle me-2"></i> {ErrorMessage}
    </div>
    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
  </div>
</div>
```

### Modal Dialogs

```html
<div class="modal fade" id="{modalId}" tabindex="-1" data-testid="{entity}-modal">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">{ModalTitle}</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        {ModalContent}
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-primary" data-testid="{action}-button">{ActionText}</button>
      </div>
    </div>
  </div>
</div>
```

---

## Icon System

**Font Awesome Pro** is used for all icons.

**Common Icons**:
- Create: `fa-plus`
- Edit: `fa-edit` or `fa-pen`
- Delete: `fa-trash`
- View: `fa-eye`
- Save: `fa-save` or `fa-floppy-disk`
- Cancel: `fa-times` or `fa-xmark`
- Search: `fa-search` or `fa-magnifying-glass`
- Filter: `fa-filter`
- Sort: `fa-sort`
- Download: `fa-download`
- Upload: `fa-upload`

---

## Placeholder Reference

- `{ProjectName}` - Name of the project
- `{PrimaryColor}` - Primary brand color (hex)
- `{SecondaryColor}` - Secondary brand color (hex)
- `{EntityName}` - Entity name (capitalized)
- `{entity}` - Entity name (lowercase)
- `{NavigationItem}` - Navigation menu item
- `{ComponentName}` - Component name
- `{TooltipText}` - Tooltip message
- `{FieldLabel}` - Form field label
- `{PlaceholderText}` - Input placeholder text
- `{ErrorMessage}` - Validation error message

