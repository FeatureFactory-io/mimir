Feature: FOB-AGENTS-VIEW_AGENT-1 View Agent Details
  As a methodology author (Maria)
  I want to view agent details
  So that I can understand agent capabilities and guidelines

  Status: ✅ DONE - GUI CRUD implemented
  Branch: feature/skill-capability-metadata (merged to main)
  Related: act-13-mcp/interact-with-agents-via-mcp

  Background:
    Given Maria is authenticated in FOB
    And she is viewing agent "Cautious Developer (drdobbs-v2)"
    And the agent belongs to playbook "React Frontend v1.2"

  Scenario: AGENT-VIEW-01 Open agent detail page
    Given Maria is on agents list
    When she clicks [View] for "Cautious Developer (drdobbs-v2)"
    Then she is redirected to FOB-AGENTS-VIEW_AGENT-1
    And she sees breadcrumb with playbook and agent name

  Scenario: AGENT-VIEW-02 View agent header
    Given Maria is on the agent detail page
    Then she sees agent name "Cautious Developer (drdobbs-v2)"
    And she sees parent playbook badge

  Scenario: AGENT-VIEW-03 View agent description
    Given Maria is on the agent detail page
    Then she sees the full description
    And she sees creation and modification timestamps

  Scenario: AGENT-VIEW-04 View activities using this agent
    Given the agent is assigned to 5 activities
    Then she sees "Used in Activities" section
    And she sees list of activities with this agent
    And each activity link is clickable

  Scenario: AGENT-VIEW-05 Edit agent button
    Given Maria is viewing the agent
    When she clicks [Edit Agent]
    Then she is redirected to FOB-AGENTS-EDIT_AGENT-1

  Scenario: AGENT-VIEW-06 Delete agent button
    Given Maria is viewing the agent
    When she clicks [Delete Agent]
    Then the FOB-AGENTS-DELETE_AGENT-1 modal appears

  Scenario: AGENT-VIEW-09 Owner on released playbook cannot mutate agents via web
    Given Maria owns a Released playbook with agent "Cautious Developer (drdobbs-v2)"
    When Maria views the agent detail page
    Then she does not see [Edit Agent] or [Delete Agent]
    And a direct GET to agent create for that playbook is redirected with an error
    And a direct GET to agent edit is redirected with an error

  Scenario: AGENT-VIEW-10 Owner on released playbook sees Submit PIP on agent detail
    Given Maria owns a Released playbook with agent "Cautious Developer (drdobbs-v2)"
    When Maria views the agent detail page
    Then she does not see [Edit Agent]
    And she sees [Submit PIP] linking to PIP create with playbook context

  # ============================================================
  # GUEST ACCESS — anonymous read-only agent view (@guest_access)
  # ============================================================

  Scenario: AGENT-VIEW-07 Guest views agent in public released playbook read-only
    Given Bob is not logged in
    And Mike owns a Public Released playbook "React Frontend Development"
    And the playbook has agent "Cautious Developer (drdobbs-v2)"
    When Bob GET the agent detail URL for "Cautious Developer (drdobbs-v2)"
    Then he sees agent name "Cautious Developer (drdobbs-v2)"
    And he sees agent description and linked activities read-only
    And he does not see [Edit Agent] or [Delete Agent]

  Scenario: AGENT-VIEW-08 Guest cannot view agent in private playbook
    Given Bob is not logged in
    And Mike owns a Private Released playbook with agent "Secret Agent"
    When Bob GET the agent detail URL for "Secret Agent"
    Then the response status is HTTP 404

  Scenario: AGENT-VIEW-09 Guest views agent embed without login redirect
    Given Bob is not logged in
    And Mike owns a Public Released playbook "React Frontend Development"
    And the playbook has agent "Cautious Developer (drdobbs-v2)"
    When Bob GET "/agents/<pk>/?embed=1" for "Cautious Developer (drdobbs-v2)"
    Then the response status is HTTP 200
    And the embed content loads without navbar or mutation buttons
    And Bob is not redirected to the login page
