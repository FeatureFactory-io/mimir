@wip @experts @karma
Feature: FOB-EXPERT-VIEW-1 Public Expert Profile
  As a competency center head (Elena)
  I want to read an expert's full contribution summary and Karma breakdown
  So that I can judge fit before reaching out

  Background:
    Given expert "Mike Chen" (username mchen) exists with:
      | field              | value           |
      | total_karma        | 12450           |
      | primary_category   | Development     |
      | email              | mchen@example.com |
    And "Mike Chen" has released public playbooks:
      | name                        | version |
      | React Frontend Development  | 1.0     |
      | Testing Patterns Guide      | 1.0     |

  Scenario: EXPERTS-VIEW-01 Expert detail shows identity and Karma total
    Given Elena is authenticated in FOB
    When Elena GET "/experts/mchen/"
    Then the page title includes "Mike Chen"
    And data-testid="expert-karma-total" reads "12,450"
    And the primary category badge reads "Development"

  Scenario: EXPERTS-VIEW-02 Expert detail shows full Galdr contribution summary
    Given "Mike Chen" has a Galdr contribution_summary paragraph
    When Elena GET "/experts/mchen/"
    Then data-testid="expert-contribution-summary" shows the full paragraph text
    And the summary is not truncated with ellipsis

  Scenario: EXPERTS-VIEW-03 Expert detail shows Karma breakdown and public playbooks
    When Elena GET "/experts/mchen/"
    Then the Karma breakdown table is visible
    And released public playbook cards include "React Frontend Development"
    And released public playbook cards include "Testing Patterns Guide"
    And each playbook card has a [View] link

  Scenario: EXPERTS-VIEW-04 Expert detail does not expose private account data
    When Elena GET "/experts/mchen/"
    Then data-testid="profile-token-field" is not present
    And private PIPs are not listed
    And private playbooks are not listed
