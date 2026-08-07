@wip @experts @karma @guest_access
Feature: FOB-EXPERTS-REACH-OUT-1 Reach Out to an Expert
  As a competency center head (Elena) or guest (Bob)
  I want to contact an expert from the leaderboard or expert profile
  So that I can invite them to collaborate

  Background:
    Given expert "Mike Chen" (username mchen) exists with email "mchen@example.com"
    And expert "Mike Chen" has total Karma 12450 and primary category "Development"

  Scenario: EXPERTS-REACH-01 Authenticated user reach out opens mailto link
    Given Elena is authenticated in FOB
    And Elena is on /experts/?category=development
    When she clicks [Reach out] on the row for "Mike Chen"
    Then the reach out control links to mailto:mchen@example.com
    And the browser console logs "[experts] reach out: mchen"

  Scenario: EXPERTS-REACH-02 Guest reach out is disabled with login tooltip
    Given Bob is not logged in
    When Bob GET "/experts/?category=development"
    Then [Reach out] on the row for "Mike Chen" is disabled
    And hovering [Reach out] shows tooltip "You need to be logged in to reach out to the expert"
    And data-testid="experts-reach-out-guest-tooltip" is present on the control

  Scenario: EXPERTS-REACH-03 Guest reach out rules apply on expert detail page
    Given Bob is not logged in
    When Bob GET "/experts/mchen/"
    Then [Reach out] on FOB-EXPERT-VIEW-1 is disabled
    And hovering [Reach out] shows tooltip "You need to be logged in to reach out to the expert"
