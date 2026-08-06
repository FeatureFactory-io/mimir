Feature: FOB-ARTIFACTS-VIEW_ARTIFACT-1 View Artifact Details
  As a methodology author (Maria)
  I want to view artifact details
  So that I can understand deliverable requirements

  Background:
    Given Maria is authenticated in FOB
    And she is viewing artifact "Component Design Document"
    And the artifact belongs to playbook "React Frontend v1.2"

  Scenario: FOB-ARTIFACTS-VIEW_ARTIFACT-01 Open artifact detail page
    Given Maria is on artifacts list
    When she clicks [View] for "Component Design Document"
    Then she is redirected to FOB-ARTIFACTS-VIEW_ARTIFACT-1
    And she sees breadcrumb with playbook and artifact name

  Scenario: FOB-ARTIFACTS-VIEW_ARTIFACT-02 View artifact header
    Given Maria is on the artifact detail page
    Then she sees artifact name "Component Design Document"
    And she sees artifact type badge "Document"
    And she sees required status badge

  Scenario: FOB-ARTIFACTS-VIEW_ARTIFACT-03 View artifact description
    Given Maria is on the artifact detail page
    Then she sees the full description
    And she sees creation and modification timestamps

  Scenario: FOB-ARTIFACTS-VIEW_ARTIFACT-04 View associated activities
    Given the artifact is linked to 2 activities
    Then she sees "Used in Activities" section
    And she sees list of activities using this artifact
    And each activity link is clickable

  Scenario: FOB-ARTIFACTS-VIEW_ARTIFACT-05 View template file
    Given the artifact has an attached template
    Then she sees "Template" section
    And she can [Download Template] file

  Scenario: FOB-ARTIFACTS-VIEW_ARTIFACT-06 Edit artifact button
    Given Maria is viewing the artifact
    When she clicks [Edit Artifact]
    Then she is redirected to FOB-ARTIFACTS-EDIT_ARTIFACT-1

  Scenario: FOB-ARTIFACTS-VIEW_ARTIFACT-07 Delete artifact button
    Given Maria is viewing the artifact
    When she clicks [Delete Artifact]
    Then the FOB-ARTIFACTS-DELETE_ARTIFACT-1 modal appears

  Scenario: FOB-ARTIFACTS-VIEW_ARTIFACT-13 Owner views artifact in released playbook read-only with PIP path
    Given Maria owns a Released playbook with artifact "Bug Report"
    When Maria views the artifact detail page
    Then she does not see [Edit Artifact]
    And she sees [Submit PIP] linking to PIP create with playbook and producer activity context
  # ============================================================
  # ARTIFACT FLOW - See artifacts-flow.feature for complete flow scenarios
  # ============================================================

  Scenario: FOB-ARTIFACTS-VIEW_ARTIFACT-11 View artifact producer activity
    Given the artifact is produced by activity "Design Component API"
    When Maria views the artifact detail page
    Then she sees "Produced by" section
    And she sees "Design Component API" with clickable link
    And clicking the link navigates to activity detail page

  Scenario: FOB-ARTIFACTS-VIEW_ARTIFACT-12 View artifact consumer activities
    Given the artifact is consumed by 3 activities
    When Maria views the artifact detail page
    Then she sees "Consumed by" section
    And she sees list of 3 consumer activities
    And each shows whether it's required or optional input
    And each activity link is clickable

  # ============================================================
  # GUEST ACCESS — anonymous read-only artifact view (@guest_access)
  # ============================================================

  Scenario: FOB-ARTIFACTS-VIEW_ARTIFACT-08 Guest views artifact in public released playbook read-only
    Given Bob is not logged in
    And Mike owns a Public Released playbook "React Frontend Development"
    And an activity in that playbook links artifact "Component Design Document"
    When Bob GET the artifact detail URL for "Component Design Document"
    Then he sees artifact name "Component Design Document"
    And he sees artifact type and template information read-only
    And he does not see [Edit Artifact] or [Delete Artifact]

  Scenario: FOB-ARTIFACTS-VIEW_ARTIFACT-09 Guest cannot view artifact in private playbook
    Given Bob is not logged in
    And Mike owns a Private Released playbook with artifact "Secret Artifact"
    When Bob GET the artifact detail URL for "Secret Artifact"
    Then the response status is HTTP 404

  Scenario: FOB-ARTIFACTS-VIEW_ARTIFACT-10 Guest views artifact embed without login redirect
    Given Bob is not logged in
    And Mike owns a Public Released playbook "React Frontend Development"
    And an activity in that playbook links artifact "Component Design Document"
    When Bob GET "/artifacts/<pk>/?embed=1" for "Component Design Document"
    Then the response status is HTTP 200
    And the embed content loads without navbar or mutation buttons
    And Bob is not redirected to the login page
