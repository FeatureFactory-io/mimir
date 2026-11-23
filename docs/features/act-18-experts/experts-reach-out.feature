@wip @experts @guest_access
Feature: FOB-EXPERTS-REACH-OUT-1 Hand off contact with an expert
  Contact is an email handoff; the Cedar replay does not send an external email.

  Background:
    Given the CEDAR-RFP-01 baseline dataset

  Scenario: EXPERTS-REACH-01 Give authenticated Elena the correct contact destination
    Given Elena is authenticated
    When she inspects Maria's Reach out action on list and public detail
    Then both destinations are "mailto:maria.rodriguez@example.com"
    And the action does not imply that availability is confirmed

  Scenario: EXPERTS-REACH-03 Apply the same guest restriction on public detail
    Given Bob is an anonymous visitor
    When he opens "/experts/mrodriguez/"
    Then Reach out is disabled and has no mailto destination
    And its focusable wrapper explains "You need to be logged in to reach out to the expert"
    And public contribution and released-playbook evidence remain readable
