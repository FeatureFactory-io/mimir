@wip @experts @karma @pips
Feature: FOB-GALDR-CONTRIBUTION-SUMMARY-1 Refresh stable public contribution prose

  Background:
    Given the CEDAR-RFP-01 baseline dataset
    And Hana owns Accessible Forms Review at version 2.0

  Scenario: GALDR-SUMMARY-01 Refresh on submission without awarding acceptance points
    Given Maria drafts Screen Reader Error Recovery with one ADD Activity change
    When Maria submits the PIP through its normal lifecycle
    Then a contribution-summary refresh is requested during processing
    And Maria's total remains 8200
    And the new proposal is not described as accepted
    And the successful public summary is stored on her profile

  Scenario: GALDR-SUMMARY-02 Present one stored summary consistently
    Given Maria's contribution summary has refreshed
    Then her own profile and public expert detail show that stored text
    And her leaderboard hint is a visually truncated excerpt of it
    And the public detail retains the complete paragraph

  Scenario: GALDR-SUMMARY-03 Refresh on normal withdrawal and resubmission
    Given Maria's PIP has reached Reviewed
    When she withdraws it and resubmits through the normal allowed lifecycle
    Then summary refresh is requested again before an administrator decision
    And Maria's total remains 8200

  Scenario: GALDR-SUMMARY-04 Use a live numeric fallback without summary prose
    Given Mike has no stored contribution summary
    When Elena opens the Development leaderboard
    Then Mike's hint uses released-playbook and consumption counts from live data
    And no public-summary paragraph is fabricated

  Scenario: GALDR-SUMMARY-05 Exclude private data and mutable scores from generated prose
    When a contribution-summary request is assembled for Maria
    Then it includes only authorized public contribution evidence and neutral proposal facts
    And it excludes private playbooks, private PIPs, API tokens and email addresses
    And it instructs the generator to omit Karma totals and category point subtotals

  Scenario: GALDR-SUMMARY-06 Preserve stable prose when points change
    Given Maria's stored summary contains stable public facts and no aggregate scores
    When an eligible consumption awards her 5 points
    Then the numeric total is 8205
    And the stored summary is unchanged
    And no extra summary-generation call is required

  Scenario: GALDR-SUMMARY-07 Preserve last good summary on provider failure
    Given Maria has a stored successful contribution summary
    When its next generation attempt fails
    Then the last good paragraph is retained
    And the PIP follows its existing failure/recovery behavior
    And no Karma is awarded for summary generation
