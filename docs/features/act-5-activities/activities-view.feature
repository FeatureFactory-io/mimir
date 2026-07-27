Feature: FOB-ACTIVITIES-VIEW_ACTIVITY-1 View Activity Details
  As a methodology author (Maria)
  I want to view activity details
  So that I can understand work tasks completely

  Background:
    Given Maria is authenticated in FOB
    And she is viewing activity "Setup component structure"
    And the activity belongs to workflow "Component Development"

  Scenario: FOB-ACTIVITIES-VIEW_ACTIVITY-01 Open activity detail page
    Given Maria is on activities list
    When she clicks [View] for "Setup component structure"
    Then she is redirected to FOB-ACTIVITIES-VIEW_ACTIVITY-1
    And she sees breadcrumb with workflow and activity name

  Scenario: FOB-ACTIVITIES-VIEW_ACTIVITY-02 View activity header
    Given Maria is on the activity detail page
    Then she sees activity name "Setup component structure"
    And she sees parent workflow badge
    And she sees phase badge (if assigned)
    And she sees order badge

  Scenario: FOB-ACTIVITIES-VIEW_ACTIVITY-03 View activity description
    Given Maria is on the activity detail page
    Then she sees the full description
    And she sees creation and modification timestamps

  Scenario: FOB-ACTIVITIES-VIEW_ACTIVITY-04 View dependencies
    Given the activity has 2 dependencies
    Then she sees "Dependencies" section
    And she sees list of prerequisite activities
    And each dependency is clickable to view its details

  Scenario: FOB-ACTIVITIES-VIEW_ACTIVITY-05 View input artifacts
    Given the activity has 3 input artifacts
    Then she sees "Input Artifacts" card
    And the card shows count badge "3"
    And each artifact shows: Name, Type, Required status, Producer
    And each artifact is clickable to view details

  Scenario: FOB-ACTIVITIES-VIEW_ACTIVITY-06 View assigned agent
    Given the activity has assigned agent "Code Reviewer"
    Then she sees "Assigned Agent" card
    And the card shows agent name with link to detail
    And the card shows truncated agent description
    And she sees "Change Agent" button if she can edit

  Scenario: FOB-ACTIVITIES-VIEW_ACTIVITY-07 View required skill
    Given the activity has required skill "React Development"
    Then she sees "Required Skill" card
    And the card shows skill title with link to detail
    And the card shows capability domain and technology stack badges
    And she sees "Change Skill" button if she can edit

  Scenario: FOB-ACTIVITIES-VIEW_ACTIVITY-07b View linked rules
    Given the activity links playbook rules "pytest-first" and "no-mocks"
    Then she sees "Rules" card
    And each rule title links to rule detail

  Scenario: FOB-ACTIVITIES-VIEW_ACTIVITY-08 Edit activity button
    Given Maria is viewing the activity
    When she clicks [Edit Activity]
    Then she is redirected to FOB-ACTIVITIES-EDIT_ACTIVITY-1

  Scenario: FOB-ACTIVITIES-VIEW_ACTIVITY-09 Delete activity button
    Given Maria is viewing the activity
    When she clicks [Delete Activity]
    Then the FOB-ACTIVITIES-DELETE_ACTIVITY-1 modal appears

  # ============================================================
  # GUEST ACCESS — anonymous read-only activity view (@guest_access)
  # ============================================================

  Scenario: FOB-ACTIVITIES-VIEW_ACTIVITY-10 Guest views activity in public released playbook read-only
    Given Bob is not logged in
    And Mike owns a Public Released playbook "React Frontend Development"
    And the playbook has activity "Setup component structure"
    When Bob GET the activity detail URL for "Setup component structure"
    Then he sees activity name "Setup component structure"
    And he sees rendered guidance markdown
    And he sees dependencies and input/output artifacts
    And he does not see [Edit Activity], [Delete Activity], [Change Agent], or [Change Skill]

  Scenario: FOB-ACTIVITIES-VIEW_ACTIVITY-11 Guest cannot view activity in private playbook
    Given Bob is not logged in
    And Mike owns a Private Released playbook with activity "Secret Activity"
    When Bob GET the activity detail URL for "Secret Activity"
    Then the response status is HTTP 404

  Scenario: FOB-ACTIVITIES-VIEW_ACTIVITY-12 Guest views activity embed without login redirect
    Given Bob is not logged in
    And Mike owns a Public Released playbook "React Frontend Development"
    And the playbook has activity "Setup component structure"
    When Bob GET the activity embed URL with "?embed=1"
    Then the response status is HTTP 200
    And the embed HTML shows activity content without navbar or breadcrumbs
    And Bob is not redirected to the login page
