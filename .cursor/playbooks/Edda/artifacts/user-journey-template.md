# {ProjectName} User Journey

## Personas

**{PersonaName}** - {PersonaRole}  
{PersonaDescription}

**{PersonaName2}** - {PersonaRole2}  
{PersonaDescription2}

---

## System Architecture Note

**{SystemName}**: {SystemDescription}
- **Component 1**: {ComponentDescription}
- **Component 2**: {ComponentDescription}

**Domain Model Notes**:
- **Core Entities**: {EntityList}
- **Key Relationships**: {RelationshipDescription}

---

## ⚠️ Critical Architectural Principle

**{PrincipleName}**

{PrincipleDescription}

**Example**:
- {ExampleScenario}

**This separation ensures**:
- {Benefit1}
- {Benefit2}
- {Benefit3}

---

## Journey: {JourneyTitle}

### Act {ActNumber}: {ActTitle}

**Context**: {ActContext}

**Pattern**: {Entity} follows the standard CRUDLF pattern with LIST+FIND as the entry point.

#### Screen: {ScreenID}

{PersonaName} {ActionDescription}. The {ScreenName} appears:

**Layout**:
- **Header**: "{EntityName}" with count badge (e.g., "{EntityName} (3)")
- **Top Actions**:
  - [Create New {EntityName}] button (primary action, bold blue)
  - [Additional Action] button
- **Search & Filter Section**:
  - Search box: "Find {entity}..." (searches {fields})
  - Filters: {Filter1}, {Filter2}, {Filter3}
  - [Clear Filters] button
- **{EntityName} Table** with columns:
  - {Column1} | {Column2} | {Column3} | Actions
  - Sort by any column
- **Row Actions** (dropdown menu per {entity}):
  - [View] - Opens {ScreenID}-VIEW_{ENTITY}
  - [Edit] - Opens {ScreenID}-EDIT_{ENTITY}
  - [Delete] - Opens {ScreenID}-DELETE_{ENTITY} modal
  - [...More] - Additional actions
- **Empty State** (if no {entity}):
  - Illustration: {IllustrationDescription}
  - "No {entity} yet"
  - "{CallToActionMessage}"
  - [Action Buttons]
- **Pagination**: Shows 20 per page with page controls

**Example Data**:
- "{ExampleRow1}" | {Data} | {Data} | {Status}
- "{ExampleRow2}" | {Data} | {Data} | {Status}

{PersonaName} sees {UserObservation}.

---

### Act {ActNumber}: {ActTitle} - CREATE_{ENTITY}

#### Screen: {ScreenID}

{PersonaName} clicks [Create New {EntityName}]. The create form appears:

**Form Fields**:
- **{FieldName}** (required, text input)
  - Placeholder: "{ExampleValue}"
  - Validation: {ValidationRule}
- **{FieldName2}** (optional, dropdown)
  - Options: {Option1}, {Option2}, {Option3}
- **{FieldName3}** (required, textarea)
  - Placeholder: "{ExampleValue}"
  - Max length: {MaxLength} characters

**Actions**:
- [Save] button (primary, blue) - Creates {entity} and redirects to VIEW
- [Cancel] button (secondary, gray) - Returns to LIST without saving

**Validation**:
- Required fields marked with asterisk (*)
- Real-time validation on blur
- Error messages appear below fields in red
- Save button disabled until all required fields valid

{PersonaName} fills in the form and clicks [Save].

**Success**:
- Green toast: "{EntityName} '{Name}' created successfully"
- Redirects to {ScreenID}-VIEW_{ENTITY}

**Error**:
- Red toast: "Failed to create {entity}: {ErrorMessage}"
- Form remains open with error details

---

### Act {ActNumber}: {ActTitle} - VIEW_{ENTITY}

#### Screen: {ScreenID}

{PersonaName} views {entity} details:

**Layout**:
- **Header**: {EntityName} name with status badge
- **Metadata Section**:
  - Created: {Date} by {Author}
  - Last modified: {Date} by {Editor}
  - Status: {StatusBadge}
- **Details Section**:
  - {Field1}: {Value1}
  - {Field2}: {Value2}
  - {Field3}: {Value3}
- **Related Items** (if applicable):
  - {RelatedEntity1} ({Count})
  - {RelatedEntity2} ({Count})
- **Actions**:
  - [Edit] button - Opens EDIT_{ENTITY}
  - [Delete] button - Opens DELETE_{ENTITY} modal
  - [Additional Action] button

---

### Act {ActNumber}: {ActTitle} - EDIT_{ENTITY}

#### Screen: {ScreenID}

{PersonaName} clicks [Edit]. The edit form appears with current values pre-filled:

**Form Fields**: (Same as CREATE form but pre-populated)

**Actions**:
- [Save Changes] button (primary, blue)
- [Cancel] button (secondary, gray)

{PersonaName} modifies fields and clicks [Save Changes].

**Success**:
- Green toast: "{EntityName} updated successfully"
- Returns to VIEW_{ENTITY}

---

### Act {ActNumber}: {ActTitle} - DELETE_{ENTITY}

#### Screen: {ScreenID} (Modal)

{PersonaName} clicks [Delete]. A confirmation modal appears:

**Modal Content**:
- **Title**: "Delete {EntityName}?"
- **Message**: "Are you sure you want to delete '{Name}'? This action cannot be undone."
- **Warning** (if applicable): "This will also delete {RelatedCount} related {RelatedEntity}."
- **Actions**:
  - [Delete] button (danger, red)
  - [Cancel] button (secondary, gray)

{PersonaName} clicks [Delete].

**Success**:
- Green toast: "{EntityName} deleted successfully"
- Redirects to LIST+FIND
- {Entity} removed from table

**Error**:
- Red toast: "Failed to delete {entity}: {ErrorMessage}"
- Modal closes, returns to VIEW

---

## Navigation Flow Summary

```
LIST+FIND → CREATE → VIEW
         ↓         ↓
       FILTER    EDIT → VIEW
         ↓         ↓
       SEARCH   DELETE → LIST
```

## Screen ID Conventions

- **LIST+FIND**: `{PROJECT}-{ENTITY}-LIST+FIND-{VERSION}`
- **CREATE**: `{PROJECT}-{ENTITY}-CREATE_{ENTITY}-{VERSION}`
- **VIEW**: `{PROJECT}-{ENTITY}-VIEW_{ENTITY}-{VERSION}`
- **EDIT**: `{PROJECT}-{ENTITY}-EDIT_{ENTITY}-{VERSION}`
- **DELETE**: `{PROJECT}-{ENTITY}-DELETE_{ENTITY}-{VERSION}`

## Placeholder Reference

- `{ProjectName}` - Name of the project
- `{PersonaName}` - User persona name
- `{PersonaRole}` - User persona role/title
- `{EntityName}` - Name of the entity (singular, capitalized)
- `{entity}` - Name of the entity (singular, lowercase)
- `{ScreenID}` - Unique screen identifier
- `{ActNumber}` - Act number (0-15)
- `{ActTitle}` - Title of the act
- `{FieldName}` - Form field name
- `{ValidationRule}` - Validation rule description

