@experts @navigation
Feature: Discover Experts through the existing app navigation

  Background:
    Given the CEDAR-RFP-01 baseline dataset

  @wip @experts
  Scenario: FOB-NAV-EXPERTS-01 Discover Experts in the existing app sidebar
    Given Elena is authenticated in FOB
    When she opens the Collaborate section of the app sidebar
    Then Experts is a link to "/experts/" with data-testid "nav-experts"
    When she follows Experts
    Then "experts-leaderboard" is present and Experts is the active navigation item

  @wip @experts @guest
  Scenario: FOB-NAV-EXPERTS-02 Guest Experts navigation stays public
    Given Bob is an anonymous visitor
    When he follows Experts from the app sidebar
    Then he reaches "/experts/" without a login redirect
    And the guest banner explains sign-in and registration
