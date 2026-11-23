@wip @experts @karma
Feature: FOB-EXPERTS-LIST+FIND-1 Discover contributors by playbook category
  Elena needs public contribution evidence for the Cedar accessibility nomination.
  Ranking helps discovery; it does not certify availability or project suitability.

  Background:
    Given the CEDAR-RFP-01 baseline dataset

  Scenario: EXPERTS-LIST-01 Open Experts from the in-app navigation
    Given Elena is authenticated
    When she follows the Experts navigation link
    Then the URL is "/experts/"
    And the page title is "Experts"
    And the subtitle is "Top contributors by playbook category"
    And the "Development" category is current

  Scenario: EXPERTS-LIST-02 Preserve category selection in the URL
    When Elena selects the "Design" playbook category
    Then the URL is "/experts/?category=design"
    And category links show Product, Development, Research, Design and Other
    And the Design link has aria-current "page"
    When she refreshes the page
    Then Design remains current

  Scenario: EXPERTS-LIST-03 Rank Design by total points and enforce the five-person boundary
    When Elena opens "/experts/?category=design"
    Then the ranked usernames are:
      | username   | total | design_subtotal |
      | sreed      | 15400 | 13900           |
      | mrodriguez | 8200  | 7200            |
      | pnair      | 7600  | 7600            |
      | dortiz     | 6900  | 6900            |
      | hkim       | 5800  | 5800            |
    And sixth eligible Design contributor "tmartin" is absent
    And Development contributor "mchen" is absent
    And zero-Karma contributor "nberg" is absent
    When Elena selects Development
    Then Mike Chen 12450 precedes Jordan Lee 6100
    And Maria is absent because her primary playbook category is Design

  Scenario: EXPERTS-LIST-04 Show readable contribution signals and actions
    When Elena opens "/experts/?category=design"
    Then card "experts-card-mrodriguez" shows rank 2 and "Maria Rodriguez"
    And it shows total "8,200", category "Design", and an accessibility contribution hint
    And it has an avatar or initials plus View profile and Reach out controls
    And it makes no availability or suitability assertion

  Scenario: EXPERTS-LIST-05 Follow Maria to her full public evidence
    Given Elena is on the Design leaderboard
    When she follows Maria's View profile link
    Then the URL is "/experts/mrodriguez/"
    And "expert-contribution-summary" contains her full stored paragraph

  Scenario: EXPERTS-LIST-06 Explain an empty category
    When Elena opens "/experts/?category=other"
    Then no contributor cards are present
    And she sees "No experts in Other yet — release a playbook to be the first"

  Scenario: EXPERTS-LIST-07 Allow Bob to evaluate public rankings
    Given Bob is an anonymous visitor
    When he opens "/experts/?category=design"
    Then the same five Design contributors are visible
    And a guest banner offers Sign In and Register
    And no own-profile Karma card or API token is present

  Scenario: EXPERTS-LIST-08 Resolve an equal total deterministically
    Given the isolated TIE03 variant with Alina Park and Sofia Reed at 15400
    When Elena opens "/experts/?category=design"
    Then "apark" precedes "sreed"

  Scenario: EXPERTS-LIST-09 Recover an unknown category
    When Elena opens "/experts/?category=unrecognized"
    Then Development is the current category
    And no server error or unrelated category data is shown
