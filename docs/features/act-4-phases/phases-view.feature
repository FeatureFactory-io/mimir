Feature: FOB-PHASES-VIEW_PHASE-1 View Phase Details (OPTIONAL)
  As a methodology author (Maria)
  I want to view phase details
  So that I can understand its structure and activities

  Background:
    Given Maria is authenticated in FOB
    And she is viewing phase "Planning" in workflow "Component Development"
    And the phase has 3 activities

  Scenario: FOB-PHASES-VIEW_PHASE-01 Open phase detail page
    Given Maria is on phases list
    When she clicks [View] for "Planning"
    Then she is redirected to FOB-PHASES-VIEW_PHASE-1
    And she sees breadcrumb with workflow and phase name

  Scenario: FOB-PHASES-VIEW_PHASE-02 View phase header
    Given Maria is on the phase detail page
    Then she sees phase name "Planning"
    And she sees parent workflow badge
    And she sees order badge "#1 of 3"

  Scenario: FOB-PHASES-VIEW_PHASE-03 View activities in phase
    Given Maria is on the phase detail page
    Then she sees all 3 activities assigned to this phase
    And each activity shows name, description, and dependencies

  Scenario: FOB-PHASES-VIEW_PHASE-04 Edit phase button
    Given Maria is viewing the phase
    When she clicks [Edit Phase]
    Then she is redirected to FOB-PHASES-EDIT_PHASE-1

  Scenario: FOB-PHASES-VIEW_PHASE-05 Delete phase button
    Given Maria is viewing the phase
    When she clicks [Delete Phase]
    Then the FOB-PHASES-DELETE_PHASE-1 modal appears

  # ============================================================
  # GUEST ACCESS — anonymous read-only phase view (@guest_access)
  # ============================================================

  Scenario: FOB-PHASES-VIEW_PHASE-06 Guest views phase in public released playbook read-only
    Given Bob is not logged in
    And Mike owns a Public Released playbook "React Frontend Development"
    And the playbook has phase "Planning" in workflow "Component Development"
    When Bob GET the phase detail URL for "Planning"
    Then he sees phase name "Planning"
    And he sees phase description and order
    And he sees activities assigned to this phase
    And he does not see [Edit Phase] or [Delete Phase]

  Scenario: FOB-PHASES-VIEW_PHASE-07 Guest cannot view phase in private playbook
    Given Bob is not logged in
    And Mike owns a Private Released playbook with phase "Secret Phase"
    When Bob GET the phase detail URL for "Secret Phase"
    Then the response status is HTTP 404
