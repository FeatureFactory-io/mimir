# Activity: Define Information Architecture

**Activity ID**: 37
**Order**: 3
**Phase**: Inception
**Dependencies**: Predecessor: Activity 36 (Define User Journey)

## Description

Define Information Architecture

## Guidance

# Define Information Architecture

## Objective

Establish the design system foundation, layout patterns, and component standards.

## Artifacts Created

- `docs/ux/IA_guidelines.md` - Information architecture and design system

## Process

### 1. Define Information Architecture

- Document design system foundation (Bootstrap 5.3+ base)
- Define design tokens (colors, spacing, typography, shadows, borders)
- Establish layout patterns (2-column, 3-column, grid, forms)
- Define navigation structure (top navbar, breadcrumbs, tabs)
- Document component patterns (cards, buttons, forms, modals)
- Specify accessibility requirements
- Define icon system (Font Awesome Pro)

**Philosophy**: Leverage Bootstrap's conventions, utilities, and component patterns as the first choice. Customize only when necessary for brand identity or specific user experience requirements.

### Key Sections to Document

#### 1. Design Tokens
- Color palette (primary, secondary, custom colors)
- Spacing scale (Bootstrap multipliers)
- Typography (font stacks, sizes, weights)
- Shadows and borders

#### 2. Layout Patterns
- Dashboard grids
- Form layouts
- List/table views
- Detail pages

#### 3. Navigation Design
- Top navigation structure
- Breadcrumbs
- Tab navigation
- Active states and ARIA attributes

#### 4. Component Patterns
- Cards
- Buttons (with Font Awesome icons and tooltips)
- Forms and inputs
- Modals and dialogs
- Tables
- Empty states

#### 5. Page Header Pattern
Document the canonical structure for every non-dashboard page: breadcrumb row, title + action cluster row, and (for detail pages) a metadata sub-row. Specify which information belongs in each row, how the action cluster is composed, and how it adapts between list, view, and edit contexts.

#### 6. Baseline CRUDLF Page Templates
Document the skeleton layout for each standard screen operation: List+Find, View, Edit, and Delete. For each, specify the column split, which organisms compose the main area, what the sidebar (if any) may contain, and whether the operation uses a full page or a modal.

#### 7. Button Placement Rules
Document as a decision table: for each context (list page header, form footer, detail page with destructive action, modal footer) — which corner holds the action cluster, and what is the left-to-right order of buttons within it. State the universal rules that apply across all contexts (e.g. primary always rightmost; destructive always leftmost in its cluster).

#### 8. Feedback / Notification System
Document the chosen mechanism for each feedback type: success, error, warning, info, and field validation. For each, specify the UI component used, its positioning, dismissal strategy (auto-dismiss with timing vs. manual), and how backend operations surface feedback to the frontend (e.g. response headers, HTMX events, Django messages framework).

#### 9. Component State Catalogue
For every interactive component, document all states: default, hover, focus, active, disabled, and loading. List the minimum set of components that must be covered. Specify the visual treatment (CSS class, style change, or animation) for each state and note any accessibility requirements (e.g. visible focus ring, aria-disabled).

## How to Execute This Step

### 1. Plan Before Executing
- Identify all design system components needed
- Reference existing Bootstrap documentation
- Note Mimir-specific customizations
- Show plan and get approval

### 2. Work Incrementally
- Document one section at a time
- After every section: write → review → refine
- Build incrementally: tokens → layouts → navigation → components → page patterns → CRUDLF templates → button rules → feedback → states

## Deliverables

- ✅ IA guidelines with design system specifications
- ✅ **Screen ID convention documented**: Format, CRUDLF operations, examples
- ✅ Navigation structure defined
- ✅ Layout patterns documented
- ✅ Component patterns with accessibility requirements
- ✅ Icon system (Font Awesome Pro) documented
- ✅ Bootstrap customization approach clear
- ✅ Page header pattern documented (breadcrumb / title + action cluster / metadata sub-row)
- ✅ Baseline CRUDLF templates documented (List+Find, View, Edit, Delete)
- ✅ Button placement rules table documented
- ✅ Feedback system documented (mechanism and dismissal strategy per feedback type)
- ✅ Component state catalogue documented (all states for all required components)

## Agent

None

## Skill

**Title**: Bootstrap 5-based Design System for Django & HTMX

## Rules

- **Diagrams Element By Element** (`do-diagrams-element-by-element`)
- **Look Via Human Eye** (`do-look-via-human-eye`)
- **View Drawio Diagrams** (`do-view-drawio-diagrams`)

## Artifacts Produced

- **IA Guidelines** (Document) - Required
- **IA Guidelines Template** (Template) - Required

## Artifacts Consumed

None

## Notes

No additional notes.
