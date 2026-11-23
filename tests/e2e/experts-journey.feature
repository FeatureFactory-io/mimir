@wip @experts @e2e @cedar
Feature: CEDAR-RFP-01 Complete Elena's contribution-evidence job in the browser
  This E2E extension uses Playwright bindings separate from Django-client AT.

  Background:
    Given the isolated CEDAR-RFP-01 baseline is restored

  Scenario: CEDAR-JOURNEY-01 Nominate a contributor using evidence rather than rank alone
    Given Elena is authenticated and has Noor's Cedar accessibility brief
    When she opens Experts and selects Design
    Then Sofia, Maria, Priya, Daniel and Hana appear in that order
    When she inspects Sofia's profile and returns to Design
    Then the Design category is preserved
    When she inspects Maria's profile and opens Accessibility Audit Playbook
    Then keyboard-focus and form-feedback evidence is readable
    When she returns to Maria's profile
    Then Reach out targets "mailto:maria.rodriguez@example.com"
    And she can record a candidate, relevant public example, reason and next contact action
    And no email is sent and no availability is asserted

  Scenario: CEDAR-JOURNEY-02 Let Bob evaluate evidence while explaining restricted contact
    Given Bob is an anonymous visitor
    When he follows Design then Maria's public profile
    Then the contribution summary and public playbook remain readable
    And Reach out is disabled with a keyboard-accessible sign-in explanation
    And private sentinels are absent

  Scenario: CEDAR-JOURNEY-03 Show current numeric values with stable contribution prose
    Given Maria is authenticated
    When she expands her own contribution summary
    Then its full stored paragraph and reconciled source rows are visible
    When she successfully copies Mike's eligible public activity
    Then the clipboard receives the prompt and her numeric total becomes 8205
    And her stored contribution prose remains unchanged

  Scenario Outline: EXPERTS-LIST-10 Keep ranking and actions usable at required viewports
    Given the viewport is <width> by <height> CSS pixels
    When Elena opens "/experts/?category=design"
    Then the five contributors remain in the specified rank order
    And category links, names, scores and both card actions are reachable
    And there is no clipping, overlap or page-level horizontal overflow
    Examples:
      | width | height |
      | 1280  | 800    |
      | 1920  | 1080   |
      | 1512  | 982    |
      | 768   | 1024   |
      | 1024  | 768    |
      | 390   | 844    |
      | 360   | 800    |

  Scenario Outline: EXPERTS-VIEW-07 Preserve the read-and-context recipe
    Given the viewport is <width> by <height> CSS pixels
    When Elena opens "/experts/mrodriguez/"
    Then the full contribution body precedes the context rail in reading order
    And under 768 pixels wide the rail stacks below the body
    And contact and evidence links are reachable without page-level horizontal overflow
    Examples:
      | width | height |
      | 1280  | 800    |
      | 1920  | 1080   |
      | 1512  | 982    |
      | 768   | 1024   |
      | 1024  | 768    |
      | 390   | 844    |
      | 360   | 800    |
