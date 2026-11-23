@wip @experts @e2e
Feature: Experts browser-backed acceptance contracts
  Actual clipboard, focus and visual layout are certified through real Playwright.

  Background:
    Given the isolated CEDAR-RFP-01 baseline is restored

  @karma
  Scenario: EXPERTS-PROFILE-02 Expand and collapse the long stored summary
    Given Maria is authenticated and her stored paragraph exceeds four lines
    When she opens her own profile
    Then the summary initially displays a four-line preview
    And Show more has aria-expanded "false"
    When she activates Show more
    Then the full stored paragraph is visible
    And the control reads Show less with aria-expanded "true"
    When she activates Show less
    Then the four-line preview is restored

  @guest_access
  Scenario: EXPERTS-REACH-02 Explain guest contact restriction on the list
    Given Bob is an anonymous visitor
    When he opens "/experts/?category=design"
    Then Maria's Reach out button is disabled and has no mailto destination
    And its focusable wrapper explains "You need to be logged in to reach out to the expert"
    And the explanation is reachable by pointer hover and keyboard focus
    And View profile remains available

  @galdr
  Scenario: GALDR-SUMMARY-02 Present one stored summary consistently
    Given Maria's contribution summary has refreshed
    Then her own profile and public expert detail show that stored text
    And her leaderboard hint is a visually truncated excerpt of it
    And the public detail retains the complete paragraph

  @karma
  Scenario: KARMA-COPY-01 Credit a successful authenticated copy to both parties
    Given Maria is authenticated
    When she successfully copies Mike's public released activity 6203
    Then the clipboard receives the actual activity prompt
    And Maria's total becomes 8205 and Mike's becomes 12455
    And both awards belong to Development

  @karma
  Scenario: KARMA-COPY-02 Let guests copy without creating an award
    Given Bob is an anonymous visitor
    When he copies Mike's public released activity 6203
    Then the clipboard receives the actual activity prompt
    And Mike remains at 12450
    And no account or Karma award is created for Bob

  @karma
  Scenario: KARMA-COPY-03 Do not award self-copy
    Given Mike is authenticated
    When he copies his own activity 6203
    Then the clipboard receives the actual activity prompt
    And Mike remains at 12450
