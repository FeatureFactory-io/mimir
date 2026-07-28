Feature: FOB-DASHBOARD-1 Dashboard and Navigation
  As a methodology author (Maria)
  I want to navigate FOB efficiently
  So that I can access my work quickly

  Background:
    Given Maria is authenticated in FOB
    And she is on FOB-DASHBOARD-1

  Scenario: FOB-DASHBOARD-01 View dashboard overview
    Given Maria is on the dashboard
    Then she sees "My Playbooks" section with 5 most recently accessed playbooks
    And she sees "Recently Used" section showing last 10 accessed items (Playbooks/Workflows/Activities) with usage counts
    And she sees quick action buttons for Create/Import/Sync

  Scenario: FOB-DASHBOARD-02 Recently Used section shows usage statistics
    Given Maria is on the dashboard
    And she has accessed "React Frontend Development" playbook 15 times
    And she last accessed it 2 hours ago
    When she views the "Recently Used" section
    Then she sees "React Frontend Development" | Playbook | "15 times" | "2 hours ago"
    And she sees a [View] button to quickly navigate to it

  Scenario: FOB-DASHBOARD-03 Recently Used tracks only views, not edits
    Given Maria is on the dashboard
    When she views the "Recently Used" section
    Then it shows items she has VIEWED/ACCESSED
    And it does NOT show create/update/delete operations
    And it is NOT an audit trail or activity log

  Scenario: FOB-DASHBOARD-04 Navigate to Playbooks
    Given Maria is on the dashboard
    When she clicks "Playbooks" in main navigation
    Then she is redirected to FOB-PLAYBOOKS-LIST+FIND-1

  Scenario: FOB-DASHBOARD-05 Quick create playbook
    Given Maria is on the dashboard
    When she clicks [+ New Playbook] quick action
    Then she is redirected to FOB-PLAYBOOKS-CREATE_PLAYBOOK-1

  Scenario: FOB-DASHBOARD-06 View recent playbook
    Given Maria sees recent playbooks on dashboard
    When she clicks a recent playbook
    Then she is redirected to that playbook's view page

  Scenario: FOB-DASHBOARD-07 Open profile from navbar
    Given Maria is on the dashboard
    When she clicks her username in the top navigation bar
    Then a dropdown opens with items: [View Profile], [Logout]
    When she clicks [View Profile]
    Then she is redirected to FOB-PROFILE-VIEW-1 at /auth/user/profile/

  Scenario: FOB-DASHBOARD-08 Global search
    Given Maria is anywhere in FOB
    When she uses global search for "Component"
    Then she sees results across: Playbooks, Workflows, Activities
    And she can navigate to any result

  # Recently Used feed (Activity rows) — time-window filter FOB-DASHBOARD-09..13
  # Current slice: Activity entities sorted by last access/update; not the full usage-count table in 02.

  Scenario: FOB-DASHBOARD-09 Default Recently Used feed shows last 24h only
    Given Maria is on the dashboard
    Then she sees the "Recently Used" section with data-testid "recently-used-section"
    And the time filter shows [Last 24h] with data-testid "recently-used-hours-label"
    And every activity row in the Recently Used feed has a timestamp within the last 24 hours
    And she does not see activity rows older than 24 hours

  Scenario: FOB-DASHBOARD-10 Recently Used Last hour filter via HTMX
    Given Maria is on the dashboard
    And she has an activity accessed 30 minutes ago in "React Frontend Development"
    And she has an activity accessed 5 hours ago in "React Frontend Development"
    When she selects [Last hour] in the Recently Used time filter
    Then the feed shows the activity from 30 minutes ago
    And the feed does not show the activity from 5 hours ago
    And the time filter shows [Last hour] with data-testid "recently-used-hours-label"

  Scenario: FOB-DASHBOARD-11 Recently Used Last week filter includes and excludes by age
    Given Maria is on the dashboard
    And she has an activity accessed 3 days ago
    And she has an activity accessed 10 days ago
    When she selects [Last week] in the Recently Used time filter
    Then the feed shows the activity from 3 days ago
    And the feed does not show the activity from 10 days ago

  Scenario: FOB-DASHBOARD-12 Recently Used Refresh preserves selected time window
    Given Maria is on the dashboard
    When she selects [Last hour] in the Recently Used time filter
    And she clicks [Refresh] in the Recently Used section
    Then the refresh request includes "?hours=1"
    And the time filter still shows [Last hour]

  Scenario: FOB-DASHBOARD-13 Recently Used badge shows count in selected window
    Given Maria is on the dashboard
    And 3 activities were accessed within the last 24 hours across her playbooks
    And 80 additional activities exist but were not accessed within the last 24 hours
    When she views the "Recently Used" section
    Then she sees "3 in last 24h" with data-testid "recently-used-window-count"
    And she does not see "83 recent" or a total-accessible-activities count in the section header
