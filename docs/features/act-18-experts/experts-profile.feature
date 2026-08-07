@wip @experts @karma @guest_access
Feature: FOB-PROFILE-VIEW-1 Karma and Contributions on My Profile
  As a methodology author (Maria)
  I want to see my Karma total, contribution summary, and breakdown on my profile
  So that I understand my community reputation and methodology impact

  Background:
    Given Maria is authenticated in FOB

  Scenario: EXPERTS-PROFILE-01 Profile shows Karma card with total and primary category
    Given Maria has total Karma 8200 and primary category "Design"
    When Maria is on FOB-PROFILE-VIEW-1 at /auth/user/profile/
    Then data-testid="profile-karma-card" is present
    And data-testid="profile-karma-total" reads "8,200"
    And the primary category badge reads "Design"

  Scenario: EXPERTS-PROFILE-02 Profile shows Galdr contribution summary with show more
    Given Maria has a Galdr contribution_summary longer than four lines
    When Maria is on FOB-PROFILE-VIEW-1
    Then data-testid="profile-contribution-summary" shows the full summary text
    And a collapsed preview is shown by default when summary exceeds four lines
    When she clicks [Show more]
    Then the full contribution summary is expanded
    And [Show less] is visible

  Scenario: EXPERTS-PROFILE-03 Profile Karma breakdown table lists source categories
    Given Maria is on FOB-PROFILE-VIEW-1
    And her Karma breakdown includes:
      | source                  | points |
      | Released playbooks      |   5000 |
      | PIP contributions       |    600 |
      | Consumption by others     |    235 |
      | Learning                |     65 |
    Then the Karma breakdown table shows all four source rows

  Scenario: EXPERTS-PROFILE-04 Guest cannot see Karma card on profile
    Given Bob is not logged in
    When Bob GET "/auth/user/profile/"
    Then he is redirected to the login page
    And data-testid="profile-karma-card" is not present
