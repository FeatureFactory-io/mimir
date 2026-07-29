@copy_prompt
Feature: FOB-COPY-PROMPT-LIST-1 Copy Prompt in list-row Actions
  As a methodology author (Maria)
  I want [Copy Prompt] beside [View] in table Actions columns
  So that I can copy entity context from a list without opening the detail page

  # List row: icon-only btn-outline-secondary in btn-group-sm beside View (eye).
  # data-testid: copy-prompt-btn-<entity_type>-<pk>
  # Clipboard payload must match the same entity's VIEW page (see copy-prompt-view.feature).

  Background:
    Given Maria is authenticated in FOB
    And Mike owns playbook "React Frontend Development" (Public Released v1.2)

  Scenario: FOB-COPY-PROMPT-LIST-01 Workflow-scoped activities list row Actions
    Given Maria is on FOB-ACTIVITIES-LIST+FIND-1
    Then row "Setup component structure" includes data-testid "copy-prompt-btn-activity-<pk>"
    When she clicks [Copy Prompt] on that row without opening detail
    Then the clipboard receives the same text as FOB-COPY-PROMPT-SERVICE-01

  Scenario: FOB-COPY-PROMPT-LIST-02 Playbook-scoped activities list row Actions
    Given Maria is on the playbook activities list for "React Frontend Development"
    Then each activity row includes data-testid "copy-prompt-btn-activity-<pk>"

  Scenario: FOB-COPY-PROMPT-LIST-03 Global activities list row Actions
    Given Maria is on "/activities/"
    Then each visible activity row includes data-testid "copy-prompt-btn-activity-<pk>"

  Scenario: FOB-COPY-PROMPT-LIST-04 Playbook-scoped skills list row Actions
    Given Maria is on FOB-SKILLS-LIST+FIND-1 for "React Frontend Development"
    Then each skill row includes data-testid "copy-prompt-btn-skill-<pk>"

  Scenario: FOB-COPY-PROMPT-LIST-05 Global skills list row Actions
    Given Maria is on "/skills/"
    Then each visible skill row includes data-testid "copy-prompt-btn-skill-<pk>"

  Scenario: FOB-COPY-PROMPT-LIST-06 Playbook-scoped agents list row Actions
    Given Maria is on the agents list for "React Frontend Development"
    Then each agent row includes data-testid "copy-prompt-btn-agent-<pk>"

  Scenario: FOB-COPY-PROMPT-LIST-07 Global agents list row Actions
    Given Maria is on "/agents/"
    Then each visible agent row includes data-testid "copy-prompt-btn-agent-<pk>"

  Scenario: FOB-COPY-PROMPT-LIST-08 Global rules list row Actions
    Given Maria is on "/rules/"
    Then each visible rule row includes data-testid "copy-prompt-btn-rule-<pk>"

  Scenario: FOB-COPY-PROMPT-LIST-09 Playbook-scoped rules list row Actions
    Given Maria is on the playbook rules list for "React Frontend Development"
    Then each rule row includes data-testid "copy-prompt-btn-rule-<pk>"

  Scenario: FOB-COPY-PROMPT-LIST-10 Playbook-scoped artifacts list row Actions
    Given Maria is on the artifacts list for "React Frontend Development"
    Then each artifact row includes data-testid "copy-prompt-btn-artifact-<pk>"

  Scenario: FOB-COPY-PROMPT-LIST-11 Global artifacts list row Actions
    Given Maria is on "/artifacts/"
    Then each visible artifact row includes data-testid "copy-prompt-btn-artifact-<pk>"

  Scenario: FOB-COPY-PROMPT-LIST-12 Playbook-scoped workflows list row Actions
    Given Maria is on FOB-WORKFLOWS-LIST+FIND-1
    Then each workflow row includes data-testid "copy-prompt-btn-workflow-<pk>"

  Scenario: FOB-COPY-PROMPT-LIST-13 Global workflows list row Actions
    Given Maria is on "/workflows/"
    Then each visible workflow row includes data-testid "copy-prompt-btn-workflow-<pk>"

  Scenario: FOB-COPY-PROMPT-LIST-14 Playbook-scoped phases list row Actions
    Given Maria is on FOB-PHASES-LIST+FIND-1
    Then each phase row includes data-testid "copy-prompt-btn-phase-<pk>"

  Scenario: FOB-COPY-PROMPT-LIST-15 Global phases list row Actions
    Given Maria is on "/phases/"
    Then each visible phase row includes data-testid "copy-prompt-btn-phase-<pk>"

  Scenario: FOB-COPY-PROMPT-LIST-16 PIP list row Actions beside View
    Given Maria is on FOB-PIP-LIST-1
    Then PIP-42 row Actions includes data-testid "copy-prompt-btn-pip-42"
    And [Copy Prompt] sits beside the View (eye) button in the same btn-group

  Scenario: FOB-COPY-PROMPT-LIST-17 Playbook Workflows tab nested table Actions
    Given Maria is on FOB-PLAYBOOKS-VIEW_PLAYBOOK-1 Workflows tab
    Then each row in data-testid "workflows-table" includes copy-prompt-btn-workflow-<pk>

  Scenario: FOB-COPY-PROMPT-LIST-18 Phase detail nested activities table Actions
    Given Maria is on FOB-PHASES-VIEW_PHASE-1 with assigned activities
    Then each activity row in the phase activities table includes copy-prompt-btn-activity-<pk>

  Scenario: FOB-COPY-PROMPT-LIST-19 List copy matches detail copy for the same entity
    Given activity "Setup component structure" exists
    When Maria copies from the global activities list row
    And Maria copies from FOB-ACTIVITIES-VIEW_ACTIVITY-1 header
    Then both clipboard payloads are identical
