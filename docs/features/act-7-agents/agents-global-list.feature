Feature: FOB-AGENTS-GLOBAL-LIST-1 Global Agents List and Navigation
  As a methodology author (Maria)
  I want to view all agents across all playbooks from the main navbar
  So that I can manage AI assistants globally and navigate to them quickly

  Status: 📋 PLANNED - Not yet implemented
  Related: act-7-agents/agents-list-find.feature (playbook-scoped list)

  Background:
    Given Maria is authenticated in FOB
    And she has 3 playbooks with agents:
      | playbook                  | agents |
      | React Frontend v1.2       |      8 |
      | Product Discovery v2.0    |      5 |
      | UX Research Methodology   |      3 |

  Scenario: AGENT-GLOBAL-01 Navigate to global agents list from navbar
    Given Maria is on any page in FOB
    When she clicks "Agents" in the main navigation bar
    Then she is redirected to FOB-AGENTS-GLOBAL-LIST-1
    And she sees "All Agents" header
    And she sees agent count "(16 agents across 3 playbooks)"

  Scenario: AGENT-GLOBAL-02 View global agents table
    Given Maria is on global agents list
    Then she sees all 16 agents from all playbooks
    And each agent shows: Name, Description, Playbook, Activities, Actions
    And agents are sorted by playbook name by default

  Scenario: AGENT-GLOBAL-03 Filter by playbook
    Given Maria is on global agents list
    When she selects "React Frontend v1.2" from playbook filter
    Then only agents from "React Frontend v1.2" are shown
    And she sees 8 agents

  Scenario: AGENT-GLOBAL-04 Search agents by name across all playbooks
    Given Maria is on global agents list
    When she enters "Developer" in search
    Then agents matching "Developer" from any playbook are shown
    And each result shows which playbook it belongs to

  Scenario: AGENT-GLOBAL-05 Navigate to agent detail from global list
    Given Maria is on global agents list
    When she clicks [View] for an agent
    Then she is redirected to FOB-AGENTS-VIEW_AGENT-1
    And the agent detail page shows playbook context

  Scenario: AGENT-GLOBAL-06 Navigate to playbook from agent row
    Given Maria is on global agents list
    When she clicks the playbook name in an agent row
    Then she is redirected to FOB-PLAYBOOKS-VIEW_PLAYBOOK-1
    And the Agents tab is active

  Scenario: AGENT-GLOBAL-07 Create new agent from global list
    Given Maria is on global agents list
    When she clicks [Create New Agent]
    Then a modal appears "Select Playbook"
    And she sees list of her playbooks
    When she selects a playbook and confirms
    Then she is redirected to FOB-AGENTS-CREATE_AGENT-1
    And the playbook is pre-selected

  Scenario: AGENT-GLOBAL-08 Filter by activity usage
    Given some agents are used in activities
    When she filters by "Used in Activities"
    Then only agents assigned to activities are shown
    And unused agents are hidden

  Scenario: AGENT-GLOBAL-09 Sort by activity count
    Given Maria is on global agents list
    When she clicks the "Activities" column header
    Then agents are sorted by activity count (descending)
    And agents with most activities appear first

  Scenario: AGENT-GLOBAL-10 Empty state display
    Given Maria has zero agents across all playbooks
    Then she sees "No agents yet"
    And she sees "Create your first agent to define AI assistants"
    And she sees [Create Agent] button

  Scenario: AGENT-GLOBAL-11 Breadcrumb navigation
    Given Maria is on global agents list
    Then she sees breadcrumb "Dashboard > Agents"
    When she clicks "Dashboard" in breadcrumb
    Then she returns to FOB-DASHBOARD-1

  Scenario: AGENT-GLOBAL-12 Active navbar indicator
    Given Maria is on global agents list
    Then the "Agents" link in main navbar has "active" class
    And it shows she is on the Agents section

  # ============================================================
  # GUEST ACCESS — anonymous global agents list (@guest_access)
  # See also: guest-global-entity-lists.feature (FOB-GUEST-GLOBAL-05)
  # ============================================================

  Scenario: AGENT-GLOBAL-13 Guest navigates to global agents list without login
    Given Bob is not logged in
    When Bob opens "/agents/"
    Then he sees the global agents list page
    And he sees "All Agents" header
    And he sees the guest banner with data-testid "guest-auth-banner"
    And he does not see the authenticated user menu or dashboard link in the full app navbar

  Scenario: AGENT-GLOBAL-14 Guest global agents list shows released-public rows only
    Given Bob is not logged in
    And Mike owns a Public Released playbook "React Frontend Development" with agents
    And Mike owns a Private Released playbook with agents that must not appear for guests
    When Bob opens "/agents/"
    Then he sees agents from "React Frontend Development"
    And each row shows playbook "React Frontend Development"
    And he does not see agents from private or non-released-public playbooks
    And he can [View] an agent to open read-only agent detail

  Scenario: AGENT-GLOBAL-15 Guest cannot create agent from global list
    Given Bob is not logged in
    When Bob opens "/agents/"
    Then [Create New Agent] is absent or redirects to login with "?next="
    When Bob GET the create-agent URL directly
    Then he is redirected to the FOB login page
