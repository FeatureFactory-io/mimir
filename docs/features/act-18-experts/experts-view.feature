@wip @experts @karma
Feature: FOB-EXPERT-VIEW-1 Inspect public contribution evidence
  Elena needs a published example that explains why Maria fits Noor's brief.

  Background:
    Given the CEDAR-RFP-01 baseline dataset

  Scenario: EXPERTS-VIEW-01 Show Maria's identity and full contribution paragraph
    When Elena opens "/experts/mrodriguez/"
    Then the title includes "Maria Rodriguez"
    And "expert-karma-total" reads "8,200"
    And the primary playbook category is "Design"
    And "expert-contribution-summary" contains the complete stored nine-sentence paragraph
    And the paragraph has no line clamp or ellipsis truncation

  Scenario: EXPERTS-VIEW-02 Reconcile the public score-source breakdown
    When Elena opens "/experts/mrodriguez/"
    Then score sources are Released playbooks 5000, PIP contributions 1600, Consumption 1200 and Learning 400
    And the source rows sum to the displayed total 8200
    And category subtotals Design 7200 and Development 1000 are not mislabeled as source rows

  Scenario: EXPERTS-VIEW-03 Follow relevant public released evidence
    Given Elena is on Maria's public expert profile
    When she follows "Accessibility Audit Playbook" version "1.0"
    Then the existing playbook detail route "/playbooks/6101/" is shown
    And its workflow "Lead an Accessibility Review" includes "Trace Keyboard Focus" and "Review Form Feedback"

  Scenario: EXPERTS-VIEW-04 Keep private data out of the public response
    When anonymous Bob opens "/experts/mrodriguez/"
    Then the response omits "Cedar Bid Pricing"
    And it omits "Internal staffing notes for Cedar"
    And it omits "DEMO_ONLY_NOT_A_REAL_TOKEN"
    And no "profile-token-field" exists

  Scenario Outline: EXPERTS-VIEW-05 Reject missing and ineligible profiles
    When Bob opens "/experts/<username>/"
    Then the response status is 404
    Examples:
      | username           |
      | no-such-cedar-user |
      | nberg              |

  Scenario: EXPERTS-VIEW-06 Explain a positive contributor with no public released playbook
    When Elena opens "/experts/skim/"
    Then Sam Kim's positive Karma identity is shown
    And the evidence section says "No public released playbooks to show"
