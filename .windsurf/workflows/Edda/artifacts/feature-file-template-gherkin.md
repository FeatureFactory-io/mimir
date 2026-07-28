Feature: {ScreenID} {EntityName} {Operation}
  As a {PersonaRole} ({PersonaName})
  I want to {UserGoal}
  So that {BusinessValue}

  Background:
    Given {PersonaName} is authenticated in {SystemName}
    And {InitialContext}

  Scenario: {ScenarioID} {ScenarioTitle}
    Given {GivenContext}
      | {Column1} | {Column2} | {Column3} | {Column4} |
      | {Value1}  | {Value2}  | {Value3}  | {Value4}  |
      | {Value5}  | {Value6}  | {Value7}  | {Value8}  |
    When {WhenAction}
    Then {ThenOutcome}
    And {AdditionalOutcome}

  Scenario: {ScenarioID} {ScenarioTitle} - Happy Path
    Given {PersonaName} is on the {ScreenName} page
    And {Precondition}
    When {PersonaName} clicks the [{ButtonName}] button
    Then {PersonaName} is redirected to {TargetScreenID}
    And {PersonaName} sees {ExpectedResult}

  Scenario: {ScenarioID} {ScenarioTitle} - Search Functionality
    Given {PersonaName} is on the {ScreenName} page
    And {PersonaName} has {EntityName} including "{ExampleName}"
    When {PersonaName} enters "{SearchTerm}" in the search box
    Then {PersonaName} sees only {EntityName} matching "{SearchTerm}" in {SearchFields}
    And "{ExampleName}" appears in the results
    And unmatched {EntityName} are hidden

  Scenario: {ScenarioID} {ScenarioTitle} - Search with No Results
    Given {PersonaName} is on the {ScreenName} page
    When {PersonaName} enters "{NonExistentTerm}" in the search box
    Then {PersonaName} sees "No {EntityName} found matching '{NonExistentTerm}'"
    And {PersonaName} sees a [Clear Search] button
    And the {EntityName} table is empty

  Scenario: {ScenarioID} {ScenarioTitle} - Filter by Status
    Given {PersonaName} is on the {ScreenName} page
    And {PersonaName} has both {Status1} and {Status2} {EntityName}
    When {PersonaName} selects "{Status1}" from the Status filter
    Then {PersonaName} sees only {Status1} {EntityName}
    And {Status2} {EntityName} are hidden
    And the filter badge shows "Status: {Status1}"

  Scenario Outline: {ScenarioID} {ScenarioTitle} - Filter by Category
    Given {PersonaName} is on the {ScreenName} page
    And {PersonaName} has {EntityName} from different categories
    When {PersonaName} selects "<category>" from the Category filter
    Then {PersonaName} sees only "<category>" {EntityName}
    And the filter badge shows "Category: <category>"

    Examples:
      | category   |
      | {Category1} |
      | {Category2} |
      | {Category3} |

  Scenario: {ScenarioID} {ScenarioTitle} - Clear All Filters
    Given {PersonaName} is on the {ScreenName} page
    And {PersonaName} has applied Status filter "{Status1}"
    And {PersonaName} has applied Category filter "{Category1}"
    When {PersonaName} clicks [Clear Filters]
    Then all filters are removed
    And {PersonaName} sees all {EntityName} regardless of status or category
    And no filter badges are displayed

  Scenario: {ScenarioID} {ScenarioTitle} - Sort by Column
    Given {PersonaName} is on the {ScreenName} page
    And {PersonaName} has multiple {EntityName}
    When {PersonaName} clicks the "{ColumnName}" column header
    Then {EntityName} are sorted by {ColumnName} (ascending)
    When {PersonaName} clicks the "{ColumnName}" column header again
    Then {EntityName} are sorted by {ColumnName} (descending)
    And a sort indicator appears on the "{ColumnName}" column

  Scenario: {ScenarioID} {ScenarioTitle} - Navigate to View Details
    Given {PersonaName} is on the {ScreenName} page
    And "{ExampleName}" is in the list
    When {PersonaName} clicks [View] in the Actions menu for "{ExampleName}"
    Then {PersonaName} is redirected to {ViewScreenID}
    And {PersonaName} sees the detail page for "{ExampleName}"

  Scenario: {ScenarioID} {ScenarioTitle} - Navigate to Edit
    Given {PersonaName} is on the {ScreenName} page
    And "{ExampleName}" is in the list
    And {PersonaName} is the author of "{ExampleName}"
    When {PersonaName} clicks [Edit] in the Actions menu for "{ExampleName}"
    Then {PersonaName} is redirected to {EditScreenID}
    And {PersonaName} sees the edit form pre-populated with {EntityName} data

  Scenario: {ScenarioID} {ScenarioTitle} - Open Delete Confirmation
    Given {PersonaName} is on the {ScreenName} page
    And "{ExampleName}" is in the list
    When {PersonaName} clicks [Delete] in the Actions menu for "{ExampleName}"
    Then the {DeleteScreenID} modal appears
    And the modal shows "Delete {EntityName}?"
    And the modal shows {EntityName} details for "{ExampleName}"

  Scenario: {ScenarioID} {ScenarioTitle} - Empty State Display
    Given {PersonaName} is on the {ScreenName} page
    And {PersonaName} has zero {EntityName}
    Then {PersonaName} sees an empty {IllustrationName} illustration
    And {PersonaName} sees "No {EntityName} yet"
    And {PersonaName} sees "{EmptyStateMessage}"
    And {PersonaName} sees action buttons:
      | button        |
      | {Action1}     |
      | {Action2}     |
      | {Action3}     |

  Scenario: {ScenarioID} {ScenarioTitle} - Pagination
    Given {PersonaName} is on the {ScreenName} page
    And {PersonaName} has {TotalCount} {EntityName}
    When the page loads
    Then {PersonaName} sees the first {PageSize} {EntityName}
    And {PersonaName} sees pagination controls at the bottom
    And the controls show "Page 1 of {TotalPages}"
    When {PersonaName} clicks "Next Page"
    Then {PersonaName} sees {EntityName} {NextRangeStart}-{NextRangeEnd}
    And the controls show "Page 2 of {TotalPages}"

  Scenario: {ScenarioID} {ScenarioTitle} - Combine Search and Filter
    Given {PersonaName} is on the {ScreenName} page
    And {PersonaName} has multiple {EntityName}
    When {PersonaName} enters "{SearchTerm}" in the search box
    And {PersonaName} selects "{Status1}" from the Status filter
    Then {PersonaName} sees only {Status1} {EntityName} with "{SearchTerm}" in {SearchFields}
    And both search term and filter badge are displayed
    And results match both criteria

  Scenario: {ScenarioID} {ScenarioTitle} - Form Validation Error
    Given {PersonaName} is on the {CreateScreenID} page
    When {PersonaName} leaves "{RequiredField}" empty
    And {PersonaName} clicks [Save]
    Then {PersonaName} sees error message "{ErrorMessage}" below "{RequiredField}"
    And the [Save] button remains disabled
    And the form is not submitted

  Scenario: {ScenarioID} {ScenarioTitle} - Create Success
    Given {PersonaName} is on the {CreateScreenID} page
    When {PersonaName} fills in:
      | field         | value        |
      | {Field1}      | {Value1}     |
      | {Field2}      | {Value2}     |
      | {Field3}      | {Value3}     |
    And {PersonaName} clicks [Save]
    Then {PersonaName} sees green toast "{EntityName} '{Value1}' created successfully"
    And {PersonaName} is redirected to {ViewScreenID}
    And the new {EntityName} appears in the list

  Scenario: {ScenarioID} {ScenarioTitle} - Edit Success
    Given {PersonaName} is on the {EditScreenID} page for "{ExampleName}"
    And the form is pre-populated with current values
    When {PersonaName} changes "{Field1}" to "{NewValue}"
    And {PersonaName} clicks [Save Changes]
    Then {PersonaName} sees green toast "{EntityName} updated successfully"
    And {PersonaName} is redirected to {ViewScreenID}
    And the updated value "{NewValue}" is displayed

  Scenario: {ScenarioID} {ScenarioTitle} - Delete Success
    Given {PersonaName} is on the {DeleteScreenID} modal for "{ExampleName}"
    When {PersonaName} clicks [Delete]
    Then {PersonaName} sees green toast "{EntityName} deleted successfully"
    And {PersonaName} is redirected to {ListScreenID}
    And "{ExampleName}" is removed from the table

  Scenario: {ScenarioID} {ScenarioTitle} - Delete with Dependencies Warning
    Given {PersonaName} is on the {DeleteScreenID} modal for "{ExampleName}"
    And "{ExampleName}" has {DependencyCount} related {DependencyEntity}
    Then the modal shows warning "This will also delete {DependencyCount} related {DependencyEntity}"
    When {PersonaName} clicks [Delete]
    Then both {EntityName} and related {DependencyEntity} are deleted

