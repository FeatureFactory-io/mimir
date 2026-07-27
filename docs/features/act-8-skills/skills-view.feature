Feature: FOB-SKILLS-VIEW_SKILL-1 View Skill Details
  As a methodology author (Maria)
  I want to view skill details including capability and tech stack metadata
  So that I can understand what technology guidance is available and which activities use it

  Status: ✅ DONE - GUI CRUD implemented
  Branch: feature/skill-capability-metadata (merged to main)
  Related: act-13-mcp/interact-with-skills-via-mcp

  Background:
    Given Maria is authenticated in FOB
    And she is viewing skill "React Form Component" in playbook "React Frontend v1.2"
    And the skill has capability_domain "GUI_FORM" and technology_stack "React+Redux"

  Scenario: FOB-SKILLS-VIEW_SKILL-01 Open skill detail page
    Given Maria is on FOB-SKILLS-LIST+FIND-1
    When she clicks [View] for "React Form Component"
    Then she is redirected to FOB-SKILLS-VIEW_SKILL-1
    And she sees breadcrumb: Playbooks > React Frontend v1.2 > Skills > React Form Component

  Scenario: FOB-SKILLS-VIEW_SKILL-02 View skill header with metadata
    Given Maria is on the skill detail page
    Then she sees skill title "React Form Component"
    And she sees Capability Domain badge "GUI_FORM"
    And she sees Technology Stack badge "React+Redux"
    And she sees parent playbook badge "React Frontend v1.2"

  Scenario: FOB-SKILLS-VIEW_SKILL-03 View skill content
    Given Maria is on the skill detail page
    Then she sees the formatted Markdown content
    And formatting is preserved (headings, bold, italic, lists, code blocks)

  Scenario: FOB-SKILLS-VIEW_SKILL-04 View activities referencing this skill
    Given 3 activities reference this skill
    Then she sees "Referenced by Activities (3)" section
    And she sees a list of activity names with their workflow context
    And each activity link navigates to FOB-ACTIVITIES-VIEW_ACTIVITY-1

  Scenario: FOB-SKILLS-VIEW_SKILL-05 Edit skill button
    Given Maria is viewing the skill
    When she clicks [Edit Skill]
    Then she is redirected to FOB-SKILLS-EDIT_SKILL-1

  Scenario: FOB-SKILLS-VIEW_SKILL-06 Delete skill button
    Given Maria is viewing the skill
    When she clicks [Delete Skill]
    Then the FOB-SKILLS-DELETE_SKILL-1 modal appears

  # ============================================================
  # GUEST ACCESS — anonymous read-only skill view (@guest_access)
  # ============================================================

  Scenario: FOB-SKILLS-VIEW_SKILL-07 Guest views skill in public released playbook read-only
    Given Bob is not logged in
    And Mike owns a Public Released playbook "React Frontend Development"
    And the playbook has skill "React Form Component"
    When Bob GET the skill detail URL for "React Form Component"
    Then he sees skill title "React Form Component"
    And he sees capability domain and technology stack badges
    And he sees formatted Markdown content
    And he does not see [Edit Skill] or [Delete Skill]

  Scenario: FOB-SKILLS-VIEW_SKILL-08 Guest cannot view skill in private playbook
    Given Bob is not logged in
    And Mike owns a Private Released playbook with skill "Secret Skill"
    When Bob GET the skill detail URL for "Secret Skill"
    Then the response status is HTTP 404

  Scenario: FOB-SKILLS-VIEW_SKILL-09 Guest views skill embed without login redirect
    Given Bob is not logged in
    And Mike owns a Public Released playbook "React Frontend Development"
    And the playbook has skill "React Form Component"
    When Bob GET the skill embed URL with "?embed=1"
    Then the response status is HTTP 200
    And the embed content loads without navbar or mutation buttons
    And Bob is not redirected to the login page