# ============================================================
# PLACEHOLDER REFERENCE
# ============================================================
# {ScreenID} - Unique screen identifier (e.g., FOB-PLAYBOOKS-LIST+FIND-1)
# {EntityName} - Entity name capitalized (e.g., Playbook, Workflow)
# {Operation} - CRUD operation (List and Search, Create, View, Edit, Delete)
# {PersonaRole} - User role (e.g., methodology author, developer)
# {PersonaName} - User persona name (e.g., Maria, Mike)
# {UserGoal} - What the user wants to accomplish
# {BusinessValue} - Why this matters to the user
# {SystemName} - System name (e.g., FOB, HB)
# {ScenarioID} - Unique scenario identifier
# {ScenarioTitle} - Descriptive scenario title
# {GivenContext} - Initial state/precondition
# {WhenAction} - User action
# {ThenOutcome} - Expected result
# {ScreenName} - Human-readable screen name
# {ButtonName} - Button label
# {TargetScreenID} - Destination screen ID
# {ExpectedResult} - What user should see
# {SearchTerm} - Search query
# {SearchFields} - Fields to search in
# {Status1}, {Status2} - Status values
# {Category1}, {Category2}, {Category3} - Category values
# {ColumnName} - Table column name
# {ViewScreenID}, {EditScreenID}, {DeleteScreenID}, {CreateScreenID}, {ListScreenID} - Screen IDs
# {ExampleName} - Example entity name
# {IllustrationName} - Empty state illustration name
# {EmptyStateMessage} - Empty state message
# {Action1}, {Action2}, {Action3} - Action button labels
# {TotalCount} - Total number of items
# {PageSize} - Items per page
# {TotalPages} - Total number of pages
# {NextRangeStart}, {NextRangeEnd} - Pagination range
# {RequiredField} - Required form field name
# {ErrorMessage} - Validation error message
# {Field1}, {Field2}, {Field3} - Form field names
# {Value1}, {Value2}, {Value3} - Form field values
# {NewValue} - Updated value
# {DependencyCount} - Number of dependent items
# {DependencyEntity} - Type of dependent entity

